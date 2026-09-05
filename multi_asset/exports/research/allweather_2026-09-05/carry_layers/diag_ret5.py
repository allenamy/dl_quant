import numpy as np, time, io, zipfile, os
t0=time.time(); F5="/workspace/data/dlnative_5m_wide829_f16_ext.npz"
z=zipfile.ZipFile(F5); ts5=np.load(io.BytesIO(z.read("ts.npy"))).astype(np.int64)
D=np.load(F5)["data"]; r16=D[:,:,0]; del D
np.save("data/ret5_f16.npy", r16); np.save("data/ts5.npy", ts5); print("cached ret5_f16.npy", r16.shape, time.time()-t0, flush=True)
ret5=r16.astype(np.float32)
MT=np.load("/workspace/review_scratch/health_check/dev/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True); E=MT["E_ts"].astype(np.int64); y4=MT["y4"]
MP=np.load("/workspace/review_scratch/health_check/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True); y4p=MP["y4"]
row5={int(t):r for r,t in enumerate(ts5)}
rng=np.random.default_rng(0); pairs=[]
for i in rng.choice(np.arange(500,len(E)-100),300,replace=False):
    r0=row5.get(int(E[i]))
    if r0 is None: continue
    for k in rng.choice(829,4,replace=False):
        seg=ret5[r0-2:r0+52,k]
        if np.isfinite(y4[i,k]) and np.isfinite(seg).all(): pairs.append((i,k,float(y4[i,k]),float(y4p[i,k]),seg.copy()))
print("n pairs",len(pairs))
Y=np.array([p[2] for p in pairs]); Yp=np.array([p[3] for p in pairs]); SEG=np.stack([p[4] for p in pairs])  # cols: offsets -2..51 relative to r0
for off in range(-2,5):
    s=SEG[:,off+2:off+2+48].sum(1); pr=np.prod(1+SEG[:,off+2:off+2+48],1)-1
    print(f"offset {off:+d}: median|y4-Σ| {np.median(np.abs(Y-s)):.3e} corr {np.corrcoef(Y,s)[0,1]:.4f} | median|y4p-Π| {np.median(np.abs(Yp-pr)):.3e} corr {np.corrcoef(Yp,pr)[0,1]:.4f} | scale ratio med(y4/Σ) {np.median(Y/np.where(np.abs(s)>1e-6,s,np.nan)):.3f}")
print("sample y4, y4p, Σ(+1..+48), Σ(0..47):", [(round(Y[q],5), round(Yp[q],5), round(SEG[q,3:51].sum(),5), round(SEG[q,2:50].sum(),5)) for q in range(5)])
print("ret5 stats: std", np.nanstd(ret5[::50]), "abs mean", np.nanmean(np.abs(ret5[::50])), "max", np.nanmax(np.abs(ret5[::50])), "finite share", np.isfinite(ret5).mean())
print("DIAG_DONE", time.time()-t0)
