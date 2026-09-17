import numpy as np, time
T=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True); sy=[str(s) for s in T["symbols"]]; E=T["E_ts"]; y=T["y4s"]
def w(a,b): return (E>=np.datetime64(a).astype("datetime64[s]").astype(np.int64))&(E<np.datetime64(b).astype("datetime64[s]").astype(np.int64))
for nm,a,b in [("BOBUSDT","2026-02-01","2026-03-01"),("BMTUSDT","2026-02-01","2026-03-01"),("MTLUSDT","2026-04-01","2026-05-01")]:
    j=sy.index(nm); m=w(a,b); v=y[m,j].astype(np.float64); f=np.isfinite(v)
    print(f"{nm} y4s [{a},{b}) anchors={m.sum()} finite={f.sum()} NaN={(~f).sum()} max|y4s|={np.nanmax(np.abs(v)) if f.any() else float('nan'):.5f} qvk>0:{(T['qvk'][m,j]>0).sum()}")
H=np.load("/workspace/review_scratch/holefix2_cells.npz",allow_pickle=True); print("holefix2_cells keys",H.files)
for k in H.files:
    a=H[k]; print(" ",k,getattr(a,'shape',None),getattr(a,'dtype',None))
