"""Getis-Ord Gi* hotspot analysis (Method 2).

Gi* identifies statistically-significant spatial clusters of HIGH values
(hotspots, Gi* z > 0) and LOW values (coldspots, z < 0), unlike PHV/percentile
which are purely value-based. A high HCHO cell is only a Gi* hotspot if its
neighbours are ALSO high -> robust to single-pixel TROPOMI retrieval noise.

    Gi*(i) = [ sum_j w_ij x_j - X_bar * sum_j w_ij ] / [ S * sqrt(...) ]

We use PySAL/esda (G_Local with star=True) for the heavy lifting and apply a
Benjamini-Hochberg FDR correction to the p-values (recommended for many
simultaneous local tests).
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from isro_aqi.utils.logging import get_logger

log = get_logger("getis_ord")


def gi_star(
    hcho: xr.DataArray,
    distance_band_deg: float = 0.05,
    fdr: bool = True,
    alpha: float = 0.05,
    permutations: int = 999,
) -> xr.Dataset:
    """Compute Gi* z-scores and significance over a gridded HCHO field.

    Returns a Dataset with `gi_z` (z-score), `gi_p` (p-value) and `hotspot`
    (boolean, significant high cluster after optional FDR correction).
    """
    from esda.getisord import G_Local
    from libpysal.weights import DistanceBand

    lon2d, lat2d = np.meshgrid(hcho["lon"].values, hcho["lat"].values)
    vals = hcho.values.astype("float64")
    valid = np.isfinite(vals)

    coords = np.column_stack([lon2d[valid], lat2d[valid]])
    y = vals[valid]

    w = DistanceBand(coords, threshold=distance_band_deg, binary=True, silence_warnings=True)
    gi = G_Local(y, w, transform="B", star=True, permutations=permutations)

    z_flat = np.full(vals.shape, np.nan)
    p_flat = np.full(vals.shape, np.nan)
    z_flat[valid] = gi.Zs
    p_flat[valid] = gi.p_sim

    pvals = gi.p_sim.copy()
    if fdr:
        pvals = _benjamini_hochberg(pvals)
    hot = np.zeros(vals.shape, dtype=bool)
    hot_flat = (pvals < alpha) & (gi.Zs > 0)
    hot[valid] = hot_flat

    log.info(f"Gi*: {hot_flat.sum()} significant hotspot cells (alpha={alpha}, fdr={fdr})")
    return xr.Dataset(
        {
            "gi_z": (hcho.dims, z_flat.astype("float32")),
            "gi_p": (hcho.dims, p_flat.astype("float32")),
            "hotspot": (hcho.dims, hot),
        },
        coords=hcho.coords,
    )


def _benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """BH-adjusted p-values for multiple-comparison control."""
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(ranked, 0, 1)
    return out
