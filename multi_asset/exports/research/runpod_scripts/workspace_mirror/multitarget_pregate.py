"""多目标 pre-gate: 族特征在【非收益目标】上是否有增量?
T1 波动目标: fwd 24h 实现波动(xsec rank) — book/metrics 的天然主场(#32 尺寸直接受益)
T2 频带目标: y8−y4, y24−y8(多尺度分解的增量带) — 特征在不同频带的差异化含量
判据: Δ ≥ +0.005(波动目标信噪比高, 门槛提高) / 频带 Δ ≥ +0.003
v2: npz 一次性物化(修复逐索引全量解压), FVOL 分块(防大瞬时分配), faulthandler"""
import numpy as np, datetime as dt, faulthandler
faulthandler.enable()
R = np.load("/workspace/data/wide_dl_prodmask32.npz", allow_pickle=True)
M = np.load("/workspace/data/metrics_hourly.npz", allow_pickle=True)
B5 = np.load("/workspace/data/book5_hourly.npz", allow_pickle=True)
P = np.load("/workspace/data/panel_targets.npz", allow_pickle=True)
S8 = np.load("/workspace/data/y8y12_sidecar.npz", allow_pickle=True)
MEM = R["MEMBER110"]
CH = R["CH"]; MX = M["X"]; B5X = B5["X"]
Y1 = P["Y1"]; Y4 = P["Y4"]; Y24 = P["Y24"]; Y8 = S8["Y8"]
TS = np.asarray(P["ts"]).astype(np.int64)
T, N = Y4.shape
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in TS])
print("物化完成 CH%s MX%s B5X%s" % (CH.shape, MX.shape, B5X.shape), flush=True)
# 目标构造(分块, 上限 ~90MB 瞬时)
from numpy.lib.stride_tricks import sliding_window_view
FVOL = np.full((T, N), np.nan, np.float32)
with np.errstate(all="ignore"):
    sw = sliding_window_view(Y1, 24, axis=0)
    for _s in range(0, sw.shape[0], 4096):
        _v = np.nanstd(sw[_s:_s+4096], axis=-1); FVOL[_s:_s+_v.shape[0]] = _v
BAND1 = Y8 - Y4          # 4-8h 增量带
BAND2 = Y24 - Y8         # 8-24h 增量带
print("目标构造完成", flush=True)
def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o
rows = np.array([i for i in range(24, T-30) if i % 4 == 0])
def run(target, extra):
    ics = []
    for y in (2024, 2025, 2026):
        tr = rows[YEAR[rows] < y]; te = rows[YEAR[rows] == y]
        XS, YS = [], []
        for i in tr[::2]:
            m = MEM[i] & np.isfinite(target[i])
            if m.sum() < 25: continue
            c = [zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)]
            if extra == "met": c += [zr(np.where(m, MX[i,:,k], np.nan)) for k in range(21)]
            if extra == "book": c += [zr(np.where(m, B5X[i,:,k], np.nan)) for k in range(22)]
            XS.append(np.nan_to_num(np.column_stack(c)[m])); YS.append(zr(np.where(m, target[i], np.nan))[m])
        A = np.vstack(XS); b = np.concatenate(YS)
        mu, sd = A.mean(0), A.std(0)+1e-9
        w = np.linalg.solve(((A-mu)/sd).T@((A-mu)/sd)+200*np.eye(A.shape[1]), ((A-mu)/sd).T@b)
        per = []
        for i in te:
            m = MEM[i] & np.isfinite(target[i])
            if m.sum() < 25: continue
            c = [zr(np.where(m, CH[i,:,k], np.nan)) for k in range(32)]
            if extra == "met": c += [zr(np.where(m, MX[i,:,k], np.nan)) for k in range(21)]
            if extra == "book": c += [zr(np.where(m, B5X[i,:,k], np.nan)) for k in range(22)]
            a = np.nan_to_num(np.column_stack(c)[m])
            p = zr((a-mu)/sd@w); t_ = zr(np.where(m, target[i], np.nan))[m]
            ok = np.isfinite(p)&np.isfinite(t_)
            if ok.sum() >= 20: per.append(float((p[ok]*t_[ok]).mean()))
        ics.append(float(np.mean(per)))
    return np.mean(ics)
for tn, tgt in (("fwd_vol24", FVOL), ("band_4_8h", BAND1), ("band_8_24h", BAND2)):
    b0 = run(tgt, None); bm = run(tgt, "met"); bb = run(tgt, "book")
    print("%-11s 32ch %.4f | +metrics %+.4f | +book %+.4f" % (tn, b0, bm-b0, bb-b0), flush=True)
print("MT_PREGATE_DONE", flush=True)
