"""PHV index -- "Percentage Higher than Vicinity" (Dong et al. 2026, Atmosphere 17:321).

    PHV(i,j) = C(i,j) / ( (1/8) * sum of the 8 Moore-neighbour cells )

Interpretation:
    PHV > 1  -> the centre cell exceeds its surroundings -> local HCHO anomaly.
    PHV >> 1 -> sharp, localised enhancement (likely a point/area source).

A cell is a hotspot candidate (High-Value Area, HVA) when BOTH:
    PHV > phv_min (default 1.0)  AND  C >= hva_threshold (default 1e16 molec/cm^2,
    i.e. the paper's 1000 x 10^13 lower bound).

The paper finds a ~1 km (0.01 deg) grid optimal: 0.5 km over-fits TROPOMI noise,
2 km smooths real anomalies away. Optional `mutation` flag keeps only cells whose
PHV anomaly persists/changes vs a reference field, mirroring the paper's
mutation-detection step that cut false positives ~93%.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from isro_aqi.utils.geo import moore_neighbourhood


def phv_field(hcho: np.ndarray) -> np.ndarray:
    """PHV value for every cell of a 2-D HCHO field (NaN where neighbours absent)."""
    neighbours = moore_neighbourhood(hcho)          # (8, H, W)
    neighbour_mean = np.nanmean(neighbours, axis=0)  # (H, W)
    with np.errstate(divide="ignore", invalid="ignore"):
        phv = hcho / neighbour_mean
    return phv


def detect_hotspots(
    hcho: xr.DataArray,
    phv_min: float = 1.0,
    hva_threshold: float = 1.0e16,
    reference: xr.DataArray | None = None,
    mutation_factor: float = 1.2,
    to_molec_cm2: float = 6.022e19,
) -> xr.Dataset:
    """Return a Dataset with phv, hva mask and (optional) mutation-confirmed mask.

    Parameters
    ----------
    hcho : DataArray (lat, lon) of tropospheric HCHO column. If units are mol/m^2
        (TROPOMI native), `to_molec_cm2` converts to molec/cm^2 for the threshold
        (1 mol/m^2 = 6.022e19 molec/cm^2). Pass to_molec_cm2=1 if already converted.
    reference : optional baseline field for mutation detection (e.g. prior-year /
        seasonal mean). A candidate is confirmed only if it also rises
        `mutation_factor`x above the reference -- this is the change-detection step.
    """
    values = hcho.values.astype("float64") * to_molec_cm2
    phv = phv_field(values)

    hva = (phv > phv_min) & (values >= hva_threshold)

    ds = xr.Dataset(
        {
            "phv": (hcho.dims, phv.astype("float32")),
            "hcho_molec_cm2": (hcho.dims, values.astype("float32")),
            "hva": (hcho.dims, hva),
        },
        coords=hcho.coords,
    )

    if reference is not None:
        ref = reference.values.astype("float64") * to_molec_cm2
        with np.errstate(divide="ignore", invalid="ignore"):
            mutation = (values / ref) > mutation_factor
        ds["hva_confirmed"] = (hcho.dims, hva & mutation)
    return ds


def phv_percent(ds: xr.Dataset) -> float:
    """Fraction (%) of valid cells flagged as HVA -- the paper's per-scene PHV%."""
    hva = ds["hva"].values
    valid = ~np.isnan(ds["phv"].values)
    return float(100.0 * hva.sum() / max(valid.sum(), 1))
