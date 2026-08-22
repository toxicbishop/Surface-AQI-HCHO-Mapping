# Phase 5 — Feature Engineering

Derive physically-motivated predictors that encode chemistry, seasonality, persistence and column-to-surface scaling, turning the co-registered cube into informative inputs for tabular and deep models.

## Objectives
- Add chemistry-aware ratios (FNR = HCHO/NO₂) that flag the O₃-production regime.
- Encode seasonality without a Dec-31 discontinuity (cyclical day-of-year).
- Capture photochemical forcing and column-to-surface scaling via interactions (T×SSRD, AOD×BLH).
- Inject temporal memory (lags + rolling means) for accumulation / smog build-up.

## Scientific rationale
Meteorology dominates secondary-pollutant chemistry, the very driver [C] omitted. [A] shows solar radiation and temperature dominate surface O₃ (KZ-filtered seasonal correlations with O₃: **Tem +88.4%, SSRD +75.6%, SP −80.3%, BLH +41.5%, RH +28.3%, V10 +30.3%**), motivating `photo_index = T × SSRD`. [A] also establishes BLH as the control on column-to-surface representativeness (high BLH ⇒ well-mixed), motivating `aod_blh = AOD × BLH`. [B] reports a **+10 °C doubling of HCHO** and that **FNR = HCHO/NO₂ indicates the O₃ regime** — VOC-limited at low FNR, NOₓ-limited at high FNR. Multi-day persistence under a low, stable boundary layer produces smog accumulation, captured by lags and 3-day rolling means.

## Input datasets / inputs
The QC'd analysis cube / long table from Phase 4: AOD, NO₂, HCHO, SO₂, CO, O₃ columns; ERA5 `temperature`, `solar_radiation`, `blh`, `rh`, `pressure`, `v10`; static elevation/land cover; and the `date`, `lat`, `lon` keys.

## Algorithm / workflow / architecture
`add_engineered_features` applies the chain in order: `add_fnr` → `add_cyclical_doy` → `add_interactions` → (optional) `add_temporal_lags`. Tabular outputs feed RF/XGBoost; the CNN/LSTM/CNN-LSTM instead consume spatial patches and sequences assembled in `models/dataset.py`. Lags are computed **per cell** (`groupby(lat, lon)` on date-sorted data) to avoid bleeding values across locations.

## Mathematical formulation
Formaldehyde-to-NO₂ ratio (regime flag; thresholds 2.67 / 3.47 [B]):
```
FNR = HCHO / (NO2 + ε),   ε = 1e-30
regime = VOC-limited if FNR < 2.67 ;  NOx-limited if FNR > 3.47
```
Cyclical day-of-year (no discontinuity):
```
doy_sin = sin(2π·DOY/365.25),   doy_cos = cos(2π·DOY/365.25)
```
Photochemical / dilution interactions:
```
photo_index = T × SSRD          # photochemistry proxy (O3, HCHO)  [A][B]
aod_blh      = AOD × BLH         # column-to-surface scaling        [A]
```
Per-cell temporal memory:
```
x_lagk(c,d) = x(c, d−k),  k∈{1,2,3}
x_roll3(c,d) = mean( x(c,d−2 : d) )
```

## Python libraries
`pandas`, `numpy` (tabular features); `xarray` upstream; features later standardized by the model `Standardizer` (z-score, train-only stats).

## Code in this repo
- `src/isro_aqi/features/engineering.py` — `add_fnr`, `add_cyclical_doy`, `add_interactions`, `add_temporal_lags`, `add_engineered_features`

```python
from isro_aqi.features.engineering import add_engineered_features

df = add_engineered_features(
    df, lag_cols=["aod", "no2", "blh", "temperature"]
)
# new columns: fnr, doy_sin, doy_cos, aod_blh, photo_index,
#              *_lag1..3, *_roll3
```

`add_fnr` only fires when both `hcho` and `no2` exist; `add_interactions` adds `aod_blh` when `{aod, blh}` present and `photo_index` when `{temperature, solar_radiation}` present — features degrade gracefully on partial inputs.

## Expected outputs
An augmented training table with derived columns appended, ready for RF/XGBoost; the same physical features (FNR, photo_index, aod_blh) are also available as CNN/LSTM channels. FNR additionally feeds the HCHO ozone-regime mapping (Phase on hotspots).

## Potential challenges & mitigations
- **NO₂→0 inflating FNR.** Mitigation: ε floor; clip FNR to a sane range before use.
- **Leakage from temporal lags across stations/years.** Mitigation: `groupby(lat, lon)` + date-sort; lags created **before** the temporal split.
- **Collinearity (T, SSRD, photo_index).** Mitigation: tree models are robust; for linear baselines use AIC/BIC selection [C].
- **NaNs from early-record lags.** Mitigation: `rolling(min_periods=1)`; trees `fillna(0)`.

## Validation metrics
RF feature-importance ranking (expect T, SSRD, BLH, AOD high for O₃/PM); ablation ΔR² with vs without engineered features; correlation of `photo_index` and `aod_blh` with target residuals. _(SHAP explainability was prototyped but removed in the redesign.)_

## Publication-quality figures
- RF feature-importance bar per pollutant.
- FNR feature map (HCHO/NO₂, VOC- vs NOₓ-limited proxy) over India.
- Lag/rolling autocorrelation of PM2.5 during a stubble-burning episode.
- Partial-dependence of O₃ on `photo_index` and BLH.
