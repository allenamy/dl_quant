#!/usr/bin/env bash
# d10_pull_may_to_july.sh -- fill 2026-05/06/07, the gap between the audited Jan-Apr and Aug.
#
# Why these three and why now: the P2 ledger audit and the legs.npz RN8 audit both cover 2026-01..04 and
# 2026-08; 05/06/07 are the hole between them. Pulling is the one kind of work that ONLY runs in the quiet
# window, so it is what the window is for. data.binance.vision only (static CDN, no fapi weight), <=5 req/s
# enforced inside the puller, nice 10.
#
# Resumable by construction: the window is RE-MEASURED before every month via the canonical device, and the
# run stops cleanly rather than half-pulling into a closed window. Already-verified months are not re-fetched
# (d10_month_state.py), and after R25-11 "verified" means checksum_match True + set equality + re-hash, so an
# interrupted month that left unverified files is now re-pulled instead of being read as done -- which is
# exactly the 2026-01 hole this same pair of devices found earlier today.
set -u
REPO=/Users/haosiyu/Desktop/quant_research
QW=$REPO/multi_asset/exports/research/common/venue_quiet_window.py
EXP=/dev/shm/d10_2026-09-25
PY=/workspace/venv/bin/python
SCR=${SCR:-/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/d10}
LOG=$SCR/may_july.log
mkdir -p "$SCR"
# the log's first line carries THIS run's identity, so a waiter can tell it from a superseded run's log
RUNID="mayjul-$$-$(date -u +%Y%m%dT%H%M%SZ)"
say() { echo "$(date -u +%H:%M:%SZ) [$RUNID] $*" | tee -a "$LOG"; }
say "START run_id=$RUNID months=2026-05,2026-06,2026-07"

for M in 2026-05 2026-06 2026-07; do
  ST=$(ssh pod2 "$PY -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M" 2>/dev/null || echo ABSENT)
  case "$ST" in
    VERIFIED*) say "$M $ST -> not re-fetched"; continue;;
  esac

  if ! python3 -B "$QW" --json > /tmp/d10mj_$M.json 2>&1; then
    say "WINDOW CLOSED before $M -> stopping cleanly (resumable); $(python3 -c "import json;d=json.load(open('/tmp/d10mj_$M.json'));print('reason=%s now=%s'%(d.get('reason'),d.get('now_utc')))" 2>/dev/null)"
    say "STOPPED_RESUMABLE"; exit 0
  fi
  REM=$(python3 -c "import json;print(int(json.load(open('/tmp/d10mj_$M.json'))['remaining_min']))")
  if [ "$REM" -lt 8 ]; then
    say "only ${REM} min left -> stopping before $M (resumable)"; say "STOPPED_RESUMABLE"; exit 0
  fi
  N=$(ssh pod2 "wc -l < $EXP/symlists/$M.txt")
  say "$M START state=$ST symbols=$N window_remaining=${REM}min"

  t0=$(date +%s); rc=0
  ssh pod2 "nice -n 10 $PY -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $EXP/symlists/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1" || rc=$?
  if [ "$rc" != "0" ] && [ "$rc" != "1" ]; then
    say "$M PULL FAILED rc=$rc -- stopping, not retrying"
    ssh pod2 "tail -6 $EXP/logs/pull_$M.log" | tee -a "$LOG"; say "FAILED"; exit 1
  fi
  if [ "$rc" = "1" ]; then
    say "$M checksum mismatch on first pass -> repairing exactly those and re-fetching ONCE"
    ssh pod2 "$PY -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M" | tee -a "$LOG"
    rc2=0
    ssh pod2 "nice -n 10 $PY -B $EXP/devices/p9_pull_monthly_funding_zips.py $M $EXP/symlists/$M.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1" || rc2=$?
    if [ "$rc2" = "1" ]; then
      say "$M STILL MISMATCHING after one re-fetch -> naming them, not silently skipped"
      ssh pod2 "$PY -B $EXP/devices/d10_drop_mismatched.py $EXP/zips/$M $M --report-only" | tee -a "$LOG"
    elif [ "$rc2" != "0" ]; then
      say "$M RE-FETCH FAILED rc=$rc2 -- stopping"; say "FAILED"; exit 1
    fi
  fi
  t1=$(date +%s)
  say "$M DONE in $(( t1 - t0 ))s  $(ssh pod2 "$PY -B $EXP/devices/d10_month_state.py $EXP/zips/$M $M")"
done
say "ALL_THREE_MONTHS_ATTEMPTED"
for M in 2026-05 2026-06 2026-07; do
  say "final $M: $(ssh pod2 "$PY -B $EXP/devices/d10_manifest_gate.py $EXP/zips/$M $M 2>&1 | head -1")"
done
say "COMPLETE"
