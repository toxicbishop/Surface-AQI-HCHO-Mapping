"""TROPOMI NO2 -> surface-NO2 bias correction (Change 2 -- was missing).

Raw TROPOMI tropospheric NO2 *columns* systematically underestimate *surface*
NO2 (by ~4x in 2019 validation): the column integrates the whole troposphere and
its relation to the surface depends strongly on boundary-layer height (high BLH =>
better mixed => column more representative; low BLH => column biased). So before
TROPOMI NO2 can serve a surface AQI, it must be calibrated against ground truth.

We fit a regression-kriging-style TREND: column (+ BLH + met) -> CPCB surface NO2
(Valerio et al. 2025 use exactly GBR/RF/KNN as the regression stage). The residual
kriging refinement is provided generically by models/hybrid.py. Persist the fitted
transform and apply it to the full grid to get a satellite surface-NO2 product.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import xarray as xr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

from isro_aqi.utils.logging import get_logger

log = get_logger("calibrate_no2")

DEFAULT_COVARIATES = ["no2", "blh", "temperature", "wind_speed", "rh"]


class NO2Calibrator:
    """Map TROPOMI NO2 column (+ met) to surface NO2 using CPCB ground truth."""

    def __init__(self, covariates: list[str] | None = None, method: str = "rf",
                 column: str = "no2", target: str = "no2_obs", seed: int = 42):
        self.covariates = covariates or DEFAULT_COVARIATES
        self.method = method
        self.column = column
        self.target = target
        self.seed = seed
        self.model = None
        self._cov_used: list[str] = []

    def fit(self, df: pd.DataFrame) -> "NO2Calibrator":
        self._cov_used = [c for c in self.covariates if c in df.columns]
        sub = df.dropna(subset=[self.target] + self._cov_used)
        X, y = sub[self._cov_used].to_numpy(), sub[self.target].to_numpy()
        if self.method == "linear":
            self.model = LinearRegression()
        else:
            self.model = RandomForestRegressor(n_estimators=200, n_jobs=-1, random_state=self.seed)
        self.model.fit(X, y)
        log.info(f"NO2 calibration ({self.method}) fit on {len(sub):,} station-days "
                 f"using {self._cov_used}")
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("call fit() first")
        # The model was fitted on self._cov_used; those columns MUST be present at
        # predict time. Silently reindexing missing covariates to 0.0 (the old
        # behaviour) would feed the RF a column of zeros and quietly corrupt the
        # calibrated surface-NO2 field. Fail loudly instead.
        missing = [c for c in self._cov_used if c not in df.columns]
        if missing:
            raise KeyError(
                f"NO2Calibrator.predict: covariates missing from input grid: {missing}. "
                f"Required: {self._cov_used}"
            )
        # Per-row NaNs in present covariates are still filled (the grid has gaps);
        # the absence of an entire required column is what we refuse to tolerate.
        X = df[self._cov_used].fillna(0.0).to_numpy()
        return self.model.predict(X)

    def report(self, df: pd.DataFrame) -> dict:
        """Skill + the column->surface bias the calibration removes."""
        sub = df.dropna(subset=[self.target] + self._cov_used)
        pred = self.predict(sub)
        true = sub[self.target].to_numpy()
        col = sub[self.column].to_numpy() if self.column in sub else None
        # linear slope of surface ~ column (the raw, uncalibrated relationship)
        rep = {
            "r2": float(r2_score(true, pred)),
            "rmse": float(np.sqrt(mean_squared_error(true, pred))),
            "n": int(len(sub)),
            "method": self.method,
        }
        if col is not None and np.ptp(col) > 0:
            lr = LinearRegression().fit(col.reshape(-1, 1), true)
            rep["raw_column_slope"] = float(lr.coef_[0])
            rep["raw_column_r2"] = float(r2_score(true, lr.predict(col.reshape(-1, 1))))
            # how much the calibration improves over using the raw column alone
            rep["r2_gain_over_raw_column"] = round(rep["r2"] - rep["raw_column_r2"], 4)
        return rep

    def save(self, path: str):
        joblib.dump({"model": self.model, "cov": self._cov_used, "method": self.method}, path)

    @classmethod
    def load(cls, path: str) -> "NO2Calibrator":
        d = joblib.load(path)
        obj = cls(covariates=d["cov"], method=d["method"])
        obj.model, obj._cov_used = d["model"], d["cov"]
        return obj


def calibrate_no2_stack(stack: xr.Dataset, training_df: pd.DataFrame,
                        covariates: list[str] | None = None, method: str = "rf",
                        out_var: str = "no2_surface") -> tuple[xr.Dataset, dict]:
    """Add a calibrated surface-NO2 field to the stack; return (stack, report).

    training_df must hold the collocated covariates (incl. the TROPOMI 'no2'
    column) and the CPCB 'no2_obs' surface truth.
    """
    cal = NO2Calibrator(covariates, method).fit(training_df)
    report = cal.report(training_df)
    gdf = stack.to_dataframe().reset_index()
    gdf[out_var] = cal.predict(gdf)
    da = gdf.set_index(["time", "lat", "lon"])[out_var].to_xarray()
    out = stack.copy()
    out[out_var] = da.transpose("time", "lat", "lon").astype("float32")
    log.info(f"NO2 calibration: added '{out_var}' grid; r2={report['r2']:.3f}, "
             f"rmse={report['rmse']:.2f}")
    return out, report
