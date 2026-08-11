"""Full-window equivalence report — 0C-release prerequisite (lead's finishing requirement).

Proves the three vectorizations shipped for batch_001 reproduce the slow reference at FULL-WINDOW SCALE:
  (A) null      : _maxnull_fast  vs  slow per-anchor max-null  -> quantile table (rank ties / precision)
  (B) ts ops    : ts_rank / decay_linear (my vectorization)  vs  independent .rolling().apply() ref
                  + ts_max (UNCHANGED, pandas rolling.max) shown for the 2 ts_max candidates (#2,#7)
  (C) score     : vectorized stage0 scoring _rowwise_rankcorr(_xsec_ranks(.))  vs  the original
                  per-anchor score_series() loop (surfaces rank-then-intersect vs intersect-then-rank)

The slow references here are INDEPENDENT code paths (explicit per-window .apply / per-anchor loop), not
copies of the strided-view code, so a real vectorization bug (axis/off-by-one/NaN-compare/tie) would show.
CPU, single run on the idle server after the campaign finished.
"""
import json, sys, time
import numpy as np
import pandas as pd

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P
from pipeline import _xsec_ranks, _rowwise_rankcorr, _maxnull_fast

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
EPS = dsl.EPS

CANDIDATES = [
    "neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))",
    "neg(xsec_z(ts_max(abs(ret_1h), 24)))",
    "neg(xsec_z(power(ret_24h, 3)))",
    "where(gt(xsec_z(rvol_24h), xsec_z(rvol_72h)), s2, king)",
    "where(gt(xsec_z(mom_72h), xsec_z(mom_24h)), s2, king)",
    "where(gt(xsec_z(dvol_24h), xsec_z(dvol_72h)), king, s2)",
    "neg(xsec_z(ts_max(rvol_6h, 42)))",
]


