#!/usr/bin/env python3
"""Read-only analysis of -5022 (post-only would cross) rejects in the live pilot_log.
Inputs: state/live/pilot_log/<day>/orders.jsonl (append-only). No writes outside scratch."""
import json, glob, os, sys, math, collections
from datetime import datetime, timezone
ROOT = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
DAY0 = sys.argv[1] if len(sys.argv) > 1 else "20260815"
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "2026*"))):
    day = os.path.basename(d)
    if day < DAY0: continue
    f = os.path.join(d, "orders.jsonl")
    if not os.path.exists(f): continue
    with open(f) as fh:
        for i, l in enumerate(fh):
            try: r = json.loads(l)
            except Exception: continue
            r["_day"] = day; r["_line"] = i
            rows.append(r)
print("rows", len(rows), "days", DAY0, "..", rows[-1]["_day"] if rows else None)
def is5022(r): return r.get("terminal_reason") == "venue_reject" and "-5022" in (r.get("note") or "")
def ts(a): return datetime.fromtimestamp(a, tz=timezone.utc).strftime("%m-%d %HZ")
# ---- per-anchor table: attempt-1 maker orders that reached the venue (submitted or venue_reject)
by_anchor = collections.OrderedDict()
for r in rows:
    if r.get("attempt_idx") != 1: continue
    if r.get("order_type") not in (None, "maker", "LIMIT", "limit") and r.get("topup_source"): continue
    a = r["anchor_ts"]
    d = by_anchor.setdefault(a, dict(n_rows=0, n_venue=0, n5022=0, n_other_rej=0, n_sub=0, sub_ts=[], spans=None, n_behind=0, n5022_behind=0, n_join=0, n5022_join=0, buy=0, sell=0, b5022=0, s5022=0))
    d["n_rows"] += 1
    tr = r.get("terminal_reason")
    reached = (r.get("submit_ts") is not None) or tr == "venue_reject"
    if not reached: continue
    d["n_venue"] += 1
    if r.get("submit_ts") is not None:
        d["n_sub"] += 1; d["sub_ts"].append(r["submit_ts"])
    if is5022(r):
        d["n5022"] += 1
        if r.get("side") == "buy": d["b5022"] += 1
        else: d["s5022"] += 1
    elif tr == "venue_reject": d["n_other_rej"] += 1
    if r.get("side") == "buy": d["buy"] += 1
    else: d["sell"] += 1
    arm = r.get("placement_arm")
    if arm == "behind":
        d["n_behind"] += 1; d["n5022_behind"] += is5022(r)
    elif arm == "join":
        d["n_join"] += 1; d["n5022_join"] += is5022(r)
print("\n=== per-anchor (attempt-1 makers that reached the venue) ===")
print(f"{'anchor':>9} {'nrow':>5} {'venue':>5} {'5022':>5} {'rate':>6} {'oth':>4} {'span_s':>7} {'buy%':>5} {'sell%':>5} {'join%':>6} {'behind%':>7}")
for a, d in by_anchor.items():
    if d["n_venue"] == 0: continue
    span = (max(d["sub_ts"]) - min(d["sub_ts"])) if len(d["sub_ts"]) > 1 else float("nan")
    jr = d["n5022_join"] / d["n_join"] * 100 if d["n_join"] else float("nan")
    br = d["n5022_behind"] / d["n_behind"] * 100 if d["n_behind"] else float("nan")
    print(f"{ts(a):>9} {d['n_rows']:>5} {d['n_venue']:>5} {d['n5022']:>5} {d['n5022']/d['n_venue']*100:>5.1f}% {d['n_other_rej']:>4} {span:>7.1f} {d['b5022']/max(d['buy'],1)*100:>4.0f}% {d['s5022']/max(d['sell'],1)*100:>4.0f}% {jr:>5.0f}% {br:>6.0f}%")
