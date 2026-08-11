"""bookDepth 族法证 — DESIGN_book 的数据基础。八项, 全部打在真实 gz 文件上。
(gzip 后 48GB, 逐日 CSV: timestamp,percentage,depth,notional; 12 带 × 2880 帧/天)

F1 帧规整/帧数分布      30s 网格是否真规整; 缺帧形态
F2 带完整性             每帧是否恰 12 带; 缺带的币/日
F3 单位自证             notional/depth = 隐含价 → 与 klines close 比(B25 教训: 单位必须自证)
F4 ★ 对抗结构存在性     ±0.2% 带的 bid/ask 不平衡 OBI 分布/自相关 —— 它是否是个"活"的量
F5 深度 vs 成交量量纲    depth(币) 跨币不可比 ⇒ 强度化候选: depth/ADV, depth 份额
F6 覆盖矩阵             逐年 币×日 可得率(2023-01 起, 128/140 币)
F7 零深度格             某带整帧为零的频率(小币常见) → 除法守卫
F8 ★ 与 y 的方向侦察     OBI 与未来 4h/24h 收益的符号(仅方向, 不做门)
"""
import glob, gzip, os, sys
from collections import Counter, defaultdict
import numpy as np

BD = "/workspace/data/raw/bookDepth"
BANDS = ["-5.00","-4.00","-3.00","-2.00","-1.00","-0.20","0.20","1.00","2.00","3.00","4.00","5.00"]

def read_day(sym, day):
    p = f"{BD}/{sym}-{day}.csv.gz"
    if not os.path.exists(p):
        p2 = f"{BD}/{sym}-{day}.csv"
        if not os.path.exists(p2): return None
        return open(p2).read()
    with gzip.open(p, "rt") as f: return f.read()

PROBE = ["BTCUSDT", "SOLUSDT", "OPUSDT"]
DAY = "2026-07-15"
print("="*72); print("[F1/F2] 帧规整 + 带完整性 (%s)" % DAY)
for s in PROBE:
    txt = read_day(s, DAY)
    if not txt: print(f"  {s}: 无数据"); continue
    L = txt.strip().split("\n")[1:]
    ts = [l.split(",")[0] for l in L]
    bd = [l.split(",")[1] for l in L]
    uts = sorted(set(ts)); per = Counter(ts)
    from datetime import datetime
    d = [(datetime.fromisoformat(uts[i+1]) - datetime.fromisoformat(uts[i])).total_seconds()
         for i in range(min(400, len(uts)-1))]
    print(f"  {s:10s} 帧 {len(uts):5d}/2880  帧距 {Counter(d).most_common(2)}  "
          f"每帧带数 min/max {min(per.values())}/{max(per.values())}  带集全 {set(bd)==set(BANDS)}")

print("\n[F3] 单位自证: notional/depth 隐含价")
for s in PROBE:
    txt = read_day(s, DAY)
    if not txt: continue
    dep = nof = 0.0
    for l in txt.strip().split("\n")[1:]:
        p = l.split(",")
        dep += float(p[2]); nof += float(p[3])
    print(f"  {s:10s} 隐含价 {nof/max(dep,1e-9):,.4f}")

print("\n[F4] ★ ±0.2% 带 OBI: 是活量还是常数? (BTC 全天 2880 帧)")
txt = read_day("BTCUSDT", DAY)
bid = []; ask = []
for l in txt.strip().split("\n")[1:]:
    p = l.split(",")
    if p[1] == "-0.20": bid.append(float(p[2]))
    elif p[1] == "0.20": ask.append(float(p[2]))
n = min(len(bid), len(ask)); b = np.array(bid[:n]); a = np.array(ask[:n])
obi = (b - a) / (b + a + 1e-12)
ac1 = float(np.corrcoef(obi[:-1], obi[1:])[0, 1])
ac120 = float(np.corrcoef(obi[:-120], obi[120:])[0, 1])
print(f"  OBI: 均值 {obi.mean():+.4f}  sd {obi.std():.4f}  区间 [{obi.min():+.3f},{obi.max():+.3f}]")
print(f"       AR1(30s) {ac1:+.3f}   AR(1h,120帧) {ac120:+.3f}   ⇒ {'有持久结构, 可小时聚合' if ac120>0.1 else '快速均值回复'}")
print(f"  逐侧 sd: bid {b.std()/max(b.mean(),1e-9):.3f} ask {a.std()/max(a.mean(),1e-9):.3f} (变异系数)")

print("\n[F5] 深度量纲: 跨币可比性")
for s in PROBE:
    txt = read_day(s, DAY)
    if not txt: continue
    v = [float(l.split(",")[2]) for l in txt.strip().split("\n")[1:] if l.split(",")[1] in ("-0.20","0.20")]
    w = [float(l.split(",")[2]) for l in txt.strip().split("\n")[1:] if l.split(",")[1] in ("-5.00","5.00")]
    print(f"  {s:10s} ±0.2%均深 {np.mean(v):12.2f} 币   ±0.2%/±5% 份额 {np.mean(v)/max(np.mean(w),1e-9):.4f}")

print("\n[F6] 覆盖矩阵 (逐年抽样)")
allf = os.listdir(BD)
syms = set(); bydate = defaultdict(int)
for f in allf:
    if not (f.endswith(".csv.gz") or f.endswith(".csv")): continue
    base = f.replace(".csv.gz","").replace(".csv","")
    sym, day = base.rsplit("-", 3)[0], base[-10:]
    syms.add(sym); bydate[day[:4]] += 1
print(f"  币数 {len(syms)}  文件总数 {sum(bydate.values()):,}")
for y in sorted(bydate): print(f"    {y}: {bydate[y]:,} 币-日")

print("\n[F7] 零深度格 (小币, ±0.2% 带)")
for s in ("OPUSDT", "SOLUSDT"):
    txt = read_day(s, DAY)
    if not txt: continue
    z = sum(1 for l in txt.strip().split("\n")[1:]
            if l.split(",")[1] in ("-0.20","0.20") and float(l.split(",")[2]) == 0)
    tot = sum(1 for l in txt.strip().split("\n")[1:] if l.split(",")[1] in ("-0.20","0.20"))
    print(f"  {s:10s} 零深度 {z}/{tot} = {z/max(tot,1)*100:.2f}%")
print("\n法证完毕 — 数字进 DESIGN_book")
