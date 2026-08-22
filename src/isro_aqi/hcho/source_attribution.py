"""HCHO hotspot source attribution (Phase 10).

Classify each detected hotspot (cluster centroid) into one of:
    urban         -- near a major city centre (traffic / solvent VOCs)
    industrial    -- within an industrial corridor (point-source VOCs)
    agri_burning  -- crop-residue belt AND coincident fire activity, in season
    forest_fire   -- forest-fire region AND coincident fire activity, in season
    biogenic      -- high EVI, no fire (vegetation isoprene -> HCHO)
    other         -- none of the above

Decision logic combines the static region masks (config/regions.yaml), the
collocated MODIS/VIIRS fire signal (FRP / fire_count), land cover and EVI.
Grounding: Kuttippurath et al. 2022 attribute Apr-May HCHO over Punjab/Haryana/MP
/NE to biomass burning via fire+EVI; Dong et al. 2026 place HVAs in VOC-limited
urban/industrial zones.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from isro_aqi.utils.geo import haversine_km
from isro_aqi.utils.logging import get_logger

log = get_logger("attribution")


def connected_clusters(mask: xr.DataArray, value: xr.DataArray | None = None) -> pd.DataFrame:
    """Group adjacent hotspot cells into clusters via connected components.

    A dependency-light replacement for DBSCAN that stays in the "statistical
    threshold" family: take a boolean hotspot mask (from PHV HVA or Gi*), label
    spatially-connected blobs, and return one centroid row per blob with lon/lat,
    cell count and (optional) mean field value. Feeds source_attribution.attribute.
    """
    from scipy import ndimage

    m = np.asarray(mask.values, dtype=bool)
    labels, n = ndimage.label(m)
    lons, lats = mask["lon"].values, mask["lat"].values
    vals = None if value is None else np.asarray(value.values, dtype="float64")
    rows = []
    for k in range(1, n + 1):
        ys, xs = np.where(labels == k)
        rec = {"lon": float(lons[xs].mean()), "lat": float(lats[ys].mean()),
               "n_cells": int(len(xs))}
        if vals is not None:
            rec["hcho_value"] = float(np.nanmean(vals[ys, xs]))
        rows.append(rec)
    return pd.DataFrame(rows, columns=["lon", "lat", "n_cells"] + (["hcho_value"] if value is not None else []))


def _in_bbox(lon, lat, bbox) -> bool:
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def _near_city(lon, lat, urban_cfg) -> str | None:
    for name, spec in urban_cfg.items():
        clon, clat = spec["center"]
        if haversine_km(lon, lat, clon, clat) <= spec["radius_km"]:
            return name
    return None


def attribute(
    hotspots: pd.DataFrame,
    regions: dict,
    fire_col: str = "frp_mean",
    evi_col: str = "evi",
    fire_threshold: float = 1.0,
    evi_threshold: float = 0.4,
    season: str | None = None,
) -> pd.DataFrame:
    """Add a `source` (and `source_detail`) column to a hotspots table.

    hotspots must have at least lon/lat; fire_col/evi_col are used if present
    (join them from the collocated database first). `season` (IMD season name)
    gates the burning classes so a summer fire isn't attributed to winter paddy.

    PRECEDENCE (lowest -> highest; the LAST matching rule wins for a hotspot):
      1. urban         -- within a city radius
      2. industrial    -- within an industrial bbox
      3. agri_burning  -- crop bbox + fire (in season)
      4. forest_fire   -- forest bbox + fire (in season)
    So a fire-coincident crop/forest match overrides an urban/industrial label,
    and forest overrides crop where bboxes overlap. ``biogenic`` is assigned only
    when nothing above matched (src still ``other``), there is high EVI and no
    fire. Region specs without a ``bbox`` are skipped (guarded by ``.get``).
    """
    urban = regions.get("urban", {})
    industrial = regions.get("industrial", {})
    crop = regions.get("crop_burning", {})
    forest = regions.get("forest_fire", {})

    sources, details = [], []
    for _, r in hotspots.iterrows():
        lon, lat = float(r["lon"]), float(r["lat"])
        fire = float(r.get(fire_col, 0) or 0)
        evi = float(r.get(evi_col, 0) or 0)
        src, detail = "other", None

        # 1) urban (lowest precedence)
        city = _near_city(lon, lat, urban)
        if city:
            src, detail = "urban", city

        # 2) industrial (overrides urban)
        for name, spec in industrial.items():
            bbox = spec.get("bbox")
            if bbox is not None and _in_bbox(lon, lat, bbox):
                src, detail = "industrial", name

        # 3) agri_burning, then 4) forest_fire (both require coincident fire and
        #    override urban/industrial; forest is evaluated last so it wins ties)
        if fire >= fire_threshold:
            for name, spec in crop.items():
                bbox = spec.get("bbox")
                in_season = season is None or season in spec.get("seasons", [])
                if bbox is not None and _in_bbox(lon, lat, bbox) and in_season:
                    src, detail = "agri_burning", name
            for name, spec in forest.items():
                bbox = spec.get("bbox")
                in_season = season is None or season in spec.get("seasons", [])
                if bbox is not None and _in_bbox(lon, lat, bbox) and in_season:
                    src, detail = "forest_fire", name

        # biogenic only if nothing above matched
        if src == "other" and evi >= evi_threshold and fire < fire_threshold:
            src = "biogenic"

        sources.append(src)
        details.append(detail)

    out = hotspots.copy()
    out["source"] = sources
    out["source_detail"] = details
    log.info(f"attributed {len(out)} hotspots: {out['source'].value_counts().to_dict()}")
    return out
