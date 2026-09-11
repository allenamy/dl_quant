#!/usr/bin/env python3
import numpy as np, time, math, datetime as dt, json
S="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/w10"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
LIVE=-91.0125469180; LIVE_MEAN=-0.9480; LIVE_SD=35.77; LIVE_N=96
def load(tag):
    z=np.load(f"{S}/w10_ablation_series_{tag}.npz",allow_pickle=True)
    c=[str(x) for x in z["cols"]]; r=z["d30_n2_c42_rec"]; g=lambda k:r[:,c.index(k)].astype(float)
    return r[:,c.index("ts")].astype(np.int64), g("net_ex")/g("gross_total"), g("net_ex"), g("gross_total"), g("leg_fund"), g("leg_king")

print("=== ARM SENSITIVITY of the percentile ===")
for tag in ("pod_live_w3fix_callog_s42","pod_live_callog_s42","pod_canon_callog_s42","pod_live_w3fix_calsimple_s42"):
    ts,u,ne,gt,lf,lk=load(tag)
    DAY=np.array([time.strftime("%Y%m%d",time.gmtime(int(t))) for t in ts])
    idx={}
    for d_,v in zip(DAY,u): idx[d_]=idx.get(d_,0)+v
    for lab,lo,hi in (("2024on","20240101","20260830"),("2026","20260101","20260830")):
        c=dt.date(int(lo[:4]),int(lo[4:6]),int(lo[6:])); e=dt.date(int(hi[:4]),int(hi[4:6]),int(hi[6:]))
        v=[]
        while c<=e: v.append(idx.get(c.strftime("%Y%m%d"),0.0)); c+=dt.timedelta(days=1)
        v=np.array(v); s=np.convolve(v,np.ones(17),mode="valid")
        yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
        m=(yr>=2024) if lab=="2024on" else (yr==2026)
        print(f"  {tag:32s} {lab:7s} bt_mean={u[m].mean():+6.3f}bps  win_mean={s.mean():+7.0f} sd={s.std(ddof=1):5.0f} | LIVE {LIVE:+.0f} -> pct {100*(s<=LIVE).mean():5.2f}%")

ts,u,ne,gt,lf,lk=load("pod_live_w3fix_callog_s42")
DAY=np.array([time.strftime("%Y%m%d",time.gmtime(int(t))) for t in ts]); M=np.array([d[:6] for d in DAY])
Y=np.array([int(d[:4]) for d in DAY])

print("\n=== 2026 CONCENTRATION: drop the two best months ===")
s26=Y==2026; tot=u[s26].sum()
ex=s26 & (M!="202604") & (M!="202606")
print(f"  2026 all      : n={s26.sum()} sum {tot/100:+.1f}%gross  mean {u[s26].mean():+.3f} bps Sharpe {u[s26].mean()/u[s26].std(ddof=1)*np.sqrt(2190):+.2f}  ann(arith) {u[s26].mean()*21.90:+.1f}%")
print(f"  2026 ex Apr+Jun: n={ex.sum()} sum {u[ex].sum()/100:+.1f}%gross  mean {u[ex].mean():+.3f} bps Sharpe {u[ex].mean()/u[ex].std(ddof=1)*np.sqrt(2190):+.2f}  ann(arith) {u[ex].mean()*21.90:+.1f}%")
onlyAJ=s26&((M=="202604")|(M=="202606"))
print(f"  Apr+Jun only  : n={onlyAJ.sum()} ({100*onlyAJ.sum()/s26.sum():.0f}% of 2026 anchors) sum {u[onlyAJ].sum()/100:+.1f}%gross = {100*u[onlyAJ].sum()/tot:.1f}% of the year")
# day concentration by year
print("\n=== DAY CONCENTRATION by year (share of the year's total from the best k days) ===")
for y in (2024,2025,2026):
    s=Y==y; ds={}
    for d_,v in zip(DAY[s],u[s]): ds[d_]=ds.get(d_,0)+v
    dv=np.array(sorted(ds.values())[::-1]); T=dv.sum()
    print(f"  {y}: total {T/100:+7.1f}%gross over {len(dv)} days | top5 {100*dv[:5].sum()/T if T!=0 else float('nan'):6.1f}% | top10 {100*dv[:10].sum()/T:6.1f}% | top20 {100*dv[:20].sum()/T:6.1f}% | %days>0 {100*(dv>0).mean():.1f}%")

