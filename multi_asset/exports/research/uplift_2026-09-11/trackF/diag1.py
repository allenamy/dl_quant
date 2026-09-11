import numpy as np, time, calendar
from judgeF import gseries, levels, C, boot, FROZEN, T
A=np.load('arms.npz'); B=np.load('tf.npz'); L=np.load('labels.npz')
lmap={int(t):int(l) for t,l in zip(L['ts'],L['lab'])}
NAMES={-1:'WARM',0:'LL',1:'LH',2:'HL',3:'HH'}
CAND={"A0":A['PARITY_A0_dyn_s42__rec'],"R1":B['TF_R1__rec'],"R1b":B['TF_R1b__rec'],"R2":B['TF_R2__rec'],
      "R3":B['TF_R3__rec'],"F1":B['TF_F1__rec'],"F1R":B['TF_F1R__rec']}
print("=== seat weights by year (w3_king incl. the DL slot, w3_fund) ===")
for nm,rec in CAND.items():
    ts=np.round(rec[:,0]).astype(np.int64); yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
    print(f"{nm:5s} "+" ".join(f"{y}:k{rec[yr==y,C['w3_king']].mean():.2f}/f{rec[yr==y,C['w3_fund']].mean():.2f}/r{rec[yr==y,C['w3_rev24']].mean():.2f}" for y in range(2022,2027) if (yr==y).any()))
print()
print("=== cross-regime summary: mean g / annualised Sharpe (SE) ===")
SPANS={"FULL 2022-01-31->2026-08-10":(0,T(2026,8,10,20)+1),
       "2023-01->2026-08-10 (DL era)":(T(2023,1,1),T(2026,8,10,20)+1),
       "2024-01->2026-08-10 (full arsenal)":(T(2024,1,1),T(2026,8,10,20)+1),
       "frozen 2025-03->2026-08-10":FROZEN}
hdr=f"{'form':6s}"+"".join(f"{s.split(' ')[0]:>26s}" for s in SPANS)
print(hdr)
for nm,rec in CAND.items():
    ts,g=gseries(rec); line=f"{nm:6s}"
    for s,(lo,hi) in SPANS.items():
        m=(ts>=lo)&(ts<hi); v=g[m]
        sh=v.mean()/v.std(ddof=1)*np.sqrt(2190); se=np.sqrt(2190/m.sum())
        line+=f"  {v.mean():6.3f} Sh{sh:5.2f}+-{se:4.2f}"
    print(line)
print()
print("=== per-year annualised Sharpe (SE) ===")
print(f"{'form':6s}"+"".join(f"{y:>17d}" for y in range(2022,2027)))
for nm,rec in CAND.items():
    ts,g=gseries(rec); yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); line=f"{nm:6s}"
    for y in range(2022,2027):
        m=yr==y
        if y==2026: m=m&(ts<=T(2026,8,10,20))
        if m.sum()<3: line+=f"{'--':>17s}"; continue
        v=g[m]; line+=f"{v.mean()/v.std(ddof=1)*np.sqrt(2190):11.2f}+-{np.sqrt(2190/m.sum()):4.2f}"
    print(line)
print()
print("=== A0 vs F1 by regime cell (all anchors, post burn-in) ===")
for nm in ("A0","F1","R1"):
    rec=CAND[nm]; ts,g=gseries(rec); lb=np.array([lmap.get(int(t),-1) for t in ts]); line=f"{nm:5s}"
    for l in (0,1,2,3):
        v=g[lb==l]; line+=f"  {NAMES[l]} {v.mean():6.3f}({v.mean()/v.std(ddof=1)*np.sqrt(2190):5.2f})n{len(v)}"
    print(line)
print()
print("=== decomposition per unit gross by year: A0 vs F1 ===")
for nm in ("A0","F1"):
    rec=CAND[nm]; ts=np.round(rec[:,0]).astype(np.int64); yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); gt=rec[:,C['gross_total']]
    for y in range(2022,2027):
        m=yr==y
        print(f"{nm:4s}{y} pnl {np.mean(rec[m,C['pnl_ex']]/gt[m]):7.3f} carry {np.mean(rec[m,C['carry_ex']]/gt[m]):7.3f} cost {np.mean(rec[m,C['cost_ex']]/gt[m]):7.3f} net {np.mean(rec[m,C['net_ex']]/gt[m]):7.3f} turn {np.mean(rec[m,C['turnover']]):6.4f} gross {gt[m].mean():5.3f}")
