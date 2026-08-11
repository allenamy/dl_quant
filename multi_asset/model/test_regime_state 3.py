"""D1 substrate tests: bit-identity, batch-invariance, stat-fit.

Run (local): PYTHONPATH=. python multi_asset/model/test_regime_state.py
Uses synthetic tensors only — no cache needed. The overlay-alignment unit test
and the CPU pre-gate live in multi_asset/data/build_state_prior.py (need CSVs).
"""
from __future__ import annotations

import numpy as np
import torch

from multi_asset.model.dual_lob_regarch import DualLOBREGArch

torch.set_grad_enabled(False)

N_FEAT, N_LEV, L = 88, 20, 600


def base_cfg(d_prior=6):
    return dict(
        n_features=N_FEAT, n_levels=N_LEV,
        d_model=32, d_raw=16, n_mask_blocks=1, n_cross_layers=1, patch_size=5,
        attn_nhead=2, attn_d_ff=64, d_prior=d_prior, dropout=0.2,
        n_horizons=1, n_symbols=1, use_monotonic_quantile=True, use_revin=True,
        use_masknet=False, use_gdcn=True, use_raw_path=True, use_attention=False,
        use_conv=False, use_channel_mix_conv=True, use_level_attention_pool=True,
        use_patch_attention_pool=False, use_ppnet_gate=True,
        backbone_kind="conformer",
        backbone_kwargs={"n_blocks": 2, "n_heads": 2, "kernel_size": 15},
        use_direction_aware_head=True, use_film_multistage=True,
        use_regime_film=True, regime_film_hidden=8, use_regime_bias=True,
        # perp residual (production default)
        use_perp_residual=True, perp_n_levels=N_LEV, d_perp=32, perp_alpha_init=0.02,
    )


def build(seed=0, **extra):
    cfg = base_cfg(d_prior=extra.pop("d_prior", 6))
    cfg.update(extra)
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = DualLOBREGArch(**cfg)
    return m.eval()


def make_inputs(B, d_prior=6, seed=1):
    g = torch.Generator().manual_seed(seed)
    x_feat = torch.randn(B, L, N_FEAT, generator=g)
    x_raw = torch.randn(B, L, N_LEV, 4, generator=g)
    x_perp = torch.randn(B, L, N_LEV, 4, generator=g)
    rp = torch.randn(B, d_prior, generator=g)
    return x_feat, x_raw, x_perp, rp


def fwd(m, x_feat, x_raw, x_perp, rp):
    # Compare the FULL quantile vector (q10/q50/q90). NOTE: q50/point_pred is
    # identically 0 for a fresh DAQH at init, so comparing point_pred would make
    # every test a trivial pass — the quantiles carry the real signal.
    return m(x_feat, x_raw, regime_prior=rp, x_raw_perp_deep=x_perp)["quantiles"]


def maxabs(a, b):
    return float((a - b).abs().max())


