#!/usr/bin/env python
"""End-to-end demonstration of the FULL redesigned pipeline on synthetic India data.

Runs every stage with no external credentials, producing real artifacts and
exercising the 6 redesign changes (see docs/REDESIGN_PLAN.md):

  [1] synthetic ingestion -> stack + stations + observations + fires
  [2] AOD gap-fill        inject ~clustered missingness, fill with RF + clustered CV   (Change 1)
  [3] collocate + features unified training table (FNR, cyclical time, lags)
  [4] NO2 calibration     TROPOMI column -> CPCB surface NO2 (regression)              (Change 2)
  [5] hybrid model        trend (RF) + kriged residual; trend-vs-hybrid + benchmark    (Changes 3,6)
  [6] PM2.5 3-scheme CV   random vs spatial vs temporal (autocorrelation leakage)      (Change 6)
  [7] CNN-LSTM            the ISRO-specified spatio-temporal learner
  [8] dual AQI atlas      CPCB (Main) + RAPI (USP) + RAPI-CPCB divergence maps          (dual index)
  [9] HCHO hotspots       PHV + Getis-Ord Gi* -> connected clusters -> attribution     (Change 5)
  [10] transport          ERA5 back-trajectory + VIIRS fires-along-path

    python pipelines/run_demo.py            # full demo (~few minutes)
    python pipelines/run_demo.py --fast     # tiny/quick smoke run

Swapping synthetic -> real data means only providing credentials + running the
ingestion modules; every downstream stage below is unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import numpy as np

import pandas as pd
import xarray as xr

from isro_aqi.aqi import AQIEngine
from isro_aqi.analysis_layers import build_analysis_layers
from isro_aqi.database.schema import PREDICTORS
from isro_aqi.features import add_engineered_features
from isro_aqi.models import baselines
from isro_aqi.models.hybrid import INDIA_BENCHMARK_R2, HybridModel, evaluate_trend_vs_hybrid
from isro_aqi.preprocessing.calibrate_no2 import NO2Calibrator
from isro_aqi.preprocessing.collocate import join_targets, sample_at_stations
from isro_aqi.preprocessing.gapfill_aod import fill_aod_stack, inject_aod_gaps
from isro_aqi.synthetic import SyntheticConfig, generate_all
from isro_aqi.utils.geo import Grid
from isro_aqi.utils.io import ensure_dir, write_parquet
from isro_aqi.utils.logging import get_logger

warnings.filterwarnings("ignore", category=RuntimeWarning)
log = get_logger("demo")

TARGETS = ["pm25", "pm10", "no2_obs", "so2_obs", "o3_obs", "co_obs"]
# engine pollutant -> training/target column
AQI_MAP = {"pm25": "pm25", "pm10": "pm10", "no2": "no2_obs",
           "so2": "so2_obs", "o3": "o3_obs", "co": "co_obs"}
FIG = "outputs/figures"
MAP = "outputs/maps"


def _date_split(df, frac=0.2):
    """Temporal split: last `frac` of unique dates -> test."""
    dates = np.sort(df["date"].unique())
    cut = dates[int(len(dates) * (1 - frac))]
    return df[df["date"] < cut], df[df["date"] >= cut]


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="tiny quick run")
    ap.add_argument("--config", default=None, help="(optional) config for AQI breakpoints/regions")
    args = ap.parse_args()

    for d in (FIG, MAP, "data/interim", "data/processed", "models", "outputs"):
        ensure_dir(d)
    summary: dict = {}

    import yaml
    bp = yaml.safe_load(open("config/aqi_breakpoints.yaml"))
    regions = yaml.safe_load(open("config/regions.yaml"))
    engine = AQIEngine(bp)

    # ===== [1] synthetic ingestion ========================================
    scfg = SyntheticConfig(
        resolution_deg=1.0 if args.fast else 0.5,
        n_days=15 if args.fast else 60,
        n_stations=30 if args.fast else 120,
    )
    log.info(f"[1/10] generating synthetic India data {scfg}")
    data = generate_all(scfg)
    stack, stations, obs, fires = data["stack"], data["stations"], data["observations"], data["fires"]
    grid = Grid(scfg.bbox, scfg.resolution_deg)

    # ===== [2] AOD gap-fill (Change 1) ====================================
    log.info("[2/10] AOD gap-fill: inject clustered missingness + RF fill")
    gappy = inject_aod_gaps(stack, frac=0.3, seed=scfg.seed)
    stack, gf_report = fill_aod_stack(gappy, report_cv=not args.fast)
    summary["aod_gapfill"] = {k: gf_report[k] for k in gf_report if k != "covariates"}
    log.info(f"   missing {gf_report['missing_frac']*100:.0f}% filled; "
             f"clustered-CV r2={gf_report.get('cv_r2')}")

    write_parquet(stations, "data/processed/stations.parquet")
    write_parquet(obs, "data/processed/cpcb_daily.parquet")
    write_parquet(fires, "data/processed/fire_pixels.parquet")
    stack.to_netcdf("data/interim/daily.nc")

    # ===== [3] collocate + features =======================================
    predictors = sample_at_stations(stack, stations)
    training = join_targets(predictors, obs)
    training = add_engineered_features(training, lag_cols=None)
    features = [c for c in PREDICTORS if c in training.columns]
    write_parquet(training, "data/processed/training.parquet")
    summary["training_rows"] = int(len(training))
    summary["n_features"] = len(features)
    log.info(f"[3/10] training table: {len(training):,} rows x {len(features)} features")

    # ===== [4] NO2 calibration (Change 2) =================================
    log.info("[4/10] TROPOMI NO2 -> surface calibration")
    cal = NO2Calibrator().fit(training)
    summary["no2_calibration"] = cal.report(training)
    cal.save("models/no2_calibration.joblib")
    log.info(f"   surface-NO2 r2={summary['no2_calibration']['r2']:.3f} "
             f"(raw column r2={summary['no2_calibration'].get('raw_column_r2')})")

    # ===== [5] hybrid trend + kriging residual (Changes 3, 6) =============
    tr, te = _date_split(training, 0.2)
    log.info(f"[5/10] hybrid (RF trend + kriged residual); split {len(tr):,}/{len(te):,}")
    summary["hybrid"] = evaluate_trend_vs_hybrid(tr, te, TARGETS, features)
    for t in TARGETS:
        m = summary["hybrid"].get(t)
        if m:
            log.info(f"   {t:8s} trend R2={m['trend']['r2']:.3f} -> hybrid R2={m['hybrid']['r2']:.3f}"
                     f" (India target {m['benchmark_r2']})")

    # ===== [6] PM2.5 3-scheme CV (Change 6) ===============================
    summary["cv_pm25"] = _cv_comparison(training, features)
    log.info(f"[6/10] PM2.5 CV R2 -> random {summary['cv_pm25']['random']:.3f} | "
             f"spatial {summary['cv_pm25']['spatial']:.3f} | temporal {summary['cv_pm25']['temporal']:.3f}")

    # ===== [7] CNN-LSTM (ISRO-specified learner) ==========================
    summary["cnn_lstm"] = _train_cnn_lstm(stack, training, grid, args.fast)
    log.info("[7/10] CNN-LSTM val: "
             + ", ".join(f"{k} R2={v['r2']:.2f}" for k, v in summary["cnn_lstm"].items()))

    # ===== [8] dual AQI atlas: CPCB + RAPI + divergence ===================
    log.info("[8/10] dual AQI atlas (CPCB Main + RAPI USP + divergence)")
    hybrid_full = HybridModel(TARGETS, features).fit(training)
    import joblib
    joblib.dump(hybrid_full, "models/hybrid.joblib")          # for export_web.py / inference
    burn_idx = int(np.argmax([float(stack["frp_mean"].isel(time=i).mean())
                              for i in range(stack.sizes["time"])]))
    summary["aqi"] = _aqi_maps(stack, hybrid_full, features, engine, burn_idx)

    # ===== [9] HCHO hotspots (Change 5) ===================================
    log.info("[9/10] HCHO hotspots: PHV + Gi* -> connected clusters -> attribution")
    summary["hcho"] = _hcho_analysis(stack, fires, regions)

    # ===== [9b] comparative analysis layers ================================
    log.info("[9b/10] K-Means pollution zones + Isolation Forest comparison")
    summary["analysis_layers"] = _analysis_layers(stack, hybrid_full, features, engine, burn_idx)

    # ===== [10] transport =================================================
    log.info("[10/10] transport: back-trajectory + fires-along-path")
    summary["transport"] = _transport(stack, fires)

    with open("outputs/demo_summary.json", "w", encoding="utf-8") as fh:
        json.dump(_jsonable(summary), fh, indent=2)

    _write_summary_md(summary)
    log.info("DEMO COMPLETE -> see outputs/ (maps, figures, demo_summary.md)")


# --------------------------------------------------------------------------- #
def _cv_comparison(training, features, target="pm25"):
    from sklearn.model_selection import train_test_split

    from isro_aqi.models.train import spatial_blocks
    df = training.dropna(subset=[target])
    a, b = train_test_split(df, test_size=0.2, random_state=0)
    m = baselines.RandomForestModel([target], features, n_estimators=150).fit(a)
    r_random = baselines.metrics(b[target].to_numpy(), m.predict(b)[target].to_numpy())["r2"]
    tr, va = next(spatial_blocks(df, block_deg=2.0, k=5))
    m = baselines.RandomForestModel([target], features, n_estimators=150).fit(tr)
    r_spatial = baselines.metrics(va[target].to_numpy(), m.predict(va)[target].to_numpy())["r2"]
    tr, te = _date_split(df, 0.2)
    m = baselines.RandomForestModel([target], features, n_estimators=150).fit(tr)
    r_temporal = baselines.metrics(te[target].to_numpy(), m.predict(te)[target].to_numpy())["r2"]
    return {"random": r_random, "spatial": r_spatial, "temporal": r_temporal}


def _train_cnn_lstm(stack, training, grid, fast):
    from isro_aqi.models.cnn_lstm import PollutantCNNLSTM
    from isro_aqi.models.dataset import PatchSequenceDataset, Standardizer
    from isro_aqi.models.train import train_model

    channels = list(stack.data_vars)
    samples = training[["date"]].copy()
    samples["lon"] = training["lon_meta"].values if "lon_meta" in training else training["lon"].values
    samples["lat"] = training["lat_meta"].values if "lat_meta" in training else training["lat"].values
    for t in TARGETS:
        samples[t] = training[t].values
    tr, va = _date_split(samples, 0.2)

    std = Standardizer.fit(stack, channels)
    tmean = np.array([np.nanmean(tr[t]) for t in TARGETS])
    tstd = np.array([np.nanstd(tr[t]) for t in TARGETS])
    P, T = (5, 3) if fast else (7, 5)
    mk = lambda df: PatchSequenceDataset(  # noqa: E731
        stack, df, channels, TARGETS, grid, patch_size=P, sequence_length=T,
        standardizer=std, target_mean=tmean, target_std=tstd,
    )
    model = PollutantCNNLSTM(len(channels), len(TARGETS), patch_size=P)
    train_model(
        model, mk(tr), mk(va), TARGETS,
        epochs=5 if fast else 30, batch_size=128, lr=1e-3, patience=8,
        ckpt_path="models/cnn_lstm_demo.pt", num_workers=0,
    )
    return _eval_cnn_lstm(model, mk(va), tmean, tstd)


def _eval_cnn_lstm(model, ds_va, tmean, tstd):
    import torch
    from torch.utils.data import DataLoader

    from isro_aqi.models.train import select_device
    dev = select_device("auto")
    model = model.to(dev).eval()
    preds, trues = [], []
    with torch.no_grad():
        for x, y in DataLoader(ds_va, batch_size=128):
            preds.append(model(x.to(dev)).cpu().numpy())
            trues.append(y.numpy())
    P = np.vstack(preds) * tstd + tmean
    Y = np.vstack(trues) * tstd + tmean
    return {t: baselines.metrics(Y[:, i], P[:, i]) for i, t in enumerate(TARGETS)}


def _predict_grid(day_ds, model, features, date):
    """Predict pollutant grids for one day's Dataset -> dict of 2-D arrays.

    `model` is any object with .predict(df)->DataFrame (RF or HybridModel); the
    hybrid additionally uses the lon/lat columns for the kriged residual.
    """
    df = day_ds.to_dataframe().reset_index()
    df["date"] = pd.Timestamp(date)
    df = add_engineered_features(df, lag_cols=None)
    for c in features:
        if c not in df:
            df[c] = 0.0
    pred = model.predict(df)
    lat, lon = day_ds["lat"].values, day_ds["lon"].values
    out = {}
    for t in pred.columns:
        piv = df.assign(_p=pred[t].values).pivot_table(index="lat", columns="lon", values="_p")
        out[t] = piv.reindex(index=lat, columns=lon).values
    return out, lat, lon


def _aqi_maps(stack, model, features, engine, burn_idx):
    from isro_aqi.viz.maps import aqi_map, scalar_map

    date = pd.to_datetime(stack["time"].values[burn_idx])
    grids, lat, lon = _predict_grid(stack.isel(time=burn_idx), model, features, date)
    conc = {eng: grids[col] for eng, col in AQI_MAP.items() if col in grids}
    out = engine.compute_grid(conc)              # cpcb, rapi, dominant, divergence
    coords = {"lat": lat, "lon": lon}

    cpcb_da = xr.DataArray(out["cpcb"], coords=coords, dims=("lat", "lon"))
    rapi_da = xr.DataArray(out["rapi"], coords=coords, dims=("lat", "lon"))
    div_da = xr.DataArray(out["divergence"], coords=coords, dims=("lat", "lon"))

    # Main view: CPCB headline (official compliance)
    aqi_map(cpcb_da, title=f"Surface AQI — CPCB (Main view) {date.date()}",
            out_path=f"{MAP}/aqi_cpcb_{date.date()}.png")
    # USP view: RAPI headline (entropy multi-pollutant), same CPCB ramp
    aqi_map(rapi_da, title=f"Surface AQI — RAPI entropy (USP view) {date.date()}",
            out_path=f"{MAP}/aqi_rapi_{date.date()}.png")
    # Divergence: where RAPI reclassifies cells the CPCB max rule misses
    scalar_map(div_da, title=f"RAPI − CPCB divergence {date.date()}", cmap="magma",
               label="RAPI − CPCB", out_path=f"{MAP}/aqi_divergence_{date.date()}.png")
    scalar_map(xr.DataArray(grids["pm25"], coords=coords, dims=("lat", "lon")),
               title=f"Predicted PM2.5 {date.date()}", cmap="magma_r", label="PM2.5 (ug/m3)",
               out_path=f"{MAP}/pm25_{date.date()}.png")

    # seasonal-mean CPCB AQI
    mean_ds = stack.mean("time")
    mgrids, mlat, mlon = _predict_grid(mean_ds, model, features, date)
    mconc = {eng: mgrids[col] for eng, col in AQI_MAP.items() if col in mgrids}
    mcpcb = engine.aqi_grid(mconc)[0]
    aqi_map(xr.DataArray(mcpcb, coords={"lat": mlat, "lon": mlon}, dims=("lat", "lon")),
            title="Seasonal-mean Surface AQI — CPCB", out_path=f"{MAP}/aqi_seasonal_mean.png")

    cpcb = out["cpcb"]
    cats = {}
    for v in cpcb[np.isfinite(cpcb)]:
        c = engine.category(float(v))
        cats[c] = cats.get(c, 0) + 1
    return {"date": str(date.date()),
            "cpcb_mean": float(np.nanmean(cpcb)), "cpcb_max": float(np.nanmax(cpcb)),
            "rapi_mean": float(np.nanmean(out["rapi"])),
            "divergence_mean": float(np.nanmean(out["divergence"][np.isfinite(out["divergence"])])),
            "category_cells": cats}


def _analysis_layers(stack, model, features, engine, burn_idx):
    """Export the plan's K-Means and Isolation Forest layers beside VAYU outputs."""
    from isro_aqi.hcho import phv

    date = pd.to_datetime(stack["time"].values[burn_idx])
    grids, lat, lon = _predict_grid(stack.isel(time=burn_idx), model, features, date)
    conc = {eng: grids[col] for eng, col in AQI_MAP.items() if col in grids}
    aqi = engine.compute_grid(conc)
    hcho = stack["hcho"].isel(time=burn_idx)
    fields = {
        "lat": np.repeat(lat, len(lon)),
        "lon": np.tile(lon, len(lat)),
        "aqi": aqi["cpcb"].ravel(),
        "rapi": aqi["rapi"].ravel(),
        "hcho": hcho.values.ravel(),
    }
    for name in ("no2", "co", "frp_mean"):
        if name in stack:
            fields[name] = stack[name].isel(time=burn_idx).values.ravel()
    grid_df = pd.DataFrame(fields)
    phv_mask = phv.detect_hotspots(
        hcho, phv_min=1.05, hva_threshold=8e15, to_molec_cm2=1.0
    )["hva"].values.ravel()
    layers = build_analysis_layers(
        grid_df,
        date_value=date,
        phv_mask=phv_mask,
        zone_features=["aqi", "hcho", "no2", "co"],
        isolation_features=["hcho", "no2", "co", "frp_mean"],
        k_range=(3, 4, 5),
        contamination=0.05,
    )
    layers["analysis_metadata"]["data_status"] = "synthetic_demo"
    ensure_dir("public/data")
    for filename, key in (("zone_cells.json", "zone_cells"),
                          ("isolation_hotspots.json", "isolation_hotspots"),
                          ("analysis_metadata.json", "analysis_metadata")):
        with open(f"public/data/{filename}", "w") as fh:
            json.dump(_jsonable(layers[key]), fh, separators=(",", ":"))
    return {
        "selected_k": layers["zone_cells"]["selected_k"],
        "zone_silhouette": layers["zone_cells"]["candidate_silhouette"],
        "isolation_anomalies": layers["isolation_hotspots"]["n_anomalies"],
        "isolation_clusters": layers["isolation_hotspots"]["n_clusters"],
        "phv_comparison": layers["isolation_hotspots"].get("phv_comparison"),
    }


