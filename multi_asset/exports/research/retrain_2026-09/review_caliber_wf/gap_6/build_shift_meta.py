"""GAP#6: build y4 override metas with the tradable holding window rows [E+6, E+53] (= (E+25m, E+4h+25m]),
Σ (sum of 5m simple returns) and Π (prod(1+r)-1) variants; same construction as refute_C6_2/build_alt_meta.py
(rows [E+1,E+48]) and pod_alpha_decay.py y4s_shift(E,k=5) (lo=E+1+k, hi=E+48+1+k)."""
import numpy as np, time, sys
ROOT="/workspace/review_scratch/gap_6/altrun"; t0=time.time()
Z=np.load("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True); CTS=Z["ts"].astype(np.int64); D=Z["data"]
r5=D[:,:,0].astype(np.float32); fin=np.isfinite(r5); r5z=np.where(fin,r5,0).astype(np.float64); NW=r5.shape[1]; del D
CS_r=np.concatenate([np.zeros((1,NW)),np.cumsum(r5z,0)]); CS_L=np.concatenate([np.zeros((1,NW)),np.cumsum(np.log1p(r5z),0)]); CS_f=np.concatenate([np.zeros((1,NW),np.int32),np.cumsum(fin,0,dtype=np.int32)])
print("cumsums",round(time.time()-t0,1),"s",flush=True)
MT=np.load("/workspace/data/wide_fea_v2ext_meta.npz",allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]; qvk=MT["qvk"]; names=MT["names"]
print("meta keys", MT.files)
row={int(t):k for k,t in enumerate(CTS)}; r=np.array([row[int(t)] for t in E_ts]); assert (r+54<=len(CTS)).all()
K=5  # +25min shift: rows [E+1+K, E+48+K] = [E+6, E+53]
def win(lo,hi):
    n=CS_f[hi]-CS_f[lo]
    s=(CS_r[hi]-CS_r[lo]).astype(np.float32); s[n<46]=np.nan
    p=np.expm1(CS_L[hi]-CS_L[lo]).astype(np.float32); p[n<46]=np.nan
    return s,p,n
newsum,newprod,n0=win(r+1,r+49)          # (E, E+4h]      rows [E+1,E+48]  (refute_C6_2 'new*')
shiftsum,shiftprod,n5=win(r+1+K,r+49+K)  # (E+25m,E+4h+25m] rows [E+6,E+53] (this gap)
assert (r+1+K==r+6).all() and (r+49+K-1==r+53).all()
print(f"window check: first row E+{1+K}, last row E+{49+K-1}  (5m grid, 48 rows)")
# parity with refute_C6_2 metas (bitwise): proves same row mapping / same construction
for nm,X,p in (("newsum",newsum,f"/workspace/review_scratch/refute_C6_2/altrun/meta_newsum.npz"),("newprod",newprod,f"/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz")):
    Y=np.load(p,allow_pickle=True)["y4"]; b=np.isfinite(X)&np.isfinite(Y)
    print(f"PARITY {nm} vs refute_C6_2 meta_{nm}: cells {b.sum()} exact_eq {(X[b]==Y[b]).mean():.6f} max|Δ| {np.max(np.abs(X[b]-Y[b])):.2e} nan-mismatch {(np.isfinite(X)^np.isfinite(Y)).sum()}")
# parity with dlw y4s (Π (E,E+4h]) on common anchors
DT=np.load("/workspace/data/dlw_targets.npz",allow_pickle=True); dts=DT["E_ts"].astype(np.int64); y4s=DT["y4s"]; ER=DT["E_row"].astype(np.int64)
dm={int(t):k for k,t in enumerate(dts)}; a=[];bb=[]
for k,t in enumerate(E_ts):
    j=dm.get(int(t))
    if j is not None: a.append(k); bb.append(j)
a=np.array(a); bb=np.array(bb)
b=np.isfinite(newprod[a])&np.isfinite(y4s[bb]); print(f"PARITY newprod vs dlw y4s: common {len(a)} cells {b.sum()} exact_eq {(newprod[a][b]==y4s[bb][b]).mean():.6f} nan-mismatch {(np.isfinite(newprod[a])^np.isfinite(y4s[bb])).sum()}")
# parity with pod_alpha_decay.py y4s_shift(E,5) formula evaluated with dlw E_row (independent row source)
lo=ER+1+K; hi=ER+48+1+K; ok=hi<=len(CTS)
yshift_ad=np.full((len(ER),NW),np.nan,np.float32); n_ad=CS_f[hi[ok]]-CS_f[lo[ok]]; tmp=np.expm1(CS_L[hi[ok]]-CS_L[lo[ok]]).astype(np.float32); tmp[n_ad<46]=np.nan; yshift_ad[ok]=tmp
b=np.isfinite(shiftprod[a])&np.isfinite(yshift_ad[bb]); print(f"PARITY shiftprod vs pod_alpha_decay y4s_shift(E_row,5): common {len(a)} cells {b.sum()} exact_eq {(shiftprod[a][b]==yshift_ad[bb][b]).mean():.6f} nan-mismatch {(np.isfinite(shiftprod[a])^np.isfinite(yshift_ad[bb])).sum()}")
yrs=np.array([time.gmtime(int(t)).tm_year for t in E_ts])
for yv in (2022,2023,2024,2025,2026):
    m=yrs==yv; b=m[:,None]&np.isfinite(newsum)&np.isfinite(shiftsum)&np.isfinite(newprod)&np.isfinite(shiftprod)
    print(f"{yv}: cells {b.sum()} mean(shiftsum-newsum)={np.mean(shiftsum[b]-newsum[b])*1e4:+.3f} bps mean|Δ|={np.mean(np.abs(shiftsum[b]-newsum[b]))*1e4:.2f}  mean(shiftprod-newprod)={np.mean(shiftprod[b]-newprod[b])*1e4:+.3f} bps mean|Δ|={np.mean(np.abs(shiftprod[b]-newprod[b]))*1e4:.2f}  nan-mismatch(new vs shift) {((np.isfinite(newprod)^np.isfinite(shiftprod))&m[:,None]).sum()}")
import os; os.makedirs(ROOT,exist_ok=True)
np.savez(f"{ROOT}/meta_shiftsum.npz",E_ts=E_ts,members=members,y4=shiftsum,qvk=qvk,names=names)
np.savez(f"{ROOT}/meta_shiftprod.npz",E_ts=E_ts,members=members,y4=shiftprod,qvk=qvk,names=names)
import hashlib
for f in ("meta_shiftsum.npz","meta_shiftprod.npz"): print("sha256",f,hashlib.sha256(open(f"{ROOT}/{f}","rb").read()).hexdigest())
print("saved",round(time.time()-t0,1),"s")
