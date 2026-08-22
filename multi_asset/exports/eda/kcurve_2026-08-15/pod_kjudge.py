"""K 曲线固定锚终判 @pod: 判据冻结 DESIGN_wide_book_v1_2026-08-15 §3.4.
输入: exports_train/kcurve_pred_K400_s{42,2027,3037}_{2023..2026}.npy(s2027 从 jpline 拉回)
方法: 重建 y4/成员/量能(与训练装置同一代码路径, 常数逐字一致), 只取"K400 完整可行"
     的固定锚集(len(m)>=360), 同一批锚上算全部 serve-K 的逐锚 rank-IC:
     三种子均值±sd / K400 vs K110 配对t / Q4(BTC尾随7日波动最坏五分位)不衰减.
输出: kjudge.json + 终端表. 此脚本与结论同寿命(当日入库).
"""
import json, time
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata, spearmanr
W = 576; FWD = 48; TRAIL = 2016; NTOP = 400
SERVE_KS = (110, 200, 250, 300, 400)
SEEDS = (42, 2027, 3037)
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; csyms = [str(s) for s in Z["symbols"]]
NW = len(csyms); TT = CD.shape[0]
BTC_T = csyms.index("BTCUSDT")
r5 = CD[:, :, 0].astype(np.float32)
fin = np.isfinite(r5)
r5z = np.where(fin, r5, 0).astype(np.float32)
qvz = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], 0).astype(np.float32)
btc_r = np.where(np.isfinite(r5[:, BTC_T]), r5[:, BTC_T], 0).astype(np.float64)
z1 = np.zeros((1, NW))
CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
CS_r = np.concatenate([z1, np.cumsum(r5z, 0, dtype=np.float64)])
CS_r2 = np.concatenate([z1, np.cumsum(r5z * r5z, 0, dtype=np.float64)])
CS_q = np.concatenate([z1, np.cumsum(qvz, 0, dtype=np.float64)])
CB_r = np.concatenate([[0.0], np.cumsum(btc_r)])
CB_r2 = np.concatenate([[0.0], np.cumsum(btc_r * btc_r)])
del r5, r5z, qvz, fin, CD
grid = np.where(CTS % 14400 == 0)[0]
grid = grid[(grid >= W) & (grid + FWD <= TT)]
E = grid
S = np.maximum(E - TRAIL, 0)
nfin = np.maximum(CS_f[E] - CS_f[S], 1)
covr = (CS_f[E] - CS_f[S]) / np.maximum(E - S, 1)[:, None]
qvm = (CS_q[E] - CS_q[S]) / nfin
rs_ = CS_r[E] - CS_r[S]
vstd = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S]) / nfin - (rs_ / nfin) ** 2, 0))
nb = np.maximum(E - S, 1).astype(np.float64)
btcv = np.sqrt(np.maximum((CB_r2[E] - CB_r2[S]) / nb - ((CB_r[E] - CB_r[S]) / nb) ** 2, 0))
y4n = CS_f[E + FWD] - CS_f[E]
y4full = (CS_r[E + FWD] - CS_r[E]).astype(np.float32)
y4full[y4n < FWD - 2] = np.nan
MS, keep = [], []
for i in range(len(E)):
    ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4full[i])
    m = np.where(ok)[0]
    if len(m) > NTOP:
        m = np.sort(m[np.argsort(-qvm[i, m])[:NTOP]])
    if len(m) >= 50:
        MS.append(m); keep.append(i)
keep = np.array(keep)
E = E[keep]; y4full = y4full[keep]; qvk = qvm[keep]; btcv = btcv[keep]
yrs = np.array([time.gmtime(int(t)).tm_year for t in CTS[E]])
print(f"重建 anchors {len(E)}(须与训练装置 10086 一致)", flush=True)
assert len(E) == 10086, f"锚数不一致 {len(E)}"
PRED = {}
for sd in SEEDS:
    P = np.full((len(E), NW), np.nan, np.float32)
    nload = 0
    for YV in (2023, 2024, 2025, 2026):
        try:
            p = np.load(f"/workspace/exports_train/kcurve_pred_K400_s{sd}_{YV}.npy")
            rows = np.where(yrs == YV)[0]
            P[rows] = p[rows]; nload += 1
        except FileNotFoundError:
            print(f"  缺 s{sd} {YV}", flush=True)
    PRED[sd] = P
    print(f"seed {sd}: {nload}/4 折已载", flush=True)
