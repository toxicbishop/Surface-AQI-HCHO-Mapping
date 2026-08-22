"""I/O helpers. Parquet for tabular (the unified database), NetCDF/Zarr for
gridded stacks, GeoTIFF for single-layer rasters.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import xarray as xr


def ensure_dir(path: str | Path) -> Path:
    """Create a directory (and parents) and return it as a Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- tabular (unified database) -------------------------------------------- #
def write_parquet(df: pd.DataFrame, path: str | Path, partition_cols: list[str] | None = None):
    """Write a DataFrame to parquet, optionally Hive-partitioned (e.g. by year/month)."""
    p = Path(path)
    ensure_dir(p.parent)
    df.to_parquet(p, partition_cols=partition_cols, index=False)


def read_parquet(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(path, columns=columns)


# --- gridded stacks -------------------------------------------------------- #
def write_netcdf(ds: xr.Dataset, path: str | Path):
    p = ensure_dir(Path(path).parent) / Path(path).name
    comp = {"zlib": True, "complevel": 4}
    encoding = {v: comp for v in ds.data_vars}
    ds.to_netcdf(p, encoding=encoding)


def read_netcdf(path: str | Path) -> xr.Dataset:
    return xr.open_dataset(path)


def write_zarr(ds: xr.Dataset, path: str | Path):
    """Zarr is preferred for large multi-year stacks (chunked, cloud-friendly)."""
    p = Path(path)
    ensure_dir(p.parent)
    ds.to_zarr(p, mode="w")


def read_zarr(path: str | Path) -> xr.Dataset:
    return xr.open_zarr(path)
