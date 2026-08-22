"""TROPOMI NO2 -> surface calibration tests."""

import numpy as np
import pandas as pd
import xarray as xr

from isro_aqi.preprocessing.calibrate_no2 import NO2Calibrator, calibrate_no2_stack


def _toy_training(n=600, seed=0):
    rng = np.random.default_rng(seed)
    col = rng.uniform(1, 10, n)          # TROPOMI NO2 column (arb units)
    blh = rng.uniform(200, 2000, n)
    # surface NO2 depends on column AND inversely on BLH (mixing) + noise
    surf = 4.0 * col + 6000.0 / blh + rng.normal(0, 1.5, n)
    return pd.DataFrame({
        "no2": col, "blh": blh, "temperature": rng.uniform(280, 310, n),
        "wind_speed": rng.uniform(0.5, 6, n), "rh": rng.uniform(20, 90, n),
        "no2_obs": surf,
    })


def test_calibrator_learns_column_to_surface():
    df = _toy_training()
    cal = NO2Calibrator().fit(df)
    rep = cal.report(df)
    assert rep["r2"] > 0.8
    assert rep["n"] == len(df)


def test_calibration_beats_raw_column():
    df = _toy_training(seed=2)
    cal = NO2Calibrator().fit(df)
    rep = cal.report(df)
    # using BLH on top of the column should beat the raw column-only fit
    assert "r2_gain_over_raw_column" in rep
    assert rep["r2"] >= rep["raw_column_r2"]


def test_calibrate_stack_adds_surface_var():
    rng = np.random.default_rng(1)
    lats = np.linspace(8, 36, 8)
    lons = np.linspace(70, 96, 8)
    times = pd.date_range("2021-10-15", periods=4, freq="D")
    shp = (len(times), 8, 8)
    ds = xr.Dataset(
        {"no2": (("time", "lat", "lon"), rng.uniform(1, 10, shp).astype("float32")),
         "blh": (("time", "lat", "lon"), rng.uniform(200, 2000, shp).astype("float32")),
         "temperature": (("time", "lat", "lon"), rng.uniform(280, 310, shp).astype("float32")),
         "wind_speed": (("time", "lat", "lon"), rng.uniform(0.5, 6, shp).astype("float32")),
         "rh": (("time", "lat", "lon"), rng.uniform(20, 90, shp).astype("float32"))},
        coords={"time": times, "lat": lats, "lon": lons},
    )
    out, rep = calibrate_no2_stack(ds, _toy_training())
    assert "no2_surface" in out.data_vars
    assert out["no2_surface"].shape == shp
    assert np.isfinite(out["no2_surface"].values).all()
