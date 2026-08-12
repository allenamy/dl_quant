"""SMOKE test for the dual-LOB TRAINING integration (Stage D2).

Distinct from ``multi_asset/model/test_dual_lob_regarch.py`` (which unit-tests the
MODEL's zero-init identity / grad). This file proves the END-TO-END training
WIRING works on the real merged cache:

  1. ``DualLOBDataset`` over ``data/npz_duallob`` yields the 6-tuple
     (x_feat, x_raw, regime_prior, y, mask, x_raw_perp_deep) with the perp deep
     book shaped like the spot book, and X / y identical to the spot2perp source.
  2. ``train_one_fold_dual`` runs a handful of steps with the real loss
     (dul_config), loss is FINITE and DECREASES, and ``perp_alpha`` receives a
     NON-ZERO gradient (the perp residual sub-net is actually training, not
     gradient-starved).

Tiny by construction (1-2 days, ~30 steps, CPU). The cache must be built first:
    python multi_asset/data/build_duallob_npz.py --days 2025-02-10 2025-02-11

Run on jpline:
    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/train/test_dual_lob_smoke.py -q -s
"""
from __future__ import annotations

import os
import os.path as osp
import sys

import numpy as np
import pytest
import torch

# jpline CPU torch raises "could not create a primitive" in oneDNN conv1d under
# this env; disable MKL-DNN for the (pure-correctness) smoke. No semantic effect.
torch.backends.mkldnn.enabled = False

