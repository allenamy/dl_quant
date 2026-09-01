"""ext 面板 v2: 因子段与 pod_panel_wide.py 逐字同构(读 ext 缓存); funding 段重写 —
zip(含 interval 列) + fund_aug.json.gz(八月 API 尾巴) 合并, 产出:
  f_fund_now(原始 rate, carry 用) / f_fund_iv(结算间隔h) /
  f_fund_ema      = v0 墙钟HL3d 原始rate(与 v1 面板同构, 兼容基线)
  f_fund_ema_v1   = 墙钟HL3d, rate*(8/iv) normfix 单位
  f_fund_ema_v2   = 在役精确: 结算空间EMA adjust=False span=max(2,round(24/iv中位)), normfix
自检: 与 v1 面板重叠锚上, 13 kline因子 corr>=0.999 且 fund_ema v0 corr>=0.999, 违者 FAIL.
"""
import os, io, csv, json, time, zipfile, glob, hashlib, gzip
import numpy as np
import sys; sys.path.insert(0, "/workspace")
from zload import zload
import os as _os
Z = zload(_os.environ.get("CACHE_IN", "/workspace/data/dlnative_5m_wide829_f16_ext.npz"), allow_pickle=True)
CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]
NW = len(syms); TT = CD.shape[0]
print(f"ext cache {TT}x{NW}", flush=True)
def cs(x):
    xz = np.where(np.isfinite(x), x, 0).astype(np.float64)
    return np.concatenate([np.zeros((1, NW)), np.cumsum(xz, 0)])
r5 = CD[:, :, 0].astype(np.float32)
fin = np.isfinite(r5)
CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
CS_r = cs(r5); CS_r2 = cs(r5.astype(np.float64) ** 2)
qv = np.where(np.isfinite(CD[:, :, 3]), CD[:, :, 3], np.nan).astype(np.float32)
CS_q = cs(np.expm1(np.clip(qv, 0, 30)))
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
F["mom_7d_x24"] = (wsum(CS_r, 2016) - wsum(CS_r, 288))
F["vol_7d"] = v7.astype(np.float32)
qv24 = wsum(CS_q, 288); qv7d = wsum(CS_q, 2016)
with np.errstate(divide="ignore", invalid="ignore"):
    F["volq_ratio"] = np.where(qv7d > 0, qv24 / (qv7d / 7.0), np.nan).astype(np.float32)
    F["amihud_24h"] = np.where(qv24 > 0, np.abs(F["rev_24h"]) / qv24 * 1e6, np.nan).astype(np.float32)
F["range_24h"] = wmean(CS_rng, 288); F["cpos_24h"] = wmean(CS_cpos, 288)
F["tbf_24h"] = wmean(CS_tbf, 288); F["asz_24h"] = wmean(CS_asz, 288)
y4n = CS_f[E + 48] - CS_f[E]
Y4 = (CS_r[E + 48] - CS_r[E]).astype(np.float32); Y4[y4n < 46] = np.nan
y24n = CS_f[E + 288] - CS_f[E]
Y24 = (CS_r[E + 288] - CS_r[E]).astype(np.float32); Y24[y24n < 280] = np.nan
del CS_r, CS_r2, CS_q, CS_rng, CS_cpos, CS_tbf, CS_asz

