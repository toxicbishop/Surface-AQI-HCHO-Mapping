# Surface AQI & HCHO Hotspot Detection over India — Detailed Project Plan

## 1. Scope Decision (read this first)

This plan works at two speeds:
- **Sprint mode (24–48h hackathon):** Sections marked `[MVP]` only. Skip Isolation Forest tuning, skip mobile alerts, use a pre-trained baseline where possible.
- **Extended mode (post-hackathon, portfolio-grade):** Everything, including the Future Scope items, CI/CD, and a deployed live dashboard.

Pick your track before starting — it changes what "done" means for each phase below.

---

## 2. System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Data Sources    │────▶│  Processing/ML    │────▶│  Presentation      │
│                  │     │                   │     │                    │
│ Sentinel-5P (GEE)│     │ Merge & clean     │     │ Streamlit dashboard│
│ CPCB stations    │     │ Feature engineer  │     │ Folium heatmaps    │
│ (optional: ERA5  │     │ RF Regression     │     │ Plotly time-series │
│  weather data)   │     │ K-Means zones      │     │ Hotspot alert list │
└─────────────────┘     │ Isolation Forest  │     └───────────────────┘
                          └──────────────────┘
```

Data flow: raw satellite rasters → tabular grid (lat/lon/time indexed) → joined with CPCB ground truth → model training → predictions written back to a grid → rendered as map layers.

---

## 3. Phase 1 — Data Acquisition & Preprocessing `[MVP]`

### 3.1 Satellite data (Sentinel-5P via Google Earth Engine)
- Bands needed: `TROPOSPHERIC_HCHO_COLUMN_NUMBER_DENSITY`, `NO2_column_number_density`, `CO_column_number_density`.
- Use `COPERNICUS/S5P/OFFL/L3_HCHO`, `L3_NO2`, `L3_CO` collections.
- Define an India bounding box (68°E–97°E, 6°N–37°N) and clip all imagery to it.
- Temporal resolution: daily composites; aggregate to weekly or monthly means to reduce cloud-cover gaps (HCHO retrievals are noisy on a daily basis).
- Export as a regular grid (e.g., 0.05° or ~5km resolution) using `ee.Image.reduceRegion` or export to Google Drive as GeoTIFF, then load with `rasterio`/`geopandas`.

### 3.2 Ground truth (CPCB)
- Pull station-level PM2.5, PM10, NO2, SO2, CO, O3 from the [CPCB CAAQMS portal](https://cpcb.nic.in) or the `data.gov.in` AQI API/bulk CSVs.
- Each station has a lat/lon — this becomes your regression target (AQI) and your validation anchor points for HCHO.
- Compute the official CPCB AQI sub-index formula per pollutant, then take the max sub-index (standard method) rather than inventing your own composite score — this is defensible to judges who know the domain.

### 3.3 Merge strategy
- Spatial join: for each CPCB station, extract the nearest satellite grid cell (or interpolate from the 4 nearest cells — bilinear).
- Temporal join: match satellite composite window to the CPCB reading date/week.
- Output: one row per (station, time) = `[lat, lon, date, HCHO, NO2, CO, PM2.5, PM10, AQI_ground_truth]`.
- **Known problem to flag proactively in your pitch:** CPCB stations are urban-biased (~500 stations, mostly cities). Your model will be extrapolating into rural/industrial zones it never saw ground truth for — call this out as a stated limitation rather than letting a judge catch it.

### 3.4 Feature engineering
Beyond raw pollutant columns, add:
- Day-of-year / season (winter stubble-burning season matters a lot for HCHO in North India)
- Land-use category if available (urban/agricultural/industrial) — can pull from a static land-cover raster (ESA WorldCover) as a categorical feature
- Population density (WorldPop) as a proxy for source strength
- Rolling 7/30-day mean of each pollutant column (captures persistence)

---

## 4. Phase 2 — Machine Learning Models

### 4.1 Random Forest Regression — Surface AQI prediction `[MVP]`
- Target: CPCB-derived AQI.
- Features: satellite pollutant columns + engineered features from 3.4.
- Train/test split: **spatial** split, not random row split — hold out entire stations/regions for testing, or you'll get inflated R² from spatial autocorrelation (a classic mistake judges will probe).
- Baseline hyperparameters to start: `n_estimators=300`, `max_depth=15`, `min_samples_leaf=5`. Tune with `RandomizedSearchCV` if time allows.
- Metrics: RMSE, MAE, R² — report per-region (urban vs non-urban) since performance will differ.

### 4.2 K-Means Clustering — Pollution zone segmentation `[MVP]`
- Cluster grid cells on the predicted AQI surface (plus HCHO/NO2 levels) into 4–5 zones: Good / Moderate / Poor / Severe / Hazardous.
- Use elbow method or silhouette score to justify `k`, don't just hardcode k=4 without showing the justification — it's a 2-minute addition that reads as rigor.
- Alternative if you want it to look more novel: cluster on the *feature vector* (HCHO+NO2+CO+season) rather than on AQI directly, so zones reflect pollution *character* (e.g., biomass-burning zone vs traffic zone) not just severity.

### 4.3 Isolation Forest — HCHO anomaly/hotspot detection
- Train on HCHO column density grid (+ optionally NO2 as a co-feature, since pure biomass burning tends to show a different NO2:HCHO ratio than industrial sources).
- `contamination` parameter ~0.05–0.1 to flag the top anomalous cells as hotspots.
- Post-process: cluster contiguous anomalous cells (e.g., `scipy.ndimage.label`) so you report "hotspot regions" not just scattered pixels — much better for a map visualization.
- Cross-check flagged hotspots against known sources (industrial clusters, NCR stubble-burning belt) as a sanity/validation step — this becomes a strong slide ("our model independently rediscovered the known Punjab-Haryana stubble corridor").

---

## 5. Phase 3 — Visualization & Dashboard `[MVP for a basic version]`

### 5.1 Streamlit app structure
```
app.py
├── Sidebar: date range picker, pollutant selector, zone filter
├── Tab 1: India AQI heatmap (Folium, choropleth or gridded heatmap)
├── Tab 2: HCHO hotspot map (markers/polygons on flagged regions)
├── Tab 3: Time-series trends (Plotly, per-region or per-station)
└── Tab 4: Model performance / methodology (for judge credibility)
```
- Folium: use `folium.plugins.HeatMap` for continuous AQI surface, and `folium.GeoJson` with color-coded polygons for the K-Means zones.
- Cache expensive operations with `@st.cache_data` — GEE calls and model inference should not re-run on every widget interaction.
- Keep the map load fast: pre-compute and store the gridded predictions as a static file (Parquet/GeoJSON) rather than calling GEE live during the demo — live GEE calls during a hackathon judging session are a reliability risk.

### 5.2 What makes the dashboard demo well
- Default view should load pre-computed data instantly, not trigger a live API call.
- One clear "headline" visual on load (India-wide AQI heatmap), details behind tabs.
- Add a short methodology tab — judges often reward transparency about limitations (CPCB coverage gaps, satellite retrieval noise) over an over-confident pitch.

---

## 6. Repository Structure

```
aqi-hcho-satellite-india/
├── README.md                 # problem, approach, results, screenshots, how to run
├── data/
│   ├── raw/                  # gitignored — raw GEE exports, CPCB CSVs
│   └── processed/            # merged grid, train/test splits (small samples OK to commit)
├── notebooks/
│   ├── 01_data_acquisition.ipynb
│   ├── 02_preprocessing_merge.ipynb
│   ├── 03_rf_aqi_model.ipynb
│   ├── 04_kmeans_zones.ipynb
│   └── 05_isolation_forest_hotspots.ipynb
├── src/
│   ├── gee_extract.py
│   ├── cpcb_loader.py
│   ├── features.py
│   ├── models.py
│   └── evaluate.py
├── dashboard/
│   └── app.py
├── outputs/
│   ├── figures/
│   └── model_artifacts/      # saved .pkl models
├── requirements.txt
└── LICENSE
```

---

## 7. Timeline

### Hackathon sprint (assume ~36 active hours across the event)
| Block | Hours | Task |
|---|---|---|
| 1 | 0–4 | GEE account setup, pull HCHO/NO2/CO for India, pull CPCB data, initial merge |
| 2 | 4–10 | Clean merged dataset, feature engineering, EDA plots |
| 3 | 10–16 | Random Forest AQI model, spatial train/test split, evaluate |
| 4 | 16–20 | K-Means zone clustering |
| 5 | 20–26 | Isolation Forest hotspot detection + hotspot region clustering |
| 6 | 26–32 | Streamlit dashboard (all 4 tabs), pre-computed data caching |
| 7 | 32–36 | README, screenshots, pitch deck, rehearse demo, buffer for bugs |

### Extended/portfolio track (post-hackathon, ~3–4 weeks part-time)
| Week | Focus |
|---|---|
| 1 | Rebuild pipeline properly: automate GEE pulls, add ERA5 weather covariates, proper data versioning |
| 2 | Model rigor: hyperparameter tuning, spatial cross-validation, add SO2/O3 targets from Future Scope |
| 3 | Deploy dashboard live (Streamlit Community Cloud or Railway), add CI (lint + basic tests on `src/`), write a short technical report |
| 4 | NCAP alignment write-up, mobile-alert stub (even a simple email/webhook alert on new hotspot detection counts as delivering that Future Scope item), polish README with real screenshots + metrics table |

---

## 8. Validation & Credibility Checklist (what separates a good submission from a generic one)

- [ ] Spatial (not random) train/test split, explicitly justified
- [ ] Reported metrics broken down by region type (urban vs rural/industrial), not just one aggregate R²
- [ ] Explicit statement of CPCB coverage limitation and how it affects the AQI surface confidence away from stations
- [ ] Isolation Forest hotspots cross-validated against at least one known real-world source (e.g., stubble-burning belt, a known industrial cluster)
- [ ] Dashboard loads from pre-computed data by default (no live-call fragility during demo)
- [ ] Clear NCAP policy tie-in in the pitch (judges at an ISRO hackathon respond well to explicit alignment with a named government programme)

---

## 9. Immediate Next Actions

1. Set up Google Earth Engine access (if not already done) and confirm quota for the India bounding box export.
2. Pull a small CPCB sample (even 1 month, 20 stations) to validate the merge logic before scaling up.
3. Decide track (sprint vs extended) so the team isn't debating scope mid-build.

If you want, I can also draft the `README.md` skeleton or the actual `gee_extract.py` / `cpcb_loader.py` starter scripts next.
