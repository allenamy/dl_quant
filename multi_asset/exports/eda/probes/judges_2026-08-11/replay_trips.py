#!/usr/bin/python3
"""Replay the 8 real trips against OLD code and NEW code, on the SAME reconstructed ledger.

The ledger is append-only (B33's price fix runs before the row is persisted, it does not rewrite
history), so truncating each table to `anchor_ts <= trip_ts` reconstructs exactly what the
watchdog saw at that moment.

OLD code is `git show HEAD:live/watchdog.py` — the real file, not a re-implementation of its rule.
"""
import json, os, shutil, subprocess, sys, tempfile, time

REPO = os.path.expanduser("~/dl_quant_live")
SRC = os.path.join(REPO, "state/testnet/pilot_log")
OLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay_old")

TABLES = ["orders", "anchors", "position_readback", "daily_nav", "funding", "fills"]
TRIPS = [
    "2026-07-26T00:17:11Z", "2026-07-26T04:15:42Z", "2026-07-26T12:17:31Z",
    "2026-07-26T16:16:40Z", "2026-07-27T00:18:14Z", "2026-07-27T04:15:49Z",
    "2026-07-27T16:18:34Z", "2026-07-28T08:18:08Z",
]
TS_FIELD = {"orders": "anchor_ts", "anchors": "anchor_ts", "position_readback": "anchor_ts",
            "fills": "anchor_ts", "funding": "settlement_ts"}


def to_epoch(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone


def build_tree(cut_ts, dst):
    """Truncate every table to rows that existed at `cut_ts`. daily_nav is a per-day row keyed by
    day; it is carried whole for days strictly before the cut day and for the cut day itself."""
    n = 0
    for day in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, day)
        if not os.path.isdir(d):
            continue
        if day > time.strftime("%Y%m%d", time.gmtime(cut_ts)):
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
                if f is None or r.get(f) is None:
                    keep.append(ln)                   # daily_nav etc: no row timestamp
                elif float(r[f]) <= cut_ts:
                    keep.append(ln)
            if keep:
                open(os.path.join(od, f"{t}.jsonl"), "w").writelines(keep)
                n += len(keep)
    return n


CHILD = r'''
import importlib.util, json, os, sys
which, root = sys.argv[1], sys.argv[2]
LIVE = os.path.expanduser("~/dl_quant_live/live")
sys.path.insert(0, LIVE)
# ★ sys.path ORDER CANNOT SELECT THE OLD COPY, and the first draft's assertion caught that: both
# `pilot_log` and `pilot_metrics` insert LIVE at position 0 when they load, so importing the old
# watchdog dragged LIVE to the front and `watchdog_inputs` then resolved to the NEW file — an
# "old" replay running half the new code. Loading by FILE PATH and pre-registering in sys.modules
# removes the ordering question instead of trying to win it.
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
if which == "old":
    OLD = os.environ["OLD_DIR"]
    WI = _load("watchdog_inputs", os.path.join(OLD, "watchdog_inputs.py"))
    WD = _load("watchdog", os.path.join(OLD, "watchdog.py"))
else:
    WI = _load("watchdog_inputs", os.path.join(LIVE, "watchdog_inputs.py"))
    WD = _load("watchdog", os.path.join(LIVE, "watchdog.py"))
assert ("replay_old" in WD.__file__) == (which == "old"), (which, WD.__file__)
assert ("replay_old" in WI.__file__) == (which == "old"), (which, WI.__file__)
# and the shared modules must be the LIVE ones in both arms — only watchdog[_inputs] differ
import reconcile as _RC, pilot_log as _PL
assert _RC.__file__.startswith(LIVE) and _PL.__file__.startswith(LIVE), (_RC.__file__, _PL.__file__)
ops = WI.derive_ops_stats(root)
ev = WD.evaluate(root, venue_events=[], ops_stats=ops)
c5 = ev["conditions"].get("cond5_venue_event", {})
b = c5.get("5b_liquidation_anomaly", {})
e = c5.get("5e_position_break", {})
print(json.dumps({
    "which": which, "watchdog_file": WD.__file__,
    "tripped": ev["tripped"], "triggers": ev["triggers"],
    "5b_state": b.get("state"), "5b_triggered": b.get("triggered"), "5b_n": b.get("n"),
    "5b_n_trade_break": b.get("n_trade_break_latest"),
    "5e_state": e.get("state"), "5e_triggered": e.get("triggered"),
    "5e_dev_frac": ((e.get("latest") or {}) if isinstance(e, dict) else {}).get("portfolio_dev_frac"),
    "5e_dev_usdt": ((e.get("latest") or {}) if isinstance(e, dict) else {}).get("portfolio_dev_usdt"),
    "5e_n_sym": ((e.get("latest") or {}) if isinstance(e, dict) else {}).get("n_symbol_breaches"),
    "drift": ev["conditions"].get("cond7_ops", {}).get("unrecovered_drift"),
    "degraded": ev.get("conditions_degraded"),
}))
'''

def run(which, root):
    env = dict(os.environ, OLD_DIR=OLD_DIR, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run(["/usr/bin/python3", "-c", CHILD, which, root],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        return {"which": which, "ERROR": p.stderr[-900:]}
    return json.loads(p.stdout.strip().splitlines()[-1])


def main():
    print(f"{'TRIP':22s} {'OLD':>5s} {'NEW':>5s}  detail")
    print("-" * 118)
    n_old = n_new = 0
    rows = []
    for trip in TRIPS:
        cut = to_epoch(trip)
        tmp = tempfile.mkdtemp(prefix="replay_")
        try:
            build_tree(cut, tmp)
            o, n = run("old", tmp), run("new", tmp)
            if "ERROR" in o or "ERROR" in n:
                print(trip, "ERROR", (o.get("ERROR") or n.get("ERROR"))[:600]); continue
            n_old += bool(o["tripped"]); n_new += bool(n["tripped"])
            rows.append((trip, o, n))
            print(f"{trip:22s} {'TRIP' if o['tripped'] else '-':>5s} "
                  f"{'TRIP' if n['tripped'] else '-':>5s}  "
                  f"old5b={o['5b_state']}/{o['5b_n']} -> new5b={n['5b_state']}"
                  f"(pos={n['5b_n']},tradebrk={n['5b_n_trade_break']}) | "
                  f"5e={n['5e_state']} frac={n['5e_dev_frac']} nsym={n['5e_n_sym']} | "
                  f"drift {o['drift']}->{n['drift']}")
            for t in o["triggers"]:
                print(f"{'':22s}   OLD trigger: {t}")
            for t in n["triggers"]:
                print(f"{'':22s}   NEW trigger: {t}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("-" * 118)
    print(f"CONTROL (old code reproduces the trip): {n_old}/8")
    print(f"AFTER THE SPLIT (new code halts)      : {n_new}/8")
    json.dump([{"trip": t, "old": o, "new": n} for t, o, n in rows],
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "replay_result.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
