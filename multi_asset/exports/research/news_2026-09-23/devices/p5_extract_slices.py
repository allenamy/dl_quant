import numpy as np, json, hashlib
W="/dev/shm/news_2026-09-23"
ax=np.load(f"{W}/work/cache_x0918r_axes.npz"); ts=ax["ts"].astype(np.int64)
D=np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
A0=1789660800; A1=1789776000
i0=int(np.searchsorted(ts,A0))-11519; i1=int(np.searchsorted(ts,A1))
np.savez(f"{W}/work/parity_cache_slice.npz", ts=ts[i0:i1+1], data=np.array(D[i0:i1+1]), symbols=ax["symbols"], ch=ax["ch"], row0=np.int64(i0))
mk=np.load("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"); mts=mk["ts"].astype(np.int64); k=(mts>=A0-86400*2)&(mts<=A1)
np.savez(f"{W}/work/parity_mask_slice.npz", ts=mts[k], mask=mk["mask"][k], symbols=mk["symbols"])
h=np.load("/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz"); s=(h["row"]>=i0)&(h["row"]<=i1)
np.savez(f"{W}/work/parity_holes_slice.npz", row=h["row"][s], col=h["col"][s])
fr=np.load(f"{W}/work/fund_replay.npz"); k2=fr["anchors"]>=A0-86400
np.savez(f"{W}/work/parity_fund_slice.npz", **{kk: (fr[kk][k2] if fr[kk].ndim>=1 and len(fr[kk])==len(fr["anchors"]) else fr[kk]) for kk in fr.files})
print(i0, i1, int(s.sum()))
