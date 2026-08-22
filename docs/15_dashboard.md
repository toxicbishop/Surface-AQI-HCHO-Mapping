# Dashboard — Streamlit Air-Quality & HCHO Explorer

A thin Streamlit front-end that reads **pre-rendered pipeline artifacts** so the UI never does heavy compute — an interactive atlas over INSAT-3D · Sentinel-5P TROPOMI · CPCB · ERA5 · MODIS/VIIRS.

## Objectives
- Single interactive surface to explore daily AQI, pollutants, HCHO hotspots, fire activity, attributed sources, and transport trajectories.
- Stay **stateless and fast**: load images/tables from `outputs/` and `data/processed/`, never recompute.
- Reproducible selectors (date, layer, pollutant, hotspot method, receptor) mapping 1:1 to artifact paths.

## Scientific rationale
The dashboard is the delivery vehicle for every prior phase: it surfaces the HCHO–O₃ regime maps (Phase 12 [A][B]), the back-trajectory source–receptor links (Phase 13 [B]), the SHAP driver attributions (Phase 14 [A], fixing [C]'s met omission), and the attributed hotspots (urban/industrial/agri_burning/forest_fire). Decoupling rendering (pipelines) from presentation (app) keeps results auditable and the UI responsive.

## Input datasets / inputs
Pre-rendered artifacts produced by the pipelines:
- `outputs/maps/aqi_<date>.png`, `outputs/maps/<pollutant>_<date>.png`, `outputs/maps/hcho_<date>.png`, `outputs/maps/fire_<date>.png`.
- `outputs/figures/shap_importance.png`, `outputs/figures/hcho_o3_panel.png`.
- `outputs/tables/hotspots_<date>.csv` (with `source`/`source_detail`), `outputs/tables/hcho_o3_corr.csv`.
- Trajectory overlays `outputs/maps/trajectory_<receptor>_<date>.png` / GeoJSON.
- `config/config.yaml` + `config/regions.yaml` (receptor list).

## Architecture (thin app over artifacts)
`dashboard/app.py` is intentionally thin (see its docstring). It loads config once, builds sidebar controls, then displays the matching pre-rendered artifact. No model inference, no GEE calls, no trajectory math in-process — all of that is upstream in `pipelines/`.

```
pipelines/*  ──writes──▶  outputs/ (PNG, CSV, GeoJSON) ──reads──▶  dashboard/app.py ──▶ browser
config/regions.yaml ─────────────────────────────────────────────┘ (receptor selector)
```

## The 6 tabs / features (layer selector)
- **AQI** — daily AQI map + dominant-pollutant + category legend.
- **Pollutants** — per-pollutant surface maps (PM2.5, PM10, NO₂, SO₂, CO, O₃).
- **HCHO** — HCHO column + hotspots with a **method selector** (PHV / Getis-Ord Gi* / DBSCAN / P95).
- **Fire** — VIIRS/MODIS fire density + FRP.
- **Hotspots** — attributed hotspot table (urban/industrial/agri/forest) + map.
- **Transport** — back-trajectory overlay for a chosen **receptor** (delhi/lucknow/patna/kanpur) and date.

A date selector plus context-sensitive selectors (pollutant / hotspot method / receptor) appear in the sidebar; results render across Map / Statistics / About sub-tabs.

## Wiring / data-flow
Selectors compose an artifact path that the app loads:

```python
with st.sidebar:
    sel_date = st.date_input("Date", value=date(2021, 11, 5))
    layer = st.radio("Layer", ["AQI","Pollutants","HCHO","Fire","Hotspots","Transport"])
    if layer == "HCHO":
        st.selectbox("Hotspot method", ["PHV","Getis-Ord Gi*","DBSCAN","P95"])
    if layer == "Transport":
        receptors = list(cfg.regions.get("receptors", {}).keys()) or ["delhi"]
        st.selectbox("Receptor", receptors)
# render: st.image(f"outputs/maps/aqi_{sel_date}.png")
#         st.image(f"outputs/maps/trajectory_{receptor}_{sel_date}.png")
#         st.dataframe(pd.read_csv(f"outputs/tables/hotspots_{sel_date}.csv"))
```

Example artifact paths: `outputs/maps/no2_2021-11-05.png`, `outputs/maps/trajectory_delhi_2021-11-05.png`, `outputs/tables/hotspots_2021-11-05.csv`.

## Caching
- `@st.cache_resource` for the config/connection singletons (already on `get_config`).
- `@st.cache_data` for artifact loaders (CSV/GeoJSON read, image bytes) keyed on `(layer, date, method, receptor)` so re-selecting a date is instant.
- Cache TTL only if artifacts are regenerated on a schedule; otherwise leave unbounded for static runs.

## Python libraries
`streamlit`, `pandas`, `pyyaml` (config), `pillow`/`matplotlib` (image display), optional `pydeck`/`folium` (interactive maps), `geopandas` (GeoJSON trajectories).

## Code in this repo
`dashboard/app.py` — `get_config` (`@st.cache_resource`), `main` (sidebar controls + tabbed display). Consumes `isro_aqi.config.load_config` and artifacts from `outputs/`. Figures originate in `viz/figures.py` and `viz/maps.py`; tables in `outputs/tables/`.

## Deployment notes
- **Local**: `streamlit run dashboard/app.py` (after `pip install -e .` / `environment.yml`).
- **Streamlit Community Cloud**: point at repo + `dashboard/app.py`; commit a `requirements.txt`; ship a lightweight `outputs/` sample or fetch from object storage at startup (don't run full pipelines on the host).
- **Docker**: `FROM python:3.11-slim`, install requirements, `EXPOSE 8501`, `CMD ["streamlit","run","dashboard/app.py","--server.address=0.0.0.0"]`; mount `outputs/` as a volume.
- Run pipelines (incl. `pipelines/07_transport.py`) **offline** to (re)generate artifacts; the app only reads them.

## Expected outputs
A browser app: pick a date/layer → see the corresponding map, statistics panel, and (for Hotspots/Transport) tables and trajectory overlays — a self-serve atlas of all phases' results.

## Potential challenges & mitigations
- **Missing artifact for a date** → guard with existence checks and a friendly `st.info` fallback (as in the stub).
- **Large images/tables** → downsample/tile maps; paginate tables; lean on `@st.cache_data`.
- **Cloud cold storage** → lazy-fetch artifacts from object storage; cache locally per session.
- **Config drift** → single source of truth in `config/regions.yaml` for receptors/regions.

## Validation metrics
Artifact-coverage check (every selectable date/layer resolves to a file); load latency per tab (target < 1 s warm cache); selector→path mapping unit-tested; visual parity of in-app figures vs `viz/` originals.

## Publication-quality figures
The dashboard surfaces the same publication figures generated upstream: `viz/figures.py:hcho_o3_panel`, `importance_bar`, `scatter_obs_pred`, and `viz/maps.py` AQI/HCHO/fire/trajectory maps — embedded read-only via `st.image`.
