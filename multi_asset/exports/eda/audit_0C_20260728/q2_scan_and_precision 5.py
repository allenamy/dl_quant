#!/usr/bin/env python3
"""0C audit Q2 — full-window sweep + the blind spots the per-anchor list cannot show.

Four things the lead's n=2 does NOT answer, checked here:
  (1) PRECISION: is `residual_A == 0` a real zero or a printed one?
  (2) DROPOUT:   reconcile iterates `cur.items()` only. A symbol present at T1 and ABSENT from the
                 T2 readback is never compared at all — it is not an anomaly, not unreconcilable,
                 it simply is not in any list. That is invisible from the eval output.
  (3) HISTORY:   the trigger says "4 in this window's history". Which anchors, which names, which
                 kinds — and is any of them a `quantity_residual` (real drift) rather than an
                 `execution_of_unknown_size`?
  (4) SOURCE:    is `venue_position_qty` actually venue-reported, or is it our own book echoed
                 back? If it were ours, caliber A would be our books against our books.
Read-only.
"""
import json, os, datetime, subprocess
from collections import defaultdict, Counter

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
    return datetime.datetime.fromtimestamp(float(t), datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


RB = [(d, r) for d in DAYS for r in rd(d, "position_readback")]
FILLS = [f for d in DAYS for f in rd(d, "fills")]

rb_by_anchor = defaultdict(dict)
rb_time, rb_day = {}, {}
for d, r in RB:
    rb_by_anchor[r["anchor_ts"]][r["symbol"]] = r
    rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
    rb_day[r["anchor_ts"]] = d
anchors = sorted(rb_by_anchor)

print("=" * 100)
print("(4) PROVENANCE of venue_position_qty — `source` values, all readbacks in the window")
print("=" * 100)
print(Counter(r.get("source") for _, r in RB))
print("\ngrep of the producer:")
print(subprocess.run(
    ["grep", "-rn", "venue_position_qty", os.path.expanduser("~/dl_quant_live/live"),
     os.path.expanduser("~/dl_quant_live/ops"), os.path.expanduser("~/dl_quant_live/scheduler")],
    capture_output=True, text=True).stdout[:3000])

print("=" * 100)
print("(1)+(2) EVERY consecutive readback pair in the window: precision, dropouts, residuals")
print("=" * 100)
print(f"{'anchor(T2)':<22}{'day':<10}{'nT1':>5}{'nT2':>5}{'dropped':>9}{'appeared':>10}"
      f"{'maxResid(qty)':>16}{'maxResid(USDT)':>16}{'#overFloor':>12}")

FLOOR = lambda s: 50.0 if s == "BTCUSDT" else (20.0 if s in
        ("ETHUSDT", "BCHUSDT", "LTCUSDT", "ETCUSDT", "LINKUSDT") else 5.0)

dropout_detail = []
for i in range(1, len(anchors)):
    a1, a2 = anchors[i - 1], anchors[i]
    t_lo, t_hi = rb_time[a1], rb_time[a2]
    prv, cur = rb_by_anchor[a1], rb_by_anchor[a2]
    dq = defaultdict(float)
    for f in FILLS:
        t = f.get("fill_ts")
        if t is None or not (t_lo < float(t) <= t_hi):
            continue
        px, nt, sd = f.get("fill_px"), f.get("fill_notional"), (f.get("side") or "").lower()
        if not px or nt is None or sd not in ("buy", "sell"):
            continue
        dq[f["symbol"]] += (1 if sd == "buy" else -1) * float(nt) / float(px)
    dropped = sorted(set(prv) - set(cur))
    appeared = sorted(set(cur) - set(prv))
    mq = mu = 0.0
    n_over = 0
    for s, c in cur.items():
        q2 = c.get("venue_position_qty")
        p = prv.get(s)
        q1 = 0.0 if p is None else p.get("venue_position_qty")
        if q2 is None or q1 is None:
            continue
        r = float(q2) - (float(q1) + dq.get(s, 0.0))
        n2 = float(c.get("venue_position_notional") or 0.0)
        mk = abs(n2 / float(q2)) if float(q2) else 0.0
        u = abs(r) * mk
        mq, mu = max(mq, abs(r)), max(mu, u)
        n_over += (u > FLOOR(s))
    # a DROPPED name still holds whatever it held at T1 plus whatever traded: quantify it
    for s in dropped:
        q1 = float(prv[s].get("venue_position_qty") or 0.0)
        n1 = float(prv[s].get("venue_position_notional") or 0.0)
        mk = abs(n1 / q1) if q1 else 0.0
        dropout_detail.append({"a2": a2, "sym": s, "q1": q1, "dq": dq.get(s, 0.0),
                               "implied_qty_if_untraded": q1 + dq.get(s, 0.0),
                               "usdt": abs(q1 + dq.get(s, 0.0)) * mk})
    print(f"{a2:<22.6f}{rb_day[a2]:<10}{len(prv):>5}{len(cur):>5}{len(dropped):>9}{len(appeared):>10}"
          f"{mq:>16.3e}{mu:>16.3e}{n_over:>12}")

print("\nDROPOUT DETAIL (names in T1's readback and absent from T2's — never compared by reconcile):")
if not dropout_detail:
    print("  none in the whole window.")
for d in dropout_detail[:40]:
    print(f"  T2={iso(d['a2'])} {d['sym']:<14} q1={d['q1']:>14.4f} dq={d['dq']:>12.4f} "
          f"implied_remaining={d['implied_qty_if_untraded']:>14.4f}  ~{d['usdt']:.2f} USDT")

print("\n" + "=" * 100)
print("(3) THE WINDOW'S HISTORY — run the PRODUCTION reconciler and enumerate all anomalies")
print("=" * 100)
import sys
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import pilot_log as PL, reconcile as RC
rec = RC.reconcile([(d, PL.read_day(ROOT, d)) for d in DAYS])
print(f"n_reconciled_anchors      : {rec['n_reconciled_anchors']}")
print(f"last_reconciled_ats       : {rec['last_reconciled_ats']!r}  ({iso(rec['last_reconciled_ats'])})")
print(f"n_anomalies (window)      : {len(rec['anomalies'])}   by kind: {rec['n_anomalies_by_kind']}")
print(f"n_unreconcilable (window) : {rec['n_unreconcilable']} by kind: {rec['n_unreconcilable_by_kind']}")
print(f"latest anomalies          : {len(rec['latest'])}")
print(f"latest_unreconcilable     : {len(rec['latest_unreconcilable'])}")
print("\nALL anomalies in the window:")
for a in rec["anomalies"]:
    print(f"  {iso(a['anchor_ts'])} {a['symbol']:<14} kind={a['kind']:<26} "
          f"resid_qty={a.get('residual_qty')} resid_usdt={a.get('residual_usdt')} "
          f"tr={a.get('terminal_reason')!r}")
print("\nunreconcilable, grouped by anchor:")
c = Counter(iso(u["anchor_ts"]) for u in rec["unreconcilable"])
for k, v in sorted(c.items()):
    print(f"  {k}: {v}")