print("\n=== FULL-CYCLE YEARLY, live caliber (arm pod_live_w3fix_callog_s42), per unit GROSS ===")
print("year | anchors | bps/anch | Sharpe_ann | realized %gross in-year | annualized %gross | maxDD %gross | worst month %gross | @2x NAV ann")
for y in sorted(set(Y.tolist())):
    s=Y==y; x=u[s]
    if s.sum()<100: continue
    sh=x.mean()/x.std(ddof=1)*np.sqrt(2190); cs=np.cumsum(x)
    dd=(cs-np.maximum.accumulate(cs)).min()/100
    wmo=min(x[M[s]==m].sum() for m in sorted(set(M[s].tolist())))/100
    rom=ne[s].mean()/gt[s].mean()*2190/100
    print(f"{y} | {s.sum():5d} | {x.mean():+8.3f} | {sh:+6.2f} | {x.sum()/100:+8.1f}% | {x.mean()*21.90:+7.1f}% (ratio-of-means {rom:+.1f}%) | {dd:7.1f}% | {wmo:+7.1f}% | {2*x.mean()*21.90:+7.1f}%")
s=Y>=2024; x=u[s]
print(f"2024on | {s.sum():5d} | {x.mean():+8.3f} | {x.mean()/x.std(ddof=1)*np.sqrt(2190):+6.2f} | {x.sum()/100:+8.1f}% | {x.mean()*21.90:+7.1f}% | | | {2*x.mean()*21.90:+7.1f}%")

print("\n=== STOPPING RULE: how bad, for how long, before the 2026-regime backtest is rejected (one-sided 95%) ===")
mu26=u[Y==2026].mean(); sd26=u[Y==2026].std(ddof=1)
mu24=u[Y>=2024].mean(); sd24=u[Y>=2024].std(ddof=1)
for N in (96,204,408,600,1000):
    thr26=mu26*N-1.645*sd26*math.sqrt(N); thr24=mu24*N-1.645*sd24*math.sqrt(N)
    print(f"  after {N:5d} anchors ({N/6:4.0f} days): reject 2026-regime if cum < {thr26:+8.0f} bps of gross ; reject 2024on-regime if cum < {thr24:+8.0f}")
print(f"  live is at {LIVE:+.0f} bps of gross after {LIVE_N} anchors -> neither rejected.")
# where would live have to be to reject now
print(f"  to reject the 2026 regime TODAY the 96-anchor cum would have to be < {mu26*96-1.645*sd26*math.sqrt(96):+.0f} bps (live {LIVE:+.0f}).")

print("\n=== BASE RATE of stretches at least this bad, backtest 2024-2026 ===")
idx={}
for d_,v in zip(DAY,u): idx[d_]=idx.get(d_,0)+v
c=dt.date(2024,1,1); e=dt.date(2026,8,30); v=[]; ds=[]
while c<=e: ds.append(c.strftime("%Y%m%d")); v.append(idx.get(ds[-1],0.0)); c+=dt.timedelta(days=1)
v=np.array(v); s17=np.convolve(v,np.ones(17),mode="valid")
print(f"  P(17d window <= -91 bps) = {100*(s17<=LIVE).mean():.1f}% ; P(<=0) = {100*(s17<=0).mean():.1f}% ; P(<= -500) = {100*(s17<=-500).mean():.1f}%")
cum=np.cumsum(v); ddown=cum-np.maximum.accumulate(cum)
print(f"  2024-2026 backtest: max drawdown {ddown.min()/100:.1f}% of gross; longest stretch under water {max((lambda a: [len(x) for x in ''.join('1' if q<0 else '0' for q in ddown).split('0')] )(ddown) or [0])} days")

print("\n=== SENSITIVITY of the percentile to the live window value ===")
for LV in (-45,-76,-91,-130,-150,-200,-258,-300,-400):
    print(f"  live window {LV:+5d} bps of gross -> pct(2024on) {100*(s17<=LV).mean():5.1f}%")
c=dt.date(2026,1,1); e=dt.date(2026,8,30); v2=[]
while c<=e: v2.append(idx.get(c.strftime('%Y%m%d'),0.0)); c+=dt.timedelta(days=1)
s26w=np.convolve(np.array(v2),np.ones(17),mode='valid')
for LV in (-45,-76,-91,-130,-150,-200,-258,-300):
    print(f"  live window {LV:+5d} bps of gross -> pct(2026)   {100*(s26w<=LV).mean():5.1f}%")
