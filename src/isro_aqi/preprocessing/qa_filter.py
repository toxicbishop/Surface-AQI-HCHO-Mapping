"""Quality control.

  * TROPOMI HCHO qa screening is applied at INGESTION via a cloud_fraction mask
    (cloud_fraction < cfg.hcho.cloud_fraction_max, default 0.4) plus the config
    qa_threshold (default 0.5, the HCHO community standard -- NOT 0.75). This
    module then adds physical-range and statistical-outlier filters for all
    variables before they enter the database.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

# Physically plausible ranges (loose) used to drop retrieval garbage.
# Column densities are in mol/m^2; met/AOD/ground in their native units.
#
# NOTE on units: the gas COLUMN ranges below are written for the mol/m^2 (GEE/L3)
# convention. Our synthetic stack -- and many TROPOMI products -- carry columns in
# molec/cm^2 instead (magnitudes ~1e15-1e16). Hard-clipping a molec/cm^2 column to
# a mol/m^2 range would NaN 100% of valid data. So gas columns are clipped only
# when the data's magnitude PLAUSIBLY matches the configured range (see
# ``_plausible_for_range``); otherwise the clip is skipped and a sentinel non-
# negativity / sigma screen still guards against garbage downstream.
VALID_RANGES = {
    "aod": (0.0, 5.0),
    "no2": (0.0, 5e-3),
    "so2": (-1e-3, 5e-3),
    "co": (0.0, 1.0),
    "o3": (0.0, 1.0),
    "hcho": (-1e-4, 5e-3),
    "temperature": (220.0, 330.0),
    "rh": (0.0, 100.0),
    "pressure": (5e4, 1.1e5),
    "pm25": (0.0, 1000.0),
    "pm10": (0.0, 2000.0),
}

# Gas-column variables whose unit convention may differ from VALID_RANGES.
_GAS_COLUMNS = ("no2", "so2", "co", "o3", "hcho")


def _plausible_for_range(da: xr.DataArray, lo: float, hi: float) -> bool:
    """True if the data's typical magnitude plausibly matches [lo, hi].

    Compares the median |value| against the range scale. If the data is orders of
    magnitude larger (e.g. molec/cm^2 vs mol/m^2), the configured range does not
    apply and clipping would destroy the column -- so we skip it.
    """
    finite = da.where(np.isfinite(da))
    med = float(np.abs(finite).median(skipna=True))
    if not np.isfinite(med) or med == 0.0:
        return True  # nothing to judge by -> allow clip (it's a no-op anyway)
    # allow up to ~100x the upper bound before declaring a unit mismatch.
    return med <= max(abs(lo), abs(hi)) * 100.0


def clip_valid_range(ds: xr.Dataset) -> xr.Dataset:
    """Mask values outside each variable's physical range to NaN.

    Gas-column variables are clipped only when their magnitude plausibly matches
    the (mol/m^2) range, so a molec/cm^2 column is not destroyed (unit-tolerant).
    Non-gas variables (AOD, met, PM) are always clipped to their native ranges.
    """
    for var, (lo, hi) in VALID_RANGES.items():
        if var not in ds:
            continue
        if var in _GAS_COLUMNS and not _plausible_for_range(ds[var], lo, hi):
            # unit mismatch (e.g. molec/cm^2): skip range clip, keep non-negativity
            if lo >= 0.0:
                ds[var] = ds[var].where(ds[var] >= lo)
            continue
        ds[var] = ds[var].where((ds[var] >= lo) & (ds[var] <= hi))
    return ds


def drop_sigma_outliers(da: xr.DataArray, n_sigma: float = 5.0) -> xr.DataArray:
    """Mask points beyond n_sigma from the mean (per-variable global screen)."""
    mu = da.mean(skipna=True)
    sd = da.std(skipna=True)
    return da.where(np.abs(da - mu) <= n_sigma * sd)


def apply(ds: xr.Dataset, sigma: float = 5.0) -> xr.Dataset:
    ds = clip_valid_range(ds)
    for var in ds.data_vars:
        ds[var] = drop_sigma_outliers(ds[var], sigma)
    return ds
