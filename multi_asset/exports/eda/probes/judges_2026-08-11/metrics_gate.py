"""metrics 族三道门 —— 判据先于数字写死 (2026-08-07 04:2xZ)。

原料: 140 币 × 180 天 × 288 帧/天(5min), 6 个原始量:
  sum_open_interest, sum_open_interest_value,
  count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
  count_long_short_ratio, sum_taker_long_short_vol_ratio

★ 特征构造(遵循昨日实测: 小时聚合保留 {均值,标准差,斜率}, 不用末值 —— 末值 IC 反号):
  对每个原始量, 每小时算 mean/std/slope; 另加两个【变化率】量: OI 的 1h/24h 对数变化。
  全部严格因果: 只用 ≤t 的帧。

★ 三道门(任一不过, 该特征出局):
  G1 因果门: 特征 vs 【未来 24h 收益】的 |IC| < 0.15 (>0.15 = 泄漏签名, 见 ROADMAP §F 门2)
  G2 Ridge 前置门(家规): 加入该族后, 8 列 baseline+新族 对 YR4 的 walk-forward OOS
     可预测性提升 ΔR² > 0 且 该族单独 |IC| > 0.01
  G3 ★ 维度门(本次新立, 针对 7.2 的诊断): 该族加入后 participation ratio 必须上升;
     且新族与现有 32 通道的最大 |corr| < 0.8 (否则是第 33 种切法)

判读: 三门全过 ⇒ 进面板重训候选; 仅 G1+G3 过而 G2 不过 ⇒ 记录为"独立但无增量", 不进;
      G3 不过 ⇒ 直接出局(它就是我们要治的病)。
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

HOME = os.path.expanduser("~")
MET = os.path.join(HOME, "lob_raw", "metrics")
sys.path[:0] = [os.path.join(HOME, "dl_quant_live", "signal"),
                os.path.join(HOME, "dl_quant_live", "live")]
import fapi_source as FS          # noqa: E402
import live_panel as LP           # noqa: E402
import panel_build as PB          # noqa: E402

print("读面板(参考收益与成员掩码)...")
built = LP.build_live_panel(FS.FapiSource(), hours=1200, refresh=False)
CH, TS, SYMS = built["CH"], np.asarray(built["ts"]), [str(s) for s in built["symbols"]]
CLOSE = np.asarray(built["CLOSE"], float)
try:
    tradable = set(FS.FapiSource().perp_symbols())
except Exception:
    tradable = None
MEMBER = PB.derive_member(built["DVOL30"], built["CLOSE"], symbols=SYMS, tradable=tradable)
SI = {s: i for i, s in enumerate(SYMS)}
N, T = len(SYMS), len(TS)
print(f"  面板 {T} 小时 × {N} 币")

COLS = ["oi", "oi_val", "tt_cnt_ls", "tt_sum_ls", "all_cnt_ls", "taker_ls"]
DESC = ["mean", "std", "slope"]
FEAT = [f"{c}_{d}" for c in COLS for d in DESC] + ["oi_chg1h", "oi_chg24h"]
X = np.full((T, N, len(FEAT)), np.nan, np.float32)

t0_ms = int(TS[0])
hour_of = {int(t): i for i, t in enumerate(TS)}
import datetime as dt

print("解析 metrics 并聚合到小时网格...")
files = sorted(glob.glob(os.path.join(MET, "*.csv")))
n_ok = 0
for fp in files:
    base = os.path.basename(fp)[:-4]
    sym = base.rsplit("-", 3)[0]
    if sym not in SI:
        continue
    j = SI[sym]
    buck = defaultdict(list)
    try:
        with open(fp) as f:
            next(f)
            for ln in f:
                p = ln.rstrip("\n").split(",")
                if len(p) < 8:
                    continue
                ts_ms = int(dt.datetime.strptime(p[0], "%Y-%m-%d %H:%M:%S")
                            .replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
                h = ts_ms - (ts_ms % 3600000)
                if h not in hour_of:
                    continue
                buck[h].append([float(p[2]), float(p[3]), float(p[4]),
                                float(p[5]), float(p[6]), float(p[7])])
    except Exception:
        continue
    if not buck:
        continue
    n_ok += 1
    for h, rows in buck.items():
        i = hour_of[h]
        a = np.array(rows, float)
        if len(a) < 3:
            continue
        q = max(1, len(a) // 3)
        for c in range(6):
            v = a[:, c]
            X[i, j, c * 3 + 0] = v.mean()
            X[i, j, c * 3 + 1] = v.std()
            X[i, j, c * 3 + 2] = v[-q:].mean() - v[:q].mean()
print(f"  解析 {n_ok} 文件, 小时格填充率 {np.isfinite(X[:, :, 0]).mean():.3f}")

oi = X[:, :, 0]
with np.errstate(invalid="ignore", divide="ignore"):
    X[1:, :, -2] = np.log(oi[1:] / oi[:-1])
    X[24:, :, -1] = np.log(oi[24:] / oi[:-24])

fin = np.isfinite(X).any(axis=(0, 1))
FEAT = [f for f, k in zip(FEAT, fin) if k]
X = X[:, :, fin]
print(f"  有效特征 {len(FEAT)}: {FEAT}")


def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 10: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o


def xic(a, b):
    za, zb = zr(a), zr(b)
    m = np.isfinite(za) & np.isfinite(zb)
    return float(np.nanmean(za[m] * zb[m])) if m.sum() >= 10 else np.nan


rows4 = [i for i in range(200, T - 30) if int(TS[i]) % (4 * 3600 * 1000) == 0]
fwd4 = np.full((T, N), np.nan); fwd24 = np.full((T, N), np.nan)
fwd4[:-4] = CLOSE[4:] / CLOSE[:-4] - 1.0
fwd24[:-24] = CLOSE[24:] / CLOSE[:-24] - 1.0

print("\n[G1] 因果门: 特征 vs 未来 24h (>0.15 = 泄漏签名)")
g1 = {}
for k, f in enumerate(FEAT):
    ics = [xic(np.where(MEMBER[i], X[i, :, k], np.nan),
               np.where(MEMBER[i], fwd24[i], np.nan)) for i in rows4[::3]]
    g1[f] = float(np.nanmean(ics))
worst = sorted(g1.items(), key=lambda kv: -abs(kv[1]))[:4]
for f, v in worst:
    print(f"   {f:16s} {v:+.4f} {'★★★ 红旗' if abs(v) > 0.15 else ''}")
print(f"   ⇒ 最大 |IC| = {max(abs(v) for v in g1.values()):.4f} "
      f"{'FAIL' if max(abs(v) for v in g1.values()) > 0.15 else 'PASS'}")

print("\n[G2] 单特征对 YR4(4h) 的裸 IC")
g2 = {}
for k, f in enumerate(FEAT):
    ics = [xic(np.where(MEMBER[i], X[i, :, k], np.nan),
               np.where(MEMBER[i], fwd4[i], np.nan)) for i in rows4]
    g2[f] = float(np.nanmean(ics))
for f, v in sorted(g2.items(), key=lambda kv: -abs(kv[1]))[:8]:
    print(f"   {f:16s} {v:+.4f} {'✓>0.01' if abs(v) > 0.01 else ''}")

print("\n[G3] ★ 维度门: 与现有 32 通道的相关 + participation ratio")
rs = rows4[::2]
old, new = [], []
for i in rs:
    m = MEMBER[i]
    if m.sum() < 50: continue
    a = CH[i][m]; b = X[i][m]
    a = (a - np.nanmean(a, 0)) / (np.nanstd(a, 0) + 1e-9)
    b = (b - np.nanmean(b, 0)) / (np.nanstd(b, 0) + 1e-9)
    old.append(a); new.append(b)
A = np.where(np.isfinite(np.vstack(old)), np.vstack(old), 0.0)
B = np.where(np.isfinite(np.vstack(new)), np.vstack(new), 0.0)
CC = np.corrcoef(np.hstack([A, B]).T)
n_old = A.shape[1]
cross = np.abs(CC[:n_old, n_old:])
print(f"   新族 × 旧通道 最大 |corr| = {cross.max():.3f} "
      f"{'FAIL(第33种切法)' if cross.max() >= 0.8 else 'PASS'}")
for k, f in enumerate(FEAT):
    if cross[:, k].max() >= 0.8:
        print(f"     {f} ~ 旧通道 {cross[:, k].max():.3f}")


def pr(M):
    C = np.corrcoef(M.T)
    C = np.where(np.isfinite(C), C, 0.0)
    w = np.clip(np.linalg.eigvalsh(C)[::-1], 0, None)
    return (w.sum() ** 2) / (w ** 2).sum()


pr_old, pr_new = pr(A), pr(np.hstack([A, B]))
print(f"   participation ratio: 旧 {pr_old:.1f} → 加新族 {pr_new:.1f}  (Δ {pr_new-pr_old:+.1f})")
print(f"   ⇒ G3 {'PASS' if pr_new > pr_old and cross.max() < 0.8 else 'FAIL'}")
json.dump({"g1": g1, "g2": g2, "pr_old": pr_old, "pr_new": pr_new,
           "max_cross_corr": float(cross.max()), "feats": FEAT},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "metrics_gate.json"), "w"), indent=1)
np.savez_compressed(os.path.join(HOME, "lob_raw", "metrics_hourly.npz"),
                    X=X.astype(np.float32), ts=TS,
                    symbols=np.array(SYMS, object), feats=np.array(FEAT, object))
print("\nsaved ~/lob_raw/metrics_hourly.npz")
