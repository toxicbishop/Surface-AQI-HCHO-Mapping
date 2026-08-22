"""AOD gap-fill tests -- RF recovers a learnable AOD field and reports CV skill."""

import numpy as np
import pandas as pd
import xarray as xr

from isro_aqi.preprocessing.gapfill_aod import (
    RandomForestGapFiller,
    fill_aod_stack,
    inject_aod_gaps,
)


def _toy_stack(seed=0):
    rng = np.random.default_rng(seed)
    lats = np.linspace(8, 36, 12)
    lons = np.linspace(70, 96, 12)
    times = pd.date_range("2021-10-15", periods=6, freq="D")
    lon2d, lat2d = np.meshgrid(lons, lats)
    blh = np.broadcast_to((1500 - 20 * lat2d)[None], (len(times), 12, 12))
    elev = np.broadcast_to((lon2d - 70)[None], (len(times), 12, 12))
    # AOD is a learnable function of the covariates + small noise
    aod = (0.3 + 0.0008 * (1500 - 20 * lat2d) + 0.02 * (lon2d - 70))[None] \
        + 0.01 * rng.standard_normal((len(times), 12, 12))
    ds = xr.Dataset(
        {"aod": (("time", "lat", "lon"), aod.astype("float32")),
         "blh": (("time", "lat", "lon"), blh.astype("float32")),
         "elevation": (("time", "lat", "lon"), elev.astype("float32"))},
        coords={"time": times, "lat": lats, "lon": lons},
    )
    return ds


def test_inject_then_fill_removes_all_gaps():
    ds = _toy_stack()
    gappy = inject_aod_gaps(ds, frac=0.3, seed=1)
    assert np.isnan(gappy["aod"].values).any()          # gaps were punched
    filled, report = fill_aod_stack(gappy, covariates=["blh", "elevation", "lat", "lon"])
    assert not np.isnan(filled["aod"].values).any()      # all gaps filled
    assert 0.0 < report["missing_frac"] < 1.0


def test_filled_values_track_truth():
    ds = _toy_stack(seed=3)
    truth = ds["aod"].values.copy()
    gappy = inject_aod_gaps(ds, frac=0.3, seed=2)
    miss = np.isnan(gappy["aod"].values)
    filled, _ = fill_aod_stack(gappy, covariates=["blh", "elevation", "lat", "lon"])
    # filled cells should correlate strongly with the held-out truth
    pred = filled["aod"].values[miss]
    true = truth[miss]
    r = np.corrcoef(pred, true)[0, 1]
    assert r > 0.7


def test_cv_score_reports_metrics():
    ds = _toy_stack()
    df = ds.to_dataframe().reset_index()
    filler = RandomForestGapFiller(["blh", "elevation", "lat", "lon"]).fit(df)
    score = filler.cv_score(df, block_deg=8.0, k=3)
    assert set(score) >= {"cv_r2", "cv_rmse", "cv_n"}
    assert score["cv_n"] > 0
