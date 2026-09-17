# FP2-7 probe (read-only): does OUR holefix2 5m cache / RAW targets carry the C1/C3 defect for BOB/BMT/MTL?
import numpy as np, zipfile, os, glob, sys, time
Z="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
z=zipfile.ZipFile(Z); info={i.filename:i for i in z.infolist()}
ts=np.load(z.open("ts.npy")); sy=[str(s) for s in np.load(z.open("symbols.npy"),allow_pickle=True)]
print("cache rows",len(ts),"symbols",len(sy),"ts0",time.strftime("%F %T",time.gmtime(int(ts[0]))),"ts-1",time.strftime("%F %T",time.gmtime(int(ts[-1]))))
di=info["data.npy"]
if di.compress_type==0:
    off=di.header_offset; f=open(Z,"rb"); f.seek(off); import struct
    f.seek(off+26); nl,el=struct.unpack("<HH",f.read(4)); start=off+30+nl+el
    f.seek(start); ver=np.lib.format.read_magic(f); shp,fo,dt=np.lib.format._read_array_header(f,ver); doff=f.tell()
    data=np.memmap(Z,dtype=dt,mode="r",offset=doff,shape=shp,order="F" if fo else "C"); print("memmap",shp,dt)
else:
    data=np.load(z.open("data.npy")); print("loaded",data.shape,data.dtype)
def win(a,b): return (ts>=np.datetime64(a).astype("datetime64[s]").astype(np.int64))&(ts<np.datetime64(b).astype("datetime64[s]").astype(np.int64))
cases=[("BOB","2026-01-30","2026-03-03"),("BMT","2026-01-30","2026-03-03"),("MTL","2026-03-30","2026-05-03")]
for nm,a,b in cases:
    js=[j for j,s in enumerate(sy) if s.startswith(nm)]
    if not js: print(nm,"NOT IN CACHE SYMBOLS"); continue
    j=js[0]; m=win(a,b); r=np.asarray(data[m,j,0],dtype=np.float64); cnt=np.asarray(data[m,j,4],dtype=np.float64); t=ts[m]
    fin=np.isfinite(r); print(f"\n{sy[j]} [{a},{b}) rows={m.sum()} ch0 NaN={(~fin).sum()} finite={fin.sum()} zero={(r==0).sum()} log_cnt==0:{(cnt==0).sum()} log_cnt NaN:{np.isnan(cnt).sum()}")
    if fin.any():
        k=np.nanargmax(np.abs(r)); print(f"  max|ch0|={r[k]:+.5f} at {time.strftime('%F %T',time.gmtime(int(t[k])))}; |ch0|>0.05 count={(np.abs(r)>0.05).sum()}")
        # NaN runs
        idx=np.flatnonzero(~fin)
        if len(idx):
            runs=np.split(idx,np.flatnonzero(np.diff(idx)>1)+1); runs=sorted(runs,key=len,reverse=True)[:2]
            for rr in runs: print(f"  NaN run {len(rr)} rows {time.strftime('%F %T',time.gmtime(int(t[rr[0]])))} .. {time.strftime('%F %T',time.gmtime(int(t[rr[-1]])))}; first finite after: {r[rr[-1]+1] if rr[-1]+1<len(r) else 'EOW'}")
        # frozen runs (ch0==0 & cnt==0)
        fz=(r==0)&(cnt==0); print(f"  frozen(ch0==0&cnt==0) rows={fz.sum()}")
print("\n=== RAW targets (dlw_v4raw) ===")
for p in sorted(glob.glob("/workspace/dlw_v4raw/data/*.npz"))[:6]:
    zz=np.load(p,allow_pickle=True); print(os.path.basename(p),{k:zz[k].shape for k in zz.files if hasattr(zz[k],'shape')})
