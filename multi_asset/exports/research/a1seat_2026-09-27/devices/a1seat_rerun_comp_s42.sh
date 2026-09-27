#!/bin/bash
# a1seat_rerun_comp_s42.sh -- control for the 07:17-07:20Z pod2 root-overlay-full minute (lead 07:2xZ): the only a1seat engine cell
# running in that minute was COMP_ONLY_m0 s42 (launched 07:14:30Z). Re-run the SAME cell (same config, same targets, copied at
# 07:25Z before the queue's cleanup deleted them; target sha asserted against the config's own npz_sha256) in a separate pod_root,
# with the queue's exact launch / save commands, and compare the saved series with the driver's SER_COMP_ONLY_m0_s42.npz bitwise.
# Run only after the driver's terminal line (no parallel cell of mine). Terminal: RERUN_IDENTICAL / RERUN_DIFFERS / RERUN_FAILED.
set -uo pipefail
R=/dev/shm/a1seat_2026-09-27; C=$R/rerun_COMP_s42; N=/dev/shm/news2_2026-09-23; PV=/workspace/venv/bin/python
FSAVE=/dev/shm/fresh_2026-09-23/devices/fa_ladsave.py; GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh; LG=$C/rerun.log
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
fail() { say "RERUN_FAILED $*"; exit 1; }
say "RERUN_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
grep -qE '^\S+ (A1SEAT_DONE|STOP)' $R/logs/rootcause.log || fail "driver has no terminal line yet"
T=f745163ef09292f7f6317731d63fee07e7ce8c8b21a1272257e4e2412bca55db
[ "$(sha256sum $C/targets/TARGETS_NEWS2_s42.npz | cut -c1-64)" = $T ] || fail "copied targets sha != config npz_sha256 $T"
$PV - $C <<'PY' || fail "config rewrite"
import json, sys, hashlib
C = sys.argv[1]; c = json.load(open(f"{C}/configs/RUN_CONFIG_MR_s42.ORIG.json")); r = c["runs"]; assert len(r) == 1
s = r[0]["targets"]["sources"]; assert len(s) == 1
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
npz, rj = f"{C}/targets/TARGETS_NEWS2_s42.npz", f"{C}/targets/TARGETS_NEWS2_s42.json"
assert sha(npz) == s[0]["npz_sha256"] and sha(rj) == s[0]["receipt_sha256"]
s[0]["npz"], s[0]["receipt"] = npz, rj; c["paths"] = dict(c["paths"]); c["paths"]["pod_root"] = f"{C}/pod_s42"
c["_a1seat_rerun_note"] = {"changed": ["runs[0].targets.sources[0].npz/receipt (byte-identical copies)", "paths.pod_root"]}
json.dump(c, open(f"{C}/configs/RUN_CONFIG_MR_s42.json", "w"), indent=1); print("config ok")
PY
mkdir -p $C/pod_s42/runs $C/pod_s42/receipts
until bash $GATE > $C/gate_last.log 2>&1 && [ "$(ps -eo pgid,args | grep 'bt_launch\.py' | grep -v grep | awk '{print $1}' | sort -u | grep -c .)" -le 1 ]; do sleep 120; done
say "launch ($(tail -1 $C/gate_last.log))"
cd $N/engine
setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 $PV -B bt_launch.py PATH,HOME,LC_CTYPE $C/configs/RUN_CONFIG_MR_s42.json --resume a1seat_rerun_COMP_42 > $C/engine.log 2>&1 < /dev/null &
sleep 5; PG=$(ps -o pgid= -p $! | tr -d ' '); echo "{\"pgid\":\"$PG\"}" > $C/PGID_engine.json; say "engine pgid=$PG"
while :; do
  grep -qE "^BT_LAUNCH VERDICT=" $C/engine.log && break
  grep -qE "^Traceback|No space left" $C/engine.log && fail "engine error (see $C/engine.log)"
  [ -n "$PG" ] && ! ps -o pid= -g $PG > /dev/null 2>&1 && { sleep 5; grep -qE "^BT_LAUNCH VERDICT=" $C/engine.log && break; fail "PGID $PG gone without a verdict"; }
  sleep 20
done
grep -qE "^BT_LAUNCH VERDICT=PASS" $C/engine.log || fail "verdict not PASS"
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B $FSAVE PATH,HOME,LC_CTYPE $C/pod_s42/runs/NEWS2_s42X_scaled_rule_raw_UAFE $C/SER_rerun.npz >> $C/save.log 2>&1 || fail "save"
a=$(sha256sum $R/series/SER_COMP_ONLY_m0_s42.npz | cut -c1-64); b=$(sha256sum $C/SER_rerun.npz | cut -c1-64)
if [ "$a" = "$b" ]; then say "RERUN_IDENTICAL driver $a == rerun $b"; else
  $PV - $R/series/SER_COMP_ONLY_m0_s42.npz $C/SER_rerun.npz <<'PY' >> $LG 2>&1
import numpy as np, sys
x, y = np.load(sys.argv[1]), np.load(sys.argv[2]); bad = False
for k in sorted(set(x.files) | set(y.files)):
    if k not in x.files or k not in y.files: print("ARRAY_ONLY_ONE_SIDE", k); bad = True; continue
    same = x[k].shape == y[k].shape and x[k].tobytes() == y[k].tobytes()
    print("ARRAY", k, "bitwise" if same else "DIFFERS max|d|=%r" % (float(np.nanmax(np.abs(x[k].astype(float) - y[k].astype(float)))) if x[k].shape == y[k].shape else "shape"))
    bad = bad or not same
print("ALL_ARRAYS_BITWISE" if not bad else "SOME_ARRAY_DIFFERS")
PY
  if tail -1 $LG | grep -q '^ALL_ARRAYS_BITWISE$'; then say "RERUN_IDENTICAL arrays bitwise (containers $a / $b differ: zip metadata only)"
  else say "RERUN_DIFFERS driver $a != rerun $b (per-array report above)"; fi; fi
