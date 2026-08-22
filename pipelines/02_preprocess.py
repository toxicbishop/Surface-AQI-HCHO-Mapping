#!/usr/bin/env python
"""Phase 4 -- preprocessing: assemble -> QA -> gap-fill -> calibrate -> collocate.

Turns the downloaded exports (GeoTIFFs in data/raw, INSAT granules + CPCB CSVs in
data/external) into the co-registered 1 km stack and the station-collocated
training table. Applies the two redesign preprocessing changes:
    Change 1  AOD gap-fill (RF + clustered-holdout CV)
    Change 2  TROPOMI NO2 -> surface bias-correction

Each stage degrades gracefully: missing CPCB skips collocation/calibration (you
still get the predictor stack); missing rasterio/data exits with a clear message.

    python pipelines/02_preprocess.py --config config/config.yaml [--no-gapfill]

Outputs:
    data/interim/daily.nc                  co-registered predictor stack
    data/processed/collocated.parquet      predictors + CPCB targets (if CPCB present)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from isro_aqi.config import load_config
from isro_aqi.preprocessing import qa_filter
from isro_aqi.utils.io import ensure_dir, write_netcdf, write_parquet
from isro_aqi.utils.logging import get_logger

log = get_logger("preprocess")


def _load_cpcb(cfg):
    """Best-effort CPCB load -> (stations_df, daily_obs_df) or (None, None)."""
    ext = Path(cfg.paths.data_external)
    csvs = [p for p in ext.glob("**/*.csv") if "firms" not in p.name.lower()]
    if not csvs:
        log.info("CPCB: no station CSVs in data/external -- skipping collocation/calibration.")
        return None, None
    from isro_aqi.ingestion import cpcb
    try:
        meta = next((p for p in csvs if "station" in p.name.lower() or "meta" in p.name.lower()), None)
        stations = cpcb.load_station_metadata(str(meta)) if meta else None
        hourly = []
        for p in csvs:
            if p is meta:
                continue
            try:
                hourly.append(cpcb.load_raw_hourly(str(p)))
            except Exception as e:
                log.warning(f"CPCB parse skipped {p.name}: {e}")
        if not hourly:
            return stations, None
        import pandas as pd
        daily = cpcb.to_daily(pd.concat(hourly, ignore_index=True))
        log.info(f"CPCB: {len(daily):,} daily station rows")
        return stations, daily
    except Exception as e:
        log.warning(f"CPCB load failed ({e}); proceeding predictor-only. "
                    "Verify CSV layout vs ingestion/cpcb.py.")
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--no-gapfill", action="store_true", help="skip AOD gap-fill")
    args = ap.parse_args()
    cfg = load_config(args.config)

    # 1. assemble the gridded stack from downloaded rasters/granules ----------
    from isro_aqi.preprocessing.assemble import assemble_stack
    try:
        stack = assemble_stack(cfg)
    except Exception as e:
        log.error(f"Could not assemble stack: {type(e).__name__}: {e}")
        log.error("Have you run `make ingest`, downloaded the GEE exports into data/raw, "
                  "and `pip install rioxarray rasterio`? See docs/INGESTION_SETUP.md.")
        return
    log.info(f"assembled stack {dict(stack.sizes)} | {list(stack.data_vars)}")

    # 2. QA filter (physical ranges + sigma outliers) -------------------------
    stack = qa_filter.apply(stack)

    # 3. AOD gap-fill (Change 1) ----------------------------------------------
    if not args.no_gapfill and "aod" in stack.data_vars:
        from isro_aqi.preprocessing.gapfill_aod import fill_aod_stack
        stack, gf = fill_aod_stack(stack)
        log.info(f"AOD gap-fill: {gf['missing_frac']*100:.0f}% filled, cv_r2={gf.get('cv_r2')}")

    # 4. collocate with CPCB + NO2 calibration (Change 2) ---------------------
    stations, cpcb_daily = _load_cpcb(cfg)
    training = None
    if stations is not None and cpcb_daily is not None:
        from isro_aqi.preprocessing.calibrate_no2 import calibrate_no2_stack
        from isro_aqi.preprocessing.collocate import join_targets, sample_at_stations
        predictors = sample_at_stations(stack, stations)
        training = join_targets(predictors, cpcb_daily)
        if "no2" in stack.data_vars and "no2_obs" in training.columns:
            stack, no2 = calibrate_no2_stack(stack, training)
            log.info(f"NO2 calibration: surface r2={no2['r2']:.3f}")

    # 5. persist --------------------------------------------------------------
    ensure_dir(cfg.paths.data_interim)
    ensure_dir(cfg.paths.data_processed)
    write_netcdf(stack, f"{cfg.paths.data_interim}/daily.nc")
    log.info(f"-> {cfg.paths.data_interim}/daily.nc")
    if training is not None:
        write_parquet(training, f"{cfg.paths.data_processed}/collocated.parquet")
        log.info(f"-> {cfg.paths.data_processed}/collocated.parquet ({len(training):,} rows)")
    else:
        log.info("No CPCB targets -> predictor stack only (cannot train without ground truth).")


if __name__ == "__main__":
    main()
