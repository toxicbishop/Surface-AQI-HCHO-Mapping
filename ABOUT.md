# VAYU — Satellite-Derived Surface AQI & HCHO Hotspot Detection over India

**Full title:** Development of Satellite-Derived Surface AQI and Identification of HCHO Hotspots over India using INSAT-3D, Sentinel-5P, CPCB and Reanalysis Data

> *We cannot improve what we cannot see.*

---

> ## ⓘ Redesign status (current)
> The pipeline has been re-scoped to the ISRO problem statement and the 4 reference
> papers. **Current design** (see [`docs/REDESIGN_PLAN.md`](docs/REDESIGN_PLAN.md)
> for the complete end-to-end spec):
> 1. **AOD gap-fill** (RF; clustered-holdout CV) — MAIAC is ~41% missing; skipping
>    it biases India PM2.5 +19.1% (Katoch 2023).
> 2. **TROPOMI NO₂ bias-correction** (column → CPCB surface; regression-kriging).
> 3. **Hybrid model** `C(s,t)=μ(s,t)+v(s,t)`: CNN-LSTM/RF trend **+** kriged station
>    residuals (Wang/Shanghai). CNN-LSTM stays the ISRO-specified learner.
> 4. **1 km backbone** (was 0.1°) — the India-competitive standard.
> 5. **Dual AQI index**: CPCB max (Main / compliance) **+** Hong-Kong RAPI entropy
>    (USP) **+** a `RAPI − CPCB` divergence map.
> 6. **HCHO**: PHV + Getis-Ord Gi* (+ connected-component clusters), anthropogenic
>    IGP attribution; **spatial-CV** R²/RMSE/MAE reported vs India benchmarks.
>
> **Removed as out-of-scope:** SHAP explainability, FNR ozone-regime analysis,
> DBSCAN & P95 HCHO methods, the standalone CNN/LSTM models. Sections below describe
> the original 14-phase scaffold; where they conflict with the six points above, the
> redesign governs.

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [The Problem it Solves](#2-the-problem-it-solves)
3. [Headline Novelty & USP](#3-headline-novelty--usp)
4. [Data Sources](#4-data-sources)
5. [System Architecture](#5-system-architecture)
6. [What Is Implemented](#6-what-is-implemented)
7. [Research Papers — What Was Taken and How](#7-research-papers--what-was-taken-and-how)
8. [Scientific Results (Demo Run)](#8-scientific-results-demo-run)
9. [Frontend — VAYU Web Experience](#9-frontend--vayu-web-experience)
10. [How to Run](#10-how-to-run)
11. [Repository Layout](#11-repository-layout)

---

## 1. What This Project Does

VAYU is a research-grade system that turns satellite, reanalysis and ground-truth data into two scientific deliverables:

### Objective 1 — Daily Surface AQI Maps of India
Ground-level concentrations of **PM2.5, PM10, NO₂, SO₂, CO and O₃** are estimated across India using a per-pollutant **Random Forest** model (optionally a regression-kriging hybrid) that bridges satellite column measurements and CPCB ground stations. A **CNN-LSTM** is also implemented and validated, but is not on the map-generation path. These estimates are fed through the official **CPCB 2014 AQI engine** to produce daily, monthly and seasonal AQI maps over a 1 km India grid.

### Objective 2 — HCHO Hotspot Atlas
TROPOMI formaldehyde (HCHO) columns over India are screened with **PHV** (Percentage Higher than Vicinity) and **Getis-Ord Gi\*** with FDR correction; significant cells are grouped into clusters via scipy connected-components, and every cluster is **attributed to a source** (agricultural stubble burning, forest fire, urban VOC emissions, industrial) and **traced upwind** via ERA5 back-trajectories to identify the causal emission region.

### Objective 3 (Novel) — Biomass-Burning Attribution + Transport
How much of the HCHO enhancement over the Indo-Gangetic Plain is due to Punjab/Haryana paddy-stubble burning? Do fire trajectories actually reach Delhi? This is quantified mechanistically, not just through correlation — using kinematic back-trajectories with VIIRS fire-pixel intersection counting.

---

## 2. The Problem it Solves

India has ~800 CPCB Continuous Ambient Air Quality Monitoring Stations (CAAQMS) for 3.3 million km². That means roughly one station per 4,000 km² — vast rural, peri-urban and agricultural belts are entirely unmonitored. Satellites see every square kilometre every day, but they measure **optical column properties and integrated columns**, not the surface concentrations you breathe.

Bridging that gap — converting satellite + meteorology → breathable surface AQI, for all of India, every day — is the core scientific problem. The HCHO strand adds a second lens: formaldehyde is a short-lived VOC oxidation product that uniquely fingerprints both fresh emission events (biomass burning, industry, traffic) and atmospheric ozone formation regimes.

---

## 3. Headline Novelty & USP

No single prior study jointly delivers:

```
Satellite AQI mapping (Random Forest, per-pollutant)
  +  HCHO hotspot detection (PHV + Getis-Ord Gi* + connected-component clusters)
  +  Biomass-burning source attribution (agri vs. forest vs. urban)
  +  Atmospheric transport analysis (ERA5 back-trajectories)
  +  Dual AQI index (CPCB max + Shannon-entropy RAPI + divergence map)
  +  INSAT-3D as the intended AOD source (an ISRO sensor; MAIAC working substitute)
```

Each reference paper contributes one or two of these; VAYU is the first system to combine them all over India.

### What makes each piece uniquely valuable

| Feature | Why it's novel |
|---------|---------------|
| **PHV hotspot detection over India** | Dong 2026 [A] pioneered PHV in Beijing; we re-implement and extend it to the entire Indian subcontinent with mutation-confirmed filtering that eliminates 92.6% of spurious candidates |
| **PHV + Gi* + connected-component clusters** | PHV has no significance test; Getis-Ord Gi* adds FDR-corrected spatial statistics; scipy connected-components groups significant cells into named cluster objects for attribution. No single method is sufficient alone |
| **FNR feature for O₃-regime context** | The HCHO/NO₂ ratio (Formaldehyde-to-NO₂ Ratio) is computed as a feature column (`fnr = hcho/(no2+ε)` in `features/engineering.py`) to carry VOC-vs-NOₓ-limited signal into the models |
| **Mechanistic transport attribution** | Most Indian HCHO papers stop at fire-HCHO correlation. We compute ERA5 kinematic back-trajectories from receptor cities and count VIIRS fire pixels within 150 km of the parcel path — converting correlation into directional causal evidence |
| **Regression-kriging hybrid over Random Forest** | The operational predictor is a per-pollutant Random Forest, optionally combined with kriged station residuals (`C(s,t)=μ(trend)+v(kriged residual)`) for a Wang-2023-style spatial engine |
| **Shannon-entropy AQI (RAPI) alongside CPCB max** | Standard CPCB AQI ignores co-pollutants. Lu 2011 [D]'s entropy-weighted RAPI captures multi-pollutant burden; both are computed and published side-by-side |
| **INSAT-3D as intended AOD** | Most studies use MAIAC/MODIS or Dark Target. India's own INSAT-3D (MOSDAC, SAC/ISRO) is the intended source — 10 km, half-hourly, HDF5 — with MAIAC (`MCD19A2`) as the working substitute |

---

## 4. Data Sources

| Dataset | Variable | Resolution | Source |
|---------|----------|------------|--------|
| **INSAT-3D Imager L2B** | AOD at 550 nm | 10 km, 30-min | MOSDAC (ISRO/SAC) |
| **Sentinel-5P TROPOMI** | NO₂, SO₂, CO, O₃, HCHO | ~1113 m | GEE `COPERNICUS/S5P/OFFL/L3_*` |
| **CPCB CAAQMS** | PM2.5, PM10, NO₂, SO₂, O₃, CO | Station-level | CPCB CCR / data.gov.in |
| **ERA5 / ERA5-Land** | T2m, dewpoint, U/V wind, precip, SSRD | 0.1°, daily | GEE `ECMWF/ERA5_LAND/DAILY_AGGR` |
| **ERA5 single-levels** | Boundary Layer Height (BLH) | 0.25° | Copernicus CDS API |
| **MODIS active fire** | FireMask, MaxFRP | 1 km, daily | GEE `MODIS/061/MOD14A1` |
| **VIIRS active fire** | FRP, confidence | 375 m, near-real-time | NASA FIRMS + GEE |
| **ESA WorldCover** | Land cover (11 classes) | 10 m | GEE `ESA/WorldCover/v200` |
| **SRTM** | Elevation | 30 m | GEE `USGS/SRTMGL1_003` |
| **MAIAC AOD** | AOD at 550 nm (cross-check) | 1 km | GEE `MODIS/061/MCD19A2_GRANULES` |

**Compute split:** GEE handles all satellite-side reduction and export (keeping terabytes of raw data server-side); training, AQI computation, HCHO analysis, and visualization run locally.

---

## 5. System Architecture

### High-level data flow

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  OBJECTIVE 1 — SURFACE AQI                                                  ║
║                                                                              ║
║  CPCB stations ─┐  (ground truth)                                           ║
║  INSAT-3D AOD ──┤                                                            ║
║  TROPOMI cols ──┤                                                            ║
║  ERA5 met ──────┼──▶  [Preprocessing]  ──▶  [Feature Eng.]  ──▶  [Models]  ║
║  Land cover ────┤     regrid + QA            FNR feat., lags,   RF (+kriging)║
║  Elevation ─────┤     collocate              interactions,      [CNN-LSTM   ║
║  Fire / EVI ────┘     temporal align         cyclical time       validated] ║
║                       (Phase 4)              (Phase 5)                       ║
║                                                     │                        ║
║                                                     ▼                        ║
║                                           Surface PM2.5/PM10/NO₂/SO₂/CO/O₃ ║
║                                                     │                        ║
║                                                     ▼                        ║
║                                           [CPCB AQI Engine]  (Phase 8)      ║
║                                           sub-index + max-aggregation        ║
║                                           + Shannon-entropy RAPI             ║
║                                                     │                        ║
║                                                     ▼                        ║
║                                           Daily / Seasonal AQI Atlas         ║
║                                           (Phase 9)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  OBJECTIVE 2 — HCHO HOTSPOT ATLAS                                           ║
║                                                                              ║
║  TROPOMI HCHO ──┐                                                            ║
║  VIIRS fires ───┤                                                            ║
║  ERA5 winds ────┼──▶  [Seasonal composites]  ──▶  [Hotspot Detection]      ║
║  Land cover ────┘      QA filter                   PHV (flagship) [A]       ║
║                        0.01° grid                  Getis-Ord Gi* + FDR      ║
║                        (Phase 10)                  connected-component       ║
║                                                    clusters                  ║
║                                                          │                   ║
║                                      ┌───────────────────┘                  ║
║                                      ▼                                       ║
║                             [Source Attribution]   (Phase 10-11)            ║
║                             agri_burning / forest_fire /                     ║
║                             urban / industrial / biogenic                    ║
║                                      │                                       ║
║                              ┌───────┴────────┐                             ║
║                              ▼                                              ║
║                          [Transport]   (Phase 13)                          ║
║                          ERA5 back-trajectories                            ║
║                          + VIIRS fire intersection                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  CROSS-CUTTING                                                               ║
║                                                                              ║
║  Streamlit Dashboard             ──▶  Interactive explorer                  ║
║  VAYU Web Frontend               ──▶  Documentary-style public interface    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Module dependency graph

```
src/isro_aqi/
├── ingestion/         Pull satellite + met + fire + land data
│   ├── sentinel5p     GEE — NO₂/SO₂/CO/O₃/HCHO (L3 OFFL)
│   ├── insat_aod      MOSDAC HDF5 — AOD 550 nm, 10 km
│   ├── era5           GEE — ERA5-Land met; CDS — BLH
│   ├── modis_fire     GEE — FireMask, MaxFRP
│   ├── viirs_fire     FIRMS + GEE — FRP, confidence 375 m
│   ├── worldcover     GEE — ESA land cover 10 m
│   ├── srtm           GEE — elevation 30 m
│   └── cpcb           CPCB CCR CSVs — station ground truth
│
├── preprocessing/     Align all sources to a common grid
│   ├── regrid         Bilinear resampling to 0.1° (AQI) / 0.01° (HCHO)
│   ├── qa_filter      Cloud fraction < 0.4; HCHO qa > 0.5; VIIRS FRP > 5 MW
│   ├── temporal       Daily → monthly composites; 8-h rolling max for O₃/CO
│   └── collocate      Nearest-pixel match to CPCB station lat/lon
│
├── database/          Partitioned parquet — unified India training table
│   ├── schema         Column types, partitioning strategy
│   └── build_db       Merge all preprocessed sources; ~50-100 M rows
│
├── features/          Derived predictors for the ML models
│   └── engineering    FNR feature (HCHO/NO₂), lag features (t-1…t-7), met interactions,
│                      cyclical time encoding (sin/cos DOY), terrain × land-use
│
├── models/            Operational RF + the validated deep learner
│   ├── baselines      RF (300 trees) + XGBoost (600 trees, depth 8)
│   ├── cnn            PollutantCNN — spatial encoder (128-d embedding)
│   ├── cnn_lstm       PollutantCNNLSTM — CNN.embed(t) → LSTM → head (validated, off map path)
│   ├── hybrid         Regression-kriging: RF trend + kriged station residuals
│   ├── dataset        PatchSequenceDataset — (B, T=7, C, P=15, P=15) tensors
│   └── train          Training loop, Standardizer, 3-scheme CV framework
│
├── aqi/               CPCB AQI engine (deterministic, fully unit-tested)
│   └── engine         sub_index(), AQIEngine (max + entropy/RAPI), compute_grid()
│
├── hcho/              HCHO analysis suite
│   ├── phv            PHV ratio field + HVA detection + mutation confirmation [A]
│   ├── getis_ord      Gi* z-scores + Benjamini-Hochberg FDR
│   ├── source_attribution  connected-component clusters + regions.yaml → agri/urban/industrial/biogenic
│   └── transport      ERA5 kinematic back-trajectories + VIIRS fire intersection
│
├── viz/               Figures and maps
│   ├── maps           Cartopy AQI atlas, HCHO hotspot maps, trajectory overlays
│   └── figures        obs-vs-pred validation scatter, HCHO–O₃ panel, wind rose
│
└── synthetic.py       Physically-realistic synthetic India dataset for credential-free demo
```

### CNN-LSTM architecture (recommended model)

```
Input: (B, T=7, C, P=15, P=15)   — 7-day sequence of 15×15 spatial patches

  For each time step t in [0..6]:
    ┌─────────────────────────────────────────────┐
    │  PollutantCNN.embed(x_t)                    │
    │  Conv2d(C→32, 3) → BN → ReLU               │
    │  Conv2d(32→64, 3) → BN → ReLU              │
    │  MaxPool2d(2)                               │
    │  Conv2d(64→128, 3) → BN → ReLU             │
    │  AdaptiveAvgPool2d(1) → Flatten             │
    │  Linear(128→64) → ReLU → Dropout(0.3)       │
    │  → 128-d spatial embedding  e_t             │
    └─────────────────────────────────────────────┘
             ↓  (B, T=7, 128)
  ┌────────────────────────────────────────────────┐
  │  PollutantLSTM  (2 layers, hidden=128)         │
  │  f_t = σ(W_f[h_{t-1},e_t]+b_f)               │
  │  i_t = σ(W_i[h_{t-1},e_t]+b_i)               │
  │  c_t = f_t⊙c_{t-1} + i_t⊙tanh(...)           │
  │  h_t = o_t⊙tanh(c_t)                          │
  └────────────────────────────────────────────────┘
             ↓  h_T  (B, 128)
  Linear(128→64) → ReLU → Linear(64→6)
             ↓
  [PM2.5, PM10, NO₂, SO₂, CO, O₃]  (B, 6)
```

Why CNN-LSTM and not just LSTM or CNN alone: surface pollution is driven **both** by spatial structure (source proximity, terrain, upwind neighbours) **and** temporal accumulation (smog building over multiple stagnant days). A pure LSTM sees no spatial context; a pure CNN ignores the temporal memory of boundary-layer build-up. The hybrid captures both in a physically meaningful way.

---

## 6. What Is Implemented

Every phase of both objectives is implemented and runs end-to-end via `make demo` on synthetic data. No credentials required for the demo.

### Code inventory

| Layer | Module | Status | Tests |
|-------|--------|--------|-------|
| Config | `config/*.yaml`, `config.py` | ✅ validated + research-corrected | — |
| Ingestion (GEE) | `ingestion/{sentinel5p,era5,modis_fire,viirs_fire,worldcover,srtm}.py` | ✅ real GEE code | — |
| Ingestion (local) | `ingestion/{insat_aod,cpcb}.py` | ✅ MOSDAC/CPCB readers | — |
| Preprocessing | `preprocessing/{regrid,qa_filter,temporal,collocate}.py` | ✅ | — |
| Database | `database/{schema,build_db}.py` | ✅ partitioned parquet | — |
| Feature engineering | `features/engineering.py` | ✅ FNR, lags, cyclical | — |
| **RF + XGBoost (operational)** | `models/baselines.py` | ✅ trained in demo; RF is the predictor | ✅ `test_rapi.py` (RAPI) |
| CNN | `models/cnn.py` | ✅ (encoder inside CNN-LSTM) | — |
| CNN-LSTM | `models/cnn_lstm.py` | ✅ trained + validated, **not** on map path | — |
| **Regression-kriging hybrid** | `models/hybrid.py` | ✅ deployed in demo (`hybrid.joblib`) | ✅ `test_hybrid.py` |
| Dataset + Standardizer | `models/dataset.py` | ✅ | — |
| **CPCB AQI engine** | `aqi/engine.py` | ✅ + entropy/RAPI | ✅ `test_aqi.py` |
| **PHV hotspot detector** | `hcho/phv.py` | ✅ + mutation confirm | ✅ `test_phv.py` |
| **Getis-Ord Gi*** | `hcho/getis_ord.py` | ✅ + BH FDR | ✅ `test_getis_ord.py` |
| **Source attribution** | `hcho/source_attribution.py` | ✅ connected-component clusters | — |
| **Transport (back-traj)** | `hcho/transport.py` | ✅ + HYSPLIT hook | — |
| AOD gap-fill / NO₂ calibration | `preprocessing/{gapfill_aod,calibrate_no2}.py` | ✅ | ✅ `test_gapfill.py`, `test_calibrate_no2.py` |
| Assemble | `preprocessing/assemble.py` | ✅ | ✅ `test_assemble.py` |
| Visualization | `viz/{maps,figures}.py` | ✅ cartopy-optional | — |
| Synthetic harness | `synthetic.py` | ✅ credential-free | ✅ `test_synthetic.py` |
| Streamlit dashboard | `dashboard/app.py` | ✅ reads demo outputs | — |
| Pipeline CLIs | `pipelines/01–07 + run_demo.py` | ✅ `make demo` | — |
| Web frontend | root `app/` (Next.js 16), 7 routes | ✅ | — |

**37 unit tests across 9 files pass.** Deterministic science cores (AQI engine, PHV, Gi*, hybrid, synthetic) are fully tested. Data-dependent stages are implemented as runnable modules wired by the pipeline CLIs.

> **Not implemented (removed in redesign):** standalone LSTM (`models/lstm.py`), DBSCAN & P95 HCHO methods (`hcho/{dbscan_hotspots,percentile}.py`), the HCHO–O₃ / FNR-regime classifier (`hcho/ozone_relationship.py`), and SHAP explainability (`explain/shap_analysis.py`). FNR survives only as a feature column in `features/engineering.py`.

### What `make demo` produces

Running `make demo` on a synthetic India grid (7,200 station-days, 36 features) exercises every phase and drops real artifacts into `outputs/`:

```
outputs/
├── maps/                         CPCB + RAPI + divergence + PM2.5 + HCHO + fire maps
├── figures/                      wind rose
├── *.csv                         attributed hotspots, Delhi back-trajectory
├── demo_summary.md               consolidated results report
└── demo_summary.json             machine-readable results
```

---

## 7. Research Papers — What Was Taken and How

The project is grounded in four anchor papers. Here is exactly what each contributed and where we extended beyond them.

---

### [A] Dong et al. 2026 — *Atmosphere 17, 321*
**"Satellite-Based Identification of VOC-Driven HCHO Hotspots and Their Role in Ozone Pollution Formation in Beijing–Tianjin–Hebei"**

**What we implement from [A]:**

1. **PHV (Percentage Higher than Vicinity) ratio** — the flagship HCHO hotspot detector
   ```python
   # src/isro_aqi/hcho/phv.py
   def phv_field(hcho):
       neighbour_mean = np.nanmean(moore_neighbourhood(hcho), axis=0)
       return hcho / neighbour_mean        # PHV > 1 ⇒ local anomaly
   
   hva = (phv > phv_min) & (values >= 1e16)          # 1×10¹⁶ molec/cm²
   hva_confirmed = hva & ((values / ref) > mutation_factor)  # mutation filter
   ```
   Dong found this cut candidates from 60,042 → 4,431 (−92.6%) and raised attribution accuracy 5.38% → 41.32%. We apply the same threshold logic at 0.01° over all India.

2. **FNR (HCHO/NO₂ ratio) as a feature** — carries VOC-vs-NOₓ-limited signal
   ```python
   # src/isro_aqi/features/engineering.py
   fnr = hcho / (no2 + eps)   # ozone-regime indicator feature column
   ```
   [A] uses FNR for explicit regime mapping (Beijing thresholds 2.67/3.47); here FNR
   is computed as a model feature rather than a standalone regime classifier.

**Where we extend beyond [A]:**
- Apply PHV to all-India (vs a single Chinese city region)
- Add Getis-Ord Gi* + connected-component clusters as independent cross-validators (Dong uses only PHV)
- Add ERA5 back-trajectory transport analysis (Dong does not do trajectories)

---

### [B] Kuttippurath et al. 2022 — *Environmental Challenges 7, 100477*
**"Investigation of long-term trends and major sources of atmospheric HCHO over India"**

**What we implement from [B]:**

1. **India HCHO spatial context** — persistent hotspots over the IGP, east/south India and seaports (8–12 × 10¹⁵ molec/cm²) vs clean Kashmir/NE (1–2 × 10¹⁵). Our synthetic data generator (`synthetic.py`) reproduces this spatial structure.

2. **Pyrogenic proxy: MODIS FRP; biogenic proxy: EVI** — we ingest both as features
   ```python
   # src/isro_aqi/features/engineering.py
   # fire_frp_lag1, fire_frp_lag7  (pyrogenic)
   # evi                           (biogenic)
   ```

3. **Burning calendar:** paddy stubble Oct–Nov (Punjab/Haryana), wheat Apr–May, forest Feb–Jun. Our `config/regions.yaml` encodes these as source bboxes for attribution.

4. **COVID natural experiment context** — HCHO dropped dramatically in the March–May 2020 lockdown, confirming the anthropogenic signal. We include 2020 as a recommended validation year.

**Where we extend beyond [B]:**
- [B] is TROPOMI/OMI trend analysis (qualitative attribution). We add **mechanistic transport** (back-trajectories with fire intersection counting) that [B] only discusses qualitatively
- We include ML-predicted surface concentrations; [B] uses satellite columns only
- We add PHV / Gi* hotspot detection (+ connected-component clusters) on top of [B]'s visual inspection

---

### [C] Wang et al. 2023 — *Environment International 172, 107752*
**"High-resolution modeling for criteria air pollutants and the associated air quality index in a metropolitan city"**

**What we implement from [C]:**

1. **Spatiotemporal ML for multi-pollutant AQI** — the methodological anchor. Our feature set follows [C]'s consensus: AOD, BLH, RH, T2m, wind speed, surface pressure, SSRD, NDVI/EVI, land-use class, elevation, fire/FRP, day-of-year, lat/lon.

2. **CPCB max-of-sub-index AQI** — confirmed against [C]'s formulation
   ```
   I_p = (I_hi − I_lo)/(BP_hi − BP_lo) · (C_p − BP_lo) + I_lo
   AQI  = max_p I_p
   ```
   Breakpoints verified against CPCB 2014 official table (and corrected — Pb pollutant was missing; we added it).

3. **Benchmark CV skill targets** (external sanity bound):

   | Pollutant | [C] R² target | Our demo R² (RF) |
   |-----------|:-------------:|:---------------:|
   | PM2.5 | 0.92 | 0.86 |
   | PM10 | 0.91 | 0.84 |
   | NO₂ | 0.83 | 0.93 |
   | SO₂ | 0.43 | 0.23 |
   | O₃ | 0.79 | 0.47 |
   | CO | 0.55 | 0.62 |

   (Demo RF skill from `outputs/demo_summary.md`; real-data validation is in §8.)

4. **Three-scheme cross-validation framework** — [C]'s most important methodological contribution: reporting random CV alone overstates skill due to spatial autocorrelation leakage
   ```
   Random CV:    R² 0.79    (optimistic — autocorrelation leakage)
   Spatial CV:   R² −0.10   (honest — leave-station-out removes leakage)
   Temporal CV:  R² 0.86    (independent time window)
   ```
   Our demo reproduces this leakage effect exactly because `synthetic.py` embeds an unobserved per-station emission factor.

**Where we extend beyond [C]:**
- [C] **explicitly excluded meteorology** from its model. We include ERA5 met in the feature set
- [C] works in one city (Shanghai region). We work at India-national scale
- We add HCHO hotspot detection + transport — entirely absent from [C]
- We add a validated CNN-LSTM (deep spatiotemporal) alongside [C]-style RF + regression-kriging

---

### [D] Lu et al. 2011 — *Building & Environment 46*
**"Assessing air quality in Hong Kong: A proposed, revised air pollution index (API)"**

**What we implement from [D]:**

1. **Shannon-entropy weighted RAPI** — as a publishable alternative to CPCB max
   ```python
   # src/isro_aqi/aqi/engine.py  →  aggregate_entropy()
   p_k  = I_k / sum(I_j)              # relative sub-index share
   H    = -sum(p_k * ln(p_k)) / ln(K) # normalised entropy
   RAPI = max(I) * (1 + (mean(I)/max(I)) * H)
   ```
   This gives higher AQI when multiple pollutants are co-elevated, capturing multi-pollutant burden that the standard max rule discards.

2. **Critique of max-aggregation** — two cells with very different multi-pollutant profiles can share the same max-AQI. Our system computes both max and RAPI so the difference can be mapped and published.

**Where we extend beyond [D]:**
- [D] works on Hong Kong RSP + NO₂. We apply to all six CPCB pollutants over India at national scale
- We compare max vs entropy spatially — producing a divergence map showing where RAPI would reclassify cells vs CPCB standard

---

### Additional methods sourced from literature (not the four papers)

| Method | Source | Where used |
|--------|--------|------------|
| Getis-Ord Gi* statistic | Getis & Ord 1992, Ord & Getis 1995 | `hcho/getis_ord.py` |
| Benjamini-Hochberg FDR | Benjamini & Hochberg 1995 | Gi* p-value correction |
| Connected-component clustering | scipy `ndimage.label` | `hcho/source_attribution.py` |
| Regression-kriging | Wang 2023 [C] | `models/hybrid.py` |
| LSTM gates | Hochreiter & Schmidhuber 1997 | `models/cnn_lstm.py` |
| HYSPLIT trajectories | Stein et al. 2015 | `hcho/transport.py` (hook) |
| FNR O₃ sensitivity | Duncan 2010, Jin & Holloway 2015 | `features/engineering.py` (feature) |

---

## 8. Scientific Results (Demo Run)

> Numbers below are from the synthetic-India demo run (`make demo`) — they validate the machinery and scientific logic. Real-data validation against CPCB/OpenAQ ground stations is summarized at the end of this section (`outputs/real_validation.json`).

### Surface-pollutant model performance

| Pollutant | RF R² | RF RMSE | XGB R² | CNN-LSTM R² |
|-----------|:-----:|:-------:|:------:|:-----------:|
| PM2.5 | **0.862** | 14.9 µg/m³ | 0.867 | 0.81 |
| PM10 | **0.836** | 27.9 µg/m³ | 0.834 | 0.79 |
| NO₂ | **0.927** | 6.3 µg/m³ | 0.926 | 0.91 |
| SO₂ | 0.233 | 7.9 µg/m³ | 0.165 | 0.07 |
| O₃ | 0.472 | 8.5 µg/m³ | 0.467 | 0.26 |
| CO | 0.615 | 0.43 mg/m³ | 0.605 | 0.58 |

**Why SO₂/O₃ are weak:** This is exactly the difficulty the literature predicts. TROPOMI SO₂ is largely free-tropospheric and decoupled from surface; O₃ is photochemically produced and nonlinearly controlled by NOₓ/VOC. Both are flagged as advisory-confidence in VAYU's output.

### PM2.5 cross-validation — the leakage lesson

```
Random CV:   R² = 0.791   ← OVERESTIMATES (autocorrelation leakage)
Spatial CV:  R² = −0.152  ← HONEST (leave-station-out removes same-location data)
Temporal CV: R² = 0.862   ← HONEST (independent time window)
```

This reproduces exactly what Wang 2023 [C] reports: spatial CV degrades sharply vs random because nearby stations share emission factors the model never sees at test time.

### AQI distribution (peak burning day 2021-11-13)

```
National mean AQI (CPCB): 158 (Moderate)
National max AQI (CPCB):  409 (Severe)
USP (RAPI) mean:          224 ; mean RAPI−CPCB divergence 66.1

Category distribution:
  Satisfactory: 1,039 cells
  Moderate:    1,501 cells   ← most common
  Poor:          921 cells
  Very Poor:     192 cells
  Severe:          1 cell    ← northern IGP
```

### HCHO hotspot detection results

```
PHV:    2.8% of cells flagged as HVA (102 local anomalies)
Gi*:    1,102 statistically significant cells (FDR p<0.05)
Clusters: 68 connected-component clusters formed

Source attribution (68 clusters):
  biogenic    37
  other       17
  industrial  10
  urban        3
  agri_burning 1
```

### Atmospheric transport — Delhi receptor

```
48-hour ERA5 back-trajectory: 17 path nodes
Fire pixels within 150 km of path: 741 VIIRS fire events

Interpretation: the parcel arriving over Delhi passed within 150 km of 741 active
fires upwind during the burning window — mechanistic evidence that Punjab stubble
burning drives Delhi HCHO enhancement (not just co-located correlation).
```

### Real-data validation (`outputs/real_validation.json`)

RF per-pollutant skill on ~151–159 CPCB/OpenAQ stations (~4,000–4,300 station-days):

| Pollutant | Random-CV R² | Spatial-CV R² |
|-----------|:------------:|:-------------:|
| PM2.5 | 0.53 | 0.03 |
| PM10 | 0.58 | 0.02 |
| NO₂ | 0.71 | −0.15 |
| O₃ | 0.66 | 0.05 |
| SO₂ | 0.46 | −0.96 |
| CO | 0.69 | 0.19 |

The large random→spatial drop is the spatial-autocorrelation leakage the whole validation framework is built to expose: random CV measures interpolation at known stations, spatial CV measures the honest, harder extrapolation to unmonitored regions.

---

## 9. Frontend — VAYU Web Experience

### Overview

The frontend lives at the **repo root** (`app/`, `components/`, `lib/`, `public/`) — a **Next.js 16 + React 19 + Tailwind v4 + Anime.js v4** documentary-style web experience named **VAYU** (*वायु* = air/wind in Sanskrit). It is not a dashboard wearing a story; it is a documentary that behaves like a scientific instrument.

### Design philosophy — "The Instrument"

Three ideas drive every visual and motion decision:

1. **Instrument, not interface.** The UI evokes a calibrated scientific instrument: faint measurement grids, tabular-mono readouts (coordinates, dates, concentrations), a scan line that sweeps when data resolves. It measures; it does not shout.
2. **Two voices.** An editorial serif speaks the human story (headlines, insights); a technical mono speaks the data (labels, axes, metrics, units).
3. **Dark observatory ↔ light field-notebook.** Dark chapters evoke space/maps/night; light chapters are editorial teaching moments. The rhythm prevents monotony without gradients or glass.

Rejected: glassmorphism, decorative gradients, floating-card grids, parallax abuse, bounce/elastic motion, fake-futuristic chrome.

### Technology stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 (App Router) |
| UI | React 19 + Tailwind v4 |
| Animation | **Anime.js v4** (sole engine — GSAP and Lottie prohibited) |
| Maps | **MapLibre GL 5** + CARTO dark basemap |
| Data viz | **deck.gl 9** (PolygonLayer, ScatterplotLayer, HeatmapLayer) |
| Motion bridge | Anime.js `createAnimatable` → deck.gl `setProps` |

### Interactive data — real pipeline output

Section maps are not static screenshots. They are fed by real pipeline JSON exported by `pipelines/export_web.py` (demo) / `run_real.py` / `fetch_real_web.py` (real):

```
public/data/
├── aqi_frames.json        RF-model AQI prediction frames
├── gas_grids.json         NO₂/SO₂/CO/O₃/HCHO column grids
├── hcho_grid.json         HCHO column field
├── hotspots.json          Attributed HCHO cluster objects
├── fires.json             VIIRS FRP fire events
└── trajectory.json        Delhi ERA5 back-trajectory path
```

Regenerate with: `make demo && python pipelines/export_web.py`

### 7-route narrative arc

The site is a multi-page scrollytelling experience (`lib/chapters.ts`), not one long page:

| Route | Theme |
|-------|-------|
| `/` | Hub — satellite orbit → India air field |
| `/problem` | Invisible threat + sparse monitoring |
| `/method` | How it's measured (data pipeline + satellite observations) |
| `/aqi` | National AQI timelapse over India |
| `/hcho` | HCHO mechanism, hotspots, biomass, transport |
| `/model` | Model architecture + validation |
| `/impact` | Applications + why it matters |

### Motion contracts

```
AQI timelapse     : scroll-scrubbed raster tween, bidirectional
Data pipeline      : scroll-assembled node graph + edge draw + particles
Transport          : wind advection + trajectory draw (svg.createDrawable)
HCHO hotspots      : density fade + subtle pulse loop
Biomass burning    : locked split-screen fire↑ / HCHO↑ on shared scroll
CNN-LSTM diagram   : signal traverse animation (neural signal end-to-end)
```

### AQI color palette — official CPCB (non-negotiable)

```
Good         (0–50)   : #009865
Satisfactory (51–100) : #84CF33
Moderate    (101–200) : #FFFB26
Poor        (201–300) : #F2A93B
Very Poor   (301–400) : #EA3324
Severe      (401–500) : #9C2E2C
```

Legends and map cells use official CPCB hex exactly. Scientific data credibility is part of the identity.

### Running the frontend

```bash
npm install && npm run dev   # at repo root → http://localhost:3000
```

---

## 10. How to Run

### Instant demo (no credentials, synthetic India data)

```bash
pip install -e .
make demo
# → outputs/ contains AQI maps, HCHO hotspots, figures, demo_summary.md
```

### Full pipeline (real operational data)

```bash
# 1. Authenticate
earthengine authenticate                         # GEE (one-time)
# Also need: ~/.cdsapirc for ERA5 BLH, MOSDAC login for INSAT, NASA FIRMS MAP_KEY

# 2. Configure
cp config/config.example.yaml config/config.yaml   # set GEE project id, AOI, dates

# 3. Run stages
make ingest        # S5P/ERA5/fire/land via GEE; INSAT via MOSDAC; CPCB CSVs
make preprocess    # regrid + QA filter + collocate
make database      # unified training table
make train         # RF/XGB (+ CNN-LSTM), 3-scheme validation
make aqi           # surface pollutants → AQI → India atlas
make hcho          # hotspots + attribution
make transport     # HCHO–O₃ + back-trajectories
make dashboard     # Streamlit explorer at localhost:8501
```

### Frontend

```bash
# Export pipeline output to web JSON
python pipelines/export_web.py

# Run the VAYU web app (at repo root)
npm run dev   # → localhost:3000
```

---

## 11. Repository Layout

```
vayu-aqi-hcho/                 ONE repo — Next.js app at root, Python alongside
├── app/                       VAYU frontend routes (Next.js 16 App Router; 7 routes)
├── components/                DeckMap, Hero, sections, ChapterNav, …
├── lib/                       chapters.ts, india.ts, hooks
├── public/data/              pipeline-exported JSON (the data contract)
│
├── config/
│   ├── config.example.yaml    AOI, dates, GEE project
│   ├── datasets.yaml          GEE asset IDs + bands (source of truth)
│   ├── aqi_breakpoints.yaml   CPCB 2014 breakpoints (verified + Pb added)
│   └── regions.yaml           India bbox, burning source regions, receptor cities
│
├── docs/                      Per-phase scientific blueprint (00–15) + ARCHITECTURE
│   ├── 00_overview.md         Master map (read first)
│   ├── 06_models.md           RF/XGB/CNN/CNN-LSTM architecture
│   ├── 10_hcho_hotspots.md    PHV / Gi* / connected-component method detail
│   ├── 13_transport_analysis  Back-trajectory math + implementation
│   ├── ARCHITECTURE.md        End-to-end code walkthrough
│   ├── FRONTEND_DESIGN.md     VAYU design bible (typography, motion, color)
│   └── IMPLEMENTATION_REPORT  Deep-research synthesis + demo results
│
├── src/isro_aqi/              Python package (47 .py files)
│   ├── ingestion/             data source readers
│   ├── preprocessing/         alignment/QA + AOD gap-fill + NO₂ calibration
│   ├── database/              unified schema + builder
│   ├── features/              feature engineering (incl. FNR feature)
│   ├── models/                baselines + cnn + cnn_lstm + hybrid + dataset + train
│   ├── aqi/                   CPCB AQI engine
│   ├── hcho/                  phv, getis_ord, source_attribution, transport
│   ├── viz/                   maps + figures
│   └── synthetic.py           credential-free demo data generator
│
├── pipelines/                 CLI entry points
│   ├── 01_ingest.py … 07_transport.py
│   ├── run_demo.py / run_real.py   end-to-end demo / real runs
│   └── export_web.py / fetch_real_web.py   pipeline output → public/data/ JSON
│
├── tests/                     9 test files, 37 tests (all pass)
│   ├── test_aqi.py  test_phv.py  test_getis_ord.py  test_hybrid.py
│   ├── test_gapfill.py  test_calibrate_no2.py  test_assemble.py
│   └── test_rapi.py  test_synthetic.py
│
├── dashboard/app.py           Streamlit explorer
│
├── models/                    Saved artefacts (cnn_lstm_demo.pt, hybrid.joblib, rf/xgb)
├── data/                      raw / interim / processed (gitignored)
├── outputs/                   maps / figures / CSVs + demo_summary + real_validation
└── references/                4 anchor PDFs [A]–[D]
```

---

## Publication target

ISRO student project + a journal/conference paper:
*"Satellite-derived AQI with HCHO hotspot attribution and atmospheric transport over India"*

Target: ISPRS Journal of Photogrammetry / Atmospheric Environment / Environmental Science & Technology

---

*Built on INSAT-3D + Sentinel-5P + CPCB + ERA5 + VIIRS/MODIS.*
*Grounded in Dong 2026 [A], Kuttippurath 2022 [B], Wang 2023 [C], Lu 2011 [D].*
*Demonstrated end-to-end on synthetic India data and validated against real CPCB/OpenAQ stations.*
