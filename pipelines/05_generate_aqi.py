#!/usr/bin/env python
"""Phases 5, 8, 9 -- estimate surface pollutants, compute AQI, render the atlas.

STATUS: SCAFFOLD. This numbered CLI documents the intended per-stage wiring but is
NOT implemented. The working end-to-end AQI generation lives in pipelines/run_demo.py
(synthetic) and pipelines/run_real.py (real CPCB/OpenAQ-validated). Use those.

Loads the trained model, predicts pollutant grids for each day, runs the CPCB AQI
engine cell-by-cell, and writes daily/monthly/seasonal/annual AQI maps.

    python pipelines/05_generate_aqi.py --config config/config.yaml [--date 2021-11-05]
"""

from __future__ import annotations

import argparse

from isro_aqi.aqi import AQIEngine
from isro_aqi.config import load_config
from isro_aqi.utils.io import ensure_dir
from isro_aqi.utils.logging import get_logger
from isro_aqi.viz.maps import aqi_map

log = get_logger("gen_aqi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--date")
    args = ap.parse_args()
    cfg = load_config(args.config)

    engine = AQIEngine(cfg.aqi_breakpoints)
    ensure_dir(cfg.paths.outputs_maps)
    ensure_dir(cfg.paths.outputs_atlas)

    # 1. predict pollutant grids:
    #    model = load(...); preds = model.predict(inference_grid_for(date))
    # 2. per-cell AQI:
    #    df = engine.compute_frame(preds)          -> aqi, aqi_dominant, aqi_category
    # 3. reshape to (lat, lon) DataArray and render:
    #    aqi_map(aqi_da, title=f"AQI {date}", out_path=f"{outputs_maps}/aqi_{date}.png")
    # 4. aggregate to monthly/seasonal/annual atlas pages.
    log.info("SCAFFOLD ONLY — implemented end-to-end in run_demo.py / run_real.py. "
             "Intended wiring: predict pollutants -> engine.compute_frame -> reshape -> aqi_map")
    _ = (engine, aqi_map)


if __name__ == "__main__":
    main()
