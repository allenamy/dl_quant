#!/bin/bash
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c; PY=/usr/bin/python3
OUT=/Users/haosiyu/cc_tmp/fx_w6c_probes/mut_led04; mkdir -p "$OUT"
run() { env -u LIVE_MODE ACCEPTANCE_INNER=1 $PY "$C/live/tests_cond4_amended_transfer_day.py" > "$OUT/$1.log" 2>&1; rc=$?
  printf "%-8s rc=%s  %s\n" "$1" "$rc" "$(grep -E '^[0-9]+/[0-9]+ checks passed' "$OUT/$1.log" | tail -1)"
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
echo "── L-M1: the sha check is dropped (a record that no longer describes its row is believed) ──"
mutate live/ledger_amendments.py 'old="    ok, why = _row_sha_ok(pilot_log_root, rec)"
new="    ok, why = True, \"\""
assert s.count(old)==1; s=s.replace(old,new,1)'
run L-M1; restore live/ledger_amendments.py
echo "── L-M2: a duplicate key is resolved by position instead of dropped ──"
mutate live/ledger_amendments.py 'old="    for k in conflict:\n        out.pop(k, None)"
new="    for k in list(conflict)[:0]:\n        out.pop(k, None)"
assert s.count(old)==1; s=s.replace(old,new,1)'
run L-M2; restore live/ledger_amendments.py
echo "── L-M3: a post-fix row is silently re-priced from its USDT slice (a second change to a trigger) ──"
mutate live/ledger_amendments.py 'old="        return dict(base, usdt=rec_usdt, source=\"recorded\", status=\"post_fix_row\","
new="        return dict(base, usdt=_finite(slice_usdt), source=\"recorded\", status=\"post_fix_row\","
assert s.count(old)==1; s=s.replace(old,new,1)'
run L-M3; restore live/ledger_amendments.py
echo "── L-M4: a missing record is BLIND instead of named (the correction becomes a way to stop the book) ──"
mutate live/watchdog.py 'old="                _re, _un = _rf.get(\"usdt\"), _r3.get(\"unrealised_pnl\")"
new="                _re, _un = (None if _rf.get(\"status\") == \"unamended_prefix_day\" else _rf.get(\"usdt\")), _r3.get(\"unrealised_pnl\")"
assert s.count(old)==1; s=s.replace(old,new,1)'
run L-M4; restore live/watchdog.py
echo "── L-M5: the reader loses its own module and cond4 keeps a private copy of the path ──"
mutate live/ledger_amendments.py 'old="REL_PATH = os.path.join(\"ledger_amendments\", \"daily_nav_realised_split.jsonl\")"
new="REL_PATH = os.path.join(\"amendments\", \"daily_nav_realised_split.jsonl\")"
assert s.count(old)==1; s=s.replace(old,new,1)'
run L-M5; restore live/ledger_amendments.py
echo "── restored ──"; run control_after
