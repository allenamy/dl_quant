"""NEW-01 / F-I5 on the REAL batches (READ-ONLY): for every protective-flatten batch in a pilot_log,
report whether it shares an anchor key with its own readback, whether §4-5e judged it, and how far
each row's `submit_ts` sits after that row's own fill.

This is the measurement the suite cannot make: the clone's committed state holds 2026-08-01 only,
and the batch the ruling names (FLATTEN-20260912T124737Z) is on the live tree.

usage: new01_flatten_identity_real_batches.py <code_tree> <pilot_log_root>
"""
import sys, os, json

CODE, ROOT = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import pilot_log as PL, position_break as PB, reconcile as RC       # noqa: E402

days = PL.available_days(ROOT)
dd = [(d, PL.read_day(ROOT, d)) for d in days]
pb = PB.evaluate(dd, residual_by_anchor=RC.reconcile(dd).get("residual_by_anchor"))
judged = {float(r["anchor_ts"]): r for r in pb["per_anchor"]}
out = []
for day, one in dd:
    rb_ts = sorted({float(r["anchor_ts"]) for r in one.get("position_readback", [])})
    batches = {}
    for o in one.get("orders", []):
        if o.get("order_type") != "protective_flatten":
            continue
        batches.setdefault(str(o.get("rebalance_id")), []).append(o)
    for rid, rows in sorted(batches.items()):
        ats = float(rows[0]["anchor_ts"])
        gaps = sorted(float(o["submit_ts"]) - float(o["last_fill_ts"]) for o in rows
                      if o.get("submit_ts") is not None and o.get("last_fill_ts") is not None)
        r = judged.get(ats) or {}
        out.append({
            "day": day, "rebalance_id": rid, "n_rows": len(rows),
            "anchor_ts": ats,
            "shares_key_with_own_readback": ats in rb_ts,
            "nearest_readback_after": next((t for t in rb_ts if t > ats), None),
            "n_distinct_submit_ts": len({o.get("submit_ts") for o in rows}),
            "submit_ts_source": sorted({str(o.get("submit_ts_source")) for o in rows}),
            "flatten_scope": sorted({str(o.get("flatten_scope")) for o in rows}),
            "n_rows_submit_after_own_fill": sum(1 for g in gaps if g > 0),
            "submit_minus_own_fill_s": ({"min": gaps[0], "median": gaps[len(gaps) // 2],
                                         "max": gaps[-1]} if gaps else None),
            "pb_judged": r.get("judged"), "pb_state": r.get("state"),
            "pb_anchor_kind": r.get("anchor_kind")})
print(json.dumps({"root": ROOT, "n_batches": len(out),
                  "n_sharing_key": sum(1 for b in out if b["shares_key_with_own_readback"]),
                  "n_judged": sum(1 for b in out if b["pb_judged"]),
                  "batches": out}, indent=1, default=str))
