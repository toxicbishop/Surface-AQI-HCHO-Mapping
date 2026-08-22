"""INSAT-3D AOD ingestion via ISRO MOSDAC.

INSAT-3D Imager L2B AOD (~10 km) is the project's flagship indigenous predictor.
It is NOT on Google Earth Engine, so it is ordered/downloaded from MOSDAC
(https://www.mosdac.gov.in) which requires (free) registration. MOSDAC serves
files over an authenticated order system / SFTP; there is no clean public REST
API, so the download step is semi-manual or scripted against your account.

This module provides:
    * the documented access flow (download_order)
    * a reader that converts an INSAT-3D L2B AOD HDF5/NetCDF granule onto the
      project analysis grid (read_granule)

Cross-check option: MAIAC AOD (MODIS/061/MCD19A2, 1 km) on GEE -- Wang et al.
2023 used MAIAC; see datasets.yaml `insat_aod.fallback_gee`.
"""

from __future__ import annotations

from pathlib import Path

import xarray as xr

from isro_aqi.config import Config
from isro_aqi.utils.geo import Grid, regrid
from isro_aqi.utils.logging import get_logger

log = get_logger("insat_aod")

MOSDAC_PORTAL = "https://www.mosdac.gov.in"


def download_order(username: str, password: str, start: str, end: str, out_dir: str) -> None:
    """Order + download INSAT-3D L2B AOD for a date range from MOSDAC.

    NOT IMPLEMENTED -- MOSDAC has no clean public REST API; access is an
    authenticated order/SFTP flow tied to your registered account, so it cannot
    be wired generically here. Use the MAIAC GEE fallback for prototyping.

    MOSDAC access flow (implement against your registered account):
      1. Authenticate to the MOSDAC portal / SFTP with credentials.
      2. Place a data order for product '3DIMG_L2B_AOD' over the date range.
      3. Poll the order until ready, then pull the granules to `out_dir`.

    Many users instead bulk-download via the MOSDAC "Open Data" / OrderID SFTP
    path. Keep credentials in env vars, never in the repo.
    """
    raise NotImplementedError(
        "Implement MOSDAC order/SFTP for your account. See README and "
        "datasets.yaml; use the MAIAC GEE fallback for prototyping."
    )


def read_granule(path: str | Path, grid: Grid, aod_var: str = "AOD") -> xr.DataArray:
    """Read one INSAT-3D L2B AOD granule (HDF5/NetCDF) and regrid onto `grid`.

    NOT IMPLEMENTED for real granules -- INSAT-3D L2B products carry geolocation
    as separate 2-D swath arrays, not CF lat/lon coords, so the swath-to-grid
    reprojection is granule-schema-specific and cannot be inferred generically;
    this function only handles the (rare) case where the granule already exposes
    'lat'/'lon' coords and otherwise raises with guidance.

    INSAT-3D L2B products are typically HDF5 with geolocation arrays. Adjust
    `aod_var` and the lat/lon variable names to match the actual granule schema
    (inspect once with `xarray.open_dataset(path).variables`).
    """
    ds = xr.open_dataset(path)
    da = ds[aod_var]
    if "lat" not in da.coords or "lon" not in da.coords:
        # INSAT granules often carry geolocation as separate 2-D arrays; the
        # real implementation reprojects from those. Documented here as the hook.
        raise ValueError(
            f"{Path(path).name}: no lat/lon coords found. Map the granule's "
            "geolocation arrays to 'lat'/'lon' before regridding."
        )
    return regrid(da.rename("aod"), grid, method="linear")
