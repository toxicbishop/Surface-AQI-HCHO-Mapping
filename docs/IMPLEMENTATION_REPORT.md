# Implementation Report

> _Point-in-time report (pre-redesign sections may be dated)._

**Development of Satellite-Derived Surface AQI and Identification of HCHO Hotspots
over India using INSAT-3D, Sentinel-5P, CPCB and Reanalysis Data**

This report documents (1) the deep-research findings that ground the methodology,
(2) the complete implementation, and (3) a working end-to-end demonstration of the
full pipeline producing real AQI maps, HCHO hotspots, source attribution, transport
analysis and explainability — executed on a physically-realistic synthetic India
dataset because the live sources require interactive credentials.

> **Headline:** every phase of both objectives is implemented and runs end-to-end
> (`make demo`). Moving from synthetic to operational data is only a matter of
> providing credentials and running the ingestion modules; no downstream code
> changes. The deterministic scientific cores (CPCB AQI, PHV, Getis-Ord Gi*,
> regression-kriging hybrid, the vectorised AQI grid) are unit-tested (37 tests).

---

## 1. Deep-research synthesis (and corrections applied)

Four targeted research streams validated the design against current (2022–2025)
literature and the official data products. Key findings and the resulting code/config
changes:

### 1.1 Satellite data products (verified GEE asset IDs)
- **Sentinel-5P OFFL L3** asset IDs and bands confirmed for NO₂/SO₂/CO/O₃/HCHO (all
  `mol/m²`, ~1113 m). **Correction:** `qa_value` is applied by Google when building
  L3 (NO₂ ≥75 %, HCHO/SO₂/CO/O₃ ≥50 %); it is *not* a band — further screening is
  done via the **`cloud_fraction`** band. Code/config updated to mask on
  `cloud_fraction < 0.4` rather than a non-existent qa band. Unit conversion
  mol/m² → molec/cm² = ×6.022 × 10¹⁹.
- **INSAT-3D AOD (MOSDAC):** product `3DIMG_L2B_AOD`, **10 km, 30-min (half-hourly),
  HDF5**, variable `AOD` (550 nm); cart/SFTP + VEDAS mirror; **not on GEE**.
  (Original guess of 4 km/hourly corrected to 10 km/30-min.)
- **MAIAC cross-check:** the GEE id requires the `_GRANULES` suffix —
  `MODIS/061/MCD19A2_GRANULES`, band `Optical_Depth_055`, scale 0.001.
- **ERA5-Land** `ECMWF/ERA5_LAND/DAILY_AGGR` bands confirmed; **BLH is absent from
  ERA5-Land** → pulled from ERA5 single-levels via Copernicus CDS (`boundary_layer_height`).
- **Fire/EVI/landcover/DEM** ids confirmed (MaxFRP scale 0.1; EVI scale 0.0001;
  WorldCover v200 `Map`; SRTM `elevation`; FIRMS VIIRS area-API pattern + MAP_KEY).

### 1.2 Surface-pollutant ML (SOTA over India)
- Tree ensembles (RF/XGBoost/stacking) are the workhorses; **CNN-LSTM** wins where
  spatial context matters (benchmark R² ≈ 0.91 / RMSE ≈ 8.2 µg/m³ for PM2.5).
- Consensus feature set: **AOD, BLH, RH, T2m, wind, surface pressure, SSR, NDVI,
  land-use, elevation, fire/FRP, day-of-year + lat/lon** — implemented.
- **SO₂ and CO are intrinsically hard** (low SNR / free-tropospheric decoupling) →
  expect low R²; flagged as low-confidence. Our demo reproduces this.
- **Validation:** random CV overstates skill; **spatial CV RMSE ≈ +48 %**; report
  random / spatial (block / leave-station-out) / temporal separately — implemented
  as the three-scheme framework.

### 1.3 HCHO hotspots & chemistry
- **HCHO qa threshold should be 0.5, not 0.75** (qa > 0.75 discards valid
  high-signal pixels). Config default changed to 0.5 + `cloud_fraction` cap.
- Work on **monthly/seasonal 0.05°–0.1° composites**, not daily (per-pixel noise
  7–12 × 10¹⁵ molec/cm²) — the hotspot pipeline aggregates before detection.
- Detection: PHV (flagship), **Getis-Ord Gi\*** (z > 1.96/2.58/3.29; + FDR), and scipy
  connected-component clusters. Mitigate single-pixel artefacts with composites +
  persistence + significance. _(DBSCAN/P95 were prototyped but removed in the redesign.)_
