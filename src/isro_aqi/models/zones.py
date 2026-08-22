"""Pollution-zone segmentation for gridded AQI and pollutant fields.

The zone layer is deliberately an exploratory complement to the official CPCB AQI
field.  K-Means is fitted on scaled, finite cells and the selected ``k`` is chosen
by the highest silhouette score over a small, auditable candidate range.  Cluster
IDs are reordered by mean AQI so that the labels remain stable and interpretable:
low-AQI zones are always assigned before high-AQI zones.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import silhouette_score


ZONE_LABELS = {
    2: ["Lower pollution", "Higher pollution"],
    3: ["Good", "Moderate", "Poor"],
    4: ["Good", "Moderate", "Poor", "Severe"],
    5: ["Good", "Moderate", "Poor", "Severe", "Hazardous"],
    6: ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"],
}


def _available_features(df: pd.DataFrame, feature_cols: Iterable[str] | None) -> list[str]:
    if feature_cols is not None:
        cols = [c for c in feature_cols if c in df.columns]
    else:
        # AQI is the severity axis; the gas columns retain pollution character.
        cols = [c for c in ("aqi", "hcho", "no2", "co", "doy_sin", "doy_cos") if c in df.columns]
    if not cols:
        raise ValueError("No usable columns were found for pollution-zone clustering")
    return cols


def _finite_frame(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    values = df[cols].apply(pd.to_numeric, errors="coerce")
    keep = np.isfinite(values.to_numpy(dtype=float)).all(axis=1)
    return df.loc[keep].copy(), values.loc[keep].to_numpy(dtype=float)


def _zone_labels(k: int) -> list[str]:
    if k in ZONE_LABELS:
        return ZONE_LABELS[k]
    return [f"Zone {i + 1}" for i in range(k)]


def fit_pollution_zones(
    df: pd.DataFrame,
    feature_cols: Iterable[str] | None = None,
    k_range: Iterable[int] = (3, 4, 5),
    random_state: int = 0,
    n_init: int = 20,
) -> tuple[pd.DataFrame, dict]:
    """Fit K-Means and return ``(labelled_cells, metadata)``.

    Parameters
    ----------
    df:
        One row per grid cell.  Coordinate columns are preserved but are not used
        unless explicitly included in ``feature_cols``.
    feature_cols:
        Defaults to AQI plus available HCHO/NO2/CO and seasonal encodings.
    k_range:
        Candidate cluster counts.  The best silhouette score wins.

    The returned frame contains ``zone_id`` (ordered from low to high mean AQI),
    ``zone_label``, and ``zone_score``.  Rows with missing clustering inputs are
    returned with null labels so map geometry is not silently discarded.
    """
    if df.empty:
        raise ValueError("Cannot cluster an empty grid")
    cols = _available_features(df, feature_cols)
    clean, raw = _finite_frame(df, cols)
    if len(clean) < 4:
        raise ValueError("At least four finite grid cells are required for K-Means")

    scaler = RobustScaler().fit(raw)
    X = scaler.transform(raw)
    candidates = sorted({int(k) for k in k_range if 2 <= int(k) < len(clean)})
    if not candidates:
        raise ValueError("No feasible K-Means value in k_range")

    scores: dict[str, float | None] = {}
    models: dict[int, KMeans] = {}
    for k in candidates:
        model = KMeans(n_clusters=k, n_init=n_init, random_state=random_state)
        labels = model.fit_predict(X)
        score = float(silhouette_score(X, labels)) if len(np.unique(labels)) > 1 else float("nan")
        scores[str(k)] = score if np.isfinite(score) else None
        models[k] = model

    def score_key(k: int) -> tuple[float, int]:
        score = scores[str(k)]
        return (float(score) if score is not None else -np.inf, -k)

    selected_k = max(candidates, key=score_key)
    model = models[selected_k]
    raw_labels = model.labels_

    # Reorder clusters by mean AQI when available; otherwise by scaled feature mean.
    order_col = "aqi" if "aqi" in clean else cols[0]
    means = clean.assign(_cluster=raw_labels).groupby("_cluster")[order_col].mean()
    ordered_clusters = list(means.sort_values().index)
    remap = {old: new for new, old in enumerate(ordered_clusters)}
    ordered_labels = np.array([remap[int(label)] for label in raw_labels], dtype=int)
    labels = _zone_labels(selected_k)

    result = df.copy()
    result["zone_id"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
    result["zone_label"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["zone_score"] = np.nan
    result.loc[clean.index, "zone_id"] = ordered_labels
    result.loc[clean.index, "zone_label"] = [labels[i] for i in ordered_labels]
    # A positive score means the cell is above the mean of the assigned cluster.
    cluster_mean = clean.assign(_zone=ordered_labels).groupby("_zone")[order_col].transform("mean")
    result.loc[clean.index, "zone_score"] = clean[order_col].to_numpy(dtype=float) - cluster_mean.to_numpy(dtype=float)

    centres_raw = scaler.inverse_transform(model.cluster_centers_)
    centres = []
    for old_id in ordered_clusters:
        new_id = remap[old_id]
        centres.append({
            "zone_id": new_id,
            "zone_label": labels[new_id],
            **{col: float(centres_raw[old_id, i]) for i, col in enumerate(cols)},
        })

    metadata = {
        "method": "KMeans",
        "selected_k": selected_k,
        "candidate_silhouette": scores,
        "feature_cols": cols,
        "n_cells": int(len(df)),
        "n_clustered_cells": int(len(clean)),
        "zone_labels": labels,
        "cluster_centres": centres,
        "zone_counts": {str(i): int((ordered_labels == i).sum()) for i in range(selected_k)},
    }
    return result, metadata
