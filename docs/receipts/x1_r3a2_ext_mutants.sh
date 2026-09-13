#!/bin/bash
# X1 R3-A2 external file-level mutants on the ledger COPY in /Users/haosiyu/cc_tmp/x1_ledger/state (never the run tree).
# For each mutant: delete ONE WHOLE flatten batch's order rows, keep events.jsonl untouched; run the NEW matrix file
# (git show 8113eed) and the OLD one (bf581eb); print each run's rc and every FAIL line; restore and cmp.
set -u
W=/Users/haosiyu/cc_tmp/x1_ledger
S=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad
NEWF=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/tests_disposition_matrix_8113eed.py
OLDF=$S/tests_disposition_matrix_bf581eb.py
git -C /Users/haosiyu/cc_tmp/exec_w6 show bf581eb:live/tests_disposition_matrix.py > "$OLDF"
EV=$W/state/live/watchdog/events.jsonl
echo "# worktree $W HEAD $(git -C $W rev-parse HEAD); ledger copy of ~/dl_quant_live/state taken $(cat $S/battery_snapshot_utc.txt) (copy end; the 225d02d battery ran in this worktree before these mutants, events.jsonl sha printed below)"
echo "# NEW file sha256 $(shasum -a 256 $NEWF | cut -d' ' -f1)   OLD file (bf581eb) sha256 $(shasum -a 256 $OLDF | cut -d' ' -f1)"
echo "# events.jsonl sha256 before: $(shasum -a 256 $EV | cut -d' ' -f1)"
run() {  # $1 label, $2 test file
  cp "$2" "$W/live/tests_disposition_matrix.py"
  (cd "$W" && bash -c '. ops/pyenv.sh && /usr/bin/python3 live/tests_disposition_matrix.py' > "$S/_mut_run.log" 2>&1); local rc=$?
  echo "  [$1] rc=$rc  $(grep -E 'ALL PASS|FAILURES' "$S/_mut_run.log" | tail -1 | grep -oE '\(([0-9]+) checks\)')  FAIL lines: $(grep -c '^  FAIL' "$S/_mut_run.log")"
  grep '^  FAIL' "$S/_mut_run.log" | cut -c1-110 | sed 's/^/      /'
  grep -F 'COMPLETENESS of a TRIP' "$S/_mut_run.log" | cut -c1-14 | sed 's/^/      completeness cell: /'
  grep -F 'COMPLETENESS of a TRIP' "$S/_mut_run.log" | grep -oE "'LEDGER_BATCH_MISSING': \{[^}]*\}" | cut -c1-260 | sed 's/^/      /'
}
for spec in "M1 20260801 FLATTEN-20260801T201827Z" "M2 20260912 FLATTEN-20260912T124737Z"; do
  set -- $spec; M=$1; D=$2; B=$3; F=$W/state/live/pilot_log/$D/orders.jsonl
  cp -p "$F" "$S/_bak_$D.jsonl"
  n0=$(wc -l < "$F"); nb=$(grep -c "\"rebalance_id\": \"$B\"" "$F")
  grep -v "\"rebalance_id\": \"$B\"" "$S/_bak_$D.jsonl" > "$F"
  echo "== $M: deleted every order row of $B from pilot_log/$D/orders.jsonl ($nb of $n0 lines; now $(wc -l < "$F")); events.jsonl untouched: $(shasum -a 256 $EV | cut -d' ' -f1)"
  run "$M NEW" "$NEWF"
  run "$M OLD bf581eb" "$OLDF"
  cp -p "$S/_bak_$D.jsonl" "$F"
  cmp "$F" "$S/_bak_$D.jsonl" && echo "   restored $D (cmp identical)"
done
echo "== M0 restored ledger:"
run "M0 NEW" "$NEWF"
cp "$NEWF" "$W/live/tests_disposition_matrix.py"
echo "# events.jsonl sha256 after: $(shasum -a 256 $EV | cut -d' ' -f1)"
