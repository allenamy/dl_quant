"""HIST 变体(2020 起缓存): 与 pod_panel_wide.py 逐字同构, 仅 CACHE_IN/PANEL_OUT 参数化. 装置入库于 devices_2026-08-21."""
"""宽 4h 因子面板 @pod: 从 wide829 缓存(含306退市币, 幸存者干净)+ funding zips 建 zoo 扫地基.
通道: ret5/range/cpos/log_qv/log_cnt/log_avgsz/tbf; 全部因子只用 ≤锚 数据(因果).
funding 限 450 现存币(退市币 NaN, wide-v1 口径旗标); funding_ema 半衰期 3 天(非在役书精确口径, 引用带标).
产物: /workspace/data/wide_panel_4h_v1.npz(ts/symbols/elig/Y4/Y24/因子字典) + SHA 打印.
"""
import os, io, csv, json, time, zipfile, glob, hashlib
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
import os
Z = zload(os.environ.get("CACHE_IN","/workspace/data/dlnative_5m_wide829_f16_hist.npz"), allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]
NW = len(syms); TT = CD.shape[0]
print(f"cache {TT}x{NW}", flush=True)
def cs(x):
    xz = np.where(np.isfinite(x), x, 0).astype(np.float64)
    return np.concatenate([np.zeros((1, NW)), np.cumsum(xz, 0)])
r5 = CD[:, :, 0].astype(np.float32)
fin = np.isfinite(r5)
CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
CS_r = cs(r5); CS_r2 = cs(r5.astype(np.float64) ** 2)
qv = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], np.nan).astype(np.float32)
CS_q = cs(np.expm1(np.clip(qv, 0, 30)))          # log_qv -> 原量能(单位任意, 只作比值/秩)
CS_rng = cs(CD[:, :, 1].astype(np.float32))
CS_cpos = cs(CD[:, :, 2].astype(np.float32))
CS_tbf = cs(CD[:, :, 6].astype(np.float32))
CS_asz = cs(CD[:, :, 5].astype(np.float32))
del r5, qv
grid = np.where(CTS % 14400 == 0)[0]
W7 = 2016
grid = grid[(grid >= 8640) & (grid + 288 <= TT)]
E = grid; S7 = E - W7
n7 = np.maximum(CS_f[E] - CS_f[S7], 1)
covr = (CS_f[E] - CS_f[S7]) / W7
m7 = (CS_r[E] - CS_r[S7])
v7 = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S7]) / n7 - (m7 / n7) ** 2, 0))
elig = (covr >= 0.95) & (v7 >= 1e-4)
def wsum(CSx, w):
    return (CSx[E] - CSx[E - w]).astype(np.float32)
def wmean(CSx, w):
    nf = np.maximum(CS_f[E] - CS_f[E - w], 1)
    return ((CSx[E] - CSx[E - w]) / nf).astype(np.float32)
F = {}
F["rev_4h"] = wsum(CS_r, 48); F["rev_24h"] = wsum(CS_r, 288); F["rev_3d"] = wsum(CS_r, 864)
F["mom_7d"] = wsum(CS_r, 2016); F["mom_30d"] = wsum(CS_r, 8640)
F["mom_7d_x24"] = (wsum(CS_r, 2016) - wsum(CS_r, 288))            # 跳近端动量
F["vol_7d"] = v7.astype(np.float32)
qv24 = wsum(CS_q, 288); qv7d = wsum(CS_q, 2016)
with np.errstate(divide="ignore", invalid="ignore"):
    F["volq_ratio"] = np.where(qv7d > 0, qv24 / (qv7d / 7.0), np.nan).astype(np.float32)
    F["amihud_24h"] = np.where(qv24 > 0, np.abs(F["rev_24h"]) / qv24 * 1e6, np.nan).astype(np.float32)
F["range_24h"] = wmean(CS_rng, 288); F["cpos_24h"] = wmean(CS_cpos, 288)
F["tbf_24h"] = wmean(CS_tbf, 288); F["asz_24h"] = wmean(CS_asz, 288)
y4n = CS_f[E + 48] - CS_f[E]
Y4 = wsum(CS_r, -48) * np.nan  # 占位防误用
Y4 = (CS_r[E + 48] - CS_r[E]).astype(np.float32); Y4[y4n < 46] = np.nan
y24n = CS_f[E + 288] - CS_f[E]
Y24 = (CS_r[E + 288] - CS_r[E]).astype(np.float32); Y24[y24n < 280] = np.nan
del CS_r, CS_r2, CS_q, CS_rng, CS_cpos, CS_tbf, CS_asz
# ---- funding: 450 现存币 zips -> 逐结算 -> 锚对齐 ----
fdir = "/workspace/wide_multisrc/funding"
fund_now = np.full((len(E), NW), np.nan, np.float32)
fund_ema = np.full((len(E), NW), np.nan, np.float32)
anchor_s = CTS[E]
HL = 3 * 86400.0
n_fund = 0
for sym_dir in sorted(glob.glob(fdir + "/*")):
    s = os.path.basename(sym_dir)
    if s not in syms: continue
    j = syms.index(s)
    rows = []
    for zp in sorted(glob.glob(sym_dir + "/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                for row in rd:
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower():
                        continue
                    try:
                        # 列序: calc_time(ms), funding_interval_hours?, rate — 以头两可解析列为 (ts, rate) 或 (ts,_,rate)
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        rows.append((ts_ // 1000, rate))
                    except Exception:
                        continue
        except Exception:
            continue
    if not rows: continue
    rows.sort()
    ft = np.array([r[0] for r in rows], np.int64); fr = np.array([r[1] for r in rows], np.float64)
    ema = np.full(len(fr), np.nan)
    acc, prev_t = None, None
    for k in range(len(fr)):
        if acc is None: acc = fr[k]
        else:
            dt = max(ft[k] - prev_t, 1)
            a = 1 - 0.5 ** (dt / HL)
            acc = acc + a * (fr[k] - acc)
        prev_t = ft[k]; ema[k] = acc
    pos = np.searchsorted(ft, anchor_s, side="right") - 1
    okp = pos >= 0
    fund_now[okp, j] = fr[pos[okp]].astype(np.float32)
    fund_ema[okp, j] = ema[pos[okp]].astype(np.float32)
    # 结算距锚 >12h 视为停更, 置 NaN(防退市尾部陈旧值)
    stale = okp & ((anchor_s - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12 * 3600)
    fund_now[stale, j] = np.nan; fund_ema[stale, j] = np.nan
    n_fund += 1
F["fund_now"] = fund_now; F["fund_ema"] = fund_ema
print(f"funding 币数 {n_fund}", flush=True)
out = os.environ.get("PANEL_OUT","/workspace/data/wide_panel_4h_hist.npz")
np.savez_compressed(out, ts=CTS[E], symbols=np.array(syms), elig=elig, Y4=Y4, Y24=Y24,
                    **{("f_" + k): v for k, v in F.items()})
h = hashlib.sha256(open(out, "rb").read()).hexdigest()[:16]
print(f"PANEL_DONE anchors {len(E)} elig均值 {elig.sum(1).mean():.0f} SHA {h}", flush=True)
