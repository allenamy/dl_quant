#!/usr/bin/env bash
# d10_census_driver.sh -- D10 stage 1 question 2: FULL archive census, driven FROM THE MAC.
# Pre-registration: docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901.
# lead's ruling 2026-09-25 (verbatim requirements implemented here):
#   1. full census WITH .CHECKSUM, month order YEAR-DESCENDING 2026 -> 2020, so whatever is finished at
#      any moment is the decision-relevant part;
#   2. an existing zip whose CHECKSUM was verified is NOT re-fetched; a CHECKSUM mismatch is RECORDED and
#      re-fetched ONCE; still mismatching => named explicitly, never silently skipped;
#   3. 13:00-15:40Z today is the executor v2 release window: the Mac-side driver PAUSES, ssh driving
#      included, and re-measures the window before the next segment;
#   4. after each completed YEAR, that year's per-event count table is produced and committed BEFORE
#      being reported, without waiting for the whole census.
#
# WHY THE DRIVER IS ON THE MAC: venue_quiet_window.py reads the executor's anchor log, which exists on the
# Mac only; on pod2 it returns "anchor log unreadable -- unknown is not open" and exit 3 forever. The gate
# is evaluated where its evidence is readable. See common/README_venue_quiet_window.md.
set -uo pipefail
REPO=/Users/haosiyu/Desktop/quant_research
QW=$REPO/multi_asset/exports/research/common/venue_quiet_window.py
DEV=$REPO/multi_asset/exports/research/news2_2026-09-23/devices
EXP=/dev/shm/d10_2026-09-25
SYMLISTS=$EXP/symlists          # per-month lists from the inventory; see d10_make_symlists.py
# NOT the global 832-symbol list: probing all 832 in all 81 months costs 47,103 known-answer 404
# requests (measured 0.77 s each => 10.1 h of nothing). The inventory already says which files exist.
# Consequence recorded: a pruned manifest carries no 404 entries, so "the venue has no file here" is
# attested by the INVENTORY receipt, not by a 404 line in the month manifest.
LEDGER=/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz
SCR=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/d10
LLOG=$SCR/census.log
BLACKOUT_FROM=1300      # lead: executor v2 release window, zero extra local load
BLACKOUT_TO=1540
mkdir -p "$SCR"
say() { echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$LLOG"; }

in_blackout() {
  local hm; hm=$(date -u +%H%M); hm=$((10#$hm))
  [ "$hm" -ge "$BLACKOUT_FROM" ] && [ "$hm" -le "$BLACKOUT_TO" ]
}

# lead's order: year-descending, months inside a year ascending
MONTHS=$(python3 - <<'PY'
out = []
for y in range(2026, 2019, -1):
    for m in range(1, 13):
        if (y, m) <= (2026, 9):
            out.append("%04d-%02d" % (y, m))
print(" ".join(out))
PY
)
say "census start; order = year-descending, $(echo $MONTHS | wc -w | tr -d ' ') months"

prev_year=""
for M in $MONTHS; do
  Y=${M%%-*}
  if [ -n "$prev_year" ] && [ "$Y" != "$prev_year" ]; then
    say "year $prev_year complete -> per-event table"
    bash "$DEV/d10_year_table.sh" "$prev_year" 2>&1 | tee -a "$LLOG"
  fi
  prev_year=$Y

  if in_blackout; then
    say "BLACKOUT $BLACKOUT_FROM-$BLACKOUT_TO Z (executor v2 release window) -> pausing, ssh driving included"
    exit 0
  fi

  # a month the inventory says has NO archive files at all (the unpublished current month)
  if ! ssh pod2 "test -s $SYMLISTS/$M.txt" 2>/dev/null; then
    say "$M NO_ARCHIVE_FILES per the inventory (the venue publishes month M in early M+1) -> skipped by name"
    continue
  fi

  # is this month already done AND checksum-verified?
  ST=$(ssh pod2 "/workspace/venv/bin/python -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M" 2>/dev/null || echo "ABSENT")
  case "$ST" in
    VERIFIED*) say "$M $ST -> not re-fetched"; continue;;
  esac

  # re-measure the window before EVERY month, on the machine that can read the anchor log
  if ! python3 -B "$QW" --json > /tmp/d10c_$M.json 2>&1; then
    say "WINDOW CLOSED before $M -> stopping cleanly (resumable)"
    python3 -c "import json;d=json.load(open('/tmp/d10c_$M.json'));print('   now=%s open=%s remaining=%s reason=%s'%(d['now_utc'],d['open'],d['remaining_min'],d['reason']))" | tee -a "$LLOG"
    exit 0
  fi
  REM=$(python3 -c "import json;print(int(json.load(open('/tmp/d10c_$M.json'))['remaining_min']))")
  NOW=$(python3 -c "import json;print(json.load(open('/tmp/d10c_$M.json'))['now_utc'])")
  [ "$REM" -lt 8 ] && { say "only ${REM} min left -> stopping before $M (resumable)"; exit 0; }
  say "$M START state=$ST window now=$NOW remaining=${REM}min"
  scp -q /tmp/d10c_$M.json pod2:$EXP/logs/window_$M.json

  t0=$(date +%s); rc=0
  ssh pod2 "nice -n 10 /workspace/venv/bin/python -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $SYMLISTS/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1" || rc=$?
  # the puller exits 1 iff at least one CHECKSUM mismatched; anything else is a real failure
  if [ "$rc" != "0" ] && [ "$rc" != "1" ]; then
    say "$M PULL FAILED rc=$rc -- stopping, not retrying"
    ssh pod2 "tail -6 $EXP/logs/pull_$M.log" | tee -a "$LLOG"; exit 1
  fi
  if [ "$rc" = "1" ]; then
    say "$M CHECKSUM MISMATCH on first pass -> deleting only the mismatching zips and re-fetching ONCE (lead's rule)"
    ssh pod2 "/workspace/venv/bin/python -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M" | tee -a "$LLOG"
    rc2=0
    ssh pod2 "nice -n 10 /workspace/venv/bin/python -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $SYMLISTS/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1" || rc2=$?
    if [ "$rc2" = "1" ]; then
      say "$M STILL MISMATCHING after one re-fetch -> naming them, NOT silently skipped"
      ssh pod2 "/workspace/venv/bin/python -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M --report-only" | tee -a "$LLOG"
    elif [ "$rc2" != "0" ]; then
      say "$M RE-FETCH FAILED rc=$rc2 -- stopping"; exit 1
    else
      say "$M checksum clean after one re-fetch"
    fi
  fi
  t1=$(date +%s)
  say "$M DONE in $(( t1 - t0 ))s  $(ssh pod2 "/workspace/venv/bin/python -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M")"
done
if [ -n "$prev_year" ]; then
  say "year $prev_year complete -> per-event table"
  bash "$DEV/d10_year_table.sh" "$prev_year" 2>&1 | tee -a "$LLOG"
fi
say "CENSUS_ALL_MONTHS_DONE"
