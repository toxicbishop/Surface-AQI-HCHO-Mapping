#!/usr/bin/env python
"""Objective 2 (transport) -- fire->HCHO transport via ERA5 back-trajectories.

Quantifies whether upwind biomass-burning feeds a receptor city's HCHO: trace the
air parcel back along ERA5 winds and count VIIRS fire pixels within a radius of the
path. Directional, mechanistic evidence (not just co-located correlation).

STATUS: SCAFFOLD. This numbered CLI documents the intended wiring but is NOT
implemented. The working back-trajectory + fire-along-path analysis runs in
pipelines/run_demo.py (synthetic) and pipelines/fetch_real_web.py (real ERA5). Use those.

    python pipelines/07_transport.py --config config/config.yaml \
        [--receptor delhi] [--date 2021-11-05]
"""

from __future__ import annotations

import argparse

from isro_aqi.config import load_config
from isro_aqi.hcho import transport
from isro_aqi.utils.logging import get_logger

log = get_logger("transport")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--receptor", default="delhi")
    ap.add_argument("--date")
    args = ap.parse_args()
    cfg = load_config(args.config)

    # receptor = cfg.regions["receptors"][args.receptor]
    # winds = read_zarr("data/interim/daily.zarr")[["u_wind","v_wind"]]
    # path = transport.back_trajectory(winds, receptor[0], receptor[1], args.date, hours=48)
    # fires = ...  # VIIRS pixels for the window
    # n = transport.fires_along_path(path, fires)  # did upwind fires feed this receptor?
    log.info(f"receptor={args.receptor} date={args.date}")
    log.info("SCAFFOLD ONLY — implemented in run_demo.py / fetch_real_web.py. "
             "Intended wiring: back_trajectory + fires_along_path (upwind fire -> receptor HCHO)")
    _ = transport


if __name__ == "__main__":
    main()
