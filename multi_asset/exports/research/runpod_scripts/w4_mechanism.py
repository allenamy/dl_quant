"""★ W4 机制关(预注册于 LOG E59, 写在终判之前):
统计过门不等于机制成立。若"更频繁重训"真的在攻 regime 漂移, 则增益应【集中在 regime 切换之后的块】,
而不是随机分布。本脚本用冻结健康分层 H(t) 定位切换点, 再看逐块 Δ 与"切换强度"的关系。

装置:
  切换强度(块 k) = 该块内 H(t) 相对上一块均值的【下探幅度】(负向变化越大 = 切换越剧烈)
  判据: corr(逐块 Δ, 切换强度) > 0 且方向一致; 若 corr ≈ 0 或反号 => 机制解释不成立,
        即使统计过门也只能记为"统计巧合", 不得作为 regime 适应的证据。
"""
import numpy as np, glob, json, datetime as dt
d = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]; Y = d["YR4"]; C = d["CL4"]; ts = d["ts"].astype(np.int64)
ML = np.load("/workspace/data/metalabel.npz", allow_pickle=True); H = ML["H"]
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
        SC = z["scores"]
        for i in keep:
            m = MEM[i] & C[i] & np.isfinite(Y[i])
            if m.sum() < 25: continue
            t_ = zr(np.where(m, Y[i], np.nan))[m]
            hs = np.column_stack([zr(np.where(m, SC[i, :, k], np.nan)) for k in range(SC.shape[2])])
            s_ = zr(np.nanmean(hs, axis=1))[m]
            g = np.isfinite(t_) & np.isfinite(s_)
            if g.sum() >= 20: out[i] = float(np.corrcoef(s_[g], t_[g])[0, 1])
        del SC
    return out

ROLL = [t for t in ("roll8_yr4", "roll8_yr4_s2027", "roll8_yr4_s3037", "roll8_yr4_s4047")
        if __import__("os").path.exists(f"/workspace/exports_train/wide_harness_{t}.json")]
REF = [t for t in ("yfold_ref8", "yfold_ref8_s2027", "yfold_ref8_s3037")
       if __import__("os").path.exists(f"/workspace/exports_train/wide_harness_{t}.json")]
print("滚动 %s | 年度 %s" % (ROLL, REF), flush=True)
A = {t: anchor_ic(t) for t in ROLL}; B = {t: anchor_ic(t) for t in REF}
common = sorted(set.intersection(*[set(v) for v in list(A.values()) + list(B.values())]))
print("共同锚 %d" % len(common), flush=True)
ra = np.array([np.mean([A[t][i] for t in A]) for i in common])
rb = np.array([np.mean([B[t][i] for t in B]) for i in common])
R = np.array(common)
nb = 8; edges = np.linspace(0, len(R), nb + 1).astype(int)
print("\n%-4s %6s %8s %8s %9s | %9s %9s %s" % ("块", "n", "滚动", "年度", "Δ", "块内H均", "vs上块", "日历"))
dl, sw = [], []
prevH = None
for k in range(nb):
    sl = slice(edges[k], edges[k+1]); idx = R[sl]
    a = np.nanmean(ra[sl]); b = np.nanmean(rb[sl]); delta = a - b
    hk = np.nanmean(H[idx])
    dH = (hk - prevH) if prevH is not None else np.nan
    prevH = hk
    t0 = dt.datetime.fromtimestamp(int(ts[idx[0]])/1000, dt.timezone.utc).strftime("%Y-%m")
    t1 = dt.datetime.fromtimestamp(int(ts[idx[-1]])/1000, dt.timezone.utc).strftime("%Y-%m")
    print("%-4d %6d %8.4f %8.4f %+9.4f | %9.4f %+9.4f %s~%s" % (k, len(idx), a, b, delta, hk, dH, t0, t1), flush=True)
    if k > 0: dl.append(delta); sw.append(-dH)      # 切换强度 = H 的下探幅度(取负号使"越负=切换越剧烈"变正)
dl = np.array(dl); sw = np.array(sw)
ok = np.isfinite(dl) & np.isfinite(sw)
c = float(np.corrcoef(dl[ok], sw[ok])[0, 1]) if ok.sum() >= 3 else np.nan
print("\n★ 机制关: corr(逐块Δ, 该块相对上块的健康度下探) = %+.3f  (n=%d)" % (c, ok.sum()))
print("   判读: >0 且明显 ⇒ 增益确实集中在 regime 恶化之后(机制成立)")
print("         ≈0 或 <0 ⇒ 【统计即使过门也只能记为巧合】, 不得作为 regime 适应证据")
print("W4_MECHANISM_DONE")
