import numpy as np, sys, time, calendar
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); syms=[str(s) for s in Z["symbols"]]
T=calendar.timegm((2022,6,7,20,0,0)); E=int(np.where(CTS==T)[0][0])
for s in ["ETHUSDT"]+[x for x in ["GALUSDT","GMTUSDT","APEUSDT"] if x in syms]: pass
F=np.load("/workspace/review_scratch/clip_flags.npz",allow_pickle=True)
has=F["has"][int(np.where(F["E_ts"].astype(np.int64)==T)[0][0])]
for j in np.where(has)[0]:
    r=Z["data"][E+1:E+49,j,0].astype(np.float32)
    print("%-14s n_finite=%2d  min=%.4f max=%.4f  n_clip_lo=%d n_clip_hi=%d  prod-1=%+.4f  sum=%+.4f"%(
        syms[j],int(np.isfinite(r).sum()),np.nanmin(r),np.nanmax(r),
        int((r==np.float32(np.float16(-0.3))).sum()),int((r==np.float32(np.float16(0.3))).sum()),
        float(np.prod(1+np.nan_to_num(r))-1),float(np.nansum(r))))
