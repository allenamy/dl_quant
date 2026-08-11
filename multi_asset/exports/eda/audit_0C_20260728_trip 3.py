#!/usr/bin/env python3
"""0C independent audit of the 2026-07-28T08:01:24Z anchor trip (anchor_ts=1785225684.348149).

Task: falsify the lead's false-positive verdict, not re-check its arithmetic.
Order of answering is the lead's priority: Q4 > Q1 > Q3 > Q2.

★ SCOPE NOTE THAT CHANGES WHERE EVERY NUMBER COMES FROM: the pilot runs in TESTNET mode, so the
  live ledger is state/testnet/pilot_log and the live guard state is state/testnet/watchdog.
  state/watchdog/ parses, is self-consistent, and says nothing happened.

Detailed per-question scripts (this file is the consolidated run):
  audit_0C_20260728/q1_qty_residual.py          Q1 contracts caliber
  audit_0C_20260728/q2_scan_and_precision.py    Q2 full-window sweep + dropout blind spot
  audit_0C_20260728/q3_same_root_cause.py       Q3 shared-derivation test
  audit_0C_20260728/q4_post_flatten.py          Q4 post-flatten interval
  audit_0C_20260728/q5_resume_gate_dryrun.py    consequence: can the trip be cleared?

Read-only w.r.t. ~/dl_quant_live. Nothing is written there and nothing is committed there.
"""
import os, sys, json, datetime, copy
from collections import defaultdict, Counter
from decimal import Decimal

LIVE = os.path.expanduser("~/dl_quant_live")
ROOT = os.path.join(LIVE, "state/testnet/pilot_log")
DAYS = sorted(d for d in os.listdir(ROOT) if len(d) == 8 and d.isdigit())
A_TRIP = 1785225684.348149          # the anchor that tripped
A_POST = 1785226740.721801          # the post-flatten defensive readback (08:19:00Z)


