import numpy as np, os
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"
SA="/mnt/storage/private/work_hsy/quant_research"  # single-asset (npz_v4 original)

def feat_names(z):
    for k in ("feature_names","feat_names","x_names","names","col_names","channel_names"):
        if k in z.files:
            return list(z[k])
    return None

def ts_unit(ts):
    m = int(np.median(np.abs(ts.astype(np.int64))))
    if m > 1e14: return "us", m
    if m > 1e11: return "ms", m
    if m > 1e8:  return "s", m
    return "?", m

def describe(path, day, label):
    fp=os.path.join(path, day+".npz")
    if not os.path.exists(fp):
        print(f"  [{label}] {day}: MISSING ({fp})"); return None
    z=np.load(fp, allow_pickle=True)
    ts=z["timestamps"] if "timestamps" in z.files else None
    u=ts_unit(ts) if ts is not None else ("na",0)
    X=z["X"] if "X" in z.files else None
    fn=feat_names(z)
    print(f"  [{label}] {day}: keys={z.files}")
    print(f"        X={None if X is None else X.shape} ts_unit={u[0]} (med={u[1]}) N_ts={0 if ts is None else ts.size}")
    if fn is not None:
        print(f"        feat_names[0]={fn[0]!r} feat_names[6]={fn[6]!r} (len={len(fn)})")
    else:
        print(f"        feat_names: NONE  (col0 mean/std={None if X is None else (float(np.nanmean(X[:,:,0])), float(np.nanstd(X[:,:,0])))})")
    return z

print("=== 2025-09-15 : compare npz_v4 (single-asset orig source) vs npz_spot (multi-asset new source) ===")
z_v4  = describe(os.path.join(SA,"data/npz_v4"), "2025-09-15", "npz_v4  ")
z_sp  = describe(os.path.join(MA,"data/npz_spot"), "2025-09-15", "npz_spot")
z_pp  = describe(os.path.join(MA,"data/npz_perp"), "2025-09-15", "npz_perp")

# col-0 / col-6 numeric equality between npz_v4 and npz_spot (same feature?)
if z_v4 is not None and z_sp is not None and "X" in z_v4.files and "X" in z_sp.files:
    # align by timestamps
    tv=z_v4["timestamps"].astype(np.int64); tsp=z_sp["timestamps"].astype(np.int64)
    common=np.intersect1d(tv, tsp)
    print(f"  npz_v4 vs npz_spot: N_v4={tv.size} N_spot={tsp.size} common_ts={common.size}")
    if common.size>0:
        iv=np.searchsorted(tv, common); isp=np.searchsorted(tsp, common)
        for j,lab in [(0,"col0(ret1s?)"),(6,"col6(obi_L5?)")]:
            a=z_v4["X"][iv][:, :, j].astype(np.float64); b=z_sp["X"][isp][:, :, j].astype(np.float64)
            cc=np.corrcoef(a.ravel(), b.ravel())[0,1]
            print(f"        {lab}: corr(v4,spot)={cc:.4f} v4[mean={a.mean():+.3e} std={a.std():.3e}] spot[mean={b.mean():+.3e} std={b.std():.3e}]")

print()
print("=== 2026-01-15 + 2025-10-15 : base npz_v2arch vs npz_spot timestamp subset ===")
for day in ["2025-10-15","2026-01-15"]:
    zb=describe(os.path.join(MA,"data/npz_v2arch"), day, "v2arch ")
    zs=describe(os.path.join(MA,"data/npz_spot"), day, "npz_spot")
    zp=describe(os.path.join(MA,"data/npz_perp"), day, "npz_perp")
    if zb is not None and zs is not None:
        tb=zb["timestamps"].astype(np.int64); tsp=zs["timestamps"].astype(np.int64)
        frac=np.isin(tb, tsp).mean()
        print(f"  >> {day}: base(v2arch) ts IN npz_spot ts = {frac:.4f} (need 1.0 for isin mask)")
    print()
