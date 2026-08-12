"""Ensemble utilities: average predictions across multiple models (seeds).

The simplest effective variance-reduction tool for low-SNR regression is
seed ensembling: train the *same* architecture on the *same* data with
several different random seeds and average their predictions.  The theory
is elementary -- uncorrelated (or weakly correlated) errors cancel when
averaged, while the shared signal component adds up.  For quantile models
we average the entire ``(B, n_quantiles)`` tensor, which preserves the
per-quantile interpretation.

Public API:
    - :class:`ModelEnsemble`    -- callable wrapper over a list of models
    - :func:`train_ensemble`    -- train ``n_seeds`` models sequentially
    - :func:`ensemble_predict`  -- batched inference with averaging

The trainer :func:`src.training.trainer_v2.train_one_fold_v2` accepts a
``seed`` kwarg that makes each fit deterministic-given-seed, which is what
:func:`train_ensemble` relies on.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .trainer_v2 import train_one_fold_v2


# ---------------------------------------------------------------------------
# Default seed set
# ---------------------------------------------------------------------------

_DEFAULT_SEEDS: List[int] = [42, 123, 7, 91, 555]


# ---------------------------------------------------------------------------
# ModelEnsemble
# ---------------------------------------------------------------------------

class ModelEnsemble(nn.Module):
    """Average predictions from a list of trained models.

    All member models must accept the same ``forward`` signature and
    return a dict with at least the key ``"quantiles"`` of shape
    ``(B, n_quantiles)``.

    Usage
    -----
    >>> ens = ModelEnsemble([m1, m2, m3])
    >>> ens.eval()
    >>> out = ens(x_feat, x_raw)
    >>> out["quantiles"].shape  # (B, n_quantiles)

    The ensemble itself is an :class:`nn.Module` so ``.to(device)``,
    ``.eval()`` and ``.train()`` propagate to every member.
    """

    def __init__(self, models: List[nn.Module]):
        super().__init__()
        if len(models) == 0:
            raise ValueError("ModelEnsemble requires at least one model")
        # Register as ModuleList so .to()/.eval() propagate and members
        # show up in state_dict() (useful for bundled checkpoints).
        self.models = nn.ModuleList(models)

    def forward(self, *args, **kwargs) -> Dict[str, torch.Tensor]:
        outputs = [m(*args, **kwargs) for m in self.models]
        # Average quantiles -- stack along a new "model" axis then mean.
        q_stack = torch.stack([o["quantiles"] for o in outputs], dim=0)
        avg_q = q_stack.mean(dim=0)
        # Median column (index n_q // 2) as point prediction.  Works for any
        # odd n_quantiles including the default 3.
        point = avg_q[:, avg_q.shape[1] // 2]
        return {"quantiles": avg_q, "point_pred": point}


# ---------------------------------------------------------------------------
# train_ensemble
# ---------------------------------------------------------------------------

def train_ensemble(
    model_fn: Callable[[], nn.Module],
    train_dataset,
    val_dataset,
    out_dir: str,
    n_seeds: int = 5,
    seeds: Optional[List[int]] = None,
    **train_kwargs: Any,
) -> Dict[str, Any]:
    """Train ``n_seeds`` models with different seeds, save each checkpoint.

    Each member is trained by :func:`train_one_fold_v2` with its own
    ``seed`` kwarg in a dedicated sub-directory
    ``{out_dir}/seed_{seed}/``.  The freshly-trained model (still in
    memory) is returned in the output dict; the on-disk ``best_model.pt``
    is also available for later reload.

    Parameters
    ----------
    model_fn : callable
        Zero-arg factory returning a freshly-initialised ``nn.Module``.
        A new model is built per seed so that seed-dependent weight
        initialisation is applied.
    train_dataset, val_dataset : Dataset
        Shared across all seed runs.
    out_dir : str
        Parent directory for seed sub-folders.
    n_seeds : int
        Number of ensemble members to train (clipped to ``len(seeds)``).
    seeds : list[int], optional
        Explicit seed list.  Defaults to ``[42, 123, 7, 91, 555][:n_seeds]``.
    **train_kwargs
        Forwarded to :func:`train_one_fold_v2`.  ``seed`` and ``out_dir``
        are injected per-member and must NOT appear in ``train_kwargs``.

    Returns
    -------
    dict with keys:
        ``models``         -- list[nn.Module]  trained members
        ``seeds``          -- list[int]        seeds actually used
        ``best_metrics``   -- list[dict]       per-member metrics
        ``mean_val_corr``  -- float            mean across members
        ``std_val_corr``   -- float            std across members (NaN if n<2)
    """
    if seeds is None:
        seeds = list(_DEFAULT_SEEDS)
    seeds = list(seeds)[:n_seeds]
    if len(seeds) < n_seeds:
        raise ValueError(
            f"Need {n_seeds} seeds, got {len(seeds)} in `seeds`"
        )

    if "seed" in train_kwargs:
        raise ValueError("`seed` is injected per-member; do not pass it in train_kwargs")
    if "out_dir" in train_kwargs:
        raise ValueError("`out_dir` is injected per-member; do not pass it in train_kwargs")

    os.makedirs(out_dir, exist_ok=True)

    models: List[nn.Module] = []
    metrics_list: List[Dict[str, Any]] = []
    val_corrs: List[float] = []

    for s in seeds:
        sub_dir = os.path.join(out_dir, f"seed_{s}")
        # Seed *before* instantiating the model so weight init is
        # seed-dependent (otherwise every member would share identical
        # initial weights and only differ by data-shuffle order).
        torch.manual_seed(s)
        np.random.seed(s)
        model = model_fn()
        m = train_one_fold_v2(
            model=model,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            out_dir=sub_dir,
            seed=s,
            **train_kwargs,
        )
        metrics_list.append(m)
        val_corrs.append(float(m.get("val_corr", float("nan"))))
        # Note: the *best* checkpoint on disk may differ from the in-memory
        # weights (which are the *last*-epoch weights).  For strict best
        # reuse, the caller can reload best_model.pt.  In practice both
        # give very similar ensemble results given val-correlation
        # checkpointing; exposing the in-memory model keeps the API simple.
        models.append(model)

    mean_val_corr = float(np.mean(val_corrs)) if val_corrs else float("nan")
    std_val_corr = float(np.std(val_corrs, ddof=0)) if len(val_corrs) >= 2 else float("nan")

    return {
        "models": models,
        "seeds": seeds,
        "best_metrics": metrics_list,
        "mean_val_corr": mean_val_corr,
        "std_val_corr": std_val_corr,
    }


# ---------------------------------------------------------------------------
# ensemble_predict
# ---------------------------------------------------------------------------

def ensemble_predict(
    models: List[nn.Module],
    dataloader: DataLoader,
    device: str = "cpu",
    has_raw: bool = True,
) -> np.ndarray:
    """Run ensemble inference, returning averaged quantile predictions.

    Each member is run on every batch; the ``"quantiles"`` tensors are
    averaged across members on a per-batch basis and concatenated.

    Parameters
    ----------
    models : list[nn.Module]
        Trained ensemble members.
    dataloader : DataLoader
        Yields 3/4/5-tuples matching the trainer's conventions.
    device : str
        Torch device for inference.
    has_raw : bool
        If ``True``, batches are expected as ``(x_feat, x_raw, y, mask)``
        (or ``(x_feat, x_raw, regime_prior, y, mask)`` for 5-tuples).
        If ``False``, batches are ``(x_feat, y, mask)``.

    Returns
    -------
    np.ndarray of shape ``(N_total, n_quantiles)``
        Ensemble-averaged quantile predictions in dataset order.
    """
    if len(models) == 0:
        raise ValueError("ensemble_predict requires at least one model")

    device_obj = torch.device(device)
    for m in models:
        m.to(device_obj)
        m.eval()

    chunks: List[np.ndarray] = []
    with torch.no_grad():
        for batch in dataloader:
            # Detect 5-tuple (regime_prior) vs 4-tuple vs 3-tuple.
            if has_raw and len(batch) == 5:
                x_feat, x_raw, regime_prior, _y, _mask = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                regime_prior = regime_prior.to(device_obj)
                outs = [
                    m(x_feat, x_raw, regime_prior=regime_prior) for m in models
                ]
            elif has_raw:
                x_feat, x_raw, _y, _mask = batch
                x_feat = x_feat.to(device_obj)
                x_raw = x_raw.to(device_obj)
                outs = [m(x_feat, x_raw) for m in models]
            else:
                x_feat, _y, _mask = batch
                x_feat = x_feat.to(device_obj)
                outs = [m(x_feat) for m in models]

            q_stack = torch.stack([o["quantiles"] for o in outs], dim=0)
            avg_q = q_stack.mean(dim=0).cpu().numpy()
            chunks.append(avg_q)

    return np.concatenate(chunks, axis=0)
