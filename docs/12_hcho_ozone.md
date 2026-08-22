> ⚠️ **DEPRECATED IN REDESIGN — this module was removed; kept as design rationale only.**
> The HCHO–O₃ / FNR-regime classifier (`hcho/ozone_relationship.py`) is **not implemented**.
> FNR survives only as a feature column (`fnr = hcho/(no2+ε)`) in `features/engineering.py`.

# Phase 12 — HCHO–Ozone Relationship

Quantify how satellite HCHO columns track surface ozone and its VOC/NOx production regime over India, stratified by season.

## Objectives
- Measure the HCHO–O₃ association (strength, sign, significance) per region and season.
- Establish HCHO as a **precursor** (leading O₃) via lagged cross-correlation, not mere co-occurrence.
- Map the **ozone-production regime** (VOC-limited / transition / NOx-limited) from the FNR = HCHO/NO₂ column ratio, locating where VOC/HCHO control is the effective lever for O₃ abatement.

## Scientific rationale
HCHO is a high-yield intermediate of VOC oxidation and an excellent proxy for VOC reactivity: [A] reports R(HCHO,VOC)=0.73 annual and 0.77 in the ozone season. Its very short daytime half-life (~50 min, ~35 min in the presence of NO₂ [A]) makes the column a near-instantaneous emission/oxidation tracer rather than a transported burden. Crucially, R(HCHO,O₃) jumps from 0.43 annual to **0.89 during the ozone season (Apr–Sep) [A]** — photochemistry is seasonally gated, so we **always stratify by season**. The FNR ratio diagnoses which precursor limits O₃ formation: where FNR is low (VOC-limited), cutting NOx is counter-productive and VOC/HCHO control wins. [A] places HCHO Very-High-Areas (HVAs) inside VOC-limited urban/industrial zones, identifying the policy target.

## Input datasets / inputs
- **Sentinel-5P TROPOMI** HCHO and NO₂ tropospheric vertical columns (QA-filtered, regridded; Phase 04).
- **CPCB / reanalysis surface O₃** (`o3_obs`) collocated to satellite footprints.
- Season label (`season`, IMD seasons) from the temporal preprocessor.
- A tidy `data/processed/training.parquet` with columns `hcho`, `no2`, `o3_obs`, `season`, lon/lat.

## Algorithm / workflow
1. Load collocated table; drop QA-failed rows.
2. `correlation` / `correlation_by_season` → Pearson & Spearman r per season and region.
3. `cross_correlation` per receptor time series → lag (days) of peak r ⇒ precursor lead time.
4. `fnr_regime` → append `fnr` and `o3_regime`; aggregate regime fractions per region/season.
5. Cross-reference HVA hotspots (Phase 10) against the regime map to flag VOC-limited HVAs.

## Mathematical formulation
Pearson correlation:

```
r = Σ(xᵢ − x̄)(yᵢ − ȳ) / sqrt( Σ(xᵢ − x̄)² · Σ(yᵢ − ȳ)² )
```

Cross-correlation at lag k (HCHO leading O₃ by k days), computed on mean-centred series:

```
r(k) = Σ HCHO'(t)·O₃'(t+k) / sqrt( Σ HCHO'² · Σ O₃'² ),   k = 0…7
k* = argmaxₖ r(k)   (apparent precursor lead time)
```

Formaldehyde-to-NO₂ ratio and regime classification:

```
FNR = HCHO_column / NO₂_column
FNR < 2.67            → VOC-limited
2.67 ≤ FNR ≤ 3.47     → transition
FNR > 3.47            → NOx-limited        (alt single threshold ≈ 3.06)  [A]
```

The canonical India rule [B] (Duncan 2010; Jin & Holloway 2015) is offered as a configurable alternative: <1 VOC-sensitive, 1–2 mixed, >2 NOx-limited.

## Python libraries
`numpy`, `pandas`, `scipy.stats` (`pearsonr`, `spearmanr`), `matplotlib`, `statsmodels` (optional CCF), `geopandas` (regime maps).

## Code in this repo
`src/isro_aqi/hcho/ozone_relationship.py` — `correlation`, `correlation_by_season`, `cross_correlation`, `fnr_regime`. Wired in `pipelines/07_transport.py`.

```python
def fnr_regime(df, hcho="hcho", no2="no2",
               voc_limited_max=2.67, nox_limited_min=3.47):
    out = df.copy()
    out["fnr"] = out[hcho] / (out[no2] + 1e-30)
    out["o3_regime"] = pd.cut(out["fnr"],
        bins=[-np.inf, voc_limited_max, nox_limited_min, np.inf],
        labels=["VOC-limited", "transition", "NOx-limited"])
    return out
```

```python
by_season = ozone_relationship.correlation_by_season(df, hcho="hcho", o3="o3_obs")
ccf = ozone_relationship.cross_correlation(df_delhi["hcho"], df_delhi["o3_obs"], max_lag=7)
```

## Expected outputs
- Per-season/region correlation table (`outputs/tables/hcho_o3_corr.csv`) reproducing the annual≈0.4 → season≈0.9 contrast [A].
- Cross-correlation curves with k* (typically 0–1 day for a ~1-h-lifetime precursor).
- Regime fraction maps and a list of VOC-limited HVAs (control targets).

## Potential challenges & mitigations
- **TROPOMI HCHO noise/low SNR** → seasonal/spatial averaging, oversampling, QA≥0.5.
- **Spurious correlation via shared meteorology (T, radiation)** → partial correlation / control in the Phase-14 SHAP model; report seasonal stratification.
- **Column vs surface mismatch** → restrict to well-mixed midday overpass; note BLH dependence.
- **FNR threshold transferability** → expose thresholds as config; report both [A] and [B] rules.

## Validation metrics
Pearson/Spearman r with p-values and n; bootstrap CIs on r; regime-map agreement vs published India FNR maps [A][B]; sign and magnitude of k* (HCHO should lead, not lag).

## Publication-quality figures
- `viz/figures.py:hcho_o3_panel` — HCHO vs O₃ scatter coloured by season (the headline seasonality figure).
- Cross-correlation stem plot (r vs lag) per receptor.
- Choropleth of `o3_regime` fractions with HVA overlay.
