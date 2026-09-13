#!/usr/bin/python3
"""LED-01 req. 4 positive control (read-only): run the fills write contract (pilot_log.fills_contract_violations, from the
executor tree given as argv[1]) over EVERY day of a guarded ledger copy (argv[2] = pilot_log root). Expect 0 violations;
any violation means the contract is wrong, not history. Also counts (symbol, trade_id) keys present in more than one
day file, rows per key, and chain shapes. Writes nothing except the receipt JSON (argv[3]).
Usage: /usr/bin/python3 led01_contract_positive_control.py <executor_tree> <pilot_log_root> <receipt.json>"""
import collections, hashlib, json, os, sys, time
TREE, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(TREE, "live"))
import pilot_log as PL
pl_sha = hashlib.sha256(open(os.path.join(TREE, "live", "pilot_log.py"), "rb").read()).hexdigest()
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tree": TREE, "pilot_log_py_sha256": pl_sha,
       "root": ROOT, "days": {}, "violations": [], "n_rows": 0, "n_keys": 0}
day_of_key = collections.defaultdict(set)
shapes = collections.Counter()
for day in PL.available_days(ROOT):
    p = os.path.join(ROOT, day, "fills.jsonl")
    if not os.path.exists(p):
        continue
    raw = open(p, "rb").read()
    assert len(raw) == os.stat(p).st_size
    rows = PL._read_jsonl(p)
    v = PL.fills_contract_violations(rows)
    per = collections.defaultdict(list)
    for r in rows:
        k = PL.fill_key(r)
        if k is not None:
            per[k].append(r)
            day_of_key[k].add(day)
    for k, rs in per.items():
        shapes[tuple("S" if r.get("supersedes_trade_id") is not None else "O" for r in rs)] += 1
    res["days"][day] = {"fills_sha256": hashlib.sha256(raw).hexdigest(), "n_rows": len(rows), "n_keys": len(per),
                        "n_no_trade_id": sum(1 for r in rows if PL.fill_key(r) is None), "n_violations": len(v)}
    res["violations"] += [dict(x, day=day) for x in v]
    res["n_rows"] += len(rows); res["n_keys"] += len(per)
res["n_violations"] = len(res["violations"])
res["violations_by_kind"] = dict(collections.Counter(x["kind"] for x in res["violations"]))
res["keys_in_more_than_one_day"] = sum(1 for k, d in day_of_key.items() if len(d) > 1)
res["chain_shapes"] = {"".join(k): n for k, n in shapes.most_common()}
json.dump(res, open(OUT, "w"), indent=1, default=str)
print("LED01_POSITIVE_CONTROL days", len(res["days"]), "rows", res["n_rows"], "keys", res["n_keys"], "violations",
      res["n_violations"], res["violations_by_kind"], "cross_day_keys", res["keys_in_more_than_one_day"],
      "shapes", res["chain_shapes"], "pilot_log.py", pl_sha[:16])
