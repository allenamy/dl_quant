import numpy as np, sys, hashlib
ref=np.load("/workspace/uplift_2026-09-11/r8_inbook/arms/R8_A0_dyn_s42.npz")
C=[str(c) for c in ref["cols"]]; rts=ref["rec"][:,C.index("ts")]
for p in sys.argv[1:]:
    Z=np.load(p); C2=[str(c) for c in Z["cols"]]
    for k in [k for k in Z.files if k.endswith("rec")]:
        a=Z[k]; ts=a[:,C2.index("ts")]
        nn=np.isnan(ts).sum()
        common=np.intersect1d(ts[~np.isnan(ts)], rts)
        print(p.rsplit("/",1)[1], k, a.shape, "nan_ts",nn, "in_ref",len(common), "extra",int((~np.isin(ts[~np.isnan(ts)],rts)).sum()), "missing_vs_ref", int((~np.isin(rts,ts)).sum()), "first_missing", (np.setdiff1d(rts,ts)[:3]).astype(np.int64))
