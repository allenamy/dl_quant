#!/usr/bin/env python3
"""AXIS: is 2026-08-26..09-11 'just a bad period'?
Device: w10_universe.py port on pod2 (/workspace/port_w10, sha 64c70a44... = orig 43578158 with 3 path consts).
Arm: pod_live_w3fix_callog_s42 = LEGS=101 (no rev24) + PHI=0.45 (V2MAIN blended into king slot)
     + W3FIX=0.21,0,0.79 (fixed live seats) + MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero (live form)
     + CAL=log  <-- on the pod 5m-cache panel lineage y4 = SUM of 5m SIMPLE returns, so CAL=log means
       "use y4 raw"; CAL=simple applies expm1 = the E-0904-F pseudo-convexity artifact. CAL=log is the
       UNBIASED caliber for this panel (RESULT_caliber_revalidation_2026-09-04.md).
Unit: E-0904-G -- device net_ex is bps per unit NAV with book gross = gross_total (0.5-0.9),
      so PER UNIT GROSS = net_ex / gross_total.
"""
import numpy as np, time, json, sys, os
S="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/w10"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"

def load(tag, arm="d30_n2_c42"):
    z=np.load(f"{S}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    cols=[str(c) for c in z["cols"]]; rec=z[f"{arm}_rec"]
    g=lambda k: rec[:,cols.index(k)].astype(float)
    cfg=json.loads(str(z["config_json"])) if "config_json" in z else {}
    return dict(ts=rec[:,cols.index("ts")].astype(np.int64), net_ex=g("net_ex"),
                gross=g("gross_total"), pnl=g("pnl_ex"), carry=g("carry_ex"), cost=g("cost_ex"),
                nsel=g("nsel"), cfg=cfg)

TAG="pod_live_w3fix_callog_s42"
d=load(TAG)
print("CONFIG:", json.dumps(d["cfg"]))
ts=d["ts"]; u = d["net_ex"]/d["gross"]           # bps per unit gross per anchor
Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
M=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in ts])
DAY=np.array([time.strftime("%Y%m%d",time.gmtime(int(t))) for t in ts])
print(f"anchors {len(ts)}  {time.strftime('%Y-%m-%d %HZ',time.gmtime(ts.min()))} -> {time.strftime('%Y-%m-%d %HZ',time.gmtime(ts.max()))}")

# ---- parity check vs docs/RESULT_caliber_revalidation_2026-09-04.md
print("\n== PARITY: yearly net_ex (bps/anchor, per unit NAV) vs published table ==")
for y in (2024,2025,2026):
    s=Y==y
    print(f"  {y}: net_ex mean {d['net_ex'][s].mean():+.4f} (doc: 2024 -0.642 / 2025 +0.284 / 2026 +2.378)"
          f"  gross_total {d['gross'][s].mean():.4f}  %/gross = {u[s].mean()*2190/100:+.2f}%  (mean-of-ratios)")

# ---- FULL-CYCLE YEARLY TABLE, live caliber, per unit gross
print("\n== TABLE A: FULL-CYCLE YEARLY, live caliber (arm %s) ==" % TAG)
print(f"{'year':>6} {'n':>5} {'bps/anch/gross':>15} {'Sharpe_ann':>10} {'%/gross/yr(arith)':>18} {'%/gross/yr(compd)':>18} {'maxDD %gross':>13} {'worst month %gross':>19}")
yearly={}
for y in sorted(set(Y.tolist())):
    s=Y==y; x=u[s]
    if s.sum()<100: continue
    sh=x.mean()/x.std(ddof=1)*np.sqrt(2190)
    arith=x.mean()*2190/100
    eq=np.cumprod(1+x/1e4); compd=eq[-1]**(2190/len(x))-1
    cs=np.cumsum(x); dd=(cs-np.maximum.accumulate(cs)).min()/100
    mm=M[s]; wmo=min(x[mm==m].sum() for m in sorted(set(mm.tolist())))/100
    yearly[int(y)]=dict(n=int(s.sum()),bps=float(x.mean()),sharpe=float(sh),arith_pct=float(arith),
                        compd_pct=float(compd*100),maxdd_pct=float(dd),worst_month_pct=float(wmo))
    print(f"{y:>6} {s.sum():>5} {x.mean():>+15.4f} {sh:>+10.2f} {arith:>+17.1f}% {compd*100:>+17.1f}% {dd:>12.1f}% {wmo:>18.1f}%")
