"""Collocate gridded predictors with CPCB stations.

For supervised training we need, for each (station, date), the satellite/met/static
predictor values sampled at the station location aligned with the observed
pollutant. This produces the long-format training table consumed by the database
builder.
"""

from __future__ import annotations

import pandas as pd
import xarray as xr

from isro_aqi.utils.logging import get_logger

log = get_logger("collocate")


def sample_at_stations(
    ds: xr.Dataset, stations: pd.DataFrame, lon_col="lon", lat_col="lat"
) -> pd.DataFrame:
    """Nearest-cell sample of every predictor at each station, per time step.

    Returns long format: one row per (station_id, time) with predictor columns.
    """
    lons = xr.DataArray(stations[lon_col].values, dims="station")
    lats = xr.DataArray(stations[lat_col].values, dims="station")
    sampled = ds.sel(lon=lons, lat=lats, method="nearest")  # (time, station)

    df = sampled.to_dataframe().reset_index()
    # attach station identity
    station_lookup = stations.reset_index(drop=True)
    df = df.merge(
        station_lookup.assign(station=range(len(station_lookup))),
        on="station",
        suffixes=("", "_meta"),
    )
    log.info(f"collocated {len(df)} predictor rows at {len(stations)} stations")
    return df


def join_targets(predictors: pd.DataFrame, cpcb_daily: pd.DataFrame) -> pd.DataFrame:
    """Inner-join collocated predictors with CPCB daily observations on (station, date)."""
    pred = predictors.copy()
    pred["date"] = pd.to_datetime(pred["time"]).dt.floor("D")
    merged = pred.merge(cpcb_daily, on=["station_id", "date"], how="inner")
    log.info(f"training rows after target join: {len(merged)}")
    return merged
