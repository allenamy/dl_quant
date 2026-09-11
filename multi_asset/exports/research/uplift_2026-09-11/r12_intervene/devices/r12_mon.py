"""r12 monitors: (a) 5m intra-anchor book MtM path (I-4), (b) causal sigma_fund regime coordinate,
(c) book realised rank-IC (I-2).  Reads only archived artifacts.  ENV whitelist = EMPTY SET."""
import os, json, time, hashlib
import numpy as np
from scipy.stats import rankdata
_W=["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","W3FIX","MEMBERS_TOPN","FTRIM","FTRIM_TH","FTPOS",
    "CEM_Q","CEM_MODE","BYP_STATE","BYP_Q","BYP_A","UMASK_NPZ","UMASK_SCOPE","COSTB_JSON","SLOW_NPY"]
assert {k:os.environ[k] for k in _W if k in os.environ}=={}
U="/workspace/uplift_2026-09-11"; R=f"{U}/r12_intervene"
A=np.load(f"{R}/dev_ext/probe_artifacts/w10_ablation_series_R12_GATEP_s42.npz",allow_pickle=True)
COLS=[str(c) for c in A["cols"]]; C={k:i for i,k in enumerate(COLS)}
REC=np.asarray(A["d30_n2_c42_rec"],float); W=np.asarray(A["d30_n2_c42_W"],float)
ts=np.round(REC[:,C["ts"]]).astype(np.int64); SYM=[str(s) for s in A["symbols"]]
MT=np.load(f"{U}/r6/out/meta_newprod_v4_x0910.npz",allow_pickle=True)
E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]
mi={int(t):i for i,t in enumerate(E_ts)}; ridx=np.array([mi[int(t)] for t in ts])
PW=np.load(f"{U}/r6/out/wide_panel_4h_v2ext_x0910.npz",allow_pickle=True)
pts=PW["ts"].astype(np.int64); pw={int(t):j for j,t in enumerate(pts)}
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]
assert [str(s) for s in PW["symbols"]]==SYM
nA=len(ts); NW=W.shape[1]
# ---- (b) causal sigma_fund: std of members' 8h-equivalent funding rate, in bp (regime_dash caliber)
sig=np.full(nA,np.nan)
for p in range(nA):
    j=pw[int(ts[p])]; m=members[ridx[p]]
    f=FN[j,m]; iv=IV[j,m]; ok=np.isfinite(f)
    iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0)
    if ok.sum()>50: sig[p]=float(np.std(np.asarray(f[ok],float)*(8.0/np.asarray(iv[ok],float)))*1e4)
# ---- (c) book realised rank-IC (sm vs y4 on members)
ic=np.full(nA,np.nan)
for p in range(nA):
    m=members[ridx[p]]; w=W[p,m]; yy=np.asarray(y4[ridx[p],m],np.float64)
    ok=np.isfinite(yy)&(np.abs(w)>1e-12)
    if ok.sum()>=30: ic[p]=float(np.corrcoef(rankdata(w[ok]),rankdata(yy[ok]))[0,1])
# ---- (a) 5m intra-anchor book MtM path, per unit gross, bps.  Convention VERIFIED in V1b:
#      y4 = prod(1+ret5[E+1 .. E+48]) - 1, median error 1.2e-10.
Z5=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz",allow_pickle=True)
t5=Z5["ts"].astype(np.int64); D5=Z5["data"]; r5={int(t):k for k,t in enumerate(t5)}
assert [str(s) for s in Z5["symbols"]]==SYM and str(Z5["ch"][0])=="ret5"
gt=REC[:,C["gross_total"]]
PATH=np.zeros((nA,48),np.float64)
t0=time.time()
for p in range(nA):
    k0=r5.get(int(ts[p]))
    if k0 is None or k0+49>len(t5): PATH[p]=np.nan; continue
    m=members[ridx[p]]; w=W[p,m]
    nz=np.abs(w)>1e-12
    if not nz.any(): continue
    mm=m[nz]; ww=w[nz]
    blk=np.nan_to_num(np.asarray(D5[k0+1:k0+49,mm,0],np.float64))
    cp=np.cumprod(1.0+blk,0)-1.0                    # (48, n) running simple return per name
    PATH[p]=(cp@ww)*1e4/max(gt[p],1e-12)            # bps per unit gross
    if p%2000==0: print("path",p,"/",nA,round(time.time()-t0,1),"s",flush=True)
end=PATH[:,47]; ref=REC[:,C["pnl"]]/gt               # file-caliber price pnl per unit gross (uses sm = W)
ok=np.isfinite(end)&np.isfinite(ref)
V={"endpoint_vs_pnl_over_gross":{"n":int(ok.sum()),"maxabs":float(np.max(np.abs(end[ok]-ref[ok]))),
   "median_abs":float(np.median(np.abs(end[ok]-ref[ok]))),"corr":float(np.corrcoef(end[ok],ref[ok])[0,1])}}
ref_ex=REC[:,C["pnl_ex"]]/gt
V["endpoint_vs_pnl_ex_over_gross"]={"maxabs":float(np.max(np.abs(end[ok]-ref_ex[ok]))),
   "median_abs":float(np.median(np.abs(end[ok]-ref_ex[ok]))),"corr":float(np.corrcoef(end[ok],ref_ex[ok])[0,1])}
V["sigma_fund_bp"]={"finite":int(np.isfinite(sig).sum()),
   "pct":{q:float(np.nanpercentile(sig,q)) for q in (5,33.333,50,66.667,95)},
   "by_year":{}}
yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
for y in sorted(set(yrs.tolist())):
    V["sigma_fund_bp"]["by_year"][str(y)]={"mean":float(np.nanmean(sig[yrs==y])),"median":float(np.nanmedian(sig[yrs==y]))}
V["book_ic"]={"mean":float(np.nanmean(ic)),"finite":int(np.isfinite(ic).sum())}
print(json.dumps(V,indent=1),flush=True)
np.savez_compressed(f"{R}/out/monitors.npz",ts=ts,ridx=ridx,sig=sig,ic=ic,path5m=PATH.astype(np.float32),
                    gross_total=gt,cols=np.array(COLS),rec=REC)
json.dump(V,open(f"{R}/out/MONITORS.json","w"),indent=1)
print("MON_DONE",round(time.time()-t0,1),"s")