# ---------------- independent slow references (NOT the vectorized code path) ----------------
def slow_ts_rank(A, n):
    """rank of last elem in trailing full window, tie=<= (max-rank), degenerate->NaN,
    min-finite=max(2,n//2), full windows only (t>=n-1). Explicit per-window .apply()."""
    n = int(n); mp = max(2, n // 2)
    def f(w):
        if w.shape[0] < n:            # partial start window -> drop (matches out[n-1:])
            return np.nan
        last = w[-1]
        if not np.isfinite(last):
            return np.nan
        fin = w[np.isfinite(w)]
        if fin.size < mp or np.nanstd(w) <= EPS:
            return np.nan
        le = int((fin <= last).sum())
        return (le - 1) / max(fin.size - 1, 1) - 0.5
    return pd.DataFrame(A).rolling(n, min_periods=mp).apply(f, raw=True).to_numpy()


def slow_decay(A, n):
    n = int(n); mp = max(2, n // 2); w = np.arange(1, n + 1, dtype=float)
    def f(win):
        if win.shape[0] < n:
            return np.nan
        fin = np.isfinite(win)
        if fin.sum() < mp:
            return np.nan
        den = (fin * w).sum()
        return (np.where(fin, win, 0.0) * w).sum() / den if den > 1e-12 else np.nan
    return pd.DataFrame(A).rolling(n, min_periods=mp).apply(f, raw=True).to_numpy()


def slow_ts_max(A, n):
    n = int(n); mp = max(2, n // 2)
    return pd.DataFrame(A).rolling(n, min_periods=mp).max().to_numpy()


def cmp_op(name, vec_sub, ref_sub, n, ncols):
    """element-wise compare two (T,ncols) subset arrays; classify NaN-mask disagreements by t<n-1."""
    v = vec_sub; r = ref_sub
    both = np.isfinite(v) & np.isfinite(r)
    maxdiff = float(np.nanmax(np.abs(v[both] - r[both]))) if both.any() else 0.0
    dis = np.isfinite(v) ^ np.isfinite(r)               # one finite, other NaN
    T = v.shape[0]; rowidx = np.arange(T)[:, None] * np.ones((1, ncols), int)
    dis_rows = rowidx[dis]
    dis_total = int(dis.sum())
    dis_in_boundary = int((dis_rows < n - 1).sum())     # partial-window region t<n-1
    return dict(op=name, window=n, cols=ncols, n_both_finite=int(both.sum()),
                max_abs_diff=round(maxdiff, 12), nan_mask_disagreements=dis_total,
                disagreements_in_boundary_tlt_nminus1=dis_in_boundary,
                disagreements_outside_boundary=dis_total - dis_in_boundary)


# ---------------- slow max-null (independent per-anchor loop) ----------------
def slow_maxnull(facs, C, rng, null_r):
    tg = C["target"]; rows = C["rows"]
    day_of = {int(t): int(C["day"][t]) for t in rows}
    tmask = {int(t): (C["member"][t] & C["CL"][t] & np.isfinite(tg[t])) for t in rows}
    d2r = {}; [d2r.setdefault(int(C["day"][t]), int(t)) for t in rows]
    ud = np.array(sorted(d2r)); mn = []
    for _ in range(null_r):
        dm = dict(zip(ud, rng.permutation(ud))); best = -np.inf
        for factor in facs:
            ics = []
            for t in rows:
                ti = int(t); tt = d2r[dm[day_of[ti]]]
                cb = np.where(tmask[ti] & tmask[tt] & np.isfinite(factor[ti]))[0]
                if cb.size >= 8:
                    ics.append(P._ric(factor[ti, cb], tg[tt, cb]))
            if ics:
                best = max(best, float(np.nanmean(ics)))
        mn.append(best)
    return mn


def main():
    horizon = 4
    C = P.load_context(horizon=horizon, subsample=1)
    n_anchors = len(C["rows"])
    print(f"[equiv] FULL-WINDOW context: {n_anchors} anchors, panel {C['target'].shape}", flush=True)
    facs = [dsl.evaluate(dsl.parse(f), C["ctx"]) for f in CANDIDATES]
    report = dict(n_anchors=n_anchors, panel_shape=list(C["target"].shape), candidates=CANDIDATES)

    # ---------- (B) ts-op element-wise alignment ----------
    print("[equiv] (B) ts-op alignment ...", flush=True)
    ctx = C["ctx"]
    rng = np.random.default_rng(0)
    ncol = ctx["ret_1h"].shape[1]
    cols = np.sort(rng.choice(ncol, size=min(12, ncol), replace=False))
    op_rows = []
    nc = len(cols)
    # ts_rank + decay_linear on representative channels (the ops I vectorized). Vectorized runs on the
    # full panel then we slice to `cols`; the slow .apply ref runs on the col-subset only (tractable).
    for chan, n in [("mom_24h", 24), ("rvol_72h", 72), ("ret_1h", 12)]:
        A = ctx[chan]; Asub = A[:, cols]
        op_rows.append(cmp_op(f"ts_rank[{chan}]", dsl.ts_rank(A, n)[:, cols], slow_ts_rank(Asub, n), n, nc))
        op_rows.append(cmp_op(f"decay_linear[{chan}]", dsl.decay_linear(A, n)[:, cols], slow_decay(Asub, n), n, nc))
    # ts_max on the EXACT candidate inputs (#2 abs(ret_1h),24 ; #7 rvol_6h,42) — UNCHANGED code
    A2 = np.abs(ctx["ret_1h"])
    op_rows.append(cmp_op("ts_max[abs(ret_1h)]#2", dsl.ts_max(A2, 24)[:, cols], slow_ts_max(A2[:, cols], 24), 24, nc))
    A7 = ctx["rvol_6h"]
    op_rows.append(cmp_op("ts_max[rvol_6h]#7", dsl.ts_max(A7, 42)[:, cols], slow_ts_max(A7[:, cols], 42), 42, nc))
    report["B_ts_op_alignment"] = op_rows
    for r in op_rows:
        print(f"    {r['op']:28s} w={r['window']:<3d} max_abs_diff={r['max_abs_diff']:.2e} "
              f"nan_mask_dis={r['nan_mask_disagreements']} (boundary={r['disagreements_in_boundary_tlt_nminus1']}"
              f" outside={r['disagreements_outside_boundary']})", flush=True)

    # ---------- (C) score_series alignment (vectorized stage0 scoring vs original loop) ----------
    print("[equiv] (C) score_series alignment ...", flush=True)
    tr = _xsec_ranks(C["target"], C)
    day_w = C["day"][C["rows"]]
    c_rows = []
    tg, mem, CL = C["target"], C["member"], C["CL"]
    for f, fac in zip(CANDIDATES, facs):
        vec_by_row = _rowwise_rankcorr(_xsec_ranks(fac, C), tr)      # vectorized path (what stage0 used)
        vec_mean = float(np.nanmean(vec_by_row)) if np.isfinite(vec_by_row).any() else np.nan
        # original per-anchor score loop (spec ref: _ric ranks over the JOINT finite set)
        slow_full = np.full(len(C["rows"]), np.nan)
        for i, t in enumerate(C["rows"]):
            b = np.where(mem[t] & CL[t] & np.isfinite(tg[t]) & np.isfinite(fac[t]))[0]
            if b.size >= 8:
                icv = P._ric(fac[t, b], tg[t, b])
                if np.isfinite(icv):
                    slow_full[i] = icv
        slow_mean = float(np.nanmean(slow_full)) if np.isfinite(slow_full).any() else np.nan
        both = np.isfinite(vec_by_row) & np.isfinite(slow_full)
        maxdiff = float(np.nanmax(np.abs(vec_by_row[both] - slow_full[both]))) if both.any() else 0.0
        anchor_mask_dis = int((np.isfinite(vec_by_row) ^ np.isfinite(slow_full)).sum())
        c_rows.append(dict(formula=f, inc_ic_vectorized=round(vec_mean, 6),
                           inc_ic_slow_loop=round(slow_mean, 6),
                           per_anchor_max_abs_diff=round(maxdiff, 8),
                           anchor_finite_disagreements=anchor_mask_dis,
                           n_common_anchors=int(both.sum())))
        print(f"    {f[:46]:46s} vec={vec_mean:+.5f} slow={slow_mean:+.5f} "
              f"perAnchorMaxDiff={maxdiff:.2e} maskDis={anchor_mask_dis}", flush=True)
    report["C_score_series_alignment"] = c_rows

    # ---------- (A) full-window null quantiles ----------
    print(f"[equiv] (A) full-window null: {len(facs)} candidate factors x 200 draws on {n_anchors} anchors ...", flush=True)
    t0 = time.time(); fast = _maxnull_fast(facs, C, np.random.default_rng(7), 200); tf = time.time() - t0
    t0 = time.time(); slow = slow_maxnull(facs, C, np.random.default_rng(7), 200); ts = time.time() - t0
    qs = [50, 90, 95, 99]
    fq = {q: round(float(np.nanpercentile(fast, q)), 6) for q in qs}
    sq = {q: round(float(np.nanpercentile(slow, q)), 6) for q in qs}
    maxq = max(abs(fq[q] - sq[q]) for q in qs)
    rel95 = abs(fq[95] - sq[95]) / (abs(sq[95]) + 1e-9)
    report["A_null_quantiles"] = dict(n_anchors=n_anchors, null_r=200, n_factors=len(facs),
                                      fast_quantiles=fq, slow_quantiles=sq,
                                      max_abs_quantile_diff=round(maxq, 7),
                                      rel_diff_at_rc95=round(rel95, 5),
                                      fast_sec=round(tf, 1), slow_sec=round(ts, 1))
    print(f"    fast q {fq}  ({tf:.1f}s)", flush=True)
    print(f"    slow q {sq}  ({ts:.1f}s)", flush=True)
    print(f"    max_abs_quantile_diff={maxq:.2e}  rel_diff@rc95={rel95:.4f}", flush=True)

    out = MA + "/exports/eda/equiv_full_batch001_h4.json"
    json.dump(report, open(out, "w"), indent=1, default=str)
    print("[equiv] saved " + out, flush=True)


if __name__ == "__main__":
    main()
