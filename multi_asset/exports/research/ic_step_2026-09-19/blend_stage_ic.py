# -*- coding: utf-8 -*-
"""独立复核 独立研究员 2026-09-19 第三轮 §3: **融合阶段**是不是 IC 变负的位置。

他们报的:

| 窗口 | King 侧组合 IC | 最终融合目标 IC | 实际持仓 IC |
|---|---|---|---|
| 九月 | −0.00311 | −0.01056 | −0.01120 |
| 最近 24 锚 | −0.01796 | −0.03092 | −0.03104 |

配对差(整个 combo 期, 融合目标 − king 侧组合) **−0.00614**, 3 日块 CI **[−0.00992, −0.00304]**。

## 本装置怎么测

**三本书, 同一批名、同一条收益口径、同一批锚**, 逐锚算 Spearman(权重, 下锚收益):

| 书 | 来源 |
|---|---|
| KING 侧组合 | `~/wide_shadow/state/target_live_king/{A}.json` |
| 最终融合目标 | `~/wide_shadow/state/target_live/{A}.json` |
| 实际持仓 | `~/dl_quant_live/state/live/pilot_log/*/position_readback.jsonl`(场所回读) |

收益 = **场所隐含价** `p = |notional| / |qty|` 的相邻 4h 网格锚之比 −1, 与生产 `ic_monitor` 同源
(该统计量的正控: 我此前从同一数据重算其 261 锚, 最大 |Δ| 4.98e-06)。

**关键: 三本书必须限制在【同一批可评分的名】上**, 否则比的是不同人口而不是不同书。
本装置对每个锚取 **三书 ∩ 有收益** 的交集, 并把交集大小写进产物。

## 边界(先写)

- 这里比的是**组合权重**。融合阶段还包含成员选择、归一化、FTRIM、平滑 —— **本装置分不开这些**。
- **不能据此判定 F10 无效**, 也**没有证明移除 F10 能提高净收益**。
- IC 是**排序**量, 不是**净额**量; 排序差 ≠ 亏损归因。

用法: python3 blend_stage_ic.py
"""
import collections
import glob
import json
import os
import time

import numpy as np

WS = "/Users/haosiyu/wide_shadow/state"
PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
GRID = 14400
U = lambda t: time.strftime("%m-%d %HZ", time.gmtime(t))


def rankdata(x):
    x = np.asarray(x, float); o = np.argsort(x, kind="mergesort"); r = np.empty(len(x), float)
    r[o] = np.arange(1, len(x) + 1)
    i, xs = 0, x[o]
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    return r


def spear(a, b):
    if len(a) < 30:
        return None
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return None if d == 0 else float((ra * rb).sum() / d)


# ── 场所隐含价(与 ic_monitor 同源) ──
px = {}
pos = {}
for p in sorted(glob.glob(f"{PL}/*/position_readback.jsonl")):
    for l in open(p, errors="ignore"):
        if not l.strip():
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        q, nt = r.get("venue_position_qty"), r.get("venue_position_notional")
        if q in (None, 0) or nt is None:
            continue
        g = int(float(r.get("anchor_ts") or 0) // GRID * GRID)
        px.setdefault(g, {})[r["symbol"]] = abs(float(nt)) / abs(float(q))
        pos.setdefault(g, {})[r["symbol"]] = float(nt)


def book(dirname, A):
    p = f"{WS}/{dirname}/{A}.json"
    if not os.path.exists(p):
        return None
    try:
        j = json.load(open(p))
    except Exception:
        return None
    w = j.get("weights")
    return {k: float(v) for k, v in w.items()} if w else None


rows = []
for A in sorted(px):
    nxt = [g for g in px if A < g <= A + 6 * 3600]
    if not nxt:
        continue
    B = min(nxt)
    kb, tb, hb = book("target_live_king", A), book("target_live", A), pos.get(A)
    if not (kb and tb and hb):
        continue
    # ★ 同一批可评分的名: 三书 ∩ 两端都有隐含价
    names = sorted(set(kb) & set(tb) & set(hb) & set(px[A]) & set(px[B]))
    if len(names) < 30:
        continue
    ret = np.array([px[B][s] / px[A][s] - 1.0 for s in names])
    rows.append({"A": A, "n": len(names),
                 "king": spear(np.array([kb[s] for s in names]), ret),
                 "blend": spear(np.array([tb[s] for s in names]), ret),
                 "held": spear(np.array([hb[s] for s in names]), ret)})

print(f"可评分锚 {len(rows)}  ({U(rows[0]['A'])} .. {U(rows[-1]['A'])}); 逐锚交集名数 中位 {int(np.median([r['n'] for r in rows]))}")
print("★ 三本书限制在【同一批名】上, 否则比的是不同人口而不是不同书\n")

import calendar
SEP = calendar.timegm(time.strptime("2026-09-01T00:00Z", "%Y-%m-%dT%H:%MZ"))
COMBO = 1787716800


def blk(sub, key):
    return np.array([r[key] for r in sub if r[key] is not None], float)


print(f"{'窗口':<16}{'n锚':>5}{'KING 侧组合':>14}{'最终融合目标':>14}{'实际持仓':>12}{'融合−KING':>12}")
for lab, sub in (("九月", [r for r in rows if r["A"] >= SEP]),
                 ("最近 24 锚", rows[-24:]),
                 ("整个 combo 期", [r for r in rows if r["A"] >= COMBO])):
    if not sub:
        continue
    k, b, h = blk(sub, "king"), blk(sub, "blend"), blk(sub, "held")
    print(f"{lab:<16}{len(sub):>5}{k.mean():>+14.5f}{b.mean():>+14.5f}{h.mean():>+12.5f}{b.mean()-k.mean():>+12.5f}")

print("\n=== 配对差(融合目标 − KING 侧组合), 整个 combo 期, 3 日块自举 ===")
sub = [r for r in rows if r["A"] >= COMBO and r["king"] is not None and r["blend"] is not None]
d = np.array([r["blend"] - r["king"] for r in sub])
day = np.array([time.strftime("%Y-%m-%d", time.gmtime(r["A"])) for r in sub])
days = sorted(set(day))
blocks = [days[i:i + 3] for i in range(0, len(days), 3)]
rng = np.random.default_rng(20260919)
bs = []
for _ in range(8000):
    pick = [blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]
    sel = np.concatenate([d[np.isin(day, b)] for b in pick])
    bs.append(sel.mean())
bs = np.array(bs)
print(f"  n {len(d)} 锚 / {len(days)} 日 / {len(blocks)} 个 3 日块")
print(f"  点估计 {d.mean():+.5f}   95% CI [{np.percentile(bs,2.5):+.5f}, {np.percentile(bs,97.5):+.5f}]"
      f"   含 0 = {np.percentile(bs,2.5) < 0 < np.percentile(bs,97.5)}")
print(f"  复审报的是 −0.00614, CI [−0.00992, −0.00304]")
print("\n★ 边界: 比的是【组合权重】; 融合阶段还含成员选择/归一化/FTRIM/平滑, 本装置分不开。")
print("  不能据此判定 F10 无效, 也没有证明移除 F10 能提高净收益。IC 是排序量不是净额量。")
