# Phase 11 — Biomass-Burning Detection & Fire Maps

Identify pyrogenic HCHO/aerosol sources over India from MODIS/VIIRS fires, separate them from biogenic emissions, and quantify trends — anchored to Kuttippurath et al. 2022 [B].

## Objectives
- Map active fires, FRP and burned area over India and link them to HCHO enhancements [B].
- Separate **pyrogenic** (fire) from **biogenic** (vegetation) HCHO using fire/FRP vs EVI proxies.
- Use the **COVID-lockdown natural experiment** to isolate non-anthropogenic sources [B].
- Quantify long-term trends with robust statistics.

## Scientific rationale
Kuttippurath et al. 2022 [B] attribute **>70% of India's HCHO emissions (2014)** to biomass burning, using MODIS fire-count + FRP (0.5°) as the pyrogenic proxy and EVI as the biogenic proxy, with ERA5 winds for dispersion. Burning is seasonal and regional: crop residue over **Punjab, Haryana, MP, Chhattisgarh, Odisha** (post-monsoon Oct–Nov paddy; pre-monsoon Apr–May wheat) and forest fires over **NE India / Uttarakhand / Western Ghats** (Feb–Mar). The 2020 lockdown suppressed anthropogenic activity while fires continued, giving a clean attribution lever.

## Input datasets
- **MODIS** — MOD14A1 active fire (MaxFRP, FireMask), MCD64A1 burned area, MOD13A2 EVI (`ingestion/modis_fire.py`).
- **VIIRS 375 m** — FIRMS API (VNP14IMGTDL_NRT) for small stubble fires MODIS misses (`ingestion/viirs_fire.py`).
- **ERA5 winds** (`ingestion/era5.py`) for dispersion/back-trajectory context.
- **TROPOMI HCHO** (qa>0.75) from Phase 10; **`config/regions.yaml`** burning belts + seasons.

## Algorithm / workflow
1. Ingest active fire/FRP, burned area and EVI; grid to 0.5° [B]; fetch VIIRS 375 m near receptors.
2. Build pyrogenic (fire-count, FRP, burned area) and biogenic (EVI) proxies.
3. Regress/correlate HCHO against both proxies seasonally and per burning region.
4. Run the COVID natural experiment: compare pre-lockdown (Mar 2020), lockdown (Apr–Jun), unlock (Jul–Sep).
5. Estimate per-pixel trends (Theil-Sen + Mann-Kendall) over the full record.
6. Render fire-density and FRP maps; overlay on HCHO hotspots.

## Mathematical formulation
Theil-Sen slope (robust trend):
```
β = median_{i<j} ( x_j − x_i ) / ( t_j − t_i )
```
Mann-Kendall statistic & significance (|Z|>1.96 ⇒ significant at 95%):
```
S = Σ_{i<j} sign(x_j − x_i)
Var(S) = [ n(n−1)(2n+5) − Σ_g t_g(t_g−1)(2t_g+5) ] / 18
Z = (S−1)/√Var(S) if S>0 ;  0 if S=0 ;  (S+1)/√Var(S) if S<0
```
Pyrogenic vs biogenic apportionment (proxy regression):
```
HCHO ≈ a·FRP + b·EVI + c       # a→pyrogenic, b→biogenic
```

## Python libraries
`earthengine-api` (MODIS via GEE), `requests`/`pandas` (FIRMS API), `xarray`, `numpy`, `pymannkendall` / `scipy.stats` (Theil-Sen, Mann-Kendall), `cartopy`/`matplotlib`.

## Code in this repo
`src/isro_aqi/ingestion/modis_fire.py` (`active_fire_frp`, `burned_area`, `evi`, `export_period`), `viirs_fire.py` (`fetch_firms_api` 375 m, `gridded_fallback`); maps in `viz/maps.py` (`fire_density_map`); regions in `config/regions.yaml`. Driver: `pipelines/06_hcho_analysis.py`.

```python
def active_fire_frp(cfg, start, end):
    coll = ee.ImageCollection(spec["asset"]).select("MaxFRP")\
             .filterDate(start, end).filterBounds(aoi_geometry(cfg))
    frp = coll.map(lambda i: i.divide(10.0))     # MaxFRP/10 -> MW
    return ee.Image.cat(frp.mean().rename("frp_mean"),
                        frp.max().rename("frp_max"),
                        coll.count().rename("fire_count"))
```

## Expected outputs
- Fire-count, FRP, burned-area and EVI rasters (0.5°) + VIIRS 375 m point fires.
- Seasonal fire-density maps for crop-residue and forest-fire belts.
- COVID-window HCHO comparison (pre/lockdown/unlock) quantifying non-anthropogenic share.
- Per-pixel Theil-Sen slope + Mann-Kendall significance maps; pyrogenic share toward the >70% benchmark [B].

## Potential challenges & mitigations
- **MODIS misses small stubble fires** → VIIRS 375 m supplement [B].
- **Cloud/smoke gaps in HCHO** → qa>0.75 + temporal compositing; report coverage.
- **Confounded anthropogenic/biogenic signals** → COVID natural experiment + FRP/EVI regression [B].
- **Autocorrelation in trends** → Mann-Kendall (non-parametric) with tie correction; |Z|>1.96 gate.

## Validation metrics
- HCHO–FRP and HCHO–fire-count correlations by season/region.
- Lockdown vs pre-lockdown HCHO ratio in burning vs urban belts.
- Theil-Sen/Mann-Kendall slope significance maps; pyrogenic apportionment vs the >70% [B] figure.

## Publication-quality figures
- Seasonal fire-density map over India (`fire_density_map`) with burning-belt boxes.
- FRP-vs-HCHO scatter coloured by season/region.
- Three-panel COVID comparison (pre / lockdown / unlock) of HCHO over Punjab–Haryana.
- Theil-Sen trend map with Mann-Kendall significance stippling.
