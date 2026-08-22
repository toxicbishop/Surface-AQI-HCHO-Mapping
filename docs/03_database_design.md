# Phase 3 — Database Creation

A unified, analysis-ready feature store: one record per (date, lat, lon) cell over India, joining all predictors with CPCB targets, partitioned for ~50–100 M rows.

## Objectives
- Define a single canonical schema fusing satellite, meteorology, fire, static and engineered predictors with CPCB targets.
- Build a **training table** (predictors collocated with labelled CPCB cells) and a much larger **inference grid** (all cells, targets NaN) for wall-to-wall AQI prediction.
- Persist compactly (float32, partitioned Parquet) so multi-year India fits in the **~50–100 M row** target.

## Scientific rationale
The supervised problem in [C] is a tabular regression over a wide covariate stack; we materialise exactly that stack so any model (RF baseline → CNN-LSTM) reads one consistent schema. Separating labelled training rows from the full inference grid mirrors the [C] design: fit where CPCB exists, then predict the unobserved majority to make maps. Cyclical day-of-year and the FNR ratio are pre-engineered so chemistry-aware features [A][B] are first-class columns.

## Input datasets
The harmonised Phase 2 outputs: TROPOMI columns, INSAT/MAIAC AOD, ERA5 + CDS BLH, MODIS/VIIRS fire, WorldCover fractions, SRTM terrain, and CPCB daily station observations — all on the 0.1° AQI grid (HCHO additionally at 0.01°).

## Algorithm / workflow
1. **Stack & align** all sources to the 0.1° grid and a common date index.
2. **Collocate** CPCB daily values to their grid cell → labelled rows.
3. **Engineer** `fnr = hcho/no2`, `doy_sin/doy_cos`, `wind_speed` (`features/engineering.py`).
4. `build_training_table` — coerce to float32, add `year`/`month` partitions, write Parquet.
5. `build_inference_grid` — flatten the daily `xarray.Dataset` **per day** (bounded memory), drop all-NaN-predictor cells, append to year/month partitions.
6. Targets remain NaN on inference cells; these are what models predict.

## Mathematical formulation
Engineered columns and database scale:

```
fnr        = hcho / no2                      # O3-sensitivity regime [A][B]
doy_sin    = sin(2π · doy / 365)
doy_cos    = cos(2π · doy / 365)
N_rows    ≈ N_days · N_cells(grid 0.1°)  →  ~50–100 M  (multi-year India)
```

**Record schema** (`KEYS + PREDICTORS + TARGETS`, all float32 except date):

```
KEYS       = [date, lat, lon]
PREDICTORS = [
  aod, no2, so2, co, o3, hcho,                                    # satellite
  temperature, rh, u_wind, v_wind, wind_speed,
  pressure, precipitation, solar_radiation, blh,                 # met + CDS BLH
  frp_mean, frp_max, fire_count, burned, evi,                    # fire/biomass
  elevation, slope, aspect,                                       # terrain
  lc_tree, lc_shrub, lc_grass, lc_crop, lc_built,
  lc_bare, lc_water, lc_wetland,                                  # WorldCover fractions
  fnr, doy_sin, doy_cos ]                                         # engineered
TARGETS    = [pm25, pm10, no2_obs, so2_obs, o3_obs, co_obs]       # CPCB
PARTITION  = [year, month]
```

## Python libraries
`pandas`, `numpy`, `xarray`, `pyarrow`/`fastparquet` (partitioned Parquet), `dask` (out-of-core builds), `pyproj`.

## Code in this repo
Schema and builders are in `src/isro_aqi/database/`, driven by `pipelines/03_build_database.py`.

```python
from isro_aqi.database.schema import KEYS, PREDICTORS, TARGETS, COLUMNS, PARTITION_COLS
from isro_aqi.database.build_db import build_training_table, build_inference_grid

train_df = build_training_table(collocated, "data/db/train")          # labelled rows
build_inference_grid(daily_ds,            "data/db/inference")         # ~50–100 M rows
```

`build_inference_grid` iterates `daily["time"]`, flattens each day to a DataFrame, drops cells where all PREDICTORS are NaN, and appends to `year=/month=` Parquet partitions.

## Expected outputs
- `train/` — Hive-partitioned Parquet of collocated predictor+target rows.
- `inference/` — partitioned Parquet, ~50–100 M rows, predictors only (targets NaN).
- A data dictionary auto-derived from `schema.COLUMNS` + `DTYPES`.

## Potential challenges & mitigations
- *Memory at 50–100 M rows* → per-day flattening, float32 DTYPES, year/month partition pruning, optional `dask`.
- *Collocation mismatch (point CPCB vs cell)* → nearest-cell join with distance QC; flag multi-station cells.
- *Missing predictors per cell* → keep NaNs (models/imputers handle), but drop fully-empty cells to save space.
- *Schema drift* → `schema.py` is the single source of truth; builders import `COLUMNS`/`PARTITION_COLS`.

## Validation / QA
- Row-count audit vs `N_days · N_cells`; per-partition null-rate report.
- Range checks per column (e.g., AOD ≥ 0, RH ∈ [0,100], lc fractions sum ≈ 1).
- Train/inference schema-equality assertion; CPCB collocation spot-checks against station maps.

## Publication-quality figures
- Fig 3.1 Entity diagram of the (date,lat,lon) record and column groups.
- Fig 3.2 Per-column data-availability/null heatmap across partitions.
- Fig 3.3 Spatial density of labelled (CPCB-collocated) vs inference-only cells over India.
