"""Publication figures: validation scatter, correlation panels, importance bars."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def scatter_obs_pred(
    obs: np.ndarray, pred: np.ndarray, pollutant: str, out_path: str | None = None
):
    """Observed-vs-predicted density scatter with 1:1 line and R2/RMSE annotation."""
    from sklearn.metrics import mean_squared_error, r2_score

    mask = ~(np.isnan(obs) | np.isnan(pred))
    o, p = obs[mask], pred[mask]
    r2 = r2_score(o, p)
    rmse = np.sqrt(mean_squared_error(o, p))

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.hexbin(o, p, gridsize=50, cmap="viridis", mincnt=1)
    # lower bound must follow the data: hardcoding 0 clips negatives (e.g.
    # standardized residuals or fields like SO2 column that can be < 0).
    lim = [min(0.0, float(o.min()), float(p.min())), max(o.max(), p.max())]
    ax.plot(lim, lim, "k--", linewidth=1)
    ax.set(xlabel=f"Observed {pollutant}", ylabel=f"Predicted {pollutant}", xlim=lim, ylim=lim)
    ax.set_title(f"{pollutant}: R²={r2:.2f}, RMSE={rmse:.2f} (n={mask.sum():,})")
    if out_path:
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
    return fig


def importance_bar(importance: pd.DataFrame, top: int = 20, out_path: str | None = None):
    """Horizontal bar chart of SHAP mean-|value| feature importance."""
    d = importance.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 0.35 * len(d) + 1))
    ax.barh(d["feature"], d["importance"], color="#1f77b4")
    ax.set_xlabel("mean(|SHAP value|)")
    ax.set_title("Feature importance")
    if out_path:
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
    return fig


def hcho_o3_panel(df: pd.DataFrame, hcho="hcho", o3="o3_obs", out_path: str | None = None):
    """HCHO vs O3 scatter coloured by season (Phase 12 figure)."""
    fig, ax = plt.subplots(figsize=(5, 5))
    if "season" in df:
        for s, g in df.groupby("season"):
            ax.scatter(g[hcho], g[o3], s=6, alpha=0.4, label=str(s))
        ax.legend(fontsize=8)
    else:
        ax.scatter(df[hcho], df[o3], s=6, alpha=0.4)
    ax.set(xlabel="HCHO column", ylabel="Surface O₃")
    ax.set_title("HCHO–O₃ relationship")
    if out_path:
        fig.savefig(out_path, dpi=300, bbox_inches="tight")
    return fig
