"""How much does pod_merge_cache_ext.py L27  np.clip(pct_change, -0.3, 0.3)  actually bind,
and how much of OUR replay book sits on the affected cells?  Read-only, CPU only."""
import numpy as np, json, time, calendar, sys
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); CD=Z["data"]; syms=[str(s) for s in Z["symbols"]]
r5=CD[:,:,0].astype(np.float32); fin=np.isfinite(r5)
HI=np.float32(np.float16(0.3)); LO=np.float32(np.float16(-0.3))
clip_hi=(r5==HI)&fin; clip_lo=(r5==LO)&fin; clipped=clip_hi|clip_lo
yr=np.array([time.gmtime(int(t)).tm_year for t in CTS])
print("cache %s rows x %d syms; ch0 finite %.3f%%"%(CD.shape[:2],len(syms),100*fin.mean()))
print("float16(0.3)=%.10f  float16(-0.3)=%.10f"%(HI,LO))
print("\n== clipped 5m bars by year ==")
print("%6s %14s %14s %10s %10s %10s"%("year","finite bars","clipped","share","hi(+30%)","lo(-30%)"))
for y in sorted(set(yr.tolist())):
    m=yr==y; f=int(fin[m].sum()); c=int(clipped[m].sum())
    print("%6d %14d %14d %9.4f%% %10d %10d"%(y,f,c,100*c/max(f,1),int(clip_hi[m].sum()),int(clip_lo[m].sum())))
f=int(fin.sum()); c=int(clipped.sum())
print("%6s %14d %14d %9.4f%% %10d %10d"%("ALL",f,c,100*c/f,int(clip_hi.sum()),int(clip_lo.sum())))
# ---- per 4h anchor, rows [E+1, E+48] (the y4s window) ----
CSC=np.concatenate([np.zeros((1,len(syms)),np.int32),np.cumsum(clipped,0,dtype=np.int32)])
grid=np.where(CTS%14400==0)[0]; grid=grid[(grid>=8640)&(grid+288<=CD.shape[0])]
E=grid; nclip=CSC[E+49]-CSC[E+1]          # clipped bars per (anchor,name) in the target window
has=nclip>0
ets=CTS[E]; eyr=np.array([time.gmtime(int(t)).tm_year for t in ets])
print("\n== per 4h anchor: names with >=1 clipped bar in the y4s window [E+1,E+48] ==")
print("%6s %8s %14s %14s %10s %12s"%("year","anchors","name-anchors","with clip","share","anch w/ any"))
for y in sorted(set(eyr.tolist())):
    m=eyr==y; tot=int(m.sum())*len(syms); wc=int(has[m].sum())
    print("%6d %8d %14d %14d %9.4f%% %12d"%(y,int(m.sum()),tot,wc,100*wc/max(tot,1),int(has[m].any(1).sum())))
np.savez_compressed("/workspace/review_scratch/clip_flags.npz",E_ts=ets,has=has,nclip=nclip.astype(np.int16),symbols=np.array(syms))
print("\nsaved clip_flags.npz")
