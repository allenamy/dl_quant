"""Aggregate the walk-forward monthly trajectory: per-month CLEAN P/S/beta/sigma/DA + pooled + IC-IR +
worst-month + %-CLEAN-positive + a net-of-cost Sharpe sketch. Streams (run anytime; uses whatever months are done).
"""
from __future__ import annotations
import numpy as np, glob, os
from multi_asset.eval.eval_caliber import eval_file
import datetime
months=[]
d=datetime.date(2024,6,1)
while d<=datetime.date(2026,5,1):
    months.append(f"{d.year:04d}_{d.month:02d}"); d=(d.replace(day=28)+datetime.timedelta(days=7)).replace(day=1)
rows=[]
print(f"{'month':8s} {'D_P':>7s} {'C_P':>7s} {'C_S':>7s} {'beta':>6s} {'sig':>5s} {'DA':>5s}")
for mk in months:
    pf=f"experiments/walkforward/wf_{mk}/fold_0/test_preds.npz"
    if not os.path.exists(pf): continue
    try:
        dense,clean=eval_file(pf)
        rows.append((mk,dense['P'],clean['P'],clean['S'],clean['beta'],clean['sigma'],clean.get('DA',0)))
        print(f"{mk:8s} {dense['P']:+.4f} {clean['P']:+.4f} {clean['S']:+.4f} {clean['beta']:+.2f} {clean['sigma']:.3f} {clean.get('DA',0):.3f}")
    except Exception as e: print(f"{mk}: {e}")
if rows:
    cP=np.array([r[2] for r in rows]); cS=np.array([r[3] for r in rows])
    print(f"\n=== AGGREGATE ({len(rows)} months done) ===")
    print(f"  POOLED clean-P mean = {cP.mean():+.4f} | clean-S mean = {cS.mean():+.4f}")
    print(f"  IC-IR (mean monthly clean-P / std) = {cP.mean()/(cP.std()+1e-9):+.3f}")
    print(f"  worst month clean-P = {cP.min():+.4f} ({rows[int(np.argmin(cP))][0]})")
    print(f"  best  month clean-P = {cP.max():+.4f} ({rows[int(np.argmax(cP))][0]})")
    print(f"  %-months CLEAN-positive = {100*np.mean(cP>0):.0f}%  ({int((cP>0).sum())}/{len(cP)})")
    # net-of-cost Sharpe sketch: monthly IC -> rough daily, minus cost. Crude per the cost-tiering caveat.
    # treat each month's clean-P as a monthly IC; annualized IC-IR proxy * sqrt(12)
    print(f"  annualized IC-IR proxy = {cP.mean()/(cP.std()+1e-9)*np.sqrt(12):+.2f} (sqrt-12 of monthly IC-IR; gross, pre-cost)")
