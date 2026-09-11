"""Methodology (e): forward vs backward cross-sectional rank-IC at k = 0, -1, -2.
SIGNAL LAYER, not the book layer. Y4[i] = forward return of bar (i, i+1]; the book entering at
anchor i earns Y4[i]. So k=0 is the forward IC. k=-1 uses Y4[i-1] (= the already-closed bar
(i-1,i]), k=-2 uses Y4[i-2]. A feature whose |IC(k=-1)| dwarfs |IC(k=0)| has no forward
predictive power (this killed round 1's TBF at 30x)."""
import numpy as np, json, sys
R="/workspace/uplift_2026-09-11/r2_factor"; FT=R+"/feat"
P=np.load(R+"/dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
Y4=np.asarray(P["Y4"],np.float64); B=np.load(FT+"/_B.npy"); ZF=np.load(FT+"/_ZFUND.npy").astype(np.float64)
FAMS=json.load(open(R+"/feat_manifest.json"))["families"]
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def orth(Z):
    Rr=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        Rr[i][ok]=y-b*x
    return Rr
def ric(Z,k):
    """mean per-anchor Spearman between Z[i] and Y4[i+k] (k<=0 means a PAST bar)."""
    n=Z.shape[0]; out=[]
    for i in range(n):
        j=i+k
        if j<0 or j>=n: continue
        a=Z[i]; b=Y4[j]
        ok=np.isfinite(a)&np.isfinite(b)&B[i]
        if ok.sum()<30: continue
        x=a[ok]; y=b[ok]
        rx=np.argsort(np.argsort(x)).astype(float); ry=np.argsort(np.argsort(y)).astype(float)
        rx-=rx.mean(); ry-=ry.mean()
        d=np.sqrt((rx*rx).sum()*(ry*ry).sum())
        if d>0: out.append(float((rx*ry).sum()/d))
    o=np.array(out); return float(o.mean()), float(o.mean()/o.std(ddof=1)*np.sqrt(len(o))) if len(o)>2 else float("nan"), len(o)
rows=[]
for fam in FAMS:
    F=np.where(B,np.load(FT+"/"+fam+".npy").astype(np.float64),np.nan)
    Z=rz(F); ZO=orth(Z)
    r={}
    for tagz,Zx in (("raw",Z),("orth",ZO)):
        for k in (0,-1,-2):
            m,t,n=ric(Zx,k); r["%s_k%d"%(tagz,k)]=m; r["%s_k%d_t"%(tagz,k)]=t
    r["fam"]=fam; rows.append(r)
    print("%-11s raw k0 %+.5f (t %+6.2f)  k-1 %+.5f  k-2 %+.5f | orth k0 %+.5f (t %+6.2f)  k-1 %+.5f  k-2 %+.5f  ratio|k-1/k0| %6.2f"%(
        fam,r["raw_k0"],r["raw_k0_t"],r["raw_k-1"],r["raw_k-2"],r["orth_k0"],r["orth_k0_t"],r["orth_k-1"],r["orth_k-2"],
        abs(r["orth_k-1"])/max(abs(r["orth_k0"]),1e-12)),flush=True)
json.dump(rows,open(R+"/ic_table.json","w"),indent=1)
