#!/bin/bash
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c; PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/mut_i6; mkdir -p "$OUT"
run() { env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$C/live/tests_offschedule_held_book.py" > "$OUT/$1.log" 2>&1; rc=$?
  printf "%-6s rc=%s  %s\n" "$1" "$rc" "$(grep -E '^[0-9]+/[0-9]+ checks passed' "$OUT/$1.log" | tail -1)"
  grep '  FAIL ' "$OUT/$1.log" | sed 's/^  FAIL /        red: /' | cut -c1-92; }
mutate() { cp "$C/$1" "$OUT/$(basename $1).orig"; $PY - "$C/$1" <<PYEOF
import sys
p=sys.argv[1]; s=open(p).read()
$2
open(p,"w").write(s)
PYEOF
}
restore() { cp "$OUT/$(basename $1).orig" "$C/$1"; }
echo "── control ──"; run control
echo "── I6-M1: the judge drops off_schedule from the held-book list ──"
mutate live/position_break.py 'old="BOOK_HELD_HALT_KINDS = (\"proportional_local\", \"book_unobserved\", \"off_schedule\")"
new="BOOK_HELD_HALT_KINDS = (\"proportional_local\", \"book_unobserved\")"
assert s.count(old)==1; s=s.replace(old,new,1)'
run I6-M1; restore live/position_break.py
echo "── I6-M2: the writer stops marking the row ──"
mutate scheduler/anchor_loop.py 'old="                elif outA.get(\"off_schedule_halt\") and outA.get(\"action\") != \"FLATTEN\":\n                    row[\"halt_kind\"] = \"off_schedule\""
new="                elif False:\n                    row[\"halt_kind\"] = \"off_schedule\""
assert s.count(old)==1; s=s.replace(old,new,1)'
run I6-M2; restore scheduler/anchor_loop.py
echo "── I6-M3: the writer marks a FLATTEN run too (a book being emptied would be judged as held) ──"
mutate scheduler/anchor_loop.py 'old="elif outA.get(\"off_schedule_halt\") and outA.get(\"action\") != \"FLATTEN\":"
new="elif outA.get(\"off_schedule_halt\"):"
assert s.count(old)==1; s=s.replace(old,new,1)'
run I6-M3; restore scheduler/anchor_loop.py
echo "── I6-M4: the trip halt is also treated as a held book (the 2026-07-29 ghost book would be forgiven) ──"
mutate scheduler/anchor_loop.py 'old="                _wh = outA.get(\"watchdog_halt\") or {}\n                if _wh.get(\"state_kind\") == \"proportional_local\" and _wh.get(\"book_flattened\") is False:\n                    row[\"halt_kind\"] = \"proportional_local\""
new="                _wh = outA.get(\"watchdog_halt\") or {}\n                if _wh:\n                    row[\"halt_kind\"] = \"off_schedule\""
assert s.count(old)==1; s=s.replace(old,new,1)'
run I6-M4; restore scheduler/anchor_loop.py
echo "── restored ──"; run control_after
