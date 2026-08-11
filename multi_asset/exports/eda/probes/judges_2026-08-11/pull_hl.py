"""拉 Hyperliquid 逐小时 funding + premium 历史 —— 跨场所族的数据获取。

只做数据获取, 不构造任何因子(因子设计走预注册)。
公开端点, 无鉴权。分页: 每页 500 条(约 21 天), 用最早一条的时间往前滚。
"""
import json, time, os, sys, urllib.request, datetime as dt
import numpy as np

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/hl_funding_hourly.npz"
U = "https://api.hyperliquid.xyz/info"
UNIV = [str(s) for s in json.load(
    open("/Users/haosiyu/dl_quant_live/state/live/preds_latest.json"))["symbols"]]
SLEEP = 0.35
BACK_DAYS = 800


def post(p, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(U, data=json.dumps(p).encode(),
                                       headers={"Content-Type": "application/json",
                                                "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=25) as x:
                return json.load(x)
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(1.5 * (k + 1))


meta = post({"type": "metaAndAssetCtxs"})[0]
names = [u["name"] for u in meta["universe"]]
targets = sorted({n for n in names if f"{n}USDT" in UNIV})
print(f"HL perp {len(names)}  与在役宇宙交集 {len(targets)}", flush=True)

t_end = int(time.time() * 1000)
t_floor = int((time.time() - 86400 * BACK_DAYS) * 1000)
data = {}
t0 = time.time()
for i, c in enumerate(targets):
    rows, cur = {}, t_end
    for page in range(60):                      # 60×21d ≈ 3.4 年上限
        try:
            h = post({"type": "fundingHistory", "coin": c,
                      "startTime": max(cur - 86400_000 * 25, t_floor), "endTime": cur})
        except Exception as e:
            print(f"  {c} page{page} 失败 {type(e).__name__}", flush=True); break
        if not h:
            break
        for r in h:
            rows[int(r["time"])] = (float(r["fundingRate"]),
                                    float(r.get("premium") or "nan"))
        earliest = min(int(r["time"]) for r in h)
        if earliest <= t_floor or earliest >= cur:
            break
        cur = earliest
        time.sleep(SLEEP)
    data[c] = rows
    if rows:
        lo = dt.datetime.fromtimestamp(min(rows)/1000, dt.timezone.utc)
        hi = dt.datetime.fromtimestamp(max(rows)/1000, dt.timezone.utc)
        print(f"[{i+1:3d}/{len(targets)}] {c:10s} {len(rows):6d} 条  {lo:%Y-%m-%d} → {hi:%Y-%m-%d}  "
              f"{time.time()-t0:.0f}s", flush=True)
    else:
        print(f"[{i+1:3d}/{len(targets)}] {c:10s} 空", flush=True)
    time.sleep(SLEEP)

allts = sorted({t for r in data.values() for t in r})
ts = np.array(allts, dtype=np.int64)
idx = {t: i for i, t in enumerate(allts)}
F = np.full((len(ts), len(targets)), np.nan, dtype=np.float32)
P = np.full((len(ts), len(targets)), np.nan, dtype=np.float32)
for j, c in enumerate(targets):
    for t, (f, p) in data[c].items():
        F[idx[t], j] = f; P[idx[t], j] = p
np.savez_compressed(OUT, ts=ts, coins=np.array(targets, dtype=object),
                    FUNDING=F, PREMIUM=P,
                    source="hyperliquid /info fundingHistory (hourly, public)",
                    pulled_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    note="FUNDING 与 PREMIUM 均为 HL 原生逐小时口径; 与 Binance 比较前必须先做区间归一")
print(f"\n网格 {F.shape}  有限格 funding {np.isfinite(F).mean():.4f} premium {np.isfinite(P).mean():.4f}")
print(f"时间 {dt.datetime.fromtimestamp(ts[0]/1000,dt.timezone.utc):%Y-%m-%d} → "
      f"{dt.datetime.fromtimestamp(ts[-1]/1000,dt.timezone.utc):%Y-%m-%d}")
print(f"-> {OUT}\nHLPULL_DONE")