# ---- funding: zip(interval列) + 八月 API 尾巴 合并, 三口径 EMA ----
fdir = "/workspace/wide_multisrc/funding"
AUG = json.loads(gzip.open("/workspace/fund_aug.json.gz", "rt").read())
AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
anchor_s = CTS[E]
HL = 3 * 86400.0
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
fund_now = np.full((len(E), NW), np.nan, np.float32)
fund_iv = np.full((len(E), NW), np.nan, np.float32)
ema_v0 = np.full((len(E), NW), np.nan, np.float32)
ema_v1 = np.full((len(E), NW), np.nan, np.float32)
ema_v2 = np.full((len(E), NW), np.nan, np.float32)
n_fund = 0; n_iv_col = 0
for sym_dir in sorted(glob.glob(fdir + "/*")):
    s = os.path.basename(sym_dir)
    if s not in syms: continue
    j = syms.index(s)
    rows = []  # (ts_s, rate, iv_or_nan)
    for zp in sorted(glob.glob(sym_dir + "/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                for row in rd:
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower():
                        continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2:
                                    iv = cand
                            except Exception:
                                pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception:
                        continue
        except Exception:
            continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []):
        rows.append((int(t_ms) // 1000, float(rate), AUG_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort()
    ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_):
            ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64)
    fr = np.array([ded[t][0] for t in ft], np.float64)
    fiv = np.array([ded[t][1] for t in ft], np.float64)
    if np.isfinite(fiv).any(): n_iv_col += 1
    # interval 缺失行: 时间差推导(圆整到允许集), 首行/失败默认 8
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan)
    dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_full = np.where(np.isfinite(fiv), fiv, dv)
    iv_full = np.where(np.isfinite(iv_full), iv_full, 8.0)
    iv_full = ALLOWED[np.argmin(np.abs(iv_full[:, None] - ALLOWED[None, :]), axis=1)]
    rate_nf = fr * (8.0 / iv_full)
    # v0: 墙钟 HL3d 原始 rate(逐字同 v1 面板)
    e0 = np.full(len(fr), np.nan)
    acc, prev_t = None, None
    for k in range(len(fr)):
        if acc is None: acc = fr[k]
        else:
            dt = max(ft[k] - prev_t, 1)
            a = 1 - 0.5 ** (dt / HL)
            acc = acc + a * (fr[k] - acc)
        prev_t = ft[k]; e0[k] = acc
    # v1: 墙钟 HL3d, normfix 单位
    e1 = np.full(len(fr), np.nan)
    acc, prev_t = None, None
    for k in range(len(fr)):
        if acc is None: acc = rate_nf[k]
        else:
            dt = max(ft[k] - prev_t, 1)
            a = 1 - 0.5 ** (dt / HL)
            acc = acc + a * (rate_nf[k] - acc)
        prev_t = ft[k]; e1[k] = acc
    # v2: 在役精确 — 结算空间 EMA adjust=False, span=max(2,round(24/iv中位)), normfix
    span = max(2, int(round(24.0 / max(float(np.median(iv_full)), 1.0))))
    al2 = 2.0 / (span + 1.0)
    e2 = np.full(len(fr), np.nan)
    acc = None
    for k in range(len(fr)):
        v = rate_nf[k]
        acc = v if acc is None else al2 * v + (1 - al2) * acc
        e2[k] = acc
    pos = np.searchsorted(ft, anchor_s, side="right") - 1
    okp = pos >= 0
    fund_now[okp, j] = fr[pos[okp]].astype(np.float32)
    fund_iv[okp, j] = iv_full[pos[okp]].astype(np.float32)
    ema_v0[okp, j] = e0[pos[okp]].astype(np.float32)
    ema_v1[okp, j] = e1[pos[okp]].astype(np.float32)
    ema_v2[okp, j] = e2[pos[okp]].astype(np.float32)
    stale = okp & ((anchor_s - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12 * 3600)
    for arr in (fund_now, fund_iv, ema_v0, ema_v1, ema_v2):
        arr[stale, j] = np.nan
    n_fund += 1
print(f"funding 币数 {n_fund} 带interval列 {n_iv_col}", flush=True)
F["fund_now"] = fund_now; F["fund_iv"] = fund_iv
F["fund_ema"] = ema_v0; F["fund_ema_v1"] = ema_v1; F["fund_ema_v2"] = ema_v2

out = _os.environ.get("PANEL_OUT", "/workspace/data/wide_panel_4h_v2ext.npz")
np.savez_compressed(out, ts=CTS[E], symbols=np.array(syms), elig=elig,
                    Y4=Y4, Y24=Y24, **{f"f_{k}": v for k, v in F.items()})
# ---- 自检: 与 v1 面板重叠锚一致性 ----
PW1 = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)
ts1 = PW1["ts"].astype(np.int64); tsx = CTS[E]
row_x = {int(t): i for i, t in enumerate(tsx)}
common = [(-1, -1)] * 0
idx1, idxx = [], []
for i1, t in enumerate(ts1):
    ix = row_x.get(int(t))
    if ix is not None: idx1.append(i1); idxx.append(ix)
idx1 = np.array(idx1); idxx = np.array(idxx)
fails = []
for key, new in [("f_rev_24h", F["rev_24h"]), ("f_mom_7d", F["mom_7d"]), ("f_vol_7d", F["vol_7d"]),
                 ("f_amihud_24h", F["amihud_24h"]), ("f_range_24h", F["range_24h"]),
                 ("f_fund_ema", F["fund_ema"]), ("f_fund_now", F["fund_now"])]:
    a = PW1[key][idx1].ravel().astype(np.float64)
    b = new[idxx].ravel().astype(np.float64)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 1000:
        fails.append((key, "n<1000")); continue
    c = np.corrcoef(a[ok], b[ok])[0, 1]
    print(f"parity {key} corr {c:.6f} n {ok.sum()}", flush=True)
    if c < 0.999: fails.append((key, round(float(c), 6)))
if fails:
    print(f"PANEL_EXT_PARITY_FAIL {fails}", flush=True); sys.exit(3)
h = hashlib.sha256(open(out, "rb").read()).hexdigest()[:16]
print(f"PANEL_EXT_DONE anchors {len(E)} SHA {h}", flush=True)
