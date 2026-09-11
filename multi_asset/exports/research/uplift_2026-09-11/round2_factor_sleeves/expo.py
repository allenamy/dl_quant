"""(1) value-IC vs rank-IC for every family (the 'rank_ic_positive_value_ic_zero' trap).
(2) The book's OWN unintentional factor exposure: gross-normalised position-weighted mean factor rank
    per anchor from A0's W matrix, and whether that exposure is compensated."""
import numpy as np, json
R="/workspace/uplift_2026-09-11/r2_factor"; FT=R+"/feat"
P=np.load(R+"/dev/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz",allow_pickle=True)
Y4=np.asarray(P["Y4"],np.float64); pts=P["ts"].astype(np.int64)
B=np.load(FT+"/_B.npy"); FAMS=json.load(open(R+"/feat_manifest.json"))["families"]
A=np.load("/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz",allow_pickle=True)
cols=[str(x) for x in A["cols"]]; C={n:i for i,n in enumerate(cols)}
rec=A["d30_n2_c42_rec"]; W=A["d30_n2_c42_W"]; bts=rec[:,C["ts"]].astype(np.int64)
row={int(t):j for j,t in enumerate(pts)}
ix=np.array([row.get(int(t),-1) for t in bts])
assert (ix>=0).all(), "book ts not all in panel"
print("A0 W shape",W.shape,"aligned rows",len(ix))
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
gross=np.abs(W).sum(axis=1)
print("mean gross", gross.mean(), "zero-gross rows", int((gross<=0).sum()))
out={}
for fam in FAMS:
    F=np.where(B,np.load(FT+"/"+fam+".npy").astype(np.float64),np.nan)
    Z=rz(F)
    # value-IC: per-anchor Pearson of rank(feature) with RAW forward return
    v=[]
    for i in range(Z.shape[0]):
        a=Z[i]; b=Y4[i]; ok=np.isfinite(a)&np.isfinite(b)&B[i]
        if ok.sum()<30: continue
        x=a[ok]-a[ok].mean(); y=b[ok]-b[ok].mean()
        d=np.sqrt((x*x).sum()*(y*y).sum())
        if d>0: v.append(float((x*y).sum()/d))
    v=np.array(v); vic=float(v.mean()); vict=float(v.mean()/v.std(ddof=1)*np.sqrt(len(v)))
    # decile mean forward return (top minus bottom), in bps, VALUE not rank
    tb=[]
    for i in range(Z.shape[0]):
        a=Z[i]; b=Y4[i]; ok=np.isfinite(a)&np.isfinite(b)&B[i]
        if ok.sum()<50: continue
        q=np.quantile(a[ok],[0.1,0.9])
        hi=b[ok][a[ok]>=q[1]]; lo=b[ok][a[ok]<=q[0]]
        if len(hi)>2 and len(lo)>2: tb.append(float(hi.mean()-lo.mean())*1e4)
    tb=np.array(tb)
    # book exposure: gross-normalised position-weighted mean feature rank
    Zb=Z[ix]
    num=np.nansum(np.where(np.isfinite(Zb),W*Zb,0.0),axis=1)
    expo=np.where(gross>0,num/np.maximum(gross,1e-12),np.nan)
    out[fam]=dict(value_ic=vic,value_ic_t=vict,d10_spread_bps=float(tb.mean()),
                  d10_t=float(tb.mean()/tb.std(ddof=1)*np.sqrt(len(tb))),
                  book_expo_mean=float(np.nanmean(expo)),book_expo_sd=float(np.nanstd(expo)),
                  book_expo_t=float(np.nanmean(expo)/np.nanstd(expo)*np.sqrt(np.isfinite(expo).sum())))
    print("%-11s valueIC %+.5f (t %+6.2f)  D10-D1 %+7.2f bps (t %+6.2f) | book exposure %+.4f (sd %.4f, t %+7.1f)"%(
        fam,vic,vict,out[fam]["d10_spread_bps"],out[fam]["d10_t"],out[fam]["book_expo_mean"],
        out[fam]["book_expo_sd"],out[fam]["book_expo_t"]),flush=True)
json.dump(out,open(R+"/value_ic_and_exposure.json","w"),indent=1)
