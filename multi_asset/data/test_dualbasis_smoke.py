"""SMOKE test for the DUAL-SOURCE basis-SEQUENCE integration (Stage E).

Proves, on the real merged cache (built first by the controller):

  1. ``build_basis_seq`` self-test (shape + corrupt-future-mids leakage) passes.
  2. ``data/npz_dualbasis/<day>.npz`` has X EXPANDED to (N,600,68): the first 64
     channels are byte-identical to the spot2perp / duallob X; the trailing 4 are
     the basis-seq channels, finite, and (at least one) non-degenerate. X_raw and
     X_raw_perp_deep are present and the PERP y_600 is preserved (== perp cache).
  3. ``DualLOBDataset`` over npz_dualbasis yields the 6-tuple with x_feat width 68.
  4. A real training step: loss FINITE + DECREASES; gradient reaches BOTH the
     GDCN basis channels (d(loss)/d(x_feat) is non-zero on channels 64:68 — the
     basis seq actually drives the prediction through GDCN+backbone) AND
     ``perp_alpha`` (the perp deep-book residual sub-net is not gradient-starved).

Tiny by construction (≤3 days, ~8 steps, CPU). Build the cache first:
    python multi_asset/data/build_basis_seq.py --days 2025-02-10 2025-02-11 2026-01-05

Run on jpline:
    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/data/test_dualbasis_smoke.py -q -s
"""
from __future__ import annotations

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

from multi_asset.data import build_basis_seq as bseq  # noqa: E402
from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402
from multi_asset.train.train_dual_lob import (  # noqa: E402
    build_dual_lob_model,
    train_one_fold_dual,
    _forward_dual,
)

_CAND_DAYS = ["2025-02-10", "2025-02-11", "2026-01-05"]
_DUALBASIS_DIR = osp.join(_ROOT, "data", "npz_dualbasis")
_SPOT2PERP_DIR = osp.join(_ROOT, "data", "npz_spot2perp")
_PERP_DIR = osp.join(_ROOT, "data", "npz_perp")

N_SPOT = 64
N_BASIS = bseq.N_BASIS_CH          # 4
N_FEAT_EXPECT = N_SPOT + N_BASIS   # 68


def _avail_days():
    if not osp.isdir(_DUALBASIS_DIR):
        return []
    return [d for d in _CAND_DAYS
            if osp.exists(osp.join(_DUALBASIS_DIR, f"{d}.npz"))]


_DAYS = _avail_days()
_skip = pytest.mark.skipif(
    len(_DAYS) == 0,
    reason=f"no dualbasis cache under {_DUALBASIS_DIR}; build with "
           f"build_basis_seq.py --days {' '.join(_CAND_DAYS)}",
)

_MODEL_CFG = dict(
    d_model=32, d_raw=16, d_prior=6, dropout=0.0, n_horizons=1,
    use_monotonic_quantile=True, use_revin=True, use_masknet=False, use_gdcn=True,
    use_raw_path=True, use_attention=False, use_conv=False,
    use_channel_mix_conv=True, use_level_attention_pool=True,
    use_patch_attention_pool=False, use_ppnet_gate=True,
    backbone_kind="conformer",
    backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
    use_direction_aware_head=True, use_film_multistage=True,
    use_perp_residual=True, perp_n_levels=20, d_perp=16, perp_alpha_init=0.05,
)
_DUL = dict(
    lambda_quantile=0.1, lambda_utility_rank=0.5, lambda_dir_huber=0.5,
    utility_alpha=0.0, dir_huber_w_wrong=0.0, dir_huber_w_extreme=0.0,
    lambda_cls=0.1, lambda_mag_focal_huber=0.3, cls_weight_mode="tail_focal_1p5",
)


# --------------------------------------------------------------------------- #
# 0. builder self-test (shape + leakage) — runs even with no cache on disk    #
# --------------------------------------------------------------------------- #
def test_builder_selftest_shape_and_leakage():
    assert bseq._selftest(), "build_basis_seq self-test (shape/leakage) failed"