# ---- sequence-position effect: within each anchor, rank rows by line order; decile of position vs reject prob
print("\n=== reject prob by within-anchor submission position decile (pooled, attempt-1, reached venue) ===")
pos_bins = collections.defaultdict(lambda: [0, 0])
age_bins = collections.defaultdict(lambda: [0, 0])
for a, d in by_anchor.items():
    seq = [r for r in rows if r["anchor_ts"] == a and r.get("attempt_idx") == 1 and ((r.get("submit_ts") is not None) or r.get("terminal_reason") == "venue_reject")]
    n = len(seq)
    if n < 20: continue
    # interpolate time for rejected rows from neighbouring submitted rows (line order = submission order)
    t0 = min(r["submit_ts"] for r in seq if r.get("submit_ts"))
    last = t0
    for k, r in enumerate(seq):
        if r.get("submit_ts"): last = r["submit_ts"]
        age = last - t0
        dec = min(int(k / n * 10), 9)
        pos_bins[dec][0] += 1; pos_bins[dec][1] += is5022(r)
        ab = min(int(age // 10), 12)
        age_bins[ab][0] += 1; age_bins[ab][1] += is5022(r)
for dec in sorted(pos_bins):
    n, k = pos_bins[dec]; print(f"  position decile {dec}: n={n:5d} reject={k/n*100:5.1f}%")
print("=== reject prob by approx quote age (s since first submit of the anchor) ===")
for ab in sorted(age_bins):
    n, k = age_bins[ab]; print(f"  age {ab*10:3d}-{ab*10+10:3d}s: n={n:5d} reject={k/n*100:5.1f}%")
# ---- spread effect (spread_at_submit_bps only exists on submitted rows; for rejects use anchor-level median from other rows of the same symbol/day)
print("\n=== reject prob by anchor-time spread bucket (bps; spread taken from the symbol's submitted rows same day) ===")
sp_by = collections.defaultdict(list)
for r in rows:
    if r.get("spread_at_submit_bps") is not None: sp_by[(r["_day"], r["symbol"])].append(r["spread_at_submit_bps"])
sp_bins = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r.get("attempt_idx") != 1: continue
    if not ((r.get("submit_ts") is not None) or r.get("terminal_reason") == "venue_reject"): continue
    s = r.get("spread_at_submit_bps")
    if s is None:
        l = sp_by.get((r["_day"], r["symbol"]))
        if not l: continue
        s = sorted(l)[len(l) // 2]
    b = 0 if s < 2 else 1 if s < 5 else 2 if s < 10 else 3 if s < 20 else 4
    sp_bins[b][0] += 1; sp_bins[b][1] += is5022(r)
lab = ["<2", "2-5", "5-10", "10-20", ">=20"]
for b in sorted(sp_bins):
    n, k = sp_bins[b]; print(f"  spread {lab[b]:>5} bps: n={n:5d} reject={k/n*100:5.1f}%")
# ---- attempt-2 requote outcomes and top-ups
print("\n=== attempt-2 (fresh-quote requote) outcomes per day ===")
a2 = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    if r.get("attempt_idx") == 2: a2[r["_day"]][r.get("terminal_reason")] += 1
for d in sorted(a2): print(" ", d, dict(a2[d]))
print("\n=== top-up rows (topup_source) per day: count, |notional| ===")
tu = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
for r in rows:
    src = r.get("topup_source")
    if src:
        tu[r["_day"]][src][0] += 1; tu[r["_day"]][src][1] += abs(r.get("intended_notional") or 0)
for d in sorted(tu): print(" ", d, {k: (v[0], round(v[1])) for k, v in tu[d].items()})
# ---- symbol concentration of rejects (last 3 days)
print("\n=== symbols most often -5022 (last 3 days) ===")
days = sorted({r["_day"] for r in rows})[-3:]
c = collections.Counter(); tot = collections.Counter()
for r in rows:
    if r["_day"] in days and r.get("attempt_idx") == 1 and ((r.get("submit_ts") is not None) or r.get("terminal_reason") == "venue_reject"):
        tot[r["symbol"]] += 1
        if is5022(r): c[r["symbol"]] += 1
for s, k in c.most_common(15): print(f"  {s:>14} {k:3d}/{tot[s]:3d}")
print("  n symbols with >=1 reject:", len(c), "of", len(tot))
