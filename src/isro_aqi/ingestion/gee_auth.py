"""Earth Engine authentication + shared helpers used by every GEE ingester.

One-time interactive auth:
    earthengine authenticate         # or: import ee; ee.Authenticate()

Headless / cron auth uses a service account (set gee.service_account + key_file
in config.yaml).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from isro_aqi.utils.logging import get_logger

if TYPE_CHECKING:
    import ee

    from isro_aqi.config import Config

log = get_logger("gee")
_INITIALISED = False


def init_ee(cfg: "Config") -> None:
    """Initialise Earth Engine once per process (interactive or service account)."""
    global _INITIALISED
    if _INITIALISED:
        return
    import ee

    if cfg.gee.service_account and cfg.gee.key_file:
        creds = ee.ServiceAccountCredentials(cfg.gee.service_account, cfg.gee.key_file)
        ee.Initialize(creds, project=cfg.gee.project)
        log.info(f"EE initialised (service account, project={cfg.gee.project})")
    else:
        ee.Initialize(project=cfg.gee.project)
        log.info(f"EE initialised (user creds, project={cfg.gee.project})")
    _INITIALISED = True


def aoi_geometry(cfg: "Config") -> "ee.Geometry":
    """Return the India AOI as an ee.Geometry (precise boundary if configured)."""
    import ee

    if cfg.aoi.boundary_asset and cfg.aoi.boundary_filter:
        f = cfg.aoi.boundary_filter
        fc = ee.FeatureCollection(cfg.aoi.boundary_asset).filter(
            ee.Filter.eq(f["property"], f["value"])
        )
        return fc.geometry()
    min_lon, min_lat, max_lon, max_lat = cfg.aoi.bbox
    return ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])


def export_image(
    image: "ee.Image",
    cfg: "Config",
    description: str,
    scale_m: int,
    folder: str = "isro_aqi",
) -> "ee.batch.Task":
    """Start an export of `image` clipped to the AOI.

    Exports to GCS if cfg.paths.gcs_bucket is set (matches the milestone-2-bucket
    workflow), otherwise to Google Drive. Returns the started Task so callers can
    poll task.status().
    """
    import ee

    region = aoi_geometry(cfg)
    common = dict(
        image=image.clip(region),
        description=description,
        region=region,
        scale=scale_m,
        crs=cfg.grid.crs,
        maxPixels=1e13,
    )
    if cfg.paths.gcs_bucket:
        bucket = cfg.paths.gcs_bucket.replace("gs://", "")
        task = ee.batch.Export.image.toCloudStorage(
            bucket=bucket, fileNamePrefix=f"{folder}/{description}", **common
        )
    else:
        task = ee.batch.Export.image.toDrive(folder=folder, fileNamePrefix=description, **common)
    task.start()
    log.info(f"export started: {description} @ {scale_m} m")
    return task


def daily_collection(
    asset: str, band: str, start: str, end: str, region: "ee.Geometry"
) -> "ee.ImageCollection":
    """Filtered single-band ImageCollection over the AOI/time window."""
    import ee

    return (
        ee.ImageCollection(asset)
        .select(band)
        .filterDate(start, end)
        .filterBounds(region)
    )
