"""Q1 决定性实验 · 判据冻结(先于数字)
两问两臂, 同装置同锚同标签(9821 锚 OOS, walk-forward 2023-26, 早停用训练尾 20%):
 臂A "树能走多远": LGBM(32ch × 滞后{0,1,3,6,24}h = 160 特征) 直接预测 Y4 —— 对照 king(在役
    持有形态, 同锚 spearman 0.0546)。回答"DL 对树的提升到底多大"; 预期(受据): 浅面板天花板
    0.033, DL 边际应主要来自时序深度+池化。
 臂B "树能否在 DL 之上再找到东西": LGBM(同 160 特征 + king 分数作第 161 特征) —— Δic vs
    king 单独。冻结门: Δ ≥ +0.003 且评估年全部非负 ⇒ "树发现了 DL 漏掉的结构"成立并立项;
    否则该假设以受据关闭(与冻结表征天花板证明合并为第四条独立三角测量)。
LGBM 保守参: leaves 63, lr .05, min_data 500, ff .7, bag .8, ≤500 轮早停 50。NaN 原生处理;
面板通道已逐资产 MAD 归一, 树对单调变换不敏感, 不再额外归一。"""
import sys
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
PD = "/mnt/storage/private/work_hsy/probe_artifacts"; sys.path.insert(0, PD)
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import lightgbm as lgb
import engine.replay_fullhist as RF
src = RF.get_src(None, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
a, yr = RF._all_anchors(src); N = src.N; n = len(a)
C = src.CH.shape[2]
LAGS = [0, 1, 3, 6, 24]
F = C * len(LAGS)
print(f"n={n} N={N} C={C} F={F}", flush=True)
X = np.full((n, N, F), np.nan, dtype=np.float32)
Y = np.full((n, N), np.nan, dtype=np.float32)
KING = np.full((n, N), np.nan, dtype=np.float32)
held_k = np.full(N, np.nan)
for i, t in enumerate(a):
    ti = int(t); m = np.asarray(src.tradeable(ti))
    if m.dtype == bool: m = np.where(m)[0]
    if i == 0 or ti % 8 == 0:
        v = np.full(N, np.nan); v[m] = src.king[ti, m]; held_k = v
    KING[i] = held_k
    Y[i, m] = src.Y4[ti, m]
    for li, L in enumerate(LAGS):
        if ti - L >= 0:
            X[i, m, li*C:(li+1)*C] = src.CH[ti-L, m, :]
def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
yrs = np.array(yr)
def eval_pred(P, idx):
    return float(np.nanmean([spear(P[i], Y[i]) for i in idx]))
king_ic = {int(Yv): float(np.nanmean([spear(KING[i], Y[i]) for i in np.where(yrs == Yv)[0]]))
           for Yv in (2023, 2024, 2025, 2026)}
print(f"king(在役持有形态) 逐年 IC: {king_ic}", flush=True)
PAR = dict(objective="regression", num_leaves=63, learning_rate=0.05, min_data_in_leaf=500,
           feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, verbosity=-1,
           num_threads=8)
res = {"A": {}, "B": {}}
for Yv in (2023, 2024, 2025, 2026):
    tr = np.where(yrs < Yv)[0]; te = np.where(yrs == Yv)[0]
    trs = tr[::2]  # 训练降采样一半(内存/速度), 评估全锚
    cut = int(len(trs)*0.8); tr1, va1 = trs[:cut], trs[cut:]
    def flat(idx, with_king):
        xs, ys = [], []
        for i in idx:
            ok = np.isfinite(Y[i])
            x = X[i, ok]
            if with_king:
                x = np.concatenate([x, KING[i, ok][:, None]], axis=1)
            xs.append(x); ys.append(Y[i, ok])
        return np.concatenate(xs), np.concatenate(ys)
    for tag, wk in (("A", False), ("B", True)):
        Xtr, ytr = flat(tr1, wk); Xva, yva = flat(va1, wk)
        d1 = lgb.Dataset(Xtr, ytr); d2 = lgb.Dataset(Xva, yva, reference=d1)
        mdl = lgb.train(PAR, d1, num_boost_round=500, valid_sets=[d2],
                        callbacks=[lgb.early_stopping(50, verbose=False)])
        P = np.full((n, N), np.nan, dtype=np.float32)
        for i in te:
            ok = np.isfinite(Y[i])
            x = X[i, ok]
            if wk: x = np.concatenate([x, KING[i, ok][:, None]], axis=1)
            P[i, ok] = mdl.predict(x, num_iteration=mdl.best_iteration)
        res[tag][Yv] = eval_pred(P, te)
        print(f"  {Yv} 臂{tag}: IC {res[tag][Yv]:+.4f} (轮数 {mdl.best_iteration})", flush=True)
print("\n== 判决 ==", flush=True)
ka = np.mean(list(king_ic.values()))
aa = np.mean(list(res["A"].values())); bb = np.mean(list(res["B"].values()))
print(f"臂A LGBM纯树(时序滞后特征): 均值 {aa:+.4f} vs king {ka:+.4f} ⇒ DL 相对优势 {(ka-aa)/max(aa,1e-9)*100:+.0f}%")
dv = [res["B"][y_] - king_ic[y_] for y_ in (2023, 2024, 2025, 2026)]
print(f"臂B LGBM(特征+king): 均值 {bb:+.4f}, Δ vs king 逐年 {[round(x,4) for x in dv]} 均值 {np.mean(dv):+.4f}")
ok_ = np.mean(dv) >= 0.003 and all(x >= 0 for x in dv)
print("★臂B PASS: 树在 DL 之上发现结构, 立项" if ok_ else "臂B FAIL ⇒ '树能找到 DL 漏掉的结构'假设关闭(第四条三角测量)")
print("LGBMVSDL_DONE", flush=True)
