import numpy as np, calendar, os, glob
from scipy.stats import rankdata
APY=2190
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
SPAN={"F23":(T(2023,1,1),T(2026,8,10,20)+1),"F24":(T(2024,1,1),T(2026,8,10,20)+1),
      "y2026":(T(2026,1,1),T(2026,8,10,20)+1)}
U="/workspace/uplift_2026-09-11"; W=U+"/r3_attack_b9646"
A={}
def ld(k,p):
    if not os.path.exists(p): return
    Z=np.load(p,allow_pickle=True); kk="rec" if "rec" in Z.files else "d30_n2_c42_rec"
    R=np.asarray(Z[kk],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    gt=np.maximum(R[:,ix["gross_total"]],1e-12)
    A[k]=dict(ts=np.round(R[:,ix["ts"]]).astype(np.int64),g=R[:,ix["net_ex"]]/gt,
              p=R[:,ix["pnl_ex"]]/gt,tn=R[:,ix["turnover"]],gt=gt,
              warm=np.abs(R[:,ix["w3_rev24"]])>=1e-9)
ld("ARM",U+"/r3_integrate/out/RS_RESID_SHARPE_s42_STD.npz")
for f in sorted(glob.glob(W+"/out/NULL_*.npz")): ld(os.path.basename(f)[5:-4],f)
print("%-12s %-7s %6s %9s %9s %8s %9s"%("arm","win","n","pnl_ex","net_ex","SR","turn/gross"))
for k in ["ARM","STATIC","DYNRESID","SHIFT101","SHIFT503"]:
    if k not in A: continue
    for w in ["F23","F24","y2026"]:
        d=A[k]; lo,hi=SPAN[w]; m=(d["ts"]>=lo)&(d["ts"]<hi)&np.isfinite(d["g"])&(~d["warm"])
        if m.sum()<30: continue
        v=d["g"][m]
        print("%-12s %-7s %6d %+9.4f %+9.4f %+8.3f %9.5f"%(k,w,m.sum(),d["p"][m].mean(),v.mean(),
              v.mean()/v.std(ddof=1)*np.sqrt(APY),d["tn"][m].mean()/d["gt"][m].mean()))
    print()
print("### SCORE AUTOCORRELATION DECAY (xsec Spearman between anchor i and i+L)")
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True); yrs=TG["yrs"].astype(int)
def xz(v): r=rankdata(v); return (r-r.mean())/(r.std()+1e-12)
for nm in ("RESID_SHARPE_s42","CTRL_inservice_f10"):
    M=np.load(U+"/r2_learned/preds/%s.npy"%nm); nA=M.shape[0]
    rows=[i for i in range(nA) if yrs[i]>=2023 and np.isfinite(M[i]).sum()>=50]
    out=[]
    for L in (1,6,42,101,503,1009):
        o=[]
        for i in rows[::11]:
            if i+L>=nA: continue
            a,b=M[i],M[i+L]; m=np.isfinite(a)&np.isfinite(b)
            if m.sum()>=50: o.append(float((xz(a[m])*xz(b[m])).mean()))
        out.append((L,np.mean(o) if o else float("nan")))
    print("  %-22s "%nm + "  ".join("L=%-5d %+0.4f"%(L,v) for L,v in out))
