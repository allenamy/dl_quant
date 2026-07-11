"""Engine A leaderboard scorer — one backbone arm through the pre-registered 5-column read.

Scores each of the K=6 orthogonal heads (+ per-fold-best + 6-head equal-risk ensemble) on the wide
panel, vs YR (the [funding+zoo]-residual target → IC(pred,YR) IS the incremental-over-book metric):
  (a) INCREMENTAL rank-IC (pooled) + null-z (re-derived N≈110: null-mean 0.0001, std 0.00184)
  (b) PERSISTENCE (weight-autocorr) — the tradability KPI + fill-window proxy at the 4h horizon
  (c) FILL-WINDOW — 4h target ≫ 5min fill window → passes by design; persistence(b) is the fast-signal
      flag (a fast sub-signal would show low autocorr). Full 1s entry-lag decay only if (b) looks fast.
  (d) NET-COST — L/S net-Sh on YR (incremental PnL) at prop cost {0.2,0.5,1.0} bps, 4h rebalance
  (e) ★ gate-d WALK-FORWARD — per-fold IC(pred,YR) (the folds ARE expanding walk-forward) + sign-consistency

Pre-reg bars (docs/2026-07-11_EngineA_leaderboard_prereg.md): z≥2.5 (IC≥0.0047) per-arm / FWER z≥3.0
(IC≥0.0056) winner; gate-d ΔIC≥+0.003 sign-consistent; persistence healthy; net-cost>0 at prop cost.

Usage: PYTHONPATH=. python multi_asset/eval/wideA_score.py --tag wideA_conformer_ref
"""
from __future__ import annotations
import sys, os.path as op, glob, argparse, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from scipy.stats import rankdata
from multi_asset.eval.portfolio_scorecard import book_stats
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
NULL_MEAN, NULL_STD = 0.00010, 0.00184   # re-derived N≈110 (wide_null_calib.py)
COSTS = [0.2, 0.5, 1.0]
H4 = 4 * 3600
MIN = 8


def _ric(f, y):
    rf = rankdata(f); ry = rankdata(y); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return float((rf * ry).sum() / d) if d > 1e-12 else np.nan


def perts_ic(F, Y, M, rows=None):
    T = F.shape[0]; ics = []; idxs = range(T) if rows is None else rows
    for t in idxs:
        v = M[t] & np.isfinite(F[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN and np.std(F[t, v]) > 1e-12 and np.std(Y[t, v]) > 1e-12:
            ic = _ric(F[t, v], Y[t, v])
            if np.isfinite(ic):
                ics.append(ic)
    return np.array(ics)


def persistence(F, Y, M):
    S = F.shape[1]; W = []
    for t in range(F.shape[0]):
        v = M[t] & np.isfinite(F[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN and np.std(F[t, v]) > 1e-12:
            w = np.zeros(S); idx = np.where(v)[0]; w[idx] = rank_weights(F[t, idx]); W.append(w)
    W = np.array(W); a, b = W[:-1].ravel(), W[1:].ravel(); m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="wideA_conformer_ref"); a = ap.parse_args()
    d = op.join(E, a.tag); ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    YR, Yraw = ref["YR"].astype(np.float64), ref["Yraw"].astype(np.float64)
    M = (ref["member"].astype(bool) & ref["CL"].astype(bool))
    ts, day = ref["ts"].astype(np.int64), ref["day"].astype(np.int64)
    T, N, K = *YR.shape, 6
    heads = [np.full((T, N), np.nan) for _ in range(K)]
    fold_rows = []
    for f in sorted(glob.glob(op.join(d, "fold_*_head_scores.npz"))):
        z = np.load(f); tr = z["te_rows"]; fold_rows.append(tr)
        for k in range(K):
            heads[k][tr] = z["scores"][tr, :, k]
    ens = np.nanmean(np.stack(heads), axis=0)                     # 6-head equal-risk ensemble

    print(f"arm={a.tag} | T={T} N={N} | usable-grid frac={M.mean():.3f} | folds={len(fold_rows)} (te sizes {[len(r) for r in fold_rows]})")
    print(f"\n{'factor':>10} | {'IC(YR)':>8} {'null-z':>7} | {'per-fold IC (gate-d)':>26} {'sign-cons':>9} | {'persist':>7} | {'net-Sh@0.2/0.5/1.0':>20} | {'IC(raw)':>8}")
    cand = [(f"head_{k}", heads[k]) for k in range(K)] + [("ENSEMBLE", ens)]
    best = None
    for nm, F in cand:
        ic = perts_ic(F, YR, M); pooled = ic.mean() if len(ic) else np.nan
        z = (pooled - NULL_MEAN) / NULL_STD
        pf = [perts_ic(F, YR, M, rows=r).mean() for r in fold_rows]
        sign = all(np.sign(x) == np.sign(pf[0]) for x in pf if np.isfinite(x)) and np.isfinite(pf[0])
        per = persistence(F, YR, M)
        ns = []
        for c in COSTS:
            st = book_stats(F, YR, M, ts, day, H4, cost_bps=c); ns.append(st["net_sh_grid"].get(c, st["net_sh_c2"]))
        icr = perts_ic(F, Yraw, M).mean()
        print(f"{nm:>10} | {pooled:>+8.4f} {z:>7.1f} | {str([round(x,4) for x in pf]):>26} {str(sign):>9} | "
              f"{per:>+7.3f} | {ns[0]:>+6.2f}/{ns[1]:>+5.2f}/{ns[2]:>+5.2f} | {icr:>+8.4f}")
        if best is None or (np.isfinite(pooled) and pooled > best[1]):
            best = (nm, pooled, z, pf, sign, per)
    print("\n★ CONFORMER-REF BAR (the incumbent every paradigm must beat incrementally):")
    nm, pooled, z, pf, sign, per = best
    print(f"  best head = {nm}: incremental IC {pooled:+.4f} (null-z {z:.1f}, FWER-bar IC 0.0056), "
          f"gate-d per-fold {[round(x,4) for x in pf]} sign-consistent={sign}, persistence {per:+.3f}")
    print(f"  pre-reg gates: null-z≥2.5 {'PASS' if z>=2.5 else 'FAIL'} | FWER-z≥3.0 {'PASS' if z>=3.0 else 'FAIL'} | "
          f"gate-d≥+0.003+sign {'PASS' if (np.nanmean(pf)>=0.003 and sign) else 'FAIL'} | "
          f"fill-window(4h≫5min, persist {per:+.2f}) {'PASS' if per>0.2 else 'CHECK-fast'}")
    print("DONE_WIDEA_SCORE")


if __name__ == "__main__":
    main()
