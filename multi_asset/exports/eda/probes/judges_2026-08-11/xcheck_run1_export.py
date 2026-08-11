"""Independent caliber cross-check of 0C's Run1 production export (5ec8a72).
Reconciles my clipped-npz statusline numbers vs the export's RAW-y numbers, verifies
denorm, the clip landmine, coverage, and that DirAcc is on raw y."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.model.score_align import _cd, _pear  # canonical per-day-CLEAN operators
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
exp = pd.read_csv(f"{MA}/exports/run1_production_preds_from_2025_08.csv")
print("cols:", list(exp.columns), "| rows:", len(exp))
exp["ts_us"] = exp.timestamp_ms.astype(np.int64) * 1000   # for _cd (expects µs)

def cd_month(m, use_raw=True):
    d = exp[(exp.month==m)]
    if "has_ytrue" in d.columns: d = d[d.has_ytrue==True]
    if "mask" in d.columns: d = d[d["mask"]==True]
    if len(d)<20: return np.nan, 0
    return _cd(d.y_pred_bps.values.astype(float), d.y_true_bps.values.astype(float), d.ts_us.values.astype(np.int64))

print("\n== RAW-y per-day-CLEAN Pearson (export) vs my CLIPPED statusline ==")
clip_ref = {"2025_08":0.0798,"2025_09":0.0493,"2025_10":0.1025,"2025_11":0.0485,"2025_12":0.0575,
            "2026_01":0.0175,"2026_02":0.0178,"2026_03":0.0281,"2026_04":0.0417,"2026_05":0.0540}
for m in clip_ref:
    cd, nd = cd_month(m)
    print(f"  {m}: export raw-y cd={cd:+.4f} (days={nd:>3})  |  my clipped statusline={clip_ref[m]:+.4f}  Δ(clip)={clip_ref[m]-cd:+.4f}")

# CLIP LANDMINE: denorm(clipped npz targets) vs RAW y corr on 2025_10 + 2026_01
print("\n== CLIP LANDMINE: corr(denorm(clipped npz target), RAW y) ==")
prod = pd.read_csv(f"{MA}/exports/final_l01/y600_backtest_dataset.csv")
praw = dict(zip(prod.timestamp_ms.astype(np.int64), prod.y_true_ret_bps.astype(float)))
for m in ["2025_10","2026_01"]:
    z=np.load(f"{MA}/experiments/d1gate/d1_{m}_run1/fold_0/ema_test_preds.npz", allow_pickle=True)
    tgt=z["targets"].astype(float); ysig=float(z["y_sigma"]); ymed=float(z["y_median"])
    ts_ms=(z["timestamps"].astype(np.int64)//1000); mk=z["mask"].astype(bool)
    denorm_clip=(tgt*ysig+ymed)*1e4
    raw=np.array([praw.get(int(t),np.nan) for t in ts_ms])
    ok=mk & np.isfinite(raw)
    c=_pear(denorm_clip[ok], raw[ok]); md=float(np.max(np.abs(denorm_clip[ok]-raw[ok])))
    print(f"  {m}: corr(denorm-clipped, raw-y)={c:.4f}  maxΔ={md:.0f}bps  clip_frac={float((np.abs(tgt[mk])>=4.999).mean())*100:.1f}%  -> clipped npz UNUSABLE as realized y")

# COVERAGE per month
print("\n== COVERAGE (raw-y availability) ==")
for m in clip_ref:
    d=exp[exp.month==m]; hy=int(d.has_ytrue.sum()) if "has_ytrue" in d.columns else len(d)
    print(f"  {m}: {hy}/{len(d)} = {hy/max(len(d),1)*100:.0f}% raw-y")

# DirAcc on RAW y (sanity a couple months) — sign match, |y|>0
print("\n== DirAcc on RAW y (sanity) ==")
for m in ["2025_10","2026_01"]:
    d=exp[(exp.month==m)&(exp.has_ytrue==True)&(exp["mask"]==True)]
    da=float(np.mean(np.sign(d.y_pred_bps.values)==np.sign(d.y_true_bps.values)))
    print(f"  {m}: DirAcc(raw)={da:.4f}  n={len(d)}")
