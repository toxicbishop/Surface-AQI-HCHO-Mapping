"""CPCB National AQI engine.

Sub-index by piecewise-linear interpolation between breakpoints:

    I_p = (I_hi - I_lo)/(BP_hi - BP_lo) * (C_p - BP_lo) + I_lo

Overall AQI = max(sub-indices), valid only when >= `min_pollutants` are present
and at least one of `mandatory` (PM2.5 / PM10) is available.

Breakpoints, averaging windows and validity rules come from
config/aqi_breakpoints.yaml (CPCB 2014). The engine is deterministic and fully
unit-tested (tests/test_aqi.py).

Reference for the aggregation form: Wang et al. 2023 (Eq. 4-5); the max-of-sub-
index rule matches both CPCB and the Chinese AQI. Lu et al. 2011 propose a
Shannon-entropy alternative (RAPI) -- see aggregate_entropy() for the optional,
publishable comparison.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd


def sub_index(conc: float, breakpoints: list[list[float]]) -> float | None:
    """Linear-interpolated sub-index for one pollutant concentration.

    breakpoints: list of [C_lo, C_hi, I_lo, I_hi]. Returns None if conc is NaN;
    concentrations above the top breakpoint are capped at the top band.

    The CPCB bands have integer gaps ([0,30],[31,60],...). A value landing in a
    gap (e.g. PM2.5=30.5) is assigned to the band whose lower bound it meets or
    exceeds, by extending each band UP TO the next band's lower bound:
    ``c_lo <= conc < next_c_lo``. The interpolation still uses the band's own
    [C_lo, C_hi] so the result is sensible and the scalar/vector paths agree.
    """
    if conc is None or (isinstance(conc, float) and math.isnan(conc)) or conc < 0:
        return None
    n = len(breakpoints)
    for k, (c_lo, c_hi, i_lo, i_hi) in enumerate(breakpoints):
        # extend the band's upper edge up to the next band's lower bound so gap
        # values (c_hi < conc < next_c_lo) fall into THIS band, not the cap.
        upper = breakpoints[k + 1][0] if k + 1 < n else c_hi
        if c_lo <= conc < upper or (k == n - 1 and conc <= c_hi):
            return (i_hi - i_lo) / (c_hi - c_lo) * (conc - c_lo) + i_lo
    # above the highest breakpoint -> cap at the top sub-index
    top = breakpoints[-1]
    return float(top[3])


class AQIEngine:
    """Computes CPCB sub-indices and overall AQI from a breakpoints config."""

    def __init__(self, breakpoints_cfg: dict):
        self.bp: dict[str, list[list[float]]] = breakpoints_cfg["breakpoints"]
        self.categories = breakpoints_cfg["categories"]
        self.mandatory = breakpoints_cfg.get("mandatory", ["pm25", "pm10"])
        self.min_pollutants = int(breakpoints_cfg.get("min_pollutants", 3))

    # --- sub-indices -------------------------------------------------------
    def sub_indices(self, concentrations: dict[str, float]) -> dict[str, float]:
        """Map {pollutant: concentration} -> {pollutant: sub-index} (drops None)."""
        out = {}
        for p, c in concentrations.items():
            if p in self.bp:
                si = sub_index(c, self.bp[p])
                if si is not None:
                    out[p] = si
        return out

    # --- overall AQI -------------------------------------------------------
    def aqi(self, concentrations: dict[str, float]) -> tuple[float | None, str | None, str | None]:
        """Return (AQI, dominant_pollutant, category_label) or (None, ...) if invalid.

        Validity: >= min_pollutants present AND at least one mandatory pollutant.
        """
        si = self.sub_indices(concentrations)
        if len(si) < self.min_pollutants or not any(m in si for m in self.mandatory):
            return None, None, None
        dominant = max(si, key=si.get)
        value = si[dominant]
        return value, dominant, self.category(value)

    def category(self, aqi_value: float) -> str:
        for band in self.categories:
            if band["lo"] <= aqi_value <= band["hi"]:
                return band["label"]
        return self.categories[-1]["label"]

    def color(self, aqi_value: float) -> str:
        for band in self.categories:
            if band["lo"] <= aqi_value <= band["hi"]:
                return band["color"]
        return self.categories[-1]["color"]

    # --- vectorised over a DataFrame --------------------------------------
    def compute_frame(self, df: pd.DataFrame, cols: dict[str, str] | None = None) -> pd.DataFrame:
        """Add aqi / aqi_dominant / aqi_category columns to a per-cell DataFrame.

        cols maps engine pollutant names -> DataFrame column names (defaults to
        identity for pm25, pm10, no2, so2, co, o3).
        """
        cols = cols or {p: p for p in ("pm25", "pm10", "no2", "so2", "co", "o3")}

        def _row(r):
            conc = {p: r[c] for p, c in cols.items() if c in r and pd.notna(r[c])}
            v, dom, cat = self.aqi(conc)
            return pd.Series({"aqi": v, "aqi_dominant": dom, "aqi_category": cat})

        return df.join(df.apply(_row, axis=1))

    # --- vectorised grid computation (for India-scale daily maps) ----------
    @staticmethod
    def _sub_index_vec(conc: np.ndarray, breakpoints: list[list[float]]) -> np.ndarray:
        """Vectorised sub-index over an array of concentrations."""
        conc = np.asarray(conc, dtype="float64")
        out = np.full(conc.shape, np.nan)
        n = len(breakpoints)
        for k, (c_lo, c_hi, i_lo, i_hi) in enumerate(breakpoints):
            # match the scalar path: extend each band up to the next band's lower
            # bound so gap values (c_hi < conc < next_c_lo) map into THIS band.
            upper = breakpoints[k + 1][0] if k + 1 < n else c_hi
            if k == n - 1:
                m = (conc >= c_lo) & (conc <= c_hi)
            else:
                m = (conc >= c_lo) & (conc < upper)
            out[m] = (i_hi - i_lo) / (c_hi - c_lo) * (conc[m] - c_lo) + i_lo
        top = breakpoints[-1]
        out[conc > top[1]] = float(top[3])   # cap above highest breakpoint
        out[conc < 0] = np.nan
        return out

    def aqi_grid(self, concentrations: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
        """Vectorised AQI over gridded concentration arrays.

        Returns (aqi, dominant) arrays of the same shape. Invalid cells (fewer
        than min_pollutants, or no mandatory pollutant) are NaN / None.
        """
        sis = {p: self._sub_index_vec(a, self.bp[p]) for p, a in concentrations.items() if p in self.bp}
        names = list(sis)
        stack = np.stack([sis[n] for n in names], axis=0)            # (P, ...)
        valid_count = np.sum(~np.isnan(stack), axis=0)
        has_mand = np.zeros(stack.shape[1:], dtype=bool)
        for m in self.mandatory:
            if m in sis:
                has_mand |= ~np.isnan(sis[m])
        filled = np.where(np.isnan(stack), -np.inf, stack)
        dom_idx = np.argmax(filled, axis=0)
        with np.errstate(invalid="ignore"):
            aqi = np.nanmax(stack, axis=0)
        valid = (valid_count >= self.min_pollutants) & has_mand
        aqi = np.where(valid, aqi, np.nan)
        dominant = np.array(names, dtype=object)[dom_idx]
        dominant = np.where(valid, dominant, None)
        return aqi, dominant

    # --- entropy aggregation (Lu et al. 2011, Hong Kong RAPI) --------------
    @staticmethod
    def aggregate_entropy(sub_indices: Iterable[float]) -> float:
        """Shannon-entropy-weighted aggregation -- accounts for co-occurring
        pollutants instead of max-only (Lu et al. 2011, Hong Kong RAPI).

            p_k  = I_k / sum(I)
            H    = -sum(p_k ln p_k) / ln(K)          # normalised entropy 0..1
            RAPI = max(I) * (1 + (mean(I)/max(I)) * H)

        RAPI >= max(I): it is the CPCB max scaled up when co-pollutants are also
        elevated. Equals max when only one pollutant carries the signal (H -> 0).
        """
        vals = np.array([s for s in sub_indices if s is not None and s > 0], dtype=float)
        if vals.size == 0:
            return float("nan")
        p = vals / vals.sum()
        entropy = -np.sum(p * np.log(p + 1e-12)) / math.log(len(vals)) if len(vals) > 1 else 0.0
        return float(vals.max() * (1 + (vals.mean() / vals.max()) * entropy))

    def rapi_grid(self, concentrations: dict[str, np.ndarray]) -> np.ndarray:
        """Vectorised RAPI over gridded concentration arrays (Hong Kong [D]).

        Same validity rules as ``aqi_grid``. Returns an array (NaN where invalid).
        This is the per-pixel spatial form of ``aggregate_entropy``.
        """
        sis = {p: self._sub_index_vec(a, self.bp[p]) for p, a in concentrations.items() if p in self.bp}
        names = list(sis)
        stack = np.stack([sis[n] for n in names], axis=0)            # (P, ...)
        valid = ~np.isnan(stack)
        K = valid.sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            smax = np.nanmax(np.where(valid, stack, np.nan), axis=0)
            ssum = np.nansum(np.where(valid, stack, 0.0), axis=0)
            smean = np.nanmean(np.where(valid, stack, np.nan), axis=0)
            shares = np.where(valid & (ssum > 0), stack / ssum, 0.0)
            ent = -np.sum(np.where(shares > 0, shares * np.log(shares), 0.0), axis=0)
            lnK = np.log(np.maximum(K, 1))
            Hn = np.where(K > 1, ent / np.where(lnK == 0, 1.0, lnK), 0.0)
            rapi = np.where(smax > 0, smax * (1 + (smean / np.where(smax == 0, 1.0, smax)) * Hn), 0.0)
        has_mand = np.zeros(stack.shape[1:], dtype=bool)
        for m in self.mandatory:
            if m in sis:
                has_mand |= ~np.isnan(sis[m])
        valid_cells = (K >= self.min_pollutants) & has_mand
        return np.where(valid_cells, rapi, np.nan)

    def compute_grid(self, concentrations: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Both indices + divergence in one call, for the dual-view atlas.

        Returns dict with:
            cpcb        max-aggregation AQI (official; the 'Main' view headline)
            rapi        entropy-weighted RAPI (Hong Kong; the 'USP' view headline)
            dominant    dominant pollutant per cell (object array; None if invalid)
            divergence  rapi - cpcb  (>= 0 where valid; the headline novelty map)
        """
        cpcb, dominant = self.aqi_grid(concentrations)
        rapi = self.rapi_grid(concentrations)
        return {"cpcb": cpcb, "rapi": rapi, "dominant": dominant, "divergence": rapi - cpcb}
