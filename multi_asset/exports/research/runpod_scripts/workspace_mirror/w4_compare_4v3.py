"""W4 判据比较器 —— 滚动重训(约4月) vs 年度重训, 同期同锚。
预注册判据(/workspace/w4.sh): 重叠期 Δens ≥ +0.003 且【逐块 IC 差 ≥0 的块占比 > 60%】。
今日四条教训全部内建:
  1) 双种子(roll8 两颗) + 同期对照(yfold_ref8), 不用单臂/异期基线
  2) 只报可判读的量, 不混口径(统一 YR4/CL4, 头均先逐头 z-rank 再平均)
  3) 共同锚集取交集后再比
  4) npz 逐折物化, 不在循环里索引
"""
import numpy as np, glob, json, sys

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

def anchor_ic(tag, rowset=None):
    out = {}
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f); te = z["te_rows"]
        keep = [int(i) for i in te if rowset is None or int(i) in rowset]
        if not keep: continue
        SC = z["scores"]                                  # 逐折物化一次
        for i in keep:
            m = MEM[i] & C[i] & np.isfinite(Y[i])
            if m.sum() < 25: continue
            t_ = zr(np.where(m, Y[i], np.nan))[m]
            hs = np.column_stack([zr(np.where(m, SC[i, :, k], np.nan)) for k in range(SC.shape[2])])
            s_ = zr(np.nanmean(hs, axis=1))[m]
            X = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan))[m] for k in BI])
            g = np.isfinite(t_) & np.isfinite(s_) & np.all(np.isfinite(X), axis=1)
            if g.sum() < 20: continue
            t2, s2, X2 = t_[g], s_[g], X[g]
            A = np.column_stack([np.ones(len(X2)), X2])
            beta, *_ = np.linalg.lstsq(A, s2, rcond=None)
            rs = s2 - A @ beta
            out[i] = (float(np.corrcoef(s2, t2)[0, 1]),
                      float(np.corrcoef(rs, t2)[0, 1]) if rs.std() > 1e-9 else np.nan)
        del SC
    return out

ROLL = ["roll8_yr4", "roll8_yr4_s2027", "roll8_yr4_s3037", "roll8_yr4_s4047"]
REF = ["yfold_ref8", "yfold_ref8_s2027", "yfold_ref8_s3037"]
have = lambda t: __import__("os").path.exists(f"/workspace/exports_train/wide_harness_{t}.json")  # ★必须【完整】臂: 部分折会把交集压缩到极小样本
ROLL = [t for t in ROLL if have(t)]; REF = [t for t in REF if have(t)]
if not ROLL or not REF:
    print("尚缺臂: ROLL=%s REF=%s" % (ROLL, REF)); sys.exit(0)

A = {t: anchor_ic(t) for t in ROLL}
B = {t: anchor_ic(t) for t in REF}
common = set.intersection(*[set(v) for v in list(A.values()) + list(B.values())])
common = sorted(common)
print("共同锚 %d(滚动 %s / 年度 %s)" % (len(common), [len(A[t]) for t in ROLL], [len(B[t]) for t in REF]), flush=True)

def agg(dd, key):
    return np.array([np.mean([dd[t][i][key] for t in dd]) for i in common])
roll_tot = agg(A, 0); roll_res = agg(A, 1)
ref_tot = agg(B, 0); ref_res = agg(B, 1)
print("\n%-14s %8s %8s" % ("", "总分IC", "残差IC"))
print("%-14s %8.4f %8.4f" % ("滚动(约4月)", np.nanmean(roll_tot), np.nanmean(roll_res)))
print("%-14s %8.4f %8.4f" % ("年度重训", np.nanmean(ref_tot), np.nanmean(ref_res)))
dt = np.nanmean(roll_tot) - np.nanmean(ref_tot)
dr = np.nanmean(roll_res) - np.nanmean(ref_res)
print("%-14s %+8.4f %+8.4f" % ("Δ(滚动−年度)", dt, dr))

R = np.array(common); nb = 8
edges = np.linspace(0, len(R), nb + 1).astype(int)
wins = 0; tot = 0
print("\n逐块(8 块, 与滚动重训的重训边界对齐):")
for k in range(nb):
    sl = slice(edges[k], edges[k + 1])
    a = np.nanmean(roll_tot[sl]); b = np.nanmean(ref_tot[sl])
    tot += 1; wins += int(a - b >= 0)
    print("  块%d n=%4d  滚动 %.4f  年度 %.4f  Δ %+.4f %s" % (k, edges[k+1]-edges[k], a, b, a-b, "✓" if a>=b else ""))
frac = wins / max(tot, 1)
print("\n逐块 Δ≥0 占比 = %.0f%% (判据 >60%%)" % (100 * frac))
ok = (dt >= 0.003) and (frac > 0.60)
print("★ 预注册判据: Δens ≥ +0.003 且 逐块占比 >60%%  ⇒  %s" % ("过门" if ok else "不过门"))
print("W4_COMPARE_DONE")
