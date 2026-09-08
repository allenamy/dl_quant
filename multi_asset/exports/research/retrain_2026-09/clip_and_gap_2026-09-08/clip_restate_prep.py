import numpy as np, time, calendar, json
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
fts=F["E_ts"].astype(np.int64); has=F["has"]; syms=[str(s) for s in F["symbols"]]
A=np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s42_ccal.npz",allow_pickle=True)
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
R=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]; ats=R[:,0].astype(np.int64)
gi={t:i for i,t in enumerate(fts)}
need=set(); cells=[]
for p,t in enumerate(ats):
    if t not in gi: continue
    w=W[p]; hit=has[gi[t]]&(np.abs(w)>0)
    if not hit.any(): continue
    ym=time.strftime("%Y-%m",time.gmtime(int(t)))
    for j in np.where(hit)[0]:
        need.add((syms[j],ym)); cells.append((int(t),syms[j],float(w[j])))
print("affected held cells: %d ; distinct (symbol,month): %d ; distinct symbols: %d"%(len(cells),len(need),len({s for s,_ in need})))
from collections import Counter
c=Counter(m for _,m in need)
print("by month:", sorted(c.items()))
json.dump({"need":sorted(list(need)),"cells":cells},open("/workspace/review_scratch/clip_need.json","w"))
