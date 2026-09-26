#!/usr/bin/env bash
# d10_pull_resume_pod2.sh -- resume the 2026-05/06/07 archive pull, running ENTIRELY on pod2.
#
# Why not re-run d10_pull_may_to_july.sh: that driver ran the puller in the foreground of one ssh session per
# month, so when the session dropped at 2026-09-25T18:51:08Z (rc 255) the puller died with it and 2026-06 stopped
# at 281/646 (receipt D10_INFLIGHT_INVENTORY_2026-09-26.json). Here the whole loop lives on pod2 under setsid, so
# a Mac sleep/reboot or an ssh drop cannot kill it. Lead rule 2026-09-26: the pull may run in the local quiet
# window OR on pod2; it downloads only from data.binance.vision (no exchange API) and uses no Mac CPU, so the
# local quiet-window gate does not apply here.
#
# Month logic is the original driver's, unchanged: d10_month_state.py decides (VERIFIED -> skip); the puller
# re-verifies every existing zip against the venue .CHECKSUM (never trusts it); a rc-1 checksum mismatch drops
# exactly those files and re-fetches ONCE, a second mismatch is named, not skipped; any other rc stops.
# Usage (on pod2): setsid nohup bash d10_pull_resume_pod2.sh </dev/null >/dev/null 2>&1 &
set -u
EXP=/dev/shm/d10_2026-09-25
PY=/workspace/venv/bin/python
LOG=$EXP/logs/pull_resume_pod2.log
RUNID="resume-$$-$(date -u +%Y%m%dT%H%M%SZ)"
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$RUNID] $*" >> "$LOG"; }
say "START run_id=$RUNID pgid=$(ps -o pgid= -p $$ | tr -d ' ') months=2026-05,2026-06,2026-07"

for M in 2026-05 2026-06 2026-07; do
  ST=$($PY -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M 2>&1 || echo "STATE_DEVICE_FAILED")
  case "$ST" in
    VERIFIED*) say "$M $ST -> not re-fetched"; continue;;
    STATE_DEVICE_FAILED*) say "$M state device failed: $ST"; say "FAILED"; exit 1;;
  esac
  say "$M START state=$ST symbols=$(wc -l < $EXP/symlists/$M.txt)"
  t0=$(date +%s); rc=0
  nice -n 10 $PY -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $EXP/symlists/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1 || rc=$?
  if [ "$rc" != "0" ] && [ "$rc" != "1" ]; then
    say "$M PULL FAILED rc=$rc -- stopping, not retrying"; tail -6 $EXP/logs/pull_$M.log >> "$LOG"; say "FAILED"; exit 1
  fi
  if [ "$rc" = "1" ]; then
    say "$M checksum mismatch on first pass -> repairing exactly those and re-fetching ONCE"
    $PY -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M >> "$LOG" 2>&1
    rc2=0
    nice -n 10 $PY -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $EXP/symlists/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1 || rc2=$?
    if [ "$rc2" = "1" ]; then
      say "$M STILL MISMATCHING after one re-fetch -> naming them, not silently skipped"
      $PY -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M --report-only >> "$LOG" 2>&1
    elif [ "$rc2" != "0" ]; then
      say "$M RE-FETCH FAILED rc=$rc2 -- stopping"; say "FAILED"; exit 1
    fi
  fi
  say "$M DONE in $(( $(date +%s) - t0 ))s  $($PY -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M 2>&1)"
done
for M in 2026-05 2026-06 2026-07; do
  say "final $M: $($PY -B $EXP/devices/d10_manifest_gate.py $EXP/zips/$M $M 2>&1 | head -1)"
done
say "COMPLETE"
