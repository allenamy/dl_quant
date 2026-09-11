"""P6 step 1: can a PRODUCER-SHAPED Amihud reproduce the panel column f_amihud_24h bit-for-bit?
Reference recipe = pod_panel_ext.py L20-54 VERBATIM (cumsum-from-t0 path), run on the PINNED v4 cube
(dlnative_5m_wide829_f16_holefix2.npz).  Producer-shaped = direct 288-bar window sums over exactly the two
channels shadow_loop_v3.py wstat() can see (ch0 ret5, ch3 log_qv), in the two accumulator precisions the
producer could plausibly use.  Also prices the round-2 shape (mean-of-log-qv) and the RESEARCH column
(wide_panel_4h_v2ext.npz, built from the FORBIDDEN _ext cube) against the same reference.
"""
import numpy as np, json, sys
from scipy.stats import rankdata
sys.path.insert(0,"/workspace")
from zload import zload
OUT={}
CUBE="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
Z=zload(CUBE, allow_pickle=True)
CTS=Z["ts"].astype(np.int64); CD=Z["data"]; syms=[str(s) for s in Z["symbols"]]
NW=len(syms); TT=CD.shape[0]
print("cube",TT,NW,flush=True)
# --- grid EXACTLY as pod_panel_ext.py ---
grid=np.where(CTS%14400==0)[0]; grid=grid[(grid>=8640)&(grid+288<=TT)]
E=grid; print("anchors",len(E),flush=True)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts_ext=PW["ts"].astype(np.int64)
OUT["axis"]={"n_holefix2":int(len(E)),"n_v2ext":int(len(ts_ext)),
             "ts_equal":bool(len(E)==len(ts_ext) and np.array_equal(CTS[E],ts_ext))}
print("axis",OUT["axis"],flush=True)
# --- channels ---
r5=CD[:,:,0].astype(np.float32)
qv=np.where(np.isfinite(CD[:,:,3]),CD[:,:,3],np.nan).astype(np.float32)
del CD, Z
def cs(x):
    xz=np.where(np.isfinite(x),x,0).astype(np.float64)
    return np.concatenate([np.zeros((1,NW)),np.cumsum(xz,0)])
CS_r=cs(r5); CS_q=cs(np.expm1(np.clip(qv,0,30)))
def wsum(CSx,w): return (CSx[E]-CSx[E-w]).astype(np.float32)
rev24_P=wsum(CS_r,288); qv24_P=wsum(CS_q,288)
with np.errstate(divide="ignore",invalid="ignore"):
    AM_P=np.where(qv24_P>0,np.abs(rev24_P)/qv24_P*1e6,np.nan).astype(np.float32)
del CS_r,CS_q
# --- producer-shaped: direct 288-bar window, only ch0/ch3, two accumulator precisions ---
rev64=np.empty((len(E),NW),np.float64); qvs64=np.empty((len(E),NW),np.float64)
rev32=np.empty((len(E),NW),np.float32); qvs32=np.empty((len(E),NW),np.float32)
lqm=np.empty((len(E),NW),np.float32)
for k,e in enumerate(E):
    s0=slice(e-288,e)
    a=r5[s0]; fa=np.isfinite(a); az=np.where(fa,a,0)
    b=qv[s0]; fb=np.isfinite(b); bz=np.where(fb,np.expm1(np.clip(b,0,30)),0).astype(np.float32)
    rev64[k]=az.astype(np.float64).sum(0); qvs64[k]=bz.astype(np.float64).sum(0)
    rev32[k]=az.sum(0);                    qvs32[k]=bz.sum(0)
    lqm[k]=np.where(fb,b,0).sum(0)/np.maximum(fb.sum(0),1)
def amih(rev,q):
    rev=rev.astype(np.float32); q=q.astype(np.float32)
    with np.errstate(divide="ignore",invalid="ignore"):
        return np.where(q>0,np.abs(rev)/q*1e6,np.nan).astype(np.float32)
AM_Q64=amih(rev64,qvs64); AM_Q32=amih(rev32,qvs32)
# round-2 shape: producer has only MEAN of log_qv (wstat kind="mean") -> expm1 of the mean, x288
with np.errstate(divide="ignore",invalid="ignore"):
    qJ=(288.0*np.expm1(np.clip(lqm,0,30))).astype(np.float32)
    AM_R2=np.where(qJ>0,np.abs(rev32)/qJ*1e6,np.nan).astype(np.float32)
AM_X=np.asarray(PW["f_amihud_24h"],np.float32)   # research column (ext cube lineage)
def cmp(name,A,B):
    """A vs reference B"""
    na=np.isnan(A); nb=np.isnan(B)
    both=(~na)&(~nb)
    r={"nan_pattern_equal":bool(np.array_equal(na,nb)),
       "n_both_finite":int(both.sum()),
       "n_A_finite":int((~na).sum()),"n_B_finite":int((~nb).sum())}
    a=A[both]; b=B[both]
    r["bitwise_equal_frac"]=float((a==b).mean())
    d=np.abs(a.astype(np.float64)-b.astype(np.float64))
    rel=d/np.maximum(np.abs(b.astype(np.float64)),1e-30)
    r["max_abs_rel_diff"]=float(rel.max()); r["p999_rel_diff"]=float(np.quantile(rel,0.999))
    # per-anchor spearman on the member-ish set (all finite in the row)
    sp=[]
    for i in range(A.shape[0]):
        ok=(~np.isnan(A[i]))&(~np.isnan(B[i]))
        if ok.sum()<10: continue
        x=rankdata(A[i][ok]); y=rankdata(B[i][ok])
        sx=x.std(); sy=y.std()
        if sx<1e-12 or sy<1e-12: continue
        sp.append(float(((x-x.mean())*(y-y.mean())).mean()/(sx*sy)))
    sp=np.array(sp)
    r["spearman_mean"]=float(sp.mean()); r["spearman_min"]=float(sp.min()); r["spearman_p01"]=float(np.quantile(sp,0.01))
    r["n_anchors_scored"]=int(len(sp))
    print(name,json.dumps(r),flush=True)
    OUT[name]=r
cmp("Q64_direct_float64_vs_PANEL",AM_Q64,AM_P)
cmp("Q32_direct_float32_vs_PANEL",AM_Q32,AM_P)
cmp("R2_meanlogqv_vs_PANEL",AM_R2,AM_P)
cmp("RESEARCH_extcube_vs_PANEL_holefix2",AM_X,AM_P)
np.savez("/workspace/uplift_2026-09-11/p6/AM_variants.npz",ts=CTS[E],symbols=np.array(syms),
         AM_P=AM_P,AM_Q64=AM_Q64,AM_Q32=AM_Q32,AM_R2=AM_R2,AM_X=AM_X)
json.dump(OUT,open("/workspace/uplift_2026-09-11/p6/P6_PARITY.json","w"),indent=1)
print("DONE",flush=True)
