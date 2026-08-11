#!/usr/bin/env python3
"""0C audit Q1/Q2 — is there REAL position drift at anchor 1785225684.348149 (2026-07-28T08:01:24Z)?

WHAT THE LEAD DID: compared `venue_position_notional` and found -2.366 / -4.903 USDT residuals,
inside the 5 USDT dust floor. That caliber carries a price term (notional = qty x mark), which is
exactly what B30 removed from the guard.

WHAT THIS DOES INSTEAD: compares CONTRACTS, three ways, and states for each which input is
independent of the lead's assumption (that the missing `avg_fill_px` is the only defect).

  CALIBER A  q2 - (q1 + sum dq_from_FILLS)
             q1,q2   = position_readback.venue_position_qty   (VENUE-reported contracts)
             dq      = sum over fills.jsonl of +-(fill_notional / fill_px)
                       fill_px = venue userTrades `price`; fill_notional = venue `quoteQty`
             ==> BOTH SIDES ARE VENUE DATA. `avg_fill_px` (the field the lead says is broken) is
                 NEVER READ. This caliber cannot measure the lead's assumption because it does
                 not contain it. This is the decisive number.

  CALIBER B  the production caliber (reconcile._exec_qty), with the unquantifiable legs filled in
             from fills. Shown to locate where A and production diverge.

  CALIBER C  price the unknown legs at the READBACK MARK (n2/q2) instead of at a fill price.
             Used only to BOUND the error of any price-based reconstruction.

Read-only. Writes nothing into ~/dl_quant_live.
"""
import json, os, sys, datetime
from collections import defaultdict

ROOT = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
DAYS = sorted(d for d in os.listdir(ROOT) if len(d) == 8 and d.isdigit())
ATS = 1785225684.348149


