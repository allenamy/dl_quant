"""B13 census (READ-ONLY, on a COPY of live state).

For every anchor key in the pilot_log, cross-tab three independent facts:
  · is there an `anchors` row?           (written only when a rebalance was ATTEMPTED — the repo's
                                          property-based discriminant for "scheduled anchor",
                                          live/rebalance_id.py:26-30)
  · how many order rows carry that key?
  · how many position_readback rows carry that key?

The B13 shape is "`anchors` row present, readback absent". Everything else is reported so the
denominator is visible rather than asserted.

usage: probe_b13_census.py <code_tree> <pilot_log_root>
"""
import sys, os, json

CODE, ROOT = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import pilot_log as PL                                              # noqa: E402

days = PL.available_days(ROOT)
rows = []
for day in days:
    one = PL.read_day(ROOT, day)
    a_ts = {float(a["anchor_ts"]) for a in one.get("anchors", []) if a.get("anchor_ts") is not None}
    o_by = {}
    for o in one.get("orders", []):
        t = float(o["anchor_ts"])
        e = o_by.setdefault(t, {"n": 0, "n_sub": 0, "rids": set()})
        e["n"] += 1
        if o.get("submit_ts") is not None:
            e["n_sub"] += 1
        e["rids"].add(str(o.get("rebalance_id")))
    rb = {}
    for r in one.get("position_readback", []):
        t = float(r["anchor_ts"])
        rb[t] = rb.get(t, 0) + 1
    for t in sorted(a_ts | set(o_by) | set(rb)):
        rows.append({"day": day, "anchor_ts": t,
                     "anchors_row": t in a_ts,
                     "n_orders": o_by.get(t, {}).get("n", 0),
                     "n_submitted": o_by.get(t, {}).get("n_sub", 0),
                     "rids": sorted(o_by.get(t, {}).get("rids", set())),
                     "n_readback": rb.get(t, 0)})

def _sel(pred):
    return [r for r in rows if pred(r)]

both   = _sel(lambda r: r["anchors_row"] and r["n_readback"] > 0)
b13    = _sel(lambda r: r["anchors_row"] and r["n_readback"] == 0)      # ← the B13 shape
rb_only= _sel(lambda r: (not r["anchors_row"]) and r["n_readback"] > 0)
ord_only=_sel(lambda r: (not r["anchors_row"]) and r["n_readback"] == 0)
print(json.dumps({
    "root": ROOT, "n_days": len(days), "day_range": [days[0], days[-1]] if days else None,
    "n_anchor_keys": len(rows),
    "counts": {"anchors_row_and_readback": len(both),
               "anchors_row_no_readback_B13_SHAPE": len(b13),
               "readback_no_anchors_row": len(rb_only),
               "orders_only": len(ord_only)},
    "anchors_row_no_readback": b13,
    "readback_no_anchors_row": rb_only,
    "orders_only": ord_only,
}, indent=1, default=str))
