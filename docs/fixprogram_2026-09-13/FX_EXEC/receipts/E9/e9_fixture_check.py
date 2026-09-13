import json, os, sys, tempfile, shutil
TREE = sys.argv[1]
FX = "/Users/haosiyu/cc_tmp/fx_exec/live/tests_fixtures/e9_constant_columns"
sys.path.insert(0, os.path.join(TREE, "ops"))
import assert_anchor_artifacts as AA  # noqa: E402
def tree(day_rows, hist_rows=None):
    t = tempfile.mkdtemp(prefix="e9fx_")
    if hist_rows:
        os.makedirs(os.path.join(t, "20260912")); open(os.path.join(t, "20260912", "orders.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in hist_rows))
    os.makedirs(os.path.join(t, "20260913")); open(os.path.join(t, "20260913", "orders.jsonl"), "w").write("".join(json.dumps(r) + "\n" for r in day_rows))
    return t
rd = lambda n: [json.loads(l) for l in open(os.path.join(FX, n)) if l.strip()]
for label, rows, hist, rid in (("12Z subset", rd("orders_20260913_to_12Z_subset.jsonl"), None, "A1789302239"),
                               ("00Z halted + history", rd("orders_20260913_00Z_halted.jsonl"), rd("history_20260912_subset.jsonl"), "A1789259039")):
    t = tree(rows, hist)
    res = AA.check_artifacts(rid, None, anchor_ts=None, root=t, day="20260913", mode="LIVE", rebalanced=True)
    a = [x for x in res["assertions"] if x["assert"] == "no orders column is constant for want of a producer"][0]
    print(label, "ok=", a["ok"], "|", a["detail"][:600])
    shutil.rmtree(t)
