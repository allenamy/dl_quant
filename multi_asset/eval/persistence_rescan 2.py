"""B — PERSISTENCE re-scan of existing DL artifacts (the new KPI applied retroactively, no GPU).

Weight-autocorr (persistence) + rank-IC + net-Sh@5 for: the 3 M0 seeds (42/43/44), the ★ 3-seed
ENSEMBLE (averaging cancels UNCORRELATED fast components → may be intrinsically more persistent than
any single seed = a no-retrain M0 rescue lead), and the 5 stage-2b heads (esp head_2, the gate-b
near-miss watch item — if it's SLOW its marginal fail deserves a second look).

All on the 487-window (2024-06..2025-09, the 2025-persistent regime — the artifacts only exist here).
NOTE: this window is where M0 is ALREADY persistent (~0.43); a materially-higher persistence here is
suggestive that the artifact would also be more persistent on the 2023/24 defect regime — but the
DECISIVE test (net-cost on 2023/24) needs a fullhist rebuild (flagged, not run). Grid = fund_ema_h3600
>=3600 CL. Any 'rescue' claim → full net-cost EMA-hold per-year (pre-registered).

Usage: PYTHONPATH=. python multi_asset/eval/persistence_rescan.py
"""
from __future__ import annotations
import sys, os.path as op, glob, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from multi_asset.eval.factor_pipeline import load_panel
from multi_asset.eval.factor_scorer import _perts_ic
from multi_asset.eval.portfolio_scorecard import book_stats, MIN_ASSETS
from multi_asset.eval.backtest_longshort import rank_weights

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"


def _persist(sig, Y, CL):
    rows = []
    for t in range(Y.shape[0]):
        v = CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t])
        if v.sum() >= MIN_ASSETS and np.std(sig[t, v]) > 1e-12:
            rows.append(t)
    S = Y.shape[1]; W = np.zeros((len(rows), S))
    for i, t in enumerate(rows):
        v = np.where(CL[t] & np.isfinite(sig[t]) & np.isfinite(Y[t]))[0]; W[i, v] = rank_weights(sig[t, v])
    a, b = W[:-1].ravel(), W[1:].ravel(); m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 10 else np.nan


def _align(grid_ts, pred, pred_ts):
    if pred.shape[0] == len(grid_ts) and np.array_equal(pred_ts, grid_ts):
        return pred
    out = np.full((len(grid_ts), pred.shape[1]), np.nan)
    common, ig, io = np.intersect1d(grid_ts, pred_ts, return_indices=True)
    out[ig] = pred[io]; return out


def _stitch_heads():
    """stitch stage2b scores[T,S,5] by te_rows across folds -> list of 5 (T,S) head preds + ts."""
    fs = sorted(glob.glob(op.join(E, "stage2b_kheads", "fold_*_head_scores.npz")))
    z0 = np.load(fs[0]); T, S, K = z0["scores"].shape
    ref = np.load(op.join(E, "stage2b_kheads", "panel_ref.npz"))
    heads = [np.full((T, S), np.nan) for _ in range(K)]
    for f in fs:
        z = np.load(f); tr = z["te_rows"]
        for k in range(K):
            heads[k][tr] = z["scores"][tr, :, k]
    return heads, ref["ts"].astype(np.int64)


def main():
    G = load_panel("fund_ema_h3600", E)
    Y, CL, ts, day = G["Y"], G["CL"].astype(bool), G["ts"].astype(np.int64), G["day"].astype(np.int64)

    seeds = {}
    for tag, nm in [("fund_resid_h3600", "M0_s42"), ("fund_resid_h3600_s43", "M0_s43"), ("fund_resid_h3600_s44", "M0_s44")]:
        P = load_panel(tag, E); seeds[nm] = _align(ts, P["pred"], P["ts"].astype(np.int64))
    ens = np.nanmean(np.stack([seeds["M0_s42"], seeds["M0_s43"], seeds["M0_s44"]]), axis=0)  # 3-seed ensemble

    heads, hts = _stitch_heads()
    arts = list(seeds.items()) + [("M0_ENSEMBLE(3seed)", ens)] + [(f"head_{k}", _align(ts, heads[k], hts)) for k in range(len(heads))]

    print(f"grid fund_ema_h3600: T={len(ts)} CL-frac={CL.mean():.3f}  (487-window = 2025-persistent regime)")
    print(f"\n{'artifact':22s} | rank-IC  | persistence(wt-ac) | net-Sh@5  BE   turn")
    base = None
    rows = {}
    for nm, sig in arts:
        ic, _ = _perts_ic(sig, Y, CL)
        if len(ic) == 0:
            print(f"{nm:22s} | (no usable rows)"); continue
        pz = _persist(sig, Y, CL); st = book_stats(sig, Y, CL, ts, day, 3600)
        rows[nm] = dict(ic=ic.mean(), persist=pz, nsh5=st["net_sh_grid"][5.0], be=st["be"])
        print(f"{nm:22s} | {ic.mean():+.4f} | {pz:+.3f}             | {st['net_sh_grid'][5.0]}  {st['be']:.1f}  {st['turnover']:.3f}")
        if nm == "M0_s42":
            base = pz
    print(f"\n★ M0_s42 persistence baseline = {base:+.3f}. Flag artifacts materially above it:")
    for nm, r in rows.items():
        if nm != "M0_s42" and np.isfinite(r["persist"]) and r["persist"] > base + 0.03:
            print(f"  {nm}: persistence {r['persist']:+.3f} (+{r['persist']-base:.3f} vs M0_s42) — RESCUE LEAD "
                  f"→ needs fullhist net-cost EMA-hold per-year confirm")
    print("DONE_PERSIST_RESCAN")


if __name__ == "__main__":
    main()
