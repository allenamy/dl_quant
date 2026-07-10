"""FORMAL verdict for BATCH-1 L1 (w_rank 0.1->0.3 loss variant of M0) — replacement DL leg?

L1 is a LOSS variant of M0 (same arch, heavier rank-loss), 487-day window. So the question is
REPLACEMENT (is L1 a better DL leg than M0?), not additive. Reports:
  (1) HEAD-TO-HEAD L1 vs M0: rank-IC, IC t-stat, monotonicity (10-bin), persistence (weight-autocorr),
      net-Sh@5 (deployable). #15 signature = rank-IC held but monotonicity/calibration decays.
  (2) FACTORY additive check: run_factory(L1, B=[funding, M0]) — is L1 additive over the current book?
Grid = fund_ema_h3600 >=3600 CL (aligns L1/M0 preds by ts). Baselines: funding=fund_ema_h3600,
M0=fund_resid_h3600, L1=L1_wrank03.

Usage: PYTHONPATH=. python multi_asset/eval/l1_verdict.py
"""
from __future__ import annotations
import sys, os.path as op, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel, run_factory
from multi_asset.eval.factor_scorer import _perts_ic
from multi_asset.eval.portfolio_scorecard import book_stats, MIN_ASSETS
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"


def _align(grid_ts, other):
    ots = other["ts"].astype(np.int64)
    if np.array_equal(ots, grid_ts):
        return other["pred"]
    common, ig, io = np.intersect1d(grid_ts, ots, return_indices=True)
    p = np.full((len(grid_ts), other["pred"].shape[1]), np.nan)
    p[ig] = other["pred"][io]
    return p


def _persist(sig, Y, CL):
    rows = [t for t in range(Y.shape[0]) if (CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])).sum() >= MIN_ASSETS
            and np.std(sig[t, CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])]) > 1e-12]
    S = Y.shape[1]; W = np.zeros((len(rows), S))
    for i, t in enumerate(rows):
        v = np.where(CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t]))[0]; W[i, v] = rank_weights(sig[t, v])
    a, b = W[:-1].ravel(), W[1:].ravel(); m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def _mono(sig, Y, CL, nb=10):
    fs, ys = [], []
    for t in range(Y.shape[0]):
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN_ASSETS:
            fs.append(sig[t, v]); ys.append(Y[t, v])
    f = np.concatenate(fs); y = np.concatenate(ys)
    q = np.quantile(f, np.linspace(0, 1, nb + 1)); bm = []
    for i in range(nb):
        m = (f >= q[i]) & (f <= q[i + 1] if i == nb - 1 else f < q[i + 1])
        bm.append(y[m].mean() if m.sum() > 0 else np.nan)
    bm = np.array(bm); ok = np.isfinite(bm)
    from scipy.stats import rankdata
    r1 = rankdata(np.arange(nb)[ok]); r2 = rankdata(bm[ok])
    return float(np.corrcoef(r1, r2)[0, 1]) if ok.sum() > 2 else np.nan


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="L1_wrank03"); ap.add_argument("--label", default=None)
    a = ap.parse_args(); lab = a.label or a.tag
    G = load_panel("fund_ema_h3600", E)
    Y, CL, ts, day = G["Y"], G["CL"].astype(bool), G["ts"].astype(np.int64), G["day"].astype(np.int64)
    funding = G["pred"]
    M0 = _align(ts, load_panel("fund_resid_h3600", E))
    CAND = _align(ts, load_panel(a.tag, E))
    print(f"grid fund_ema_h3600: T={len(ts)} CL-frac={CL.mean():.3f} | candidate tag={a.tag}")

    print(f"\n=== HEAD-TO-HEAD (replacement: is {lab} a better DL leg than M0?) ===")
    print(f"{'factor':8s} | rank-IC  IC-tstat | mono(10bin) | persist(wt-ac) | net-Sh@5 BE turn")
    for nm, sig in [("M0", M0), (lab, CAND)]:
        ic, _ = _perts_ic(sig, Y, CL); tstat = ic.mean() / (ic.std() / np.sqrt(len(ic)) + 1e-12)
        st = book_stats(sig, Y, CL, ts, day, 3600)
        print(f"{nm:8s} | {ic.mean():+.4f}  {tstat:6.1f}   | {_mono(sig, Y, CL):+.3f}      | "
              f"{_persist(sig, Y, CL):+.3f}         | {st['net_sh_grid'][5.0]}  {st['be']:.1f}  {st['turnover']:.3f}")

    print(f"\n=== FACTORY additive check: {lab} vs book [funding, M0] ===")
    r = run_factory(CAND, [funding, M0], Y, CL, ts, day, 3600, label=lab,
                    z_gate=2.5, base_names=["funding", "M0"])
    p = r["passes"]
    print(f"  gate_a standalone null-z = {r['gate_a_nullz']['z']} (>=2.5? {p['a']})")
    print(f"  gate_b incremental-over-book null-z = {r['gate_b_nullz']['z']} (>=2.5? {p['b']})")
    print(f"  gate_c max|corr| vs book = {r['gate_c_corr_vs_B']} (<0.7? {p['c']})  per-factor {r['gate_c_corr_each']}")
    print(f"  gate_d walk-forward ΔIC = {r['gate_d_ridge'].get('dIC')} sign-consistent={r['gate_d_ridge'].get('sign_consistent')} ({p['d']})")
    print(f"  gate_e net-cost Δbreak-even = {r['gate_e_netcost'].get('d_be')} ({p['e']})")
    print(f"  ACCEPT (additive over book) = {r['ACCEPT']}")
    print("DONE_L1_VERDICT")


if __name__ == "__main__":
    main()
