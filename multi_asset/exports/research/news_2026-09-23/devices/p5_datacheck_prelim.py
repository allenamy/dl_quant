import numpy as np, json, time
W="/dev/shm/news_2026-09-23"
z=np.load(f"{W}/work/snap_1789776000_rolling.npz", allow_pickle=True); rts=z["ts"].astype(np.int64); RD=z["data"]
ax=np.load(f"{W}/work/cache_x0918r_axes.npz"); ts=ax["ts"].astype(np.int64); syms=[str(s) for s in ax["symbols"]]
D=np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
cfg=json.load(open(f"{W}/inputs/bundle_config.json")); live=[syms.index(s) for s in cfg["symbols_live"]]
i0=int(np.searchsorted(ts, rts[0])); i1=int(np.searchsorted(ts, rts[-1]))
assert np.array_equal(ts[i0:i1+1], rts), (rts[0], rts[-1], ts[i0], ts[i1])
H=np.array(D[i0:i1+1])[:, live, :]; L=RD[:, live, :]
h=np.load("/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"); hole=np.zeros(H.shape[:2], bool)
col={j:k for k,j in enumerate(live)}
sel=(h["row"]>=i0)&(h["row"]<=i1)
for r,c in zip(h["row"][sel], h["col"][sel]):
    if c in col: hole[r-i0, col[c]]=True
print("rows", len(rts), time.strftime("%m-%d %H:%M", time.gmtime(int(rts[0]))), "->", time.strftime("%m-%d %H:%M", time.gmtime(int(rts[-1]))), "hole cells among 450:", int(hole.sum()))
for c,nm in enumerate(["ret5","range","cpos","log_qv","log_cnt","log_avgsz","tbf"]):
    a=H[:,:,c].view(np.uint16); b=L[:,:,c].view(np.uint16)
    fa=np.isfinite(H[:,:,c]); fb=np.isfinite(L[:,:,c])
    eq=(a==b)|(~fa&~fb)
    ne=~eq
    print(nm, "cells", ne.size, "diff", int(ne.sum()), "diff_nonhole", int((ne&~hole).sum()), "hist_nan_live_fin", int((~fa&fb).sum()), "hist_fin_live_nan", int((fa&~fb).sum()),
          "both_fin_diff", int((fa&fb&ne).sum()), "rows_with_diff_last", time.strftime("%m-%d %H:%M", time.gmtime(int(rts[np.flatnonzero(ne.any(1))[-1]]))) if ne.any() else None)
ne=np.zeros(H.shape[:2],bool)
for c in range(7): ne|= ~((H[:,:,c].view(np.uint16)==L[:,:,c].view(np.uint16))|(~np.isfinite(H[:,:,c])&~np.isfinite(L[:,:,c])))
dd=np.flatnonzero(ne.any(1)); import collections
print("days with diffs", collections.Counter(time.strftime("%m-%d", time.gmtime(int(rts[r]))) for r in dd).most_common(20))
print("names with diffs (non-hole)", collections.Counter(cfg["symbols_live"][k] for k in np.flatnonzero((ne&~hole).any(0))).most_common(10), int((ne&~hole).any(0).sum()))
