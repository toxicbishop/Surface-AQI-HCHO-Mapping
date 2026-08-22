# Phase 7 — Training & Validation Framework

Train the surface-pollutant models with a masked multi-target loss and evaluate them under three complementary cross-validation schemes — random, spatial, and temporal — to obtain honest, leakage-free skill estimates.

## Objectives
- Train deep models with Adam + early stopping + LR scheduling and a leakage-free standardizer.
- Handle multi-target labels where stations report only some pollutants (masked MSE).
- Report **three** CV schemes separately and per-pollutant R²/RMSE/MAE.

## Scientific rationale
[C] makes the decisive observation that **temporal CV ≫ spatial CV**: for PM2.5 the temporal-CV R²=0.93 but the spatial-CV R²=0.49. A single random k-fold number is therefore **optimistic** — spatial and temporal autocorrelation leak across the random split, so neighbouring cells / adjacent days inflate the score. Honest deployment skill is bounded by (a) prediction at **unseen locations** (spatial) and (b) prediction in **unseen time / held-out years** (temporal). We follow [C] and report all three; the temporal split over held-out years is the operationally honest metric for daily AQI mapping.

## Input datasets / inputs
The Phase-5 engineered table (baselines) and `PatchSequenceDataset` tensors (deep models). Config: `epochs=100`, `batch_size=256`, `lr=1e-3`, `early_stopping_patience=12`, `validation.scheme=[random_kfold, spatial_kfold, temporal_split]`, `k_folds=10`, `spatial_blocks=0.5°`, `test_years=[2023]`.

## Algorithm / workflow / architecture
1. **Split** before any fitting. `temporal_split` holds out `test_years`; `spatial_blocks` assigns each row a 0.5° block and partitions **whole blocks** into k folds (no block split across train/val); random k-fold is the optimistic reference.
2. **Standardize** with `Standardizer` fit on the **train split only** (no leakage).
3. **Train** (`train_model`): Adam, `ReduceLROnPlateau(patience=4, factor=0.5)`, masked-MSE; checkpoint best val to `models/cnn_lstm.pt`; **early stop** after `patience=12` stale epochs.
4. **Evaluate** per-target with `evaluate_metrics`. Device auto-selected (`select_device`: cuda→mps→cpu).

## Mathematical formulation
z-score standardization (train-only stats):
```
z = (x − μ_train) / σ_train ,   σ=1 where σ_train=0
```
Masked multi-target MSE (NaN targets contribute no gradient):
```
mask = ¬isnan(y)
L = mean_{mask} (ŷ − y)²        (0 if mask empty)
```
Spatial blocking (0.5°): `block = (⌊lon/0.5⌋, ⌊lat/0.5⌋)`, folds over unique blocks.
Temporal split: `test = {rows : year ∈ test_years}`.
Per-target metrics: R²/RMSE/MAE as in Phase 6.

## Python libraries
`torch` (`DataLoader`, `Adam`, `ReduceLROnPlateau`), `numpy`, `pandas`, `scikit-learn` metrics; `xgboost`/`sklearn` for baselines.

## Code in this repo
- `src/isro_aqi/models/train.py` — `train_model`, `masked_mse`, `temporal_split`, `spatial_blocks`, `evaluate_metrics`, `select_device`, `_evaluate_loss`
- `src/isro_aqi/models/baselines.py` — `metrics` (R²/RMSE/MAE)
- `pipelines/04_train.py` — end-to-end driver

```python
from isro_aqi.models.train import (
    train_model, spatial_blocks, temporal_split)

train_df, test_df = temporal_split(df, test_years=[2023])   # honest split
for tr, val in spatial_blocks(train_df, block_deg=0.5, k=10):
    best = train_model(model, make_ds(tr), make_ds(val),
                       targets, epochs=100, patience=12)     # per-target R2/RMSE/MAE
```

`masked_mse` masks NaN targets so a station reporting only PM2.5/PM10 still trains those heads without corrupting SO₂/CO/O₃.

## Expected outputs
- Best checkpoint(s) + fold logs (`epoch | train | val`).
- A results matrix: rows = pollutants, columns = {random, spatial, temporal} × {R², RMSE, MAE}, with the expected pattern random ≥ temporal ≥ spatial per [C].
- Per-pollutant skill compared against the [C] benchmark (Phase 6 table).

## Potential challenges & mitigations
- **Optimistic random CV.** Mitigation: always co-report spatial + temporal; headline the temporal number [C].
- **Standardizer leakage.** Mitigation: `Standardizer.fit` on train split only.
- **Unstable val loss → premature stop.** Mitigation: `ReduceLROnPlateau` before early stop; `min_delta=1e-5`.
- **Sparse-pollutant heads (SO₂/CO).** Mitigation: masked loss; per-target weighting; more met features [A].
- **MPS/CUDA numerics.** Mitigation: `select_device` fallback; fixed `random_seed=42`.

## Validation metrics
Per-pollutant R²/RMSE/MAE under each of the three schemes; 10-fold aggregation (mean ± sd); AIC/BIC for baseline model selection [C]; the random–spatial–temporal gap reported as a generalisation diagnostic.

## Publication-quality figures
- Grouped bar chart: R² per pollutant across random / spatial / temporal schemes (visualising the [C] gap).
- Training/validation loss curves with early-stop marker.
- Spatial-fold map (0.5° blocks colour-coded by fold).
- Residual maps for the held-out year (2023) per pollutant.
