"""E9 reproduction: run a tree's ops/assert_anchor_artifacts.check_artifacts on the REAL 09-13 day as each LIVE anchor saw it
(orders/anchors/readback/nav/fills rows with anchor_ts <= that anchor; the prior days' orders for the event history).
usage: e9_repro.py <tree> [history_days...]"""
import json, os, sys, tempfile, shutil
TREE = sys.argv[1]
HIST = sys.argv[2:] or ["20260912"]
CEN = "/Users/haosiyu/cc_tmp/fx_exec_census"
DAY = os.path.join(CEN, "day20260913_full")
sys.path.insert(0, os.path.join(TREE, "ops"))
os.environ["LIVE_MODE"] = "LIVE"
import assert_anchor_artifacts as AA  # noqa: E402

def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []

orders = rows(os.path.join(DAY, "orders.jsonl"))
anchors = sorted({(r["anchor_ts"], r["rebalance_id"]) for r in orders})
for ats, rid in anchors:
    tmp = tempfile.mkdtemp(prefix="e9_repro_")
    try:
        for h in HIST:
            os.makedirs(os.path.join(tmp, h))
            shutil.copy(os.path.join(CEN, "pilot_log", h, "orders.jsonl"), os.path.join(tmp, h, "orders.jsonl"))
        d = os.path.join(tmp, "20260913"); os.makedirs(d)
        for t in ("orders", "anchors", "position_readback", "daily_nav", "fills"):
            rr = [r for r in rows(os.path.join(DAY, f"{t}.jsonl")) if float(r.get("anchor_ts") or r.get("ts") or 0) <= ats + 3600]
            with open(os.path.join(d, f"{t}.jsonl"), "w") as f:
                f.write("".join(json.dumps(r) + "\n" for r in rr))
        mine = [r for r in orders if r["rebalance_id"] == rid]
        res = AA.check_artifacts(rid, len(mine), anchor_ts=ats, root=tmp, day="20260913", mode="LIVE", rebalanced=True)
        a = [x for x in res["assertions"] if x["assert"] == "no orders column is constant for want of a producer"][0]
        print(rid, "ok=", a["ok"], "|", a["detail"])
        print("   tables:", {k: v["state"] for k, v in res["constant_columns"].items() if k.endswith(".*")})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
