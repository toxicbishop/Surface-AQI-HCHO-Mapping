"""Hybrid trend + kriging-residual model (Change 3).

Implements Wang/Shanghai's regression-kriging structure:

    C(s, t) = mu(s, t) + v(s, t)

  mu : the TREND -- a learner with a sklearn-style fit/predict. RandomForest is
       used here for fast full-grid maps. (The CNN-LSTM in models/ uses a torch
       training loop, NOT this same fit/predict object, so it is trained/applied
       separately -- it does not drop into HybridModel as the trend.)
  v  : the RESIDUAL field -- station residuals (obs - trend) interpolated over
       space. Near a station v corrects the local bias; far from any station the
       weights vanish so v -> 0 and the prediction falls back to the pure trend
       (matches Lee 2012: kriging helps within ~100 km of a monitor). We do NOT
       claim kriging replaces the trend -- it is an additive correction.

The residual interpolator is a Gaussian-kernel simple-kriging (zero far-field
mean): w_i = exp(-d_i^2 / 2L^2); v = sum(w_i r_i) / (sum(w_i) + reg). With the
+reg damping, sparse/far regions decay to 0 rather than extrapolating wildly.
(There is no 'gp' / exact Gaussian-process option here -- only this kernel
weighting, tuned via ``length_scale_deg`` and ``reg``.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from isro_aqi.models.baselines import RandomForestModel, metrics
from isro_aqi.utils.logging import get_logger

log = get_logger("hybrid")

# India-competitive skill targets (deep-research verified; see REDESIGN_PLAN §3).
INDIA_BENCHMARK_R2 = {
    "pm25": 0.86, "pm10": 0.85, "no2": 0.83, "o3": 0.60, "so2": 0.40, "co": 0.58,
}


class ResidualKriging:
    """Gaussian-kernel simple kriging of station residuals (zero far-field mean)."""

    def __init__(self, length_scale_deg: float = 0.6, reg: float = 1e-2):
        self.L = float(length_scale_deg)
        self.reg = float(reg)

    def fit(self, lon, lat, residuals) -> "ResidualKriging":
        self.lon = np.asarray(lon, dtype="float64")
        self.lat = np.asarray(lat, dtype="float64")
        self.res = np.asarray(residuals, dtype="float64")  # (N,) or (N, T)
        return self

    def predict(self, qlon, qlat, chunk: int = 20000) -> np.ndarray:
        qlon = np.asarray(qlon, dtype="float64")
        qlat = np.asarray(qlat, dtype="float64")
        out = []
        for s in range(0, len(qlon), chunk):
            ql, qa = qlon[s:s + chunk], qlat[s:s + chunk]
            d2 = (ql[:, None] - self.lon[None, :]) ** 2 + (qa[:, None] - self.lat[None, :]) ** 2
            w = np.exp(-d2 / (2 * self.L ** 2))                 # (q, N)
            num = w @ self.res                                  # (q,) or (q, T)
            den = w.sum(axis=1) + self.reg
            out.append(num / (den[:, None] if self.res.ndim == 2 else den))
        return np.concatenate(out, axis=0)


class HybridModel:
    """Trend learner + kriged residual: C(s,t) = mu(s,t) + v(s,t)."""

    def __init__(self, targets: list[str], features: list[str], trend=None,
                 length_scale_deg: float = 0.6, lon_col: str = "lon", lat_col: str = "lat",
                 station_col: str = "station_id"):
        self.targets = targets
        self.features = features
        self.trend = trend or RandomForestModel(targets, features)
        self.krig = ResidualKriging(length_scale_deg)
        self.lon_col, self.lat_col, self.station_col = lon_col, lat_col, station_col

    def fit(self, train_df: pd.DataFrame) -> "HybridModel":
        self.trend.fit(train_df)
        pred = self.trend.predict(train_df)
        df = train_df.copy()
        for t in self.targets:
            if t in pred:
                df[f"_res_{t}"] = df[t] - pred[t].to_numpy()
        # per-station mean residual (a stable spatial bias field, per target)
        key = self.station_col if self.station_col in df else None
        grp = df.groupby(key) if key else df.groupby([self.lon_col, self.lat_col])
        coords = grp[[self.lon_col, self.lat_col]].first()
        rescols = [f"_res_{t}" for t in self.targets if f"_res_{t}" in df]
        res = grp[rescols].mean()
        self._modeled_targets = [c[len("_res_"):] for c in rescols]
        self.krig.fit(coords[self.lon_col].to_numpy(), coords[self.lat_col].to_numpy(),
                      res.to_numpy())
        log.info(f"hybrid fit: trend + residual kriging over {len(coords)} stations "
                 f"(L={self.krig.L} deg)")
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        mu = self.trend.predict(df)
        v = self.krig.predict(df[self.lon_col].to_numpy(), df[self.lat_col].to_numpy())
        if v.ndim == 1:
            v = v[:, None]
        out = mu.copy()
        for i, t in enumerate(self._modeled_targets):
            if t in out:
                out[t] = mu[t].to_numpy() + v[:, i]
        return out


def evaluate_trend_vs_hybrid(train_df: pd.DataFrame, test_df: pd.DataFrame,
                             targets: list[str], features: list[str],
                             length_scale_deg: float = 0.6) -> dict:
    """Per-target metrics for trend-only vs hybrid on a held-out set.

    Returns {target: {"trend": {...}, "hybrid": {...}, "benchmark_r2": float}}.
    """
    hyb = HybridModel(targets, features, length_scale_deg=length_scale_deg).fit(train_df)
    trend_pred = hyb.trend.predict(test_df)
    hyb_pred = hyb.predict(test_df)
    out = {}
    for t in targets:
        if t not in trend_pred:
            continue
        yt = test_df[t].to_numpy()
        out[t] = {
            "trend": metrics(yt, trend_pred[t].to_numpy()),
            "hybrid": metrics(yt, hyb_pred[t].to_numpy()),
            "benchmark_r2": INDIA_BENCHMARK_R2.get(t.replace("_obs", "")),
        }
    return out
