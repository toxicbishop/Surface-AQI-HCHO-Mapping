"""Hybrid trend + kriging-residual tests."""

import numpy as np
import pandas as pd

from isro_aqi.models.hybrid import HybridModel, ResidualKriging, evaluate_trend_vs_hybrid


def test_residual_kriging_decays_far_from_stations():
    krig = ResidualKriging(length_scale_deg=0.5, reg=1e-2).fit(
        lon=[80.0], lat=[25.0], residuals=[5.0])
    near = krig.predict(np.array([80.0]), np.array([25.0]))[0]
    far = krig.predict(np.array([10.0]), np.array([10.0]))[0]
    assert near > 4.0            # at the station, ~the residual
    assert abs(far) < 0.1        # far away -> ~0 (falls back to pure trend)


def _spatial_dataset(seed=0):
    """y = trend(x) + per-station spatial bias + noise, across several days."""
    rng = np.random.default_rng(seed)
    n_st, n_days = 40, 12
    st_lon = rng.uniform(70, 96, n_st)
    st_lat = rng.uniform(8, 36, n_st)
    st_bias = rng.normal(0, 8, n_st)          # unobserved per-station bias
    rows = []
    for j in range(n_st):
        for d in range(n_days):
            x = rng.uniform(0, 10)
            y = 3.0 * x + st_bias[j] + rng.normal(0, 1.0)
            rows.append({"station_id": f"S{j}", "lon": st_lon[j], "lat": st_lat[j],
                         "x": x, "day": d, "pm25": y})
    return pd.DataFrame(rows)


def test_hybrid_beats_trend_on_seen_stations():
    df = _spatial_dataset()
    train = df[df["day"] < 9]
    test = df[df["day"] >= 9]            # same stations, held-out days
    res = evaluate_trend_vs_hybrid(train, test, ["pm25"], ["x"])
    trend_r2 = res["pm25"]["trend"]["r2"]
    hybrid_r2 = res["pm25"]["hybrid"]["r2"]
    # the kriged residual recovers the per-station bias the trend can't see
    assert hybrid_r2 > trend_r2


def test_hybrid_predict_returns_finite():
    df = _spatial_dataset(seed=1)
    hyb = HybridModel(["pm25"], ["x"]).fit(df)
    grid = pd.DataFrame({"x": np.linspace(0, 10, 50),
                         "lon": np.linspace(70, 96, 50),
                         "lat": np.linspace(8, 36, 50)})
    out = hyb.predict(grid)
    assert np.isfinite(out["pm25"].to_numpy()).all()
