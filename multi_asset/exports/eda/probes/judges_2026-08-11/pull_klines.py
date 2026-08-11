"""[安全版] 拉 Binance 1h klines —— 让跨场所族的第一道筛选【完全脱离 jpline】。
速率同前: 1 req/s, 只在非锚窗。用 startTime 往前滚(方向已在 funding 那次踩过一次)。
★ 会红的断言: 每个 symbol 必须覆盖到近 3 天内。
"""
import json, time, urllib.request, datetime as dt
import numpy as np
OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_klines_1h.npz"
z = np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_funding_settlements.npz",
            allow_pickle=True)
TARGETS = [str(x) for x in z["symbols"]]
FLOOR = int((time.time() - 86400*820)*1000); NOW = int(time.time()*1000)
def g(u, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=20) as x: return json.load(x)
        except Exception:
            if k == tries-1: raise
            time.sleep(2*(k+1))
print(f"目标 {len(TARGETS)}", flush=True)
data, t0 = {}, time.time()
for i, s in enumerate(TARGETS):
    rows, cur = {}, FLOOR
    for page in range(20):
        h = g(f"https://fapi.binance.com/fapi/v1/klines?symbol={s}&interval=1h"
              f"&startTime={cur}&limit=1500")
        if not h: break
        for r in h: rows[int(r[0])] = float(r[4])       # close
        mx = max(int(r[0]) for r in h)
        if len(h) < 1500 or mx >= NOW - 3600_000: break
        cur = mx + 1; time.sleep(1.0)
    data[s] = rows
    if i % 10 == 0 or i == len(TARGETS)-1:
        print(f"[{i+1:3d}/{len(TARGETS)}] {s:14s} {len(rows):6d} 根  {time.time()-t0:.0f}s", flush=True)
    time.sleep(1.0)
stale = [k for k, v in data.items() if v and (NOW - max(v)) > 3*86400_000]
assert not stale, f"这些 symbol 未覆盖到近 3 天: {stale[:8]} (共 {len(stale)})"
print(f"[assert] {len(data)} 个 symbol 全部覆盖到近 3 天 ✓", flush=True)
allts = sorted({t for r in data.values() for t in r}); ts = np.array(allts, dtype=np.int64)
idx = {t: i for i, t in enumerate(allts)}
C = np.full((len(ts), len(TARGETS)), np.nan, dtype=np.float32)
for j, s in enumerate(TARGETS):
    for t, c in data[s].items(): C[idx[t], j] = c
np.savez_compressed(OUT, ts=ts, symbols=np.array(TARGETS, dtype=object), CLOSE=C,
                    source="binance fapi/v1/klines interval=1h (public)",
                    pulled_utc=dt.datetime.now(dt.timezone.utc).isoformat())
print(f"网格 {C.shape} 有限 {np.isfinite(C).mean():.4f}  -> {OUT}\nKLPULL_DONE")
