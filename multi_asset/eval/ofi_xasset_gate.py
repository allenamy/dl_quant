"""BATCH-0 B0b-d cross-asset Ridge pre-gates (lagged cross-asset flow / slow context /
market-state interactions).

B0b (highest interest — Cont's one horizon-tolerant cross-sectional flow lever): each asset
sees the LEADERS' (BTC/ETH) lagged aggressive-OFI + lagged returns (seesaw: large-cap lagged
return negatively predicts small-cap). Strict >=t lag (>=1 pred-step=180s) + shuffle-future
null on the leader series (lead-lag leak surface).
B0c: linear 4-8h slow-context descriptors — trailing mean ret / rv (80/160 pred-steps) +
cross-sectional rank of trailing return, cross-day continuous on the common grid.
B0d: market-state g_t = [BTC ret_600s, cap-wtd mean ret, xsec dispersion, market rv] as
Ridge INTERACTION terms (g_t x asset ret_600s / obi_L1) — g_t alone is constant across the
cross-section so only the interactions carry cross-sectional signal (pre-gate for Batch-2 FiLM).

Reuses the own-book gate's Ridge walk-forward (expanding monthly folds, per-asset clean Pearson,
per-fold sign, shuffle-null). Gate: ΔP>=+0.005, sign-consistent, z>=3.
Run: PYTHONPATH=. python multi_asset/eval/ofi_xasset_gate.py
"""
from __future__ import annotations

import os.path as p

import numpy as np

from multi_asset.eval.ofi_ridge_gate import (
    BASE, OFI, SYMBOLS, eval_family, build_folds, ALPHA)

RET600 = 4          # baseline feature index: ret_600s
RV300 = 25          # rv_300s
OBI1 = 26           # obi_L1
LEADERS = ("bnfbtc", "bnfeth")
LAGS = (1, 2, 5, 10, 20)          # pred-steps (180s each) ~ 3/6/15/30/60 min
SLOW = (80, 160)                  # trailing pred-steps ~ 4h / 8h
AGGR_COL = None                   # aggrofi_ema300 index in ofi names (resolved at load)


def _causal_roll_mean(x, w):
    """Trailing mean over [t-w+1,t], cross-day continuous. NaN->0."""
    xf = np.where(np.isfinite(x), x, 0.0)
    cs = np.cumsum(xf); c = np.cumsum(np.isfinite(x).astype(float))
    out = cs.copy(); cnt = c.copy()
    if w < len(x):
        out[w:] = cs[w:] - cs[:-w]; cnt[w:] = c[w:] - c[:-w]
    return np.where(cnt > 0, out / np.maximum(cnt, 1), 0.0)


def _lag(x, k):
    """x shifted forward by k on the common grid: out[t]=x[t-k], out[<k]=0 (>=t causal)."""
    out = np.zeros_like(x)
    if k < len(x):
        out[k:] = x[:-k]
    return out


def load_common():
    """Per-symbol arrays aligned to the COMMON ts grid (intersection of every symbol's
    baseline AND ofi ts, so cross-asset lags/aggregates are row-aligned)."""
    import json
    onames = json.load(open(p.join(OFI, "channel_names.json")))
    aggr_idx = onames.index("aggrofi_ema300")
    loaded = {}
    common = None
    for s in SYMBOLS:
        b = np.load(p.join(BASE, f"{s}.npz"), allow_pickle=True)
        o = np.load(p.join(OFI, f"{s}.npz"), allow_pickle=True)
        loaded[s] = (b, o)
        ts_s = np.intersect1d(b["ts"].astype(np.int64), o["ts"].astype(np.int64))
        common = ts_s if common is None else np.intersect1d(common, ts_s)
    data = {}
    for s in SYMBOLS:
        b, o = loaded[s]
        tb = b["ts"].astype(np.int64); to = o["ts"].astype(np.int64)
        ib = np.searchsorted(tb, common); io = np.searchsorted(to, common)
        data[s] = dict(Xb=b["X"][ib], y=b["y"][ib], day=b["day"][ib],
                       clean=b["clean600"][ib].astype(bool),
                       aggr=o["X"][io, aggr_idx], ts=common)
    return data, common


