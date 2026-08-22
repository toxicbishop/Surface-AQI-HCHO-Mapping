"""SRTM elevation (+ derived slope/aspect) ingestion via GEE.

Elevation is a static predictor: terrain modulates boundary-layer dynamics,
ventilation and pollutant trapping (e.g. the Indo-Gangetic Plain bowl).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.config import Config
from isro_aqi.ingestion.gee_auth import aoi_geometry, export_image, init_ee
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("srtm")


def terrain_stack(cfg: Config) -> "ee.Image":
    """Elevation + slope + aspect over the AOI."""
    import ee

    spec = cfg.datasets["srtm"]
    region = aoi_geometry(cfg)
    dem = ee.Image(spec["asset"]).select(spec["band"]).clip(region)
    terrain = ee.Terrain.products(dem)  # elevation, slope, aspect, hillshade
    return ee.Image.cat(
        dem.rename("elevation"),
        terrain.select("slope").rename("slope"),
        terrain.select("aspect").rename("aspect"),
    )


def export(cfg: Config, scale_m: int = 7000) -> list:
    init_ee(cfg)
    return [export_image(terrain_stack(cfg), cfg, "srtm_terrain", scale_m, folder="static")]
