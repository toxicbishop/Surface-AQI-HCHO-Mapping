"""Synthetic-data generator tests: shapes, ranges, and learnable signal."""

import numpy as np

from isro_aqi.synthetic import SyntheticConfig, generate_all


def test_generate_all_shapes_and_ranges():
    out = generate_all(SyntheticConfig(resolution_deg=1.0, n_days=10, n_stations=25))
    stack, stations, obs, fires = out["stack"], out["stations"], out["observations"], out["fires"]

    assert dict(stack.sizes)["time"] == 10
    assert len(stack.data_vars) >= 25                 # full predictor set
    assert {"hcho", "aod", "no2", "frp_mean", "blh"}.issubset(set(stack.data_vars))
    assert len(stations) == 25
    assert len(obs) == 25 * 10
    assert {"pm25", "pm10", "no2_obs", "so2_obs", "o3_obs", "co_obs"}.issubset(obs.columns)

    # physical plausibility
    assert obs["pm25"].between(0, 1000).all()
    assert 1e15 < float(stack["hcho"].mean()) < 5e16   # India HCHO column magnitude
    assert (obs["pm25"] <= obs["pm10"] + 1e-6).mean() > 0.9  # PM10 >= PM2.5 mostly
    assert len(fires) > 0


def test_signal_is_learnable():
    """AOD should drive PM2.5 (positive correlation) so models can learn."""
    from isro_aqi.preprocessing.collocate import join_targets, sample_at_stations

    out = generate_all(SyntheticConfig(resolution_deg=1.0, n_days=12, n_stations=40))
    stack, stations, obs = out["stack"], out["stations"], out["observations"]
    # properly aligned (station, date) join via the real collocation path
    joined = join_targets(sample_at_stations(stack, stations), obs)
    r = np.corrcoef(joined["aod"].to_numpy(), joined["pm25"].to_numpy())[0, 1]
    assert r > 0.3   # genuine, learnable AOD->PM2.5 signal
