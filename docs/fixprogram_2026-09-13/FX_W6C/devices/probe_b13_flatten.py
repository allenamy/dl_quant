"""B13 / NEW-01 (READ-ONLY): every FLATTEN order batch in the record, against the readback that
follows it. Prints the two anchor_ts values and their delta, and how far the written
submit_ts/anchor_ts sits after the batch's last fill.

usage: probe_b13_flatten.py <code_tree> <pilot_log_root>
"""
import sys, os, json

CODE, ROOT = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import pilot_log as PL                                              # noqa: E402

out = []
for day in PL.available_days(ROOT):
    one = PL.read_day(ROOT, day)
    batches = {}
    for o in one.get("orders", []):
        rid = str(o.get("rebalance_id") or "")
        if not rid.startswith("FLATTEN"):
            continue                       # instance names are never a filter elsewhere; here the
        batches.setdefault(rid, []).append(o)   # question IS "which rows did the ladder write"
    rb_ts = sorted({float(r["anchor_ts"]) for r in one.get("position_readback", [])})
    rb_n = {}
    for r in one.get("position_readback", []):
        rb_n[float(r["anchor_ts"])] = rb_n.get(float(r["anchor_ts"]), 0) + 1
    for rid, rows in sorted(batches.items()):
        ats = float(rows[0]["anchor_ts"])
        after = [t for t in rb_ts if t >= ats]
        nearest = min(after, key=lambda t: t - ats) if after else None
        fills = sorted(float(o["last_fill_ts"]) for o in rows if o.get("last_fill_ts"))
        # ONE write moment per batch: the gap to each ROW's own fill is what a reader of
        # submit_ts sees, so report the spread, not only its smallest member.
        gaps = sorted(ats - f for f in fills)
        out.append({"day": day, "rebalance_id": rid, "n_orders": len(rows),
                    "n_distinct_order_anchor_ts": len({float(o["anchor_ts"]) for o in rows}),
                    "n_distinct_order_submit_ts": len({o.get("submit_ts") for o in rows}),
                    "order_anchor_ts": ats,
                    "order_submit_ts": rows[0].get("submit_ts"),
                    "readback_anchor_ts": nearest,
                    "n_readback_rows": rb_n.get(nearest) if nearest else None,
                    "delta_readback_minus_orders_s": (None if nearest is None else nearest - ats),
                    "n_rows_with_fill": len(fills),
                    "write_minus_own_fill_s": (None if not gaps else
                                               {"min": gaps[0], "median": gaps[len(gaps) // 2],
                                                "max": gaps[-1]}),
                    "same_key": bool(nearest is not None and nearest == ats)})
print(json.dumps({"root": ROOT, "n_flatten_batches": len(out),
                  "n_sharing_one_key_with_their_readback": sum(1 for r in out if r["same_key"]),
                  "batches": out}, indent=1, default=str))
