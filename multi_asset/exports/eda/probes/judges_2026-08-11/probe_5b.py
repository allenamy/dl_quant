"""0C — is the §4-5b trigger a TRUE positive? (applying the 'a guard firing != firing correctly' rule
to my own cited evidence). Reproduces the watchdog's own comparison, then characterises the hits."""
import sys, os
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live")
import pilot_log as PL
from collections import defaultdict
import numpy as np

root = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/live/pilot_log"
days = sorted([d for d in os.listdir(root) if d.isdigit()])
prev_rb = None
rows, ncomp = [], 0
for d in days:
    one = PL.read_day(root, d)
    rb = defaultdict(dict)
    for r in one["position_readback"]:
        rb[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
    fb = defaultdict(lambda: defaultdict(float))
    for o in one["orders"]:
        f = float(o["filled_notional"] or 0.0)
        if f > 0:
            fb[o["anchor_ts"]][o["symbol"]] += (1 if o["side"] == "buy" else -1) * f
    for ats in sorted(rb):
        cur = rb[ats]
        if prev_rb is not None:
            for sym, v in cur.items():
                exp = prev_rb.get(sym, 0.0) + fb[ats].get(sym, 0.0)
                un = abs(v - exp)
                sc = max(abs(exp), abs(v), 1.0)
                ncomp += 1
                if un / sc > 0.10:
                    rows.append((sym, exp, v, un, un / sc, max(abs(exp), abs(v))))
        prev_rb = cur

print(f"comparisons {ncomp} | anomalies {len(rows)} ({len(rows)/max(ncomp,1):.2%})", flush=True)
if rows:
    u = np.array([r[3] for r in rows])
    s = np.array([r[5] for r in rows])
    fr = np.array([r[4] for r in rows])
    print(f"unexplained USD : median {np.median(u):.2f}  p90 {np.percentile(u,90):.2f}  max {u.max():.2f}")
    print(f"position scale $: median {np.median(s):.2f}  p90 {np.percentile(s,90):.2f}  max {s.max():.2f}")
    print(f"unexplained FRAC: median {np.median(fr):.3f}  max {fr.max():.3f}")
    print(f"hits with unexplained < $5 : {int((u<5).sum())}/{len(rows)}")
    print(f"hits with scale       < $50: {int((s<50).sum())}/{len(rows)}")
    print(f"hits that are a FULL position appear/vanish (frac>0.99): {int((fr>0.99).sum())}")
    for r in rows[:6]:
        print(f"   {r[0]:12s} expected {r[1]:10.2f}  observed {r[2]:10.2f}  unexplained {r[3]:8.2f} ({r[4]:.2f})")
