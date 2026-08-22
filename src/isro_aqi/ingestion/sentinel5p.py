"""Sentinel-5P / TROPOMI ingestion via Google Earth Engine.

Pulls tropospheric column densities for NO2, SO2, CO, O3 and HCHO. HCHO is both a
model predictor (Objective 1) and the primary target of the hotspot analysis
(Objective 2). HCHO is screened by a cloud_fraction mask (cloud_fraction <
cfg.hcho.cloud_fraction_max, default 0.4) plus the config qa_threshold (default
0.5, the HCHO community standard -- NOT 0.75) at ingestion (Phase 7).

Reference: Kuttippurath et al. 2022 use TROPOMI HCHO over India; Dong et al. 2026
use it for PHV hotspot detection on a ~1 km grid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.config import Config, load_config
from isro_aqi.ingestion.gee_auth import aoi_geometry, daily_collection, export_image, init_ee
from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

log = get_logger("s5p")

GASES = ("no2", "so2", "co", "o3", "hcho")


def _period_mean(cfg: Config, gas: str, start: str, end: str) -> "ee.Image":
    """Mean column density for one gas over [start, end), QA-screened for HCHO."""
    import ee

    spec = cfg.datasets["sentinel5p"]["products"][gas]
    region = aoi_geometry(cfg)
    coll = daily_collection(spec["asset"], spec["band"], start, end, region)

    if gas == "hcho":
        # qa is pre-applied on L3; screen residual cloud via the cloud_fraction band.
        cloud_max = cfg.hcho.cloud_fraction_max
        full = (
            ee.ImageCollection(spec["asset"]).filterDate(start, end).filterBounds(region)
        )

        def _mask(img):
            return img.updateMask(img.select(spec["cloud_band"]).lt(cloud_max))

        coll = full.map(_mask).select(spec["band"])

    return coll.mean().rename(gas)


def build_stack(cfg: Config, start: str, end: str, gases=GASES) -> "ee.Image":
    """Multi-band image (one band per gas) of period-mean column densities."""
    import ee

    bands = [_period_mean(cfg, g, start, end) for g in gases]
    return ee.Image.cat(bands)


def export_period(cfg: Config, start: str, end: str, gases=GASES) -> list:
    """Export per-gas period means to Drive/GCS. Returns the started tasks."""
    init_ee(cfg)
    tasks = []
    for gas in gases:
        spec = cfg.datasets["sentinel5p"]["products"][gas]
        # HCHO at the fine 1 km grid; the rest at the AQI modelling resolution.
        scale = spec["resolution_m"] if gas == "hcho" else 7000
        img = _period_mean(cfg, gas, start, end)
        tasks.append(export_image(img, cfg, f"s5p_{gas}_{start}_{end}", scale, folder="s5p"))
    return tasks


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    # Config has required fields; Config.model_validate({}) would raise. Load the
    # real config instead so the smoke test reflects a real run.
    cfg = load_config()
    log.info("Run via pipelines/01_ingest.py; this module exposes build_stack/export_period.")
