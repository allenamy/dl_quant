#!/bin/bash
# W6C-B13 mutation battery: each mutation must turn live/tests_book_observability.py RED.
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c
PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/mut
mkdir -p "$OUT"
run() {  # $1 = tag
  env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$C/live/tests_book_observability.py" > "$OUT/$1.log" 2>&1
  rc=$?
  printf "%-6s rc=%s  %s\n" "$1" "$rc" "$(grep -E '^[0-9]+/[0-9]+ checks passed' "$OUT/$1.log" | tail -1)"
  grep '  FAIL ' "$OUT/$1.log" | sed 's/^  FAIL /        red: /' | cut -c1-96
}
mutate() {  # $1 file  $2 python-replacement-script
  cp "$C/$1" "$OUT/$(basename $1).orig"
  $PY - "$C/$1" <<PYEOF
import sys
p=sys.argv[1]; s=open(p).read()
$2
open(p,"w").write(s)
PYEOF
}
restore() { cp "$OUT/$(basename $1).orig" "$C/$1"; }

echo "── control (unmutated) ──"; run control

echo "── M1: the reference becomes AT-OR-AFTER instead of AT (the ladder's own readback would count as having looked at the scheduled anchor) ──"
mutate live/reconcile.py 'old="\"observed_at_newest_scheduled\": (None if newest is None else n_newest > 0),"
new="\"observed_at_newest_scheduled\": (None if newest is None else any(t >= newest for t in per_anchor)),"
assert s.count(old)==1; s=s.replace(old,new,1)'
run M1; restore live/reconcile.py

echo "── M2: NEVER_OBSERVED (DRY_RUN) also halts opening ──"
mutate live/watchdog.py 'old="_OBS_HALTING = (\"UNOBSERVED\", \"UNKNOWN\")"
new="_OBS_HALTING = (\"UNOBSERVED\", \"UNKNOWN\", \"NEVER_OBSERVED\")"
assert s.count(old)==1; s=s.replace(old,new,1)'
run M2; restore live/watchdog.py

echo "── M3: the new halt kind is dropped from the judge's held-book list (5e would judge the halted anchor against intent ZERO) ──"
mutate live/position_break.py 'old="BOOK_HELD_HALT_KINDS = (\"proportional_local\", \"book_unobserved\")"
new="BOOK_HELD_HALT_KINDS = (\"proportional_local\",)"
assert s.count(old)==1; s=s.replace(old,new,1)'
run M3; restore live/position_break.py

echo "── M4: an ABSENT last_eval fails closed (every fresh tree halts) ──"
mutate scheduler/anchor_loop.py 'old="        out.update(state=\"NO_EVALUATION\","
new="        out.update(halt=True, state=\"NO_EVALUATION\","
assert s.count(old)==1; s=s.replace(old,new,1)'
run M4; restore scheduler/anchor_loop.py

echo "── M5: 5b stops inheriting the observability verdict ──"
mutate live/watchdog.py 'old="\"blind\": last_reconciled_ats is None or _obs_blind,"
new="\"blind\": last_reconciled_ats is None,"
assert s.count(old)==1; s=s.replace(old,new,1)'
run M5; restore live/watchdog.py

echo "── M6: the producer no longer distinguishes a failed read from DRY_RUN ──"
mutate scheduler/anchor_loop.py 'old="            (\"READ_FAILED\" if _read_error is not None else"
new="            (\"NO_ACCOUNT\" if _read_error is not None else"
assert s.count(old)==1; s=s.replace(old,new,1)'
run M6; restore scheduler/anchor_loop.py

echo "── restored control ──"; run control_after
