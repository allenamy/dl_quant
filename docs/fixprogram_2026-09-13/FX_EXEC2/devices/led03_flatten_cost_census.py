#!/usr/bin/python3
"""LED-03 before-state census (committed BEFORE any run; read-only, no venue, no credentials).
For every protective_flatten batch in a ledger copy, the LED-02 reader cost_buckets.flatten_cost (from --executor-tree) over
that batch's order rows and the day's fills read through pilot_log.read_fills: how many legs are measured / fee_unknown /
unpriced and why. This is the state the EXACT backfill (led03_flatten_fills_backfill_exact.py, lead-run) must move, and the
after-state receipt of that run must be this same census.
Usage: led03_flatten_cost_census.py --root <pilot_log root> --executor-tree T --out OUT.json"""
import argparse, collections, hashlib, json, os, sys, time
ap = argparse.ArgumentParser(allow_abbrev=False)
for k in ("--root", "--executor-tree", "--out"): ap.add_argument(k, required=True)
a = ap.parse_args()
for d in ("live", "ops", "scheduler", "signal"): sys.path.insert(0, os.path.join(a.executor_tree, d))
os.environ.setdefault("LIVE_MODE", "DRY_RUN")
import pilot_log as PL, cost_buckets as CB
days = sorted(d for d in os.listdir(a.root) if d.isdigit() and len(d) == 8)
out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": a.root, "executor_tree": a.executor_tree,
       "cost_buckets_py_sha256": hashlib.sha256(open(os.path.join(a.executor_tree, "live", "cost_buckets.py"), "rb").read()).hexdigest(),
       "batches": {}}
for d in days:
    orders = PL.read_day(a.root, d)["orders"]
    if not any(o.get("order_type") == "protective_flatten" for o in orders): continue
    fills = PL.read_fills(a.root, d)
    for rid, r in CB.flatten_cost_by_batch(orders, fills).items():
        out["batches"][rid] = {"day": d, **{k: r[k] for k in ("n_rows", "n_fills", "n_measured", "n_fee_unknown", "n_unpriced", "n_unknown_fill",
                                                           "notional_usdt", "notional_measured_usdt", "fee_unknown_notional_usdt", "unpriced_notional_usdt",
                                                           "fee_measured_usdt", "bps_measured", "fee_bps_measured", "coverage_measured_notional",
                                                           "measurement_complete", "reasons_not_measured", "fee_source_counts")},
                               "n_fills_rows_of_batch": sum(1 for f in fills if f.get("rebalance_id") == rid)}
json.dump(out, open(a.out, "w"), indent=1)
for rid, b in out["batches"].items():
    print(rid, "rows", b["n_rows"], "measured", b["n_measured"], "fee_unknown", b["n_fee_unknown"], "unpriced", b["n_unpriced"],
          "cov", None if b["coverage_measured_notional"] is None else round(b["coverage_measured_notional"], 4),
          "fee_bps", None if b["fee_bps_measured"] is None else round(b["fee_bps_measured"], 3), "fills_rows", b["n_fills_rows_of_batch"], b["reasons_not_measured"])
