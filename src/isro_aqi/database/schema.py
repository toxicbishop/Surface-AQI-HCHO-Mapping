"""Unified record schema for the India-wide database.

Each record = one (date, lat, lon) cell. PREDICTORS are model inputs; TARGETS are
the CPCB-observed surface concentrations (present only where a cell collocates
with a station, or NaN elsewhere -- the unlabelled cells are what we predict to
make the maps).
"""

from __future__ import annotations

import numpy as np

# --- keys ------------------------------------------------------------------
KEYS = ["date", "lat", "lon"]

# --- predictors (model inputs) ---------------------------------------------
PREDICTORS = [
    # satellite columns
    "aod",                       # INSAT-3D (or MAIAC fallback)
    "no2", "so2", "co", "o3", "hcho",   # TROPOMI tropospheric columns
    # meteorology (ERA5 + BLH from CDS)
    "temperature", "rh", "u_wind", "v_wind", "wind_speed",
    "pressure", "precipitation", "solar_radiation", "blh",
    # fire / biomass
    "frp_mean", "frp_max", "fire_count", "burned", "evi",
    # static
    "elevation", "slope", "aspect",
    "lc_tree", "lc_shrub", "lc_grass", "lc_crop", "lc_built",
    "lc_bare", "lc_water", "lc_wetland",
    # spatial context (standard AQ-ML predictors; also surface spatial CV leakage)
    "lat", "lon",
    # engineered (see features/engineering.py)
    "fnr",                       # HCHO / NO2 ratio (O3-sensitivity regime)
    "doy_sin", "doy_cos",        # cyclical day-of-year
]

# --- targets (CPCB ground truth) -------------------------------------------
TARGETS = ["pm25", "pm10", "no2_obs", "so2_obs", "o3_obs", "co_obs"]

COLUMNS = KEYS + PREDICTORS + TARGETS

# dtypes for compact parquet
DTYPES = {c: np.float32 for c in PREDICTORS + TARGETS}
DTYPES["lat"] = np.float32
DTYPES["lon"] = np.float32

# Partition the parquet store by these (added at build time from `date`).
PARTITION_COLS = ["year", "month"]
