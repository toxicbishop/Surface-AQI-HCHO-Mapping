"""CPCB ground-station ingestion -- the model's ground truth / targets.

CPCB runs 500+ Continuous Ambient Air Quality Monitoring Stations (CAAQMS).
Hourly pollutant data is downloaded from the CCR portal
(https://airquality.cpcb.gov.in/ccr/) or data.gov.in. Bulk access is
captcha/manual, so this module assumes you have station CSVs on disk and focuses
on parsing them into a tidy daily table with the correct CPCB averaging windows
(24-h means; 8-h max for O3 and CO) ready for AQI computation and collocation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from isro_aqi.utils.logging import get_logger

log = get_logger("cpcb")

POLLUTANT_ALIASES = {
    "PM2.5": "pm25", "PM10": "pm10", "NO2": "no2",
    "SO2": "so2", "Ozone": "o3", "O3": "o3", "CO": "co",
}


def load_station_metadata(path: str | Path) -> pd.DataFrame:
    """Load station metadata CSV -> columns: station_id, name, lat, lon, state, city."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def load_raw_hourly(path: str | Path) -> pd.DataFrame:
    """Read a raw CPCB hourly export into long form (station_id, datetime, pollutant, value)."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={c: POLLUTANT_ALIASES.get(c, c) for c in df.columns})
    return df


def to_daily(hourly: pd.DataFrame, station_col="station_id", time_col="datetime") -> pd.DataFrame:
    """Aggregate hourly observations to CPCB daily values.

    24-h mean for PM2.5/PM10/NO2/SO2; 8-h rolling max for O3 and CO (per CPCB AQI
    averaging rules in config/aqi_breakpoints.yaml). Requires at least 16 valid
    hours/day (CPCB completeness rule) else the day is dropped as NaN.

    Cadence-aware: some sources (e.g. OpenAQ) already deliver DAILY rows, not
    hourly. For a station-day with only a few records the 16-distinct-hour gate
    and the 8h ``min_periods=6`` rolling window would silently drop everything.
    When a station-day has <= ``DAILY_MAX_ROWS`` rows we treat it as already
    daily and pass the values through (simple aggregation, no completeness gate).
    """
    hourly = hourly.copy()
    hourly[time_col] = pd.to_datetime(hourly[time_col])
    hourly["date"] = hourly[time_col].dt.floor("D")

    mean_cols = [c for c in ("pm25", "pm10", "no2", "so2") if c in hourly]
    max8_cols = [c for c in ("o3", "co") if c in hourly]

    # A station-day with at most this many rows is treated as already-daily.
    DAILY_MAX_ROWS = 3

    out = []
    for (sid, date), g in hourly.groupby([station_col, "date"]):
        already_daily = len(g) <= DAILY_MAX_ROWS
        if not already_daily and g[time_col].dt.hour.nunique() < 16:
            continue
        rec = {"station_id": sid, "date": date}
        for c in mean_cols:
            rec[c] = g[c].mean()
        for c in max8_cols:
            if already_daily:
                # already a daily value -> take the day's max directly; the 8h
                # rolling window cannot apply to a single sub-daily observation.
                rec[c] = g[c].max()
            else:
                # 8-hour rolling mean, then take the daily max of those windows
                roll = g.set_index(time_col)[c].sort_index().rolling("8h", min_periods=6).mean()
                rec[c] = roll.max()
        out.append(rec)
    daily = pd.DataFrame(out)
    log.info(f"CPCB daily records: {len(daily)} from {hourly[station_col].nunique()} stations")
    return daily
