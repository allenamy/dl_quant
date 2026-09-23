import numpy as np, zipfile, json
p='/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz'
z=zipfile.ZipFile(p); fh=z.open('data.npy'); ver=np.lib.format.read_magic(fh)
shp,fo,dt=(np.lib.format.read_array_header_1_0(fh) if ver==(1,0) else np.lib.format.read_array_header_2_0(fh))
T,N,C=shp; rowb=N*C*2; B=np.float32(np.float16(0.3))
crypto=np.load('/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz')['crypto'].astype(bool)
H=np.load('/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz'); hole=set(zip(H['row'].tolist(),H['col'].tolist()))
cells=[]
for r0 in range(0,T,8192):
    k=min(8192,T-r0); a=np.frombuffer(fh.read(k*rowb),np.float16).reshape(k,N,C)[:,:,0].astype(np.float32)
    rr,cc=np.nonzero(np.isfinite(a)&(np.abs(a)==B)); cells+= [(int(r0+x),int(y)) for x,y in zip(rr,cc)]
nc=[c for c in cells if not crypto[c[1]]]; hc=[c for c in cells if c in hole]
print(json.dumps({"bound_all":len(cells),"bound_noncrypto":len(nc),"bound_in_hole":len(hc),"bound_crypto_nonhole":sum(1 for c in cells if crypto[c[1]] and c not in hole)}))