def build_xasset_channels(data):
    """Append B0b/B0c/B0d channels to each symbol's Xo; return names."""
    S = SYMBOLS
    n = len(data[S[0]]["ts"])
    # market aggregates on the common grid
    ret_mat = np.stack([data[s]["Xb"][:, RET600] for s in S], axis=1)     # (n,14)
    rv_mat = np.stack([data[s]["Xb"][:, RV300] for s in S], axis=1)
    mkt_ret = np.nanmean(ret_mat, axis=1)                                 # cap-wt≈equal here
    mkt_disp = np.nanstd(ret_mat, axis=1)
    mkt_rv = np.nanmean(rv_mat, axis=1)
    btc_ret = data["bnfbtc"]["Xb"][:, RET600]
    gt = np.stack([btc_ret, mkt_ret, mkt_disp, mkt_rv], axis=1)           # (n,4)
    lead_aggr = {L: data[L]["aggr"] for L in LEADERS}
    lead_ret = {L: data[L]["Xb"][:, RET600] for L in LEADERS}
    names = None
    for s in S:
        cols, nm = [], []
        # B0b: leader lagged aggr-OFI + lagged return (seesaw)
        for L in LEADERS:
            for k in LAGS:
                cols.append(_lag(lead_aggr[L], k)); nm.append(f"b0b_{L[3:]}aggr_l{k}")
                cols.append(_lag(lead_ret[L], k));  nm.append(f"b0b_{L[3:]}ret_l{k}")
        # B0c: slow context (trailing ret/rv + xsec-rank of trailing ret)
        r = data[s]["Xb"][:, RET600]; v = data[s]["Xb"][:, RV300]
        for w in SLOW:
            cols.append(_causal_roll_mean(r, w)); nm.append(f"b0c_ret_tr{w}")
            cols.append(_causal_roll_mean(v, w)); nm.append(f"b0c_rv_tr{w}")
        # B0d: market-state interactions (g_t x asset ret / obi)
        a_ret = data[s]["Xb"][:, RET600]; a_obi = data[s]["Xb"][:, OBI1]
        for j in range(4):
            cols.append(gt[:, j] * a_ret); nm.append(f"b0d_gt{j}xret")
            cols.append(gt[:, j] * a_obi); nm.append(f"b0d_gt{j}xobi")
        Xo = np.stack(cols, axis=1).astype(np.float32)
        Xo = np.nan_to_num(Xo, nan=0.0, posinf=0.0, neginf=0.0)
        data[s]["Xo"] = Xo
        names = nm
    # B0c xsec-rank of trailing-4h return (needs cross-section) — append as one more col
    tr4 = np.stack([_causal_roll_mean(data[s]["Xb"][:, RET600], 80) for s in S], axis=1)  # (n,14)
    rank = np.argsort(np.argsort(tr4, axis=1), axis=1).astype(np.float32) / (len(S) - 1) - 0.5
    for si, s in enumerate(S):
        data[s]["Xo"] = np.concatenate([data[s]["Xo"], rank[:, si:si+1]], axis=1)
    names = names + ["b0c_xsecrank_tr4h"]
    return names


def _fam(names):
    fam = {"b0b": [], "b0c": [], "b0d": []}
    for i, nm in enumerate(names):
        fam[nm[:3]].append(i)
    return {k: np.array(v) for k, v in fam.items()}


def main():
    data, common = load_common()
    names = build_xasset_channels(data)
    fam = _fam(names)
    folds = build_folds(data)
    print(f"[xgate] common ts={len(common)} folds={len(folds)} | "
          f"b0b={len(fam['b0b'])} b0c={len(fam['b0c'])} b0d={len(fam['b0d'])}", flush=True)
    base = eval_family(data, names, None, "baseline", folds)
    print(f"BASELINE cleanP per-fold {np.round(base,4)} mean={np.nanmean(base):+.4f}\n")
    combos = {"b0b": fam["b0b"], "b0c": fam["b0c"], "b0d": fam["b0d"],
              "all_x": np.concatenate([fam["b0b"], fam["b0c"], fam["b0d"]])}
    rows = []
    for lab, cols in combos.items():
        pf = eval_family(data, names, cols, lab, folds)
        dP = pf - base
        sg = np.sign(dP[np.isfinite(dP)])
        rows.append((lab, np.nanmean(pf), np.nanmean(dP),
                     bool(np.all(sg == sg[0])) if len(sg) else False, np.round(dP, 4)))
    # shuffle-future null on b0b (lead-lag surface): permute leader series in time.
    # The baseline is INVARIANT to the leader permutation (baseline uses only Xb, not
    # aggr), so reuse `base` instead of refitting it 20x — the big speedup.
    rng = np.random.default_rng(0); null = []
    for _ in range(20):
        dN = {s: dict(data[s]) for s in SYMBOLS}
        perm = rng.permutation(len(common))
        for s in SYMBOLS:
            dN[s] = dict(data[s]); dN[s]["aggr"] = data[s]["aggr"][perm]
        nm2 = build_xasset_channels(dN)
        pf = eval_family(dN, nm2, _fam(nm2)["b0b"], "null", folds)
        null.append(np.nanmean(pf - base))
    null = np.array(null)
    print("=== ΔP over baseline (cross-sectional clean Pearson) ===")
    print(f"{'family':8s} {'meanP':>8s} {'ΔP':>8s} {'sign':>6s}  per-fold ΔP")
    for lab, mp, dp, cons, pfd in rows:
        print(f"{lab:8s} {mp:+8.4f} {dp:+8.4f} {str(cons):>6s}  {pfd}")
    b0b_dp = [r[2] for r in rows if r[0] == "b0b"][0]
    z = (b0b_dp - null.mean()) / (null.std() + 1e-9)
    print(f"\nb0b shuffle-future null ΔP mean={null.mean():+.4f} std={null.std():.4f} -> b0b z={z:+.2f}")
    for lab, mp, dp, cons, pfd in rows:
        verdict = "PASS" if (dp >= 0.005 and cons and (z >= 3 if lab == "b0b" else True)) else "FAIL"
        print(f"GATE {lab}: {verdict} (ΔP {dp:+.4f}, sign {cons})")


if __name__ == "__main__":
    main()
