import numpy as np, calendar, time, json
from scipy.stats import rankdata, spearmanr
W="/dev/shm/news2_2026-09-23"
leg=np.load(W+"/work/legs.npz"); a=leg["E_ts"].astype(np.int64); WL=leg["WL"]; ready=leg["ready"]; KZ=leg["KZ"]
F=np.load(W+"/work/NEWS_FEATURES.npz"); off=F["off"]; mm=F["m"].astype(np.int64)
K=np.load(W+"/work/king/KING_OOF.npz")["P"]
def ts(s): return calendar.timegm(time.strptime(s,"%Y-%m-%dT%H:%M:%SZ"))
SEG={"2023H2":("2023-06-30T04:00:00Z","2023-12-31T20:00:00Z"),"2024":("2024-01-01T00:00:00Z","2024-12-31T20:00:00Z"),
     "2025":("2025-01-01T00:00:00Z","2025-12-31T20:00:00Z"),"pre2026":("2023-06-30T04:00:00Z","2025-12-31T20:00:00Z"),
     "2026":("2026-01-01T00:00:00Z","2026-08-31T00:00:00Z")}
print("=== A. WL[0]==0 (F10 score gets ZERO weight in its own training utility) ===")
for s,(lo,hi) in SEG.items():
    m=(a>=ts(lo))&(a<=ts(hi))&ready
    w=WL[m]
    print("%-8s n=%5d  frac(WL0<=1e-9)=%.4f  frac(WL1<=1e-9,rev24)=%.4f  frac(WL2<=1e-9,fund)=%.4f  WL0_mean=%.4f WL1_mean=%.4f WL2_mean=%.4f" % (
        s,m.sum(),(w[:,0]<=1e-9).mean(),(w[:,1]<=1e-9).mean(),(w[:,2]<=1e-9).mean(),w[:,0].mean(),w[:,1].mean(),w[:,2].mean()))
print()
print("=== B. rho(F10 production rank, King rank) per anchor, and rank-IC between them ===")
for sd in (42,2027):
    P=np.load(W+f"/work/f10_s{sd}/F10_OOF.npz")["P"]
    for s in ("pre2026","2026"):
        lo,hi=SEG[s]; rows=np.flatnonzero((a>=ts(lo))&(a<=ts(hi))&ready)
        rr=[]
        for i in rows:
            mmm=mm[off[i]:off[i+1]]
            p=P[i][mmm]; k=KZ[i][mmm]; ok=np.isfinite(p)&np.isfinite(k)
            if ok.sum()<20: continue
            zf=rankdata(p[ok])/max(ok.sum()-1,1)-.5
            c=spearmanr(zf,k[ok]).statistic
            if np.isfinite(c): rr.append(float(c))
        rr=np.array(rr)
        print("s%-5d %-8s n=%5d  rho_mean=%+.4f  sd=%.4f  p10=%+.3f p90=%+.3f  frac(rho>0)=%.3f" % (sd,s,len(rr),rr.mean(),rr.std(),np.percentile(rr,10),np.percentile(rr,90),(rr>0).mean()))
