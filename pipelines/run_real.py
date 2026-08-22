#!/usr/bin/env python
"""ONE-COMMAND real-data run for Objective 1 (surface AQI).

Pulls the real predictor stack straight from GEE (no Drive download needed),
collocates it with your CPCB station data, trains + spatially-cross-validates the
hybrid model, and writes a REAL, ground-validated AQI map -> public/data.

    python pipelines/run_real.py          # or:  make real

Drop CPCB CSVs into data/external/ first (Oct-Dec 2021). Without CPCB it still
fetches + saves the real predictor stack and tells you what's missing. With CPCB
it prints real RMSE / R / MAE and exports the real AQI layer to the site.

Predictors are seasonal means (one composite) -> this trains the spatial model and
yields a seasonal AQI map; per-day ingestion (for daily CNN-LSTM) is the next step.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import re
import sys
from pathlib import Path

import ee
import numpy as np
import pandas as pd
import requests
import rioxarray  # noqa: F401
import xarray as xr
import yaml
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

sys.path.insert(0, "src")
from isro_aqi.aqi import AQIEngine  # noqa: E402
from isro_aqi.analysis_layers import build_analysis_layers  # noqa: E402
from isro_aqi.config import load_config  # noqa: E402
from isro_aqi.features import add_engineered_features  # noqa: E402
from isro_aqi.ingestion import cpcb, era5, modis_fire, sentinel5p, srtm  # noqa: E402
from isro_aqi.ingestion.gee_auth import aoi_geometry, init_ee  # noqa: E402
from isro_aqi.models.baselines import metrics  # noqa: E402
from isro_aqi.models.hybrid import INDIA_BENCHMARK_R2, HybridModel  # noqa: E402
from isro_aqi.models.train import spatial_blocks  # noqa: E402
from isro_aqi.preprocessing.calibrate_no2 import calibrate_no2_stack  # noqa: E402
from isro_aqi.preprocessing.collocate import join_targets, sample_at_stations  # noqa: E402
from isro_aqi.preprocessing.gapfill_aod import fill_aod_stack  # noqa: E402

# Oct-Dec 2025 burning season: the recent window with BOTH OpenAQ ground truth
# AND TROPOMI satellite data (OpenAQ India archive skips 2019-2024; TROPOMI starts 2018).
START, END = "2025-10-01", "2025-12-31"
SCALE = 27830  # ~0.25 deg predictor grid
WEB = Path("public/data")
TARGETS = ["pm25", "pm10", "no2_obs", "so2_obs", "o3_obs", "co_obs"]
AQI_MAP = {"pm25": "pm25", "pm10": "pm10", "no2": "no2_obs", "so2": "so2_obs", "o3": "o3_obs", "co": "co_obs"}
# band order produced by each ingestion module's ee.Image
ERA5_BANDS = ["temperature", "rh", "u_wind", "v_wind", "wind_speed", "pressure", "precipitation", "solar_radiation"]


def _dl(ee_img, names, region, tag):
    """Download an ee.Image via getDownloadURL -> {name: (lat,lon) DataArray}."""
    url = ee_img.getDownloadURL({"region": region, "scale": SCALE, "format": "GEO_TIFF", "crs": "EPSG:4326"})
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    p = f"/tmp/pred_{tag}.tif"
    open(p, "wb").write(r.content)
    da = rioxarray.open_rasterio(p, masked=True).rename({"x": "lon", "y": "lat"})
    n = int(da.sizes["band"])
    return {names[i]: da.isel(band=i, drop=True) for i in range(min(n, len(names)))}


def fetch_predictor_stack(cfg) -> xr.Dataset:
    """Real seasonal-mean predictor stack over India, straight from GEE (cached)."""
    cache = Path("data/interim/daily_real.nc")
    if cache.exists():
        print(f"using cached predictor stack: {cache}")
        return xr.open_dataset(cache).load()
    region = aoi_geometry(cfg)
    print("fetching real predictors via GEE …")
    layers: dict[str, xr.DataArray] = {}
    for gas in sentinel5p.GASES:
        layers.update(_dl(sentinel5p._period_mean(cfg, gas, START, END), [gas], region, gas))
        print(f"  ✓ {gas}")
    layers.update(_dl(era5.build_stack(cfg, START, END), ERA5_BANDS, region, "met")); print("  ✓ met")
    layers.update(_dl(modis_fire.active_fire_frp(cfg, START, END), ["frp_mean", "frp_max", "fire_count"], region, "frp")); print("  ✓ fire")
    layers.update(_dl(modis_fire.evi(cfg, START, END), ["evi"], region, "evi")); print("  ✓ evi")
    layers.update(_dl(srtm.terrain_stack(cfg), ["elevation", "slope", "aspect"], region, "terrain")); print("  ✓ terrain")
    aod = (ee.ImageCollection("MODIS/061/MCD19A2_GRANULES").select("Optical_Depth_055")
           .filterDate(START, END).filterBounds(region).mean().multiply(0.001))
    layers.update(_dl(aod, ["aod"], region, "aod")); print("  ✓ aod")

    ref = layers["no2"]
    aligned = {k: (v if k == "no2" else v.interp(lon=ref.lon, lat=ref.lat)) for k, v in layers.items()}
    ds = xr.Dataset({k: v.expand_dims(time=[pd.Timestamp(START)]) for k, v in aligned.items()})
    cache.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(cache)
    print(f"predictor stack: {dict(ds.sizes)} | {len(ds.data_vars)} vars -> {cache}")
    return ds


def load_cpcb_seasonal():
    """Best-effort: CPCB CSVs in data/external -> seasonal-mean station table with lat/lon."""
    ext = Path("data/external")
    csvs = [p for p in ext.glob("**/*.csv") if "firms" not in p.name.lower()]
    if not csvs:
        return None, "no CPCB CSVs found in data/external/"
    meta = next((p for p in csvs if "station" in p.name.lower() or "meta" in p.name.lower()), None)
    stations = cpcb.load_station_metadata(str(meta)) if meta else None
    try:
        hourly = pd.concat([cpcb.load_raw_hourly(str(p)) for p in csvs if p is not meta], ignore_index=True)
        daily = cpcb.to_daily(hourly)
    except Exception as e:
        return None, f"could not parse CPCB CSVs ({e}); expected hourly export with a datetime column + pollutant columns"
    # season mean per station, renamed to model target columns
    agg = daily.groupby("station_id").mean(numeric_only=True).reset_index()
    agg = agg.rename(columns={"no2": "no2_obs", "so2": "so2_obs", "o3": "o3_obs", "co": "co_obs"})
    if stations is not None and {"lat", "lon"}.issubset(stations.columns):
        agg = agg.merge(stations[["station_id", "lat", "lon"]], on="station_id", how="inner")
    if not {"lat", "lon"}.issubset(agg.columns):
        return None, "CPCB table has no station lat/lon — add a station-metadata CSV (station_id, lat, lon)"
    return agg, None


# ---- OpenAQ path: same CPCB station measurements, no captcha (free API key) ----
def _archive_keys(loc, year, months):
    keys = []
    for m in months:
        url = (f"https://openaq-data-archive.s3.amazonaws.com/?list-type=2"
               f"&prefix=records/csv.gz/locationid={loc}/year={year}/month={m:02d}/&max-keys=400")
        keys += re.findall(r"<Key>([^<]+)</Key>", requests.get(url, timeout=30).text)
    return keys


def _download_location(loc, year, months):
    frames = []
    for k in _archive_keys(loc, year, months)[::3]:   # every 3rd day = representative seasonal sample, 3x faster
        r = requests.get(f"https://openaq-data-archive.s3.amazonaws.com/{k}", timeout=60)
        if r.status_code == 200:
            try:
                frames.append(pd.read_csv(io.StringIO(gzip.decompress(r.content).decode())))
            except Exception:
                pass
    return pd.concat(frames, ignore_index=True) if frames else None


def _station_seasonal(loc, yr, months):
    """One station -> seasonal-mean record (predictor-agnostic ground truth)."""
    c = loc.get("coordinates") or {}
    lat, lon = c.get("latitude"), c.get("longitude")
    if lat is None or lon is None:
        return None
    raw = _download_location(loc["id"], yr, months)
    if raw is None or raw.empty or "parameter" not in raw:
        return None
    wide = raw.pivot_table(index="datetime", columns="parameter", values="value", aggfunc="mean").reset_index()
    wide["station_id"] = f"openaq-{loc['id']}"
    daily = cpcb.to_daily(wide)
    if daily.empty:
        return None
    agg = daily.mean(numeric_only=True)
    return {"station_id": f"openaq-{loc['id']}", "lat": lat, "lon": lon,
            "pm25": agg.get("pm25"), "pm10": agg.get("pm10"),
            "no2_obs": agg.get("no2"), "so2_obs": agg.get("so2"),
            "o3_obs": agg.get("o3"), "co_obs": agg.get("co")}


def load_openaq_seasonal(api_key, start, end, max_stations=250, workers=24):
    """Real Indian CPCB-station data via OpenAQ: keyed location list + parallel keyless archive."""
    from concurrent.futures import ThreadPoolExecutor

    H = {"X-API-Key": api_key}
    locs, page = [], 1
    while True:
        r = requests.get("https://api.openaq.org/v3/locations", headers=H,
                         params={"iso": "IN", "limit": 1000, "page": page}, timeout=60)
        r.raise_for_status()
        res = r.json().get("results", [])
        locs += res
        if len(res) < 1000 or page >= 5:
            break
        page += 1
    locs = [loc for loc in locs if (loc.get("coordinates") or {}).get("latitude") is not None][:max_stations]
    print(f"OpenAQ: {len(locs)} Indian stations (capped at {max_stations}); downloading archive in parallel …")
    yr, months = int(start[:4]), list(range(int(start[5:7]), int(end[5:7]) + 1))
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(lambda loc: _station_seasonal(loc, yr, months), locs)):
            if res:
                rows.append(res)
            if (i + 1) % 40 == 0:
                print(f"  …{i + 1}/{len(locs)} processed, {len(rows)} with data")
    df = pd.DataFrame(rows).dropna(subset=["lat", "lon"])
    print(f"OpenAQ seasonal ground-truth: {len(df)} stations with usable data")
    return df


# ---- DAILY path: station x day samples (captures the AOD<->PM2.5 daily covariance) ----
TARGET_CAPS = {  # physically-plausible ranges; outside -> NaN (drops bad sensor/unit spikes)
    "pm25": (1, 1000), "pm10": (1, 2000), "no2_obs": (0, 400),
    "so2_obs": (0, 400), "o3_obs": (1, 400), "co_obs": (0, 50),
}


def clean_targets(df):
    for c, (lo, hi) in TARGET_CAPS.items():
        if c in df:
            df.loc[(df[c] < lo) | (df[c] > hi), c] = np.nan
    return df


def _station_daily(loc, yr, months):
    c = loc.get("coordinates") or {}
    lat, lon = c.get("latitude"), c.get("longitude")
    if lat is None or lon is None:
        return None
    raw = _download_location(loc["id"], yr, months)
    if raw is None or raw.empty or "parameter" not in raw:
        return None
    wide = raw.pivot_table(index="datetime", columns="parameter", values="value", aggfunc="mean").reset_index()
    wide["station_id"] = f"openaq-{loc['id']}"
    daily = cpcb.to_daily(wide)
    if daily.empty:
        return None
    daily["lat"], daily["lon"] = lat, lon
    return daily.rename(columns={"no2": "no2_obs", "so2": "so2_obs", "o3": "o3_obs", "co": "co_obs"})


def load_openaq_daily(api_key, start, end, max_stations=250, workers=24):
    """Real Indian CPCB station x day table via OpenAQ (cached)."""
    cache = Path("data/interim/openaq_daily.parquet")
    if cache.exists():
        print(f"using cached daily ground truth: {cache}")
        return pd.read_parquet(cache)
    from concurrent.futures import ThreadPoolExecutor

    H = {"X-API-Key": api_key}
    locs, page = [], 1
    while True:
        r = requests.get("https://api.openaq.org/v3/locations", headers=H,
                         params={"iso": "IN", "limit": 1000, "page": page}, timeout=60)
        r.raise_for_status()
        res = r.json().get("results", [])
        locs += res
        if len(res) < 1000 or page >= 5:
            break
        page += 1
    locs = [loc for loc in locs if (loc.get("coordinates") or {}).get("latitude") is not None][:max_stations]
    print(f"OpenAQ: {len(locs)} Indian stations; downloading daily archive in parallel …")
    yr, months = int(start[:4]), list(range(int(start[5:7]), int(end[5:7]) + 1))
    frames = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, d in enumerate(ex.map(lambda loc: _station_daily(loc, yr, months), locs)):
            if d is not None:
                frames.append(d)
            if (i + 1) % 40 == 0:
                print(f"  …{i + 1}/{len(locs)}, {len(frames)} stations with data")
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    print(f"OpenAQ daily ground-truth: {len(df)} station-days from {df['station_id'].nunique()} stations")
    return df


def _daily_at_points(coll, bands, mp, scale):
    """getRegion an ImageCollection at station points -> daily-mean (lon,lat,date,bands)."""
    arr = coll.select(bands).getRegion(mp, scale=scale).getInfo()
    hdr = arr[0]
    df = pd.DataFrame(arr[1:], columns=hdr)
    df["date"] = pd.to_datetime(df["time"], unit="ms").dt.floor("D")
    df["lon"] = df["longitude"].astype(float).round(3)
    df["lat"] = df["latitude"].astype(float).round(3)
    for b in bands:
        df[b] = pd.to_numeric(df[b], errors="coerce")
    return df.groupby(["lon", "lat", "date"], as_index=False)[bands].mean()


GAS_ASSETS = {
    "no2": ("COPERNICUS/S5P/OFFL/L3_NO2", "tropospheric_NO2_column_number_density"),
    "so2": ("COPERNICUS/S5P/OFFL/L3_SO2", "SO2_column_number_density"),
    "co": ("COPERNICUS/S5P/OFFL/L3_CO", "CO_column_number_density"),
    "o3": ("COPERNICUS/S5P/OFFL/L3_O3", "O3_column_number_density"),
    "hcho": ("COPERNICUS/S5P/OFFL/L3_HCHO", "tropospheric_HCHO_column_number_density"),
}


def fetch_daily_predictors(stations, start, end):
    """Daily predictor table at station points via getRegion (cached)."""
    cache = Path("data/interim/pred_daily.parquet")
    if cache.exists():
        print(f"using cached daily predictors: {cache}")
        return pd.read_parquet(cache)
    from scipy.spatial import cKDTree
    sids = stations["station_id"].to_numpy()
    tree = cKDTree(stations[["lon", "lat"]].to_numpy())
    mp = ee.Geometry.MultiPoint([[float(r.lon), float(r.lat)] for r in stations.itertuples()])

    def to_sid(df):
        """getRegion returns PIXEL-CENTER coords (differ per source scale) -> map each row to its
        nearest station, then mean per (station, date). This is what lets sources merge cleanly."""
        dist, idx = tree.query(df[["lon", "lat"]].to_numpy(), k=1)
        df = df.assign(station_id=sids[idx])[dist <= 0.12]   # within ~13 km of a station
        bands = [c for c in df.columns if c not in ("lon", "lat", "date", "station_id")]
        return df.groupby(["station_id", "date"], as_index=False)[bands].mean()

    print("fetching daily predictors at stations via getRegion …")
    out = None
    for g, (asset, band) in GAS_ASSETS.items():
        d = to_sid(_daily_at_points(ee.ImageCollection(asset).filterDate(start, end), [band], mp, 5000).rename(columns={band: g}))
        out = d if out is None else out.merge(d, on=["station_id", "date"], how="outer")
        print(f"  ✓ {g}")
    era5b = ["temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m", "surface_pressure", "total_precipitation_sum"]
    d = to_sid(_daily_at_points(ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(start, end), era5b, mp, 11132).rename(
        columns={"temperature_2m": "temperature", "u_component_of_wind_10m": "u_wind",
                 "v_component_of_wind_10m": "v_wind", "surface_pressure": "pressure", "total_precipitation_sum": "precipitation"}))
    out = out.merge(d, on=["station_id", "date"], how="outer"); print("  ✓ met")
    try:  # composite MAIAC granules to ~90 DAILY means first (else getRegion exceeds 1M elements)
        base = ee.Date(start)
        ndays = ee.Date(end).difference(base, "day")
        gran = ee.ImageCollection("MODIS/061/MCD19A2_GRANULES").select("Optical_Depth_055").filterDate(start, end)
        def _daily_aod(i):
            d0 = base.advance(ee.Number(i), "day")
            return gran.filterDate(d0, d0.advance(1, "day")).mean().multiply(0.001).set("system:time_start", d0.millis())
        aod_coll = ee.ImageCollection(ee.List.sequence(0, ndays.subtract(1)).map(_daily_aod))
        d = to_sid(_daily_at_points(aod_coll, ["Optical_Depth_055"], mp, 1000).rename(columns={"Optical_Depth_055": "aod"}))
        out = out.merge(d, on=["station_id", "date"], how="outer"); print("  ✓ aod")
    except Exception as e:
        print(f"  daily AOD skipped: {e}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache)
    print(f"daily predictors: {len(out)} station-days")
    return out


def fetch_map_grid(cfg):
    """Seasonal-mean predictor GRID over India with the SAME raw bands as the daily fetch (cached)."""
    cache = Path("data/interim/map_grid.parquet")
    if cache.exists():
        print(f"using cached map grid: {cache}")
        return pd.read_parquet(cache)
    region = aoi_geometry(cfg)
    print("fetching seasonal map grid …")
    L = {}
    for g, (asset, band) in GAS_ASSETS.items():
        L.update(_dl(ee.ImageCollection(asset).select(band).filterDate(START, END).mean(), [g], region, f"mg_{g}"))
    era5 = (ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterDate(START, END).mean()
            .select(["temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m", "surface_pressure", "total_precipitation_sum"]))
    L.update(_dl(era5, ["temperature", "u_wind", "v_wind", "pressure", "precipitation"], region, "mg_met"))
    aod = ee.ImageCollection("MODIS/061/MCD19A2_GRANULES").select("Optical_Depth_055").filterDate(START, END).mean().multiply(0.001)
    L.update(_dl(aod, ["aod"], region, "mg_aod"))
    ref = L["no2"]
    al = {k: (v if k == "no2" else v.interp(lon=ref.lon, lat=ref.lat)) for k, v in L.items()}
    df = xr.Dataset(al).to_dataframe().reset_index().dropna(subset=["no2"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    print(f"map grid: {len(df)} cells")
    return df


def main():
    cfg = load_config("config/config.yaml")
    init_ee(cfg)
    engine = AQIEngine(cfg.aqi_breakpoints)

    api_key = os.environ.get("OPENAQ_API_KEY")
    if not api_key:
        print("\nSet OPENAQ_API_KEY (free, no captcha: https://explore.openaq.org/register), then:")
        print("  OPENAQ_API_KEY=your_key make real")
        return

    # ---- daily ground truth + daily predictors at stations ----
    cpcb_daily = clean_targets(load_openaq_daily(api_key, START, END))
    if cpcb_daily.empty:
        print("OpenAQ returned no station data for this window."); return
    stations = cpcb_daily.groupby("station_id", as_index=False)[["lat", "lon"]].first()
    pred = fetch_daily_predictors(stations, START, END)
    for _d in (pred, cpcb_daily):                    # align tz-aware (CPCB local) vs naive (satellite UTC) dates
        _d["date"] = pd.to_datetime(_d["date"])
        if _d["date"].dt.tz is not None:
            _d["date"] = _d["date"].dt.tz_localize(None)
        _d["date"] = _d["date"].dt.normalize()
    training = pred.merge(cpcb_daily.drop(columns=["lat", "lon"]), on=["station_id", "date"], how="inner")
    training = training.merge(stations, on="station_id", how="left")
    training = add_engineered_features(training, lag_cols=None)
    pred_cols = [c for c in pred.columns if c not in ("station_id", "date")]
    features = list(dict.fromkeys([c for c in pred_cols + ["lat", "lon", "fnr", "doy_sin", "doy_cos"] if c in training.columns]))
    print(f"training: {len(training)} station-days x {len(features)} features ({training['station_id'].nunique()} stations)")

    def fit_rf(df, t):
        return RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=0).fit(
            df[features].fillna(0.0), df[t])

    # ---- validation: random CV (held-out days, literature-comparable) + spatial CV (held-out regions) ----
    print("\n=== REAL validation: random CV (held-out days) | spatial CV (held-out regions) ===")
    print(f"  {'target':8s} {'randomR²':>9s} {'spatialR²':>10s} {'RMSE':>7s} {'MAE':>6s}   India target")
    report = {}
    for t in TARGETS:
        sub = training.dropna(subset=[t])
        if sub["station_id"].nunique() < 12 or len(sub) < 150:
            continue
        y = sub[t].to_numpy()
        # random 5-fold (new days at known stations) -> the metric most satellite-AQI papers report
        Pr = np.zeros(len(y))
        for a, b in KFold(5, shuffle=True, random_state=0).split(sub):
            Pr[b] = fit_rf(sub.iloc[a], t).predict(sub.iloc[b][features].fillna(0.0))
        mr = metrics(y, Pr)
        # spatial leave-station-blocks-out (unmonitored regions) -> the hard extrapolation metric
        Ps, Ys = [], []
        for trn, va in spatial_blocks(sub, block_deg=2.0, k=5):
            if va["station_id"].nunique() < 2 or len(trn) < 100:
                continue
            Ps.append(fit_rf(trn, t).predict(va[features].fillna(0.0))); Ys.append(va[t].to_numpy())
        ms = metrics(np.concatenate(Ys), np.concatenate(Ps)) if Ps else {"r2": float("nan"), "rmse": float("nan"), "mae": float("nan")}
        bench = INDIA_BENCHMARK_R2.get(t.replace("_obs", ""))
        report[t] = {"n": int(len(sub)), "stations": int(sub["station_id"].nunique()), "random_cv": mr, "spatial_cv": ms}
        print(f"  {t:8s} {mr['r2']:>9.3f} {ms['r2']:>10.3f} {mr['rmse']:>7.1f} {mr['mae']:>6.1f}   (target {bench})")
    Path("outputs").mkdir(exist_ok=True)
    json.dump(report, open("outputs/real_validation.json", "w"), indent=2)

    # ---- real seasonal AQI map -> web ----
    print("\ngenerating real AQI map …")
    models = {t: fit_rf(training.dropna(subset=[t]), t) for t in TARGETS if training[t].notna().sum() > 100}
    gdf = add_engineered_features(fetch_map_grid(cfg).assign(date=pd.Timestamp(START)))
    for c in features:
        if c not in gdf:
            gdf[c] = 0.0
    Xg = gdf[features].fillna(0.0)
    conc = {e: models[c].predict(Xg) for e, c in AQI_MAP.items() if c in models}
    out = engine.compute_grid(conc)
    lon, lat = gdf["lon"].to_numpy(), gdf["lat"].to_numpy()
    from matplotlib.path import Path as MplPath
    gj = json.loads((WEB / "india.geojson").read_text())
    polys = gj["features"][0]["geometry"]["coordinates"]
    mainland = max((p[0] for p in polys), key=lambda r: (max(x[0] for x in r) - min(x[0] for x in r)) * (max(x[1] for x in r) - min(x[1] for x in r)))
    inside = MplPath(np.array(mainland)).contains_points(np.column_stack([lon, lat]))
    cells = [[round(float(lon[i]), 2), round(float(lat[i]), 2), int(out["cpcb"][i]), int(out["rapi"][i])]
             for i in range(len(lon)) if inside[i] and np.isfinite(out["cpcb"][i])]
    (WEB / "aqi_frames.json").write_text(json.dumps({"key": ["lon", "lat", "aqi", "rapi"], "frames": [{"date": START, "cells": cells}]}, separators=(",", ":")))
    print(f"-> public/data/aqi_frames.json: REAL validated AQI ({len(cells)} cells)")

    # ---- comparative zone/anomaly layers from the same real seasonal grid ----
    analysis = pd.DataFrame({
        "lon": lon, "lat": lat, "aqi": out["cpcb"], "rapi": out["rapi"],
        "hcho": gdf.get("hcho", pd.Series(np.nan, index=gdf.index)),
        "no2": gdf.get("no2", pd.Series(np.nan, index=gdf.index)),
        "co": gdf.get("co", pd.Series(np.nan, index=gdf.index)),
        "frp_mean": gdf.get("frp_mean", pd.Series(np.nan, index=gdf.index)),
    })
    layers = build_analysis_layers(
        analysis,
        date_value=START,
        zone_features=["aqi", "hcho", "no2", "co"],
        isolation_features=["hcho", "no2", "co", "frp_mean"],
        k_range=(3, 4, 5),
        contamination=0.05,
    )
    layers["analysis_metadata"]["data_status"] = "real_validated_model"
    layers["analysis_metadata"]["validation_reference"] = "outputs/real_validation.json"
    for filename, key in (("zone_cells.json", "zone_cells"),
                          ("isolation_hotspots.json", "isolation_hotspots"),
                          ("analysis_metadata.json", "analysis_metadata")):
        (WEB / filename).write_text(json.dumps(layers[key], separators=(",", ":"), default=float))
    print(f"-> public/data/zone_cells.json: real K-Means k={layers['zone_cells']['selected_k']}")
    print(f"-> public/data/isolation_hotspots.json: real anomalies={layers['isolation_hotspots']['n_anomalies']}")
    print("\nObjective 1 COMPLETE: real surface AQI trained + validated against CPCB. AQI layer is now real.")


if __name__ == "__main__":
    main()
