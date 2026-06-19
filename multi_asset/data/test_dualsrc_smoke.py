"""SMOKE test for the DEFINITIVE DUAL-SOURCE sequence-DL cache (Stage F).

Proves, on the real built cache (controller builds the smoke days first) AND a
standalone builder unit (no cache needed):

  0. builder --selftest: shape + per-step leakage (corrupt-future mids/flow).
  1. cache contract: X (N,600,69) — spot-64 byte-identical to npz_spot2perp_clean,
     the 5 trailing DIFFERENCED channels finite + ~ZERO-MEAN (RevIN-safe);
     regime_prior (N,10) — the 4 trailing LEVEL columns finite, UN-normalized
     (basis_bps in bps, |mean| >> 0; spread_ratio ~1, NOT centered); y_600 ==
     the clean (leak-free) target verbatim; ts == clean ts.
  2. LOBDatasetV2 over the cache yields the 5-tuple with x_feat width 69 and
     regime_prior width 10.
  3. REG_arch (DualPathLOBModelV3) with d_prior=10 instantiates, runs ~6 train
     steps: loss FINITE + DECREASES.
  4. gradient reaches BOTH the new x_feat channels (64:69 — the divergence seq
     drives the prediction through GDCN+backbone) AND the FiLM path (film_gate_*
     trunk params get non-zero grad — the LEVEL regime columns reach the
     prediction via FiLM, not via RevIN).
  5. RevIN does NOT touch regime_prior: (a) structurally model.revin is sized to
     n_features (69), regime_prior (10) is never fed to it; (b) functionally,
     perturbing a LEVEL regime column changes the model output (so the level is
     consumed at its raw magnitude — RevIN would have removed a per-window mean
     and a constant shift across the window would vanish; here the per-sample
     level shift survives because it enters FiLM un-normalized).

Tiny by construction (≤3 days, ~6 steps, CPU). Build the cache first:
    python multi_asset/data/build_dualsrc_npz.py --days 2025-02-10 2026-01-05 2024-12-01

Run on jpline:
    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/data/test_dualsrc_smoke.py -q -s
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

from multi_asset.data import build_dualsrc_npz as bd  # noqa: E402
from src.training.dataset import LOBDatasetV2  # noqa: E402
from src.model.dual_path_model_v3 import DualPathLOBModelV3  # noqa: E402
from src.training.trainer_v2 import _build_loss_fn_for_dul  # noqa: E402

_CAND_DAYS = ["2025-02-10", "2026-01-05", "2024-12-01"]
_DUALSRC_DIR = osp.join(_ROOT, "data", "npz_dualsrc")
_CLEAN_DIR = osp.join(_ROOT, "data", "npz_spot2perp_clean")

N_SPOT = 64
N_FEAT = bd.N_FEAT       # 69
N_PRIOR = bd.N_PRIOR     # 10

# REG_arch config matching configs/v5push/perp_dualsrc_*.json, d_prior=10.
_MODEL_CFG = dict(
    d_model=32, d_raw=16, n_mask_blocks=1, n_cross_layers=1, patch_size=5,
    attn_nhead=2, attn_d_ff=64, d_prior=N_PRIOR, dropout=0.0, n_horizons=1,
    n_symbols=1, use_monotonic_quantile=True, use_revin=True, use_masknet=False,
    use_gdcn=True, use_raw_path=True, use_attention=False, use_conv=False,
    use_channel_mix_conv=True, use_level_attention_pool=True,
    use_patch_attention_pool=False, use_ppnet_gate=True,
    backbone_kind="conformer",
    backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
    use_direction_aware_head=True, use_film_multistage=True,
)
_DUL = dict(
    lambda_quantile=0.1, lambda_utility_rank=0.5, lambda_dir_huber=0.5,
    utility_alpha=0.0, dir_huber_w_wrong=0.0, dir_huber_w_extreme=0.0,
    lambda_cls=0.1, lambda_mag_focal_huber=0.3, cls_weight_mode="tail_focal_1p5",
)


def _avail_days():
    if not osp.isdir(_DUALSRC_DIR):
        return []
    return [d for d in _CAND_DAYS
            if osp.exists(osp.join(_DUALSRC_DIR, f"{d}.npz"))]


_DAYS = _avail_days()
_skip = pytest.mark.skipif(
    len(_DAYS) == 0,
    reason=f"no dualsrc cache under {_DUALSRC_DIR}; build with "
           f"build_dualsrc_npz.py --days {' '.join(_CAND_DAYS)}",
)


def _build_model(n_feat, n_lvl):
    return DualPathLOBModelV3(n_features=n_feat, n_levels=n_lvl, **_MODEL_CFG)


# --------------------------------------------------------------------------- #
# 0. builder self-test (shape + leakage) — runs even with no cache on disk     #
# --------------------------------------------------------------------------- #
def test_builder_selftest_shape_and_leakage():
    assert bd._selftest(), "build_dualsrc_npz self-test (shape/leakage) failed"


# --------------------------------------------------------------------------- #
# 1. cache contract: X=69, regime=10, levels UN-normalized, diff ~0-mean        #
# --------------------------------------------------------------------------- #
@_skip
def test_cache_shapes_levels_unnorm_and_diff_zeromean():
    d0 = _DAYS[0]
    z = np.load(osp.join(_DUALSRC_DIR, f"{d0}.npz"), allow_pickle=True)
    X, RP = z["X"], z["regime_prior"]
    assert X.shape[1:] == (600, N_FEAT), f"X shape {X.shape} != (N,600,{N_FEAT})"
    assert RP.shape[1:] == (N_PRIOR,), f"regime shape {RP.shape} != (N,{N_PRIOR})"
    for k in ("X_raw", "y_600", "y_mask_600", "timestamps"):
        assert k in z.files, f"dualsrc cache missing key {k!r}"

    # spot-64 byte-identical to the clean source X (verbatim copy)
    cl = np.load(osp.join(_CLEAN_DIR, f"{d0}.npz"), allow_pickle=True)
    assert np.array_equal(np.nan_to_num(cl["X"]), np.nan_to_num(X[:, :, :N_SPOT])), \
        "spot-64 channels drifted vs npz_spot2perp_clean"
    # y_600 + ts == the leak-free clean target verbatim
    assert np.array_equal(np.nan_to_num(cl["y_600"]), np.nan_to_num(z["y_600"])), \
        "y_600 != clean (leak-free) target"
    assert np.array_equal(cl["timestamps"].astype(np.int64),
                          z["timestamps"].astype(np.int64)), "ts != clean ts"
    # first 6 regime cols == clean regime verbatim
    assert np.array_equal(np.nan_to_num(cl["regime_prior"]),
                          np.nan_to_num(RP[:, :6])), "regime[:6] drifted vs clean"

    # the 5 trailing X channels: finite + ~ZERO-MEAN (RevIN-safe differences).
    diff = X[:, :, N_SPOT:]
    assert np.isfinite(diff).all(), "non-finite divergence X channel"
    dmean = np.abs(diff.reshape(-1, diff.shape[-1]).mean(axis=0))
    dstd = diff.reshape(-1, diff.shape[-1]).std(axis=0)
    print(f"[smoke] {d0} div X mean(|.|)={['%.4f' % m for m in dmean]} "
          f"std={['%.4f' % s for s in dstd]} names={bd.DIV_CH_NAMES}")
    assert max(dstd) > 1e-9, f"all divergence X channels degenerate (std={dstd})"
    # differenced channels must be ~zero-mean (|mean|/std small) — the whole point
    # of routing them through RevIN. Allow generous slack; flow-divergence can be
    # mildly biased but must be << a LEVEL feature's mean/std.
    for c, name in enumerate(bd.DIV_CH_NAMES):
        if dstd[c] > 1e-9:
            ratio = dmean[c] / (dstd[c] + 1e-12)
            assert ratio < 1.5, (
                f"divergence channel {name} mean/std={ratio:.2f} not ~zero-mean "
                f"(should be RevIN-safe; route to FiLM if it is a LEVEL)")

    # the 4 trailing regime columns: finite + UN-normalized LEVELS.
    lvl = RP[:, 6:]
    assert np.isfinite(lvl).all(), "non-finite LEVEL regime column"
    lmean = lvl.mean(axis=0)
    lstd = lvl.std(axis=0)
    print(f"[smoke] {d0} LEVEL regime mean={['%+.3f' % m for m in lmean]} "
          f"std={['%.3f' % s for s in lstd]} names={bd.LEVEL_COL_NAMES}")
    # basis_bps is a bps LEVEL: it must carry a real magnitude (NOT centered ~0).
    bidx = bd.LEVEL_COL_NAMES.index("basis_bps")
    assert abs(lmean[bidx]) > 0.05 or lstd[bidx] > 0.05, (
        f"basis_bps level looks centered/empty (mean={lmean[bidx]:.4f} "
        f"std={lstd[bidx]:.4f}); it must be the raw bps LEVEL, un-normalized")
    # spread_ratio is a ratio centered near 1 (parity), NOT near 0.
    sidx = bd.LEVEL_COL_NAMES.index("spread_ratio")
    assert lmean[sidx] > 0.2, (
        f"spread_ratio mean={lmean[sidx]:.3f} not a >0 ratio level "
        f"(un-normalized check)")


# --------------------------------------------------------------------------- #
# 2. dataset width is (69, 10)                                                  #
# --------------------------------------------------------------------------- #
@_skip
def test_dataset_widths():
    ds = LOBDatasetV2(_DUALSRC_DIR, _DAYS, normalize=False, horizons=["y_600"])
    assert ds.has_regime_prior, "dataset did not detect regime_prior"
    item = ds[0]
    assert len(item) == 5, f"expected 5-tuple (x,xraw,rp,y,m); got {len(item)}"
    x_feat, x_raw, rp, y, m = item
    assert x_feat.shape[-1] == N_FEAT, f"x_feat width {x_feat.shape[-1]} != {N_FEAT}"
    assert rp.shape[-1] == N_PRIOR, f"regime width {rp.shape[-1]} != {N_PRIOR}"
    assert x_raw.shape[-2:] == (20, 4)


# --------------------------------------------------------------------------- #
# 3+4. d_prior=10 model: loss decreases; grad to new X channels AND FiLM path   #
# --------------------------------------------------------------------------- #
@_skip
def test_model_dprior10_grad_to_div_channels_and_film():
    torch.manual_seed(0)
    ds = LOBDatasetV2(_DUALSRC_DIR, _DAYS[:1], normalize=False, horizons=["y_600"])
    x0, xr0, rp0, _, _ = ds[0]
    n_feat = x0.shape[-1]
    n_lvl = xr0.shape[-2]
    assert n_feat == N_FEAT and rp0.shape[-1] == N_PRIOR
    model = _build_model(n_feat, n_lvl)
    # the model's RevIN must be sized to n_features (69), NOT to d_prior.
    assert model.revin.affine_weight.shape[0] == N_FEAT, (
        f"RevIN sized {model.revin.affine_weight.shape[0]} != n_features {N_FEAT}")
    # FiLM gates must exist and consume d_prior=10.
    assert model.film_gate_block1 is not None and model.film_gate_final is not None, \
        "FiLM multi-stage gates not constructed (use_film_multistage / d_prior?)"
    first_lin = model.film_gate_block1.trunk[0]
    assert first_lin.in_features == N_PRIOR, (
        f"FiLM trunk in_features {first_lin.in_features} != d_prior {N_PRIOR} "
        f"(d_prior hardcoded? config not propagated?)")
    model.train()

    from torch.utils.data import DataLoader
    loss_fn = _build_loss_fn_for_dul(_DUL)
    loader = DataLoader(ds, batch_size=128, shuffle=False)
    x_feat, x_raw, rp, y, m = next(iter(loader))
    idx = m.nonzero(as_tuple=True)[0]
    assert len(idx) > 0

    # grad to new x_feat channels (64:69)
    x_feat_g = x_feat.clone().requires_grad_(True)
    h = model.encode(x_feat=x_feat_g, x_raw=x_raw, regime_prior=rp)
    out = model.quantile_heads[0](h)
    mo = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
    loss = loss_fn(mo, y[idx])
    assert torch.isfinite(loss), "loss not finite"
    loss.backward()
    assert x_feat_g.grad is not None
    g_div = float(x_feat_g.grad[:, :, N_SPOT:].abs().sum())
    g_spot = float(x_feat_g.grad[:, :, :N_SPOT].abs().sum())
    assert g_div > 0.0, (
        "ZERO grad on divergence X channels (64:69) — the divergence seq is NOT "
        "influencing the prediction (GDCN/backbone fusion broken)")

    # grad to the FiLM path: film_gate trunk params must receive non-zero grad
    # (the LEVEL regime columns reach the prediction through FiLM).
    g_film = 0.0
    for gate in (model.film_gate_block1, model.film_gate_block2,
                 model.film_gate_final):
        if gate is None:
            continue
        for prm in gate.parameters():
            if prm.grad is not None:
                g_film += float(prm.grad.abs().sum())
    assert g_film > 0.0, (
        "ZERO grad on FiLM gate params — the regime_prior LEVEL path is "
        "gradient-starved (FiLM not wired / regime_prior not reaching it)")
    print(f"[smoke] grad: div_X={g_div:.4e} spot_X={g_spot:.4e} FiLM={g_film:.4e}")


@_skip
def test_revin_does_not_touch_regime_prior():
    """Two-part proof the LEVEL regime is consumed UN-normalized via FiLM, not RevIN.

    (A) STRUCTURAL: RevIN is sized to n_features (69) and regime_prior (10) is
        never fed to it — verified by tracing model.revin.normalize calls; the
        regime tensor only reaches film_gate_* / ppnet_gate / regime_bias.
    (B) FUNCTIONAL: REG_arch FiLM gates are ZERO-INIT (γ→1, β→0 == identity) AND
        PPNet is skipped under use_film_multistage, so at init the regime path is
        identity by design (perturbing a level gives Δ=0 — expected, not a bug).
        After a few TRAIN steps the FiLM projections become non-zero, so perturbing
        the basis_bps LEVEL column then MOVES the output — proving the per-sample
        level shift survives into the prediction (a RevIN'd channel's constant
        per-window shift would be removed; this one is not, because it enters FiLM
        un-normalized)."""
    torch.manual_seed(0)
    ds = LOBDatasetV2(_DUALSRC_DIR, _DAYS[:1], normalize=False, horizons=["y_600"])
    x0, xr0, _, _, _ = ds[0]
    model = _build_model(x0.shape[-1], xr0.shape[-2])

    # (A) structural: RevIN width == n_features, and feeding regime_prior to the
    # RevIN module would be a shape error (10 != 69) — i.e. it is NOT RevIN'd.
    from torch.utils.data import DataLoader
    loader = DataLoader(ds, batch_size=64, shuffle=False)
    x_feat, x_raw, rp, y, m = next(iter(loader))
    assert model.revin.affine_weight.shape[0] == x_feat.shape[-1] == N_FEAT
    assert rp.shape[-1] == N_PRIOR and N_PRIOR != N_FEAT
    # spy on RevIN.normalize: every call must receive the 69-wide x_feat, never rp.
    seen_widths = []
    orig_norm = model.revin.normalize
    def _spy(x):
        seen_widths.append(int(x.shape[-1]))
        return orig_norm(x)
    model.revin.normalize = _spy
    with torch.no_grad():
        _ = model.encode(x_feat=x_feat, x_raw=x_raw, regime_prior=rp)
    model.revin.normalize = orig_norm
    assert seen_widths and all(w == N_FEAT for w in seen_widths), (
        f"RevIN.normalize saw widths {seen_widths}; expected only {N_FEAT} "
        f"(x_feat) — regime_prior must NOT be RevIN'd")
    print(f"[smoke] RevIN.normalize input widths={seen_widths} (== n_features, "
          f"regime_prior width {N_PRIOR} never RevIN'd)")

    # (B) functional, AFTER a few train steps (FiLM zero-init → identity at init).
    loss_fn = _build_loss_fn_for_dul(_DUL)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=0.0)
    model.train()
    for _ in range(30):
        idx = m.nonzero(as_tuple=True)[0]
        opt.zero_grad()
        h = model.encode(x_feat=x_feat, x_raw=x_raw, regime_prior=rp)
        out = model.quantile_heads[0](h)
        mo = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
        loss = loss_fn(mo, y[idx])
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        q0 = model.encode(x_feat=x_feat, x_raw=x_raw, regime_prior=rp)
        out0 = model.quantile_heads[0](q0)["quantiles"][:, 1]
        rp_pert = rp.clone()
        rp_pert[:, 6] = rp_pert[:, 6] + 5.0           # +5 bps on basis_bps LEVEL
        q1 = model.encode(x_feat=x_feat, x_raw=x_raw, regime_prior=rp_pert)
        out1 = model.quantile_heads[0](q1)["quantiles"][:, 1]
    delta = float((out1 - out0).abs().mean())
    print(f"[smoke] after 30 steps: perturb basis_bps level +5 -> mean |Δq50|={delta:.6e}")
    assert delta > 1e-7, (
        "after training, perturbing the basis_bps LEVEL still did NOT move the "
        "output — the level path (FiLM) is not learning to use the un-normalized "
        "regime level")


# --------------------------------------------------------------------------- #
# 3b. few-step training: loss finite + decreasing                              #
# --------------------------------------------------------------------------- #
@_skip
def test_few_step_training_loss_decreases():
    torch.manual_seed(0)
    ds = LOBDatasetV2(_DUALSRC_DIR, _DAYS[:1], normalize=False, horizons=["y_600"])
    model = _build_model(ds[0][0].shape[-1], ds[0][1].shape[-2]).train()

    from torch.utils.data import DataLoader
    loss_fn = _build_loss_fn_for_dul(_DUL)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    loader = DataLoader(ds, batch_size=128, shuffle=False)
    batches = [b for _, b in zip(range(6), loader)]
    assert len(batches) >= 2

    losses = []
    for step in range(6):
        x_feat, x_raw, rp, y, m = batches[step % len(batches)]
        idx = m.nonzero(as_tuple=True)[0]
        if len(idx) == 0:
            continue
        opt.zero_grad()
        h = model.encode(x_feat=x_feat, x_raw=x_raw, regime_prior=rp)
        out = model.quantile_heads[0](h)
        mo = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
        loss = loss_fn(mo, y[idx])
        assert torch.isfinite(loss), f"non-finite loss at step {step}"
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        losses.append(float(loss))
    print(f"[smoke] loss steps={['%.5f' % l for l in losses]}")
    assert len(losses) >= 4
    assert np.mean(losses[-2:]) < np.mean(losses[:2]), (
        f"loss did not decrease over 6 steps: {['%.5f' % l for l in losses]}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-s"]))
