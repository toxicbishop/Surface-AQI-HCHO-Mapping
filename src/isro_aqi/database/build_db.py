"""Assemble the unified database from preprocessed daily Datasets.

Two products:
  1. TRAINING TABLE  -- station-collocated rows with non-null targets (for fitting).
  2. INFERENCE GRID  -- every cell, every day, predictors only (for map generation).

Both share the schema in schema.py and are written as year/month-partitioned
parquet so downstream code can scan single months without loading 100 M rows.
"""

from __future__ import annotations

import pandas as pd
import xarray as xr

from isro_aqi.database.schema import DTYPES, PARTITION_COLS, PREDICTORS
from isro_aqi.utils.io import write_parquet
from isro_aqi.utils.logging import get_logger

log = get_logger("build_db")


def _add_partitions(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["date"])
    df["year"] = d.dt.year
    df["month"] = d.dt.month
    return df


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    for col, dt in DTYPES.items():
        if col in df:
            df[col] = df[col].astype(dt)
    return df


def build_training_table(collocated: pd.DataFrame, out_path: str) -> pd.DataFrame:
    """Persist the supervised training table (collocated predictors + targets)."""
    df = _add_partitions(_coerce(collocated))
    write_parquet(df, out_path, partition_cols=PARTITION_COLS)
    log.info(f"training table -> {out_path} ({len(df):,} rows)")
    return df


def build_inference_grid(daily: xr.Dataset, out_path: str) -> None:
    """Flatten a daily predictor Dataset to the partitioned inference parquet.

    This is the large table (~50-100 M rows over multi-year India).

    NOTE: the previous implementation wrote each day with a SEPARATE
    ``write_parquet(..., partition_cols=...)`` call. ``DataFrame.to_parquet`` to a
    partitioned dataset overwrites the destination partition directory, so days
    sharing a year/month partition clobbered one another -- only the LAST day of
    each month survived (despite the "appended" docstring). We instead build all
    per-day frames and write them in ONE partitioned call so every day lands in
    its month partition. (For multi-year India this is still large; chunk by year
    upstream if memory is a concern -- each year is a disjoint partition set and
    can be written to its own path safely.)
    """
    frames = []
    for t in daily["time"].values:
        day = daily.sel(time=t)
        df = day.to_dataframe().reset_index()
        df = df.rename(columns={"time": "date"})
        keep = ["date", "lat", "lon"] + [c for c in PREDICTORS if c in df]
        df = _add_partitions(_coerce(df[keep].dropna(how="all", subset=PREDICTORS)))
        frames.append(df)
    if not frames:
        log.info(f"inference grid -> {out_path} (no days)")
        return
    full = pd.concat(frames, ignore_index=True)
    write_parquet(full, out_path, partition_cols=PARTITION_COLS)
    log.info(f"inference grid -> {out_path} ({len(full):,} rows)")
