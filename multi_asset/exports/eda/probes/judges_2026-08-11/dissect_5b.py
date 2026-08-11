#!/usr/bin/python3
"""Read-only dissection of the 12:00Z §4-5b trip: the three compared objects.

Copies reconcile.py's arithmetic VERBATIM (same interval rule, same scale, same tol) and
instruments it. Writes nothing.
"""
import json, os, sys, collections

REPO = "/Users/haosiyu/dl_quant_live"
for d in ("live", "ops", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))
import pilot_log as PL
import state_root as SR

root = SR.paths_for("TESTNET")["pilot_log"]
days = PL.available_days(root)
print("root :", root)
print("days :", days)

days_data = [(d, PL.read_day(root, d)) for d in days]

# ---- exactly reconcile.py's _exec build --------------------------------------------------
_exec = []
_prov = []          # parallel provenance
for _day, one in days_data:
    for o in one.get("orders", []):
        f = o.get("filled_notional")
        if f is None or not float(f):
            continue
        t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
        if t is None:
            continue
        _exec.append((float(t), o["symbol"], float(f)))
        _prov.append((float(t), o["symbol"], float(f), o.get("rebalance_id"),
                      o.get("order_type"), o.get("attempt_idx"),
                      "last_fill_ts" if o.get("last_fill_ts") else
                      ("first_fill_ts" if o.get("first_fill_ts") else "anchor_ts")))
_exec.sort(); _prov.sort()

