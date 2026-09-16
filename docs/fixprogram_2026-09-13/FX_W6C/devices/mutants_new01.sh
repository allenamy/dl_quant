#!/bin/bash
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c; PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/mut_new01; mkdir -p "$OUT"
run() { env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$C/live/tests_flatten_batch_identity.py" > "$OUT/$1.log" 2>&1; rc=$?
  printf "%-8s rc=%s  %s\n" "$1" "$rc" "$(grep -E '^[0-9]+/[0-9]+ checks passed' "$OUT/$1.log" | tail -1)"
  grep '  FAIL ' "$OUT/$1.log" | sed 's/^  FAIL /        red: /' | cut -c1-92
  env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$C/live/tests_proportional_response.py" > "$OUT/$1_prop.log" 2>&1
  printf "          tests_proportional_response: %s\n" "$(grep -E '^[0-9]+/[0-9]+ checks passed' "$OUT/$1_prop.log" | tail -1)"; }
mutate() { cp "$C/$1" "$OUT/$(basename $1).orig"; $PY - "$C/$1" <<PYEOF
import sys
p=sys.argv[1]; s=open(p).read()
$2
open(p,"w").write(s)
PYEOF
}
restore() { cp "$OUT/$(basename $1).orig" "$C/$1"; }
echo "── control ──"; run control
echo "── N-M1: the readback goes back to its own clock read (the two keys diverge again) ──"
mutate live/watchdog.py 'old="                anchor_ts=float(batch_anchor_ts if batch_anchor_ts is not None else ts),"
new="                anchor_ts=float(ts),"
assert s.count(old)==1; s=s.replace(old,new,1)'
run N-M1; restore live/watchdog.py
echo "── N-M2: the rows go back to the row-write clock for anchor_ts ──"
mutate live/watchdog.py 'old="            lg.order(anchor_ts=batch_ts, symbol=o[\"symbol\"], side=side,"
new="            lg.order(anchor_ts=ts, symbol=o[\"symbol\"], side=side,"
assert s.count(old)==1; s=s.replace(old,new,1)'
run N-M2; restore live/watchdog.py
echo "── N-M3: submit_ts falls back silently (no source column) ──"
mutate live/watchdog.py 'old="                     **({\"submit_ts_source\": _sub_src} if _sent else {}),"
new="                     **({} if _sent else {}),"
assert s.count(old)==1; s=s.replace(old,new,1)'
run N-M3; restore live/watchdog.py
echo "── N-M4: the real broker stops recording the submit moment ──"
mutate live/binance_broker.py 'old="                              \"submit_ts\": _t_submit,\n                              \"mid_at_submit\": _mids.get(o[\"symbol\"]),\n                              # ★★ THE VENUE"
new="                              \"mid_at_submit\": _mids.get(o[\"symbol\"]),\n                              # ★★ THE VENUE"
assert s.count(old)==1; s=s.replace(old,new,1)'
run N-M4; restore live/binance_broker.py
echo "── N-M5: a LOCAL response batch is judged like the ladder (EXE-01 undone one evaluation later) ──"
mutate live/position_break.py 'old="    for ats in (flatten_ats - _local_flat):"
new="    for ats in (flatten_ats | _local_flat):"
assert s.count(old)==1; s=s.replace(old,new,1)'
run N-M5; restore live/position_break.py
echo "── restored ──"; run control_after
