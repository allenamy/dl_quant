#!/usr/bin/env python3
"""0C audit Q4 — is the 08:19Z flatten the trip's normal consequence, or the self-harm loop again?

The self-harm loop, stated as a testable shape:
    ledger row missing a quantity  ->  reconcile cannot size the execution  ->  §4-5b anomaly
    ->  trip  ->  protective flatten  ->  the flatten writes MORE rows missing a quantity  ->  ...

So the question is not "did the book go to zero" (it did, and that is what a flatten does). It is:
does the 08:19Z reconciliation contain a NEW unquantifiable execution, and was it produced by the
flatten itself?

Also fixes two things my earlier pass got wrong at this anchor and must not report as evidence:
  (a) the flatten's executions are NOT in fills.jsonl (venue_fills attributes trades by the
      rebalance's client-id prefix; a flatten carries FLATTEN-<ts>), so caliber A's `dq_fills` is
      empty there and its residual is an artefact of MY method, not drift.
  (b) after a flatten q2 == 0, so `mark = |n2/q2|` is undefined; my earlier script silently priced
      a 1.06e6-contract residual at ZERO USDT. That is reconcile's own [D1] trap, reproduced in
      the audit tool. Production has the n1/q1 and last-fill-price fallback chain; this does too.
Read-only.
"""
import json, os, datetime, sys
from collections import defaultdict

ROOT = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
DAYS = sorted(d for d in os.listdir(ROOT) if len(d) == 8 and d.isdigit())
A_TRIP, A_POST = 1785225684.348149, 1785226740.721801


