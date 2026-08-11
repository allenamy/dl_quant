"""C2 影子的阻塞项: 离线宽面板 funding_ema vs 实盘 preds_latest funding_ema —— 是不是同一个口径?
若不同, C2 影子正交化减掉的东西与离线不是同一个 ⇒ 影子在测另一个因子。"""
import sys, numpy as np, json
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
import engine.replay_fullhist as RF
PD = "/mnt/storage/private/work_hsy/probe_artifacts"
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
fi = src.fund_idx
a, yrs = RF._all_anchors(src)
last = int(a[-1])
m = src.tradeable(last)
v = src.CH[last, m, fi].astype(np.float64)
v = v[np.isfinite(v)]
print(f"[离线宽面板] 末锚 n={len(v)}")
print(f"  分位[1,25,50,75,99] = {np.percentile(v,[1,25,50,75,99]).round(9).tolist()}")
print(f"  均值 {v.mean():+.4e}  sd {v.std():.4e}  |中位| {np.median(np.abs(v)):.4e}")
print(f"  ch_names[fund_idx] = {src.ch[fi]}")
# 全期分布, 排除末锚特异
allv = src.CH[a, :, fi].astype(np.float64); allv = allv[np.isfinite(allv)]
print(f"[离线全期] n={len(allv):,}  分位[1,50,99] = {np.percentile(allv,[1,50,99]).round(9).tolist()}  |中位| {np.median(np.abs(allv)):.4e}")
print("\n[实盘 preds_latest, 2026-08-09 记录]")
print("  分位[1,25,50,75,99] = [-3.057e-04, 4.000e-05, 7.960e-05, 9.740e-05, 1.000e-04]")
print("  均值 +4.725e-05  sd 1.075e-04  |中位| 8.576e-05")
print("\n判读: |中位| 与分位形状同量级 ⇒ 同口径; 差一个数量级(如 4h vs 8h, 或费率 vs EMA) ⇒ 不同口径")
