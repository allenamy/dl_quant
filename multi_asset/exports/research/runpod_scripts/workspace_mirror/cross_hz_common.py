"""加固 E56: 把 y12 与 y4 的比较限制在【共同锚集】上, 消除"锚集不同"这个松动。
E56 原读数 y12 n=3345 / y4 n=10037 —— 若 y12 的锚是 y4 的子集, 原比较仍有效但 SE 不同;
若两者只是部分重叠, 则比较本身带偏。本脚本取交集后重算, 两侧同锚同尺。
"""
import numpy as np, glob, sys
d = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]; Y = d["YR4"]; C = d["CL4"]
BC = [str(v) for v in d["baseline_cols"]]; NM = [str(v) for v in d["ch_names"]]
BI = [NM.index(b) for b in BC]
S = np.load("/workspace/data/regime_strata.npz"); QUINT = S["quint"]

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def rows_of(tag):
    R = []
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        R.extend(np.load(f)["te_rows"].tolist())
    return set(R)

TAGS12 = ["rb32_lam0_yr12_s42", "rb32_lam0_yr12_s2027", "rb32_lam0_yr12_s3037"]
TAGS4 = ["rb32_lam0_yr4_s42", "rb32_lam0_yr4_s2027", "rb32_lam0_yr4_s3037"]
r12 = set.intersection(*[rows_of(t) for t in TAGS12])
r4 = set.intersection(*[rows_of(t) for t in TAGS4])
common = sorted(r12 & r4)
print("y12 锚 %d | y4 锚 %d | 交集 %d | y12 是 y4 子集: %s" % (len(r12), len(r4), len(common), r12 <= r4), flush=True)

def card(tag, rows):
    # ★ npz 逐索引访问 = 每次全量解压(NpzFile 不缓存) —— 今日第二次咬。必须逐折物化一次。
    rowset = set(rows)
    pairs = []
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f)
        te = z["te_rows"]
        keep = [int(i) for i in te if int(i) in rowset]
        if not keep: continue
        SC = z["scores"]                       # 物化一次
        for i in keep:
            pairs.append((i, np.array(SC[i])))
        del SC
    T, St, Rs, RR = [], [], [], []
    for i, sc in pairs:
        m = MEM[i] & C[i] & np.isfinite(Y[i])
        if m.sum() < 25: continue
        t_ = zr(np.where(m, Y[i], np.nan))[m]
        hs = np.column_stack([zr(np.where(m, sc[:, k], np.nan)) for k in range(sc.shape[1])])
        s_ = zr(np.nanmean(hs, axis=1))[m]
        X = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan))[m] for k in BI])
        g = np.isfinite(t_) & np.isfinite(s_) & np.all(np.isfinite(X), axis=1)
        if g.sum() < 20: continue
        t2, s2, X2 = t_[g], s_[g], X[g]
        A = np.column_stack([np.ones(len(X2)), X2])
        beta, *_ = np.linalg.lstsq(A, s2, rcond=None)
        sh = A @ beta; rs = s2 - sh
        RR.append(i); T.append(float(np.corrcoef(s2, t2)[0, 1]))
        St.append(float(np.corrcoef(sh, t2)[0, 1]) if sh.std() > 1e-9 else np.nan)
        Rs.append(float(np.corrcoef(rs, t2)[0, 1]) if rs.std() > 1e-9 else np.nan)
    RR = np.array(RR); q = QUINT[RR]
    f = lambda a, s: float(np.nanmean(np.array(a)[s])) if s.sum() else np.nan
    return len(RR), float(np.nanmean(T)), float(np.nanmean(St)), float(np.nanmean(Rs)), f(Rs, q == 4)

print("\n%-24s %6s | %8s %8s %8s %8s" % ("臂(共同锚集, 评 YR4)", "n", "总分", "风格", "残差", "残Q4"), flush=True)
for t in TAGS12 + TAGS4:
    n, a, b, c, e = card(t, common)
    print("%-24s %6d | %8.4f %8.4f %8.4f %8.4f" % (t, n, a, b, c, e), flush=True)
print("CROSS_COMMON_DONE", flush=True)
