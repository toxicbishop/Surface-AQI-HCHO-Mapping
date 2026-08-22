# Phase 13 — Atmospheric Transport Analysis

Test whether **upwind fires drive HCHO at downwind receptor cities** using ERA5-wind back-trajectories — the project's differentiator (most student projects stop at correlations and skip trajectories).

## Objectives
- Characterise wind climatology (wind roses) at IGP receptors: delhi, lucknow, patna, kanpur.
- Compute kinematic single-level back-trajectories that answer: *did Punjab fires raise Delhi HCHO? did Uttarakhand fires affect NCR? did Central-India fires affect the IGP?*
- Count VIIRS fire pixels intersecting each trajectory to attribute receptor HCHO enhancement to specific source regions.
- Provide a HYSPLIT/`pysplit` hook for production-grade ensemble trajectories.

## Scientific rationale
[B] uses ERA5 U/V winds to explain HCHO dispersion (seaport plumes, Thar Desert outflow) but stops short of trajectory modelling. Because HCHO's lifetime is short (~50 min [A]), enhancement at a receptor is dominated by **fresh upwind production plus transported precursors and primary HCHO from biomass burning**. Back-trajectories convert a static fire map into a causal source–receptor link: if a parcel arriving over Delhi traversed burning Punjab paddy fields hours earlier, that is mechanistic evidence — far stronger than co-located correlation. This directly tackles Objective 3 (quantifying crop-residue, forest-fire and long-range-transport contributions to HCHO).

## Input datasets / inputs
- **ERA5** hourly/daily `u_wind`, `v_wind` (single pressure/10 m level) as `xarray.Dataset` on a lon/lat grid (`data/interim/daily.zarr`).
- **VIIRS/MODIS active fires** (lon, lat, FRP) for the analysis window (Phase 06).
- Receptor coordinates from `config/regions.yaml → receptors`.
- Source-region bboxes (crop_burning, forest_fire) for path-intersection labelling.

## Algorithm / workflow
1. Select receptor (lon, lat) and a date.
2. `back_trajectory` steps a parcel **backwards** through the ERA5 (u,v) field with an hourly step on a sphere for `hours` (default 48) → lon/lat path DataFrame.
3. `fires_along_path` counts VIIRS pixels within `radius_km` (default 50 km) of any path node (haversine).
4. Repeat over the burning season to build an ensemble; tag each path by which source bbox it crossed.
5. Optional `wind_rose` per receptor; optional `run_hysplit` for clustered NOAA-HYSPLIT corridors.

## Mathematical formulation
At each step the parcel is advected by the locally-sampled wind. Backward displacement over Δt with a spherical-Earth conversion (R = 6371.0088 km):

```
Δlat = − v · Δt / R · (180/π)
Δlon = − u · Δt / (R · cos(lat)) · (180/π)
lat ← lat + Δlat ,   lon ← lon + Δlon ,   t ← t − Δt
```

(u,v in m/s, Δt in s, R in m; the leading minus = backward in time.) Great-circle distance for fire intersection:

```
d = 2R · asin( sqrt( sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2) ) )
fire counted ⇔ min over path of d ≤ radius_km
```

## Python libraries
`xarray`, `numpy`, `pandas`, `windrose`, `matplotlib`, `cartopy` (overlays), `pysplit` + NOAA **HYSPLIT** (external engine for `run_hysplit`).

## Code in this repo
`src/isro_aqi/hcho/transport.py` — `wind_rose`, `back_trajectory`, `fires_along_path`, `run_hysplit`. Driven by `pipelines/07_transport.py`; receptors in `config/regions.yaml`.

```python
for _ in range(steps):
    frame = winds.isel(time=int(np.argmin(np.abs(times - t))))
    u = float(frame[u_var].sel(lon=lon, lat=lat, method="nearest"))
    v = float(frame[v_var].sel(lon=lon, lat=lat, method="nearest"))
    dlat = -(v * dt_s) / (EARTH_R_KM * 1000) * (180 / np.pi)
    dlon = -(u * dt_s) / (EARTH_R_KM * 1000 * np.cos(np.radians(lat))) * (180 / np.pi)
    lat += dlat; lon += dlon; t -= pd.Timedelta(hours=dt_hours)
```

```python
path = transport.back_trajectory(winds, *cfg.regions["receptors"]["delhi"],
                                 "2021-11-05", hours=48)
n_fires = transport.fires_along_path(path, viirs_df, radius_km=50)
```

## Expected outputs
- Per-receptor/date trajectory paths (CSV/GeoJSON) and overlay maps on the fire-density layer.
- Fire-intersection counts answering the three Punjab→Delhi / Uttarakhand→NCR / Central-India→IGP questions.
- Wind roses per receptor; (optional) clustered HYSPLIT transport corridors.
- A source-contribution summary feeding Objective-3 attribution.

## Potential challenges & mitigations
- **Single-level kinematic drift** (no vertical motion, no diffusion) → state as screening; upgrade to HYSPLIT ensembles via `run_hysplit`/`pysplit`.
- **Coarse ERA5 resolution** smooths convergence → 50 km capture radius; sensitivity tests on `radius_km`.
- **Grid edge / nearest-neighbour sampling** → clip paths to domain; flag out-of-grid steps.
- **Fire timing vs parcel passage** → restrict fires to the trajectory time window, not the whole day.

## Validation metrics
Trajectory cross-check vs NOAA HYSPLIT for sample cases (endpoint great-circle error km); enrichment test — HCHO at receptor on fire-intersecting days vs non-intersecting days (Mann–Whitney U); correlation of `fires_along_path` count with receptor HCHO anomaly.

## Publication-quality figures
- `viz/maps.py` trajectory overlay on fire-FRP basemap (cartopy), one panel per receptor.
- Wind rose grid (4 receptors) via `transport.wind_rose`.
- Box/violin of receptor HCHO split by fire-intersecting vs non-intersecting trajectories.
