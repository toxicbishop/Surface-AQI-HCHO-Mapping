"""Stack-assembler core tests (pure xarray path -- no rasterio needed)."""

import numpy as np
import xarray as xr

from isro_aqi.preprocessing.assemble import assemble_from_layers, period_label
from isro_aqi.utils.geo import Grid


def test_period_label_parses_start_date():
    assert period_label("s5p_no2_2021-10-01_2021-12-31.tif") == "2021-10-01"
    assert period_label("era5_2021-10-01_2021-12-31.tif") == "2021-10-01"
    assert period_label("worldcover_fractions.tif") is None
    assert period_label("srtm_terrain.tif") is None


def _fake_da(seed, n=10):
    rng = np.random.default_rng(seed)
    lats = np.linspace(8, 36, n)        # ascending, covers India bbox
    lons = np.linspace(70, 96, n)
    return xr.DataArray(rng.random((n, n)).astype("float32"),
                        coords={"lat": lats, "lon": lons}, dims=("lat", "lon"))


def test_assemble_two_dates_with_static_broadcast():
    grid = Grid(bbox=(70.0, 8.0, 96.0, 36.0), resolution_deg=2.0)
    dated = {
        "2021-10-01": {"no2": _fake_da(1), "hcho": _fake_da(2)},
        "2021-10-02": {"no2": _fake_da(3), "hcho": _fake_da(4)},
    }
    static = {"lc_crop": _fake_da(5), "elevation": _fake_da(6)}
    stack = assemble_from_layers(dated, static, grid)

    assert stack.sizes["time"] == 2
    assert stack.sizes["lat"] == grid.shape[0] and stack.sizes["lon"] == grid.shape[1]
    for v in ("no2", "hcho", "lc_crop", "elevation"):
        assert v in stack.data_vars
    # static layer is identical across the two time slices (broadcast, not per-date)
    e0 = stack["elevation"].isel(time=0).values
    e1 = stack["elevation"].isel(time=1).values
    assert np.allclose(e0, e1, equal_nan=True)
    # dynamic layer differs across dates
    assert not np.allclose(stack["no2"].isel(time=0).values,
                           stack["no2"].isel(time=1).values, equal_nan=True)


def test_assemble_single_period_gets_time_dim():
    grid = Grid(bbox=(70.0, 8.0, 96.0, 36.0), resolution_deg=3.0)
    dated = {"2021-10-01": {"no2": _fake_da(7), "aod": _fake_da(8)}}
    stack = assemble_from_layers(dated, {}, grid)
    assert stack.sizes["time"] == 1
    assert "aod" in stack.data_vars
