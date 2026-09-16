import numpy as np, time, json
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
out={}
# axes
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True); pt=P["ts"].astype(np.int64)
M=np.load("/workspace/data/wide_fea_v4_meta.npz",allow_pickle=True); mt=M["E_ts"].astype(np.int64)
T=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True); tt=T["E_ts"].astype(np.int64)
Z=np.load("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz",allow_pickle=True) if False else None
import zipfile
zf=zipfile.ZipFile("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")
import io
cts=np.lib.format.read_array(io.BytesIO(zf.read("ts.npy")))
out["cache"]={"n":int(len(cts)),"start":U(cts[0]),"end":U(cts[-1]),"step_ok":bool(np.all(np.diff(cts.astype(np.int64))==300))}
for nm,a in (("panel_v2ext",pt),("king_meta_v4",mt),("dlw_v4raw",tt)):
    out[nm]={"n":int(len(a)),"start":U(a[0]),"end":U(a[-1]),"grid_4h_ok":bool(np.all(np.diff(a)==14400))}
V3=np.load("/workspace/data/wide_panel_4h_v3splice.npz",allow_pickle=True); v3=V3["ts"].astype(np.int64)
out["panel_v3splice"]={"n":int(len(v3)),"start":U(v3[0]),"end":U(v3[-1]),"grid_4h_ok":bool(np.all(np.diff(v3)==14400))}
out["king_anchors_beyond_panel_v2ext_end"]=int((mt>pt[-1]).sum())
# X4 on the INCUMBENT king features: members-only finite fraction of the two funding columns
names=[str(n) for n in M["names"]]; ci={n:i for i,n in enumerate(names)}
c_e,c_n=ci["fund_ema"],ci["fund_now"]
FEA=np.load("/workspace/data/wide_fea_v4.npy",mmap_mode="r")
mem=M["members"]
rows=list(range(len(mt)-10,len(mt)))
tail=[]
for i in rows:
    m=mem[i]; a=np.asarray(FEA[i,m,c_e]); b=np.asarray(FEA[i,m,c_n])
    tail.append({"anchor":U(mt[i]),"members":int(len(m)),"fund_ema_finite":int(np.isfinite(a).sum()),"fund_now_finite":int(np.isfinite(b).sum())})
out["X4_incumbent_tail10"]=tail
# how many anchors in the whole incumbent axis are funding-blind (frac<0.95)? sample from 2025-03 on
i0=int(np.searchsorted(mt,1740787200))  # 2025-03-01
bad=[]
for i in range(i0,len(mt)):
    m=mem[i]; a=np.asarray(FEA[i,m,c_e]); f=float(np.isfinite(a).mean())
    if f<0.95: bad.append({"anchor":U(mt[i]),"frac":round(f,4)})
out["X4_incumbent_violations_since_2025_03_01"]={"n":len(bad),"list":bad[:20]}
print(json.dumps(out,indent=1))
