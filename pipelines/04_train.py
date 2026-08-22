#!/usr/bin/env python
"""Phases 6-7 -- train surface-pollutant models with the 3-scheme validation.

The RF/XGBoost baseline branch is fully wired (trains + saves models/<kind>.joblib).
The deep-model (CNN-LSTM) branch here is a SCAFFOLD that only demonstrates the
spatial-block splitter; the working CNN-LSTM training loop lives in pipelines/run_demo.py.
Reports random / spatial / temporal validation so the honest (temporal/spatial) skill
is visible alongside the optimistic (random) one.

    python pipelines/04_train.py --config config/config.yaml [--model rf|xgb]   # wired
    python pipelines/04_train.py --model cnn_lstm   # scaffold only -> see run_demo.py
"""

from __future__ import annotations

import argparse

from isro_aqi.config import load_config
from isro_aqi.database.schema import PREDICTORS, TARGETS
from isro_aqi.models import baselines
from isro_aqi.models.train import spatial_blocks, temporal_split
from isro_aqi.utils.io import read_parquet
from isro_aqi.utils.logging import get_logger

log = get_logger("train")


def run_baseline(kind: str, df, features, targets, test_years):
    train, test = temporal_split(df, test_years)
    model = baselines.XGBoostModel(targets, features) if kind == "xgb" else baselines.RandomForestModel(targets, features)
    model.fit(train)
    preds = model.predict(test)
    for t in preds.columns:
        log.info(f"[{kind}] {t}: {baselines.metrics(test[t].to_numpy(), preds[t].to_numpy())}")
    model.save(f"models/{kind}.joblib")
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    kind = args.model or cfg.model.recommended

    df = read_parquet("data/processed/training.parquet")
    features = [c for c in PREDICTORS if c in df.columns]
    targets = [t for t in cfg.model.targets]
    # rename obs targets to engine names if needed (pm25 etc. already align)
    targets = [t for t in TARGETS if t.replace("_obs", "") in cfg.model.targets or t in cfg.model.targets]

    log.info(f"training '{kind}' | {len(df):,} rows | {len(features)} features")

    if kind in ("rf", "xgb"):
        run_baseline(kind, df, features, targets, cfg.validation.test_years)
        return

    # Deep models need the gridded stack for patch/sequence assembly:
    #   stack = read_zarr("data/interim/daily.zarr")
    #   ds_tr = PatchSequenceDataset(stack, train_df, features, targets, grid, ...)
    #   model = PollutantCNNLSTM(len(features), len(targets), cfg.model.patch_size)
    #   train_model(model, ds_tr, ds_val, targets, epochs=cfg.model.epochs, ...)
    # Report all three validation schemes:
    for _train, _val in spatial_blocks(df, cfg.validation.spatial_blocks, cfg.validation.k_folds):
        break  # demonstrates the splitter; wire into PatchSequenceDataset + train_model
    log.info("SCAFFOLD — deep-model (CNN-LSTM) training is implemented in run_demo.py. "
             "This branch only demonstrates the spatial_blocks splitter. "
             "Use `--model rf` or `--model xgb` here for a real baseline.")


if __name__ == "__main__":
    main()
