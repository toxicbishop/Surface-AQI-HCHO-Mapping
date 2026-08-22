# Phase 9 — India AQI Mapping & Atlas

Render the Phase 8 AQI fields as a multi-temporal cartographic series — daily, weekly, monthly, seasonal and annual maps — collated into the deliverable **India AQI Atlas**.

## Objectives
- Produce consistent, CPCB-coloured AQI maps across daily → annual aggregations over the India AOI (68–97.5°E, 6.5–37.5°N).
- Compile the **India AQI Atlas**: ordered map series with dominant-pollutant panels and category statistics.
- Report exposure metrics (population/area in each CPCB band) and seasonal regimes (winter PM peaks, summer dust/O3).

## Scientific rationale
A single daily map cannot reveal the structural pattern of Indian air quality; aggregation exposes the post-monsoon Indo-Gangetic Plain (IGP) PM2.5 wall, summer O3/dust over the north-west, and the urban–rural gradient. Wang et al. 2023 [C] motivate mapped, satellite-derived surface AQI to cover the gaps between sparse CPCB stations; the atlas operationalises that for India at scale.

## Input datasets
- **Phase 8 AQI rasters** (`aqi`, `aqi_dominant`, `aqi_category`) on the common grid.
- **`config/aqi_breakpoints.yaml`** — categories + colours, mirrored in `viz/maps.py` (`CPCB_BOUNDS`, `CPCB_COLORS`).
- **GADM/GAUL admin boundaries** for state/district overlays and zonal statistics.
- **Gridded population** (e.g. WorldPop/GPW) for exposure-weighted summaries.

## Algorithm / workflow
1. Aggregate daily AQI to weekly/monthly/seasonal/annual using the **temporal mean of concentrations** (then recompute AQI) to avoid averaging non-linear index values directly.
2. Mask to the India AOI; apply the CPCB `BoundaryNorm` + `ListedColormap`.
3. Render with Cartopy (`aqi_map`) at 300 dpi; add coastline/borders/states.
4. Compute zonal statistics per state/district and per CPCB band.
5. Lay out the atlas: daily exemplars, monthly grid, four-season panel, annual summary, dominant-pollutant maps.

## Mathematical formulation
Temporal aggregation done on concentrations, AQI recomputed (sub-index then max) [C][D]:
```
C̄_p(T) = mean_{t∈T} C_p(t)            # window T = week/month/season/year
I_p(T)  = (I_hi−I_lo)/(BP_hi−BP_lo)·(C̄_p(T)−BP_lo) + I_lo
AQI(T)  = max_p I_p(T)
```
Exposure share in band b:
```
E_b = Σ_{cells∈b} pop_cell / Σ_all pop_cell
```

## Python libraries
`cartopy`, `matplotlib` (`ListedColormap`, `BoundaryNorm`), `xarray`, `numpy`, `rioxarray`/`rasterio` (zonal stats), `geopandas` (admin overlays).

## Code in this repo
`src/isro_aqi/viz/maps.py` — `aqi_map` (CPCB ramp), `_india_axes` (extent + features); colours from `AQIEngine.color`. Aggregation driven by `pipelines/05_generate_aqi.py`.

```python
CPCB_BOUNDS = [0, 50, 100, 200, 300, 400, 500]
CPCB_COLORS = ["#00B050","#92D050","#FFFF00","#FF9900","#FF0000","#7E0023"]

def aqi_map(aqi, title="Daily AQI", out_path=None):
    fig, ax = _india_axes()
    cmap = ListedColormap(CPCB_COLORS); norm = BoundaryNorm(CPCB_BOUNDS, cmap.N)
    p = ax.pcolormesh(aqi["lon"], aqi["lat"], aqi.values, cmap=cmap, norm=norm,
                      transform=ccrs.PlateCarree(), shading="auto")
    fig.colorbar(p, ax=ax, ticks=CPCB_BOUNDS, label="AQI"); ax.set_title(title)
```

## Expected outputs
- Daily/weekly/monthly/seasonal/annual AQI GeoTIFFs + PNGs.
- **India AQI Atlas** (compiled PDF/figure set).
- State/district AQI tables; per-band exposure fractions; dominant-pollutant maps per season.

## Potential challenges & mitigations
- **Averaging non-linear AQI** → aggregate concentrations first, recompute AQI (formula above).
- **Cloud/retrieval gaps** producing white holes → gap-fill via temporal compositing; flag low-coverage cells.
- **Colour fidelity** → single source of truth shared between `maps.py` and the engine config.
- **Projection/extent drift** → fixed PlateCarree extent and feature set in `_india_axes`.

## Validation metrics
- Map-vs-station agreement at CPCB sites per aggregation window (RMSE, R², category κ).
- Spatial coverage (% valid cells) per window.
- Seasonal-cycle correlation against published IGP/national climatologies.

## Publication-quality figures
- 12-panel monthly AQI grid for a representative year.
- Four-season AQI panel + matched dominant-pollutant panel.
- Annual mean AQI choropleth with state borders.
- Exposure bar chart: population share per CPCB band by season.