s=Y>=2024; x=u[s]
print(f"{'2024on':>6} {s.sum():>5} {x.mean():>+15.4f} {x.mean()/x.std(ddof=1)*np.sqrt(2190):>+10.2f} {x.mean()*2190/100:>+17.1f}%")

# ---- MONTHLY 2026 concentration
print("\n== TABLE B: 2026 MONTHLY, live caliber, per unit gross ==")
s26=Y==2026; tot26=u[s26].sum()
print(f"  2026 total (to {time.strftime('%Y-%m-%d',time.gmtime(ts.max()))}) = {tot26/100:+.1f}% of gross over {s26.sum()} anchors")
mrows=[]
for m in sorted(set(M[s26].tolist())):
    sm=(M==m); x=u[sm]
    mrows.append((m,int(sm.sum()),x.sum()/100,x.mean(),x.mean()/x.std(ddof=1)*np.sqrt(2190),100*x.sum()/tot26))
    print(f"  {m} n={sm.sum():4d} sum={x.sum()/100:+7.1f}%gross mean={x.mean():+6.3f}bps Sharpe={x.mean()/x.std(ddof=1)*np.sqrt(2190):+6.2f} share_of_2026={100*x.sum()/tot26:+6.1f}%")
# top-k day concentration
dsum={}
for dd_,xx in zip(DAY[s26],u[s26]): dsum[dd_]=dsum.get(dd_,0)+xx
dv=np.array(sorted(dsum.values())[::-1]); nd=len(dv)
print(f"  2026 trading days n={nd}; top 5 days = {dv[:5].sum()/100:+.1f}%gross ({100*dv[:5].sum()/tot26:.1f}% of year); "
      f"top 10 = {dv[:10].sum()/100:+.1f}% ({100*dv[:10].sum()/tot26:.1f}%); top 20 = {dv[:20].sum()/100:+.1f}% ({100*dv[:20].sum()/tot26:.1f}%)")
print(f"  median day {np.median(dv):+.3f} bps; share of days positive {100*(dv>0).mean():.1f}%")

# ---- DAILY series per unit gross (bps), backtest
uni_days=sorted(set(DAY.tolist()))
dayv=np.array([u[DAY==dd_].sum() for dd_ in uni_days])          # bps of gross per DAY (sum over anchors)
dayn=np.array([(DAY==dd_).sum() for dd_ in uni_days])
dayY=np.array([int(dd_[:4]) for dd_ in uni_days])
np.savez(f"{OUT}/backtest_daily_unitgross.npz", day=np.array(uni_days), bps=dayv, nanch=dayn)

# ---- the exact live window inside backtest coverage
print("\n== Q2: the exact live window in the backtest ==")
w_lo, w_hi = "20260826","20260911"
insel=(DAY>=w_lo)&(DAY<=w_hi)
print(f"  backtest anchors inside 08-26..09-11 : {insel.sum()} (device data ends {uni_days[-1]}; F10 OOS preds end 2026-08-10 -> DL leg is NaN->0 after that)")
if insel.sum():
    x=u[insel]
    print(f"  backtest 08-26..08-30 (overlap only): n={insel.sum()} mean={x.mean():+.4f} bps/anchor/gross  sum={x.sum()/100:+.3f}% of gross")
    print(f"     decomposition mean: pnl_ex {d['pnl'][insel].mean():+.3f} - carry_ex {d['carry'][insel].mean():+.3f} - cost_ex {d['cost'][insel].mean():+.3f} (per unit NAV) ; gross_total {d['gross'][insel].mean():.3f}")
# same calendar window in prior years
for y in (2024,2025):
    sel=(DAY>=f"{y}0826")&(DAY<=f"{y}0911"); x=u[sel]
    print(f"  seasonal analogue {y}-08-26..09-11: n={sel.sum()} mean={x.mean():+.4f} bps sum={x.sum()/100:+.3f}% of gross")
