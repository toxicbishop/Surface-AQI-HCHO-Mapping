#!/usr/bin/env python
"""Phase 2 -- real-data ingestion (graceful orchestrator).

Pulls every dataset for the configured AOI + time window, running each source it
CAN and cleanly skipping (with a reason) the ones whose dependency / credential /
input file is missing -- so the run never hard-crashes mid-way. Use
`python pipelines/check_ingest.py` first to see what's set up.

  GEE (async export to Drive/GCS): TROPOMI gases, ERA5 met, MODIS fire/EVI,
                                   + static land cover / DEM with --static
  CDS:    ERA5 boundary-layer height (needs cdsapi + ~/.cdsapirc)
  FIRMS:  VIIRS active fire CSV     (needs FIRMS_MAP_KEY env)
  Manual: INSAT-3D AOD (MOSDAC) and CPCB station CSVs -> data/external/

    python pipelines/01_ingest.py --config config/config.yaml \
        [--start 2021-10-01 --end 2021-12-31] [--static]

GEE exports are asynchronous: this starts the tasks and returns. Monitor them in
the Earth Engine Code Editor (Tasks tab) or via task.status(); the exported tiles
then download into data/raw for preprocessing (Phase 4).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

from isro_aqi.config import load_config
from isro_aqi.utils.logging import get_logger

log = get_logger("ingest")


def _gee_exports(cfg, start, end, static):
    """Start the GEE export tasks; skip gracefully if EE is unavailable."""
    try:
        from isro_aqi.ingestion import era5, modis_fire, sentinel5p, srtm, worldcover
        from isro_aqi.ingestion.gee_auth import init_ee
        init_ee(cfg)
    except Exception as e:
        log.warning(f"GEE unavailable ({type(e).__name__}: {e}). "
                    "Skipping TROPOMI/ERA5/MODIS/static exports. "
                    "Fix with: pip install earthengine-api && earthengine authenticate "
                    "(see python pipelines/check_ingest.py).")
        return []

    tasks = []
    tasks += sentinel5p.export_period(cfg, start, end)   # NO2, SO2, CO, O3, HCHO
    tasks += era5.export_period(cfg, start, end)          # meteorology
    tasks += modis_fire.export_period(cfg, start, end)    # FRP, burned area, EVI
    if static:
        tasks += worldcover.export(cfg)                   # land-cover fractions
        tasks += srtm.export(cfg)                         # elevation/slope/aspect
    log.info(f"{len(tasks)} GEE export tasks started -> monitor in the EE Code Editor (Tasks).")
    return tasks


def _era5_blh(cfg, start, end):
    """ERA5 boundary-layer height via Copernicus CDS (per year)."""
    if importlib.util.find_spec("cdsapi") is None or not (Path.home() / ".cdsapirc").exists():
        log.info("ERA5 BLH (CDS): skipped -- needs `pip install cdsapi` + ~/.cdsapirc.")
        return
    from isro_aqi.ingestion import era5
    raw = Path(cfg.paths.data_raw)
    raw.mkdir(parents=True, exist_ok=True)
    for year in range(int(start[:4]), int(end[:4]) + 1):
        out = raw / f"era5_blh_{year}.nc"
        try:
            era5.fetch_blh_cds(cfg, year, str(out))
            log.info(f"ERA5 BLH {year} -> {out}")
        except Exception as e:
            log.warning(f"ERA5 BLH {year} failed: {e}")


def _viirs_firms(cfg, start, end):
    """VIIRS active fire via NASA FIRMS API (falls back to GEE MODIS in preprocessing)."""
    key = os.environ.get("FIRMS_MAP_KEY")
    if not key:
        log.info("VIIRS FIRMS: skipped -- set FIRMS_MAP_KEY to enable (GEE MODIS fallback exists).")
        return
    if importlib.util.find_spec("requests") is None:
        log.info("VIIRS FIRMS: skipped -- `pip install requests`.")
        return
    from datetime import date

    from isro_aqi.ingestion import viirs_fire
    ext = Path(cfg.paths.data_external)
    ext.mkdir(parents=True, exist_ok=True)
    days = (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days + 1
    try:
        df = viirs_fire.fetch_firms_api(cfg, key, start, days=min(days, 10))  # FIRMS caps ~10 days/call
        out = ext / f"firms_viirs_{start[:10]}.csv"
        df.to_csv(out, index=False)
        log.info(f"VIIRS FIRMS: {len(df):,} fire pixels -> {out}")
    except Exception as e:
        log.warning(f"VIIRS FIRMS failed: {e}")


def _cpcb(cfg):
    """Parse manually-downloaded CPCB station CSVs from data/external into daily parquet."""
    ext = Path(cfg.paths.data_external)
    csvs = sorted(ext.glob("**/*.csv")) if ext.exists() else []
    csvs = [p for p in csvs if "firms" not in p.name.lower()]
    if not csvs:
        log.info("CPCB: no station CSVs in data/external -- download from "
                 "airquality.cpcb.gov.in/ccr (see docs/INGESTION_SETUP.md).")
        return
    log.info(f"CPCB: {len(csvs)} CSV(s) in data/external -- parse with "
             "cpcb.load_raw_hourly + cpcb.to_daily (formats vary; verify columns).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--static", action="store_true", help="also export static layers (DEM, land cover)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    start, end = args.start or cfg.time.start, args.end or cfg.time.end
    log.info(f"ingesting {start} .. {end} (AOI: {cfg.aoi.name})")

    _gee_exports(cfg, start, end, args.static)
    _era5_blh(cfg, start, end)
    _viirs_firms(cfg, start, end)
    _cpcb(cfg)

    log.info("Ingestion dispatched. Next: download finished GEE exports into data/raw, "
             "place INSAT AOD (MOSDAC) + CPCB CSVs in data/external, then `make preprocess`.")


if __name__ == "__main__":
    main()
