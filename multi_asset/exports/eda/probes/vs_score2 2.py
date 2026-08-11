"""C3 STAGE 7 — does the deployed model still beat what it beat, on the signal production receives?

Contenders (established from the coronation scripts, not from memory):
  champ = wideA_lamorth0_xattn_5yr  (deployed; /tmp/vs_pred_king_{TRAIN,SERVE}.npz)
  lam0  = wideA_lamorth0_5yr        (SAME recipe minus the cross-asset attn block -> controlled A/B)
  qim   = wideA_qim_multiyear       (different head class -> reported SEPARATELY, not in the A/B)

Metric: PER-ANCHOR CROSS-SECTIONAL rank-IC of the composite vs the target, over
        base = member & CL4 & finite(target) & finite(composite).
Two targets, reported separately and never merged:
  Y4  = raw forward 4h return   -> DEPLOYMENT-relevant (this is what the book trades)
  YR4 = residual target         -> SELECTION-relevant  (this is what the coronation scored on)

Anchors are the CL4 stride-4 non-overlap grid, so per-anchor ICs are far less overlapped than the
leak-timing series was; the paired difference still gets a DAY-BLOCK bootstrap rather than a naive t.
READ-ONLY; writes only /tmp.
"""
import sys, json, os
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
FULL = MA + "/exports/wide_dl_full.npz"
z = np.load(FULL, allow_pickle=True)
member = z["MEMBER110"]; CL4 = z["CL4"]
Y4 = z["Y4"].astype(np.float64); YR4 = z["YR4"].astype(np.float64)
ts = z["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
day = np.arange(len(ts)) // 24
T, N = member.shape
RNG = np.random.default_rng(0)

SRC = {("champ", "TRAIN"): "/tmp/vs_pred_king_TRAIN.npz",
       ("champ", "SERVE"): "/tmp/vs_pred_king_SERVE.npz",
       ("lam0", "TRAIN"): "/tmp/vs2_pred_lam0_TRAIN.npz",
       ("lam0", "SERVE"): "/tmp/vs2_pred_lam0_SERVE.npz",
       ("qim", "TRAIN"): "/tmp/vs2_pred_qim_TRAIN.npz",
       ("qim", "SERVE"): "/tmp/vs2_pred_qim_SERVE.npz"}

P = {}
for k, v in SRC.items():
    if os.path.exists(v):
        P[k] = np.load(v)["pred"].astype(np.float64)
    else:
        print("MISSING", v)
print("loaded:", sorted(P.keys()), flush=True)


MIN_BASE = 5      # ★ matches coronation_xattn_5yr.py::ic_at exactly (b.size < 5 -> skip).
                  #   Using a different threshold would make my numbers non-commensurable with the
                  #   coronation's, which is the whole point of the comparison.


def ic_series(pred, targ):
    """per-anchor cross-sectional rank-IC; returns (rows, ic values)."""
    rows, out = [], []
    cand = np.where((member & CL4 & np.isfinite(targ) & np.isfinite(pred)).any(1))[0]
    for t in cand:
        b = np.where(member[t] & CL4[t] & np.isfinite(targ[t]) & np.isfinite(pred[t]))[0]
        if b.size < MIN_BASE:
            continue
        v = np.corrcoef(rankdata(pred[t, b]), rankdata(targ[t, b]))[0, 1]
        if np.isfinite(v):
            rows.append(t); out.append(v)
    return np.array(rows), np.array(out)


def dayblock_boot(rows, vals, nboot=4000):
    """day-block bootstrap mean + 95% CI (anchors inside a day move together)."""
    dd = day[rows]
    ud = np.unique(dd)
    idx = {u: np.where(dd == u)[0] for u in ud}
    bs = np.empty(nboot)
    for i in range(nboot):
        pick = RNG.choice(ud, len(ud), True)
        bs[i] = vals[np.concatenate([idx[u] for u in pick])].mean()
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


res = {}
for tname, targ in (("Y4", Y4), ("YR4", YR4)):
    print("\n" + "=" * 92)
    print("TARGET %s   (%s)" % (tname, "DEPLOYMENT-relevant: what the book trades"
                                if tname == "Y4" else "SELECTION-relevant: what the coronation scored"))
    print("=" * 92)
    print("%-8s %-7s %10s %9s %8s   %s" % ("model", "caliber", "rank-IC", "t", "n", "per-year"))
    store = {}
    for mdl in ("champ", "lam0", "qim"):
        for cal in ("TRAIN", "SERVE"):
            if (mdl, cal) not in P:
                continue
            r, v = ic_series(P[(mdl, cal)], targ)
            store[(mdl, cal)] = (r, v)
            py = {int(y): round(float(v[yr[r] == y].mean()), 5) for y in sorted(set(yr[r].tolist()))}
            print("%-8s %-7s %+10.5f %+9.2f %8d   %s"
                  % (mdl, cal, v.mean(), v.mean() / v.std() * np.sqrt(len(v)), len(v),
                     " ".join("%d:%+.4f" % (k, x) for k, x in py.items())))
            res.setdefault(tname, {})["%s_%s" % (mdl, cal)] = {
                "rank_ic": float(v.mean()), "t": float(v.mean() / v.std() * np.sqrt(len(v))),
                "n": int(len(v)), "per_year": py}

    # ---- the controlled A/B: champ vs lam0, paired on identical anchors, per caliber ----
    print("\n  --- CONTROLLED A/B: champ (xattn) vs lam0 (no xattn), paired on identical anchors ---")
    for cal in ("TRAIN", "SERVE"):
        if ("champ", cal) not in store or ("lam0", cal) not in store:
            continue
        ra, va = store[("champ", cal)]
        rb, vb = store[("lam0", cal)]
        common, ia, ib = np.intersect1d(ra, rb, return_indices=True)
        d = va[ia] - vb[ib]
        lo, hi = dayblock_boot(common, d)
        py = {int(y): round(float(d[yr[common] == y].mean()), 5) for y in sorted(set(yr[common].tolist()))}
        print("  %-6s margin %+0.5f  t %+0.2f  dayblock95 [%+0.5f, %+0.5f]  n=%d  win%%=%.1f"
              % (cal, d.mean(), d.mean() / d.std() * np.sqrt(len(d)), lo, hi, len(d), 100 * (d > 0).mean()))
        print("         per-year: %s" % " ".join("%d:%+.4f" % (k, x) for k, x in py.items()))
        res[tname]["margin_champ_minus_lam0_%s" % cal] = {
            "mean": float(d.mean()), "t": float(d.mean() / d.std() * np.sqrt(len(d))),
            "ci95_dayblock": [lo, hi], "n": int(len(d)),
            "win_rate": float((d > 0).mean()), "per_year": py}
    # does the margin itself survive the caliber change?
    if all(("champ", c) in store and ("lam0", c) in store for c in ("TRAIN", "SERVE")):
        rT, _ = store[("champ", "TRAIN")]; rS, _ = store[("champ", "SERVE")]
        common = np.intersect1d(rT, rS)
        def marg(cal):
            ra, va = store[("champ", cal)]; rb, vb = store[("lam0", cal)]
            _, ia, _ = np.intersect1d(ra, common, return_indices=True)
            _, ib, _ = np.intersect1d(rb, common, return_indices=True)
            return va[ia], vb[ib]
        aT, bT = marg("TRAIN"); aS, bS = marg("SERVE")
        dT = aT - bT; dS = aS - bS
        dd = dS - dT
        lo, hi = dayblock_boot(common, dd)
        print("\n  --- does the champion's MARGIN survive the caliber change? ---")
        print("  margin(TRAIN) %+0.5f -> margin(SERVE) %+0.5f | change %+0.5f  dayblock95 [%+0.5f, %+0.5f]"
              % (dT.mean(), dS.mean(), dd.mean(), lo, hi))
        res[tname]["margin_change_SERVE_minus_TRAIN"] = {
            "margin_TRAIN": float(dT.mean()), "margin_SERVE": float(dS.mean()),
            "change": float(dd.mean()), "ci95_dayblock": [lo, hi], "n": int(len(common))}

    # ---- qim reported separately (different model class, NOT a controlled A/B) ----
    for cal in ("TRAIN", "SERVE"):
        if ("qim", cal) in store and ("champ", cal) in store:
            ra, va = store[("champ", cal)]; rb, vb = store[("qim", cal)]
            common, ia, ib = np.intersect1d(ra, rb, return_indices=True)
            d = va[ia] - vb[ib]
            lo, hi = dayblock_boot(common, d)
            print("  [separate, different head class] champ - qim %-6s %+0.5f  t %+0.2f  95%% [%+0.5f, %+0.5f]"
                  % (cal, d.mean(), d.mean() / d.std() * np.sqrt(len(d)), lo, hi))
            res[tname]["champ_minus_qim_%s" % cal] = {
                "mean": float(d.mean()), "t": float(d.mean() / d.std() * np.sqrt(len(d))),
                "ci95_dayblock": [lo, hi], "n": int(len(d))}

json.dump(res, open("/tmp/vs2_score_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs2_score_result.json", flush=True)
