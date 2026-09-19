# -*- coding: utf-8 -*-
"""Is r24 = -0.03248 unusual FOR THIS BOOK? The device's threshold comes from an offline book
(2026-08-10, 9,821 anchors, alpha=0.05/band=0.002) and its own contract says it was never re-calibrated
to the live form. So: measure the live book's OWN rolling-24 distribution. READ-ONLY."""
import json, time, statistics, random
import numpy as np
P = "/Users/haosiyu/dl_quant_live/state/live/ic_monitor.jsonl"
rows = [json.loads(l) for l in open(P) if l.strip()]
rows.sort(key=lambda r: r["anchor_ts"])
ts = np.array([r["anchor_ts"] for r in rows], float)
ic = np.array([r["rank_ic"] for r in rows], float)
br = np.array([r.get("rank_ic_beta_resid") if r.get("rank_ic_beta_resid") is not None else np.nan for r in rows], float)
n  = np.array([r["n"] for r in rows], float)
u = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))
print(f"账本 {len(rows)} 行, {u(ts[0])} .. {u(ts[-1])}")
print(f"  逐锚 rank_ic: 均值 {ic.mean():+.5f}  中位 {np.median(ic):+.5f}  sd {ic.std(ddof=1):.5f}")
print(f"  正 {int((ic>0).sum())} / 负 {int((ic<0).sum())}  ⇒ 正占比 {(ic>0).mean()*100:.1f}%")
print(f"  逐锚共持名数 n: 中位 {np.median(n):.0f} [min {n.min():.0f}, max {n.max():.0f}]")
print()

# --- gaps: the r48 window was declared incomplete; check the grid ---
d = np.diff(ts)/3600.0
print(f"相邻行间隔(小时): {dict(sorted(__import__('collections').Counter(np.round(d,1)).items()))}")
print()

W = 24
roll = np.array([ic[i-W+1:i+1].mean() for i in range(W-1, len(ic))])
rts = ts[W-1:]
cur = roll[-1]
print(f"=== 滚动 24 锚均值(在役书自身分布, {len(roll)} 个窗) ===")
print(f"  当前 r24 = {cur:+.5f}   (装置报 -0.03248; 差异来自它按成熟前沿截窗)")
print(f"  分布: 中位 {np.median(roll):+.5f}  sd {roll.std(ddof=1):.5f}  [min {roll.min():+.5f}, max {roll.max():+.5f}]")
q = (roll <= cur).mean()*100
print(f"  ★ 当前值在【本书自身】滚动分布里的分位: {q:.1f}%  (装置阈值 -0.02277 来自离线书)")
print(f"  离线阈值 -0.02277 在本书分布里的分位: {(roll <= -0.02277).mean()*100:.1f}%")
print(f"  ⇒ 若按【本书自身】5% 分位定 ALERT, 线应在 {np.percentile(roll,5):+.5f}; 1% 分位 {np.percentile(roll,1):+.5f}")
print()
print("  ★★ 但滚动窗重叠 ⇒ 上面的分位不是独立抽样的分位。不重叠的 24 锚块:")
blocks = [ic[i:i+W].mean() for i in range(0, len(ic)-W+1, W)]
print(f"     {len(blocks)} 个不重叠块: {[f'{b:+.4f}' for b in blocks]}")
print(f"     当前值比 {sum(1 for b in blocks if b<=cur)}/{len(blocks)} 个块更低")
print()

print("=== 时间轴: 逐 24 锚不重叠块 ===")
for i in range(0, len(ic)-W+1, W):
    seg = ic[i:i+W]
    print(f"  {u(ts[i])} .. {u(ts[i+W-1])}  mean {seg.mean():+.5f}  中位 {np.median(seg):+.5f}  正 {int((seg>0).sum())}/{W}")
tail = ic[len(ic)-(len(ic)%W or W):]
if len(ic) % W: print(f"  {u(ts[-(len(ic)%W)])} .. {u(ts[-1])}  (不满块 {len(ic)%W}) mean {ic[-(len(ic)%W):].mean():+.5f}")
print()

print("=== 最近 24 锚逐行 ===")
for i in range(len(ic)-24, len(ic)):
    print(f"  {u(ts[i])}  rank_ic {ic[i]:+.5f}  beta_resid {br[i]:+.5f}  n {n[i]:.0f}")
print()
print("=== 最近 24 锚是否被少数锚主导 ===")
last = ic[-24:]
print(f"  均值 {last.mean():+.5f}; 去掉最负的一个 ⇒ {np.sort(last)[1:].mean():+.5f}; 去掉最负的三个 ⇒ {np.sort(last)[3:].mean():+.5f}")
print(f"  正 {int((last>0).sum())}/24  符号检验 z = {((last>0).sum()-12)/np.sqrt(6):+.2f}")
t = np.arange(24); sl = np.polyfit(t, last, 1)[0]
print(f"  窗内线性斜率 {sl:+.5f}/锚")
print()
print("=== 自举: 最近 24 锚的均值 CI(逐锚重抽; 锚之间近似独立, 目标是 4h 不重叠的下一锚收益) ===")
random.seed(20260919)
bs = sorted(np.mean(np.random.choice(last, 24)) for _ in range(4000))
print(f"  95% CI [{bs[100]:+.5f}, {bs[3899]:+.5f}]  含 0 = {bs[100] < 0 < bs[3899]}")
