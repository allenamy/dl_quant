#!/usr/bin/env python3
"""0C audit, consequence check — CAN the 08:01Z trip actually be cleared right now?

Not one of the four questions, but it is the action the lead is preparing, so it is the one thing
worth simulating. `ops/resume_from_trip.sh` step 1/4 is a HARD GATE: it copies the pilot_log tree,
re-runs WI.collect + WD.run over the COPY, and refuses if anything still fires.

This reproduces exactly that gate, against a copy in the scratchpad. Nothing under ~/dl_quant_live
is read-write or written to: the tree is copied out, `state_dir` and `rows_root` are temp dirs.
"""
import os, sys, json, shutil, tempfile

SRC = os.path.expanduser("~/dl_quant_live/state/testnet/pilot_log")
SCRATCH = os.path.expanduser(
    "~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/"
    "6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad")
os.makedirs(SCRATCH, exist_ok=True)
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import watchdog as WD, watchdog_inputs as WI

tree = os.path.join(SCRATCH, "resume_gate_copy")
shutil.rmtree(tree, ignore_errors=True)
shutil.copytree(SRC, tree)
sdir = tempfile.mkdtemp(prefix="0C_gate_state_", dir=SCRATCH)

ops, ve, diag = WI.collect(tree)
ev, _br, _st = WD.run(tree, broker=WD.MockBroker(), venue_events=ve, ops_stats=ops,
                      verbose=False, state_dir=sdir, rows_root=os.path.join(sdir, "rows"))

print("=" * 92)
print("RESUME GATE SIMULATION (ops/resume_from_trip.sh step 1/4, run on a COPY)")
print("=" * 92)
print(f"tripped            : {ev.get('tripped')}")
print(f"triggers           : {json.dumps(ev.get('triggers'), ensure_ascii=False, indent=1)}")
print(f"conditions_blind   : {ev.get('conditions_blind')}")
print(f"conditions_partial : {ev.get('conditions_partial')}")
print(f"metric_errors      : {ev.get('metric_errors')}")
b = ev["conditions"]["cond5_venue_event"]["5b_liquidation_anomaly"]
print(f"\n5b state={b['state']} n={b['n']} anchor={b['last_reconciled_anchor_ts']}")
print(f"5b names: {[(a['symbol'], a['kind'], a.get('terminal_reason')) for a in b['examples']]}")
print(f"cond7   : {json.dumps(ev['conditions']['cond7_ops'], ensure_ascii=False)}")
print("\nVERDICT: " + ("the gate REFUSES — resume_from_trip.sh exits 1 and touches nothing"
                       if ev.get("tripped") or ev.get("conditions_blind")
                       else "the gate would ALLOW the resume"))
shutil.rmtree(tree, ignore_errors=True)
