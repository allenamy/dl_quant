"""SMOKE test for the DUAL-SOURCE + perp-raw-book 3rd arm (Stage G).

Proves, on the real built cache (controller builds the smoke days first):

  1. cache contract: data/npz_dualsrclob/<day>.npz carries EVERY key of
     data/npz_dualsrc/<day>.npz BYTE-IDENTICAL (verbatim copy) PLUS the new key
     X_raw_perp_deep, whose shape == the dual-SOURCE X_raw shape (N,600,20,4).
  2. DualLOBDataset over the cache yields the 6-tuple
     (x_feat[69], x_raw, regime_prior[10], y, mask, x_raw_perp_deep) and the perp
     book is finite. The f16-preload memory fix is exercised (preload=True): the
     resident _pre_X_raw / _pre_X_raw_perp are float16 but each fetched row is f32.
  3. DualLOBREGArch(use_perp_residual=True, d_prior=10, n_features=69) instantiates
     and runs ~6 train steps: loss FINITE + DECREASES, and gradient reaches ALL
     THREE input paths in ONE backward:
        - perp_alpha (the perp-raw gated-residual master gate),
          AND the perp residual sub-net (raw_encoder_perp / perp_proj / perp_gate),
        - the SPOT raw Path-B tower (raw_encoder),
        - the x_feat features (the 69-wide feature tensor, incl. divergence-seq).
  4. ZERO-INIT IDENTITY at perp_alpha=0: with the master gate forced to 0,
     tanh(0)=0 so the residual term is EXACTLY 0 — the full-model output is
     BIT-IDENTICAL to the same model run with x_raw_perp_deep=None (residual
     skipped). With perp_alpha != 0 the output MUST differ (residual is live).

Tiny by construction (2 days, ~6 steps, CPU). Build the cache first:
    python multi_asset/data/build_dualsrclob_npz.py --days 2025-02-10 2026-01-05

Run on jpline:
    /root/miniconda3/envs/hsy_v5push/bin/python -m pytest \
        multi_asset/data/test_dualsrclob_smoke.py -q -s
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

from multi_asset.data.dual_lob_dataset import DualLOBDataset, PERP_KEY  # noqa: E402
from multi_asset.model.dual_lob_regarch import DualLOBREGArch  # noqa: E402
from src.training.trainer_v2 import _build_loss_fn_for_dul  # noqa: E402

_CAND_DAYS = ["2025-02-10", "2026-01-05"]
_DUALSRCLOB_DIR = osp.join(_ROOT, "data", "npz_dualsrclob")
_DUALSRC_DIR = osp.join(_ROOT, "data", "npz_dualsrc")

N_SPOT = 64
N_FEAT = 69
N_PRIOR = 10

# REG_arch config matching configs/v5push/perp_dualsrclob_roll.json, d_prior=10,
# plus the perp-residual extension kwargs.
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
    # perp-residual extension:
    use_perp_residual=True, perp_n_levels=20, d_perp=16, perp_alpha_init=0.05,
)
_DUL = dict(
    lambda_quantile=0.1, lambda_utility_rank=0.5, lambda_dir_huber=0.5,
    utility_alpha=0.0, dir_huber_w_wrong=0.0, dir_huber_w_extreme=0.0,
    lambda_cls=0.1, lambda_mag_focal_huber=0.3, cls_weight_mode="tail_focal_1p5",
)


def _avail_days():
    if not osp.isdir(_DUALSRCLOB_DIR):
        return []
    return [d for d in _CAND_DAYS
            if osp.exists(osp.join(_DUALSRCLOB_DIR, f"{d}.npz"))]


_DAYS = _avail_days()
_skip = pytest.mark.skipif(
    len(_DAYS) == 0,
    reason=f"no dualsrclob cache under {_DUALSRCLOB_DIR}; build with "
           f"build_dualsrclob_npz.py --days {' '.join(_CAND_DAYS)}",
)


def _build_model(n_feat, n_lvl):
    return DualLOBREGArch(n_features=n_feat, n_levels=n_lvl, **_MODEL_CFG)


# --------------------------------------------------------------------------- #
# 1. cache contract: verbatim dualsrc keys + X_raw_perp_deep shape == X_raw     #
# --------------------------------------------------------------------------- #
@_skip
def test_cache_verbatim_dualsrc_plus_perp_book():
    for d in _DAYS:
        lob = np.load(osp.join(_DUALSRCLOB_DIR, f"{d}.npz"), allow_pickle=True)
        src = np.load(osp.join(_DUALSRC_DIR, f"{d}.npz"), allow_pickle=True)

        # NEW key present + shape == dual-SOURCE X_raw shape.
        assert PERP_KEY in lob.files, f"{d}: missing {PERP_KEY!r}"
        assert lob[PERP_KEY].shape == src["X_raw"].shape, (
            f"{d}: {PERP_KEY} shape {lob[PERP_KEY].shape} != "
            f"X_raw shape {src['X_raw'].shape}")
        assert lob[PERP_KEY].shape[1:] == (600, 20, 4)
        assert np.isfinite(np.asarray(lob[PERP_KEY], dtype=np.float32)).all(), \
            f"{d}: non-finite values in {PERP_KEY}"

        # EVERY dual-SOURCE key copied VERBATIM (byte-identical), nothing dropped.
        assert set(src.files).issubset(set(lob.files)), (
            f"{d}: dualsrclob is missing dualsrc keys "
            f"{set(src.files) - set(lob.files)}")
        # the only NEW key is the perp book
        assert set(lob.files) - set(src.files) == {PERP_KEY}, (
            f"{d}: unexpected extra keys "
            f"{set(lob.files) - set(src.files) - {PERP_KEY}}")
        for k in src.files:
            a = np.asarray(src[k])
            b = np.asarray(lob[k])
            assert a.shape == b.shape and a.dtype == b.dtype, (
                f"{d}: key {k!r} shape/dtype drift {a.shape}/{a.dtype} -> "
                f"{b.shape}/{b.dtype}")
            assert np.array_equal(np.nan_to_num(a.astype(np.float64))
                                  if a.dtype.kind == "f" else a,
                                  np.nan_to_num(b.astype(np.float64))
                                  if b.dtype.kind == "f" else b), (
                f"{d}: key {k!r} NOT byte-identical to dualsrc (verbatim copy "
                f"broken)")
        print(f"[smoke] {d}: dualsrc keys verbatim OK; {PERP_KEY} shape="
              f"{lob[PERP_KEY].shape} dtype={lob[PERP_KEY].dtype}")
        lob.close()
        src.close()


# --------------------------------------------------------------------------- #
# 2. DualLOBDataset 6-tuple + f16 preload memory fix exercised                  #
# --------------------------------------------------------------------------- #
@_skip
def test_dataset_sixtuple_and_f16_preload():
    # preload=True exercises the Stage-G f16 memory fix in _do_preload.
    ds = DualLOBDataset(_DUALSRCLOB_DIR, _DAYS, normalize=False,
                        horizons=["y_600"], preload=True)
    assert ds.has_regime_prior, "dataset did not detect regime_prior"
    # resident raw books must be float16 (the memory fix); X stays float32.
    assert ds._pre_X_raw.dtype == np.float16, (
        f"_pre_X_raw dtype {ds._pre_X_raw.dtype} != float16 (memory fix not "
        f"applied)")
    assert ds._pre_X_raw_perp.dtype == np.float16, (
        f"_pre_X_raw_perp dtype {ds._pre_X_raw_perp.dtype} != float16")
    assert ds._pre_X.dtype == np.float32, "feature X must stay float32"

    item = ds[0]
    assert len(item) == 6, f"expected 6-tuple, got {len(item)}"
    x_feat, x_raw, rp, y, m, x_perp = item
    assert x_feat.shape[-1] == N_FEAT, f"x_feat width {x_feat.shape[-1]} != {N_FEAT}"
    assert rp.shape[-1] == N_PRIOR, f"regime width {rp.shape[-1]} != {N_PRIOR}"
    assert x_raw.shape[-2:] == (20, 4)
    assert x_perp.shape[-2:] == (20, 4), f"x_perp shape {x_perp.shape}"
    # fetched rows are upcast to f32 for the model (despite f16 resident storage).
    assert x_raw.dtype == torch.float32 and x_perp.dtype == torch.float32, (
        f"fetched raw dtypes {x_raw.dtype}/{x_perp.dtype} (should be f32 per-row)")
    assert torch.isfinite(x_perp).all(), "non-finite perp book in fetched item"
    print(f"[smoke] dataset 6-tuple OK; resident raws f16, fetched rows f32; "
          f"x_perp shape={tuple(x_perp.shape)}")


# --------------------------------------------------------------------------- #
# 3. ~6 train steps: loss finite + decreasing; grad to perp_alpha + spot + feat #
# --------------------------------------------------------------------------- #
@_skip
def test_train_loss_decreases_and_grad_three_paths():
    torch.manual_seed(0)
    ds = DualLOBDataset(_DUALSRCLOB_DIR, _DAYS[:1], normalize=False,
                        horizons=["y_600"], preload=False)
    x0, xr0, rp0, _, _, xp0 = ds[0]
    n_feat = x0.shape[-1]
    n_lvl = xr0.shape[-2]
    assert n_feat == N_FEAT and rp0.shape[-1] == N_PRIOR
    model = _build_model(n_feat, n_lvl)
    assert model.use_perp_residual and model.perp_alpha is not None
    # RevIN sized to n_features (69), not d_prior.
    assert model.revin.affine_weight.shape[0] == N_FEAT
    model.train()

    from torch.utils.data import DataLoader
    loss_fn = _build_loss_fn_for_dul(_DUL)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    loader = DataLoader(ds, batch_size=128, shuffle=False)
    batches = [b for _, b in zip(range(6), loader)]
    assert len(batches) >= 2

    losses = []
    for step in range(6):
        x_feat, x_raw, rp, y, m, x_perp = batches[step % len(batches)]
        idx = m.nonzero(as_tuple=True)[0]
        if len(idx) == 0:
            continue
        opt.zero_grad()
        out = model(x_feat, x_raw, regime_prior=rp, x_raw_perp_deep=x_perp)
        mo = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
        loss = loss_fn(mo, y[idx])
        assert torch.isfinite(loss), f"non-finite loss at step {step}"
        loss.backward()

        if step == 0:
            # ---- gradient reaches ALL THREE input paths in this one backward ----
            # (a) perp master gate + perp residual sub-net (raw_encoder_perp /
            #     perp_proj / perp_gate)
            assert model.perp_alpha.grad is not None and \
                float(model.perp_alpha.grad.abs()) > 0.0, \
                "ZERO grad on perp_alpha (perp gated residual gradient-starved)"
            g_perp_sub = 0.0
            for mod in (model.raw_encoder_perp, model.perp_proj, model.perp_gate):
                for prm in mod.parameters():
                    if prm.grad is not None:
                        g_perp_sub += float(prm.grad.abs().sum())
            assert g_perp_sub > 0.0, (
                "ZERO grad on perp residual sub-net (raw_encoder_perp/perp_proj/"
                "perp_gate) — perp book not influencing prediction")
            # (b) SPOT raw Path-B tower
            g_spot_raw = 0.0
            for prm in model.raw_encoder.parameters():
                if prm.grad is not None:
                    g_spot_raw += float(prm.grad.abs().sum())
            assert g_spot_raw > 0.0, "ZERO grad on SPOT raw Path-B (raw_encoder)"
            # (c) x_feat features — re-run a single isolated forward with a
            #     leaf-grad x_feat (the loader batch is not a leaf w.r.t. input).
            xf_g = x_feat.clone().requires_grad_(True)
            h = model.encode(x_feat=xf_g, x_raw=x_raw, regime_prior=rp,
                             x_raw_perp_deep=x_perp)
            out2 = model.quantile_heads[0](h)
            mo2 = {k: v[idx] for k, v in out2.items() if torch.is_tensor(v)}
            loss2 = loss_fn(mo2, y[idx])
            loss2.backward()
            assert xf_g.grad is not None
            g_feat = float(xf_g.grad.abs().sum())
            g_div = float(xf_g.grad[:, :, N_SPOT:].abs().sum())
            assert g_feat > 0.0, "ZERO grad on x_feat features"
            assert g_div > 0.0, "ZERO grad on divergence-seq channels (64:69)"
            print(f"[smoke] grad: perp_alpha={float(model.perp_alpha.grad.abs()):.4e} "
                  f"perp_sub={g_perp_sub:.4e} spot_raw={g_spot_raw:.4e} "
                  f"x_feat={g_feat:.4e} (div={g_div:.4e})")
            opt.zero_grad()  # discard the isolated-forward grads before stepping
            # re-do the step-0 backward cleanly so the optimizer step is well-formed
            out = model(x_feat, x_raw, regime_prior=rp, x_raw_perp_deep=x_perp)
            mo = {k: v[idx] for k, v in out.items() if torch.is_tensor(v)}
            loss = loss_fn(mo, y[idx])
            loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        losses.append(float(loss))
    print(f"[smoke] loss steps={['%.5f' % l for l in losses]}")
    assert len(losses) >= 4
    assert np.mean(losses[-2:]) < np.mean(losses[:2]), (
        f"loss did not decrease over 6 steps: {['%.5f' % l for l in losses]}")


# --------------------------------------------------------------------------- #
# 4. ZERO-INIT IDENTITY at perp_alpha=0 (residual exactly off => bit-identical) #
# --------------------------------------------------------------------------- #
@_skip
def test_zero_init_identity_at_perp_alpha_zero():
    torch.manual_seed(0)
    ds = DualLOBDataset(_DUALSRCLOB_DIR, _DAYS[:1], normalize=False,
                        horizons=["y_600"], preload=False)
    x0, xr0, _, _, _, _ = ds[0]
    model = _build_model(x0.shape[-1], xr0.shape[-2])
    model.eval()

    from torch.utils.data import DataLoader
    loader = DataLoader(ds, batch_size=64, shuffle=False)
    x_feat, x_raw, rp, y, m, x_perp = next(iter(loader))

    with torch.no_grad():
        # Force the master gate to exactly 0 -> tanh(0)=0 -> residual term == 0.
        model.perp_alpha.data.fill_(0.0)
        out_a0 = model(x_feat, x_raw, regime_prior=rp,
                       x_raw_perp_deep=x_perp)["quantiles"]
        # Same model, residual SKIPPED entirely (perp tensor None).
        out_none = model(x_feat, x_raw, regime_prior=rp,
                         x_raw_perp_deep=None)["quantiles"]
        # IDENTITY: alpha=0 with the perp book present == skipping the residual.
        max_dev = float((out_a0 - out_none).abs().max())
        assert max_dev == 0.0, (
            f"perp_alpha=0 is NOT bit-identical to residual-off "
            f"(max|dev|={max_dev:.3e}); zero-init identity broken")

        # Sanity the other way: a NON-zero master gate MUST move the output (the
        # residual is genuinely wired, not dead). Use a sizeable alpha so the
        # zero-init perp_proj (std 0.02) * sigmoid-gate residual is clearly > 0.
        model.perp_alpha.data.fill_(1.0)
        out_a1 = model(x_feat, x_raw, regime_prior=rp,
                       x_raw_perp_deep=x_perp)["quantiles"]
        live = float((out_a1 - out_none).abs().max())
        assert live > 0.0, (
            "perp_alpha=1 did NOT change the output vs residual-off — the perp "
            "residual is dead-wired (perp_proj/perp_gate not contributing)")
    print(f"[smoke] zero-init identity: alpha=0 max|dev|={max_dev:.3e} (==0); "
          f"alpha=1 moves output max|dev|={live:.3e} (>0)")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-s"]))
