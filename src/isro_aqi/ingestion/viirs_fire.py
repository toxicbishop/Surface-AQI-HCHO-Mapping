"""VIIRS active-fire ingestion.

VIIRS (375 m) resolves small agricultural fires that MODIS (1 km) misses -- key
for stubble-burning over Punjab/Haryana. Two access paths:

  1. NASA FIRMS API (VNP14IMGTDL_NRT, 375 m) -> CSV of fire pixels with FRP,
     confidence, day/night. Best for point-level fire counts near receptors.
  2. GEE 'FIRMS' collection (MODIS C6 T21) -> gridded fallback when the API key
     is unavailable.

A free FIRMS map key is required for the API: https://firms.modaps.eosdis.nasa.gov/api/
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pandas as pd
import requests

from isro_aqi.config import Config
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("viirs_fire")


def fetch_firms_api(
    cfg: Config, map_key: str, start: str, days: int = 1, source: str = "VIIRS_SNPP_NRT"
) -> pd.DataFrame:
    """Fetch VIIRS active fire pixels over the India AOI from the FIRMS area API.

    Returns a DataFrame with lat/lon, FRP (`frp`), `confidence`, `acq_date`,
    `daynight`. The API serves up to 10 days per request.
    """
    min_lon, min_lat, max_lon, max_lat = cfg.aoi.bbox
    area = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{source}/{area}/{days}/{start}"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    log.info(f"FIRMS {source} {start}: {len(df)} fire pixels")
    return df


def gridded_fallback(cfg: Config, start: str, end: str) -> "ee.Image":
    """Mean MODIS FIRMS brightness temperature (T21) over the period via GEE."""
    import ee

    from isro_aqi.ingestion.gee_auth import aoi_geometry, init_ee

    init_ee(cfg)
    spec = cfg.datasets["viirs_fire"]
    region = aoi_geometry(cfg)
    coll = (
        ee.ImageCollection(spec["firms_asset"])
        .select(spec["firms_band"])
        .filterDate(start, end)
        .filterBounds(region)
    )
    return coll.mean().rename("fire_t21")
