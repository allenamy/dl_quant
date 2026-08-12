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
PANEL = MA + "/exports/wide_dl_full_corrfund_causal_v1.npz"   # ★显式因果面板(2026-08-12 规则: 特征实验禁 None 默认)
src = RF.get_src(PANEL, f"{PD}/king_pred_newgen.npz", f"{PD}/s2_pred_newgen.npz")
# 洁净受据: 因果面板逐通道 lag0 与未来 Y4 的 pooled |corr| 不得出现一骑绝尘者
import numpy as _np
_a0, _ = RF._all_anchors(src)
_cors = []
for _c in range(src.CH.shape[2]):
    _xs, _ys = [], []
    for _t in _a0[::8]:
        _ti = int(_t); _m = _np.asarray(src.tradeable(_ti))
        if _m.dtype == bool: _m = _np.where(_m)[0]
        _x = src.CH[_ti, _m, _c].astype(float); _y = src.Y4[_ti, _m].astype(float)
        _ok = _np.isfinite(_x) & _np.isfinite(_y)
        _xs.append(_x[_ok]); _ys.append(_y[_ok])
    _cors.append((abs(float(_np.corrcoef(_np.concatenate(_xs), _np.concatenate(_ys))[0, 1])), src.ch[_c]))
_cors.sort(reverse=True)
_med = float(_np.median([v for v, _ in _cors]))
print("因果面板未来相关 top3:", [(n, round(v, 4)) for v, n in _cors[:3]], "中位", round(_med, 4), flush=True)
# 洁净判据 = 分离度(泄漏签名是 30-50× 一骑绝尘), 非绝对小: top<0.15 且 top/中位<15
assert _cors[0][0] < 0.15 and _cors[0][0]/max(_med, 1e-9) < 15, f"洁净断言 FAIL: {_cors[0]} vs 中位 {_med:.4f}"
# 对照校准: 脏面板同谱(补完 08-11 未竟验尸受据; 预期 betaadj 通道一骑绝尘)
_dsrc = _np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
_dch = [str(c) for c in _dsrc["ch_names"]]; _dCH = _dsrc["CH"]; _dY4 = _dsrc["Y4"]
_dcors = []
for _c in range(_dCH.shape[2]):
    _xs, _ys = [], []
    for _t in _a0[::8]:
        _ti = int(_t); _m = _np.asarray(src.tradeable(_ti))
        if _m.dtype == bool: _m = _np.where(_m)[0]
        _x = _dCH[_ti, _m, _c].astype(float); _y = _dY4[_ti, _m].astype(float)
        _ok = _np.isfinite(_x) & _np.isfinite(_y)
        _xs.append(_x[_ok]); _ys.append(_y[_ok])
    _dcors.append((abs(float(_np.corrcoef(_np.concatenate(_xs), _np.concatenate(_ys))[0, 1])), _dch[_c]))
_dcors.sort(reverse=True)
print("【对照】脏面板 top3:", [(n, round(v, 4)) for v, n in _dcors[:3]], "中位", round(float(_np.median([v for v, _ in _dcors])), 4), flush=True)
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
# v4: 训练标签 = 逐锚横截面 rank-z(给树与 DL 同等的排序武器; 评估仍 raw y, 反模式#18)
YRZ = np.full_like(Y, np.nan)
from scipy.stats import rankdata as _rd
for _i in range(n):
    _ok = np.isfinite(Y[_i])
    if _ok.sum() >= 10:
        _r = _rd(Y[_i, _ok]); YRZ[_i, _ok] = (_r - (_ok.sum()+1)/2) / max(_ok.sum()-1, 1)

