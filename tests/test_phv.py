"""PHV index tests (Dong et al. 2026) -- deterministic, fully testable."""

import numpy as np
import xarray as xr

from isro_aqi.hcho.phv import detect_hotspots, phv_field, phv_percent


def _da(arr):
    n, m = arr.shape
    return xr.DataArray(
        arr.astype("float64"),
        coords={"lat": np.arange(n)[::-1].astype(float), "lon": np.arange(m).astype(float)},
        dims=("lat", "lon"),
    )


def test_phv_centre_spike():
    a = np.ones((7, 7))
    a[3, 3] = 10.0
    phv = phv_field(a)
    # centre = 10, mean of 8 unit neighbours = 1 -> PHV = 10
    assert phv[3, 3] == 10.0
    # a cell far from the spike (uniform neighbourhood) gives PHV = 1
    assert phv[1, 1] == 1.0
    # a cell DIAGONALLY adjacent to the spike sees an inflated neighbour mean,
    # so PHV < 1 -- this is the intended local-anomaly sensitivity.
    assert phv[2, 2] < 1.0


def test_phv_corner_uses_available_neighbours():
    a = np.ones((4, 4))
    phv = phv_field(a)
    # corner has only 3 valid neighbours (rest NaN) but all equal 1 -> PHV = 1
    assert np.isclose(phv[0, 0], 1.0)


def test_detect_hotspots_flags_spike():
    a = np.ones((5, 5))
    a[2, 2] = 10.0
    ds = detect_hotspots(_da(a), phv_min=1.0, hva_threshold=5.0, to_molec_cm2=1.0)
    assert bool(ds["hva"].values[2, 2]) is True
    # uniform cells are not hotspots (PHV == 1, not > 1)
    assert ds["hva"].values.sum() == 1


def test_mutation_detection_requires_change_vs_reference():
    a = np.ones((5, 5))
    a[2, 2] = 10.0
    ref = a.copy()  # identical reference -> no mutation
    ds = detect_hotspots(
        _da(a), phv_min=1.0, hva_threshold=5.0, reference=_da(ref),
        mutation_factor=1.2, to_molec_cm2=1.0,
    )
    assert ds["hva_confirmed"].values.sum() == 0  # unchanged -> filtered out


def test_phv_percent():
    a = np.ones((5, 5))
    a[2, 2] = 10.0
    ds = detect_hotspots(_da(a), phv_min=1.0, hva_threshold=5.0, to_molec_cm2=1.0)
    assert phv_percent(ds) > 0
