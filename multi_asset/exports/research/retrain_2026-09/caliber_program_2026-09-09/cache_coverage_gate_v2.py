"""Coverage gate v2 (fixes v1's under-detection of long holes). Per symbol: first/last day with >=200 finite ch0 bars define
its life; any zero-bar day strictly inside the life = HOLE. Runs of holes are reported with symbol counts; runs > 30 days are
listed separately as possible delist/relist (not gated). Also: WIDE-GAP days (full-bar symbols < 90% of symbols in-life)."""
import numpy as np, sys, time
sys.path.insert(0, "/workspace"); from zload import zload
p = sys.argv[1]; Z = zload(p, allow_pickle=True); ts = Z["ts"].astype(np.int64); sym = np.array([str(s) for s in Z["symbols"]])
day = ts // 86400; ud, inv = np.unique(day, return_inverse=True); nd = len(ud)
fin = np.isfinite(Z["data"][:, :, 0]); cnt = np.zeros((nd, len(sym)), np.int32); np.add.at(cnt, inv, fin.astype(np.int32))
alive_day = cnt >= 200; first = np.array([np.argmax(alive_day[:, j]) if alive_day[:, j].any() else -1 for j in range(len(sym))])
last = np.array([nd - 1 - np.argmax(alive_day[::-1, j]) if alive_day[:, j].any() else -1 for j in range(len(sym))])
inlife = np.zeros_like(alive_day)
for j in range(len(sym)):
    if first[j] >= 0: inlife[first[j]:last[j] + 1, j] = True
hole = inlife & (cnt == 0); full = cnt >= 288
D = lambda d: time.strftime("%F", time.gmtime(ud[d] * 86400))
print("cache %s : %d days x %d symbols ; symbols with a life %d" % (p.split("/")[-1], nd, len(sym), int((first >= 0).sum())), flush=True)
# runs per symbol -> aggregate by (start,end)
from collections import defaultdict
runs = defaultdict(list)
for j in range(len(sym)):
    h = np.where(hole[:, j])[0]
    if len(h) == 0: continue
    s = h[0]; prev = h[0]
    for d in h[1:]:
        if d != prev + 1: runs[(s, prev)].append(j); s = d
        prev = d
    runs[(s, prev)].append(j)
short = [(k, v) for k, v in runs.items() if k[1] - k[0] + 1 <= 30]; longr = [(k, v) for k, v in runs.items() if k[1] - k[0] + 1 > 30]
bad = 0
for (a, b), js in sorted(short, key=lambda x: (-len(x[1]), x[0])):
    if len(js) >= 3:
        bad += len(js) * (b - a + 1); print("  HOLE  %s .. %s  (%d days)  symbols %3d  e.g. %s" % (D(a), D(b), b - a + 1, len(js), ", ".join(sym[js[:6]])), flush=True)
singles = [(k, v) for k, v in short if len(v) < 3]
print("  single/double-symbol short gaps (venue halts etc., listed not gated): %d runs, e.g. %s" % (len(singles), [(D(k[0]), D(k[1]), sym[v].tolist()) for k, v in sorted(singles)[:6]]), flush=True)
for (a, b), js in sorted(longr): print("  LONG-GAP %s .. %s (%d days) symbols %d e.g. %s  [possible delist/relist, not gated]" % (D(a), D(b), b - a + 1, len(js), ", ".join(sym[js[:4]])), flush=True)
wide = [d for d in range(1, nd - 1) if inlife[d].sum() > 100 and full[d].sum() < 0.9 * inlife[d].sum()]   # first/last day are boundaries (first day has 287 bars: axis starts at 00:00)
for d in wide: print("  WIDE-GAP %s  full %d / in-life %d" % (D(d), int(full[d].sum()), int(inlife[d].sum())), flush=True)
print("  last day %s: full %d, any-bar %d (boundary, not gated)" % (D(nd - 1), int(full[nd - 1].sum()), int((cnt[nd - 1] > 0).sum())), flush=True)
print("COVERAGE_GATE_V2 %s (hole symbol-days %d in multi-symbol runs; wide-gap days %d)" % ("FAIL" if (bad or wide) else "PASS", bad, len(wide)), flush=True)
sys.exit(3 if (bad or wide) else 0)