def _hcho_analysis(stack, fires, regions):
    """HCHO hotspots on the burning-window composite (PHV + Gi*).

    PHV isolates sharp local anomalies (fire/urban/industrial spikes) above the
    broad haze; Gi* adds FDR-corrected statistical significance. PHV HVA cells are
    grouped into clusters by connected components, then each is attributed.
    """
    from isro_aqi.hcho import getis_ord, phv, source_attribution
    from isro_aqi.viz.maps import fire_density_map, hcho_map

    res = {}
    spacing = float(stack.lon[1] - stack.lon[0])
    burn_idx = int(np.argmax([float(stack["frp_mean"].isel(time=i).mean())
                              for i in range(stack.sizes["time"])]))
    lo, hi = max(0, burn_idx - 5), min(stack.sizes["time"], burn_idx + 6)
    hcho_burn = stack["hcho"].isel(time=slice(lo, hi)).mean("time")
    frp_burn = stack["frp_mean"].isel(time=slice(lo, hi)).max("time")
    hcho_season = stack["hcho"].mean("time")

    ds_phv = phv.detect_hotspots(hcho_burn, phv_min=1.05, hva_threshold=8e15, to_molec_cm2=1.0)
    res["phv_pct"] = phv.phv_percent(ds_phv)
    res["phv_hva_cells"] = int(ds_phv["hva"].values.sum())

    band = max(3 * spacing, 0.8)
    try:
        ds_gi = getis_ord.gi_star(hcho_burn, distance_band_deg=band, fdr=True, alpha=0.05, permutations=99)
        res["gi_hotspot_cells"] = int(ds_gi["hotspot"].values.sum())
    except Exception as e:  # esda edge cases on tiny grids
        log.warning(f"Gi* skipped: {e}")
        res["gi_hotspot_cells"] = None

    # connected-component clustering of the PHV HVA cells, then attribute
    clusters = source_attribution.connected_clusters(ds_phv["hva"], hcho_burn)
    res["clusters"] = int(len(clusters))
    if len(clusters):
        clusters["frp_mean"] = [float(frp_burn.sel(lon=r.lon, lat=r.lat, method="nearest"))
                                for r in clusters.itertuples()]
        clusters["evi"] = [float(stack["evi"].mean("time").sel(lon=r.lon, lat=r.lat, method="nearest"))
                           for r in clusters.itertuples()]
        attributed = source_attribution.attribute(clusters, regions, season="post_monsoon")
        attributed.to_csv("outputs/hcho_hotspots_attributed.csv", index=False)
        res["attribution"] = attributed["source"].value_counts().to_dict()

    hcho_map(hcho_season, hotspots=clusters if len(clusters) else None,
             title="Seasonal HCHO + attributed hotspots (burning window)",
             out_path=f"{MAP}/hcho_hotspots.png")
    fire_density_map(fires, title="Fire density (synthetic, post-monsoon)", out_path=f"{MAP}/fire_density.png")
    return res


