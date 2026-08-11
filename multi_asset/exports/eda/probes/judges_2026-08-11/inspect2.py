import numpy as np, pandas as pd
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
prod = pd.read_csv(f"{MA}/exports/final_l01/y600_backtest_dataset.csv")
print("PROD CSV month counts:")
print(prod.month.value_counts().sort_index())

# how much does 5sigma clipping bite? check denorm(npz targets) vs prod raw y on a covered month,
# and the clip fraction on the low-coverage months
for mk in ["2025_08","2025_09","2025_10","2026_01"]:
    z = np.load(f"{MA}/experiments/d1gate/d1_{mk}_run1/fold_0/ema_test_preds.npz", allow_pickle=True)
    tg = z["targets"].astype(float); ysig=float(z["y_sigma"]); ymed=float(z["y_median"])
    m = z["mask"].astype(bool)
    denorm_bps = (tg*ysig+ymed)*1e4
    clip_frac = np.mean(np.abs(tg[m]) >= 4.999)   # at ±5σ clip boundary
    # compare to prod raw where available
    ts = z["timestamps"].astype(np.int64); ts_ms = ts//1000 if ts[0]>3e12 else ts
    cy = dict(zip(prod.timestamp_ms.values.astype(np.int64), prod.y_true_ret_bps.values.astype(float)))
    idx = np.where(m)[0]
    pairs = [(denorm_bps[i], cy[int(ts_ms[i])]) for i in idx if int(ts_ms[i]) in cy]
    if pairs:
        a=np.array([p[0] for p in pairs]); b=np.array([p[1] for p in pairs])
        maxdiff = np.max(np.abs(a-b)); corr = np.corrcoef(a,b)[0,1]
        print(f"{mk}: clip_frac={clip_frac*100:.2f}% | denorm-vs-prodRaw on {len(pairs)} common: max|Δ|={maxdiff:.4f}bps corr={corr:.6f}")
    else:
        print(f"{mk}: clip_frac={clip_frac*100:.2f}% | no common nodes to compare")
