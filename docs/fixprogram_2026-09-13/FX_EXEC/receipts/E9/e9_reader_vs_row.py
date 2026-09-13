"""E9 premise: on every real row carrying a request ledger (09-12 and 09-13 through 12Z), the executor's reader ledger_row_columns
reproduces the persisted ledger columns exactly — so 'the reader implies a value' is the writer's own trigger."""
import json, glob, sys, os, collections
sys.path.insert(0, "/Users/haosiyu/cc_tmp/fx_exec/live")
import binance_executor as BE
cols = ["filled_known_notional", "filled_known_qty", "filled_unknown_qty", "filled_unknown_residual", "filled_qty"]
files = ["/Users/haosiyu/cc_tmp/fx_exec_census/pilot_log/20260912/orders.jsonl", "/Users/haosiyu/cc_tmp/fx_exec_census/day20260913_full/orders.jsonl"]
n = 0; mism = collections.Counter(); trig = collections.Counter()
for f in files:
    for l in open(f):
        r = json.loads(l); led = r.get("request_ledger")
        if not isinstance(led, list) or not led: continue
        n += 1; c = BE.ledger_row_columns(led)
        for k in cols:
            if c.get(k) is not None: trig[(f.split("/")[-2], k)] += 1
            a, b = c.get(k), r.get(k)
            if not ((a == b) or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a))))): mism[k] += 1
print("rows with ledgers:", n, "reader-vs-row mismatches:", dict(mism)); print("rows where the reader implies a value:", dict(trig))
