#!/usr/bin/python3
"""Per-trip CAUSE classification, on the code that was ACTUALLY IN FORCE at each trip.

Read-only. Touches nothing in the repo: every historical tree is extracted to a temp dir with
`git archive`, and the ledger is truncated (never modified) to the rows that existed at the trip.

Why not replay on today's code: the comparison caliber has been replaced since (B30 turned
§4-5b from notional to quantity on 2026-07-28T08:42 SGT), so today's code says "cannot compare"
about six of the eight trips. A cause classification has to use the guard that fired.
"""
import json, os, shutil, subprocess, sys, tempfile, time
from collections import Counter

REPO = os.path.expanduser("~/dl_quant_live")
SRC = os.path.join(REPO, "state/testnet/pilot_log")
TABLES = ["orders", "anchors", "position_readback", "daily_nav", "funding", "fills"]
TS_FIELD = {"orders": "anchor_ts", "anchors": "anchor_ts", "position_readback": "anchor_ts",
            "fills": "anchor_ts", "funding": "settlement_ts"}
TRIPS = ["2026-07-26T00:17:11Z", "2026-07-26T04:15:42Z", "2026-07-26T12:17:31Z",
         "2026-07-26T16:16:40Z", "2026-07-27T00:18:14Z", "2026-07-27T04:15:49Z",
         "2026-07-27T16:18:34Z", "2026-07-28T08:18:08Z"]


