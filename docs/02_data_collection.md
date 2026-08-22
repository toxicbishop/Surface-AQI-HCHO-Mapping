# Phase 2 — Data Collection

Acquisition and harmonisation of all predictor and ground-truth datasets over India ([68.0, 6.5, 97.5, 37.5]) via Google Earth Engine (server-side), Copernicus CDS, ISRO MOSDAC and CPCB.

## Objectives
- Ingest satellite columns, AOD, reanalysis meteorology, fire activity, land cover and terrain as model **predictors**.
- Ingest CPCB station observations as **targets** (PM2.5/PM10/NO₂/SO₂/O₃/CO).
- Reduce every source to two analysis grids: **0.1° (~10 km)** for AQI modelling and **0.01° (~1 km)** for HCHO/PHV [A].

## Scientific rationale
Surface AQI inversion needs co-located satellite signal *plus* the meteorological context that controls dispersion and chemistry — boundary-layer height, wind, RH, temperature, solar radiation [C]. HCHO source attribution additionally needs fire radiative power (FRP), burned area and vegetation state. We therefore assemble a broad covariate stack, echoing the 208-covariate philosophy of [C], using GEE for everything cloud-hosted and local downloads only for INSAT AOD (MOSDAC) and BLH (CDS).

## Input datasets
| Variable | Source / GEE asset | Band | Native res | Access |
|---|---|---|---|---|
| AOD | MOSDAC `3DIMG_L2B_AOD` (INSAT-3D); GEE `MODIS/061/MCD19A2` `Optical_Depth_055` cross-check | AOD / 0.55 µm | 10 km / 1 km | mosdac / gee |
| NO₂,SO₂,CO,O₃,HCHO | `COPERNICUS/S5P/OFFL/L3_{NO2,SO2,CO,O3,HCHO}` | tropo column densities | ~1113 m | gee |
| Meteorology | `ECMWF/ERA5_LAND/DAILY_AGGR` | t2m, d2m, u/v10, sp, precip, ssrd | ~9 km | gee |
| BLH | Copernicus CDS `reanalysis-era5-single-levels` | boundary_layer_height | ~9 km | cds |
| Fire | `MOD14A1` (FRP), `MCD64A1` (burned), `MOD13A2` (EVI); FIRMS/VIIRS | FRP, BurnDate, EVI | 1 km / 500 m / 375 m | gee / api |
| Land cover | `ESA/WorldCover/v200` | Map (11 classes) | 10 m | gee |
| Terrain | `USGS/SRTMGL1_003` | elevation→slope/aspect | 30 m | gee |
| Ground truth | CPCB CCR / data.gov.in CSVs | PM/gas hourly | station | cpcb |

## Algorithm / workflow
1. **Auth & AOI** — `gee_auth.init_ee` + `aoi_geometry` build the India bbox geometry; `export_image` standardises scale/CRS exports.
2. **TROPOMI** — `sentinel5p.build_stack`/`export_period` compute period-mean column densities; QA `qa_value>0.75` on HCHO; HCHO exported at native 1113 m, other gases at 7000 m.
3. **Meteorology** — `era5.build_stack` derives RH from t2m/d2m and wind speed from u/v; `fetch_blh_cds` pulls BLH per year (CDS, not in ERA5-Land).
4. **Fire** — `modis_fire.active_fire_frp`/`burned_area`/`evi`; `viirs_fire.fetch_firms_api` for near-real-time 375 m detections.
5. **Static** — `worldcover.fractional_cover` reduces 10 m classes to per-cell fractions; `srtm.terrain_stack` → elevation/slope/aspect.
6. **INSAT AOD** — `insat_aod.download_order` (MOSDAC), `read_granule` regrids HDF5 onto the analysis grid.
7. **CPCB** — `cpcb.load_raw_hourly` → `to_daily` (24-h mean for PM/NO₂/SO₂; 8-h rolling-max for O₃/CO; ≥16 valid hours required).

## Mathematical formulation
RH from temperature/dewpoint (Magnus) and wind speed:

```
e(T)  = 6.112 * exp(17.62*T / (243.12 + T))
RH    = 100 * e(T_d) / e(T_2m)
WS    = sqrt(u10^2 + v10^2)
```

CPCB daily aggregation (completeness ≥16 h):

```
PM/NO2/SO2_daily = mean_24h(C)
O3/CO_daily      = max_t [ mean_8h(C) ]
```

## Python libraries
`earthengine-api`, `geemap`, `cdsapi`, `requests` (FIRMS), `xarray`+`rioxarray`+`netCDF4`/`h5py` (MOSDAC granules), `pandas`, `numpy`, `pyproj`.

## Code in this repo
All ingestion lives in `src/isro_aqi/ingestion/`, driven by `pipelines/01_ingest.py` and `config/datasets.yaml`.

```python
from isro_aqi.ingestion import sentinel5p, era5, modis_fire, worldcover, srtm, insat_aod, cpcb
s5p_tasks = sentinel5p.export_period(cfg, "2023-01-01", "2023-12-31")   # GEE → Drive
era5.fetch_blh_cds(cfg, 2023, "data/blh_2023.nc")                       # CDS
daily = cpcb.to_daily(cpcb.load_raw_hourly("data/cpcb_2023.csv"))       # targets
```

## Expected outputs
Per-period multiband GeoTIFFs/NetCDFs per source on the 0.1°/0.01° grids, plus a tidy CPCB daily-station table — the raw inputs consumed by Phase 3 database assembly.

## Potential challenges & mitigations
- *INSAT AOD not on GEE* → MOSDAC bulk download + MAIAC (`MCD19A2`) as GEE cross-check/gap-fill, à la [C].
- *TROPOMI/AOD cloud gaps* → temporal compositing and RF gap-filling (AOD R²≈0.96 in [C]).
- *GEE export quotas / memory* → server-side reduction before export, per-gas tiling, year-batched CDS pulls.
- *CPCB sparsity & instrument drift* → ≥16-h completeness rule, outlier screening, station-metadata QC.

## Validation / QA
- INSAT vs MAIAC AOD scatter (bias/RMSE) per region.
- TROPOMI QA flag retention statistics; ERA5 vs CPCB met sanity checks.
- CPCB station-day completeness audit and duplicate-station deduplication.

## Publication-quality figures
- Fig 2.1 Data-flow diagram (GEE / CDS / MOSDAC / CPCB → grids).
- Fig 2.2 India coverage maps per dataset with CPCB station overlay.
- Fig 2.3 INSAT-3D vs MAIAC AOD validation scatter.
