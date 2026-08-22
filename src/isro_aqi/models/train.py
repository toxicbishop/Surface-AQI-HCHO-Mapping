"""Training loop + validation framework (Phases 6-7).

Validation follows Wang et al. 2023: report THREE schemes, because each answers a
different question:
    random_kfold   -- overall skill (optimistic; spatial+temporal autocorrelation leaks)
    spatial_kfold  -- can the model predict at UNSEEN locations? (block by lat/lon)
    temporal_split -- can it predict in UNSEEN time (held-out years)? -> the honest one

Masked MSE handles the multi-target case where a given station reports only some
pollutants (NaN targets contribute no gradient).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from isro_aqi.models.baselines import metrics as point_metrics
from isro_aqi.utils.logging import get_logger

log = get_logger("train")


def select_device(pref: str = "auto") -> torch.device:
    if pref != "auto":
        return torch.device(pref)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():  # Apple Silicon
        return torch.device("mps")
    return torch.device("cpu")


def masked_mse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    mask = ~torch.isnan(target)
    if mask.sum() == 0:
        return torch.tensor(0.0, requires_grad=True, device=pred.device)
    return ((pred[mask] - target[mask]) ** 2).mean()


# --- cross-validation splitters -------------------------------------------- #
def temporal_split(df: pd.DataFrame, test_years: list[int], date_col="date"):
    yr = pd.to_datetime(df[date_col]).dt.year
    test = df[yr.isin(test_years)]
    train = df[~yr.isin(test_years)]
    return train, test


def spatial_blocks(df: pd.DataFrame, block_deg: float = 0.5, k: int = 10, seed: int = 42):
    """Assign each row to a spatial block, then split blocks into k folds.

    Yields (train_df, val_df) so no block is split across train/val -- this is
    what makes the score reflect prediction at *unseen locations*.
    """
    rng = np.random.default_rng(seed)
    bx = (df["lon"] // block_deg).astype(int)
    by = (df["lat"] // block_deg).astype(int)
    block_id = bx.astype(str) + "_" + by.astype(str)
    blocks = block_id.unique()
    rng.shuffle(blocks)
    folds = np.array_split(blocks, k)
    for f in folds:
        val_mask = block_id.isin(set(f))
        yield df[~val_mask], df[val_mask]


# --- training -------------------------------------------------------------- #
def train_model(
    model: nn.Module,
    train_ds: Dataset,
    val_ds: Dataset,
    targets: list[str],
    epochs: int = 100,
    batch_size: int = 256,
    lr: float = 1e-3,
    patience: int = 12,
    device: str = "auto",
    ckpt_path: str = "models/cnn_lstm.pt",
    num_workers: int = 0,
) -> dict:
    """Train with Adam + early stopping on val masked-MSE. Returns best metrics.

    num_workers defaults to 0: the dataset holds a large in-memory cube, so worker
    processes would each copy it; 0 is faster and more stable for this workload
    (especially on macOS 'spawn').
    """
    dev = select_device(device)
    model = model.to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=4, factor=0.5)

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_dl = DataLoader(val_ds, batch_size=batch_size, num_workers=num_workers)

    best_val, best_state, stale = np.inf, None, 0
    for ep in range(1, epochs + 1):
        model.train()
        tr_loss = 0.0
        for x, y in train_dl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            loss = masked_mse(model(x), y)
            loss.backward()
            opt.step()
            tr_loss += loss.item() * len(x)
        tr_loss /= len(train_ds)

        val_loss = _evaluate_loss(model, val_dl, dev)
        sched.step(val_loss)
        log.info(f"epoch {ep:3d} | train {tr_loss:.4f} | val {val_loss:.4f}")

        if val_loss < best_val - 1e-5:
            best_val, best_state, stale = val_loss, {k: v.cpu() for k, v in model.state_dict().items()}, 0
            torch.save(best_state, ckpt_path)
        else:
            stale += 1
            if stale >= patience:
                log.info(f"early stop at epoch {ep}")
                break

    if best_state:
        model.load_state_dict(best_state)
    return evaluate_metrics(model, val_dl, targets, dev)


@torch.no_grad()
def _evaluate_loss(model, dl, dev) -> float:
    model.eval()
    tot, n = 0.0, 0
    for x, y in dl:
        x, y = x.to(dev), y.to(dev)
        tot += masked_mse(model(x), y).item() * len(x)
        n += len(x)
    return tot / max(n, 1)


@torch.no_grad()
def evaluate_metrics(model, dl, targets: list[str], dev) -> dict:
    """Per-target R2/RMSE/MAE on a loader, in the targets' NATIVE units.

    If the loader's dataset z-scored its targets (``target_mean``/``target_std``
    set, e.g. via PatchSequenceDataset), predictions AND truths are de-
    standardised back to physical units before metrics, so RMSE/MAE are reported
    in the pollutant's own units (ug/m^3, mg/m^3) -- matching how run_demo's
    ``_eval_cnn_lstm`` evaluates. R2 is scale-invariant either way.
    """
    model.eval()
    preds, trues = [], []
    for x, y in dl:
        preds.append(model(x.to(dev)).cpu().numpy())
        trues.append(y.numpy())
    P, Y = np.vstack(preds), np.vstack(trues)

    ds = getattr(dl, "dataset", None)
    tmean = getattr(ds, "target_mean", None)
    tstd = getattr(ds, "target_std", None)
    if tmean is not None and tstd is not None:
        # de-standardise both predictions and truths into native units
        P = P * tstd + tmean
        Y = Y * tstd + tmean
    return {t: point_metrics(Y[:, i], P[:, i]) for i, t in enumerate(targets)}