# ---- readbacks ---------------------------------------------------------------------------
rbs = []   # (anchor_ts, t_read, {sym: notional}, day)
for _day, one in days_data:
    by = collections.defaultdict(dict); tt = {}
    for r in one.get("position_readback", []):
        by[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        tt[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
    for a in sorted(by):
        rbs.append((a, tt.get(a, a), by[a], _day))

print("\n=== READBACKS IN ORDER ===")
for a, t, m, d in rbs:
    nz = {s: v for s, v in m.items() if abs(v) > 1e-9}
    print(f"  anchor_ts={a:.3f} read_ts={t:.3f} day={d} n_rows={len(m)} n_nonzero={len(nz)} "
          f"gross={sum(abs(v) for v in m.values()):.2f}")

if len(rbs) < 2:
    sys.exit("need >=2 readbacks")

(a_prev, t_prev, rb_prev, _), (a_cur, t_cur, rb_cur, _) = rbs[-2], rbs[-1]
print(f"\n=== LAST RECONCILIATION: prev anchor {a_prev:.3f} -> cur anchor {a_cur:.3f} ===")
print(f"  interval on execution time: ({t_prev:.3f}, {t_cur:.3f}]")

win = collections.defaultdict(float)
consumed = []
for t, sym, f, rid, ot, ai, key in _prov:
    if t > t_prev and t <= t_cur:
        win[sym] += f
        consumed.append((t, sym, f, rid, ot, ai, key))

print(f"\n=== EXPECTED-SIDE: WHICH EXECUTIONS WERE CONSUMED ===")
print(f"  total in-ledger executions with a nonzero fill : {len(_exec)}")
print(f"  consumed by this interval                      : {len(consumed)}")
print("  by (rebalance_id, order_type):")
for k, v in sorted(collections.Counter((c[3], c[4]) for c in consumed).items()):
    print(f"     {k}: {v}")
print("  time-key used:", dict(collections.Counter(c[6] for c in consumed)))
print("  NOT consumed (outside interval), by (rebalance_id, order_type):")
out_ = [(p[3], p[4]) for p in _prov if not (p[0] > t_prev and p[0] <= t_cur)]
for k, v in sorted(collections.Counter(out_).items()):
    print(f"     {k}: {v}")

# ---- the comparison ----------------------------------------------------------------------
TOL = 0.10
rows = []
for sym, v in rb_cur.items():
    expected = rb_prev.get(sym, 0.0) + win.get(sym, 0.0)
    unexplained = abs(v - expected)
    scale = max(abs(expected), abs(v), 1.0)
    frac = unexplained / scale
    rows.append({"symbol": sym, "prev": rb_prev.get(sym, 0.0), "fills": win.get(sym, 0.0),
                 "expected": expected, "observed": v, "unexplained": unexplained,
                 "frac": frac, "anom": frac > TOL})
anom = [r for r in rows if r["anom"]]
print(f"\n=== VERDICT ===  n_rows={len(rows)}  n_anomalous={len(anom)}  tol={TOL}")
print(f"  prev readback gross = {sum(abs(v) for v in rb_prev.values()):.2f}  "
      f"(nonzero names {sum(1 for v in rb_prev.values() if abs(v) > 1e-9)})")
print(f"  observed gross      = {sum(abs(v) for v in rb_cur.values()):.2f}")
print(f"  consumed fills gross= {sum(abs(v) for v in win.values()):.2f}  (names {len(win)})")
print(f"  expected gross      = {sum(abs(r['expected']) for r in rows):.2f}")

print("\n  top 15 anomalies by |unexplained|:")
for r in sorted(anom, key=lambda r: -r["unexplained"])[:15]:
    print(f"    {r['symbol']:14s} prev={r['prev']:10.2f} fills={r['fills']:10.2f} "
          f"expected={r['expected']:10.2f} observed={r['observed']:10.2f} frac={r['frac']:.4f}")
print("\n  bottom 5 anomalies by |unexplained|:")
for r in sorted(anom, key=lambda r: r["unexplained"])[:5]:
    print(f"    {r['symbol']:14s} prev={r['prev']:10.2f} fills={r['fills']:10.2f} "
          f"expected={r['expected']:10.2f} observed={r['observed']:10.2f} frac={r['frac']:.4f}")

# ---- intersections -------------------------------------------------------------------------
day = days[-1]
orders = PL.read_day(root, day)["orders"]
RID = "A1785067246"
mine = [o for o in orders if o.get("rebalance_id") == RID]
topup_names = {o["symbol"] for o in mine if o["order_type"] == "topup_taker"}
maker_names = {o["symbol"] for o in mine if o["order_type"] == "maker"}
maker_filled = {o["symbol"] for o in mine if o["order_type"] == "maker"
                and o.get("filled_notional") not in (None,) and float(o["filled_notional"])}
topup_filled = {o["symbol"] for o in mine if o["order_type"] == "topup_taker"
                and o.get("filled_notional") not in (None,) and float(o["filled_notional"])}
A = {r["symbol"] for r in anom}
print(f"\n=== SET ALGEBRA (rebalance {RID}) ===")
print(f"  maker rows          : {len(maker_names)} names")
print(f"  topup rows          : {len(topup_names)} names")
print(f"  maker with a fill   : {len(maker_filled)}")
print(f"  topup with a fill   : {len(topup_filled)}")
print(f"  anomalous (5b)      : {len(A)}")
print(f"  anom & topup_names  : {len(A & topup_names)}")
print(f"  anom & topup_filled : {len(A & topup_filled)}")
print(f"  anom & maker_filled : {len(A & maker_filled)}")
print(f"  anom - maker_filled : {len(A - maker_filled)}  {sorted(A - maker_filled)[:10]}")
print(f"  maker_filled - anom : {len(maker_filled - A)}")

# terminal_reason split for maker legs, cross-tabbed against anomaly membership
tr = {o["symbol"]: o.get("terminal_reason") for o in mine if o["order_type"] == "maker"}
ct = collections.Counter((tr.get(s), s in A) for s in maker_names)
print("\n  maker terminal_reason x anomalous:")
for k, v in sorted(ct.items(), key=lambda kv: str(kv[0])):
    print(f"     terminal_reason={k[0]!s:22s} anomalous={k[1]!s:5s} : {v}")

# per-name detail for a couple of anomalies: every order row for that symbol
print("\n=== ROW-LEVEL FOR 3 ANOMALOUS NAMES ===")
for r in sorted(anom, key=lambda r: -r["unexplained"])[:3]:
    s = r["symbol"]
    print(f"  -- {s}: prev={r['prev']:.2f} expected={r['expected']:.2f} observed={r['observed']:.2f}")
    for o in orders:
        if o["symbol"] == s and o.get("rebalance_id") in (RID, "A1785052866"):
            print(f"     rid={o['rebalance_id']} type={o['order_type']} attempt={o.get('attempt_idx')} "
                  f"side={o.get('side')} intended={o.get('intended_notional')} "
                  f"filled={o.get('filled_notional')} lastfill={o.get('last_fill_ts')} "
                  f"term={o.get('terminal_reason')}")

print("\n=== PHANTOM-ROW CHECK (did the scorer's flatten rows enter anything?) ===")
ph = [o for o in orders if str(o.get("rebalance_id", "")).startswith("FLATTEN-")]
print(f"  FLATTEN-* rows in day: {len(ph)}; with a nonzero fill: "
      f"{sum(1 for o in ph if o.get('filled_notional') not in (None,) and float(o['filled_notional']))}")