def rd(day, table):
    p = os.path.join(ROOT, day, f"{table}.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for ln in open(p):
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    return out


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


ORDERS = [o for d in DAYS for o in rd(d, "orders")]
FILLS = [f for d in DAYS for f in rd(d, "fills")]
RB = [r for d in DAYS for r in rd(d, "position_readback")]

# ── anchors that carry a readback, in time order (this is what reconcile walks) ────────────────
rb_by_anchor = defaultdict(dict)
rb_time = {}
for r in RB:
    rb_by_anchor[r["anchor_ts"]][r["symbol"]] = r
    rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
anchors = sorted(rb_by_anchor)
i = anchors.index(ATS)
prev_ats = anchors[i - 1]
t_lo, t_hi = rb_time[prev_ats], rb_time[ATS]

print("=" * 100)
print(f"anchor under audit : {ATS!r}  {iso(ATS)}   read_ts={t_hi!r} {iso(t_hi)}")
print(f"previous readback  : {prev_ats!r}  {iso(prev_ats)}   read_ts={t_lo!r} {iso(t_lo)}")
print(f"interval           : ({iso(t_lo)}, {iso(t_hi)}]   = {t_hi - t_lo:.1f}s")
print("=" * 100)

cur, prv = rb_by_anchor[ATS], rb_by_anchor[prev_ats]

# ── CALIBER A: contracts from the venue on both sides ─────────────────────────────────────────
dq_fills = defaultdict(float)
n_fill_rows = defaultdict(int)
fill_backfill_ts = defaultdict(set)
bad_fill = []
for f in FILLS:
    t = f.get("fill_ts")
    if t is None or not (t_lo < float(t) <= t_hi):
        continue
    px, nt, sd = f.get("fill_px"), f.get("fill_notional"), (f.get("side") or "").lower()
    if not px or nt is None or sd not in ("buy", "sell"):
        bad_fill.append(f)
        continue
    dq_fills[f["symbol"]] += (1 if sd == "buy" else -1) * float(nt) / float(px)
    n_fill_rows[f["symbol"]] += 1
    if f.get("backfilled_utc"):
        fill_backfill_ts[f["symbol"]].add(f["backfilled_utc"])

# ── legs the production caliber could not size (the §4-5b anomaly) ─────────────────────────────
unknown_legs = defaultdict(list)
known_dq_orders = defaultdict(float)
for o in ORDERS:
    t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
    if t is None or not (t_lo < float(t) <= t_hi):
        continue
    fn = o.get("filled_notional")
    if fn is None:
        if o.get("submit_ts") is None:
            continue                                   # structural zero
        unknown_legs[o["symbol"]].append(o)
        continue
    fn = float(fn)
    if fn == 0.0:
        continue
    px = o.get("avg_fill_px")
    if px:
        known_dq_orders[o["symbol"]] += fn / float(px)
    else:
        unknown_legs[o["symbol"]].append(o)

syms = sorted(set(cur) | set(prv) | set(dq_fills) | set(unknown_legs))
rows = []
for s in syms:
    c, p = cur.get(s), prv.get(s)
    q2 = None if c is None else c.get("venue_position_qty")
    q1 = 0.0 if p is None else p.get("venue_position_qty")
    n2 = 0.0 if c is None else float(c.get("venue_position_notional") or 0.0)
    if q2 is None or q1 is None:
        rows.append({"sym": s, "skip": "no venue_position_qty"})
        continue
    q1, q2 = float(q1), float(q2)
    resid_A = q2 - (q1 + dq_fills.get(s, 0.0))
    mark = abs(n2 / q2) if q2 else None
    # CALIBER C: reconstruct the unknown legs at the readback mark instead of at a fill price
    dq_C = known_dq_orders.get(s, 0.0)
    for o in unknown_legs.get(s, []):
        fn = o.get("filled_notional")
        m = mark or o.get("mid_at_anchor") or o.get("mid_at_submit")
        if fn is not None and m:
            dq_C += float(fn) / float(m)
    resid_C = q2 - (q1 + dq_C)
    rows.append({"sym": s, "q1": q1, "q2": q2, "dq_fills": dq_fills.get(s, 0.0),
                 "dq_orders_known": known_dq_orders.get(s, 0.0),
                 "n_unknown_legs": len(unknown_legs.get(s, [])),
                 "n_fill_rows": n_fill_rows.get(s, 0),
                 "resid_A": resid_A, "resid_C": resid_C, "mark": mark,
                 "resid_A_usdt": None if mark is None else abs(resid_A) * mark,
                 "resid_C_usdt": None if mark is None else abs(resid_C) * mark,
                 "floor": 50.0 if s == "BTCUSDT" else (20.0 if s in
                          ("ETHUSDT", "BCHUSDT", "LTCUSDT", "ETCUSDT", "LINKUSDT") else 5.0)})

flagged = [r for r in rows if r.get("skip")]
ok = [r for r in rows if not r.get("skip")]

print("\n### Q1 — the two names §4-5b named, in CONTRACTS")
print(f"{'symbol':<12}{'q1(venue)':>16}{'q2(venue)':>16}{'dq_fills':>16}{'residual_A':>16}"
      f"{'resid_A USDT':>14}{'#unk':>6}{'#fills':>8}")
for r in ok:
    if r["sym"] in ("SAGAUSDT", "SKLUSDT"):
        print(f"{r['sym']:<12}{r['q1']:>16.4f}{r['q2']:>16.4f}{r['dq_fills']:>16.6f}"
              f"{r['resid_A']:>16.8f}{(r['resid_A_usdt'] or 0):>14.6f}"
              f"{r['n_unknown_legs']:>6}{r['n_fill_rows']:>8}")
        print(f"{'':14}CALIBER C (unknown legs priced at readback mark {r['mark']:.8g}): "
              f"residual_C = {r['resid_C']:.8f} contracts = {r['resid_C_usdt']:.6f} USDT")

print("\n### Q2 — EVERY name at this anchor, ranked by |residual_A| in USDT")
print(f"{'symbol':<14}{'residual_A(qty)':>18}{'USDT':>12}{'floor':>8}{'over?':>7}"
      f"{'#unk':>6}{'#fills':>8}{'q2':>16}")
worst = sorted(ok, key=lambda r: -(r["resid_A_usdt"] or 0.0))
n_over = 0
for r in worst[:20]:
    over = (r["resid_A_usdt"] or 0) > r["floor"]
    n_over += bool(over)
    print(f"{r['sym']:<14}{r['resid_A']:>18.8f}{(r['resid_A_usdt'] or 0):>12.4f}"
          f"{r['floor']:>8.0f}{('YES' if over else '.'):>7}"
          f"{r['n_unknown_legs']:>6}{r['n_fill_rows']:>8}{r['q2']:>16.4f}")
n_over_all = sum(1 for r in ok if (r["resid_A_usdt"] or 0) > r["floor"])
print(f"\nnames compared          : {len(ok)}")
print(f"names NOT comparable    : {len(flagged)}  {[r['sym'] for r in flagged][:10]}")
print(f"names over their floor  : {n_over_all}")
print(f"max |residual_A| USDT   : {max((r['resid_A_usdt'] or 0) for r in ok):.6f}")
print(f"sum |residual_A| USDT   : {sum((r['resid_A_usdt'] or 0) for r in ok):.6f}")
print(f"names with unknown legs : {sorted(unknown_legs)}")
print(f"fill rows with unusable px/notional in window: {len(bad_fill)}")

# ── does any unknown-size name ALSO carry a real residual? (the [D2] classification question) ──
print("\n### Q2b — names that are BOTH unknown-size AND carry a residual")
for s in sorted(unknown_legs):
    r = next((x for x in ok if x["sym"] == s), None)
    if r is None:
        print(f"  {s}: no comparable readback pair")
        continue
    print(f"  {s}: residual_A={r['resid_A']:.8f} contracts = {r['resid_A_usdt']:.6f} USDT "
          f"(floor {r['floor']:.0f}) -> {'REAL DRIFT' if r['resid_A_usdt'] > r['floor'] else 'below floor'}")
    for o in unknown_legs[s]:
        print(f"      leg: type={o.get('order_type')} reason={o.get('terminal_reason')!r} "
              f"filled_notional={o.get('filled_notional')} avg_fill_px={o.get('avg_fill_px')!r} "
              f"submit_ts={o.get('submit_ts')} last_fill_ts={o.get('last_fill_ts')} "
              f"rebalance_id={o.get('rebalance_id')}")
    print(f"      fills backfilled_utc for this symbol in window: {sorted(fill_backfill_ts.get(s, []))}")

# ── independence bound: how much could a WRONG price move the reconstruction? ──────────────────
print("\n### Q1b — error bound on any PRICE-BASED reconstruction (caliber C vs A)")
for s in sorted(unknown_legs):
    r = next((x for x in ok if x["sym"] == s), None)
    if r is None:
        continue
    print(f"  {s}: |resid_C - resid_A| = {abs(r['resid_C'] - r['resid_A']):.8f} contracts "
          f"= {abs(r['resid_C'] - r['resid_A']) * (r['mark'] or 0):.6f} USDT")
