from __future__ import annotations

import numpy as np
import pandas as pd

from isro_aqi.hcho.isolation_forest import compare_masks, detect_isolation_hotspots
from isro_aqi.models.zones import fit_pollution_zones


def test_kmeans_selects_and_orders_pollution_zones():
    rows = []
    for i, (aqi, hcho, no2, co) in enumerate(
        [(40, 0.10, 0.10, 0.10), (120, 0.30, 0.25, 0.20), (240, 0.60, 0.55, 0.45), (380, 0.90, 0.85, 0.80)]
    ):
        for j in range(8):
            rows.append({
                "lat": float(i), "lon": float(j), "aqi": aqi + j * 0.4,
                "hcho": hcho + j * 0.001, "no2": no2 + j * 0.001, "co": co + j * 0.001,
            })
    result, meta = fit_pollution_zones(pd.DataFrame(rows), k_range=(3, 4, 5), random_state=2)

    assert meta["selected_k"] in {3, 4, 5}
    assert set(meta["candidate_silhouette"]) == {"3", "4", "5"}
    assert result["zone_id"].notna().all()
    assert result["zone_label"].notna().all()
    means = result.groupby("zone_id")["aqi"].mean().to_numpy()
    assert np.all(np.diff(means) >= 0)


def test_isolation_forest_groups_adjacent_anomalies():
    rows = []
    for lat in range(8):
        for lon in range(8):
            anomaly = lat in {5, 6} and lon in {5, 6}
            rows.append({
                "lat": lat, "lon": lon,
                "hcho": 1.8 if anomaly else 0.2,
                "no2": 1.2 if anomaly else 0.2,
                "co": 1.0 if anomaly else 0.2,
            })
    result, meta = detect_isolation_hotspots(
        pd.DataFrame(rows), feature_cols=["hcho", "no2", "co"], contamination=0.08, random_state=1, n_estimators=100
    )

    assert meta["n_anomalies"] > 0
    assert meta["n_clusters"] >= 1
    assert result.loc[result["isolation_anomaly"], "isolation_cluster_id"].ge(0).all()
    assert result.loc[result["isolation_anomaly"], "isolation_cluster_size"].ge(1).all()


def test_mask_comparison_is_explicitly_diagnostic():
    reference = np.array([True, True, False, False])
    candidate = np.array([True, False, True, False])
    report = compare_masks(reference, candidate)

    assert report["overlap_cells"] == 1
    assert report["jaccard"] == 1 / 3
    assert report["interpretation"] == "agreement diagnostic, not supervised accuracy"