_HERE = osp.dirname(osp.abspath(__file__))
_ROOT = osp.dirname(osp.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402
from multi_asset.model.dual_lob_regarch import DualLOBREGArch  # noqa: E402
from multi_asset.train.train_dual_lob import (  # noqa: E402
    build_dual_lob_model,
    train_one_fold_dual,
    _forward_dual,
)

# Candidate smoke days (any subset that exists is used). Built by the controller
# before running this test.
_CAND_DAYS = ["2025-02-10", "2025-02-11", "2024-12-01"]
_DUALLOB_DIR = osp.join(_ROOT, "data", "npz_duallob")
_SPOT2PERP_DIR = osp.join(_ROOT, "data", "npz_spot2perp")


def _avail_days():
    if not osp.isdir(_DUALLOB_DIR):
        return []
    return [d for d in _CAND_DAYS if osp.exists(osp.join(_DUALLOB_DIR, f"{d}.npz"))]


_DAYS = _avail_days()
_skip = pytest.mark.skipif(
    len(_DAYS) == 0,
    reason=f"no dual-LOB cache days under {_DUALLOB_DIR}; build with "
           f"build_duallob_npz.py --days {' '.join(_CAND_DAYS[:2])}",
)

# Small model config (production-shaped but cheap window via dataset's real T=600;
# d_model/d_raw small to keep CPU fast). Mirrors the perp_strong_duallob recipe.
_MODEL_CFG = dict(
    d_model=32, d_raw=16, d_prior=6, dropout=0.0, n_horizons=1,
    use_monotonic_quantile=True, use_revin=True, use_masknet=False, use_gdcn=True,
    use_raw_path=True, use_attention=False, use_conv=False,
    use_channel_mix_conv=True, use_level_attention_pool=True,
    use_patch_attention_pool=False, use_ppnet_gate=True,
    backbone_kind="conformer", backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
    use_direction_aware_head=True, use_film_multistage=True,
    use_perp_residual=True, perp_n_levels=20, d_perp=16, perp_alpha_init=0.05,
)
_DUL = dict(
    lambda_quantile=0.1, lambda_utility_rank=0.5, lambda_dir_huber=0.5,
    utility_alpha=0.0, dir_huber_w_wrong=0.0, dir_huber_w_extreme=0.0,
    lambda_cls=0.1, lambda_mag_focal_huber=0.3, cls_weight_mode="tail_focal_1p5",
)


# --------------------------------------------------------------------------- #
# 1. Dataset contract                                                          #
# --------------------------------------------------------------------------- #
@_skip
def test_dataset_returns_perp_and_matches_source():
    ds = DualLOBDataset(_DUALLOB_DIR, _DAYS, normalize=False, horizons=["y_600"])
    assert ds.has_raw
    item = ds[0]
    assert len(item) in (5, 6), f"expected 5/6-tuple, got len={len(item)}"
    x_perp = item[-1]
    x_raw = item[1]
    assert x_perp.shape == x_raw.shape, (
        f"perp book {tuple(x_perp.shape)} must match spot book {tuple(x_raw.shape)}"
    )
    assert torch.isfinite(x_perp).all()

    # X and y_600 must be identical to the spot2perp source for day 0.
    d0 = _DAYS[0]
    src = np.load(osp.join(_SPOT2PERP_DIR, f"{d0}.npz"))
    dl = np.load(osp.join(_DUALLOB_DIR, f"{d0}.npz"))
    assert np.array_equal(np.nan_to_num(src["X"]), np.nan_to_num(dl["X"])), "X drifted"
    assert np.array_equal(np.nan_to_num(src["y_600"]), np.nan_to_num(dl["y_600"])), "y_600 drifted"
    # perp deep book matches the perp cache shape (already merged in builder).
    assert dl["X_raw_perp_deep"].shape == dl["X_raw"].shape


@_skip
def test_dataset_preload_equals_lazy_first_item():
    lazy = DualLOBDataset(_DUALLOB_DIR, _DAYS[:1], normalize=False,
                          horizons=["y_600"], preload=False)
    pre = DualLOBDataset(_DUALLOB_DIR, _DAYS[:1], normalize=False,
                         horizons=["y_600"], preload=True)
    a = lazy[3]
    b = pre[3]
    assert len(a) == len(b)
    for ta, tb in zip(a, b):
        assert torch.allclose(ta.float(), tb.float(), atol=1e-6)


# --------------------------------------------------------------------------- #
# 2a. perp_alpha gets non-zero grad in a single real training step            #
# --------------------------------------------------------------------------- #
@_skip
def test_single_step_perp_alpha_grad_nonzero():
    torch.manual_seed(0)
    ds = DualLOBDataset(_DUALLOB_DIR, _DAYS[:1], normalize=False, horizons=["y_600"])
    n_feat = ds[0][0].shape[-1]
    n_lvl = ds[0][1].shape[-2]
    model = build_dual_lob_model(_MODEL_CFG, n_feat, n_lvl).train()

    from torch.utils.data import DataLoader
    from src.training.trainer_v2 import _build_loss_fn_for_dul
    loss_fn = _build_loss_fn_for_dul(_DUL)
    loader = DataLoader(ds, batch_size=64, shuffle=False)
    batch = next(iter(loader))
    x_feat, x_raw, rp, y, m, x_perp = batch
    out = _forward_dual(model, x_feat, x_raw, rp, x_perp)
    idx = m.nonzero(as_tuple=True)[0]
    assert len(idx) > 0
    m_out = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
    loss = loss_fn(m_out, y[idx])
    assert torch.isfinite(loss), "loss is not finite"
    loss.backward()

    g_alpha = model.perp_alpha.grad
    assert g_alpha is not None and float(g_alpha.abs().sum()) > 0.0, (
        "perp_alpha got ZERO grad — perp residual sub-net is not training"
    )
    g_enc = sum(float(p.grad.abs().sum()) for p in model.raw_encoder_perp.parameters()
                if p.grad is not None)
    assert g_enc > 0.0, "raw_encoder_perp got ZERO grad (gradient-starved)"


# --------------------------------------------------------------------------- #
# 2b. Few-step training: loss finite + decreasing via train_one_fold_dual      #
# --------------------------------------------------------------------------- #
@_skip
def test_few_step_training_loss_decreases(tmp_path):
    torch.manual_seed(0)
    # Use day 0 for train, day -1 for val (≥1 day each). Tiny + CPU-friendly.
    train_days = _DAYS[:1]
    val_days = _DAYS[-1:]
    train_ds = DualLOBDataset(_DUALLOB_DIR, train_days, normalize=False, horizons=["y_600"])
    val_ds = DualLOBDataset(_DUALLOB_DIR, val_days, normalize=False, horizons=["y_600"])
    n_feat = train_ds[0][0].shape[-1]
    n_lvl = train_ds[0][1].shape[-2]
    model = build_dual_lob_model(_MODEL_CFG, n_feat, n_lvl)

    out = train_one_fold_dual(
        model=model, train_dataset=train_ds, val_dataset=val_ds,
        out_dir=str(tmp_path / "fold0"), device="cpu",
        epochs=4, batch_size=64, lr=1e-3, weight_decay=1e-3, patience=10,
        grad_clip=1.0, dul_config=_DUL, seed=42, val_metric="composite",
        use_ema=False, num_workers=0, max_steps_per_epoch=8,
    )
    hist = out["train_loss_hist"]
    assert len(hist) >= 3, f"expected ≥3 epochs of loss, got {hist}"
    assert all(np.isfinite(hist)), f"non-finite loss in history: {hist}"
    # Decreasing: last epoch mean-loss strictly below the first (real learning,
    # not just noise) — these are smooth pinball/huber losses so a few hundred
    # samples × a few steps already moves them down.
    assert hist[-1] < hist[0], (
        f"train loss did not decrease over epochs: first={hist[0]:.5f} "
        f"last={hist[-1]:.5f} (full={['%.5f' % h for h in hist]})"
    )
    # A checkpoint may or may not pass the σ-gate in 4 tiny epochs; the
    # decreasing-loss + grad checks above are the binding smoke assertions.


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-s"]))
