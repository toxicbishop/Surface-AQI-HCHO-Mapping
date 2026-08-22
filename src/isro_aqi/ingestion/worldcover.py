"""ESA WorldCover land-cover ingestion via GEE.

WorldCover v200 has 11 LULC classes at 10 m. For modelling we don't want the raw
10 m map; we want the *fractional cover* of each class within every analysis grid
cell (e.g. % cropland, % urban, % forest), which becomes a set of static
predictors. Cropland fraction also helps explain agricultural-burning HCHO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.config import Config
from isro_aqi.ingestion.gee_auth import aoi_geometry, export_image, init_ee
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("worldcover")

# WorldCover class code -> short name
CLASSES = {
    10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built",
    60: "bare", 70: "snow", 80: "water", 90: "wetland", 95: "mangrove", 100: "moss",
}


def fractional_cover(cfg: Config, scale_m: int = 7000) -> "ee.Image":
    """Per-class fractional cover image aggregated to `scale_m` cells (0-1)."""
    import ee

    spec = cfg.datasets["worldcover"]
    region = aoi_geometry(cfg)
    lc = ee.ImageCollection(spec["asset"]).first().select(spec["band"]).clip(region)

    bands = []
    for code, name in CLASSES.items():
        frac = (
            lc.eq(code)
            # 10 m -> ~7 km is ~700^2 ~= 490k native pixels per output cell; the
            # old maxPixels=1024 silently truncated the aggregation. GEE caps
            # reduceResolution at 65535 input pixels, so we max it out here and
            # aggregate in TWO stages (10 m -> ~1 km -> target) so each stage
            # stays within the cap while still covering every input pixel.
            .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=65535)
            .reproject(crs=cfg.grid.crs, scale=1000)
            .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=65535)
            .reproject(crs=cfg.grid.crs, scale=scale_m)
            .rename(f"lc_{name}")
        )
        bands.append(frac)
    return ee.Image.cat(bands)


def export(cfg: Config, scale_m: int = 7000) -> list:
    init_ee(cfg)
    img = fractional_cover(cfg, scale_m)
    return [export_image(img, cfg, "worldcover_fractions", scale_m, folder="static")]
