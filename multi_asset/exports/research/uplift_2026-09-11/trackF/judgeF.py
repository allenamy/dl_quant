"""Track F evaluator. g = net_ex/gross_total (judge_v4.load, verbatim formula); windows and the
UTC-day block bootstrap copied verbatim from judge_v4.py (boot/levels), base seed 20260905 with a
per-contrast substream. Reference = A0 (the frozen in-service arm), same anchor set enforced."""
import numpy as np, time, calendar, json, sys
def T(*a): return calendar.timegm(a + (0,)*(6-len(a)))
FROZEN=(T(2025,3,1), T(2026,8,10,20)+1)
WIN={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),
     "2025":(T(2025,1,1),T(2026,1,1)),"2026->08-10":(T(2026,1,1),T(2026,8,10,20)+1),
     "frozen":FROZEN,"2024-01->2026-08-10":(T(2024,1,1),T(2026,8,10,20)+1),
     "EXT 2025-03->2026-08-31":(T(2025,3,1),T(2026,8,31,20)+1),
     "holdout 2025-01->2026-08-10":(T(2025,1,1),T(2026,8,10,20)+1)}
APY=2190
COLSR=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLSR)}
def boot(v, days, rng, lo=2.5, hi=97.5):
    ud,inv=np.unique(days,return_inverse=True); nd=len(ud)
    if nd<3: return (float('nan'),)*3
    S=np.bincount(inv,weights=v,minlength=nd); N=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(2000,nd)); mn=S[idx].sum(1)/N[idx].sum(1)
    return float(np.percentile(mn,lo)), float(np.percentile(mn,hi)), float((mn>0).mean())
def gseries(rec):
    ts=np.round(rec[:,0]).astype(np.int64); return ts, rec[:,C["net_ex"]]/rec[:,C["gross_total"]]
def levels(ts,g):
    o={}
    for w,(lo,hi) in WIN.items():
        m=(ts>=lo)&(ts<hi)
        if not m.any(): continue
        v=g[m]; c=np.concatenate([[0.0],np.cumsum(v)]); dd=float(np.max(np.maximum.accumulate(c)-c))
        o[w]={"n":int(m.sum()),"mean":float(v.mean()),
              "sharpe":float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if m.sum()>2 and v.std(ddof=1)>0 else float('nan'),
              "se_sharpe":float(np.sqrt(APY/m.sum())),"maxdd":dd,"ann_pct":float(v.mean()*APY/1e4*100)}
    return o
def contrast(tsA,gA,tsB,gB,k,alpha_lo=2.5,alpha_hi=97.5):
    """B - A on the frozen window, matched anchor set."""
    ia={int(t):i for i,t in enumerate(tsA)}; ib={int(t):i for i,t in enumerate(tsB)}
    common=np.array(sorted(set(ia)&set(ib)))
    m=(common>=FROZEN[0])&(common<FROZEN[1]); cc=common[m]
    d=np.array([gB[ib[int(t)]]-gA[ia[int(t)]] for t in cc])
    rng=np.random.default_rng([20260905,k])
    lo,hi,p=boot(d, cc//86400, rng, alpha_lo, alpha_hi)
    return {"n":int(len(cc)),"delta":float(d.mean()),"ci_lo":lo,"ci_hi":hi,"p_gt0":p}
if __name__=="__main__":
    A=np.load('arms.npz'); B=np.load('tf.npz')
    REF=("A0", A['PARITY_A0_dyn_s42__rec'])
    CANDS=[("A0(parity)",A['PARITY_A0_dyn_s42__rec']),("TFPARITY",B['TFPARITY__rec']),
           ("R1 regime seat 900",B['TF_R1__rec']),("R1b regime seat 300",B['TF_R1b__rec']),
           ("R2 regime seat+rev24",B['TF_R2__rec']),("R3 regime EMA .20",B['TF_R3__rec']),
           ("F1 DL own seat",B['TF_F1__rec']),("F1R DL seat+regime",B['TF_F1R__rec'])]
    tsA,gA=gseries(REF[1])
    rows=[]
    print(f"{'candidate':24s}"+"".join(f"{w:>13s}" for w in ("2022","2023","2024","2025","2026->08-10"))+f"{'frozen':>10s}{'Sh':>7s}{'24on':>9s}{'Sh':>7s}")
    for i,(nm,rec) in enumerate(CANDS):
        ts,g=gseries(rec); L=levels(ts,g)
        line=f"{nm:24s}"+"".join(f"{L[w]['mean']:13.3f}" if w in L else f"{'--':>13s}" for w in ("2022","2023","2024","2025","2026->08-10"))
        line+=f"{L['frozen']['mean']:10.3f}{L['frozen']['sharpe']:7.2f}{L['2024-01->2026-08-10']['mean']:9.3f}{L['2024-01->2026-08-10']['sharpe']:7.2f}"
        print(line); rows.append((nm,L))
    print()
    print(f"{'contrast (B-A0) frozen window':32s}{'n':>6s}{'delta':>9s}{'CI95':>22s}{'CI99.17(Bonf K=6)':>26s}{'P>0':>7s}")
    for k,(nm,rec) in enumerate(CANDS[2:],start=1):
        ts,g=gseries(rec)
        c=contrast(tsA,gA,ts,g,k); c2=contrast(tsA,gA,ts,g,k,0.4167,99.5833)
        print(f"{nm:32s}{c['n']:6d}{c['delta']:9.3f}   [{c['ci_lo']:7.3f},{c['ci_hi']:7.3f}]   [{c2['ci_lo']:8.3f},{c2['ci_hi']:8.3f}]{c['p_gt0']:7.3f}")
    json.dump({nm:L for nm,L in rows}, open('RESULT_levels.json','w'), indent=1)
