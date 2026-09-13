#!/usr/bin/env python3
"""t7_pull_binance_format_breakdown.py — splits the C6 FORMAT_FAIL and PARTIAL_MONTH flags into their causes from the Binance manifest (no network):
no_header (older archive format; the loader handles it), not_ms, not_contiguous (hours missing inside the month), close_time_bad;
partial months at the symbol's first/last stored month (listing boundary) vs internal. Output <root>/checks/BINANCE_FORMAT_BREAKDOWN.json."""
import os, json, collections, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
last = {}
for l in open(ROOT + "/manifest/pages_binance.jsonl"):
    r = json.loads(l)
    if "symbol" in r: last[(r["symbol"], r["month"])] = r
ok = [r for r in last.values() if r["status"] == "OK"]
sub = collections.Counter(); byyear = collections.defaultdict(collections.Counter)
for r in ok:
    for k, bad in (("no_header", not r["header"]), ("not_ms", not r["ms_units"]), ("not_contiguous", not r["contiguous"]), ("close_time_bad", not r["close_time_ok"])):
        if bad: sub[k] += 1; byyear[k][r["month"][:4]] += 1
bysym = collections.defaultdict(list)
for r in ok: bysym[r["symbol"]].append(r["month"])
part = collections.Counter()
for r in ok:
    if r["n_rows"] != r["expected_rows_full_month"]:
        ms = sorted(bysym[r["symbol"]]); part["boundary_month" if r["month"] in (ms[0], ms[-1]) else "internal_month"] += 1
format_fail_any = sum(1 for r in ok if not (r["header"] and r["ms_units"] and r["contiguous"] and r["close_time_ok"]))
out = {"device": os.path.basename(__file__), "n_ok_zips": len(ok), "format_fail_any": format_fail_any, "sub_check_failures": dict(sub),
       "sub_check_failures_by_year": {k: dict(v) for k, v in byyear.items()}, "partial_months": dict(part),
       "both_no_header_and_not_contiguous": sum(1 for r in ok if not r["header"] and not r["contiguous"])}
json.dump(out, open(ROOT + "/checks/BINANCE_FORMAT_BREAKDOWN.json", "w"), indent=1); print(json.dumps(out, indent=1))
