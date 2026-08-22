# Phase 4 — Preprocessing

Convert heterogeneous satellite, meteorological, static and ground inputs into a single co-registered, quality-controlled, temporally-composited analysis cube ready for feature engineering and modelling.

## Objectives
- Resample every source (INSAT-3D AOD ~10 km, Sentinel-5P/TROPOMI ~1 km, OMI, ERA5 ~0.1°, WorldCover 10 m, SRTM) onto **one** regular EPSG:4326 grid so they become co-registered tensors.
- Apply quality control: TROPOMI `qa_value > 0.75` screening, physical-range clipping, and statistical-outlier removal.
- Composite to daily / monthly / seasonal / annual levels on the IMD seasonal calendar.
- Collocate gridded predictors with CPCB stations to build the supervised long-format training table.

## Scientific rationale
Surface-pollutant retrieval models are only as good as their input alignment: a 1 km TROPOMI NO₂ pixel and a 0.1° ERA5 boundary-layer-height (BLH) cell describe different footprints, and BLH governs how a satellite *column* maps to a *surface* concentration — high, well-mixed BLH dilutes the column [A]. [C] demonstrates that disciplined gap-filling and harmonisation of AOD/NO₂ (RF R²=0.96 for AOD and TROPOMI NO₂, 0.79 for OMI NO₂) is the foundation of skilful PM/gas mapping. Unlike [C], which **excludes meteorology and lists it as a limitation**, we retain met fields here precisely because they dominate O₃ and HCHO behaviour [A][B].

## Input datasets / inputs
- **Satellite columns:** INSAT-3D AOD; TROPOMI NO₂/HCHO/SO₂/CO/O₃; OMI NO₂ (gap-fill).
- **Meteorology (ERA5):** 2 m temperature, surface solar radiation (SSRD), surface pressure (SP), BLH, RH, V10.
- **Static:** SRTM elevation, ESA WorldCover land cover.
- **Ground truth:** CPCB daily PM2.5/PM10/NO₂/SO₂/CO/O₃.

## Algorithm / workflow / architecture
1. **Open** each raster as a lat/lon `DataArray` (`open_raster`).
2. **Regrid** continuous fields by bilinear (`linear`) and categorical fields by `nearest` onto the analysis `Grid` (`regrid_to_dataset`).
3. **QC**: `clip_valid_range` → `drop_sigma_outliers` (`apply`).
4. **Composite** to daily/monthly/seasonal means.
5. **Collocate** at stations (`sample_at_stations`) and **join** CPCB targets (`join_targets`).

## Mathematical formulation
Bilinear regrid weights for target point between four source cells:
```
v(x,y) = Σ_{i,j∈{0,1}} w_ij v_ij ,  w_ij = (1-|Δx_i|)(1-|Δy_j|)
```
Relative humidity from dewpoint via Magnus:
```
RH = 100 · exp( a·Td/(b+Td) − a·T/(b+T) ),   a=17.625, b=243.04 °C
```
Statistical outlier mask (per variable, global):
```
keep = |x − μ| ≤ n·σ ,   n = 5
```
Daily composite for cell c: `x̄_c,d = mean_{t∈d} x_c,t`.

## Python libraries
`xarray`, `rioxarray`/`rasterio`, `numpy`, `pandas`, plus `earthengine-api` for cloud-side reprojection of large collections.

## Code in this repo
- `src/isro_aqi/preprocessing/regrid.py` — `open_raster`, `regrid_to_dataset`
- `src/isro_aqi/preprocessing/qa_filter.py` — `VALID_RANGES`, `clip_valid_range`, `drop_sigma_outliers`, `apply`
- `src/isro_aqi/preprocessing/temporal.py` — `daily_mean`, `monthly_mean`, `seasonal_mean`
- `src/isro_aqi/preprocessing/collocate.py` — `sample_at_stations`, `join_targets`
- `src/isro_aqi/utils/geo.py` — `Grid`, `regrid`, `moore_neighbourhood`

```python
from isro_aqi.utils.geo import Grid
from isro_aqi.preprocessing import regrid, qa_filter, temporal, collocate

grid = Grid(bbox=(68.0, 6.5, 97.5, 37.5), resolution_deg=0.1)   # ~10 km, India
stack = regrid.regrid_to_dataset(layers, grid,
                                 methods={"landcover": "nearest"})
stack = qa_filter.apply(stack, sigma=5.0)           # clip + 5σ screen
daily = temporal.daily_mean(stack)
preds = collocate.sample_at_stations(daily, cpcb_stations)
train = collocate.join_targets(preds, cpcb_daily)
```

## Expected outputs
- `data/interim/stack.nc` — `(time, lat, lon)` Dataset, one variable per predictor.
- Daily/monthly/seasonal composites in `data/processed/`.
- `train.parquet` — long-format `(station_id, date, predictors…, targets…)`.

## Potential challenges & mitigations
- **AOD/NO₂ retrieval gaps (cloud).** Mitigation: RF gap-filling as in [C] (R²=0.96), applied before compositing.
- **Footprint mismatch (1 km vs 0.1°).** Mitigation: regrid to a common 0.1° AQI grid; keep a 0.01° grid for HCHO PHV.
- **Column vs surface bias.** Mitigation: carry BLH as a predictor so models learn the column-to-surface scaling [A].
- **Negative SO₂/HCHO retrievals.** Mitigation: `VALID_RANGES` permits small negatives (retrieval noise) but clips garbage.

## Validation metrics
QC retention rate per variable; gap-fill cross-validated R²/RMSE against withheld pixels (target R²≥0.9 for AOD/TROPOMI NO₂ [C]); station-collocation match count and nearest-cell distance distribution.

## Publication-quality figures
- Before/after regrid mosaics for AOD and NO₂.
- QC retention bar chart per variable.
- Seasonal-mean panels (winter / pre-/post-monsoon) highlighting the IGP burning windows.
- Map of CPCB stations over the analysis grid.