# --------------------------------------------------------------------------- #
# 1. cache contract: X expanded to 68, spot-64 preserved, basis-seq finite     #
# --------------------------------------------------------------------------- #
@_skip
def test_cache_X_expanded_and_spot_preserved():
    d0 = _DAYS[0]
    db = np.load(osp.join(_DUALBASIS_DIR, f"{d0}.npz"), allow_pickle=True)
    X = db["X"]
    assert X.ndim == 3 and X.shape[1] == 600 and X.shape[2] == N_FEAT_EXPECT, (
        f"X shape {X.shape} != (N,600,{N_FEAT_EXPECT})"
    )
    # required keys carried verbatim
    for k in ("X_raw", "X_raw_perp_deep", "y_600", "y_mask_600", "timestamps"):
        assert k in db.files, f"dualbasis cache missing key {k!r}"
    assert db["X_raw_perp_deep"].shape == db["X_raw"].shape

    # first 64 channels byte-identical to the spot2perp source X (verbatim copy).
    src = np.load(osp.join(_SPOT2PERP_DIR, f"{d0}.npz"), allow_pickle=True)
    assert np.array_equal(
        np.nan_to_num(src["X"]), np.nan_to_num(X[:, :, :N_SPOT])
    ), "spot-64 channels drifted vs spot2perp source"

    # PERP y_600 preserved (== the perp cache → dual-source target intact).
    perp = np.load(osp.join(_PERP_DIR, f"{d0}.npz"), allow_pickle=True)
    assert np.array_equal(
        np.nan_to_num(src["y_600"]), np.nan_to_num(db["y_600"])
    ), "y_600 drifted vs spot2perp"
    assert np.array_equal(
        np.nan_to_num(perp["y_600"]), np.nan_to_num(db["y_600"])
    ), "y_600 != PERP cache (target is no longer the perp return)"

    # basis-seq channels: finite + at least one non-degenerate (std>0).
    basis = X[:, :, N_SPOT:]
    assert np.isfinite(basis).all(), "non-finite basis-seq channel"
    stds = [float(np.std(basis[:, :, c])) for c in range(N_BASIS)]
    assert max(stds) > 1e-9, f"all basis-seq channels degenerate (std={stds})"
    print(f"[smoke] {d0}: X {X.shape}, basis-seq ch std={['%.4f' % s for s in stds]}")


