"""QIM q50 deep-audit — is the counterintuitive +0.0703 (2x everything) real DYNAMIC alpha or artifact?

QIM = 2-head panel (0=implied-mean, 1=q50 pinball point). Its own hypothesis (imean>q50) is FALSIFIED
(q50 wins every fold). BUT q50's naive resid rank-IC ~+0.070 is ~2x the K-head arms (Conformer/xattn
+0.031) — 0B's hypothesis: the K-head lam_orth=1.0 penalty dilutes signal; QIM q50 is a single
unconstrained head. SKEPTICAL because pinball-q50 >> LambdaRankIC on rank-IC is counterintuitive.
Battery: naive IC, ★ shuffle-future DYNAMIC/STATIC split (dynamic = real timing; static = tilt),
per-fold gate-d, persistence, net-cost at realistic wide-book cost, funding-echo.

Usage: PYTHONPATH=. python multi_asset/eval/qim_audit.py --tag wideA_qim --head 1
"""
from __future__ import annotations
import sys, os.path as op, glob, argparse, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from scipy.stats import rankdata
from multi_asset.eval.portfolio_scorecard import book_stats
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
MIN = 8; COSTS = [2.3, 5.0, 9.5]


def _ric(f, y):
    rf = rankdata(f); ry = rankdata(y); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return float((rf * ry).sum() / d) if d > 1e-12 else np.nan


def perts_ic(F, Y, M, rows=None, ymap=None):
    ics = []
    for t in (range(F.shape[0]) if rows is None else rows):
        yt = Y[t] if ymap is None else Y[ymap[t]]
        v = M[t] & np.isfinite(F[t]) & np.isfinite(yt)
        if v.sum() >= MIN and np.std(F[t, v]) > 1e-12 and np.std(yt[v]) > 1e-12:
            ic = _ric(F[t, v], yt[v])
            if np.isfinite(ic):
                ics.append(ic)
    return np.array(ics)


def persist(F, Y, M):
    S = F.shape[1]; W = []
    for t in range(F.shape[0]):
        v = M[t] & np.isfinite(F[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN and np.std(F[t, v]) > 1e-12:
            w = np.zeros(S); idx = np.where(v)[0]; w[idx] = rank_weights(F[t, idx]); W.append(w)
    W = np.array(W); a, b = W[:-1].ravel(), W[1:].ravel(); m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="wideA_qim"); ap.add_argument("--head", type=int, default=1)
    a = ap.parse_args(); d = op.join(E, a.tag)
    ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    YR, Yraw = ref["YR"].astype(np.float64), ref["Yraw"].astype(np.float64)
    M = (ref["member"].astype(bool) & ref["CL"].astype(bool)); ts, day = ref["ts"].astype(np.int64), ref["day"].astype(np.int64)
    funding = ref["funding"].astype(np.float64); T, N = YR.shape
    z0 = np.load(op.join(d, "fold_0_head_scores.npz")); nheads = z0["scores"].shape[2]
    F = np.full((T, N), np.nan); fold_rows = []
    for f in sorted(glob.glob(op.join(d, "fold_*_head_scores.npz"))):
        z = np.load(f); tr = z["te_rows"]; fold_rows.append(tr); F[tr] = z["scores"][tr, :, a.head]
    print(f"tag={a.tag} head={a.head}/{nheads} (0=imean,1=q50) | T={T} folds={len(fold_rows)}")

    naive = perts_ic(F, YR, M).mean(); raw = perts_ic(F, Yraw, M).mean()
    pf = [perts_ic(F, YR, M, rows=r).mean() for r in fold_rows]
    per = persist(F, YR, M)
    # shuffle-future dynamic/static
    vr = np.array([t for t in range(T) if (M[t] & np.isfinite(F[t]) & np.isfinite(YR[t])).sum() >= MIN])
    rng = np.random.default_rng(0); sh = []
    for _ in range(30):
        pm = vr.copy(); rng.shuffle(pm); rmap = np.arange(T); rmap[vr] = pm
        sh.append(perts_ic(F, YR, M, rows=vr, ymap=rmap).mean())
    static = float(np.mean(sh)); dyn = naive - static; zdyn = (naive - static) / (np.std(sh) + 1e-12)
    ns = [book_stats(F, YR, M, ts, day, 4 * 3600, cost_bps=c)["net_sh_c2"] for c in COSTS]
    fe = np.nanmean([_ric(F[t, M[t] & np.isfinite(F[t]) & np.isfinite(funding[t])],
                          funding[t, M[t] & np.isfinite(F[t]) & np.isfinite(funding[t])])
                     for t in vr if (M[t] & np.isfinite(F[t]) & np.isfinite(funding[t])).sum() >= MIN])

    print(f"\n  naive incremental IC(YR) = {naive:+.4f}   (raw-Y IC {raw:+.4f})")
    print(f"  ★ DYNAMIC {dyn:+.4f} (shuffle-future z {zdyn:.1f}) + STATIC-tilt {static:+.4f}")
    print(f"  gate-d per-fold {[round(x,4) for x in pf]}  persistence {per:+.3f}")
    print(f"  net-Sh @2.3/5.0/9.5bps(wide) = {ns[0]:+.2f}/{ns[1]:+.2f}/{ns[2]:+.2f}   funding-echo {fe:+.3f}")
    print(f"\n★ VERDICT: DYNAMIC {dyn:+.4f} vs xattn bar +0.0313 -> "
          f"{'PARADIGM SHIFT (pinball head > K-head orthogonality)' if dyn > 0.04 else 'strong but check' if dyn > 0.031 else 'STATIC-INFLATED (naive overstated the timing)' if static > 0.02 else 'below leader'}")
    print("DONE_QIM_AUDIT")


if __name__ == "__main__":
    main()
