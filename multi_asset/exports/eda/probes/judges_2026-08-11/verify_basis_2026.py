import numpy as np, os
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"
for day in ["2025-09-15","2026-01-15","2026-03-15","2026-05-15"]:
    bp=os.path.join(MA,"data/basis_cache",day+".npz")
    line=day+" "
    if os.path.exists(bp):
        d=np.load(bp)
        F=d["F"]; bb=d["basis_bps"]
        line+=f"basis_cache N={F.shape} bps[min/mean/max/std]=({np.nanmin(bb):+.2f}/{np.nanmean(bb):+.2f}/{np.nanmax(bb):+.2f}/{np.nanstd(bb):.3f}) F_finite={np.isfinite(F).mean():.3f} Fstd={np.nanstd(F,0).round(3).tolist()}"
    else:
        line+="basis_cache MISSING"
    mp=os.path.join(MA,"data/mid_cache",day+".npz")
    if os.path.exists(mp):
        m=np.load(mp); ks=m.files
        sm=m["spot_mid"] if "spot_mid" in ks else None
        pm=m["perp_mid"] if "perp_mid" in ks else None
        if sm is not None:
            line+=f" | mid_cache spot[mean={np.nanmean(sm):.1f} std={np.nanstd(sm):.1f} fin={np.isfinite(sm).mean():.3f}] perp[mean={np.nanmean(pm):.1f}]"
    print(line)
