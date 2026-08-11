"""[安全版] 拉 Binance USDT-M 逐笔 funding 结算历史 —— 跨场所比较的另一半。

★ 关键: 不落"费率"本身, 而是落 (fundingTime, fundingRate, interval_h)。
  `interval_h` 由**相邻结算时间戳的间距**逐笔算出 —— 不用 funding_span_table 的静态值,
  因为该表自己的注释就写着「实测 2026-07-26, 15 个我们仍标 8h 的名字在生产上已是 4h」。
  从时间戳推间隔对**迁移自动免疫**, 这是记忆 funding_settlement_interval_unit_bug 的正解。

★★ 速率纪律(2026-08-09 吃了一次 429 之后加的):
   实盘单个锚点的 peak_window_weight 实测 1940 / 上限 2400 = **81%**, 而它的自保阈值就是 80%。
   ⇒ 同 IP 的研究拉取会把实盘推过 backstop、让锚点等待。
   本脚本: **1 req/s**(243 请求 ≈ 4 分钟 ≈ 上限的 2.5%), 且**只在非锚窗运行**
   (锚在 00/04/08/12/16/20 UTC, 执行约 23 分钟 ⇒ 安全窗 = 锚后 40 分钟至下一锚前 40 分钟)。
"""
import json, time, urllib.request, datetime as dt
import numpy as np

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_funding_settlements.npz"
UNIV = [str(s) for s in json.load(
    open("/Users/haosiyu/dl_quant_live/state/live/preds_latest.json"))["symbols"]]
hl = np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/hl_funding_hourly.npz",
             allow_pickle=True) if False else None
# HL 还在拉 ⇒ 先按"与 HL 交集"的同一规则重算目标集(只需 metaAndAssetCtxs, 便宜)
req = urllib.request.Request("https://api.hyperliquid.xyz/info",
                             data=json.dumps({"type": "meta"}).encode(),
                             headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=25) as x:
    names = [u["name"] for u in json.load(x)["universe"]]
TARGETS = sorted({f"{n}USDT" for n in names if f"{n}USDT" in UNIV})
print(f"目标 {len(TARGETS)} 个(与 HL 交集)", flush=True)

FLOOR = int((time.time() - 86400 * 820) * 1000)


def g(u, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=20) as x:
                return json.load(x)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


data, t0 = {}, time.time()
NOW = int(time.time() * 1000)
for i, sym in enumerate(TARGETS):
    rows, cur = {}, FLOOR
    for page in range(14):
        h = g(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}"
              f"&startTime={cur}&limit=1000")
        if not h:
            break
        for r in h:
            rows[int(r["fundingTime"])] = float(r["fundingRate"])
        mx = max(int(r["fundingTime"]) for r in h)
        if len(h) < 1000 or mx >= NOW - 3600_000:
            break
        cur = mx + 1                      # ★ 往【前】滚: API 带 startTime 返回升序的最早 1000 条
        time.sleep(1.0)
    data[sym] = rows
    if rows:
        lo = dt.datetime.fromtimestamp(min(rows)/1000, dt.timezone.utc)
        hi = dt.datetime.fromtimestamp(max(rows)/1000, dt.timezone.utc)
        print(f"[{i+1:3d}/{len(TARGETS)}] {sym:14s} {len(rows):5d} 笔  {lo:%Y-%m-%d} → {hi:%Y-%m-%d}  "
              f"{time.time()-t0:.0f}s", flush=True)
    time.sleep(1.0)

# ★ 会红的断言 —— 上一版就是死在"只拿到最老的一年"而没有任何东西报警
_stale = [k for k, v in data.items() if v and (NOW - max(v)) > 3 * 86400_000]
assert not _stale, (f"这些 symbol 的最新结算距今 >3 天, 说明分页没滚到头: {_stale[:8]} "
                    f"(共 {len(_stale)} 个)")
print(f"[assert] 全部 {len(data)} 个 symbol 都覆盖到近 3 天内 ✓", flush=True)

allts = sorted({t for r in data.values() for t in r})
ts = np.array(allts, dtype=np.int64); idx = {t: i for i, t in enumerate(allts)}
R = np.full((len(ts), len(TARGETS)), np.nan, dtype=np.float32)   # 费率
H = np.full((len(ts), len(TARGETS)), np.nan, dtype=np.float32)   # 该笔的实际间隔(小时)
for j, s in enumerate(TARGETS):
    tt = sorted(data[s])
    for k, t in enumerate(tt):
        R[idx[t], j] = data[s][t]
        if k > 0:
            H[idx[t], j] = (t - tt[k-1]) / 3600_000.0
np.savez_compressed(OUT, ts=ts, symbols=np.array(TARGETS, dtype=object), RATE=R, INTERVAL_H=H,
                    source="binance fapi/v1/fundingRate (public)",
                    pulled_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    note="INTERVAL_H 由相邻结算时间戳间距逐笔算出, 对结算间隔迁移免疫; "
                         "per-hour rate = RATE / INTERVAL_H")
fin = np.isfinite(H)
import collections
c = collections.Counter(np.round(H[fin]).astype(int).tolist())
print(f"\n网格 {R.shape}  费率有限 {np.isfinite(R).mean():.4f}")
print(f"实测间隔分布(小时): {dict(c.most_common(6))}")
print(f"时间 {dt.datetime.fromtimestamp(ts[0]/1000,dt.timezone.utc):%Y-%m-%d} → "
      f"{dt.datetime.fromtimestamp(ts[-1]/1000,dt.timezone.utc):%Y-%m-%d}")
print(f"-> {OUT}\nBNPULL_DONE")