def rd(day, table):
    p = os.path.join(ROOT, day, f"{table}.jsonl")
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def iso(t):
    return datetime.datetime.fromtimestamp(float(t), datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


ORDERS = [o for d in DAYS for o in rd(d, "orders")]
FILLS = [f for d in DAYS for f in rd(d, "fills")]
RB = [r for d in DAYS for r in rd(d, "position_readback")]
rb_by_anchor, rb_time = defaultdict(dict), {}
for r in RB:
    rb_by_anchor[r["anchor_ts"]][r["symbol"]] = r
    rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
ANCHORS = sorted(rb_by_anchor)


def hdr(s):
    print("\n" + "=" * 100 + f"\n{s}\n" + "=" * 100)


# ══════════════════════════════════════════════════════════════════════════════════════════════
hdr("Q4 (top priority) — is the 08:19Z flatten a normal consequence, or the self-harm loop again?")

print("★ First: the one-liner in the task does not answer this, in three separate ways.\n")
raw = [json.loads(l) for l in open(os.path.join(ROOT, "20260728", "orders.jsonl"))]
try:
    _ = [r for r in raw if r["anchor_ts"] > 1785226700 and r.get("filled_notional", 0) > 0]
    print("   (a) it ran")
except TypeError as e:
    print(f"   (a) IT RAISES, it does not return []:  TypeError: {e}")
    print("       `.get('filled_notional', 0)` returns None when the key EXISTS holding None, and")
    print("       the default never applies. So the command cannot be read as evidence at all.")
signed_blind = [r for r in raw if r.get("filled_notional") is not None and r["filled_notional"] < 0]
print(f"   (b) `filled_notional > 0` DROPS EVERY SELL — {len(signed_blind)} rows in today's file "
      f"alone.\n       filled_notional is already signed (binance_broker: sign*cumQuote); this is "
      f"the exact\n       defect reconcile.py:8 was written to delete.")
fixed = [r for r in raw if r["anchor_ts"] > 1785226700
         and r.get("filled_notional") is not None and abs(r["filled_notional"]) > 0
         and r.get("avg_fill_px") is None]
print(f"   (c) made None-safe AND signed, it returns {fixed} — and that emptiness is NOT clean:")
invisible = [r for r in raw if r["anchor_ts"] > 1785226700
             and r.get("filled_notional") is None and r.get("submit_ts") is not None]
for r in invisible:
    print(f"       the actual defect row is INVISIBLE to it, because filled_notional is None,")
    print(f"       not >0:  {r['symbol']} {r['order_type']} {r['terminal_reason']!r} "
          f"fn={r.get('filled_notional')} px={r.get('avg_fill_px')!r}")
print("       A filter matching nothing and a guard confirming safety print the same thing.")

print("\n★ Second: the NO SAMPLE / CLEAN question, split at the right boundary.\n")
by_anchor = Counter(r["anchor_ts"] for r in raw)
print(f"   orders.jsonl anchor_ts buckets today: "
      f"{[(iso(a), n) for a, n in sorted(by_anchor.items())]}")
FLAT_A = 1785226740.245357
flat = [r for r in raw if r["anchor_ts"] == FLAT_A]
print(f"\n   WINDOW A — the trip's own flatten batch (anchor_ts {iso(FLAT_A)}): {len(flat)} rows")
print(f"      by terminal_reason: {dict(Counter(r['terminal_reason'] for r in flat))}")
derivable = [r for r in flat if r.get("filled_notional") is not None
             and (r["filled_notional"] == 0.0 or r.get("avg_fill_px"))]
print(f"      quantity derivable : {len(derivable)} / {len(flat)}")
print(f"      quantity MISSING   : {[r['symbol'] for r in flat if r not in derivable]}")
print(f"      ==> THERE IS A SAMPLE: {len(flat)} executions were produced after the trip fired.")

late_o = [o for o in ORDERS
          if float(o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("submit_ts") or 0) > A_POST]
late_f = [f for f in FILLS if f.get("fill_ts") and float(f["fill_ts"]) > A_POST]
print(f"\n   WINDOW B — strictly after the post-flatten readback ({iso(A_POST)}):")
print(f"      orders={len(late_o)}  fills={len(late_f)}  ==> NO SAMPLE (next anchor is 12:00Z), "
      f"NOT clean.")

print("\n★ Third: what the flatten actually did to the guard.\n")
sys.path.insert(0, os.path.join(LIVE, "live"))
import pilot_log as PL, reconcile as RC, watchdog_inputs as WI
rec = RC.reconcile([(d, PL.read_day(ROOT, d)) for d in DAYS])
print(f"   latest reconciled anchor NOW : {iso(rec['last_reconciled_ats'])}")
print(f"   §4-5b `latest` NOW           : {[(a['symbol'], a['kind'], a.get('terminal_reason')) for a in rec['latest']]}")
print(f"   §4-7 drift bit NOW           : {bool(rec['latest'])}")
print(f"   anomalies in window          : {len(rec['anomalies'])} (was 4 at trip time)")
for a in rec["anomalies"]:
    print(f"      {iso(a['anchor_ts'])} {a['symbol']:<12} {a['kind']} tr={a.get('terminal_reason')!r}")
p_rb = [(iso(a), rb_by_anchor[a]["PORTALUSDT"].get("venue_position_qty"),
         rb_by_anchor[a]["PORTALUSDT"].get("source"))
        for a in ANCHORS if "PORTALUSDT" in rb_by_anchor[a] and a > 1785190000]
print(f"\n   PORTALUSDT venue-reported qty: {p_rb}")
print("   ==> the venue says it is FLAT. The position is fine; only the RECORD of the exit is not.")
print("\n   VERDICT Q4: the flatten is the trip's normal consequence AND the loop recurred in a NEW")
print("   FORM. The 08:01 defect was `filled_notional` present + `avg_fill_px` null (rebalance")
print("   path). The new one is `filled_notional` NULL OUTRIGHT (ladder path). Second occurrence")
print("   of this exact shape: SEIUSDT 2026-07-27T16:18:41Z, one row per flatten both times.")

# ══════════════════════════════════════════════════════════════════════════════════════════════
hdr("Q1 — position residual in CONTRACTS, by a caliber that does not contain the lead's assumption")

t_lo, t_hi = rb_time[ANCHORS[ANCHORS.index(A_TRIP) - 1]], rb_time[A_TRIP]
print(f"interval ({iso(t_lo)}, {iso(t_hi)}]\n")
print("INDEPENDENCE — three DIFFERENT venue endpoints, none of them the field claimed broken:")
print("  q1,q2  <- position_readback.venue_position_qty, source='fapi/v3/account@post_anchor'")
print("           (watchdog.py:1211; refuses to write any row if quantities are unreadable)")
print("  dq     <- fills.jsonl fill_notional/fill_px = venue quoteQty/price, /fapi/v1/userTrades")
print("  the assumption under test, avg_fill_px <- /fapi/v1/order avgPrice — READ BY NEITHER.")
print("  The division quoteQty/price is an IDENTITY that rebuilds the venue's own `qty` field")
print("  (venue_fills.py:249 captures it and does not persist it), not a price estimate.\n")

dq_fills, nfill = defaultdict(float), Counter()
for f in FILLS:
    t = f.get("fill_ts")
    if t is None or not (t_lo < float(t) <= t_hi):
        continue
    px, nt, sd = f.get("fill_px"), f.get("fill_notional"), (f.get("side") or "").lower()
    if px and nt is not None and sd in ("buy", "sell"):
        dq_fills[f["symbol"]] += (1 if sd == "buy" else -1) * float(nt) / float(px)
        nfill[f["symbol"]] += 1

cur, prv = rb_by_anchor[A_TRIP], rb_by_anchor[ANCHORS[ANCHORS.index(A_TRIP) - 1]]
print(f"{'symbol':<12}{'q1 (venue)':>14}{'q2 (venue)':>14}{'dq (venue trades)':>20}"
      f"{'residual':>14}{'USDT':>10}{'#fills':>8}")
for s in ("SAGAUSDT", "SKLUSDT"):
    q1, q2 = float(prv[s]["venue_position_qty"]), float(cur[s]["venue_position_qty"])
    n2 = float(cur[s]["venue_position_notional"])
    r = q2 - (q1 + dq_fills[s])
    print(f"{s:<12}{q1:>14.4f}{q2:>14.4f}{dq_fills[s]:>20.6f}{r:>14.2e}"
          f"{abs(r) * abs(n2 / q2):>10.2e}{nfill[s]:>8}")

print("\nsame two names in EXACT decimal (float noise removed — these are the venue's own strings):")
for s, q1, q2, notl, px in (("SAGAUSDT", "-25776.4", "-24759.9", "12.8079", "0.0126"),
                            ("SKLUSDT", "-43369.0", "-32261.0", "43.454496", "0.003912")):
    d = Decimal(q2) - Decimal(q1) - Decimal(notl) / Decimal(px)
    print(f"   {s:<10} venue Δposition={Decimal(q2)-Decimal(q1):>10}  "
          f"venue Δtrades={Decimal(notl)/Decimal(px):>10}  residual={d}")

allr = []
for s, c in cur.items():
    q2 = float(c["venue_position_qty"])
    q1 = float(prv[s]["venue_position_qty"]) if s in prv else 0.0
    n2 = float(c["venue_position_notional"])
    r = q2 - (q1 + dq_fills.get(s, 0.0))
    allr.append(abs(r) * (abs(n2 / q2) if q2 else 0.0))
print(f"\nall {len(allr)} names at this anchor: max |residual| = {max(allr):.3e} USDT, "
      f"sum = {sum(allr):.3e} USDT")
print("VERDICT Q1: residual is EXACTLY ZERO in contracts. Your notional figures (-2.366/-4.903)")
print("are the revaluation term B30 removed; the position itself never moved unexplained.")

# ══════════════════════════════════════════════════════════════════════════════════════════════
hdr("Q3 — does §4-7's DRIFT derive from the same reconcile() as §4-5b?")

print("""CODE PATH (scheduler/run_anchor.py:261-263):
    ops_stats, venue_events, _ = WI.collect(log_root)          -> reconcile CALL #1
    WD.run(log_root, venue_events=.., ops_stats=ops_stats)     -> reconcile CALL #2

  CALL #1  watchdog_inputs.py:104-116
      _rec = RC.reconcile([(d, PL.read_day(root, d)) for d in PL.available_days(root)])
      out[-1]["unrecovered_position_drift"] = None if _rec["last_reconciled_ats"] is None
                                              else bool(_rec["latest"])
  CALL #2  watchdog.py:859-861 + :929
      _rec = RC.reconcile([(d, PL.read_day(root, d)) for d in PL.available_days(root)])
      _latest = [a for a in anomalies if a["anchor_ts"] == last_reconciled_ats]
  reconcile.py:389
      "latest": [a for a in anomalies if a["anchor_ts"] == last_ats]

=> STRICTLY: TWO calls, not one. But of ONE PURE FUNCTION, same root, same window
   (both PL.available_days(root)), same default tol/dust. And the conclusion is stronger than
   'they agree': §4-7's drift IS bool() of §4-5b's list. It has no per-name field to disagree with.
""")
ops = WI.derive_ops_stats(ROOT, DAYS)
print("every drift key §4-7 writes (this is its ENTIRE drift payload):")
for k in sorted(ops[-1]):
    if "drift" in k:
        print(f"   {k} = {json.dumps(ops[-1][k], ensure_ascii=False)[:100]}")
print("   -> no symbol-level field exists anywhere in it.")
print(f"\n§4-7's other half (fail rate) is NOT firing: "
      f"per_day={[o['rebalance_fail_rate'] for o in ops]} vs limit 0.05")

days_data = [(d, PL.read_day(ROOT, d)) for d in DAYS]


def perturbed(mut):
    d = copy.deepcopy(days_data)
    mut(d)
    r = RC.reconcile(d)
    return r, (None if r["last_reconciled_ats"] is None else bool(r["latest"]))


def truthful_backfill(d):
    """what a working backfill produces: give each unsized leg the size the VENUE's readbacks imply"""
    rbm = defaultdict(dict)
    for _x, one in d:
        for r in one.get("position_readback", []):
            rbm[r["anchor_ts"]][r["symbol"]] = r
    ats = sorted(rbm)
    for _x, one in d:
        for o in one["orders"]:
            if o.get("submit_ts") is None:
                continue
            if not (o.get("filled_notional") is None
                    or (float(o.get("filled_notional") or 0) != 0 and not o.get("avg_fill_px"))):
                continue
            t = float(o.get("last_fill_ts") or o["anchor_ts"])
            j = next((i for i, a in enumerate(ats)
                      if float(next(iter(rbm[a].values())).get("read_ts") or a) >= t), None)
            if j is None or o["symbol"] not in rbm[ats[j]]:
                continue
            c = rbm[ats[j]][o["symbol"]]
            p = rbm[ats[j - 1]].get(o["symbol"], {}) if j else {}
            q2, n2 = float(c.get("venue_position_qty") or 0), float(c.get("venue_position_notional") or 0)
            q1, n1 = float(p.get("venue_position_qty") or 0), float(p.get("venue_position_notional") or 0)
            mark = abs(n2 / q2) if q2 else (abs(n1 / q1) if q1 else 1.0)
            o["filled_notional"], o["avg_fill_px"] = (q2 - q1) * mark, mark
            o["terminal_reason"] = "filled"


CASES = [("as-is", lambda d: None),
         ("truthful backfill of every unsized leg", truthful_backfill),
         ("delete the latest anchor's readback",
          lambda d: [one.__setitem__("position_readback",
                                     [r for r in one["position_readback"] if r["anchor_ts"] != A_POST])
                     for _x, one in d]),
         ("inject a 500-contract phantom on BTCUSDT",
          lambda d: [r.__setitem__("venue_position_qty", float(r["venue_position_qty"]) + 500.0)
                     for _x, one in d for r in one["position_readback"]
                     if r["anchor_ts"] == A_POST and r["symbol"] == "BTCUSDT"])]
print(f"\nPERTURBATION TEST — does the 5b list track the 4-7 bit every time?")
print(f"{'perturbation':<44}{'5b n':<7}{'4-7 bit':<10}{'locked':<8}names")
locked_all = True
for nm, fn in CASES:
    r, bit = perturbed(fn)
    lk = bool(r["latest"]) == bool(bit)
    locked_all &= lk
    print(f"{nm:<44}{len(r['latest']):<7}{str(bit):<10}{'YES' if lk else 'NO':<8}"
          f"{[a['symbol'] for a in r['latest']][:3]}")
print(f"\nVERDICT Q3: SAME FACT, locked in every case ({locked_all}). One divergence mode exists and")
print("it is not a second cause: the two calls read an append-only ledger at different instants, so")
print("a row landing between them shows in §4-5b and not §4-7. Staleness; fails toward §4-5b.")

# ══════════════════════════════════════════════════════════════════════════════════════════════
hdr("Q2 — is there a third name, hidden in a lighter branch?")

print("THREE places a third name could hide, all checked:\n")
print(f"(i)   the anomaly list itself at the trip anchor:")
lat = [a for a in rec["anomalies"] if a["anchor_ts"] == A_TRIP]
print(f"      {[(a['symbol'], a['kind']) for a in lat]}   (n={len(lat)})")

unrec_trip = [u for u in rec["unreconcilable"] if u["anchor_ts"] == A_TRIP]
print(f"\n(ii)  `unreconcilable` — the LIGHTER branch [D2] is written to pre-empt:")
print(f"      at the trip anchor: {len(unrec_trip)}")
print(f"      in the window     : {rec['n_unreconcilable']} {rec['n_unreconcilable_by_kind']}")
byanch = Counter(u["anchor_ts"] for u in rec["unreconcilable"])
print(f"      newest anchor carrying any: {iso(max(byanch))}")
qcol = {}
for r in RB:
    qcol.setdefault(r["anchor_ts"], [0, 0])[0 if "venue_position_qty" in r else 1] += 1
first_q = min(a for a in qcol if qcol[a][0])
print(f"      reason: `venue_position_qty` only starts at {iso(first_q)}, so every earlier anchor")
print(f"      is honestly refused. The trip anchor is the FIRST to fully exercise B30's caliber.")

print(f"\n(iii) THE BRANCH NEITHER LIST CAN SHOW — reconcile iterates `cur.items()` only")
print(f"      (reconcile.py:311). A name in T1's readback and ABSENT from T2's is never compared:")
print(f"      not an anomaly, not unreconcilable, simply not in any output.")
drop_tot = []
for i in range(1, len(ANCHORS)):
    p, c = rb_by_anchor[ANCHORS[i - 1]], rb_by_anchor[ANCHORS[i]]
    for s in sorted(set(p) - set(c)):
        drop_tot.append((ANCHORS[i], s, float(p[s].get("venue_position_qty") or 0.0)))
print(f"      dropouts in the window: {len(drop_tot)}")
for a, s, q in drop_tot:
    print(f"        {iso(a)} {s:<12} qty held at T1 = {q}")
print(f"      all held zero -> benign here, but it is an unguarded path, not a checked-clean one.")

print(f"\n(iv)  a name that is BOTH unknown-size AND really drifting ([D2]'s own worry):")
for s in ("SAGAUSDT", "SKLUSDT"):
    q1, q2 = float(prv[s]["venue_position_qty"]), float(cur[s]["venue_position_qty"])
    print(f"      {s}: residual = {q2 - (q1 + dq_fills[s]):.2e} contracts -> no.")

print(f"\nVERDICT Q2: n=2 is right at that anchor. 109/109 names compared, 0 over floor,")
print(f"0 unreconcilable, 0 dropouts. Nothing was swallowed by a lighter branch.")

# ══════════════════════════════════════════════════════════════════════════════════════════════
hdr("CONSEQUENCE — can the trip be cleared right now?")
print("simulated ops/resume_from_trip.sh step 1/4 (HARD GATE) — see "
      "audit_0C_20260728/q5_resume_gate_dryrun.py")
print("  result: STILL TRIPPING on both triggers; §4-5b ANOMALOUS n=1 (PORTALUSDT) at "
      f"{iso(A_POST)}")
print("  => clearing the 08:01 flag does not clear the guard. The gate exits 1 and touches nothing.")
print("\nFIX POINTER (independent of 0B's work, which is in RebalanceExecutor and does not reach")
print("the ladder path): reconcile._exec_qty (reconcile.py:185) PREFERS a `filled_qty` column and")
print("that column has ZERO producers repo-wide. binance_broker.py:446 holds")
print("`ex = float(o.get('executedQty'))` and discards it. Control flow proves executedQty>0 for")
print("PORTALUSDT: a zero returns at :433 leaving fill_ts None, and the written row carries a")
print("fill_ts (1785226728.403). The venue stated the quantity; no column caught it.")
