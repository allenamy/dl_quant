"""X-A3 rho_pre recomputed from the LIVE ledger, read-only.
Reads ONLY: rebalance_id, order_type, attempt_idx, symbol, prev_w, terminal_reason (orders.jsonl)
and anchors.jsonl keys needed to count plans. No price / fill / markout / arm field is read.
Definition (AMENDMENT_1 -> DRAFT §1 X-A3): rho_pre(a) = sum over distinct symbols of |prev_w| taken
from the FIRST orders.jsonl row with rebalance_id == a, order_type == 'maker', attempt_idx == 1.
"""
import glob, json, math, os, sys
ROOT = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
first = {}      # rid -> {sym: prev_w of first att-1 maker row}
order = {}      # rid -> first seen anchor date dir
for d in sorted(glob.glob(os.path.join(ROOT, "2026*"))):
    fn = os.path.join(d, "orders.jsonl")
    if not os.path.exists(fn):
        continue
    for line in open(fn, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("order_type") != "maker" or r.get("attempt_idx") != 1:
            continue
        rid = r.get("rebalance_id")
        if not rid or not str(rid).startswith("A"):
            continue
        m = first.setdefault(rid, {})
        order.setdefault(rid, os.path.basename(d))
        if r.get("symbol") not in m:
            m[r.get("symbol")] = r.get("prev_w")
out = []
for rid in sorted(first, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
    m = first[rid]
    bad = [s for s, w in m.items() if not isinstance(w, (int, float)) or not math.isfinite(w)]
    rho = None if bad else sum(abs(w) for w in m.values())
    import datetime as _dt
    try:
        ts = _dt.datetime.utcfromtimestamp(int(rid[1:])).strftime("%Y-%m-%dT%H:%MZ")
    except Exception:
        ts = "?"
    out.append({"rebalance_id": rid, "utc": ts, "n_symbols": len(m), "rho_pre": rho, "n_unreadable_prev_w": len(bad)})
json.dump(out, open(sys.argv[1], "w"), indent=0)
for o in out:
    if o["utc"] >= "2026-08-28":
        flag = "  <-- REBUILD (<0.50)" if (o["rho_pre"] is not None and o["rho_pre"] < 0.5) else ""
        print(f"{o['utc']}  {o['rebalance_id']}  n={o['n_symbols']:4d}  rho_pre={o['rho_pre'] if o['rho_pre'] is None else round(o['rho_pre'],4)}  unread={o['n_unreadable_prev_w']}{flag}")
