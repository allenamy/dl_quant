# -*- coding: utf-8 -*-
"""Does the Aug->Sep realized rank-IC step survive at MATCHED BREADTH?
The co-held name count jumps 107 -> 248 at the 08-26 combo switch. A broader book holds more
marginal names, which can lower realized rank-IC with no signal decay at all. So: recompute the
device's own statistic restricted to the top-k names by |notional|, for several k, both sides.

POSITIVE CONTROL FIRST: the full-book replication must reproduce ic_monitor.jsonl's rank_ic.
READ-ONLY."""
import json, glob, os, time, collections
import numpy as np

PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
GRID, MAXGAP, MINN = 14400, 6*3600, 30
SW = 1787716800  # 2026-08-26 04Z, first combo anchor

# ---- load position_readback exactly as the device does ----
anch = {}
for p in sorted(glob.glob(f"{PL}/*/position_readback.jsonl")):
    for l in open(p, errors="ignore"):
        try: r = json.loads(l)
        except Exception: continue
        q, nt = r.get("venue_position_qty"), r.get("venue_position_notional")
        if q in (None, 0) or nt is None: continue
        t = float(r.get("anchor_ts") or 0)
        g = int(t//GRID*GRID)
        anch.setdefault(g, {})[r["symbol"]] = (float(nt), abs(float(nt))/abs(float(q)))
print(f"position_readback: {len(anch)} 个网格锚, {time.strftime('%m-%d %HZ', time.gmtime(min(anch)))} .. {time.strftime('%m-%d %HZ', time.gmtime(max(anch)))}")

def rankdata(x):
    x = np.asarray(x, float); o = np.argsort(x, kind="mergesort"); r = np.empty(len(x), float)
    r[o] = np.arange(1, len(x)+1)
    # average ties
    i = 0
    xs = x[o]
    while i < len(xs):
        j = i
        while j+1 < len(xs) and xs[j+1] == xs[i]: j += 1
        if j > i: r[o[i:j+1]] = (i+1+j+1)/2.0
        i = j+1
    return r
def spear(a, b):
    if len(a) < 3: return None
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra*ra).sum()*(rb*rb).sum())
    return None if d == 0 else float((ra*rb).sum()/d)

def ic_at(t0, topk=None):
    t1 = t0 + GRID
    if t0 not in anch: return None, 0
    nxt = [g for g in anch if t0 < g <= t0+MAXGAP]
    if not nxt: return None, 0
    t1 = min(nxt)
    a, b = anch[t0], anch[t1]
    syms = [s for s in a if s in b]
    if len(syms) < MINN: return None, len(syms)
    syms.sort(key=lambda s: -abs(a[s][0]))
    if topk is not None: syms = syms[:topk]
    if len(syms) < MINN: return None, len(syms)
    w   = np.array([a[s][0] for s in syms], float)
    ret = np.array([b[s][1]/a[s][1]-1.0 for s in syms], float)
    return spear(w, ret), len(syms)

# ---- positive control ----
led = {r["anchor_ts"]: r for r in (json.loads(l) for l in open("/Users/haosiyu/dl_quant_live/state/live/ic_monitor.jsonl") if l.strip())}
ok = bad = 0; worst = 0.0
for t, r in led.items():
    mine, nn = ic_at(int(t))
    if r.get("rank_ic") is None or mine is None: continue
    d = abs(mine - r["rank_ic"])
    worst = max(worst, d)
    if d <= 6e-5 and nn == r["n"]: ok += 1
    else:
        bad += 1
        if bad <= 3: print(f"   不符 {time.strftime('%m-%d %HZ',time.gmtime(t))} 我 {mine:+.5f}/n{nn} vs 账本 {r['rank_ic']:+.5f}/n{r['n']}")
print(f"★ 正控: 复现账本 {ok} 锚逐值相符(|Δ| ≤ 6e-5 且 n 相同), 不符 {bad}, 最大 |Δ| {worst:.2e}")
if bad or ok < 200:
    print("  ⇒ 复现不充分, 下面的变体不出结论。"); raise SystemExit(1)
print()

# ---- matched breadth ----
ts_all = sorted(t for t in anch if ic_at(t)[0] is not None)
day = {t: time.strftime("%Y-%m-%d", time.gmtime(t)) for t in ts_all}
rng = np.random.default_rng(20260919)
def dayblock(vals_by_t, tsel, B=6000):
    ds = sorted({day[t] for t in tsel}); dm = collections.defaultdict(list)
    for t in tsel: dm[day[t]].append(vals_by_t[t])
    return np.array([np.mean(np.concatenate([dm[rng.choice(ds)] for _ in ds])) for _ in range(B)])

print(f"{'topk':<8}{'前 n锚':>7}{'前 IC':>10}{'后 n锚':>7}{'后 IC':>10}{'差':>10}{'日块自举 95% CI':>26}{'含0':>6}")
for k in (30, 50, 80, 107, 150, 200, None):
    vals = {}
    for t in ts_all:
        v, nn = ic_at(t, k)
        if v is not None: vals[t] = v
    pre  = [t for t in vals if t <  SW]
    post = [t for t in vals if t >= SW]
    if len(pre) < 20 or len(post) < 20: continue
    a = np.array([vals[t] for t in pre]); b = np.array([vals[t] for t in post])
    d = dayblock(vals, pre) - dayblock(vals, post)
    lo, hi = np.percentile(d, 2.5), np.percentile(d, 97.5)
    print(f"{str(k or 'all'):<8}{len(a):>7}{a.mean():>+10.5f}{len(b):>7}{b.mean():>+10.5f}{a.mean()-b.mean():>+10.5f}"
          f"{f'[{lo:+.5f}, {hi:+.5f}]':>26}{str(lo<0<hi):>6}")
print()
print("读法: 若把换装后的书【截到与换装前同样的宽度】(topk≈107)之后差仍显著, 则宽度稀释【不能】解释台阶;")
print("      若差在匹配宽度下消失, 则台阶主要是【书变宽】而不是【信号变差】。")
