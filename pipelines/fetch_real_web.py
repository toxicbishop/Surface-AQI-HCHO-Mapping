#!/usr/bin/env python
"""Fetch REAL satellite layers directly from GEE -> public/data/*.json.

No Google Drive round-trip and no CPCB needed: pulls the post-monsoon 2021
seasonal-mean TROPOMI gas columns + MAIAC AOD + MODIS fire over India straight
into Python via getDownloadURL, then rebuilds the OBSERVATION layers with real
data:

  gas_grids.json   real AOD / NO2 / SO2 / CO / O3 / HCHO seasonal columns (0..1)
  hcho_grid.json   real HCHO column (0..1)
  hotspots.json    real PHV hotspots on real HCHO, attributed
  fires.json       real MODIS high-FRP fire cells

The surface AQI layer (aqi_frames.json) still needs the trained model + CPCB
ground truth, so it is left as the model estimate and clearly labelled in the UI.

    python pipelines/fetch_real_web.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import ee
import numpy as np
import pandas as pd
import requests
import rioxarray  # noqa: F401
import xarray as xr
import yaml
from matplotlib.path import Path as MplPath

sys.path.insert(0, "src")
from isro_aqi.hcho import phv, source_attribution, transport  # noqa: E402

OUT = Path("public/data")
OUT.mkdir(parents=True, exist_ok=True)
REGION_BBOX = [68.0, 6.5, 97.5, 37.5]
START, END = "2021-10-01", "2021-12-31"
SCALE = 55660  # ~0.5 deg — matches the map's 0.5° cell size (HALF=0.25) + the AQI grid

GASES = {
    "no2": ("COPERNICUS/S5P/OFFL/L3_NO2", "tropospheric_NO2_column_number_density"),
    "so2": ("COPERNICUS/S5P/OFFL/L3_SO2", "SO2_column_number_density"),
    "co": ("COPERNICUS/S5P/OFFL/L3_CO", "CO_column_number_density"),
    "o3": ("COPERNICUS/S5P/OFFL/L3_O3", "O3_column_number_density"),
    "hcho": ("COPERNICUS/S5P/OFFL/L3_HCHO", "tropospheric_HCHO_column_number_density"),
}


def fetch(img, name, region):
    url = img.rename(name).getDownloadURL(
        {"region": region, "scale": SCALE, "format": "GEO_TIFF", "crs": "EPSG:4326"})
    r = requests.get(url, timeout=240)
    r.raise_for_status()
    p = f"/tmp/real_{name}.tif"
    open(p, "wb").write(r.content)
    da = rioxarray.open_rasterio(p, masked=True).squeeze(drop=True).rename({"x": "lon", "y": "lat"})
    return da


def fetch_winds(region, days: list[str]) -> xr.Dataset:
    """Real ERA5-Land daily 10 m winds over India -> (time, lat, lon) u_wind/v_wind."""
    us, vs, times = [], [], []
    for d in days:
        nxt = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        im = (ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(d, nxt).first()
              .select(["u_component_of_wind_10m", "v_component_of_wind_10m"]))
        url = im.getDownloadURL({"region": region, "scale": SCALE, "format": "GEO_TIFF", "crs": "EPSG:4326"})
        r = requests.get(url, timeout=240)
        r.raise_for_status()
        p = f"/tmp/wind_{d}.tif"
        open(p, "wb").write(r.content)
        da = rioxarray.open_rasterio(p, masked=True).rename({"x": "lon", "y": "lat"})
        us.append(da.isel(band=0, drop=True))
        vs.append(da.isel(band=1, drop=True))
        times.append(pd.Timestamp(d))
    g0 = us[0]
    us = [a.interp(lon=g0.lon, lat=g0.lat) for a in us]
    vs = [a.interp(lon=g0.lon, lat=g0.lat) for a in vs]
    return xr.Dataset({
        "u_wind": xr.concat(us, dim=pd.Index(times, name="time")),
        "v_wind": xr.concat(vs, dim=pd.Index(times, name="time")),
    })


def india_mask(lonf, latf):
    gj = json.loads((OUT / "india.geojson").read_text())
    polys = gj["features"][0]["geometry"]["coordinates"]
    area = lambda r: (max(p[0] for p in r) - min(p[0] for p in r)) * (max(p[1] for p in r) - min(p[1] for p in r))  # noqa: E731
    mainland = max((p[0] for p in polys), key=area)
    return MplPath(np.array(mainland)).contains_points(np.column_stack([lonf, latf]))


def main():
    ee.Initialize(project="vayu-500014")
    region = ee.Geometry.Rectangle(REGION_BBOX)
    print(f"fetching REAL seasonal means {START}..{END} over India @0.5deg …")

    layers = {}
    for g, (asset, band) in GASES.items():
        im = ee.ImageCollection(asset).select(band).filterDate(START, END).filterBounds(region).mean()
        layers[g] = fetch(im, g, region)
        print(f"  ✓ real {g}")
    aod = (ee.ImageCollection("MODIS/061/MCD19A2_GRANULES").select("Optical_Depth_055")
           .filterDate(START, END).filterBounds(region).mean().multiply(0.001))
    layers["aod"] = fetch(aod, "aod", region)
    print("  ✓ real aod")
    frp = (ee.ImageCollection("MODIS/061/MOD14A1").select("MaxFRP")
           .filterDate(START, END).filterBounds(region).max().multiply(0.1))
    layers["frp"] = fetch(frp, "frp", region)
    print("  ✓ real fire (MaxFRP)")

    # align everything to the NO2 grid
    ref = layers["no2"]
    glon, glat = ref["lon"].values, ref["lat"].values
    for k in list(layers):
        if k != "no2":
            layers[k] = layers[k].interp(lon=glon, lat=glat, method="linear")

    lon2d, lat2d = np.meshgrid(glon, glat)
    lonf, latf = lon2d.ravel(), lat2d.ravel()
    inside = india_mask(lonf, latf)

    # ---- gas_grids.json (real, normalised 0..1) ----
    gases = ["aod", "no2", "so2", "co", "o3", "hcho"]
    norm = {}
    for g in gases:
        v = layers[g].values.ravel()
        vin = v[inside & np.isfinite(v)]
        lo, hi = np.nanpercentile(vin, 2), np.nanpercentile(vin, 98)
        norm[g] = np.clip((v - lo) / (hi - lo + 1e-12), 0, 1)
    valid = inside & np.isfinite(layers["no2"].values.ravel())
    cells = [{"lon": round(float(lonf[i]), 2), "lat": round(float(latf[i]), 2),
              **{g: round(float(norm[g][i]), 3) for g in gases}}
             for i in range(len(lonf)) if valid[i]]
    (OUT / "gas_grids.json").write_text(json.dumps({"gases": gases, "cells": cells}, separators=(",", ":")))
    (OUT / "hcho_grid.json").write_text(json.dumps([[c["lon"], c["lat"], c["hcho"]] for c in cells], separators=(",", ":")))
    print(f"wrote REAL gas_grids + hcho_grid: {len(cells)} cells")

    # ---- real HCHO hotspots via PHV (mol/m^2 -> molec/cm^2 = x 6.022e19) ----
    hcho_da = layers["hcho"].fillna(0)
    ds_phv = phv.detect_hotspots(hcho_da, phv_min=1.08, hva_threshold=8e15, to_molec_cm2=6.022e19)
    clusters = source_attribution.connected_clusters(ds_phv["hva"], hcho_da)
    if len(clusters):
        regions = yaml.safe_load(open("config/regions.yaml"))
        clusters["frp_mean"] = [float(np.nan_to_num(layers["frp"].sel(lon=r.lon, lat=r.lat, method="nearest").values, nan=0.0))
                                for r in clusters.itertuples()]
        clusters = source_attribution.attribute(clusters, regions, season="post_monsoon")
        hs = [{"lon": round(float(r.lon), 2), "lat": round(float(r.lat), 2),
               "source": str(r.source), "detail": str(getattr(r, "source_detail", "") or ""),
               "frp": round(float(r.frp_mean), 1), "n": int(r.n_cells)}
              for r in clusters.itertuples()]
        (OUT / "hotspots.json").write_text(json.dumps(hs, separators=(",", ":")))
        print(f"wrote REAL hotspots: {len(hs)} (attributed)")

    # ---- real fire cells (high FRP) -> fires.json ----
    fv = layers["frp"].values.ravel()
    fire_pts = [[round(float(lonf[i]), 2), round(float(latf[i]), 2), round(float(fv[i]), 0)]
                for i in range(len(lonf)) if inside[i] and np.isfinite(fv[i]) and fv[i] > 5]
    (OUT / "fires.json").write_text(json.dumps(fire_pts, separators=(",", ":")))
    print(f"wrote REAL fires: {len(fire_pts)} cells")

    # ---- real ERA5 back-trajectory: did upwind fires feed Delhi? (Objective 2) ----
    receptor = (77.10, 28.65)              # Delhi
    rdate = "2021-11-08"                   # peak burning window
    days = [(date(2021, 11, 1) + timedelta(days=i)).isoformat() for i in range(14)]
    try:
        winds = fetch_winds(region, days)
        path = transport.back_trajectory(winds, receptor[0], receptor[1], rdate, hours=48, dt_hours=3.0)
        (OUT / "trajectory.json").write_text(json.dumps(
            [[round(float(r.lon), 2), round(float(r.lat), 2)] for r in path.itertuples()], separators=(",", ":")))
        fires_df = pd.DataFrame([{"longitude": float(lonf[i]), "latitude": float(latf[i])}
                                 for i in range(len(lonf)) if inside[i] and np.isfinite(fv[i]) and fv[i] > 5])
        n = transport.fires_along_path(path, fires_df, radius_km=150) if len(fires_df) else 0
        print(f"wrote REAL trajectory: {len(path)} pts, {n} fires within 150 km of Delhi's 48h back-path")
    except Exception as e:
        print(f"ERA5 trajectory skipped: {e}")

    print("done -> real observation layers (gas/HCHO/hotspots/fire/transport). AQI stays model-estimate (needs CPCB).")


if __name__ == "__main__":
    main()
