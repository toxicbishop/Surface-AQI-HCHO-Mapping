#!/usr/bin/env python
"""Export the REAL (redesigned) model's outputs to public/data/*.json.

Reads the trained HYBRID model (trend + kriged residual) + the gridded stack +
the HCHO hotspot / back-trajectory / fire artifacts produced by run_demo.py (on
synthetic data today; on real satellite data once the pipeline runs), and writes
compact JSON the MapLibre + deck.gl frontend renders:

  aqi_frames.json   N time frames of per-cell [lon,lat,CPCB-AQI,RAPI]  (hybrid -> engine)
  gas_grids.json    seasonal-mean per-cell columns for AOD/NO2/SO2/CO/O3/HCHO (0..1)
  hcho_grid.json    seasonal-mean per-cell HCHO (0..1) for the hotspot basemap
  hotspots.json     attributed HCHO hotspots (lon/lat/source/frp)
  fires.json        downsampled VIIRS-style fire pixels
  trajectory.json   Delhi 48h back-trajectory path

The national outline public/data/india.geojson is the OFFICIAL Survey-of-India
boundary and is intentionally NOT overwritten here.

Run after `make demo`:  python pipelines/export_web.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xarray as xr
import yaml
from matplotlib.path import Path as MplPath

sys.path.insert(0, "src")
from isro_aqi.aqi import AQIEngine  # noqa: E402
from isro_aqi.analysis_layers import build_analysis_layers  # noqa: E402
from isro_aqi.features import add_engineered_features  # noqa: E402

OUT = Path("public/data")
OUT.mkdir(parents=True, exist_ok=True)

# engine pollutant -> model target column
AQI_MAP = {"pm25": "pm25", "pm10": "pm10", "no2": "no2_obs",
           "so2": "so2_obs", "o3": "o3_obs", "co": "co_obs"}


def india_mask_path() -> MplPath:
    """Build an ocean mask from the OFFICIAL India boundary (largest landmass ring)."""
    gj = json.loads((OUT / "india.geojson").read_text())
    polys = gj["features"][0]["geometry"]["coordinates"]
    area = lambda r: (max(p[0] for p in r) - min(p[0] for p in r)) * (max(p[1] for p in r) - min(p[1] for p in r))  # noqa: E731
    mainland = max((p[0] for p in polys), key=area)
    return MplPath(np.array(mainland))


def write(name: str, obj) -> None:
    p = OUT / name
    p.write_text(json.dumps(obj, separators=(",", ":")))
    print(f"  {name}: {p.stat().st_size / 1024:.0f} KB")


def grid_df(day_ds: xr.Dataset, date, features):
    df = day_ds.to_dataframe().reset_index()
    df["date"] = pd.Timestamp(date)
    df = add_engineered_features(df, lag_cols=None)
    for c in features:
        if c not in df:
            df[c] = 0.0
    return df


def main():
    print("loading stack + hybrid model …")
    stack = xr.open_dataset("data/interim/daily.nc")
    model = joblib.load("models/hybrid.joblib")          # the redesigned hybrid
    features = list(model.features)
    engine = AQIEngine(yaml.safe_load(open("config/aqi_breakpoints.yaml")))
    times = pd.to_datetime(stack["time"].values)
    PATH = india_mask_path()

    # ---- AQI time frames: CPCB + RAPI from the hybrid model -------------
    print("predicting AQI frames (CPCB + RAPI) …")
    idxs = np.unique(np.linspace(0, len(times) - 1, 8).astype(int))
    frames = []
    for fi in idxs:
        day = stack.isel(time=int(fi))
        df = grid_df(day, times[fi], features)
        pred = model.predict(df)
        conc = {e: pred[c].to_numpy() for e, c in AQI_MAP.items() if c in pred}
        out = engine.compute_grid(conc)                  # cpcb, rapi, dominant, divergence
        lon, lat = df["lon"].to_numpy(), df["lat"].to_numpy()
        inside = PATH.contains_points(np.column_stack([lon, lat]))
        cpcb, rapi = out["cpcb"], out["rapi"]
        cells = [
            [round(float(lon[i]), 2), round(float(lat[i]), 2), int(cpcb[i]), int(rapi[i])]
            for i in range(len(cpcb)) if inside[i] and np.isfinite(cpcb[i])
        ]
        frames.append({"date": str(times[fi].date()), "cells": cells})
    write("aqi_frames.json", {"key": ["lon", "lat", "aqi", "rapi"], "frames": frames})

    # ---- gas seasonal-mean grids (normalised 0..1) ----------------------
    print("exporting gas grids …")
    gases = [g for g in ["aod", "no2", "so2", "co", "o3", "hcho"] if g in stack]
    mean = stack[gases].mean("time")
    lon2d, lat2d = np.meshgrid(stack["lon"].values, stack["lat"].values)
    lonf, latf = lon2d.ravel(), lat2d.ravel()
    inside = PATH.contains_points(np.column_stack([lonf, latf]))
    norm = {}
    for g in gases:
        v = mean[g].values.ravel()
        vin = v[inside]
        lo, hi = np.nanpercentile(vin, 2), np.nanpercentile(vin, 98)
        norm[g] = np.clip((v - lo) / (hi - lo + 1e-12), 0, 1)
    gas_cells = [
        {"lon": round(float(lonf[i]), 2), "lat": round(float(latf[i]), 2),
         **{g: round(float(norm[g][i]), 3) for g in gases}}
        for i in range(len(lonf)) if inside[i]
    ]
    write("gas_grids.json", {"gases": gases, "cells": gas_cells})
    write("hcho_grid.json", [[c["lon"], c["lat"], c.get("hcho", 0)] for c in gas_cells])

    # ---- comparative K-Means zones + Isolation Forest anomalies -----------
    print("exporting comparative zone and anomaly layers …")
    mean_df = grid_df(mean, times[-1], features)
    mean_pred = model.predict(mean_df)
    mean_conc = {e: mean_pred[c].to_numpy() for e, c in AQI_MAP.items() if c in mean_pred}
    mean_aqi = engine.compute_grid(mean_conc)
    analysis = pd.DataFrame({
        "lon": mean_df["lon"].to_numpy(), "lat": mean_df["lat"].to_numpy(),
        "aqi": mean_aqi["cpcb"], "rapi": mean_aqi["rapi"],
        "hcho": mean_df.get("hcho", pd.Series(np.nan, index=mean_df.index)),
        "no2": mean_df.get("no2", pd.Series(np.nan, index=mean_df.index)),
        "co": mean_df.get("co", pd.Series(np.nan, index=mean_df.index)),
        "frp_mean": mean_df.get("frp_mean", pd.Series(np.nan, index=mean_df.index)),
    })
    layers = build_analysis_layers(
        analysis,
        date_value=str(times[-1].date()),
        zone_features=["aqi", "hcho", "no2", "co"],
        isolation_features=["hcho", "no2", "co", "frp_mean"],
        k_range=(3, 4, 5),
        contamination=0.05,
    )
    layers["analysis_metadata"]["data_status"] = "synthetic_demo"
    for filename, key in (("zone_cells.json", "zone_cells"),
                          ("isolation_hotspots.json", "isolation_hotspots"),
                          ("analysis_metadata.json", "analysis_metadata")):
        write(filename, layers[key])

    # ---- hotspots / fires / trajectory (real artifacts) -----------------
    print("exporting hotspots / fires / trajectory …")
    hs = pd.read_csv("outputs/hcho_hotspots_attributed.csv")
    write("hotspots.json", [
        {"lon": round(float(r.lon), 2), "lat": round(float(r.lat), 2),
         "source": str(r.source), "detail": str(getattr(r, "source_detail", "") or ""),
         "frp": (round(float(r.frp_mean), 1) if pd.notna(r.frp_mean) else None), "n": int(r.n_cells)}
        for r in hs.itertuples()
    ])

    fires = pd.read_parquet("data/processed/fire_pixels.parquet")
    if len(fires) > 1400:
        fires = fires.sample(1400, random_state=0)
    write("fires.json", [
        [round(float(r.longitude), 2), round(float(r.latitude), 2), round(float(r.frp), 0)]
        for r in fires.itertuples()
    ])

    traj = pd.read_csv("outputs/delhi_backtrajectory.csv")
    write("trajectory.json", [[round(float(r.lon), 2), round(float(r.lat), 2)] for r in traj.itertuples()])

    print("done -> public/data/  (india.geojson left untouched — official boundary)")


if __name__ == "__main__":
    main()
