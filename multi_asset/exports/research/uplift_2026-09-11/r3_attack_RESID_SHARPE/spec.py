import numpy as np, json
from scipy.stats import rankdata
R2="/workspace/uplift_2026-09-11/r2_learned"
TG=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)
y4=TG["y4s"]; nA,NW=y4.shape; yrs=TG["yrs"].astype(int)
FE=np.load("/workspace/dlw_v4raw/data/dlw_fea82.npz",allow_pickle=True)
names=[str(x) for x in FE["names"]]
pa=FE["pair_a"].astype(np.int64); ps=FE["pair_s"].astype(np.int64)
X=np.asarray(FE["X"]); ST=np.searchsorted(pa,np.arange(nA+1))
j48=names.index("ret5_sum_48_v") if "ret5_sum_48_v" in names else None
print("feature idx ret5_sum_48_v =",j48,"NF",X.shape[1])
def xz(v):                      # AVERAGE ranks, per the pinned caliber note
    r=rankdata(v); return (r-r.mean())/(r.std()+1e-12)
def ic_k(M,k,rows):
    o=[]
    for i in rows:
        j=i+k
        if j<0 or j>=nA: continue
        s=M[i]; t=y4[j]; m=np.isfinite(s)&np.isfinite(t)
        if m.sum()<50: continue
        o.append(float((xz(s[m])*xz(t[m])).mean()))
    return (float(np.mean(o)),len(o)) if o else (None,0)
ARMS=["RESID_SHARPE_s42","RESID_SHARPE_s2027","CTRL_inservice_f10","RESID_SHARPE_PERM_s42"]
print("\n### OFFSET SPECTRUM k=-3..+3, Spearman(score_i, y4_{i+k}), AVERAGE ranks, F23 rows")
print("%-24s %8s %8s %8s %8s %8s %8s %8s %7s"%("arm","k=-3","k=-2","k=-1","k=0","k=+1","k=+2","k=+3","|k-1/k0|"))
OUT={}
for a in ARMS:
    M=np.load(R2+"/preds/%s.npy"%a)
    rows=[i for i in range(nA) if yrs[i]>=2023 and np.isfinite(M[i]).sum()>=50][::3]
    v={}
    for k in range(-3,4):
        r,n=ic_k(M,k,rows); v[k]=r
    OUT[a]=v
    rat=abs(v[-1]/v[0]) if v[0] and abs(v[0])>1e-9 else float("nan")
    print("%-24s %8.5f %8.5f %8.5f %8.5f %8.5f %8.5f %8.5f %7.2f"%(a,*[v[k] for k in range(-3,4)],rat))
print("\n### per-year k=0 and k=-1 (AVERAGE ranks), RESID_SHARPE both seeds")
for a in ["RESID_SHARPE_s42","RESID_SHARPE_s2027"]:
    M=np.load(R2+"/preds/%s.npy"%a)
    for y in (2023,2024,2025,2026):
        rows=[i for i in range(nA) if yrs[i]==y and np.isfinite(M[i]).sum()>=50][::3]
        a0,_=ic_k(M,0,rows); am,_=ic_k(M,-1,rows)
        print("  %-22s %d  k=0 %+0.5f   k=-1 %+0.5f  n=%d"%(a,y,a0,am,len(rows)))
print("\n### MECHANISM: rank-corr(score, trailing 4h return feature ret5_sum_48_v) and score persistence")
for a in ["RESID_SHARPE_s42","RESID_SHARPE_s2027","CTRL_inservice_f10"]:
    M=np.load(R2+"/preds/%s.npy"%a)
    rows=[i for i in range(nA) if yrs[i]>=2023 and np.isfinite(M[i]).sum()>=50]
    cs=[];ac=[];sp=[];sy=[]
    prev=None; previ=None
    for i in rows[::3]:
        a_,b_=int(ST[i]),int(ST[i+1])
        s=M[i][ps[a_:b_]]; f=X[a_:b_,j48]; t=y4[i][ps[a_:b_]]
        m=np.isfinite(s)&np.isfinite(f)
        if m.sum()>=50: cs.append(float((xz(s[m])*xz(f[m])).mean()))
        mm=np.isfinite(s)&np.isfinite(t)
        if mm.sum()>=50: sp.append(float(np.std(s[mm]))); sy.append(float(np.std(t[mm])))
    # score autocorrelation lag-1 anchor, on common symbols
    for i in rows[:-1]:
        if i+1 not in set(): pass
    prevrow=None
    for i in rows[::3]:
        s0=M[i]; s1=M[i+1] if i+1<nA else None
        if s1 is None: continue
        m=np.isfinite(s0)&np.isfinite(s1)
        if m.sum()>=50: ac.append(float((xz(s0[m])*xz(s1[m])).mean()))
    print("  %-24s corr(score, trailing4h) %+0.4f | score lag-1 autocorr %+0.4f | sigma_pred/sigma_y %.3f"%(
        a,np.mean(cs),np.mean(ac),np.mean(sp)/np.mean(sy)))
json.dump({k:{str(a):b for a,b in v.items()} for k,v in OUT.items()},
          open("/workspace/uplift_2026-09-11/r3_attack_b9646/spectrum.json","w"),indent=1)
