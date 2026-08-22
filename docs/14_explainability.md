> ⚠️ **DEPRECATED IN REDESIGN — this module was removed; kept as design rationale only.**
> SHAP explainability (`explain/shap_analysis.py`) is **not implemented** in the current codebase.

# Phase 14 — Explainable AI (SHAP)

Model-agnostic driver attribution for the surface-AQI / HCHO predictors: *what actually drives PM2.5 and O₃ — AOD, temperature, BLH, wind, or fire?*

## Objectives
- Quantify global and local feature importance for the tree (RF/XGBoost) and deep (CNN-LSTM) models with **SHAP**.
- Generalise [A]'s KZ-filter + MLR driver attribution to a **model-agnostic** framework, and fix [C]'s limitation of **excluding meteorology**.
- Confirm physically-sensible drivers (radiation, temperature dominate O₃) and expose surprising ones for scrutiny.

## Scientific rationale
[A] attributes O₃ variability with a KZ-filter + multiple-linear-regression: KZ-decomposed correlations with O₃ of **Tem +88.4%, SSRD +75.6%, BLH +41.5%** — a strong physical prior our explanations should recover. KZ+MLR is, however, linear and method-specific. SHAP (Shapley additive explanations) is grounded in cooperative game theory and gives **globally-consistent, locally-faithful** attributions that work for any model, capturing nonlinearity and interactions the MLR misses. [C] explicitly **excluded meteorological drivers** — a limitation we correct by feeding ERA5 met (T, SSRD, BLH, wind) into the feature set and letting SHAP rank them, so met confounding of the HCHO–O₃ link (Phase 12) is made explicit rather than assumed away.

## Input datasets / inputs
- Fitted estimators: RF/XGBoost regressors (`models/baselines.py`) and the CNN-LSTM (`models/cnn_lstm.py`).
- Feature matrix `X` (tabular for trees; `(B, T, C, P, P)` tensors for the deep model): AOD, HCHO, NO₂, T, SSRD, BLH, U/V wind, fire FRP, EVI, terrain, temporal encodings.
- A background sample for the deep explainer.

## Algorithm / workflow
1. **Trees** → `explain_tree_model` runs exact `shap.TreeExplainer` on a sampled `X` (≤5000 rows).
2. `mean_abs_importance` → global ranking = mean(|SHAP|) per feature.
3. **Deep** → `explain_deep_model` runs `shap.GradientExplainer` against a background batch on a small sample.
4. Render beeswarm (distribution + sign), bar (global importance), and dependence plots.
5. Compare the SHAP ranking against [A]'s KZ correlations (T, SSRD, BLH) as a sanity check.

## Mathematical formulation
SHAP gives an **additive** local attribution: the prediction decomposes as the base value plus per-feature contributions φⱼ.

```
f(x) = φ₀ + Σⱼ φⱼ,      φ₀ = E[f(X)]   (base/expected value)
```

Each Shapley value is the average marginal contribution of feature j over all subsets S of the feature set F:

```
φⱼ = Σ_{S ⊆ F\{j}}  |S|!·(|F|−|S|−1)! / |F|!  · [ f(S ∪ {j}) − f(S) ]
```

Global importance used for the bar chart:

```
Iⱼ = (1/n) Σᵢ |φⱼ(xᵢ)|
```

For tree ensembles, TreeExplainer computes these exactly in polynomial time; for the CNN-LSTM, GradientExplainer approximates φ via expected gradients over the background distribution.

## Python libraries
`shap` (`TreeExplainer`, `GradientExplainer`), `numpy`, `pandas`, `scikit-learn`/`xgboost`, `torch` (deep model), `matplotlib`.

## Code in this repo
`src/isro_aqi/explain/shap_analysis.py` — `explain_tree_model`, `mean_abs_importance`, `explain_deep_model`. Plotted via `viz/figures.py:importance_bar`.

```python
def explain_tree_model(estimator, X, max_samples=5000):
    import shap
    Xs = X.sample(min(len(X), max_samples), random_state=42).fillna(0.0)
    explainer = shap.TreeExplainer(estimator)
    return explainer.shap_values(Xs), Xs

def mean_abs_importance(shap_values, feature_names):
    imp = np.abs(shap_values).mean(axis=0)
    return (pd.DataFrame({"feature": feature_names, "importance": imp})
            .sort_values("importance", ascending=False).reset_index(drop=True))
```

```python
sv, Xs = explain_tree_model(rf, X)
imp = mean_abs_importance(sv, list(Xs.columns))
figures.importance_bar(imp, out_path="outputs/figures/shap_importance.png")
```

## Expected outputs
- Global feature-importance table/bar (`outputs/tables/shap_importance.csv`, `outputs/figures/shap_importance.png`).
- Beeswarm summary and dependence plots (e.g. O₃ vs SSRD/T) recovering [A]'s met dominance.
- Per-pollutant rankings; HCHO-driver panel quantifying fire/EVI vs anthropogenic contributions.

## Potential challenges & mitigations
- **GradientExplainer cost on CNN-LSTM** → explain a subset against a small background batch.
- **Correlated features split importance** → report clustered/grouped SHAP; pair with dependence plots.
- **Causal misreading** → SHAP is associational; corroborate with [A]'s KZ physical priors and Phase-13 trajectories.
- **Background-set sensitivity** → fix `random_state`, document background size; sanity-check φ₀ ≈ E[f].

## Validation metrics
Additivity check (φ₀ + Σφⱼ ≈ f(x)); rank correlation (Spearman) of SHAP importance vs [A]'s KZ correlations for T/SSRD/BLH; stability of top-k features across seeds/folds; permutation-importance cross-check.

## Publication-quality figures
- `viz/figures.py:importance_bar` — global mean(|SHAP|) bar chart.
- SHAP beeswarm summary (sign + magnitude per sample).
- Dependence plots for the top met drivers (T, SSRD, BLH) alongside [A]'s reported percentages.
