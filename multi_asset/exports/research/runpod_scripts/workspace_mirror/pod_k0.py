"""K0: king-vs-同输入树 的缺失基线(king 本体战役前置, 用户命题 2026-08-14).
问题: king(1h宽面板DL)对【同输入】的树优势从未被测量; 若树逼近 ⇒ king 未吃净自身输入,
    森林/FiLM 结构移植有空间(K1 立项); 若 king 远甩树 ⇒ 门廉价关闭.
装置: 面板 CH 通道(剔除 betaadj* — 11h 前视脏通道喂树会假高)snapshot + 滞后{24,96,168}行(1h行=1/4/7天)
    + 全部横截面秩孪生(树v2教训), LGBM, 探针判官(4折逐年, xsec rank-IC vs Y4 raw).
对照: king 探针口径记录值 fresh 0.0612 / 逐年在册 ~0.0674(锚集微差, 判读带此警告); 树v2@5m = 0.0635.
"""
import sys, time, glob; sys.path.insert(0, '/workspace')
import numpy as np
from zload import zload
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb
P = zload('/workspace/data/wide_dl_pm32_hz.npz', allow_pickle=True)
ts_ms = P['ts'].astype(np.int64); Y4 = P['Y4'].astype(np.float32); MEM = P['MEMBER110']
CH = P['CH'].astype(np.float32); CHN = [str(c) for c in P['ch_names']]
keep = [j for j, c in enumerate(CHN) if 'betaadj' not in c]
print(f"通道 {len(CHN)} 剔除 {len(CHN)-len(keep)} 个 betaadj* 后 {len(keep)}: {[CHN[j] for j in range(len(CHN)) if j not in keep]} 被剔", flush=True)
T, N = Y4.shape
rows4 = np.arange(0, T, 4)
anchors = [r for r in rows4 if (MEM[r] & np.isfinite(Y4[r])).sum() >= 30]
yrs = np.array([time.gmtime(ts_ms[r]//1000).tm_year for r in anchors])
LAGS = (0, 24, 96, 168)
FEA_CACHE = {}
def feats(i):
    if i in FEA_CACHE: return FEA_CACHE[i]
    r = anchors[i]
    if r - max(LAGS) < 0:
        FEA_CACHE[i] = None
        return None
    m = np.where(MEM[r] & np.isfinite(Y4[r]))[0]
    Fs = []
    for L in LAGS:
        X = np.nan_to_num(np.clip(CH[r - L][m][:, keep], -8, 8))
        XR = np.stack([rankdata(X[:, j])/max(len(m)-1, 1) - 0.5 for j in range(X.shape[1])], -1)
        Fs += [X, XR]
    out = (m, np.concatenate(Fs, -1).astype(np.float32))
    FEA_CACHE[i] = out
    return out
res = {}
for YV in (2023, 2024, 2025, 2026):
    first_te = int(np.where(yrs == YV)[0][0])
    tr_all = [i for i in range(len(anchors)) if yrs[i] < YV and i < first_te - 60]
    cut = int(len(tr_all)*0.85); tr1, va1 = tr_all[:cut], tr_all[cut:]
    te = list(np.where(yrs == YV)[0])
    def xy(idx):
        X, Y = [], []
        for i in idx:
            f = feats(i)
            if f is None: continue
            m, fx = f
            rr = rankdata(Y4[anchors[i], m]); yz = (rr-(len(m)+1)/2)/max(len(m)-1, 1)
            X.append(fx); Y.append(yz)
        return (np.concatenate(X), np.concatenate(Y)) if X else (None, None)
    Xtr, Ytr = xy(tr1); Xva, Yva = xy(va1)
    ds = lgb.Dataset(Xtr, Ytr); dv = lgb.Dataset(Xva, Yva, reference=ds)
    mdl = lgb.train({'objective': 'regression', 'learning_rate': 0.05, 'num_leaves': 63,
                     'feature_fraction': 0.8, 'bagging_fraction': 0.8, 'bagging_freq': 1,
                     'min_data_in_leaf': 200, 'verbose': -1}, ds, 800, valid_sets=[dv],
                    callbacks=[lgb.early_stopping(50, verbose=False)])
    tics = []
    for i in te:
        f = feats(i)
        if f is None: continue
        m, fx = f
        p = mdl.predict(fx)
        ok = np.isfinite(Y4[anchors[i], m])
        if ok.sum() >= 10:
            tics.append(spearmanr(p[ok], Y4[anchors[i], m][ok]).correlation)
    res[YV] = float(np.nanmean(tics))
    print(f"== {YV}: treeK {res[YV]:+.4f} (best_iter {mdl.best_iteration})", flush=True)
mean = float(np.mean(list(res.values())))
print(f"K0[树@king输入] 判(探针判官 raw-Y4 口径; 对照 king 记录值 fresh 0.0612/逐年~0.0674, 锚集微差警告; "
      f"树v2@5m=0.0635): 均值 {mean:+.4f} ⇒ " +
      ("king 领先<0.005 ⇒ K1 森林/FiLM 移植立项有据" if mean > 0.0612-0.005 else "king 远甩树 ⇒ 结构移植门关闭倾向"), flush=True)
print("K0_DONE", flush=True)
