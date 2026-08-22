#!/usr/bin/env python
"""Objective 2 -- HCHO hotspots (PHV + Gi*) + biomass-burning source attribution.

Two complementary detectors (problem statement: "statistical thresholds or
clustering"): PHV ratio anomalies and FDR-corrected Getis-Ord Gi*. Detected cells
are grouped into clusters via connected components and attributed to a source.

STATUS: SCAFFOLD. This numbered CLI documents the intended wiring but is NOT
implemented. The working HCHO detection/attribution runs in pipelines/run_demo.py
(synthetic) and pipelines/fetch_real_web.py (real TROPOMI). Use those.

    python pipelines/06_hcho_analysis.py --config config/config.yaml \
        [--method phv|gi] [--season post_monsoon]
"""

from __future__ import annotations

import argparse

from isro_aqi.config import load_config
from isro_aqi.hcho import getis_ord, phv, source_attribution
from isro_aqi.utils.logging import get_logger
from isro_aqi.viz.maps import hcho_map

log = get_logger("hcho")


def detect(method, hcho_da, cfg):
    if method == "gi":
        return getis_ord.gi_star(hcho_da, **cfg.hcho.getis_ord)
    return phv.detect_hotspots(hcho_da, cfg.hcho.phv_min, cfg.hcho.hva_threshold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--method", default="phv", choices=["phv", "gi"])
    ap.add_argument("--season", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)

    # hcho_da = read HCHO composite (data/interim) at cfg.grid.hcho_resolution_deg,
    #           qa-screened (qa_value > cfg.hcho.qa_threshold)
    # result = detect(args.method, hcho_da, cfg)               # PHV 'hva' or Gi* 'hotspot' mask
    # clusters = source_attribution.connected_clusters(result["hva"], hcho_da)
    # clusters = source_attribution.attribute(clusters, cfg.regions, season=args.season)
    # hcho_map(hcho_da, clusters, out_path=f"{cfg.paths.outputs_maps}/hcho_{args.method}.png")
    log.info(f"method={args.method} season={args.season}")
    log.info("SCAFFOLD ONLY — implemented in run_demo.py / fetch_real_web.py. "
             "Intended wiring: qa-screened HCHO -> detect(PHV/Gi*) -> connected_clusters -> attribute -> hcho_map")
    _ = (detect, source_attribution, hcho_map)


if __name__ == "__main__":
    main()
