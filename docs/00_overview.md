# Phase 0 — Project Overview & Blueprint

The master map for the project. Read this first; each phase doc (`01`–`15`) is the
manual for one stage. Equations, code references and figures live in the phase docs.

---

## 1. What we are building

A research-grade system that turns satellite, reanalysis and ground data into two
deliverables:

1. **Daily surface-AQI maps of India** — deep-learning estimates of surface PM2.5,
   PM10, NO₂, SO₂, CO and O₃ from satellite + meteorology + static predictors,
   passed through the CPCB AQI engine.
2. **An HCHO Hotspot Atlas** — TROPOMI formaldehyde hotspots detected, attributed
   to sources (urban / industrial / agricultural-burning / forest-fire), and traced
   upwind with transport analysis.

### Research questions

| # | Objective | Question |
|---|-----------|----------|
| 1 | Surface AQI | Can satellite observations predict ground-level pollution and generate daily AQI maps across India? |
| 2 | HCHO hotspots | Can TROPOMI HCHO identify VOC emission hotspots and biomass-burning episodes? |
| 3 | Attribution (novel) | How much do crop-residue burning, forest fires and long-range transport contribute to HCHO enhancement? |

### Headline novelty

> Satellite-derived AQI mapping **+** HCHO hotspot detection **+** biomass-burning
> attribution **+** atmospheric transport analysis **+** a dual AQI index (CPCB max +
> entropy RAPI) — a combination none of the four reference papers attempt together.

---

## 2. Scientific grounding (reference papers)

The blueprint is anchored in four papers (full citations in
[`references.md`](references.md)); they are cited inline throughout as:

- **[A]** Dong et al. 2026 (*Atmosphere*) — the **PHV/HVA** HCHO-hotspot method.
- **[B]** Kuttippurath et al. 2022 (*Environmental Challenges*) — **HCHO sources over
  India** and biomass-burning attribution.
- **[C]** Wang et al. 2023 (*Environment International*) — high-resolution
  **spatiotemporal pollutant + AQI** modelling and the **CV benchmarks** we target.
- **[D]** Lu et al. 2011 (*Building & Environment*) — the **entropy-based AQI** (RAPI)
  alternative to max-of-sub-index.

Each phase doc states explicitly what it reuses from these papers and where it
**extends beyond** them (e.g. Getis-Ord Gi* and connected-component clustering are
our additions to the PHV method; transport analysis is the differentiator that [B]
only discusses qualitatively).

---

## 3. Architecture

```
 CPCB stations ─┐  (ground truth / targets)
 INSAT-3D AOD ──┤
 TROPOMI gases ─┤
 ERA5 + BLH ────┼─▶ preprocessing ─▶ feature eng. ─▶ RF (+kriging) ─▶ surface pollutants ─▶ AQI engine ─▶ Daily AQI maps
 Land cover ────┤        (Phase 4)      (Phase 5)    (Phase 6-7)       (Phase 6)         (Phase 8)      (Phase 9)
 Elevation ─────┤                                    [CNN-LSTM validated, off map path]
 Fire / EVI ────┘

 TROPOMI HCHO ──┐
 VIIRS fires ───┤
 ERA5 winds ────┼─▶ hotspot detection ─▶ source attribution ─▶ transport ─▶ HCHO Atlas
 Land cover ────┘   PHV / Gi* + clusters   (Phase 10)       (Phase 13)
                       (Phase 10)
                                                            ─▶ dashboard (Streamlit)
```

---

## 4. Phase map

| Phase | Doc | What it produces |
|-------|-----|------------------|
| 1 | [01_literature_review](01_literature_review.md) | Positioning vs. [A]–[D]; the gap we fill |
| 2 | [02_data_collection](02_data_collection.md) | 8 datasets pulled (GEE + MOSDAC + CPCB + CDS) |
| 3 | [03_database_design](03_database_design.md) | Unified ~50–100 M-row table |
| 4 | [04_preprocessing](04_preprocessing.md) | Co-registered, QA-screened, collocated stack |
| 5 | [05_feature_engineering](05_feature_engineering.md) | FNR, lags, interactions, cyclical time |
| 6 | [06_models](06_models.md) | RF / XGBoost / CNN / **CNN-LSTM** + regression-kriging hybrid (RF is operational) |
| 7 | [07_training_validation](07_training_validation.md) | random/spatial/temporal CV framework |
| 8 | [08_aqi_engine](08_aqi_engine.md) | CPCB sub-index + AQI engine (tested) |
| 9 | [09_aqi_mapping](09_aqi_mapping.md) | Daily→annual **India AQI Atlas** |
| 10 | [10_hcho_hotspots](10_hcho_hotspots.md) | PHV / Gi* + connected-component clusters |
| 11 | [11_biomass_burning](11_biomass_burning.md) | Fire density maps, burning belts |
| 12 | [12_hcho_ozone](12_hcho_ozone.md) | ⚠️ deprecated (ozone_relationship removed); FNR kept as feature |
| 13 | [13_transport_analysis](13_transport_analysis.md) | Back-trajectories, source→receptor |
| 14 | [14_explainability](14_explainability.md) | ⚠️ deprecated (SHAP not implemented) |
| — | [15_dashboard](15_dashboard.md) | Streamlit explorer |
| — | [references](references.md) | Bibliography + dataset citations |

---

## 5. Compute model

- **Server-side (Google Earth Engine):** Sentinel-5P, ERA5-Land, MODIS/VIIRS fire,
  ESA WorldCover, SRTM — filtered and reduced to analysis-ready exports.
- **Local:** INSAT-3D AOD (MOSDAC), CPCB CSVs, database assembly, model training
  (PyTorch, CUDA/MPS/CPU), AQI computation, HCHO analysis, figures, dashboard.
- **Copernicus CDS:** ERA5 boundary-layer height (not in ERA5-Land).

## 6. Repository layout

See the top-level [`README.md`](../README.md) for the directory tree and quick-start.
Deterministic, mathematically-closed components (**AQI engine, PHV, Getis-Ord Gi*,
regression-kriging hybrid**) are fully implemented and unit-tested (`tests/` — 37
tests across 9 files); data-dependent stages (ingestion, preprocessing, training)
are implemented as runnable modules wired by the `pipelines/` CLIs.

## 7. Suggested milestones

1. **M1 — Foundation:** repo + config + AQI/PHV engines tested *(this scaffold).*
2. **M2 — Data & storage:** ingestion → unified database in a bucket (Phases 2–3).
3. **M3 — Modelling:** CNN-LSTM + baselines, 3-scheme validation (Phases 4–7).
4. **M4 — AQI atlas:** daily→annual maps (Phases 8–9).
5. **M5 — HCHO science:** hotspots → attribution → ozone → transport (Phases 10–13).
6. **M6 — Dashboard + web + paper** (Phase 15).

> Publication target: an ISRO student project + a journal/conference paper on
> *satellite-derived AQI with HCHO hotspot attribution and transport over India*.
