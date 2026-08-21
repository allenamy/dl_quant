"""B 梯队弹药: wide_fea_v1 — 5m缓存7通道×窗{48,288,864,2016,8640}滚动统计×{值,逐锚秩}+funding3列.
锚/成员与 kcurve 装置同构(NTOP=400, 同筛选). 产物: wide_fea_v1.npy(锚×829×NF f16)+ wide_fea_v1_meta.npz.
"""
import time, hashlib
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata
Z = zload("/workspace/data/dlnative_5m_wide829_f16.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]
NW = len(syms); TT = CD.shape[0]
CHN = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
WINS = (48, 288, 864, 2016, 8640)
def cs_pair(x):
    fin = np.isfinite(x)
    xz = np.where(fin, x, 0).astype(np.float64)
    return (np.concatenate([np.zeros((1, NW)), np.cumsum(xz, 0)]),
            np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)]))
CS = {}
t0 = time.time()
for c, nm in enumerate(CHN):
    CS[nm] = cs_pair(CD[:, :, c].astype(np.float32))
    print(f"cumsum {nm} ({time.time()-t0:.0f}s)", flush=True)
r2s, r2f = cs_pair((CD[:, :, 0].astype(np.float64)) ** 2)
grid = np.where(CTS % 14400 == 0)[0]
grid = grid[(grid >= 576) & (grid + 48 <= TT)]
E = grid
# 成员: 与 kcurve 同(覆盖95%/波动1e-4/y4有数/量能top400)
qv_s, qv_f = CS["log_qv"]
n7 = np.maximum(qv_f[E] - qv_f[E - 2016], 1)
covr = (CS["ret5"][1][E] - CS["ret5"][1][np.maximum(E - 2016, 0)]) / 2016
qvm = (qv_s[E] - qv_s[E - 2016]) / n7
m7 = (CS["ret5"][0][E] - CS["ret5"][0][E - 2016])
v7 = np.sqrt(np.maximum((r2s[E] - r2s[E - 2016]) / n7 - (m7 / n7) ** 2, 0))
y4n = CS["ret5"][1][E + 48] - CS["ret5"][1][E]
y4 = (CS["ret5"][0][E + 48] - CS["ret5"][0][E]).astype(np.float32); y4[y4n < 46] = np.nan
MS, keep = [], []
for i in range(len(E)):
    ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])
    m = np.where(ok)[0]
    if len(m) > 400: m = np.sort(m[np.argsort(-qvm[i, m])[:400]])
    if len(m) >= 50: MS.append(m); keep.append(i)
keep = np.array(keep); E = E[keep]; y4 = y4[keep]; qvk = qvm[keep]
print(f"anchors {len(E)}", flush=True)
# 值特征: 每通道每窗 均值(ret5 用和/波动 std 另算)
val_names = []
VAL = []
for nm in CHN:
    s_, f_ = CS[nm]
    for w in WINS:
        nf = np.maximum(f_[E] - f_[E - w], 1)
        if nm == "ret5":
            VAL.append(((s_[E] - s_[E - w])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
        else:
            VAL.append(((s_[E] - s_[E - w]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
for w in WINS:
    nf = np.maximum(CS["ret5"][1][E] - CS["ret5"][1][E - w], 1)
    mm = (CS["ret5"][0][E] - CS["ret5"][0][E - w]) / nf
    vv = np.sqrt(np.maximum((r2s[E] - r2s[E - w]) / nf - mm ** 2, 0))
    VAL.append(vv.astype(np.float32)); val_names.append(f"vol_{w}")
del CS, r2s, r2f, CD
PW = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FUND = [PW["f_fund_ema"], PW["f_fund_now"]]
fund_names = ["fund_ema", "fund_now"]
NVAL = len(VAL); NF = NVAL * 2 + len(FUND)
print(f"NF = {NVAL}值 + {NVAL}秩 + {len(FUND)}funding = {NF}", flush=True)
FEA = np.full((len(E), NW, NF), np.nan, np.float16)
t1 = time.time()
for i in range(len(E)):
    m = MS[i]
    col = 0
    for v in VAL:
        x = v[i, m]
        FEA[i, m, col] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); col += 1
        ok = np.isfinite(x); rr = np.zeros(len(m), np.float32)
        if ok.sum() >= 10:
            rr[ok] = rankdata(x[ok]) / max(ok.sum() - 1, 1) - 0.5
        FEA[i, m, col] = rr; col += 1
        col_backup = col
    j = pw_row.get(int(CTS[E[i]]))
    if j is not None:
        for fv in FUND:
            FEA[i, m, col] = np.nan_to_num(fv[j, m], nan=0); col += 1
    if i % 2000 == 0: print(f"fea {i}/{len(E)} ({time.time()-t1:.0f}s)", flush=True)
np.save("/workspace/data/wide_fea_v1.npy", FEA)
np.savez_compressed("/workspace/data/wide_fea_v1_meta.npz", E_ts=CTS[E], members=np.array(MS, dtype=object),
                    y4=y4, qvk=qvk.astype(np.float32), names=np.array([n + s for n in val_names for s in ("_v", "_r")] + fund_names))
h = hashlib.sha256(open("/workspace/data/wide_fea_v1.npy", "rb").read()).hexdigest()[:16]
print(f"FEA_DONE {FEA.shape} SHA {h}", flush=True)
