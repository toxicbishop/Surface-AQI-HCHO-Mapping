# Phase 6 — Surface-Pollutant Models (RF / XGBoost / CNN / CNN-LSTM + regression-kriging)

Models of increasing spatio-temporal capacity to predict surface PM2.5, PM10, NO₂, SO₂, CO and O₃ from satellite + meteorological + static predictors, benchmarked against [C]. **The operational predictor is the per-pollutant Random Forest** (optionally a regression-kriging hybrid, `models/hybrid.py`); the **CNN-LSTM is implemented and validated but not on the map-generation path**.

## Objectives
- Establish a tabular accuracy floor (RF, XGBoost); RF is the deployed predictor.
- Add spatial context (CNN) and spatial+temporal capacity (CNN-LSTM) as the deep learner.
- Beat [C]'s 10-fold CV skill while adding the meteorology [C] omitted [A].

## Scientific rationale
Surface pollution depends on **both** spatial behaviour (sources, terrain, upwind transport, urban gradients) **and** temporal behaviour (accumulation under a stable boundary layer, photochemistry) [A][B]. A tabular model sees neither neighbourhood nor history; a pure CNN ignores accumulation. The CNN-LSTM hybrid is therefore the deep learner: a shared CNN embeds each day's patch, and an LSTM integrates the sequence of embeddings — matching the physics where smog builds over multiple days across a spatial field. (A standalone LSTM was prototyped but removed in the redesign; the LSTM survives only as the inner recurrent cell of the CNN-LSTM.)

## Input datasets / inputs
Engineered tabular table (Phase 5) for Models 1–2; `(T, C, P, P)` patch sequences from `PatchSequenceDataset` for Models 3–5 (P=`patch_size`=15, T=`sequence_length`=7, C predictor channels). Targets: `[pm25, pm10, no2, so2, co, o3]`.

## Algorithm / workflow / architecture
- **Model 1 — Random Forest** (`RandomForestModel`, **operational**): 300 trees, one regressor per target (`_PerTargetModel`) for clean per-pollutant tuning.
- **Model 2 — XGBoost** (`XGBoostModel`): 600 trees, depth 8, lr 0.05, subsample/colsample 0.8, `tree_method="hist"`.
- **Model 3 — CNN** (`PollutantCNN`): per-patch spatial encoder.
  `Conv2d(C→32,3) BN ReLU → Conv2d(32→64,3) BN ReLU → MaxPool2d(2) → Conv2d(64→128,3) BN ReLU → AdaptiveAvgPool2d(1)` → `Flatten → Linear(128→64) ReLU Dropout(0.3) → Linear(64→n_targets)`. `.embed()` returns the **128-d** spatial vector.
- **Model 4 — CNN-LSTM** (`PollutantCNNLSTM`, the deep learner): shared `PollutantCNN.embed` over each of T frames → `(B, T, 128)` → 2-layer LSTM(128) → head → `(B, n_targets)` for the centre cell on day T. Validated but not on the map path.
- **Regression-kriging hybrid** (`HybridModel`): `C(s,t) = μ(RF trend) + v(kriged station residual)` — the deployed model in the demo (`hybrid.joblib`).

## Mathematical formulation
Convolution (per output channel k):
```
y_k(i,j) = Σ_c Σ_{u,v} W_{k,c,u,v} · x_c(i+u, j+v) + b_k
```
LSTM gates (inner cell of the CNN-LSTM):
```
f_t = σ(W_f[h_{t−1},x_t]+b_f)      i_t = σ(W_i[h_{t−1},x_t]+b_i)
o_t = σ(W_o[h_{t−1},x_t]+b_o)      g_t = tanh(W_g[h_{t−1},x_t]+b_g)
c_t = f_t⊙c_{t−1} + i_t⊙g_t        h_t = o_t⊙tanh(c_t)
```
CNN-LSTM forward: `e_t = CNN.embed(x_t)`, `h_T = LSTM(e_1..e_T)`, `ŷ = head(h_T)`.
Metrics:
```
R² = 1 − Σ(y−ŷ)²/Σ(y−ȳ)²
RMSE = sqrt( mean (y−ŷ)² )      MAE = mean |y−ŷ|
```

## Python libraries
`scikit-learn` (RF), `xgboost`, `torch`/`torch.nn` (CNN/CNN-LSTM), `joblib`, `numpy`, `pandas`, `xarray`.

## Code in this repo
- `src/isro_aqi/models/baselines.py` — `RandomForestModel`, `XGBoostModel`, `metrics`
- `src/isro_aqi/models/cnn.py` — `PollutantCNN` (`.embed()` 128-d)
- `src/isro_aqi/models/cnn_lstm.py` — `PollutantCNNLSTM` (deep learner, off map path)
- `src/isro_aqi/models/hybrid.py` — `HybridModel` (regression-kriging, deployed)
- `src/isro_aqi/models/dataset.py` — `PatchSequenceDataset`, `Standardizer`

```python
from isro_aqi.models.cnn_lstm import PollutantCNNLSTM
from isro_aqi.models.dataset import PatchSequenceDataset

ds = PatchSequenceDataset(stack, samples, channels, targets, grid,
                          patch_size=15, sequence_length=7)
model = PollutantCNNLSTM(in_channels=len(channels),
                         n_targets=len(targets))   # (B,7,C,15,15)->(B,6)
```

## Expected outputs
Trained model artefacts (`models/cnn_lstm.pt`, joblib baselines), per-pollutant prediction grids, and a benchmark table seeded with [C]'s CV skill as the **target to beat**:

| Pollutant | [C] R² | [C] RMSE | Ours R² | Ours RMSE |
|-----------|:-----:|:-------:|:------:|:--------:|
| PM2.5 | 0.92 | 6.25 | TBD | TBD |
| PM10  | 0.91 | 8.86 | TBD | TBD |
| O₃    | 0.79 | 19.18 | TBD | TBD |
| NO₂   | 0.83 | 8.29 | TBD | TBD |
| SO₂   | 0.43 | 1.86 | TBD | TBD |
| CO    | 0.55 | 0.22 | TBD | TBD |
| AQI   | 0.86 | 10.05 | TBD | TBD |

## Potential challenges & mitigations
- **SO₂/CO are hard** ([C] R²=0.43/0.55). Mitigation: emphasise met features [A], per-target tuning, log-targets.
- **Deep-model overfit on autocorrelated data.** Mitigation: BN/dropout, early stopping, spatial+temporal CV (Phase 7).
- **Class/footprint imbalance, NaN targets.** Mitigation: masked multi-target loss; `Standardizer` fit on train only.

## Validation metrics
Per-pollutant R²/RMSE/MAE under all three CV schemes (Phase 7); AIC/BIC for baseline selection [C].

## Publication-quality figures
- Predicted-vs-observed scatter per pollutant (with R²).
- Model-comparison bar chart (RF→CNN-LSTM) per pollutant.
- CNN feature-map / embedding visualisation; LSTM gate-activation timeline.
- National daily PM2.5/O₃ maps from the recommended model.
