#!/bin/bash
# Live shadow — item 5: the daily orchestrator (server-resident cron).
#
# Runs the full chain once per day: pull the latest public archives -> splice the panel tail ->
# fold_4 inference -> emit unit-gross positions -> update the dual-curve paper P&L -> C4 daily report.
# Idempotent (safe to re-run: the tail rebuild is deterministic from the frozen panel; emit/P&L/report
# overwrite). A lock prevents concurrent runs; any step failure is logged to the alarm file and aborts.
#
# Install (server crontab, daily 09:00 UTC — after the T+1 daily archive publishes):
#   (crontab -l 2>/dev/null; echo "0 9 * * * /bin/bash /mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/engine/live/run_daily.sh") | crontab -
set -uo pipefail

MA=/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python3
LIVE=$MA/exports/live
LOG=$LIVE/logs
LOCK=$LIVE/run_daily.lock
ALARM=$LOG/ALARM.log
mkdir -p "$LOG" "$LIVE/positions" "$LIVE/pnl" "$LIVE/monitor"

exec 9>"$LOCK"
if ! flock -n 9; then echo "$(date -u +%FT%TZ) another run_daily is in progress; skip" >> "$LOG/run.log"; exit 0; fi

TODAY=$(date -u +%Y%m%d)
RUNLOG=$LOG/run_$TODAY.log
step() { echo "$(date -u +%FT%TZ) [step] $*" | tee -a "$RUNLOG"; }
fail() { echo "$(date -u +%FT%TZ) [ALARM] step '$1' FAILED (exit $2) — see $RUNLOG" | tee -a "$ALARM" >> "$RUNLOG"; exit "$2"; }
run() { step "$1"; shift; "$@" >> "$RUNLOG" 2>&1 || fail "$1" $?; }

step "=== run_daily start $TODAY ==="
run "ingest (pull + splice tail -> wide_dl_live)"   "$PY" "$MA/engine/live/build_tail.py" --build
run "signal loop (inference -> positions_*.json)"    "$PY" "$MA/engine/live/signal_loop.py" --emit
run "paper P&L (dual-curve A/B)"                       "$PY" "$MA/engine/live/paper_pnl.py"
run "C4 monitor (rolling rank-IC daily report)"       "$PY" "$MA/engine/live/monitor.py"
# challenger dual-track (leg weights) — ADDITIVE and NON-FATAL: a failure here must never
# break the champion pipeline, so it is deliberately not routed through run()/fail().
step "challenger dual-track (king .50 weights; non-fatal)"
"$PY" "$MA/engine/live/challenger.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] challenger step failed (non-fatal)" | tee -a "$RUNLOG"

# champion_fixfunding third track (funding settlement-interval fix) — ADDITIVE, NON-FATAL.
# Orthogonal to the challenger track: that one tests WEIGHTS, this one tests the FACTOR FIX.
step "fixfunding third track (corrected funding factor; non-fatal)"
"$PY" "$MA/engine/live/fixfunding_track.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] fixfunding step failed (non-fatal)" | tee -a "$RUNLOG"

# pilot-prep daily chain (§9.5): regime -> guards -> v2 shadow log -> metrics -> watchdog ->
# mirrored report. ADDITIVE, NON-FATAL. MOCK ONLY: no account, no credentials, no venue contact.
step "pilot-prep daily (schema v2 log + metrics + watchdog + mirror; non-fatal, MOCK)"
"$PY" "$MA/engine/live/pilot_daily.py" --days_back 1 >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] pilot_daily step failed (non-fatal)" | tee -a "$RUNLOG"

# four-track shadow matrix (2 weight configs x 2 factor versions) — ADDITIVE, NON-FATAL.
# Three frozen comparisons + a pre-registered generalisation test; see exports/live/track_matrix/README.md
step "four-track matrix (weights x factor version; non-fatal)"
"$PY" "$MA/engine/live/track_matrix.py" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] track_matrix step failed (non-fatal)" | tee -a "$RUNLOG"

# acceptance runner — the SINGLE machine-checkable "all green" statement. Non-fatal here (the
# shadow must keep running even if a suite regresses) but its JSON is the only citable source.
step "acceptance runner (single all-green statement)"
bash "$MA/engine/live/run_acceptance.sh" --json "$MA/exports/live/acceptance/latest.json" >> "$RUNLOG" 2>&1 || echo "$(date -u +%FT%TZ) [warn] acceptance NOT green — see exports/live/acceptance/latest.json" | tee -a "$RUNLOG" "$ALARM"

step "=== run_daily done $TODAY ==="