def sp(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 30 else np.nan
# 固定锚集: K400 完整可行(成员>=360), 且三种子该锚均有预测
fixed = np.array([i for i in range(len(E)) if len(MS[i]) >= 360
                  and all(np.isfinite(PRED[sd][i, MS[i]]).sum() >= 300 for sd in SEEDS)])
print(f"固定锚集 {len(fixed)}(年份分布 {dict(zip(*np.unique(yrs[fixed], return_counts=True)))})", flush=True)
IC = {sd: {K: np.full(len(fixed), np.nan) for K in SERVE_KS} for sd in SEEDS}
for fi, i in enumerate(fixed):
    m = MS[i]
    ordm = np.argsort(-qvk[i, m])
    for sd in SEEDS:
        p = PRED[sd][i, m]
        for K in SERVE_KS:
            sub = ordm[:K]
            IC[sd][K][fi] = sp(p[sub], y4full[i, m[sub]])
# Q4: BTC 尾随7日波动最坏五分位(固定锚集内分位)
qb = np.quantile(btcv[fixed], [0.2, 0.4, 0.6, 0.8])
qgrp = np.digitize(btcv[fixed], qb)  # 0..4, 4=最高波动
out = {"n_fixed": int(len(fixed)), "per_seed": {}, "mean": {}, "t_vs_110": {}, "q4": {}}
print("\n===== 固定锚终判(同一批锚, 三种子) =====")
hdr = "K      " + "".join(f"{K:>10d}" for K in SERVE_KS)
print(hdr)
for sd in SEEDS:
    row = [float(np.nanmean(IC[sd][K])) for K in SERVE_KS]
    out["per_seed"][sd] = dict(zip(map(str, SERVE_KS), row))
    print(f"s{sd:<6d}" + "".join(f"{v:>+10.4f}" for v in row))
mrow, srow, trow = [], [], []
for K in SERVE_KS:
    stack = np.stack([IC[sd][K] for sd in SEEDS])
    per_anchor = np.nanmean(stack, 0)
    mrow.append(float(np.nanmean(per_anchor)))
    srow.append(float(np.std([np.nanmean(IC[sd][K]) for sd in SEEDS])))
    d = per_anchor - np.nanmean(np.stack([IC[sd][110] for sd in SEEDS]), 0)
    ok = np.isfinite(d)
    trow.append(float(np.mean(d[ok]) / (np.std(d[ok]) / np.sqrt(ok.sum()) + 1e-12)))
out["mean"] = dict(zip(map(str, SERVE_KS), mrow))
out["seed_sd"] = dict(zip(map(str, SERVE_KS), srow))
out["t_vs_110"] = dict(zip(map(str, SERVE_KS), trow))
print(f"{'均值':<7s}" + "".join(f"{v:>+10.4f}" for v in mrow))
print(f"{'种子sd':<7s}" + "".join(f"{v:>10.4f}" for v in srow))
print(f"{'配对t':<7s}" + "".join(f"{v:>+10.1f}" for v in trow))
print(f"{'IC×√K':<7s}" + "".join(f"{m_*np.sqrt(K):>+10.3f}" for m_, K in zip(mrow, SERVE_KS)))
print("\nQ4 最坏五分位(BTC波动最高档) vs 全体:")
for K in (110, 400):
    stack = np.nanmean(np.stack([IC[sd][K] for sd in SEEDS]), 0)
    rowq = [float(np.nanmean(stack[qgrp == g])) for g in range(5)]
    out["q4"][str(K)] = rowq
    print(f"K{K}: Q0-Q4 " + " ".join(f"{v:+.4f}" for v in rowq) + f"  (Q4/全体 {rowq[4]/np.nanmean(stack):.2f})")
json.dump(out, open("/workspace/kjudge.json", "w"), indent=1)
print("\nKJUDGE_DONE", flush=True)