def rd(day, table):
    p = os.path.join(ROOT, day, f"{table}.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def iso(t):
    return datetime.datetime.fromtimestamp(float(t), datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


ORDERS = [o for d in DAYS for o in rd(d, "orders")]
FILLS = [f for d in DAYS for f in rd(d, "fills")]
RB = [r for d in DAYS for r in rd(d, "position_readback")]

rb_by_anchor, rb_time = defaultdict(dict), {}
for r in RB:
    rb_by_anchor[r["anchor_ts"]][r["symbol"]] = r
    rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
t_lo, t_hi = rb_time[A_TRIP], rb_time[A_POST]

print("=" * 100)
print(f"POST-FLATTEN INTERVAL ({iso(t_lo)}, {iso(t_hi)}]")
print("=" * 100)

# ── every order row whose execution time lands in this interval ────────────────────────────────
in_win = []
for o in ORDERS:
    t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
    if t is not None and t_lo < float(t) <= t_hi:
        in_win.append((float(t), o))
in_win.sort(key=lambda x: x[0])
from collections import Counter
print("order rows in window, by (order_type, terminal_reason):")
for k, v in sorted(Counter((o.get("order_type"), o.get("terminal_reason")) for _, o in in_win).items()):
    print(f"   {str(k):<52} {v}")
print("fills rows in window:",
      sum(1 for f in FILLS if f.get("fill_ts") is not None and t_lo < float(f["fill_ts"]) <= t_hi))

# ── THE Q4 QUESTION: rows written after the trip that carry a missing quantity field ───────────
print("\n### Q4a — rows in this interval whose QUANTITY cannot be derived")
bad = []
for t, o in in_win:
    fn, px = o.get("filled_notional"), o.get("avg_fill_px")
    if o.get("submit_ts") is None:
        continue                                   # never left the process: structural zero
    if fn is None:
        bad.append(("filled_notional=None", t, o))
    elif float(fn) != 0.0 and not px:
        bad.append(("avg_fill_px=None (the 08:01 form)", t, o))
if not bad:
    print("  none.")
for form, t, o in bad:
    print(f"  [{form}] {iso(t)} {o['symbol']:<14} type={o.get('order_type')} "
          f"reason={o.get('terminal_reason')!r} filled_notional={o.get('filled_notional')} "
          f"avg_fill_px={o.get('avg_fill_px')!r} rebalance_id={o.get('rebalance_id')}")
    for k in ("note", "flatten_error"):
        if o.get(k):
            print(f"        {k}: {str(o[k])[:400]}")

# ── how many flatten rows DID carry a usable quantity? (denominator for the loop claim) ────────
fl = [o for _, o in in_win if o.get("order_type") == "protective_flatten"]
print(f"\n### Q4b — protective_flatten rows in this interval: {len(fl)}")
good = [o for o in fl if o.get("filled_notional") is not None
        and (float(o["filled_notional"]) == 0.0 or o.get("avg_fill_px"))]
print(f"  quantity derivable : {len(good)}")
print(f"  quantity MISSING   : {len(fl) - len(good)}   "
      f"-> {[o['symbol'] for o in fl if o not in good]}")

# ── residual at the post-flatten anchor, with the SAME fallback chain production uses ──────────
print("\n### Q4c — residual at the post-flatten anchor (dq from ORDERS, not fills, because the "
      "flatten's trades are unattributed)")
dq_ord, unknown = defaultdict(float), {}
for t, o in in_win:
    fn = o.get("filled_notional")
    if fn is None:
        if o.get("submit_ts") is not None:
            unknown[o["symbol"]] = o
        continue
    fn = float(fn)
    if fn == 0.0:
        continue
    px = o.get("avg_fill_px")
    if px:
        dq_ord[o["symbol"]] += fn / float(px)
    else:
        unknown[o["symbol"]] = o
last_px = {}
for f in FILLS:
    if f.get("fill_ts") is not None and t_lo < float(f["fill_ts"]) <= t_hi and f.get("fill_px"):
        last_px[f["symbol"]] = float(f["fill_px"])

prv, cur = rb_by_anchor[A_TRIP], rb_by_anchor[A_POST]
rows = []
for s, c in cur.items():
    q2 = float(c.get("venue_position_qty"))
    p = prv.get(s)
    q1 = float(p.get("venue_position_qty")) if p else 0.0
    n2 = float(c.get("venue_position_notional") or 0.0)
    n1 = float(p.get("venue_position_notional") or 0.0) if p else 0.0
    resid = q2 - (q1 + dq_ord.get(s, 0.0))
    mark = None
    for cand, why in ((n2 / q2 if q2 else None, "T2 notional/qty"),
                      (n1 / q1 if q1 else None, "T1 notional/qty"),
                      (last_px.get(s), "last fill px"),
                      (c.get("mid_at_anchor"), "mid")):
        if cand:
            mark = abs(float(cand)); msrc = why; break
    rows.append((abs(resid) * (mark or 0.0), s, resid, mark, msrc if mark else "NO MARK",
                 s in unknown))
rows.sort(reverse=True)
print(f"{'symbol':<14}{'residual(qty)':>18}{'USDT@fallback':>16}{'mark_src':<20}{'unknown?':>10}")
for u, s, r, mk, src, unk in rows[:12]:
    print(f"{s:<14}{r:>18.6f}{u:>16.4f}  {src:<20}{'YES' if unk else '.':>10}")
print(f"\nnames with |residual| > 1e-6 contracts: "
      f"{sum(1 for u, s, r, mk, src, unk in rows if abs(r) > 1e-6)}")
print(f"max USDT residual (fallback-priced) : {rows[0][0]:.4f} on {rows[0][1]}")

# ── is the guard currently still tripped, and on what? ─────────────────────────────────────────
print("\n### Q4d — current watchdog state")
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import pilot_log as PL, reconcile as RC
rec = RC.reconcile([(d, PL.read_day(ROOT, d)) for d in DAYS])
print(f"last_reconciled_ats = {rec['last_reconciled_ats']!r} ({iso(rec['last_reconciled_ats'])})")
print(f"§4-5b `latest` NOW  = {len(rec['latest'])} -> "
      f"{[(a['symbol'], a['kind'], a.get('terminal_reason')) for a in rec['latest']]}")
print(f"§4-7 drift NOW      = {bool(rec['latest'])}   (bool of the SAME list)")
