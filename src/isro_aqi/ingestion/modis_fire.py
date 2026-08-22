"""MODIS fire + EVI ingestion via GEE.

Three products feed the biomass-burning analysis (Phase 8) and HCHO attribution
(Phases 10-11):
    active fire   MOD14A1  (FireMask, MaxFRP)   -> daily fire activity / FRP
    burned area   MCD64A1  (BurnDate)           -> monthly burned extent
    EVI           MOD13A2  (EVI)                -> biogenic VOC proxy

Kuttippurath et al. 2022 use MODIS fire-count + FRP as the pyrogenic proxy and
EVI as the biogenic proxy, gridded to 0.5 deg.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.config import Config
from isro_aqi.ingestion.gee_auth import aoi_geometry, export_image, init_ee
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("modis_fire")


def active_fire_frp(cfg: Config, start: str, end: str) -> "ee.Image":
    """Mean and max fire radiative power over the period (MW). FRP is MaxFRP/10.

    `fire_count` is the number of days a pixel had a confident fire detection
    (MOD14A1 FireMask class >= 7: 7=low, 8=nominal, 9=high confidence fire), NOT
    the collection size -- ``coll.count()`` would return the same value for every
    pixel (the number of images), which is meaningless as a per-pixel fire metric.
    FRP bands are unmasked to 0 BEFORE mean/max so non-fire days count as 0 MW
    rather than being skipped by the masked reducer (which would bias means high).
    """
    import ee

    spec = cfg.datasets["modis_fire"]["active_fire"]
    region = aoi_geometry(cfg)
    coll = (
        ee.ImageCollection(spec["asset"])
        .filterDate(start, end)
        .filterBounds(region)
    )
    # per-pixel count of confident-fire days (FireMask >= 7)
    fire_days = coll.map(lambda i: i.select("FireMask").gte(7))
    fire_count = fire_days.sum().rename("fire_count")
    # FRP in MW (MaxFRP/10); unmask non-fire pixels to 0 before reducing.
    frp = coll.map(lambda i: i.select("MaxFRP").divide(10.0).unmask(0))
    # .toFloat(): fire_count is integer-typed while the FRP bands are Float32, and
    # GEE's image export requires all bands to share a data type -- cast to one.
    return ee.Image.cat(
        frp.mean().rename("frp_mean"),
        frp.max().rename("frp_max"),
        fire_count,
    ).toFloat()


def burned_area(cfg: Config, start: str, end: str) -> "ee.Image":
    """Binary burned mask for the period from MCD64A1 BurnDate."""
    import ee

    spec = cfg.datasets["modis_fire"]["burned_area"]
    region = aoi_geometry(cfg)
    coll = (
        ee.ImageCollection(spec["asset"]).select("BurnDate").filterDate(start, end).filterBounds(region)
    )
    return coll.max().gt(0).rename("burned").unmask(0)


def evi(cfg: Config, start: str, end: str) -> "ee.Image":
    """Mean EVI (biogenic VOC proxy), scaled to physical units."""
    import ee

    spec = cfg.datasets["modis_fire"]["evi"]
    region = aoi_geometry(cfg)
    coll = (
        ee.ImageCollection(spec["asset"]).select("EVI").filterDate(start, end).filterBounds(region)
    )
    return coll.mean().multiply(0.0001).rename("evi")


def export_period(cfg: Config, start: str, end: str) -> list:
    init_ee(cfg)
    return [
        export_image(active_fire_frp(cfg, start, end), cfg, f"modis_frp_{start}_{end}", 1000, "fire"),
        export_image(burned_area(cfg, start, end), cfg, f"modis_burned_{start}_{end}", 500, "fire"),
        export_image(evi(cfg, start, end), cfg, f"modis_evi_{start}_{end}", 1000, "fire"),
    ]
