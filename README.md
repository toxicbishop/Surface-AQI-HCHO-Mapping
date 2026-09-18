<div align="center">

# VayuDrishti

### Satellite-Derived Surface AQI & HCHO Hotspot Detection over India

*Bharatiya Antariksh Hackathon 2026 · Challenge 03*

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js_16-000000?logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Google Earth Engine](https://img.shields.io/badge/Google_Earth_Engine-4285F4?logo=googleearth&logoColor=white)
![Sentinel--5P](https://img.shields.io/badge/Sentinel--5P-TROPOMI-0072CE)
![Random Forest](https://img.shields.io/badge/Model-Random_Forest-brightgreen)
![CNN--LSTM](https://img.shields.io/badge/Model-CNN--LSTM-yellowgreen)
![deck.gl](https://img.shields.io/badge/deck.gl-MapLibre-8A2BE2)
![pnpm](https://img.shields.io/badge/pnpm-F69220?logo=pnpm&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

</div>

---

> **Built on [VAYU](https://github.com/akshhkaushik/vayu-aqi-hcho)** by
> **[akshhkaushik](https://github.com/akshhkaushik)**. VayuDrishti is an adapted and extended
> version of that repository — the core AQI/HCHO pipeline and frontend architecture are theirs.
> See [Credits](#credits) below for exactly what was inherited vs. added.

---

## What is this

VayuDrishti estimates ground-level pollutant concentrations and daily Air Quality Index (AQI)
across India from satellite data, and separately detects, attributes, and traces formaldehyde
(HCHO) hotspots tied to VOC emissions and biomass burning — all surfaced through an interactive
scrollytelling web map.

It answers three questions:

1. **Surface AQI** — can satellite observations predict ground-level pollution and generate daily AQI maps across India?
2. **HCHO hotspots** — can TROPOMI HCHO identify VOC emission hotspots and biomass-burning episodes?
3. **Source attribution** — how much do crop-residue burning, forest fires, and long-range transport contribute to HCHO enhancement?

![VayuDrishti Dashboard](public/dashboard.gif)
*Interactive dashboard — surface AQI, HCHO hotspots, biomass burning dynamics, and atmospheric back-trajectories.*

---

## Highlights

| | |
|---|---|
| **Surface AQI** | Random Forest, optionally hybridized with regression-kriging on station residuals |
| **Official AQI** | Deterministic CPCB engine (piecewise-linear sub-indices, max rule) |
| **Alternate index** | Entropy-weighted RAPI + RAPI−CPCB divergence map |
| **HCHO evidence** | PHV + Getis-Ord Gi* → connected clusters → source attribution → back-trajectory transport |
| **Pollution zoning** | K-Means, silhouette-selected K, relative severity zones *(added in this fork)* |
| **Anomaly baseline** | Isolation Forest, compared against PHV/Gi* via Jaccard overlap *(added in this fork)* |
| **Frontend** | Next.js 16 + deck.gl + MapLibre, GPU-rasterized gridded fields, no Mapbox token |

---

## Pipeline

```
 INSAT/MAIAC AOD ─┐  gap-fill (RF)      ┌─ trend μ : Random Forest (per pollutant)
 TROPOMI gases ───┤  NO2 calibration    │            +
 ERA5 met ────────┼──▶ gridded backbone ┤  resid v : kriged station residuals
 CPCB / OpenAQ ───┤  + engineered feats └─▶ C(s,t)=μ+v ─▶ AQI engine ─▶ daily maps
 Land cover / DEM ┤                              │
 Fire counts ─────┘                       CPCB AQI (max-rule) + RAPI (entropy) + divergence

 TROPOMI HCHO ──┐
 VIIRS/MODIS ───┤
 ERA5 winds ────┼─▶ PHV + Getis-Ord Gi* ─▶ connected clusters ─▶ source attribution ─▶ transport
 Land cover ────┘
```

Surface concentrations: **Random Forest**, used bare per-pollutant on the real-data path, or as
the trend term `μ` in a regression-kriging hybrid `C(s,t) = μ + v` (Gaussian-kernel kriging of
station residuals, fading to zero away from monitors). A **CNN-LSTM** is implemented and
validated as the "recommended" learner but is not yet on the map-generation path. Concentration
grids convert to AQI via the deterministic CPCB engine, plus the entropy-weighted RAPI index.

Full internals: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (§2–§4 model details, §12 an
honest list of what's real vs. showcased).

---

## Validation

Random Forest trained on real OpenAQ/CPCB ground truth vs. GEE satellite predictors —
~158 stations · ~4,300 station-days · Oct–Dec 2025, reported under **dual cross-validation**:

| Pollutant | Random-CV R² (interpolation) | Spatial-CV R² (unseen regions) |
|---|---|---|
| PM2.5 | 0.53 | 0.03 |
| PM10  | 0.58 | 0.02 |
| NO₂   | 0.71 | −0.15 |
| O₃    | 0.66 | — |
| SO₂   | 0.46 | −0.96 |
| CO    | 0.69 | 0.19 |

The gap between random and spatial CV is intentional: **random CV** measures skill at *known*
stations (held-out days); **spatial CV** measures *extrapolation* to unmonitored regions
(held-out 2°×2° blocks) — exposing spatial-autocorrelation leakage (Wang 2023).

Full results: [`outputs/real_validation.json`](outputs/real_validation.json)

---

## Getting started

<details>
<summary><strong>Run the website</strong></summary>

```bash
pnpm install
pnpm dev        # http://localhost:3000 — reads public/data/*.json
```

This project uses **pnpm** exclusively — not npm.
</details>

<details>
<summary><strong>Run the research pipeline</strong></summary>

```bash
# Setup virtual environment & dependencies
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# or: .venv\Scripts\activate    # On Windows PowerShell / Git Bash

pip install -e .
pip install -r requirements.txt

# Try it immediately — synthetic India data, no credentials needed
make demo                 # -> outputs/: AQI maps, HCHO hotspots, figures, demo_summary.md
make demo-fast            # quick smoke version; also emits zones, anomalies, and metadata

# For real data
make check-ingest         # readiness check: packages, GEE/CDS/FIRMS creds, config
earthengine authenticate  # one-time GEE auth

OPENAQ_API_KEY=... make real   # real CPCB/OpenAQ-validated AQI + dual CV
make fetch-web                 # real TROPOMI/MODIS/ERA5 layers -> public/data/*.json
```

| Target | Command | Purpose |
|---|---|---|
| `make demo` | `python pipelines/run_demo.py` | Full synthetic end-to-end simulation, no credentials required |
| `make demo-fast` | `python pipelines/run_demo.py --fast` | Quick smoke run; generates comparative layers & JSON exports |
| `make real` | `python pipelines/run_real.py` | Real OpenAQ/CPCB-validated AQI + dual CV |
| `make fetch-web` | `python pipelines/fetch_real_web.py` | Real satellite observation layers → web |
| `make check-ingest` | `python pipelines/check_ingest.py` | Pre-flight readiness check for APIs and credentials |
| `make dashboard` | `streamlit run dashboard/app.py` | Streamlit interactive research dashboard |
| `make test` / `make lint` | `pytest -q` / `ruff check` | Deterministic AQI, PHV, Gi*, K-Means, and Isolation Forest test suite |

*Note on cross-platform execution:* The `Makefile` automatically invokes `python` (overridable with `make demo PY=python3`), functioning cleanly across Windows (Git Bash/PowerShell), macOS, and Linux.
</details>

---

## Structure

```
# Web Application (Next.js 16 + React 19 + Turbopack)
src/app/           routes: / aqi case-study hcho impact method model problem
src/components/    DeckMap (deck.gl + MapLibre), sections, IndiaField, Pipeline, ...
src/lib/           chapters, geo utilities, cell context, animation hooks
public/data/       GeoJSON and precomputed analysis grids (AQI, HCHO, zones, fires)

# Python Research Pipeline & Models
config/            YAML configurations (AOI, dates, assets, AQI breakpoints, regions)
docs/              ARCHITECTURE.md, 15-phase blueprint (00-15_*.md), references
src/isro_aqi/
  ingestion/       GEE (Sentinel-5P, ERA5, MODIS/VIIRS, WorldCover, SRTM) + CPCB/OpenAQ + INSAT
  preprocessing/   regrid, QA filter, AOD gap-fill, NO2 calibration, collocation, temporal
  database/        unified (date, lat, lon) schema + parquet builder
  features/        engineered predictors (FNR, cyclical DOY, interactions)
  models/          RF, XGBoost, CNN, CNN-LSTM, regression-kriging hybrid, K-Means zoning
  aqi/             CPCB AQI sub-index + RAPI entropy engine
  hcho/            PHV, Getis-Ord Gi*, Isolation Forest, source attribution, back-trajectory
  viz/             maps & publication figures
  synthetic.py     physically-plausible synthetic India generator
pipelines/         CLI entry points — run_demo, run_real, fetch_real_web, export_web, 01–07
tests/             unit tests — AQI engine, PHV, Gi*, K-Means, Isolation Forest
outputs/           generated maps, figures, real_validation.json, demo_summary.md
```

**Compute Split:**
- *Server-side (Google Earth Engine):* Sentinel-5P, ERA5(-Land), MAIAC AOD, MODIS/VIIRS fire, ESA WorldCover, SRTM — filtered, reduced, exported as analysis-ready rasters/tables.
- *Local Machine:* CPCB/OpenAQ station data, database assembly, model training, AQI computation, HCHO analysis, figures, JSON export.

**Web Data Contract:**
The web layer consumes static layers from `public/data/`: `aqi_frames.json`, `gas_grids.json`, `hcho_grid.json`, `hotspots.json`, `fires.json`, `delhi_backtrajectory.json`, `india.geojson`, `zone_cells.json`, `isolation_hotspots.json`, and `analysis_metadata.json`.

---

## Documentation

The scientific blueprint and engineering documentation live in [`docs/`](docs/):
- [`docs/00_overview.md`](docs/00_overview.md) — Master overview and roadmap.
- [`docs/01_literature_review.md`](docs/01_literature_review.md) … [`docs/15_dashboard.md`](docs/15_dashboard.md) — 15-phase scientific implementation blueprint.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Exhaustive architecture, actual vs. showcased models, and code walkthrough.
- [`docs/references.md`](docs/references.md) — Full scientific bibliography and anchor paper citations.

---

## Credits

VayuDrishti is an adapted and extended version of **[VAYU](https://github.com/akshhkaushik/vayu-aqi-hcho)**
by **[akshhkaushik](https://github.com/akshhkaushik)**. Full credit to the original author for the
foundation this project is built on.

**Inherited from VAYU:**
Random Forest / regression-kriging pollutant models · deterministic CPCB AQI engine · RAPI index
· PHV and Getis-Ord Gi* HCHO detection · source attribution · back-trajectory analysis · core Next.js + MapLibre + deck.gl visualization architecture.

**Added in this fork:**
- **K-Means pollution zoning** (`src/isro_aqi/models/zones.py`) — silhouette-selected K, relative severity zones, explicitly not official CPCB categories.
- **Isolation Forest hotspot comparison** (`src/isro_aqi/hcho/isolation_forest.py`) — multivariate anomaly baseline compared against PHV/Gi* via Jaccard overlap.
- **Shared analysis-layer output contract** (`src/isro_aqi/analysis_layers.py`) with method/data-status metadata.
- **New frontend modes & UX enhancements**: K-Means zones, Isolation Forest anomalies, PHV-vs-Isolation Forest comparison, refined typography, and responsive model workflow diagrams.
- **Modernized dependency & build stack**: pnpm-standardized Next.js 16 Turbopack pipeline, cross-platform Makefile, and updated MapLibre v6 integration.

Official AQI and PHV/Gi* hotspot evidence remain primary and unchanged from VAYU. K-Means and
Isolation Forest are additional, clearly-labeled comparative views layered on top.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
