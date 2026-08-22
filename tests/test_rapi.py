"""RAPI (Hong Kong entropy index) tests -- deterministic, so fully testable.

Verifies the vectorised rapi_grid against the scalar aggregate_entropy, the
RAPI >= CPCB property, the divergence map, and that validity matches aqi_grid.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from isro_aqi.aqi.engine import AQIEngine

BP = yaml.safe_load(Path("config/aqi_breakpoints.yaml").read_text())
ENGINE = AQIEngine(BP)


def _conc():
    # two cells: [0,0] co-elevated (3 pollutants high); [0,1] single-dominant
    pm25 = np.array([[90.0, 250.0]])
    pm10 = np.array([[180.0, 60.0]])
    no2 = np.array([[80.0, 10.0]])
    return {"pm25": pm25, "pm10": pm10, "no2": no2}


def test_rapi_ge_cpcb_everywhere():
    conc = _conc()
    cpcb, _ = ENGINE.aqi_grid(conc)
    rapi = ENGINE.rapi_grid(conc)
    valid = ~np.isnan(cpcb)
    assert np.all(rapi[valid] >= cpcb[valid] - 1e-6)


def test_rapi_grid_matches_scalar_entropy():
    conc = _conc()
    rapi = ENGINE.rapi_grid(conc)
    for j in (0, 1):
        si = ENGINE.sub_indices({p: conc[p][0, j] for p in conc})
        expected = AQIEngine.aggregate_entropy(list(si.values()))
        assert rapi[0, j] == pytest.approx(expected, abs=1e-4)


def test_divergence_nonnegative_and_larger_when_copolluted():
    out = ENGINE.compute_grid(_conc())
    div = out["divergence"]
    assert np.all(div[~np.isnan(div)] >= -1e-6)
    # co-elevated cell (0,0) should diverge more than single-dominant cell (0,1)
    assert div[0, 0] > div[0, 1]


def test_rapi_validity_matches_cpcb():
    # only NO2/SO2/O3 -> no mandatory PM -> invalid in both indices
    z = np.array([[50.0]])
    cpcb, _ = ENGINE.aqi_grid({"no2": z, "so2": z, "o3": z})
    rapi = ENGINE.rapi_grid({"no2": z, "so2": z, "o3": z})
    assert np.isnan(cpcb[0, 0]) and np.isnan(rapi[0, 0])


def test_compute_grid_keys():
    out = ENGINE.compute_grid(_conc())
    assert set(out) == {"cpcb", "rapi", "dominant", "divergence"}
    assert out["cpcb"].shape == out["rapi"].shape == out["divergence"].shape