# --------------------------------------------------------------------------- #
def test_output_gain_noop():
    """T1a: use_output_gain ON vs OFF, identical seed -> EXACT (gain ×1 at init)."""
    x = make_inputs(64, d_prior=24)
    m_off = build(seed=7, d_prior=24, use_fixed_regime_state=True, use_state_prior=True,
                  use_output_gain=False)
    m_on = build(seed=7, d_prior=24, use_fixed_regime_state=True, use_state_prior=True,
                 use_output_gain=True)
    d = maxabs(fwd(m_off, *x), fwd(m_on, *x))
    ok = d == 0.0
    print(f"[T1a] output_gain no-op: max|Δ|={d:.3e}  -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_fixed_film_identity():
    """T1b: fixed-state pooled-h regime_film is EXACT identity at init."""
    m = build(seed=3, use_fixed_regime_state=True)
    film = m.regime_film
    zeros = (float(film.mlp[-1].weight.abs().max()) == 0.0
             and float(film.mlp[-1].bias.abs().max()) == 0.0)
    h = torch.randn(16, 32)
    desc = torch.randn(16, film.mlp[0].in_features)
    d = maxabs(film(h, desc), h)
    ok = zeros and d == 0.0
    print(f"[T1b] fixed FiLM exact identity: last-layer-zero={zeros} "
          f"film(h,desc)==h max|Δ|={d:.3e} -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_state_prior_noop():
    """T1c: the extra 18 state columns feed only zero-init gates -> no-op at init."""
    m = build(seed=5, d_prior=24, use_fixed_regime_state=True, use_state_prior=True,
              use_output_gain=True)
    x_feat, x_raw, x_perp, rp = make_inputs(48, d_prior=24)
    rp_zeroed = rp.clone()
    rp_zeroed[:, 6:] = 0.0  # zero the 18 state dims (base prior = first 6)
    d = maxabs(fwd(m, x_feat, x_raw, x_perp, rp),
               fwd(m, x_feat, x_raw, x_perp, rp_zeroed))
    ok = d == 0.0
    print(f"[T1c] state columns no-op at init: max|Δ|={d:.3e} -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_run1_vs_baseline_nonregime():
    """T1d: with shared weights synced and both pooled-h FiLMs zeroed, Run1's
    NON-regime path is bit-identical to the production baseline (the bugfix lives
    exclusively in the regime pathway)."""
    base = build(seed=9, use_fixed_regime_state=False)
    run1 = build(seed=9, use_fixed_regime_state=True)
    # copy every shared param/buffer base -> run1 (same shapes: d_prior unchanged)
    bsd = base.state_dict()
    run1.load_state_dict({k: v for k, v in bsd.items() if k in run1.state_dict()
                          and v.shape == run1.state_dict()[k].shape}, strict=False)
    # zero BOTH pooled-h regime_films -> exact identity in both
    for mdl in (base, run1):
        torch.nn.init.zeros_(mdl.regime_film.mlp[-1].weight)
        torch.nn.init.zeros_(mdl.regime_film.mlp[-1].bias)
    x = make_inputs(64, d_prior=6)
    d = maxabs(fwd(base, *x), fwd(run1, *x))
    ok = d == 0.0
    print(f"[T1d] Run1 non-regime path == baseline (FiLMs zeroed): "
          f"max|Δ|={d:.3e} -> {'PASS' if ok else 'FAIL'}")
    return ok


def test_batch_invariance():
    """T2: preds must be batch-composition invariant.

    OLD (baseline, batch-z extractor): expected to FAIL (demonstrates the bug).
    NEW (use_fixed_regime_state): expected to PASS (frozen stats, no batch stats)."""
    x_feat, x_raw, x_perp, rp = make_inputs(64, d_prior=6)

    def preds_at(m, bs):
        outs = []
        for s in range(0, 64, bs):
            outs.append(fwd(m, x_feat[s:s+bs], x_raw[s:s+bs], x_perp[s:s+bs], rp[s:s+bs]))
        return torch.cat(outs)

    base = build(seed=11, use_fixed_regime_state=False)
    d_base = maxabs(preds_at(base, 64), preds_at(base, 8))
    fixed = build(seed=11, use_fixed_regime_state=True)
    # fit is not required for batch-invariance (fixed extractor uses no batch
    # stats even unfitted), but the fitted path is exercised in T3.
    d_fixed = maxabs(preds_at(fixed, 64), preds_at(fixed, 8))
    d_fixed_1 = maxabs(preds_at(fixed, 64), preds_at(fixed, 1))  # bs=1 = fully per-sample
    # OLD extractor batch-z-scores => ALGORITHMIC batch-dependence (large).
    # NEW fixed extractor uses no batch stats; any residual is pure float32
    # conv/matmul reduction-order noise (~1e-7, ~machine-eps), NOT dependence.
    FLOAT_TOL = 1e-6
    old_broken = d_base > 1e-5
    new_ok = d_fixed < FLOAT_TOL and d_fixed_1 < FLOAT_TOL
    print(f"[T2] batch-invariance: OLD max|Δ(bs64,bs8)|={d_base:.3e} (algorithmic, broken={old_broken}); "
          f"NEW max|Δ(bs64,bs8)|={d_fixed:.3e}  NEW max|Δ(bs64,bs1)|={d_fixed_1:.3e} "
          f"(< {FLOAT_TOL:.0e} float32 tol => invariant={new_ok})")
    print(f"     OLD/NEW ratio = {d_base / max(d_fixed, 1e-12):.0f}x")
    ok = old_broken and new_ok
    print(f"     -> {'PASS' if ok else 'FAIL'} (old bug reproduced AND fix invariant to float32)")
    return ok


class _SynthDS:
    """Minimal DualLOBDataset-shaped dataset for exercising fit()."""
    def __init__(self, n=4000, d_prior=24, seed=2):
        g = torch.Generator().manual_seed(seed)
        # inject a regime-level signal in feat0 so descriptors have real spread
        self.x = torch.randn(n, L, N_FEAT, generator=g)
        scale = (1.0 + 3.0 * torch.rand(n, 1, generator=g))  # per-window vol level
        self.x[:, :, 0] *= scale
        self.xr = torch.randn(n, L, N_LEV, 4, generator=g)
        self.xp = torch.randn(n, L, N_LEV, 4, generator=g)
        self.rp = torch.randn(n, d_prior, generator=g) * 2.0 + 1.0
        self.y = torch.randn(n, generator=g)
        self.m = torch.ones(n)
    def __len__(self):
        return self.x.shape[0]
    def __getitem__(self, i):
        return (self.x[i], self.xr[i], self.rp[i], self.y[i], self.m[i], self.xp[i])


def test_fit_stats():
    """T3: fit_regime_state_stats populates finite buffers and stays batch-invariant."""
    m = build(seed=13, d_prior=24, use_fixed_regime_state=True, use_state_prior=True,
              use_output_gain=True)
    ds = _SynthDS(n=4000, d_prior=24)
    m.fit_regime_state_stats(ds, n_sample=2000, batch=512, verbose=False)
    fitted = float(m.rs_fitted.item()) == 1.0
    finite = (torch.isfinite(m.rs_desc_mean).all() and torch.isfinite(m.rs_desc_std).all()
              and (m.rs_desc_std > 0).all() and torch.isfinite(m.rs_prior_mean).all()
              and (m.rs_prior_std > 0).all())
    # batch-invariance still holds after fit
    xf, xr, xp, rp = make_inputs(48, d_prior=24)

    def preds_at(bs):
        outs = []
        for s in range(0, 48, bs):
            outs.append(fwd(m, xf[s:s+bs], xr[s:s+bs], xp[s:s+bs], rp[s:s+bs]))
        return torch.cat(outs)
    d = maxabs(preds_at(48), preds_at(6))
    ok = fitted and bool(finite) and d < 1e-6  # float32 reduction-order tol
    print(f"[T3] fit_regime_state_stats: fitted={fitted} finite={bool(finite)} "
          f"post-fit batch-inv max|Δ|={d:.3e} (<1e-6) -> {'PASS' if ok else 'FAIL'}")
    if ok:
        print(f"     desc_mean={[round(v,3) for v in m.rs_desc_mean.tolist()]}")
        print(f"     desc_std ={[round(v,3) for v in m.rs_desc_std.tolist()]}")
    return ok


RANK_SKIP = [3, 10, 11, 12, 13, 15, 16, 19, 20, 21, 22, 23, 26, 27, 28, 29, 30, 31,
             32, 33, 34, 35, 49, 50, 51, 52, 57, 70, 71, 72, 75, 81, 82, 83]


def test_revin_skip():
    """T4 (0C rank-norm arm): RevIN per-channel bypass.
    (a) BIT-IDENTITY empty-mask: revin_skip_idx None == baseline exactly.
    (b) feature works: a non-empty skip changes the output.
    (c) BATCH-INVARIANCE with mask active: preds(bs=512)==preds(bs=32) (per-element combine)."""
    x = make_inputs(48, d_prior=6)
    m_base = build(seed=21)                                   # revin_skip_idx None (baseline)
    m_skip = build(seed=21, revin_skip_idx=RANK_SKIP)          # same seed -> same weights
    q_base = fwd(m_base, *x)
    q_skip = fwd(m_skip, *x)
    d_change = maxabs(q_base, q_skip)                          # mask must change output
    m_skip._revin_skip_idx = None                             # disable -> must equal baseline
    q_off = fwd(m_skip, *x)
    d_ident = maxabs(q_base, q_off)
    # batch-invariance with mask active — use the D1-fixed model so the ONLY
    # possible batch-dependence source is the revin-skip combine (the old batch-z
    # extractor is off under use_fixed_regime_state=True). Confirms the mask does
    # not reintroduce the batch-dependence class already fixed.
    m_bi = build(seed=23, use_fixed_regime_state=True, revin_skip_idx=RANK_SKIP)
    xf, xr, xp, rp = make_inputs(64, d_prior=6, seed=9)

    def preds_at(bs):
        outs = []
        for s in range(0, 64, bs):
            outs.append(fwd(m_bi, xf[s:s+bs], xr[s:s+bs], xp[s:s+bs], rp[s:s+bs]))
        return torch.cat(outs)
    d_bi = maxabs(preds_at(64), preds_at(8))
    ok = (d_ident == 0.0) and (d_change > 1e-6) and (d_bi < 1e-6)
    print(f"[T4] revin-skip: bit-identity(None==base) max|Δ|={d_ident:.3e} (==0); "
          f"mask-changes-output max|Δ|={d_change:.3e} (>0); "
          f"batch-inv max|Δ|={d_bi:.3e} (<1e-6) -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    results = {
        "T1a output_gain no-op": test_output_gain_noop(),
        "T1b fixed FiLM identity": test_fixed_film_identity(),
        "T1c state columns no-op": test_state_prior_noop(),
        "T1d Run1 non-regime==baseline": test_run1_vs_baseline_nonregime(),
        "T2 batch-invariance": test_batch_invariance(),
        "T3 fit stats": test_fit_stats(),
        "T4 revin-skip (rank arm)": test_revin_skip(),
    }
    print("\n===== SUMMARY =====")
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    assert all(results.values()), "SOME TESTS FAILED"
    print("\nALL TESTS PASSED")
