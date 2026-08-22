"""Temporal aggregation to daily / monthly / seasonal / annual composites.

Seasons follow the Indian (IMD) calendar defined in config.time.seasons so the
post-monsoon (Oct-Nov paddy stubble) and pre-monsoon (wheat residue + forest
fires) burning windows fall cleanly into single bins.
"""

from __future__ import annotations

import xarray as xr


def daily_mean(ds: xr.Dataset) -> xr.Dataset:
    return ds.resample(time="1D").mean()


def monthly_mean(ds: xr.Dataset) -> xr.Dataset:
    return ds.resample(time="1MS").mean()


def annual_mean(ds: xr.Dataset) -> xr.Dataset:
    return ds.resample(time="1YS").mean()


def seasonal_mean(ds: xr.Dataset, seasons: dict[str, list[int]]) -> xr.Dataset:
    """Mean per IMD season per year. Adds a 'season' coordinate.

    seasons: {"winter": [1,2], "pre_monsoon": [3,4,5], ...}
    """
    month_to_season = {m: name for name, months in seasons.items() for m in months}
    season_da = xr.DataArray(
        [month_to_season[m] for m in ds["time"].dt.month.values],
        coords={"time": ds["time"]},
        dims="time",
    )
    return ds.groupby(season_da.rename("season")).mean("time")
