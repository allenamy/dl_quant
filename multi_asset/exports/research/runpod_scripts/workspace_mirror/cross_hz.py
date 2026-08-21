"""★ 视界翻译问题: y12 训出来的模型, 在【书实际兑现的 4h 收益】上值多少?
这是 y12 提案的决定性一问 —— 此前所有 y12 读数都是"对 YR12 评"; 而在役书是 4h 锚。
装置: 用已存的逐锚分数, 强制换成 YR4/CL4 评分, 与 y4 原生模型同尺对比。
输出: 总分/风格/残差 三分解 + Q0/Q4, 与 style_resid 同口径(逐头 z-rank 后平均)。
"""
import numpy as np, glob, sys, json
PAN = "/workspace/data/wide_dl_pm32_hz.npz"
d = np.load(PAN, allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]
BC = [str(v) for v in d["baseline_cols"]]; NM = [str(v) for v in d["ch_names"]]
BI = [NM.index(b) for b in BC]
S = np.load("/workspace/data/regime_strata.npz"); QUINT = S["quint"]

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def card(tag, eval_h):
    Y = d[f"YR{eval_h}"]; C = d[f"CL{eval_h}"]
    fs = sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz"))
    if not fs: return None
    R, T, St, Rs = [], [], [], []
    for f in fs:
        z = np.load(f); sc = z["scores"]; te = z["te_rows"]
        for i in te:
            m = MEM[i] & C[i] & np.isfinite(Y[i])
            if m.sum() < 25: continue
            t_ = zr(np.where(m, Y[i], np.nan))[m]
            hs = np.column_stack([zr(np.where(m, sc[i, :, k], np.nan)) for k in range(sc.shape[2])])
            s_ = zr(np.nanmean(hs, axis=1))[m]
            X = np.column_stack([zr(np.where(m, CH[i, :, k], np.nan))[m] for k in BI])
            g = np.isfinite(t_) & np.isfinite(s_) & np.all(np.isfinite(X), axis=1)
            if g.sum() < 20: continue
            t2, s2, X2 = t_[g], s_[g], X[g]
            A = np.column_stack([np.ones(len(X2)), X2])
            beta, *_ = np.linalg.lstsq(A, s2, rcond=None)
            sh = A @ beta; rs = s2 - sh
            R.append(i); T.append(float(np.corrcoef(s2, t2)[0, 1]))
            St.append(float(np.corrcoef(sh, t2)[0, 1]) if sh.std() > 1e-9 else np.nan)
            Rs.append(float(np.corrcoef(rs, t2)[0, 1]) if rs.std() > 1e-9 else np.nan)
    R = np.array(R); T = np.array(T); St = np.array(St); Rs = np.array(Rs); q = QUINT[R]
    f = lambda a, sel: float(np.nanmean(a[sel])) if sel.sum() else np.nan
    return dict(tag=tag, eval_h=eval_h, n=len(R), tot=float(np.nanmean(T)),
                sty=float(np.nanmean(St)), res=float(np.nanmean(Rs)),
                totQ0=f(T, q == 0), totQ4=f(T, q == 4), resQ0=f(Rs, q == 0), resQ4=f(Rs, q == 4))

print("%-24s %5s %6s | %7s %7s %7s | %7s %7s | %7s %7s" % (
    "臂", "评视界", "n", "总分", "风格", "残差", "总Q0", "总Q4", "残Q0", "残Q4"), flush=True)
for tag, h in [(t, int(h)) for t, h in (a.split(":") for a in sys.argv[1:])]:
    r = card(tag, h)
    if not r: print("%-24s 无分数" % tag); continue
    print("%-24s %5d %6d | %7.4f %7.4f %7.4f | %7.4f %7.4f | %7.4f %7.4f" % (
        r["tag"], r["eval_h"], r["n"], r["tot"], r["sty"], r["res"],
        r["totQ0"], r["totQ4"], r["resQ0"], r["resQ4"]), flush=True)
print("CROSS_HZ_DONE", flush=True)
