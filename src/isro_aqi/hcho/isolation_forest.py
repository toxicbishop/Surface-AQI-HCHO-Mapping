"""Isolation Forest baseline for HCHO anomaly comparison.

The repository's primary HCHO detector remains PHV/Gi* because those methods are
spatially interpretable.  This module adds the plan's Isolation Forest as a
comparative, unsupervised anomaly detector.  It reports anomaly scores and groups
adjacent anomalous grid cells into regions so the result is map-ready rather than
a scattered list of pixels.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from scipy import ndimage
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


def _features(df: pd.DataFrame, feature_cols: Iterable[str] | None) -> list[str]:
    cols = list(feature_cols) if feature_cols is not None else [
        c for c in ("hcho", "no2", "co", "frp_mean", "doy_sin", "doy_cos") if c in df.columns
    ]
    cols = [c for c in cols if c in df.columns]
    if not cols:
        raise ValueError("No HCHO anomaly features are available")
    return cols


def _grid_labels(df: pd.DataFrame, anomaly: np.ndarray) -> tuple[np.ndarray, int]:
    """Return connected-component IDs for a lat/lon grid, using 8-neighbourhood."""
    if not {"lat", "lon"}.issubset(df.columns):
        return np.full(len(df), -1, dtype=int), 0
    lats = np.sort(pd.to_numeric(df["lat"], errors="coerce").dropna().unique())
    lons = np.sort(pd.to_numeric(df["lon"], errors="coerce").dropna().unique())
    if len(lats) == 0 or len(lons) == 0:
        return np.full(len(df), -1, dtype=int), 0
    lat_idx = {float(v): i for i, v in enumerate(lats)}
    lon_idx = {float(v): i for i, v in enumerate(lons)}
    mask = np.zeros((len(lats), len(lons)), dtype=bool)
    for row, flag in zip(df.itertuples(), anomaly, strict=False):
        if not flag:
            continue
        lat, lon = float(row.lat), float(row.lon)
        if lat in lat_idx and lon in lon_idx:
            mask[lat_idx[lat], lon_idx[lon]] = True
    labelled, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    ids = np.full(len(df), -1, dtype=int)
    for i, row in enumerate(df.itertuples()):
        if anomaly[i]:
            ids[i] = int(labelled[lat_idx[float(row.lat)], lon_idx[float(row.lon)]]) - 1
    return ids, int(count)


def detect_isolation_hotspots(
    df: pd.DataFrame,
    feature_cols: Iterable[str] | None = None,
    contamination: float = 0.05,
    random_state: int = 0,
    n_estimators: int = 300,
) -> tuple[pd.DataFrame, dict]:
    """Fit Isolation Forest and return labelled cells plus auditable metadata.

    Missing predictor values are median-imputed inside the model pipeline.  The
    coordinates are deliberately not model features unless explicitly requested,
    preventing the detector from learning that certain locations are unusual only
    because they are geographically distinct.
    """
    if df.empty:
        raise ValueError("Cannot detect anomalies on an empty grid")
    cols = _features(df, feature_cols)
    X = df[cols].apply(pd.to_numeric, errors="coerce")
    valid = X.notna().any(axis=1)
    if int(valid.sum()) < 10:
        raise ValueError("At least ten cells with anomaly inputs are required")

    model = make_pipeline(
        SimpleImputer(strategy="median"),
        RobustScaler(),
        IsolationForest(
            n_estimators=n_estimators,
            contamination=float(contamination),
            random_state=random_state,
            n_jobs=-1,
        ),
    )
    model.fit(X.loc[valid])
    decision = np.full(len(df), np.nan, dtype=float)
    pred = np.zeros(len(df), dtype=bool)
    # IsolationForest's decision_function is higher for normal points; invert it.
    decision[valid.to_numpy()] = -model.decision_function(X.loc[valid])
    pred[valid.to_numpy()] = model.predict(X.loc[valid]) == -1
    cluster_id, cluster_count = _grid_labels(df, pred)

    result = df.copy()
    result["isolation_score"] = decision
    result["isolation_anomaly"] = pred
    result["isolation_cluster_id"] = cluster_id
    result["isolation_cluster_size"] = 0
    counts = pd.Series(cluster_id[cluster_id >= 0]).value_counts().to_dict()
    for cluster, size in counts.items():
        result.loc[result["isolation_cluster_id"] == cluster, "isolation_cluster_size"] = int(size)

    metadata = {
        "method": "IsolationForest",
        "feature_cols": cols,
        "contamination": float(contamination),
        "n_estimators": int(n_estimators),
        "n_cells": int(len(df)),
        "n_valid_cells": int(valid.sum()),
        "n_anomalies": int(pred.sum()),
        "n_clusters": int(cluster_count),
        "cluster_sizes": {str(k): int(v) for k, v in counts.items()},
        "score_definition": "negative sklearn decision_function; larger means more anomalous",
    }
    return result, metadata


def compare_masks(reference: np.ndarray, candidate: np.ndarray) -> dict:
    """Compare two boolean hotspot masks without treating either as ground truth."""
    ref = np.asarray(reference, dtype=bool)
    cand = np.asarray(candidate, dtype=bool)
    if ref.shape != cand.shape:
        raise ValueError("Reference and candidate masks must have the same shape")
    intersection = int(np.logical_and(ref, cand).sum())
    ref_n, cand_n = int(ref.sum()), int(cand.sum())
    union = int(np.logical_or(ref, cand).sum())
    return {
        "reference_cells": ref_n,
        "candidate_cells": cand_n,
        "overlap_cells": intersection,
        "jaccard": float(intersection / union) if union else 1.0,
        "candidate_precision_against_reference": float(intersection / cand_n) if cand_n else None,
        "reference_recall_against_candidate": float(intersection / ref_n) if ref_n else None,
        "interpretation": "agreement diagnostic, not supervised accuracy",
    }
