"""CPCB AQI engine tests -- the engine is deterministic, so it is fully testable."""

from pathlib import Path

import pytest
import yaml

from isro_aqi.aqi.engine import AQIEngine, sub_index

BP = yaml.safe_load(Path("config/aqi_breakpoints.yaml").read_text())
ENGINE = AQIEngine(BP)


def test_sub_index_linear_interpolation():
    # PM2.5 = 45 in band [31,60,51,100] -> (100-51)/(60-31)*(45-31)+51 = 74.655
    assert sub_index(45, BP["breakpoints"]["pm25"]) == pytest.approx(74.655, abs=1e-2)


def test_sub_index_band_edges():
    # exact lower/upper breakpoints map to the band's index bounds
    assert sub_index(30, BP["breakpoints"]["pm25"]) == pytest.approx(50.0, abs=1e-6)
    assert sub_index(60, BP["breakpoints"]["pm25"]) == pytest.approx(100.0, abs=1e-6)


def test_sub_index_above_top_is_capped():
    assert sub_index(10_000, BP["breakpoints"]["pm25"]) == 500.0


def test_sub_index_nan_and_negative():
    assert sub_index(float("nan"), BP["breakpoints"]["pm25"]) is None
    assert sub_index(-5, BP["breakpoints"]["pm25"]) is None


def test_overall_aqi_is_max_with_dominant():
    conc = {"pm25": 45, "pm10": 120, "no2": 50}  # 74.66, 113.62, 62.31
    value, dominant, category = ENGINE.aqi(conc)
    assert dominant == "pm10"
    assert value == pytest.approx(113.62, abs=0.1)
    assert category == "Moderate"


def test_validity_requires_min_pollutants():
    # only two pollutants -> invalid
    assert ENGINE.aqi({"pm25": 45, "no2": 50}) == (None, None, None)


def test_validity_requires_mandatory_pollutant():
    # three pollutants but none is PM2.5/PM10 -> invalid
    assert ENGINE.aqi({"no2": 50, "so2": 30, "o3": 40}) == (None, None, None)


def test_category_and_color_mapping():
    assert ENGINE.category(450) == "Severe"
    assert ENGINE.color(25) == "#009865"   # official CPCB "Good" green


def test_entropy_aggregation_runs():
    val = AQIEngine.aggregate_entropy([74.66, 113.62, 62.31])
    assert val >= 113.62  # entropy variant >= max


def test_vectorised_grid_matches_scalar():
    import numpy as np

    pm25 = np.array([[45.0, 91.0], [10.0, 250.0]])
    pm10 = np.array([[120.0, 60.0], [40.0, 300.0]])
    no2 = np.array([[50.0, 50.0], [50.0, 50.0]])
    aqi, dom = ENGINE.aqi_grid({"pm25": pm25, "pm10": pm10, "no2": no2})
    # compare every cell against the scalar engine
    for i in range(2):
        for j in range(2):
            v, d, _ = ENGINE.aqi({"pm25": pm25[i, j], "pm10": pm10[i, j], "no2": no2[i, j]})
            assert aqi[i, j] == pytest.approx(v, abs=1e-6)
            assert dom[i, j] == d


def test_sub_index_gap_value_scalar_and_grid_agree():
    import numpy as np

    # PM2.5 = 30.5 lands in the integer GAP between band [0,30,0,50] and
    # [31,60,51,100]. It must NOT return the top-band cap (500) nor NaN; it
    # should fall into the [0,30] band (extended up to the next lower bound 31),
    # giving a sub-index just above 50. Scalar and vector paths must agree.
    si = sub_index(30.5, BP["breakpoints"]["pm25"])
    assert si is not None
    assert 50.0 <= si < 51.0  # interpolated within the [0,30,0,50] band, conc>30
    vec = ENGINE._sub_index_vec(np.array([30.5]), BP["breakpoints"]["pm25"])
    assert vec[0] == pytest.approx(si, abs=1e-9)


def test_grid_invalidates_cells_without_mandatory():
    import numpy as np

    # only NO2/SO2/O3 -> no PM mandatory -> invalid (NaN)
    z = np.array([[50.0]])
    aqi, dom = ENGINE.aqi_grid({"no2": z, "so2": z, "o3": z})
    assert np.isnan(aqi[0, 0])
    assert dom[0, 0] is None
