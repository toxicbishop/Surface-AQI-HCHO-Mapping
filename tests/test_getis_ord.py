"""Getis-Ord Gi* tests (requires esda/libpysal; skipped if unavailable)."""

import numpy as np
import pytest
import xarray as xr

pytest.importorskip("esda")
pytest.importorskip("libpysal")

from isro_aqi.hcho.getis_ord import _benjamini_hochberg, gi_star  # noqa: E402


def test_benjamini_hochberg_monotone_and_bounded():
    p = np.array([0.001, 0.01, 0.02, 0.5, 0.9])
    adj = _benjamini_hochberg(p)
    assert adj.min() >= 0 and adj.max() <= 1
    assert np.all(adj >= p)  # BH adjustment never decreases a p-value


def test_gi_star_finds_high_cluster():
    a = np.zeros((20, 20))
    a[8:12, 8:12] = 50.0  # a strong high cluster
    lat = (np.arange(20)[::-1] * 0.05).astype(float)
    lon = (np.arange(20) * 0.05).astype(float)
    da = xr.DataArray(a, coords={"lat": lat, "lon": lon}, dims=("lat", "lon"))
    ds = gi_star(da, distance_band_deg=0.08, fdr=True, alpha=0.05)
    # the central block should contain significant hotspot cells
    assert ds["hotspot"].values[8:12, 8:12].sum() > 0
