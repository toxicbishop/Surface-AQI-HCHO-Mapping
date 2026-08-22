#!/usr/bin/env python
"""Phase 3 -- assemble the unified India-wide database.

Turns the collocated predictors+targets (from Phase 4) into the supervised
training table, with engineered features (FNR, cyclical time, lags). Optionally
flattens the daily stack into the large year/month-partitioned inference grid.

    python pipelines/03_build_database.py --config config/config.yaml [--inference]

Outputs:
    data/processed/training.parquet        supervised table (partitioned year/month)
    data/processed/inference/  (--inference) every-cell predictor grid for mapping
"""

from __future__ import annotations

import argparse
from pathlib import Path

from isro_aqi.config import load_config
from isro_aqi.database import build_db
from isro_aqi.features import add_engineered_features
from isro_aqi.utils.io import read_parquet
from isro_aqi.utils.logging import get_logger

log = get_logger("build_db")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--inference", action="store_true", help="also build the full inference grid")
    args = ap.parse_args()
    cfg = load_config(args.config)

    collocated_path = Path(cfg.paths.data_processed) / "collocated.parquet"
    if not collocated_path.exists():
        log.error(f"{collocated_path} not found -- run `make preprocess` first "
                  "(needs downloaded data + CPCB CSVs).")
        return

    collocated = read_parquet(collocated_path)
    collocated = add_engineered_features(collocated, lag_cols=["aod", "no2", "hcho", "temperature"])
    build_db.build_training_table(collocated, f"{cfg.paths.data_processed}/training.parquet")
    log.info(f"-> {cfg.paths.data_processed}/training.parquet")

    if args.inference:
        daily_path = Path(cfg.paths.data_interim) / "daily.nc"
        if daily_path.exists():
            from isro_aqi.utils.io import read_netcdf
            daily = add_engineered_features(
                read_netcdf(daily_path).to_dataframe().reset_index().rename(columns={"time": "date"})
            )
            # write the flattened, engineered inference table
            build_db.build_training_table(daily, f"{cfg.paths.data_processed}/inference.parquet")
            log.info(f"-> {cfg.paths.data_processed}/inference.parquet")
        else:
            log.warning(f"{daily_path} not found -- skip inference grid.")


if __name__ == "__main__":
    main()
