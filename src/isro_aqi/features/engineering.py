"""Feature engineering.

Adds physically-motivated derived predictors:
  * FNR = HCHO / NO2  -> ozone-production sensitivity regime (Dong 2026 / Jin 2015).
  * cyclical day-of-year encoding -> seasonality without a discontinuity at Dec 31.
  * temporal lags & rolling means -> persistence / accumulation (smog build-up).
  * AOD x BLH interaction -> column-to-surface scaling (high BLH dilutes columns).

Tabular features here feed RF/XGBoost. The CNN consumes spatial patches and the
LSTM consumes sequences -- those are assembled in models/dataset.py, not here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_fnr(df: pd.DataFrame, eps: float = 1e-30) -> pd.DataFrame:
    """HCHO/NO2 ratio. Regime labels: <2.67 VOC-limited, >3.47 NOx-limited."""
    if {"hcho", "no2"}.issubset(df.columns):
        df["fnr"] = df["hcho"] / (df["no2"] + eps)
    return df


def add_cyclical_doy(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    doy = pd.to_datetime(df[date_col]).dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return df


def add_interactions(df: pd.DataFrame) -> pd.DataFrame:
    if {"aod", "blh"}.issubset(df.columns):
        df["aod_blh"] = df["aod"] * df["blh"]
    if {"temperature", "solar_radiation"}.issubset(df.columns):
        # proxy for photochemical activity (drives O3 and HCHO)
        df["photo_index"] = df["temperature"] * df["solar_radiation"]
    return df


def add_temporal_lags(
    df: pd.DataFrame, cols: list[str], lags=(1, 2, 3), group=None
) -> pd.DataFrame:
    """Per-series lagged values and 3-day rolling means (requires sorted-by-date).

    ``group`` is the grouping key for the series. It defaults to ["station_id"]
    when that column is present (the natural per-station series), else falling
    back to ["lat", "lon"] for gridded data.

    The 3-day rolling mean (``_roll3``) is computed on the LAGGED series (shift 1
    then roll) so it summarises the PRIOR three days only and never leaks the
    current row's value -- otherwise the feature would include the target-day
    observation it is meant to predict from.
    """
    if group is None:
        group = ["station_id"] if "station_id" in df.columns else ["lat", "lon"]
    group = list(group)
    df = df.sort_values("date")
    g = df.groupby(group)
    for c in cols:
        if c not in df:
            continue
        for lag in lags:
            df[f"{c}_lag{lag}"] = g[c].shift(lag)
        # shift(1) before rolling so the window covers the 3 PRECEDING days only.
        df[f"{c}_roll3"] = g[c].transform(
            lambda s: s.shift(1).rolling(3, min_periods=1).mean()
        )
    return df


def add_engineered_features(df: pd.DataFrame, lag_cols: list[str] | None = None) -> pd.DataFrame:
    """Apply the full feature-engineering chain in order."""
    df = add_fnr(df)
    df = add_cyclical_doy(df)
    df = add_interactions(df)
    if lag_cols:
        df = add_temporal_lags(df, lag_cols)
    return df
