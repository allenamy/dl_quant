#!/usr/bin/env python3
"""v2: replicate the alarm ratio vs the true reject rate; latency/span; arms; economics. Read-only."""
import json, glob, os, sys, collections, math
from datetime import datetime, timezone
ROOT = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
DAY0 = sys.argv[1] if len(sys.argv) > 1 else "20260822"
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "2026*"))):
    day = os.path.basename(d)
    if day < DAY0: continue
    f = os.path.join(d, "orders.jsonl")
    if not os.path.exists(f): continue
    for l in open(f):
        try: r = json.loads(l); r["_day"] = day; rows.append(r)
        except Exception: pass
def is5022(r): return r.get("terminal_reason") == "venue_reject" and "-5022" in (r.get("note") or "")
def ts(a): return datetime.fromtimestamp(a, tz=timezone.utc).strftime("%m-%d %HZ")
A = collections.OrderedDict()
for r in rows:
    a = r["anchor_ts"]; d = A.setdefault(a, collections.Counter()); d["_day"] = r["_day"]
    att = r.get("attempt_idx"); tr = r.get("terminal_reason") or ""; tu = r.get("topup_source")
    if tu:  # top-up rows
        d["topup_" + tu] += 1
        if tu == "from_reject" and r.get("filled_notional"): d["fr_fill_notional"] += abs(r["filled_notional"]); d["fr_fee"] += (r.get("fee_paid") or 0)
        continue
    if att == 1:
        if r.get("submit_ts") is not None: d["rested1"] += 1; d.setdefault("_sub", []).append(r["submit_ts"]) if False else None
        if r.get("submit_ts") is not None:
            d["_first"] = min(d.get("_first", 9e18), r["submit_ts"]); d["_last"] = max(d.get("_last", 0), r["submit_ts"])
        elif tr == "venue_reject": d["rej1"] += 1; d["rej1_5022"] += is5022(r)
        elif tr.startswith("skipped") or tr.startswith("blocked"): d["skip1"] += 1
        else: d["other1_" + tr] += 1
        if r.get("placement_arm") in ("join", "behind") and ((r.get("submit_ts") is not None) or tr == "venue_reject"):
            d["arm_" + r["placement_arm"]] += 1; d["arm5022_" + r["placement_arm"]] += is5022(r)
    elif att == 2:
        if r.get("submit_ts") is not None and tr not in ("venue_reject",): d["rested2"] += 1
        elif tr == "venue_reject": d["rej2"] += 1
        else: d["skip2"] += 1
print(f"{'anchor':>9} {'reach1':>6} {'rej1':>5} {'true%':>6} {'skip1':>5} {'rej2':>5} {'rest2':>5} {'alarm%':>6} {'lat_s':>6} {'span_s':>6} {'fr_topup':>8} {'fr_notional':>11}")
series = []
for a, d in A.items():
    reach1 = d["rested1"] + d["rej1"]
    if reach1 < 20: continue
    true = d["rej1"] / reach1 * 100
    den = d["rej1"] + d["rej2"] + d["skip1"]
    alarm = (d["rej1"] + d["rej2"]) / den * 100 if den else float("nan")
    lat = d["_first"] - a if d.get("_first") else float("nan"); span = (d["_last"] - d["_first"]) if d.get("_first") else float("nan")
    series.append((a, d["_day"], reach1, true, alarm, d["skip1"], lat, span, d["rej1"], d["rej2"], d["rested2"]))
    print(f"{ts(a):>9} {reach1:>6} {d['rej1']:>5} {true:>5.1f}% {d['skip1']:>5} {d['rej2']:>5} {d['rested2']:>5} {alarm:>5.1f}% {lat:>6.1f} {span:>6.1f} {d['topup_from_reject']:>8} {d['fr_fill_notional']:>11.0f}")
import statistics as st
def wk(lo, hi, idx): v = [s[idx] for s in series if lo <= s[1] <= hi and not math.isnan(s[idx])]; return (st.mean(v) if v else float('nan'), len(v))
for lo, hi in [("20260822", "20260828"), ("20260829", "20260902"), ("20260903", "20260905")]:
    print(f"window {lo}..{hi}: true {wk(lo,hi,3)[0]:.1f}%  alarm {wk(lo,hi,4)[0]:.1f}%  skip1 {wk(lo,hi,5)[0]:.0f}  reach1 {wk(lo,hi,2)[0]:.0f}  lat {wk(lo,hi,6)[0]:.1f}s  span {wk(lo,hi,7)[0]:.1f}s  n={wk(lo,hi,3)[1]}")
# rank correlations across anchors
def spearman(x, y):
    n = len(x); rx = {v: i for i, v in enumerate(sorted(x))}; ry = {v: i for i, v in enumerate(sorted(y))}
    xs = [sorted(x).index(v) for v in x]; ys = [sorted(y).index(v) for v in y]
    mx, my = st.mean(xs), st.mean(ys); num = sum((a-mx)*(b-my) for a, b in zip(xs, ys)); den = math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys)); return num/den if den else float('nan')
ok = [s for s in series if not math.isnan(s[6])]
print("spearman(true reject rate, planning latency) =", round(spearman([s[6] for s in ok], [s[3] for s in ok]), 3), "n", len(ok))
print("spearman(true reject rate, submission span) =", round(spearman([s[7] for s in ok], [s[3] for s in ok]), 3))
print("spearman(true reject rate, reach1 count)     =", round(spearman([s[2] for s in ok], [s[3] for s in ok]), 3))
print("spearman(alarm ratio, skip1 count)           =", round(spearman([s[5] for s in ok], [s[4] for s in ok]), 3))
# arms pooled
tot = collections.Counter()
for d in A.values():
    for k in ("arm_join", "arm_behind", "arm5022_join", "arm5022_behind"): tot[k] += d[k]
for arm in ("join", "behind"):
    n, k = tot["arm_" + arm], tot["arm5022_" + arm]; p = k / n; se = math.sqrt(p * (1 - p) / n)
    print(f"arm {arm:>6}: n={n} reject={p*100:.1f}% ±{se*100*1.96:.1f}")
# requote outcome pooled
r2 = sum(d["rej2"] for d in A.values()); s2 = sum(d["rested2"] for d in A.values())
print(f"requote pooled: rested {s2}, refused again {r2} -> rested share {s2/(s2+r2)*100:.1f}%")
fr_n = sum(d["topup_from_reject"] for d in A.values()); fr_not = sum(d["fr_fill_notional"] for d in A.values()); fr_fee = sum(d["fr_fee"] for d in A.values())
print(f"from_reject top-ups: n={fr_n}, filled notional {fr_not:.0f} USDT, fee paid {fr_fee:.2f} USDT over {len(A)} anchors")
