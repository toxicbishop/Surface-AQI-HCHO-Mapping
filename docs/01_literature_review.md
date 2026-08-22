# Phase 1 — Literature Review

State-of-the-art on satellite-derived surface AQI and HCHO hotspot/source attribution, framing the gap this project fills over India.

## Objectives
- Survey AQI aggregation methodology (CPCB 2014 vs US EPA NowCast) and its statistical limitations.
- Review satellite-to-surface inversion of criteria pollutants (AOD→PM2.5; column→surface for NO₂/SO₂/CO/O₃).
- Synthesise HCHO chemistry — VOC proxy, O₃-sensitivity (FNR), biomass-burning attribution — over India.
- Position the headline novelty: a unified India-wide AQI map **plus** HCHO hotspot detection **plus** biomass-burning + long-range-transport attribution with explainable deep learning.

## Scientific rationale
Ground monitoring (CPCB) is spatially sparse (~hundreds of stations for 3.3 M km²), so vast rural and peri-urban India is unobserved. Satellites give wall-to-wall coverage but measure *columns/optical properties*, not breathable surface concentrations; bridging that gap statistically is the core scientific problem [C]. HCHO is a short-lived VOC oxidation product and a robust tracer of VOC emissions and pyrogenic activity, making TROPOMI HCHO a powerful, independent lens on biomass burning and ozone-formation regimes [A][B].

## Input datasets
This is a literature phase; the datasets reviewed are the same operational sources later ingested (Phase 2): TROPOMI L3 (NO₂/SO₂/CO/O₃/HCHO), INSAT-3D AOD / MAIAC, ERA5-Land + CDS BLH, MODIS/VIIRS fire, ESA WorldCover, SRTM, and CPCB station records.

## Algorithm / workflow
The reviewed literature decomposes into four threads mapped onto our pipeline:

1. **AQI methodology — CPCB vs EPA.** CPCB 2014 defines 6 categories spanning index 0–500 with piecewise-linear sub-indices; the overall AQI is the **maximum** sub-index across pollutants [C][D]. US EPA uses the same max-aggregation but a NowCast weighted average for real-time reporting. Lu et al. [D] critique max-only aggregation (it discards information from co-pollutants and is discontinuous) and propose a **Shannon-entropy** weighted Revised API (RAPI). We adopt CPCB breakpoints for compliance but report RAPI as a research cross-check.
2. **Satellite AQI studies.** Wang et al. [C] is the methodological anchor: a high-resolution spatiotemporal model fusing satellite columns, reanalysis meteorology and 208 geographic covariates to map all criteria pollutants and AQI.
3. **AOD→PM2.5 (statistical / ML / DL).** Approaches span simple AOD–PM regressions, mixed-effects and geostatistical kriging, tree ensembles, and CNN/LSTM spatiotemporal nets. [C] gap-fills MAIAC AOD (1 km) and NO₂ with random forests (AOD R²=0.96), then applies **universal kriging + PLS** over the covariate stack. Reported 10-fold CV (R²/RMSE): PM2.5 **0.92 / 6.25**, PM10 0.91 / 8.86, O₃ 0.79 / 19.18, NO₂ 0.83 / 8.29, SO₂ 0.43 / 1.86, CO 0.55 / 0.22, AQI **0.86 / 10.05** — establishing realistic skill ceilings and highlighting SO₂/CO as the hardest targets.
4. **HCHO chemistry & sources.** Kuttippurath et al. [B] map India: persistent hotspots over the Indo-Gangetic Plain, east/south India and seaports (**8–12×10¹⁵ molec/cm²**) vs clean Kashmir/NE (**1–2×10¹⁵**); strong temperature sensitivity (**+10 °C ≈ doubling of HCHO**); and **biomass burning >70%** of HCHO emissions (2014). Dong et al. [A] contribute the **Percentile / High-Value-Area (PHV/HVA)** detection method for delineating HCHO hotspots, which we re-implement at 0.01° over India.

## Mathematical formulation
CPCB sub-index and aggregation [C][D]:

```
I_p = ((I_Hi - I_Lo)/(BP_Hi - BP_Lo)) * (C_p - BP_Lo) + I_Lo
AQI = max_p { I_p }          # CPCB / EPA
```

Entropy-weighted alternative (RAPI) [D]:

```
e_j = -(1/ln n) * Σ_i p_ij ln p_ij ,   w_j = (1 - e_j) / Σ_k (1 - e_k)
RAPI = Σ_j w_j I_j
```

FNR regime indicator (HCHO/NO₂) for O₃ sensitivity [A][B]: FNR < 1 ⇒ VOC-limited, > 2 ⇒ NOₓ-limited.

## Python libraries
`numpy`, `pandas`, `scipy.stats` (entropy), `matplotlib`/`seaborn`, `bibtexparser` for reference management; figures via `cartopy`.

## Code in this repo
The CPCB sub-index and max/entropy aggregation reviewed here are implemented in `src/isro_aqi/aqi/engine.py` (breakpoints in `config/aqi_breakpoints.yaml`); the PHV/HVA method [A] in `src/isro_aqi/hcho/phv.py`, with Getis-Ord Gi* (`getis_ord.py`) and scipy connected-component clusters (`source_attribution.py`) as extensions.

```python
from isro_aqi.aqi.engine import sub_index, overall_aqi   # CPCB [C][D]
```

## Expected outputs
A referenced gap analysis and a one-page novelty statement: **no prior study jointly delivers India-wide multi-pollutant AQI maps + HCHO hotspot atlas + quantified biomass-burning/transport attribution with a dual CPCB-max/entropy-RAPI index.**

## Potential challenges & mitigations
- *Methodological heterogeneity across [A]–[D]* (different domains/resolutions) → harmonise to a common 0.1° (AQI) / 0.01° (HCHO) grid.
- *Skill ceilings for SO₂/CO* [C] → set realistic acceptance thresholds, not PM-level expectations.

## Validation / QA
Cross-check our reproduced CPCB AQI against CPCB's published station AQI; benchmark model skill against [C]'s CV table as an external sanity bound.

## Publication-quality figures
- Fig 1.1 Taxonomy of AOD→PM2.5 methods (statistical→ML→DL).
- Fig 1.2 Comparative bar chart: [C] CV R² per pollutant vs our targets.
- Fig 1.3 Conceptual schematic: HCHO as VOC/biomass-burning tracer feeding FNR-based O₃ regimes [A][B].