@_skip
def test_basis_seq_causal_on_real_day():
    """End-to-end causality on a REAL day: rebuild the day's basis-seq, corrupt
    the day's mids AFTER a cut second, and confirm every window-step at or before
    the cut is byte-identical (no future mid leaks into a ≤t basis-seq step)."""
    d0 = _DAYS[0]
    sec, spot_mid, perp_mid = bseq._load_mids(d0)
    db = np.load(osp.join(_DUALBASIS_DIR, f"{d0}.npz"), allow_pickle=True)
    ts_us = db["timestamps"].astype(np.int64)
    last_secs = ts_us // bseq.US_PER_SEC

    f0 = bseq.per_second_factors(sec, spot_mid, perp_mid)
    seq0 = bseq.basis_seq_for_windows(sec, f0, last_secs, bseq.INPUT_LEN)

    cut = int(sec[sec.size // 2])
    spot_c, perp_c = spot_mid.copy(), perp_mid.copy()
    fut = sec > cut
    spot_c[fut] = 1e-3
    perp_c[fut] = -1e9
    f1 = bseq.per_second_factors(sec, spot_c, perp_c)
    seq1 = bseq.basis_seq_for_windows(sec, f1, last_secs, bseq.INPUT_LEN)

    offs = np.arange(bseq.INPUT_LEN, dtype=np.int64) - (bseq.INPUT_LEN - 1)
    want = last_secs[:, None] + offs[None, :]
    le = want <= cut
    assert np.array_equal(seq0[le], seq1[le]), (
        "LEAKAGE: a ≤cut basis-seq step changed when future mids were corrupted"
    )
    print(f"[smoke] {d0}: causal OK ({int(le.sum())} ≤cut steps identical)")


# --------------------------------------------------------------------------- #
# 2. dataset width is 68                                                        #
# --------------------------------------------------------------------------- #
@_skip
def test_dataset_width_68():
    ds = DualLOBDataset(_DUALBASIS_DIR, _DAYS, normalize=False, horizons=["y_600"])
    item = ds[0]
    assert len(item) in (5, 6)
    x_feat = item[0]
    assert x_feat.shape[-1] == N_FEAT_EXPECT, (
        f"dataset x_feat width {x_feat.shape[-1]} != {N_FEAT_EXPECT}"
    )
    x_perp, x_raw = item[-1], item[1]
    assert x_perp.shape == x_raw.shape and torch.isfinite(x_perp).all()


# --------------------------------------------------------------------------- #
# 3. grad reaches BOTH the basis channels (via GDCN) AND perp_alpha            #
# --------------------------------------------------------------------------- #
@_skip
def test_grad_to_basis_channels_and_perp_alpha():
    torch.manual_seed(0)
    ds = DualLOBDataset(_DUALBASIS_DIR, _DAYS[:1], normalize=False, horizons=["y_600"])
    n_feat = ds[0][0].shape[-1]
    n_lvl = ds[0][1].shape[-2]
    assert n_feat == N_FEAT_EXPECT
    model = build_dual_lob_model(_MODEL_CFG, n_feat, n_lvl).train()

    from torch.utils.data import DataLoader
    from src.training.trainer_v2 import _build_loss_fn_for_dul
    loss_fn = _build_loss_fn_for_dul(_DUL)
    loader = DataLoader(ds, batch_size=64, shuffle=False)
    x_feat, x_raw, rp, y, m, x_perp = next(iter(loader))

    # require grad on x_feat → measure how much the loss depends on the basis
    # channels (64:68) vs the spot channels (0:64). Non-zero basis grad proves
    # the basis seq drives the prediction through GDCN+input_proj+backbone.
    x_feat = x_feat.clone().requires_grad_(True)
    out = _forward_dual(model, x_feat, x_raw, rp, x_perp)
    idx = m.nonzero(as_tuple=True)[0]
    assert len(idx) > 0
    m_out = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
    loss = loss_fn(m_out, y[idx])
    assert torch.isfinite(loss), "loss not finite"
    loss.backward()

    assert x_feat.grad is not None
    g_basis = float(x_feat.grad[:, :, N_SPOT:].abs().sum())
    g_spot = float(x_feat.grad[:, :, :N_SPOT].abs().sum())
    assert g_basis > 0.0, (
        "ZERO gradient on basis-seq channels (64:68) — basis seq is NOT "
        "influencing the prediction (GDCN fusion broken)"
    )
    # perp residual sub-net trains too.
    g_alpha = model.perp_alpha.grad
    assert g_alpha is not None and float(g_alpha.abs().sum()) > 0.0, (
        "perp_alpha got ZERO grad — perp residual sub-net gradient-starved"
    )
    g_enc = sum(float(p.grad.abs().sum())
                for p in model.raw_encoder_perp.parameters() if p.grad is not None)
    assert g_enc > 0.0, "raw_encoder_perp got ZERO grad (gradient-starved)"
    print(f"[smoke] grad: basis_ch={g_basis:.4e} spot_ch={g_spot:.4e} "
          f"perp_alpha={float(g_alpha.abs().sum()):.4e} perp_enc={g_enc:.4e}")


# --------------------------------------------------------------------------- #
# 4. few-step training: loss finite + decreasing                               #
# --------------------------------------------------------------------------- #
@_skip
def test_few_step_training_loss_decreases(tmp_path):
    torch.manual_seed(0)
    train_days = _DAYS[:1]
    val_days = _DAYS[-1:]
    train_ds = DualLOBDataset(_DUALBASIS_DIR, train_days, normalize=False, horizons=["y_600"])
    val_ds = DualLOBDataset(_DUALBASIS_DIR, val_days, normalize=False, horizons=["y_600"])
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
    assert len(hist) >= 3, f"expected ≥3 epochs, got {hist}"
    assert all(np.isfinite(hist)), f"non-finite loss: {hist}"
    assert hist[-1] < hist[0], (
        f"train loss did not decrease: first={hist[0]:.5f} last={hist[-1]:.5f} "
        f"(full={['%.5f' % h for h in hist]})"
    )
    print(f"[smoke] loss hist={['%.5f' % h for h in hist]}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-s"]))
