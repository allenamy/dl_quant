import numpy as np, zipfile, time, json, collections
p='/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz'
zf=zipfile.ZipFile(p); ts=np.load(zf.open('ts.npy')).astype(np.int64)
fh=zf.open('data.npy'); ver=np.lib.format.read_magic(fh); shp,fo,dt=(np.lib.format.read_array_header_1_0(fh) if ver==(1,0) else np.lib.format.read_array_header_2_0(fh))
T,N,C=shp; q=np.empty((T,N),bool); rowb=N*C*2
for r0 in range(0,T,8192):
    k=min(8192,T-r0); buf=fh.read(k*rowb); q[r0:r0+k]=np.isfinite(np.frombuffer(buf,np.float16).reshape(k,N,C)[:,:,3])
ev=collections.Counter(); per_anchor=collections.Counter()
for j in range(N):
    f=q[:,j]; idx=np.flatnonzero(f)
    if len(idx)==0: continue
    gaps=np.diff(idx); big=np.flatnonzero(gaps>=288)       # >= 1 day without any bar, then bars again
    for g in big:
        t=int(ts[idx[g+1]]); ev[time.strftime('%Y-%m',time.gmtime(t))]+=1; per_anchor[t//14400]+=1
    t0=int(ts[idx[0]])
    if t0>ts[0]: ev['first_'+time.strftime('%Y',time.gmtime(t0))]+=1
print(json.dumps({"reentry_by_month_2025_2026":{k:v for k,v in sorted(ev.items()) if k[:4] in ('2025','2026')},"first_listing_by_year":{k:v for k,v in sorted(ev.items()) if k.startswith('first_')},"max_reentries_same_4h_anchor":max(per_anchor.values()) if per_anchor else 0,"top_anchors":[(time.strftime('%Y-%m-%dT%H',time.gmtime(a*14400)),n) for a,n in per_anchor.most_common(5)]}))
