"""Build JSON-ready K-Means and Isolation Forest analysis layers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

import numpy as np
import pandas as pd

from isro_aqi.hcho.isolation_forest import compare_masks, detect_isolation_hotspots
from isro_aqi.models.zones import fit_pollution_zones


def _number(value):
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return value if np.isfinite(value) else None


def _date_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def build_analysis_layers(
    df: pd.DataFrame,
    *,
    date_value=None,
    phv_mask: Iterable[bool] | None = None,
    zone_features: Iterable[str] | None = None,
    isolation_features: Iterable[str] | None = None,
    k_range: Iterable[int] = (3, 4, 5),
    contamination: float = 0.05,
) -> dict:
    """Fit both comparative analyses and return JSON-ready payloads.

    ``df`` must contain one row per grid cell and ``lon``/``lat`` columns.  The
    official AQI value should be supplied as ``aqi`` when available.  A PHV mask
    can be passed only as a diagnostic reference; it is never treated as truth.
    """
    if not {"lon", "lat"}.issubset(df.columns):
        raise ValueError("Analysis layers require lon and lat columns")

    zones, zone_meta = fit_pollution_zones(df, feature_cols=zone_features, k_range=k_range)
    iso, iso_meta = detect_isolation_hotspots(
        df, feature_cols=isolation_features, contamination=contamination
    )

    if phv_mask is not None:
        phv = np.asarray(list(phv_mask), dtype=bool)
        if len(phv) == len(iso):
            iso_meta["phv_comparison"] = compare_masks(phv, iso["isolation_anomaly"].to_numpy())

    zone_fields = [c for c in ("aqi", "rapi", "hcho", "no2", "co") if c in zones.columns]
    zone_cells = []
    for row in zones.itertuples(index=False):
        zone_id = getattr(row, "zone_id", None)
        if pd.isna(zone_id):
            continue
        item = {
            "lon": round(float(row.lon), 3),
            "lat": round(float(row.lat), 3),
            "zone_id": int(zone_id),
            "zone_label": str(row.zone_label),
            "zone_score": _number(getattr(row, "zone_score", None)),
        }
        for field in zone_fields:
            item[field] = _number(getattr(row, field))
        zone_cells.append(item)

    iso_fields = [c for c in ("hcho", "no2", "co", "frp_mean") if c in iso.columns]
    isolation_cells = []
    for row in iso.loc[iso["isolation_anomaly"]].itertuples(index=False):
        item = {
            "lon": round(float(row.lon), 3),
            "lat": round(float(row.lat), 3),
            "isolation_score": _number(row.isolation_score),
            "cluster_id": int(row.isolation_cluster_id),
            "cluster_size": int(row.isolation_cluster_size),
        }
        for field in iso_fields:
            item[field] = _number(getattr(row, field))
        isolation_cells.append(item)

    metadata = {
        "data_status": "synthetic_demo",
        "date": _date_text(date_value),
        "zone": zone_meta,
        "isolation_forest": iso_meta,
        "scientific_note": (
            "K-Means zones are exploratory relative segments. Isolation Forest is an "
            "unsupervised anomaly baseline; PHV/Gi* and source attribution remain the "
            "primary interpretable HCHO evidence."
        ),
    }
    return {
        "zone_cells": {**{k: zone_meta[k] for k in ("method", "selected_k", "candidate_silhouette", "feature_cols", "zone_labels")}, "cells": zone_cells},
        "isolation_hotspots": {**{k: iso_meta[k] for k in ("method", "contamination", "feature_cols", "n_anomalies", "n_clusters", "score_definition")}, "cells": isolation_cells},
        "analysis_metadata": metadata,
    }
