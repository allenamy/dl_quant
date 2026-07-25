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
step "=== run_daily done $TODAY ==="
