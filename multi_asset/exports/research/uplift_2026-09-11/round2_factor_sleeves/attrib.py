"""Is any factor exposure UNCOMPENSATED? For each family:
  factor return f_t   = return of a unit-gross dollar-neutral portfolio w ~ rank(feature) demeaned,
                        realised over the bar the book holds, i.e. dot(w_t, Y4_t)/sum|w_t|, in bps.
  book exposure  e_t  = dot(W_t, rank(feature)_t)/sum|W_t|        (gross-normalised tilt)
  attributed P&L a_t  = e_t * f_t * (sum|w|-normalisation already in f) -> bps per anchor per gross
An exposure is COMPENSATED if mean(f) has the same sign as mean(e) (the book is tilted toward the paid
side); UNCOMPENSATED if mean(e) is significant while mean(f) is not, or has the opposite sign."""
import numpy as np, json, sys
R="/workspace/uplift_2026-09-11/r2_factor"; FT=R+"/feat"
P=np.load(R+"/dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
Y4=np.asarray(P["Y4"],np.float64); pts=P["ts"].astype(np.int64); B=np.load(FT+"/_B.npy")
A=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
cols=[str(x) for x in A["cols"]]; C={n:i for i,n in enumerate(cols)}
rec=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]; bts=rec[:,C["ts"]].astype(np.int64)
row={int(t):j for j,t in enumerate(pts)}; ix=np.array([row[int(t)] for t in bts])
gross=np.abs(W).sum(axis=1)
gbook=rec[:,C["net_ex"]]/rec[:,C["gross_total"]]
nb=len(bts); cut=nb-121   # full22 = all but the last 121 anchors
FAMS=json.load(open(R+"/feat_manifest.json"))["families"]
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
def tstat(x):
    x=x[np.isfinite(x)]
    return float(x.mean()), float(x.mean()/x.std(ddof=1)*np.sqrt(len(x)))
print("%-11s %10s %7s | %10s %7s | %11s %7s %8s"%(
  "family","factor_f","t","book_e","t","attrib_bps","t","%of_net"))
out={}
netmean=float(np.nanmean(gbook[:cut]))
for fam in FAMS:
    Z=rz(np.where(B,np.load(FT+"/"+fam+".npy").astype(np.float64),np.nan))
    w=np.where(np.isfinite(Z),Z,0.0)
    w=w-np.where(np.isfinite(Z),1,0)*(w.sum(axis=1,keepdims=True)/np.maximum(np.isfinite(Z).sum(axis=1,keepdims=True),1))
    w=np.where(np.isfinite(Z),w,0.0)
    gw=np.abs(w).sum(axis=1)
    f=np.where(gw>0,np.nansum(np.where(np.isfinite(Y4),w*Y4,0.0),axis=1)/np.maximum(gw,1e-12),np.nan)*1e4
    Zb=Z[ix]; e=np.where(gross>0,np.nansum(np.where(np.isfinite(Zb),W*Zb,0.0),axis=1)/np.maximum(gross,1e-12),np.nan)
    fb=f[ix]
    # attributed P&L: the book's tilt e_t scaled onto the factor portfolio's realised return.
    # e_t is a rank-units tilt; the factor portfolio's own tilt is mean|rank| = 0.25, so scale by e/0.25.
    a=(e/0.25)*fb
    mf,tf=tstat(f[:cut] if len(f)==len(pts) else fb[:cut]); me,te=tstat(e[:cut]); ma,ta=tstat(a[:cut])
    out[fam]=dict(f=mf,f_t=tf,e=me,e_t=te,attrib=ma,attrib_t=ta,pct=100*ma/netmean)
    print("%-11s %+10.4f %+7.2f | %+10.4f %+7.1f | %+11.4f %+7.2f %+8.1f"%(fam,mf,tf,me,te,ma,ta,100*ma/netmean),flush=True)
print("\nA0 net (full22) = %+.4f bps/anchor/gross"%netmean)
json.dump(out,open(R+"/attribution.json","w"),indent=1)
