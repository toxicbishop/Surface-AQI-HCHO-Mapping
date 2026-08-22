"""AOD gap-filling (Change 1 -- highest priority, India-proven).

MAIAC AOD is ~41% missing (clouds, bright surfaces; winter >> summer). Using AOD
with gaps systematically biases surface PM2.5 (Katoch et al. 2023, ES&T: +19.1%
exposure overestimation over India). So we fill the gaps BEFORE the main model.

Backend: Random Forest on physically-motivated covariates (met + static + spatial
+ cyclical time). RF is the "acceptable" path (India RF R2~0.87, Maharashtra 2024).
A residual autoencoder (Li 2020 RSE, R2~0.94) is a documented future upgrade but is
NOT implemented here -- only the RandomForestGapFiller below exists.

Critically, skill is reported with SPATIALLY-CLUSTERED holdout CV (not random),
which mimics the real cloud-gap pattern -- random holdout overstates skill
(Kianian et al. 2021).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

from isro_aqi.utils.logging import get_logger

log = get_logger("gapfill_aod")

# Covariates that are themselves gap-free (met/static/spatial/time) -- never the
# gappy satellite columns. These explain AOD's spatial/seasonal structure.
DEFAULT_COVARIATES = [
    "temperature", "rh", "wind_speed", "pressure", "solar_radiation", "blh",
    "elevation", "slope", "lc_crop", "lc_built", "lc_tree", "lc_bare",
    "lat", "lon", "doy_sin", "doy_cos",
]


def _add_doy(df: pd.DataFrame) -> pd.DataFrame:
    if "time" in df.columns and "doy_sin" not in df.columns:
        doy = pd.to_datetime(df["time"]).dt.dayofyear
        df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
        df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return df


class RandomForestGapFiller:
    """Predict missing AOD from gap-free covariates with a Random Forest."""

    def __init__(self, covariates: list[str], n_estimators: int = 200,
                 max_depth: int | None = None, seed: int = 42):
        self.covariates = covariates
        self.model = RandomForestRegressor(
            n_estimators=n_estimators, max_depth=max_depth, n_jobs=-1, random_state=seed
        )
        self._fitted = False

    def fit(self, df: pd.DataFrame, target: str = "aod") -> "RandomForestGapFiller":
        sub = df.dropna(subset=[target])
        X = sub[self.covariates].fillna(0.0)
        self.model.fit(X, sub[target])
        self._fitted = True
        log.info(f"gap-fill RF fit on {len(sub):,} observed {target} cells")
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("call fit() first")
        return self.model.predict(df[self.covariates].fillna(0.0))

    def cv_score(self, df: pd.DataFrame, target: str = "aod",
                 block_deg: float = 2.0, k: int = 5, seed: int = 42) -> dict:
        """Spatially-clustered holdout CV -- mimics the real cloud-gap pattern.

        Random holdout overstates skill because nearby cells are autocorrelated;
        leaving out whole spatial blocks is the honest estimate (Kianian 2021).
        """
        sub = df.dropna(subset=[target]).copy()
        if len(sub) < 50:
            return {"cv_r2": float("nan"), "cv_rmse": float("nan"), "cv_n": int(len(sub))}
        rng = np.random.default_rng(seed)
        bx = (sub["lon"] // block_deg).astype(int)
        by = (sub["lat"] // block_deg).astype(int)
        block = (bx.astype(str) + "_" + by.astype(str)).to_numpy()
        blocks = np.unique(block)
        rng.shuffle(blocks)
        folds = np.array_split(blocks, min(k, len(blocks)))
        preds, trues = [], []
        for f in folds:
            val_mask = np.isin(block, f)
            if val_mask.all() or (~val_mask).sum() < 20 or val_mask.sum() == 0:
                continue
            m = RandomForestRegressor(n_estimators=120, n_jobs=-1, random_state=seed)
            m.fit(sub.loc[~val_mask, self.covariates].fillna(0.0), sub.loc[~val_mask, target])
            preds.append(m.predict(sub.loc[val_mask, self.covariates].fillna(0.0)))
            trues.append(sub.loc[val_mask, target].to_numpy())
        if not preds:
            return {"cv_r2": float("nan"), "cv_rmse": float("nan"), "cv_n": int(len(sub))}
        P, Y = np.concatenate(preds), np.concatenate(trues)
        return {"cv_r2": float(r2_score(Y, P)),
                "cv_rmse": float(np.sqrt(mean_squared_error(Y, P))),
                "cv_n": int(len(Y))}


def inject_aod_gaps(stack: xr.Dataset, frac: float = 0.3, var: str = "aod",
                    seed: int = 7) -> xr.Dataset:
    """Punch realistic CLUSTERED missingness into AOD (cloud-like) for the demo.

    Real MAIAC gaps are spatially clustered (cloud systems), not random pixels;
    we drop whole moving blobs so the gap-filler faces the real problem.
    """
    rng = np.random.default_rng(seed)
    out = stack.copy()
    a = out[var].values.copy()
    nt, nh, nw = a.shape
    n_blobs = max(1, int(frac * 6))
    for t in range(nt):
        mask = np.zeros((nh, nw), dtype=bool)
        for _ in range(n_blobs):
            ci, cj = rng.integers(0, nh), rng.integers(0, nw)
            ri, rj = rng.integers(2, max(3, nh // 3)), rng.integers(2, max(3, nw // 3))
            ii, jj = np.ogrid[:nh, :nw]
            mask |= ((ii - ci) / ri) ** 2 + ((jj - cj) / rj) ** 2 <= 1.0
        # cap per-day removal near the target fraction
        if mask.mean() > frac * 1.5:
            keep = rng.random((nh, nw)) < (frac * 1.5 / max(mask.mean(), 1e-6))
            mask &= keep
        a[t][mask] = np.nan
    out[var] = (("time", "lat", "lon"), a.astype("float32"))
    log.info(f"injected AOD gaps: {np.isnan(a).mean()*100:.1f}% missing")
    return out


def fill_aod_stack(stack: xr.Dataset, covariates: list[str] | None = None,
                   var: str = "aod", report_cv: bool = True, **rf_kw) -> tuple[xr.Dataset, dict]:
    """Fill missing AOD in a (time, lat, lon) stack; return (filled_stack, report).

    Trains an RF on the observed AOD cells using gap-free covariates, predicts the
    missing cells, and writes them back. Reports the missing fraction and (by
    default) spatially-clustered holdout CV skill.
    """
    df = _add_doy(stack.to_dataframe().reset_index())
    cov = [c for c in (covariates or DEFAULT_COVARIATES) if c in df.columns]
    df[var] = df[var].astype("float64")   # avoid float32<-float64 assignment warning
    miss = df[var].isna()
    report = {"missing_frac": float(miss.mean()), "covariates": cov}
    filler = RandomForestGapFiller(cov, **rf_kw).fit(df, target=var)
    if report_cv:
        report.update(filler.cv_score(df, target=var))
    if miss.any():
        df.loc[miss, var] = filler.predict(df[miss])
    filled = df.set_index(["time", "lat", "lon"])[var].to_xarray()
    out = stack.copy()
    out[var] = filled.transpose("time", "lat", "lon").astype("float32")
    log.info(f"AOD gap-fill: filled {int(miss.sum()):,} cells "
             f"({report['missing_frac']*100:.1f}% missing); cv_r2={report.get('cv_r2')}")
    return out, report