def _transport(stack, fires):
    from isro_aqi.hcho import transport

    date = pd.to_datetime(stack["time"].values[-1])
    winds = stack[["u_wind", "v_wind"]]
    path = transport.back_trajectory(winds, 77.10, 28.65, str(date), hours=48, dt_hours=3.0)
    path.to_csv("outputs/delhi_backtrajectory.csv", index=False)
    n = transport.fires_along_path(path, fires, radius_km=150)
    try:
        u = stack["u_wind"].sel(lon=77.1, lat=28.65, method="nearest").to_series()
        v = stack["v_wind"].sel(lon=77.1, lat=28.65, method="nearest").to_series()
        transport.wind_rose(u, v, out_path=f"{FIG}/delhi_windrose.png")
    except Exception as e:
        log.warning(f"wind rose skipped: {e}")
    return {"trajectory_points": int(len(path)), "fires_along_path": int(n),
            "endpoint": [float(path.iloc[-1]["lon"]), float(path.iloc[-1]["lat"])]}


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    return o


def _write_summary_md(s):
    lines = ["# Demo run summary\n",
             "_Synthetic India data; exercises the full redesigned pipeline (6 changes)._\n"]
    lines.append(f"- Training rows: **{s['training_rows']:,}** | features: **{s['n_features']}**\n")

    gf = s["aod_gapfill"]
    lines.append(f"\n## AOD gap-fill (Change 1)\n"
                 f"- {gf['missing_frac']*100:.0f}% missing filled; clustered-holdout CV "
                 f"r2={gf.get('cv_r2')}, rmse={gf.get('cv_rmse')}\n")

    no2 = s["no2_calibration"]
    lines.append(f"\n## TROPOMI NO2 calibration (Change 2)\n"
                 f"- surface-NO2 r2 **{no2['r2']:.3f}** (raw column r2 {no2.get('raw_column_r2')}); "
                 f"gain over raw column +{no2.get('r2_gain_over_raw_column')}\n")

    lines.append("\n## Surface-pollutant skill — trend vs hybrid (Changes 3, 6)\n")
    lines.append("| Pollutant | trend R² | hybrid R² | India target |\n|---|---|---|---|")
    for t in TARGETS:
        m = s["hybrid"].get(t)
        if m:
            lines.append(f"| {t} | {m['trend']['r2']:.3f} | {m['hybrid']['r2']:.3f} | {m['benchmark_r2']} |")

    cv = s["cv_pm25"]
    lines.append(f"\n## PM2.5 CV (random vs spatial vs temporal)\n"
                 f"- random **{cv['random']:.3f}**, spatial **{cv['spatial']:.3f}**, temporal **{cv['temporal']:.3f}** "
                 f"(spatial < random confirms autocorrelation leakage — Wang 2023).\n")

    lines.append("\n## CNN-LSTM (ISRO-specified learner, val)\n")
    lines.append(", ".join(f"{k} R²={v['r2']:.2f}" for k, v in s["cnn_lstm"].items()) + "\n")

    a = s["aqi"]
    lines.append(f"\n## Dual AQI atlas — {a['date']} (dual index)\n"
                 f"- **Main (CPCB):** mean {a['cpcb_mean']:.0f}, max {a['cpcb_max']:.0f}\n"
                 f"- **USP (RAPI):** mean {a['rapi_mean']:.0f}; mean RAPI−CPCB divergence {a['divergence_mean']:.1f}\n"
                 f"- category cells: {a['category_cells']}\n")

    h = s["hcho"]
    lines.append(f"\n## HCHO hotspots (Change 5)\n"
                 f"- PHV {h['phv_pct']:.1f}% of cells ({h['phv_hva_cells']} HVA); "
                 f"Gi* {h.get('gi_hotspot_cells')} cells; {h['clusters']} clusters; "
                 f"attribution {h.get('attribution')}\n")

    al = s.get("analysis_layers", {})
    lines.append("\n## Comparative analysis layers\n"
                 f"- K-Means selected k **{al.get('selected_k')}**, silhouette scores {al.get('zone_silhouette')}\n"
                 f"- Isolation Forest flagged **{al.get('isolation_anomalies')}** cells in **{al.get('isolation_clusters')}** contiguous regions\n"
                 f"- PHV/Isolation Forest agreement is a diagnostic comparison, not supervised accuracy: {al.get('phv_comparison')}\n")

    t = s["transport"]
    lines.append(f"\n## Transport\n- Delhi 48h back-trajectory: {t['trajectory_points']} points, "
                 f"{t['fires_along_path']} fires within 150 km of path\n")

    lines.append("\n## Artifacts\n"
                 "- `outputs/maps/` CPCB + RAPI + divergence + PM2.5 + HCHO + fire maps\n"
                 "- `outputs/figures/` wind rose\n"
                 "- `outputs/*.csv` hotspots, trajectory\n")
    with open("outputs/demo_summary.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
