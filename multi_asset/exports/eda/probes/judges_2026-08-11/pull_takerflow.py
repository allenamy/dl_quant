"""拉 taker flow 三列 —— PREREG_takerflow_family FROZEN。
★ 速率 ≤1 req/s · 避开锚点 ±10 分钟 · 只用公开端点 · 只读不改任何既有文件
★ 分页向【前】走(今日已咬过一次: startTime 返回最早 1000 条升序)
"""
import time, json, os, sys, datetime as dt
import numpy as np, urllib.request

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_takerflow_1h.npz"
BASE = "https://fapi.binance.com/fapi/v1/klines"
START = int(dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp()*1000)

def anchor_guard():
    n = dt.datetime.now(dt.timezone.utc)
    m = n.hour % 4 * 60 + n.minute
    if m < 10 or m > 230:
        print(f"  ⏸ 距锚点 <10 分钟 ({n:%H:%M}Z), 等待…", flush=True); time.sleep(660)

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=25) as r: return json.loads(r.read())
        except Exception as e:
            if k == tries-1: raise
            time.sleep(3*(k+1))

syms = [str(s) for s in np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_klines_1h.npz",
                                allow_pickle=True)["symbols"]]
print(f"宇宙 {len(syms)} 币, 起点 2022-01-01, 端点 fapi klines(公开)")
tsref = np.load("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/bn_klines_1h.npz",
                allow_pickle=True)["ts"]
idx = {int(t): i for i, t in enumerate(tsref)}
T = len(tsref)
QV = np.full((T, len(syms)), np.nan, np.float32)
TB = np.full((T, len(syms)), np.nan, np.float32)
CN = np.full((T, len(syms)), np.nan, np.float32)
VO = np.full((T, len(syms)), np.nan, np.float32)
TBB = np.full((T, len(syms)), np.nan, np.float32)
t0 = time.time()
for j, s in enumerate(syms):
    cur = START; n = 0
    while True:
        anchor_guard()
        rows = get(f"{BASE}?symbol={s}&interval=1h&startTime={cur}&limit=1000")
        time.sleep(1.05)
        if not rows: break
        for r in rows:
            i = idx.get(int(r[0]))
            if i is None: continue
            VO[i, j] = float(r[5]); QV[i, j] = float(r[7]); CN[i, j] = float(r[8])
            TBB[i, j] = float(r[9]); TB[i, j] = float(r[10]); n += 1
        nxt = int(rows[-1][0]) + 3600000
        if nxt <= cur or len(rows) < 1000: break
        cur = nxt
    print(f"  [{j+1:3d}/{len(syms)}] {s:14s} {n:6d} 行  ({time.time()-t0:.0f}s)", flush=True)
    if (j+1) % 20 == 0:
        np.savez_compressed(OUT, ts=tsref, symbols=np.array(syms, dtype=object),
                            QVOL=QV, VOL=VO, TAKER_BUY_QUOTE=TB, TAKER_BUY_BASE=TBB,
                            TRADE_COUNT=CN, partial=j+1)
np.savez_compressed(OUT, ts=tsref, symbols=np.array(syms, dtype=object),
                    QVOL=QV, VOL=VO, TAKER_BUY_QUOTE=TB, TAKER_BUY_BASE=TBB, TRADE_COUNT=CN,
                    pulled_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    prereg="PREREG_takerflow_family_2026-08-09")
fin = np.isfinite(TB).mean()
print(f"\n落盘 {OUT}")
print(f"P1 覆盖: taker_buy_quote 有限值占比 {fin:.4f}   {'PASS' if fin>=0.95 else '★FAIL(<95%)'}")
tbr = TB/np.where(QV > 0, QV, np.nan)
ok = np.isfinite(tbr)
print(f"P2 恒等式: tbr∈[0,1] 占比 {((tbr>=-1e-6)&(tbr<=1+1e-6))[ok].mean():.6f}   "
      f"taker_base≤vol 占比 {(TBB<=VO*(1+1e-6))[np.isfinite(TBB)&np.isfinite(VO)].mean():.6f}")
print(f"   tbr 分位 [1,25,50,75,99] = {np.nanpercentile(tbr,[1,25,50,75,99]).round(4).tolist()}")
print("PULL_TAKERFLOW_DONE")