- **FNR (HCHO/NO₂) thresholds are regional.** India is largely NOₓ-limited; an
  India-applied set is VOC-limited < 3.2 / transition 3.2–4.1 / NOₓ-limited > 4.1.
  Config defaults updated (from the Beijing 2.67/3.47); recommend empirical
  derivation per region/season.

### 1.4 Biomass burning & transport
- Calendar: paddy-stubble **Oct–Nov** (Punjab/Haryana), wheat **Apr–May**, forest
  fires **Feb–Jun**. VIIRS 375 m, FRP > 5 MW threshold.
- **Punjab → Delhi:** fire counts explain **~78 %** of Oct–Nov Delhi AOD variance;
  ~60 % of burn-zone trajectories reach Delhi within 36 h. HYSPLIT/ERA5 back-
  trajectories are the standard attribution tool — implemented (lightweight ERA5
  kinematic back-trajectory + HYSPLIT hook).

### 1.5 CPCB AQI
- All numeric breakpoints in the config **verified correct** against the official
  CPCB 2014 table. **Corrections:** added the missing **Pb** pollutant and updated
  category colours to the official CPCB hex codes. Max-of-sub-index confirmed; the
  Lu 2011 Shannon-entropy aggregation is implemented as a publishable comparison.

---

## 2. System architecture

Mirrors the problem-statement diagram:

```
Objective 1 (AQI):
  INSAT AOD + TROPOMI columns + ERA5 met + landcover/elevation/fire
    -> preprocessing (regrid, QA, collocate) -> features -> RF (+kriging hybrid)
    -> surface PM2.5/PM10/NO2/SO2/CO/O3 -> CPCB AQI engine -> daily/seasonal AQI maps
  Ground truth: CPCB CAAQMS stations.  (CNN-LSTM validated, off the map path.)

Objective 2 (HCHO):
  TROPOMI HCHO + VIIRS/MODIS fire + ERA5 winds + landcover
    -> seasonal composites -> hotspots (PHV / Gi* + connected-component clusters)
    -> source attribution -> wind back-trajectory transport
    -> HCHO hotspot atlas.
```

Full module map is in [`00_overview.md`](00_overview.md); per-phase methodology in
`01`–`15`.

---

## 3. What was implemented

| Layer | Module(s) | Status |
|-------|-----------|--------|
| Config | `config/*.yaml`, `config.py` | ✅ validated, research-corrected |
| Ingestion (GEE) | `ingestion/{sentinel5p,era5,modis_fire,viirs_fire,worldcover,srtm}.py` | ✅ real GEE code (needs `earthengine authenticate`) |
| Ingestion (local) | `ingestion/{insat_aod,cpcb}.py` | ✅ MOSDAC/CPCB readers (need credentials/files) |
| Preprocessing | `preprocessing/{regrid,qa_filter,temporal,collocate}.py` | ✅ runnable |
| Database | `database/{schema,build_db}.py` | ✅ partitioned parquet builder |
| Features | `features/engineering.py` | ✅ FNR feature, lags, interactions, cyclical time |
| Models | `models/{baselines,cnn,cnn_lstm,hybrid,dataset,train}.py` | ✅ RF operational; CNN-LSTM validated, off map path |
| AQI | `aqi/engine.py` | ✅ fully implemented + unit-tested (scalar + vectorised) |
| HCHO | `hcho/{phv,getis_ord,source_attribution,transport}.py` | ✅ implemented + tested (clusters via scipy connected-components) |
| Visualization | `viz/{maps,figures}.py` | ✅ cartopy-optional, offline-safe |
| Dashboard | `dashboard/app.py` | ✅ Streamlit (reads demo outputs) |
| Synthetic harness | `synthetic.py` | ✅ enables credential-free end-to-end run |
| Orchestration | `pipelines/run_demo.py` + `pipelines/01–07` | ✅ `make demo` runs all phases |

---

## 4. Demonstration results (synthetic India data)

`make demo` (0.5° grid, 60 days post-monsoon, 120 CPCB-like stations, 7,200
station-days) runs the full pipeline. *Numbers below are from the synthetic run and
exist to prove the machinery and the scientific logic — not as real-world skill.*

**Surface-pollutant skill (temporal hold-out, RF / XGBoost / CNN-LSTM):**

| Pollutant | RF R² | RF RMSE | XGB R² | CNN-LSTM R² |
|-----------|-------|---------|--------|-------------|
| PM2.5 | 0.86 | 14.9 | 0.87 | 0.81 |
| PM10  | 0.84 | 27.9 | 0.83 | 0.78 |
| NO₂   | 0.93 | 6.3  | 0.93 | 0.91 |
| SO₂   | 0.23 | 7.9  | 0.17 | 0.07 |
| O₃    | 0.47 | 8.5  | 0.47 | 0.26 |
| CO    | 0.62 | 0.43 | 0.61 | 0.59 |