def epoch(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone


def head_at(ts_utc):
    """The commit that was HEAD when the trip fired."""
    out = subprocess.run(["git", "log", "--all", "--pretty=%H|%cI",
                          f"--before={ts_utc}", "-1"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    return out.split("|") if out else (None, None)


def build_tree(cut_ts, dst):
    for day in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, day)
        if not os.path.isdir(d) or day > time.strftime("%Y%m%d", time.gmtime(cut_ts)):
            continue
        od = os.path.join(dst, day)
        os.makedirs(od, exist_ok=True)
        shutil.copy(os.path.join(d, "_schema.json"), os.path.join(od, "_schema.json"))
        for t in TABLES:
            p = os.path.join(d, f"{t}.jsonl")
            if not os.path.exists(p):
                continue
            keep = []
            for ln in open(p):
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                f = TS_FIELD.get(t)
                if f is None or r.get(f) is None or float(r[f]) <= cut_ts:
                    keep.append(ln)
            if keep:
                open(os.path.join(od, f"{t}.jsonl"), "w").writelines(keep)


def extract(commit, dst):
    subprocess.run(f"git archive {commit} | tar -x -C {dst}", cwd=REPO, shell=True, check=True)


CHILD = r'''
import json, os, sys
tree, root = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(tree, "live"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import watchdog as WD, watchdog_inputs as WI
assert WD.__file__.startswith(tree), WD.__file__
try:
    ops = WI.derive_ops_stats(root)
except Exception as e:
    ops = []
try:
    ev = WD.evaluate(root, [], ops)
except TypeError:
    ev = WD.evaluate(root)
c5 = (ev.get("conditions", {}) or {}).get("cond5_venue_event", {}) or {}
b = c5.get("5b_liquidation_anomaly", {}) or {}
# the anomaly records themselves, however that version shaped them
ex = b.get("examples") or []
out = {"tripped": ev.get("tripped"), "triggers": ev.get("triggers"),
       "n_5b": b.get("n"), "5b_state": b.get("state"),
       "examples": ex[:6],
       "drift": ((ev.get("conditions", {}) or {}).get("cond7_ops", {}) or {}).get("unrecovered_drift")}
# and the full anomaly set from the reconciler of that era, if it had one
try:
    import reconcile as RC, pilot_log as PL
    days = PL.available_days(root)
    rec = RC.reconcile([(d, PL.read_day(root, d)) for d in days])
    out["kinds"] = rec.get("n_anomalies_by_kind")
    out["latest_kinds"] = {}
    for a in (rec.get("latest") or []):
        k = a.get("kind", "(no kind field)")
        out["latest_kinds"][k] = out["latest_kinds"].get(k, 0) + 1
    out["latest_sample"] = (rec.get("latest") or [])[:4]
    out["n_unrec"] = rec.get("n_unreconcilable")
except Exception as e:
    out["reconcile"] = f"{type(e).__name__}: {e}"
print(json.dumps(out, default=str))
'''


def attribution_gaps(root, ats):
    """Caliber-independent: does the ledger at THIS anchor carry the two B33 forms?

    form 1 (B33)   a submitted leg with a filled_notional and NO avg_fill_px
    form 2 (B33-2) a submitted leg with NO filled_notional at all
    Both make `reconcile._exec_qty` unable to state the leg's size.
    """
    import glob
    f1, f2, rows = [], [], 0
    for p in sorted(glob.glob(os.path.join(root, "*", "orders.jsonl"))):
        for ln in open(p):
            o = json.loads(ln)
            if ats is not None and abs(float(o["anchor_ts"]) - float(ats)) > 0.5:
                continue
            rows += 1
            if o.get("submit_ts") is None:
                continue
            fn, px = o.get("filled_notional"), o.get("avg_fill_px")
            if fn is None:
                f2.append((o["symbol"], o.get("terminal_reason"), o.get("order_type")))
            elif float(fn) != 0.0 and not px:
                f1.append((o["symbol"], o.get("terminal_reason"), o.get("order_type")))
    return {"n_rows_at_anchor": rows, "form1_B33": f1, "form2_B33_2": f2}


def main():
    print(f"{'TRIP (UTC)':22s} {'HEAD at trip':10s} {'trip?':6s} {'5b n':5s} detail")
    print("-" * 120)
    results = []
    for trip in TRIPS:
        cut = epoch(trip)
        commit, cts = head_at(trip)
        tree = tempfile.mkdtemp(prefix="tree_")
        root = tempfile.mkdtemp(prefix="ledger_")
        try:
            extract(commit, tree)
            build_tree(cut, root)
            p = subprocess.run(["/usr/bin/python3", "-c", CHILD, tree, root],
                               capture_output=True, text=True,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            if p.returncode != 0:
                print(f"{trip:22s} {commit[:9]:10s} ERROR {p.stderr[-400:]}")
                continue
            r = json.loads(p.stdout.strip().splitlines()[-1])
            # the anchor the guard was judging
            ats = None
            for t in (r.get("examples") or []):
                ats = t.get("anchor_ts")
                break
            gaps = attribution_gaps(root, ats)
            r.update({"trip": trip, "commit": commit[:9], "commit_ts": cts,
                      "judged_anchor_ts": ats, "gaps": gaps})
            results.append(r)
            print(f"{trip:22s} {commit[:9]:10s} {str(r['tripped']):6s} {str(r['n_5b']):5s} "
                  f"state={r.get('5b_state')} latest_kinds={r.get('latest_kinds')} "
                  f"kinds={r.get('kinds')} n_unrec={r.get('n_unrec')}")
            print(f"{'':22s}   triggers: {r['triggers']}")
            print(f"{'':22s}   anchor={ats} ({time.strftime('%m-%d %H:%M:%SZ', time.gmtime(ats)) if ats else '-'}) "
                  f"rows={gaps['n_rows_at_anchor']} "
                  f"B33_form1={len(gaps['form1_B33'])} {gaps['form1_B33'][:3]} "
                  f"B33-2_form2={len(gaps['form2_B33_2'])} {gaps['form2_B33_2'][:3]}")
            if r.get("examples"):
                e = r["examples"][0]
                print(f"{'':22s}   sample anomaly: "
                      f"{ {k: e.get(k) for k in ('symbol','kind','expected','observed','residual_qty','residual_usdt','why')} }")
        finally:
            shutil.rmtree(tree, ignore_errors=True)
            shutil.rmtree(root, ignore_errors=True)
    json.dump(results, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "trip_causes.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
