"""Stable local trend (PREREG_fea89_stable_trend §2): signed R² of the LOCAL cumulative log price vs LOCAL time inside [E-w+1, E]; no global cumsums.
Semantics identical to pod_f8_build_ext.py L204-L216 except numerics: post-listing mask pm, missing bars = 0 return, n<w//2 or vp<=1e-20 -> NaN."""
import numpy as np
def stable_trend_block(lr, pm, hi, w, chunk_syms=16):
    """lr: (TT, nc) float64 log1p(rz) (zeros where not finite); pm: (TT, nc) bool post-listing mask; hi: (nA,) int (=E+1); returns (nA, nc) float32."""
    TT, nc = lr.shape; nA = len(hi); out = np.full((nA, nc), np.nan, np.float32)
    idx = hi[:, None] - w + np.arange(w)[None, :]           # (nA, w) rows, may be < 0 at the start of the axis
    valid = idx >= 0; idxc = np.clip(idx, 0, TT - 1)
    for c0 in range(0, nc, chunk_syms):
        cs_ = slice(c0, min(c0 + chunk_syms, nc)); L = lr[:, cs_]; P = pm[:, cs_]
        y = np.cumsum(L[idxc, :], axis=1)                    # (nA, w, k) local cumulative log price (window-based, no global offset)
        m = P[idxc, :] & valid[:, :, None]                   # rows counted: post-listing & inside axis
        n = m.sum(1).astype(np.float64)                      # (nA, k)
        x = np.arange(w, dtype=np.float64)[None, :, None]
        mf = m.astype(np.float64); xm = (x * mf).sum(1) / np.maximum(n, 1); ym = (y * mf).sum(1) / np.maximum(n, 1)
        dx = (x - xm[:, None, :]) * mf; dy = (y - ym[:, None, :]) * mf
        cov = (dx * dy).sum(1) / np.maximum(n, 1); vt = (dx * dx).sum(1) / np.maximum(n, 1); vp = (dy * dy).sum(1) / np.maximum(n, 1)
        rho = np.clip(cov / np.sqrt(np.maximum(vt * vp, 1e-30)), -1, 1); tr = np.sign(rho) * rho ** 2
        tr[(n < w // 2) | (vp <= 1e-20)] = np.nan; out[:, cs_] = tr.astype(np.float32)
    return out
def global_trend_block(lr, pm, hi, w, tidx):
    """verbatim numerics of the builder (for G1(c) agreement checks only)."""
    def cs(a): return np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(a, 0, dtype=np.float64)])
    p = np.cumsum(lr, 0); pz = np.where(pm, p, 0.0); pmf = pm.astype(np.float64); lo = np.maximum(hi - w, 0)
    CSpm = cs(pmf); CSp = cs(pz); CSp2 = cs(pz ** 2); CSt = cs(tidx[:, None] * pmf); CSt2 = cs(tidx[:, None] ** 2 * pmf); CStp = cs(tidx[:, None] * pz)
    n = CSpm[hi] - CSpm[lo]; nn = np.maximum(n, 1); Sp = CSp[hi] - CSp[lo]; Sp2 = CSp2[hi] - CSp2[lo]; St = CSt[hi] - CSt[lo]; St2 = CSt2[hi] - CSt2[lo]; Stp = CStp[hi] - CStp[lo]
    cov = Stp / nn - (St / nn) * (Sp / nn); vt = St2 / nn - (St / nn) ** 2; vp = Sp2 / nn - (Sp / nn) ** 2
    rho = np.clip(cov / np.sqrt(np.maximum(vt * vp, 1e-30)), -1, 1); tr = np.sign(rho) * rho ** 2; tr[(n < w // 2) | (vp <= 1e-20)] = np.nan
    return tr.astype(np.float32)
if __name__ == "__main__":   # G1 invariance tests: synthetic + real cache slice
    import json, time
    from scipy.stats import spearmanr
    rng = np.random.default_rng(7); TT = 30000; nc = 8; r = rng.normal(0, 0.003, (TT, nc)); fin = rng.random((TT, nc)) > 0.02; r[~fin] = np.nan
    first = np.array([0, 100, 5000, 0, 20000, 0, 0, 0]); r[:, 4][:20000] = np.nan; fin = np.isfinite(r)
    r[:, 5] = 0.0; r[:, 5][:3000] = rng.normal(0, 0.003, 3000)          # symbol 5: flat (delisted) after row 3000
    rz = np.where(fin, r, 0.0); pm = np.arange(TT)[:, None] >= np.array([int(np.argmax(np.isfinite(r[:, j]))) for j in range(nc)])[None, :]
    lr = np.log1p(rz); hi = np.arange(9000, TT, 48); res = {}
    for w in (288, 2016):
        base = stable_trend_block(lr, pm, hi, w)
        # (a) edits strictly BEFORE every window start (rows < min(hi) - w - 1): add a constant and overwrite with noise -> output bitwise unchanged
        cut = int(hi.min()) - w - 1; lr2 = lr.copy(); lr2[:cut] += 0.01; lr2[:cut // 2] = rng.normal(0, 0.01, (cut // 2, nc)); out2 = stable_trend_block(lr2, pm, hi, w); a_ok = np.array_equal(out2, base, equal_nan=True)
        # (b) flat window (symbol 5 flat after row 3000) -> NaN deterministically, on base and on the edited history
        flat = hi > 3000 + w; b_ok = bool(np.isnan(base[flat, 5]).all()) and bool(np.isnan(out2[flat, 5]).all())
        # (c) agreement with the global formula on non-flat windows
        g = global_trend_block(lr, pm, hi, w, np.arange(TT, dtype=np.float64)); ok = np.isfinite(base) & np.isfinite(g); d = np.abs(base[ok] - g[ok])
        rc = np.nanmean([spearmanr(base[i, np.isfinite(base[i]) & np.isfinite(g[i])], g[i, np.isfinite(base[i]) & np.isfinite(g[i])]).correlation for i in range(0, len(hi), 25) if (np.isfinite(base[i]) & np.isfinite(g[i])).sum() >= 5])
        # (d) determinism
        d_ok = np.array_equal(stable_trend_block(lr, pm, hi, w), base, equal_nan=True)
        fl = np.isnan(base) != np.isnan(g); fl_cols = {int(c): int(fl[:, c].sum()) for c in range(nc) if fl[:, c].any()}
        res[w] = {"edit_cut_row": cut, "a_invariant_to_history_edits": bool(a_ok), "b_flat_nan_both": b_ok, "c_maxabs_vs_global_finite": float(np.nanmax(d)) if d.size else None, "c_n_finite_compared": int(ok.sum()), "c_rankcorr_vs_global": float(rc), "c_n_nan_flips_vs_global": int(fl.sum()), "c_nan_flips_by_col": fl_cols, "c_flips_only_on_flat_symbol": bool(set(fl_cols) <= {5}), "d_deterministic": bool(d_ok)}
        print(w, json.dumps(res[w]))
    json.dump(res, open("/workspace/review_scratch/v4_gates/stable_trend_G1_synthetic.json", "w"), indent=1); print("G1_SYNTHETIC_DONE")
