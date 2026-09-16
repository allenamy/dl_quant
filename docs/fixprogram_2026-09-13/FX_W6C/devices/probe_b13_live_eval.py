"""B13 (READ-ONLY): what anchor do §4-5b / §4-5e actually judge on a real tree, and is it the
newest scheduled anchor? Pure: calls reconcile() and position_break.evaluate() only — no state is
written, no venue is contacted.

usage: probe_b13_live_eval.py <code_tree> <pilot_log_root>
"""
import sys, os, json, time

CODE, ROOT = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import pilot_log as PL, reconcile as RC, position_break as PB      # noqa: E402

days = PL.available_days(ROOT)
dd = [(d, PL.read_day(ROOT, d)) for d in days]
newest_anchors_row = max((float(a["anchor_ts"]) for _d, one in dd
                          for a in one.get("anchors", []) if a.get("anchor_ts") is not None),
                         default=None)
newest_order = max((float(o["anchor_ts"]) for _d, one in dd for o in one.get("orders", [])), default=None)
newest_rb = max((float(r["anchor_ts"]) for _d, one in dd for r in one.get("position_readback", [])), default=None)
t0 = time.time(); rec = RC.reconcile(dd); t1 = time.time()
pb = PB.evaluate(dd, residual_by_anchor=rec.get("residual_by_anchor")); t2 = time.time()
print(json.dumps({
    "root": ROOT, "n_days": len(days),
    "newest_anchors_row_ats": newest_anchors_row,
    "newest_order_ats": newest_order,
    "newest_readback_ats": newest_rb,
    "reconcile.last_reconciled_ats": rec["last_reconciled_ats"],
    "reconcile.n_reconciled_anchors": rec["n_reconciled_anchors"],
    "reconcile.n_latest_anomalies": len(rec["latest"]),
    "position_break.latest_anchor_ts": pb["latest_anchor_ts"],
    "position_break.state": pb["state"], "position_break.blind": pb["blind"],
    "position_break.n_anchors": pb["n_anchors"], "position_break.n_judged": pb["n_judged"],
    "position_break.n_not_judged": pb["n_not_judged"],
    "judged_is_newest_anchors_row": (rec["last_reconciled_ats"] is not None
                                     and newest_anchors_row is not None
                                     and rec["last_reconciled_ats"] >= newest_anchors_row),
    "secs": {"reconcile": round(t1 - t0, 1), "position_break": round(t2 - t1, 1)},
}, indent=1, default=str))
