import numpy as np, calendar, glob, os
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C=dict((c,i) for i,c in enumerate(COLS))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
HC="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"; TD="/workspace/uplift_2026-09-11/trackD_v4"
def load(p,key="rec"):
    A=np.load(p,allow_pickle=True); R=np.asarray(A[key] if key in A.files else A["rec"],float)
    return np.round(R[:,0]).astype(np.int64),R[:,C["net_ex"]]/R[:,C["gross_total"]],R
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
t0,g0,R0=load(HC+"/w10_ablation_series_V4_A0_dyn_s42.npz","d30_n2_c42_rec")
names={"ORTH_amihud":"SL_ORTH_f_amihud_24h__p","ORTH_asz":"SL_ORTH_f_asz_24h__m","ORTH_SURP":"SL_ORTH_D_SURP__m",
 "RAW_amihud":"SL_f_amihud_24h__p","TBF":"SL_f_tbf_24h__p","VOL7_p":"SL_f_vol_7d__p","VOL7_m":"SL_f_vol_7d__m",
 "RANGE_p":"SL_f_range_24h__p","RANGE_m":"SL_f_range_24h__m","VOLQ_p":"SL_f_volq_ratio__p","VOLQ_m":"SL_f_volq_ratio__m",
 "CPOS_p":"SL_f_cpos_24h__p","LOBDEPTH_m":"SL_LOBDEPTH__m"}
G={}
BASE_TS=t0
for k,v in names.items():
    ts,g,R=load(TD+"/"+v+".npz")
    ga=np.full(len(t0),np.nan); _,ia,ib=np.intersect1d(t0,ts,return_indices=True); ga[ia]=g[ib]
    G[k]=(ts,ga,R,len(ts))
m0=(t0>=FULL[0])&(t0<FULL[1])
keys=list(names)
print("=== correlation matrix of book-layer g (full cycle) ===")
print("%-12s"%""+"".join("%9s"%k[:8] for k in keys)+"      A0")
for a in keys:
    ga=G[a][1]; row=[]
    for b in keys:
        gb=G[b][1]; ok=m0&np.isfinite(ga)&np.isfinite(gb)
        row.append(np.corrcoef(ga[ok],gb[ok])[0,1])
    print("%-12s"%a[:12]+"".join("%9.3f"%x for x in row)+"  %6.3f"%np.corrcoef(ga[m0&np.isfinite(ga)],g0[m0&np.isfinite(ga)])[0,1]+"  n=%d"%G[a][3])
print()
print("=== per-arm full-cycle level + yearly ===")
YR={"2022":(T(2022,1,1),T(2023,1,1)),"2023":(T(2023,1,1),T(2024,1,1)),"2024":(T(2024,1,1),T(2025,1,1)),"2025":(T(2025,1,1),T(2026,1,1)),"2026":(T(2026,1,1),T(2026,8,10,20)+1)}
print("%-12s %8s %7s | %s"%("arm","full","sharpe"," ".join("%8s"%y for y in YR)))
for k in keys:
    ts,g,R=load(TD+"/"+names[k]+".npz")
    m=(ts>=FULL[0])&(ts<FULL[1])
    row="%-12s %+8.3f %7.2f | "%(k,g[m].mean(),g[m].mean()/g[m].std(ddof=1)*np.sqrt(2190))
    for y,(lo,hi) in YR.items():
        mm=(ts>=lo)&(ts<hi); row+="%+8.3f "%g[mm].mean()
    print(row)
print()
print("=== universe size / selection by year (A0 vs ORTH_amihud) ===")
for y,(lo,hi) in YR.items():
    m=(t0>=lo)&(t0<hi)
    ta=G["ORTH_amihud"][0]; Ra=G["ORTH_amihud"][2]; ma=(ta>=lo)&(ta<hi)
    print("  %s  A0 nsel=%6.1f nmem=%6.1f | ORTH_amihud nsel=%6.1f nmem=%6.1f  gross=%.3f/%.3f"%(
        y,R0[m,C["nsel"]].mean(),R0[m,C["nmember"]].mean(),Ra[ma,C["nsel"]].mean(),Ra[ma,C["nmember"]].mean(),
        R0[m,C["gross_total"]].mean(),Ra[ma,C["gross_total"]].mean()))