def spear(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    return spearmanr(x[ok], y[ok]).correlation if ok.sum() >= 10 else np.nan
yrs = np.array(yr)
def eval_pred(P, idx):
    return float(np.nanmean([spear(P[i], Y[i]) for i in idx]))
king_ic = {int(Yv): float(np.nanmean([spear(KING[i], Y[i]) for i in np.where(yrs == Yv)[0]]))
           for Yv in (2023, 2024, 2025, 2026)}
print(f"king(在役持有形态) 逐年 IC: {king_ic}", flush=True)
# v3 判官修理(阳性对照失败驱动: MSE 早停在 R2<1e-3 下瞎, 轮数 1-7, king 作特征只复原 0.008/0.054):
# 去早停固定 300 轮 + min_data 200 + lr 0.03; 新增臂C = 仅 king 特征的阳性对照(必须复原 >=0.9x king IC,
# 否则整个装置无效)。判据不变。
PAR = dict(objective="regression", num_leaves=63, learning_rate=0.03, min_data_in_leaf=200,
           feature_fraction=0.7, bagging_fraction=0.8, bagging_freq=1, verbosity=-1,
           num_threads=8)
res = {"A": {}, "B": {}, "C": {}}
for Yv in (2023, 2024, 2025, 2026):
    tr = np.where(yrs < Yv)[0]; te = np.where(yrs == Yv)[0]
    trs = tr[::2]  # 训练降采样一半(内存/速度), 评估全锚
    cut = int(len(trs)*0.8); tr1, va1 = trs[:cut], trs[cut:]
    def flat(idx, with_king):
        xs, ys = [], []
        for i in idx:
            ok = np.isfinite(YRZ[i])
            x = X[i, ok]
            if with_king:
                x = np.concatenate([x, KING[i, ok][:, None]], axis=1)
            xs.append(x); ys.append(YRZ[i, ok])
        return np.concatenate(xs), np.concatenate(ys)
    def flatC(idx):
        xs, ys = [], []
        for i in idx:
            ok = np.isfinite(YRZ[i]) & np.isfinite(KING[i])
            xs.append(KING[i, ok][:, None]); ys.append(YRZ[i, ok])
        return np.concatenate(xs), np.concatenate(ys)
    for tag, wk in (("C", "king_only"), ("A", False), ("B", True)):
        if tag == "C":
            Xtr, ytr = flatC(tr1)
            mdl = lgb.train(dict(PAR, num_leaves=31), lgb.Dataset(Xtr, ytr), num_boost_round=200)
            P = np.full((n, N), np.nan, dtype=np.float32)
            for i in te:
                ok = np.isfinite(Y[i]) & np.isfinite(KING[i])
                P[i, ok] = mdl.predict(KING[i, ok][:, None])
        else:
            Xtr, ytr = flat(tr1, wk)
            mdl = lgb.train(PAR, lgb.Dataset(Xtr, ytr), num_boost_round=300)
            P = np.full((n, N), np.nan, dtype=np.float32)
            for i in te:
                ok = np.isfinite(Y[i])
                x = X[i, ok]
                if wk: x = np.concatenate([x, KING[i, ok][:, None]], axis=1)
                P[i, ok] = mdl.predict(x)
        res.setdefault(tag, {})[Yv] = eval_pred(P, te)
        print(f"  {Yv} 臂{tag}: IC {res[tag][Yv]:+.4f}", flush=True)
print("\n== 判决 ==", flush=True)
cc = np.mean(list(res["C"].values()))
ka = np.mean(list(king_ic.values()))
print(f"臂C 阳性对照(仅king特征): 均值 {cc:+.4f} vs king {ka:+.4f} ⇒ 复原率 {cc/ka*100:.0f}% "
      + ("✓装置有效" if cc >= 0.9*ka else "✗装置仍无效, A/B 不可判"))
aa = np.mean(list(res["A"].values())); bb = np.mean(list(res["B"].values()))
print(f"臂A LGBM纯树(时序滞后特征): 均值 {aa:+.4f} vs king {ka:+.4f} ⇒ DL 相对优势 {(ka-aa)/max(aa,1e-9)*100:+.0f}%")
dv = [res["B"][y_] - king_ic[y_] for y_ in (2023, 2024, 2025, 2026)]
print(f"臂B LGBM(特征+king): 均值 {bb:+.4f}, Δ vs king 逐年 {[round(x,4) for x in dv]} 均值 {np.mean(dv):+.4f}")
ok_ = np.mean(dv) >= 0.003 and all(x >= 0 for x in dv)
print("★臂B PASS: 树在 DL 之上发现结构, 立项" if ok_ else "臂B FAIL ⇒ '树能找到 DL 漏掉的结构'假设关闭(第四条三角测量)")
print("LGBMVSDL_DONE", flush=True)
