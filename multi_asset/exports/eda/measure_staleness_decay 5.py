"""What does TRAINING-DATA STALENESS cost? — measured from the folds we already have.

> **创建:** 2026-08-04 00:0x UTC | **Session:** B4-retrain | **状态:** final
> **派工:** team-lead(用户质疑触发: 部署的 fold_4 训练止于 2025-11-23, 今日已陈旧 253 天)
> **作废条件:** 折结构改变 ⇒ 重跑

THE QUESTION. The deployed model is fold 4, trained through 2025-11-23. Extending the panel moves
the TEST window, not the training window — so S2's net content for the deployed model is close to
nothing. Before redefining S2 around "train on recent data", we want a number for what the staleness
is actually costing.

THE MEASUREMENT, and it needs no new training. Every fold's test anchors sit at KNOWN distances from
that fold's own training cutoff (embargo + val push the first test anchor ~39 days out; a full-year
test runs to ~404 days). So each fold already contains an IC-versus-staleness curve, and pooling the
five folds averages the curve over five different test years.

    per anchor t:  staleness(t) = day(t) − last_train_day(fold)
                   ic(t)        = cross-sectional rank-IC of the ensemble composite vs the target
    -> regress / bin ic on staleness

★★ THE CONFOUND IS FATAL TO ATTRIBUTION, AND POOLING DOES NOT HELP. I first wrote here that pooling
  five folds "mitigates it (five different years)". That is WRONG, and the way it is wrong is the
  point:

      EVERY fold cuts training at Nov 23 and tests Jan–Dec of the next year.
      So staleness ≡ (calendar position within the test year) + constant, IDENTICALLY in all five.

  The freshest anchors are always January; the stalest are always November. Pooling five folds
  stacks five copies of the SAME alignment — it averages over years but not over the confound, so it
  adds confidence to the curve while doing nothing whatsoever to separate "the model went stale"
  from "the back half of a year scores lower". Five identical confoundings are not a control.

  ⇒ These folds CANNOT attribute the decay. What would: a fold whose training cutoff sits at a
    DIFFERENT calendar position (e.g. cut in May), so staleness and month stop moving together.
    That requires new training — which is exactly the decision this measurement is feeding.
  ⇒ So the output is an UPPER BOUND on what retraining could buy, not an estimate of it:
    "if the association is entirely staleness, closing N days buys ~slope × N; if it is entirely
    seasonal, it buys nothing." Both endpoints are live.
"""
from __future__ import annotations

import argparse
import json
import os.path as _p
import sys

import numpy as np
from scipy.stats import rankdata

_ROOT = _p.dirname(_p.dirname(_p.dirname(_p.dirname(_p.abspath(__file__)))))
sys.path.insert(0, _ROOT)
import multi_asset.train.train_wide_harness as TH  # noqa: E402


def per_anchor_ic(scores, rows, YR, YRAW, member, CL):
    """Both targets scored on ONE COMMON base per anchor.

    YR and Y4 have different NaN masks (YR finite 0.670 vs Y 0.764), so scoring them independently
    yields two different anchor sets — which cannot then be regressed against one staleness vector,
    and silently compares two different samples if you don't notice the length mismatch. Requiring
    both finite makes the resid and raw curves describe the same anchors and the same assets.
    """
    out = []
    for i in rows:
        base = np.where(member[i] & CL[i] & np.isfinite(YR[i]) & np.isfinite(YRAW[i]))[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size)
        nk = 0
        for k in range(scores.shape[2]):
            col = scores[i, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std()
                nk += 1
        if nk == 0:
            continue
        r = rankdata(comp / nk)
        ic = np.corrcoef(r, rankdata(YR[i, base]))[0, 1]
        icr = np.corrcoef(r, rankdata(YRAW[i, base]))[0, 1]
        if np.isfinite(ic) and np.isfinite(icr):
            out.append((int(i), float(ic), float(icr)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--runs", nargs="+", required=True, help="label=dir ...")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    z = np.load(a.panel, allow_pickle=True)
    member, CL, YR, Yraw = z["MEMBER110"], z["CL4"], z["YR4"], z["Y4"]
    data = TH.WidePanelData(path=a.panel, target_horizon=4, aux_horizons=(1, 24))
    folds = TH.year_folds(data, embargo_days=8, val_days=30, year_from=None)
    day = np.arange(len(z["ts"])) // 24

    rec = {}
    for spec in a.runs:
        label, d = spec.split("=", 1)
        print(f"\n===== {label} =====", flush=True)
        allst, allic, allic_raw, per_fold = [], [], [], {}
        for k, f in enumerate(folds):
            p = _p.join(d, f"fold_{k}_head_scores.npz")
            if not _p.exists(p):
                continue
            zz = np.load(p)
            sc, te = zz["scores"], zz["te_rows"]
            last_tr = int(f["tr"][-1])
            pts = per_anchor_ic(sc, te, YR, Yraw, member, CL)
            st = np.array([day[i] - last_tr for i, _, _ in pts], float)
            ic = np.array([v for _, v, _ in pts], float)
            icr = np.array([w for _, _, w in pts], float)
            slope = np.polyfit(st, ic, 1)[0] if len(st) > 10 else np.nan
            per_fold[f["year"]] = dict(n=len(st), staleness_range=[float(st.min()), float(st.max())],
                                       mean_ic=round(float(ic.mean()), 5),
                                       slope_per_day=float(slope),
                                       slope_per_100d=round(float(slope) * 100, 5))
            print(f"  fold te={f['year']}: n={len(st):5d}  staleness {st.min():.0f}..{st.max():.0f}d"
                  f"  mean IC {ic.mean():+.5f}  slope/100d {slope*100:+.5f}", flush=True)
            allst.append(st); allic.append(ic); allic_raw.append(icr)
        if not allst:
            continue
        ST, IC, ICR = np.concatenate(allst), np.concatenate(allic), np.concatenate(allic_raw)
        sl, itc = np.polyfit(ST, IC, 1)
        slr = np.polyfit(ST, ICR, 1)[0]
        print(f"  POOLED n={len(ST)}  slope {sl*100:+.5f} /100d (resid)   {slr*100:+.5f} /100d (raw)")
        bins = [(39, 90), (90, 150), (150, 220), (220, 300), (300, 410)]
        binrep = []
        for lo, hi in bins:
            m = (ST >= lo) & (ST < hi)
            if m.sum() > 20:
                binrep.append(dict(lo=lo, hi=hi, n=int(m.sum()),
                                   mean_ic=round(float(IC[m].mean()), 5),
                                   mean_ic_raw=round(float(ICR[m].mean()), 5)))
                print(f"    staleness {lo:3d}-{hi:3d}d  n={int(m.sum()):5d}  "
                      f"IC {IC[m].mean():+.5f}  rawIC {ICR[m].mean():+.5f}")
        rec[label] = dict(per_fold=per_fold, pooled_slope_per_100d_resid=round(float(sl) * 100, 5),
                          pooled_slope_per_100d_raw=round(float(slr) * 100, 5),
                          bins=binrep, n=int(len(ST)),
                          deployed_staleness_days_today=253)
        print(f"  ⇒ if causal, closing 253d of staleness ≈ {-sl*253:+.5f} resid IC "
              f"({-slr*253:+.5f} raw)", flush=True)

    json.dump(rec, open(a.out, "w"), indent=1)
    print(f"\nrecord -> {a.out}")


if __name__ == "__main__":
    main()
