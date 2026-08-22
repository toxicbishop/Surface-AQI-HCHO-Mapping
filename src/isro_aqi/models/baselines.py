"""Tabular baselines: Random Forest (Model 1) and XGBoost (Model 2).

These set the accuracy floor the deep models must beat and provide fast SHAP
attributions (Phase 13). Multi-output is handled by training one regressor per
target (clearer per-pollutant tuning + SHAP than a single multi-output tree).
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from isro_aqi.utils.logging import get_logger

log = get_logger("baselines")


class _PerTargetModel:
    """Train one estimator per target column; predict returns a DataFrame."""

    def __init__(self, make_estimator, targets: list[str], features: list[str]):
        self._make = make_estimator
        self.targets = targets
        self.features = features
        self.models: dict[str, object] = {}

    def fit(self, df: pd.DataFrame):
        for t in self.targets:
            sub = df.dropna(subset=[t])
            if sub.empty:
                log.warning(f"no rows for target {t}; skipping")
                continue
            est = self._make()
            est.fit(sub[self.features].fillna(0.0), sub[t])
            self.models[t] = est
            log.info(f"fit {type(est).__name__} for {t} on {len(sub):,} rows")
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        Xf = X[self.features].fillna(0.0)
        return pd.DataFrame(
            {t: m.predict(Xf) for t, m in self.models.items()}, index=X.index
        )

    def __getstate__(self):
        # the estimator factory (`_make`) is a closure/lambda and is only needed
        # during fit(); drop it so the fitted model pickles cleanly.
        state = self.__dict__.copy()
        state["_make"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def save(self, path: str):
        # compress: fully-grown forests are large and compress well (~10x)
        joblib.dump(self, path, compress=3)

    @staticmethod
    def load(path: str) -> "_PerTargetModel":
        return joblib.load(path)


def RandomForestModel(targets, features, **kw) -> _PerTargetModel:
    params = dict(n_estimators=300, max_depth=None, n_jobs=-1, random_state=42)
    params.update(kw)
    return _PerTargetModel(lambda: RandomForestRegressor(**params), targets, features)


def XGBoostModel(targets, features, **kw) -> _PerTargetModel:
    from xgboost import XGBRegressor

    params = dict(
        n_estimators=600, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, n_jobs=-1, random_state=42,
        tree_method="hist",
    )
    params.update(kw)
    return _PerTargetModel(lambda: XGBRegressor(**params), targets, features)


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """R2, RMSE, MAE for a single target."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    mask = ~np.isnan(y_true)
    yt, yp = y_true[mask], y_pred[mask]
    return {
        "r2": float(r2_score(yt, yp)),
        "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
        "mae": float(mean_absolute_error(yt, yp)),
        "n": int(mask.sum()),
    }
