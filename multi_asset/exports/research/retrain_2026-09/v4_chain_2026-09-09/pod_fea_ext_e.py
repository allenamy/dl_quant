"""ext 特征 E 版(PREREG_king_clock_E_2026-09-09 §2): pod_fea_ext_clamp.py 逐字, 只改时钟 —
 窗口/成员统计半开上界 hi = E+1(窗 [E-w+1, E], 与生产 shadow_loop_v3 wstat 同窗); 标签 y4 = 行 [E+1, E+48](与 DL/记账同窗)。数值口径不动(float64 累积, float16 存储)."""
import time, hashlib
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
from scipy.stats import rankdata
import os as _os
Z = zload(_os.environ.get("CACHE_IN", "/workspace/data/dlnative_5m_wide829_f16_ext.npz"), allow_pickle=True)
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
grid = grid[(grid >= 576) & (grid + 49 <= TT)]   # E版: 标签行 E+48 需存在 (CS 索引 E+49)
E = grid
HI = E + 1                                        # E版: 半开上界 => 最后一行 = E (收盘于锚时刻)
qv_s, qv_f = CS["log_qv"]
LO7 = np.maximum(HI - 2016, 0)                    # E版: 成员统计窗 [E-2015, E]
n7 = np.maximum(qv_f[HI] - qv_f[LO7], 1)
covr = (CS["ret5"][1][HI] - CS["ret5"][1][LO7]) / 2016
qvm = (qv_s[HI] - qv_s[LO7]) / n7
m7 = (CS["ret5"][0][HI] - CS["ret5"][0][LO7])
v7 = np.sqrt(np.maximum((r2s[HI] - r2s[LO7]) / n7 - (m7 / n7) ** 2, 0))
y4n = CS["ret5"][1][E + 49] - CS["ret5"][1][E + 1]   # E版: 标签行 [E+1, E+48]
y4 = (CS["ret5"][0][E + 49] - CS["ret5"][0][E + 1]).astype(np.float32); y4[y4n < 46] = np.nan
MS, keep = [], []
for i in range(len(E)):
    ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])
    m = np.where(ok)[0]
    if len(m) > 400: m = np.sort(m[np.argsort(-qvm[i, m])[:400]])
    if len(m) >= 50: MS.append(m); keep.append(i)
keep = np.array(keep); E = E[keep]; HI = HI[keep]; y4 = y4[keep]; qvk = qvm[keep]
print(f"anchors {len(E)}", flush=True)
val_names = []
VAL = []
for nm in CHN:
    s_, f_ = CS[nm]
    for w in WINS:
        Ew = np.maximum(HI - w, 0)   # E版: 窗 [E-w+1, E]; clamp >= 0 (E-0909-A)
        nf = np.maximum(f_[HI] - f_[Ew], 1)
        if nm == "ret5":
            VAL.append(((s_[HI] - s_[Ew])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
        else:
            VAL.append(((s_[HI] - s_[Ew]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
for w in WINS:
    Ew = np.maximum(HI - w, 0)   # E版
    nf = np.maximum(CS["ret5"][1][HI] - CS["ret5"][1][Ew], 1)
    mm = (CS["ret5"][0][HI] - CS["ret5"][0][Ew]) / nf
    vv = np.sqrt(np.maximum((r2s[HI] - r2s[Ew]) / nf - mm ** 2, 0))
    VAL.append(vv.astype(np.float32)); val_names.append(f"vol_{w}")
del CS, r2s, r2f, CD
PW = np.load(_os.environ.get("PANEL_IN", "/workspace/data/wide_panel_4h_v2ext.npz"), allow_pickle=True)
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
    j = pw_row.get(int(CTS[E[i]]))
    if j is not None:
        for fv in FUND:
            FEA[i, m, col] = np.nan_to_num(fv[j, m], nan=0); col += 1
    if i % 2000 == 0: print(f"fea {i}/{len(E)} ({time.time()-t1:.0f}s)", flush=True)
np.save(_os.environ.get("FEA_OUT", "/workspace/data/wide_fea_v4e.npy"), FEA)
np.savez_compressed(_os.environ.get("META_OUT", "/workspace/data/wide_fea_v4e_meta.npz"), E_ts=CTS[E], members=np.array(MS, dtype=object),
                    y4=y4, qvk=qvk.astype(np.float32), names=np.array([n + s for n in val_names for s in ("_v", "_r")] + fund_names),
                    feature_row_window="[E-w+1, E] (max_feature_row == E; production wstat clock)", label_row_window="[E+1, E+48]", builder="pod_fea_ext_e.py")
print(f"FEA_EXT_E_DONE {FEA.shape}", flush=True)
