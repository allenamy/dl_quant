"""resid_alpha 特征: 逐币尾随残差均值(因果) — P1 发现的持久身份 alpha 的显式版。
构造: 每锚, 用【截至该锚】拟合的 ridge 预测, 残差入库; 特征 = 该币过去 180 天残差均值。
严格因果: 残差只用 ≤t 的模型与 ≤t 的实现; 特征在 t 只汇总 <t-24h 的残差(标签周期隔离)。
判据: 32ch+resid_alpha vs 32ch 逐年 OOS, Δ≥+0.003 无反号 ⇒ 进面板候选。"""
import numpy as np, pandas as pd, datetime as dt
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
CH = R["CH"]; MEM = R["MEMBER110"]; Y4 = P["Y4"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
rows = np.array([i for i in range(24, T-8) if i % 4 == 0])
# 半年重拟合的走前 ridge, 逐锚记录残差
RES = np.full((T, N), np.nan, np.float32)
refit = rows[::1080//4]  # 约半年一个重拟合点
w = None; mu = None; sd = None
seg_start = 0
for si, r0 in enumerate(list(refit) + [rows[-1]+1]):
    if si > 0 and w is not None:
        seg = rows[(rows >= seg_start) & (rows < r0)]
        for i in seg:
            m = MEM[i] & np.isfinite(Y4[i])
            if m.sum() < 25: continue
            a = np.nan_to_num(np.column_stack([zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)])[m])
            p = (a-mu)/sd @ w
            t_ = zr(np.where(m, Y4[i], np.nan))[m]
            resid = t_ - p*(np.nanstd(t_)/max(np.nanstd(p),1e-9))
            RES[i, np.where(m)[0]] = resid
    tr = rows[rows < r0][-2160//4*6:]   # 最近~半年训练
    if len(tr) < 300: seg_start = r0; continue
    XS, YS = [], []
    for i in tr[::3]:
        m = MEM[i] & np.isfinite(Y4[i])
        if m.sum() < 25: continue
        a = np.column_stack([zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)])[m]
        XS.append(np.nan_to_num(a)); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
    A = np.vstack(XS); b = np.concatenate(YS)
    mu, sd = A.mean(0), A.std(0)+1e-9
    w = np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+200*np.eye(32), ((A-mu)/sd).T@b)
    seg_start = r0
# 特征: 过去 180 天(1080 锚行)残差均值, 隔离 24h
RA = np.full((T, N), np.nan, np.float32)
res_df = pd.DataFrame(RES)
ra = res_df.rolling(1080, min_periods=180).mean().shift(6)   # shift 6 行=24h 隔离
RA = ra.values.astype(np.float32)
print("resid_alpha 覆盖率 %.3f" % np.isfinite(RA[rows]).mean())
# 增量测试
def run(with_ra):
    ics = []
    for y in (2024, 2025, 2026):
        tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
        XS, YS = [], []
        for i in tr[::2]:
            m = MEM[i] & np.isfinite(Y4[i])
            if m.sum() < 25: continue
            cols = [zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)]
            if with_ra: cols.append(zr(np.where(m, RA[i], np.nan)))
            a = np.nan_to_num(np.column_stack(cols)[m])
            XS.append(a); YS.append(zr(np.where(m, Y4[i], np.nan))[m])
        A = np.vstack(XS); b = np.concatenate(YS)
        mu, sd = A.mean(0), A.std(0)+1e-9
        w = np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+200*np.eye(A.shape[1]), ((A-mu)/sd).T@b)
        per = []
        for i in te:
            m = MEM[i] & np.isfinite(Y4[i])
            if m.sum() < 25: continue
            cols = [zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)]
            if with_ra: cols.append(zr(np.where(m, RA[i], np.nan)))
            a = np.nan_to_num(np.column_stack(cols)[m])
            p = zr((a-mu)/sd @ w); t_ = zr(np.where(m, Y4[i], np.nan))[m]
            ok = np.isfinite(p) & np.isfinite(t_)
            if ok.sum() >= 20: per.append(float((p[ok]*t_[ok]).mean()))
        ics.append(float(np.mean(per)))
    return ics
b0 = run(False); b1 = run(True)
print("32ch:          %s  均 %.4f" % (["%+.4f"%x for x in b0], np.mean(b0)))
print("32ch+residα:   %s  均 %.4f" % (["%+.4f"%x for x in b1], np.mean(b1)))
print("Δ = %+.4f  逐年: %s" % (np.mean(b1)-np.mean(b0), ["%+.4f"%(x-y) for x,y in zip(b1,b0)]))
np.savez("/workspace/data/resid_alpha.npz", RA=RA, ts=TS)
print("saved resid_alpha.npz")
