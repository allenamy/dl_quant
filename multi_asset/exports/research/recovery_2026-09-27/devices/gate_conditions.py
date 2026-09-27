# the resume gate's own evaluation path (copytree -> WI.collect -> WD.run(MockBroker)), as ops/resume_from_trip.sh step 1 runs it,
# on an ISOLATED clone's LIVE pilot_log, printing every condition's verdict. Run under sandbox-exec (network denied, production unreadable).
# usage: /usr/bin/sandbox-exec -f offline_clone.sb /usr/bin/python3 gate_conditions.py <clone>
import json, os, shutil, sys, tempfile
REPO = sys.argv[1]; sys.path.insert(0, os.path.join(REPO, "live")); os.chdir(REPO)
import state_root as SR, watchdog as WD, watchdog_inputs as WI
root = SR.paths_for("LIVE")["pilot_log"]; assert root.startswith(REPO), root
tree = tempfile.mkdtemp(prefix="rg_"); shutil.rmtree(tree); shutil.copytree(root, tree)
ops, ve, _ = WI.collect(tree)
ev, _, _ = WD.run(tree, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops, verbose=False, state_dir=tempfile.mkdtemp())
print("tripped", ev.get("tripped"), "triggers", ev.get("triggers"), "blind", ev.get("conditions_blind"), "local", ev.get("local_responses"))
C = ev["conditions"]
for k, v in C.items():
    if isinstance(v, dict):
        print(k, {kk: v.get(kk) for kk in ("triggered", "blind", "state", "recent_day", "recent_day_pct") if kk in v})
c5 = C.get("cond5_venue_event") or {}; b = c5.get("5b_liquidation_anomaly") or {}; e = c5.get("5e_position_break") or {}
print("5b", {k: b.get(k) for k in ("n", "state", "last_reconciled_anchor_ts", "n_historical_anomalies", "blind", "judged_is_newest_scheduled")})
L = e.get("latest") or {}
print("5e", {k: e.get(k) for k in ("triggered", "blind", "state")}, {k: L.get(k) for k in ("trip_gate", "portfolio_dev_usdt", "anchor_ts", "target_gross")})