**PM2.5 cross-validation (the leakage lesson):** random R² **0.79**, spatial
(block) R² **−0.15**, temporal R² **0.86**. Spatial ≪ random because the data
embeds an unobserved per-station emission factor — so leave-station-out / block CV
is the honest metric (Wang 2023).

**AQI (peak burning day, 2021-11-13):** CPCB mean **158**, max **409**; RAPI (USP)
mean **224**, mean RAPI−CPCB divergence **66.1**; cells span Satisfactory → Severe
(Moderate 1501, Satisfactory 1039, Poor 921, Very Poor 192, Severe 1).

**HCHO hotspots (burning-window composite):** PHV flags 2.8 % of cells (102 local
anomalies); Getis-Ord Gi* **1102** significant cells; scipy connected-components
group these into **68 clusters**, attributed as biogenic 37, other 17, industrial 10,
urban 3, agri_burning 1.

**Transport:** Delhi 48 h back-trajectory (17 nodes) passes within 150 km of **741**
fire pixels — a clear upwind biomass-burning → receptor link.

**What the results demonstrate (and why they are scientifically right):**
- **PM2.5 and NO₂ are predicted well; SO₂/CO/O₃ are weak** — exactly the
  difficulty ordering the literature reports for column→surface retrieval.
- **Spatial CV ≪ random CV** — the autocorrelation-leakage effect (Wang 2023) is
  reproduced because the generator embeds an unobserved per-station emission factor;
  this is why leave-station-out / block CV is the honest metric.
- **PHV / Gi* flag the Punjab–Haryana burning belt**, and source attribution labels
  them in the post-monsoon window.

Artifacts produced in `outputs/`:
- `maps/` — CPCB + RAPI + divergence AQI, predicted PM2.5, HCHO + hotspots, fire density
- `figures/` — Delhi wind rose
- `*.csv` — attributed hotspots, Delhi back-trajectory
- `demo_summary.md` / `.json` — the consolidated run report

---

## 5. Running on real (operational) data

```bash
make auth                      # earthengine authenticate (one-time)
cp config/config.example.yaml config/config.yaml   # set gee.project, dates, AOI
make ingest                    # S5P/ERA5/fire/landcover/DEM via GEE; INSAT via MOSDAC; CPCB CSVs
make preprocess                # regrid + QA + temporal + collocate
make database                  # unified training table + inference grid
make train                     # CNN-LSTM (+ RF/XGB), 3-scheme validation
make aqi                       # surface pollutants -> AQI -> India atlas
make hcho                      # hotspots + attribution
make transport                 # wind back-trajectory transport
make dashboard                 # Streamlit explorer
```

Credentials/keys required: a GEE Cloud project; a Copernicus CDS account
(`~/.cdsapirc`) for BLH; a MOSDAC login for INSAT AOD; a NASA FIRMS MAP_KEY for
VIIRS; CPCB station CSVs (CCR portal) or an OpenAQ/data.gov.in key.

---

## 6. Evaluation against the problem-statement criteria

| Criterion (problem statement) | Where addressed |
|-------------------------------|-----------------|
| Obj-1 accuracy: RMSE, R, MAE | `models/baselines.metrics`, 3-scheme CV, results table |
| Obj-2 hotspot accuracy/clarity | PHV / Gi* + connected-component clusters + composites + significance/FDR |
| Multi-source integration | unified database (8 datasets co-registered) |
| Scientific interpretation | FNR feature, source attribution, transport attribution |
| Visualization quality | CPCB-coloured AQI maps, HCHO/fire/transport maps, time series |
| Innovation | biomass-burning attribution + transport + explainable DL (beyond AQI+hotspots) |

---

## 7. Limitations & next steps

- **Synthetic stand-in:** results validate machinery, not real skill. First real
  milestone: ingest one season (e.g., Oct–Nov 2021) and retrain.
- **SO₂/CO** will remain low-skill; consider reporting them as advisory only.
- **Daily HCHO** is noisy; keep hotspot detection on monthly/seasonal composites.
- **Transport:** upgrade the kinematic back-trajectory to full **HYSPLIT** ensembles
  for publication-grade attribution.
- **INSAT AOD** ingestion needs a MOSDAC-account scripting step (or MAIAC fallback
  for prototyping).
- **FNR thresholds** should be derived empirically per region/season rather than
  using fixed cut-points.
