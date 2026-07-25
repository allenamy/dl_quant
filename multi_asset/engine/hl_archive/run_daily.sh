#!/bin/bash
# Hyperliquid archive — daily orchestrator (server-resident cron).
#
# TIME-SENSITIVE: HL's hourly-candle endpoint serves a ROLLING ~210-day window (5000-row cap).
# Every day this does not run is a day of hourly history permanently lost for HL backtesting.
#
# Two jobs:
#   pull_daily.py  — incremental klines + funding + daily roster snapshot (minutes)
#   record_l2.py   — websocket L2 recorder, 1 snapshot/coin/minute (long-running; relaunched
#                    hourly by cron, flock keeps exactly one alive)
#
# Install (server crontab):
#   0 8 * * *  flock -n /tmp/hl_arch_pull.lock bash .../engine/hl_archive/run_daily.sh pull  >> .../logs/pull_$(date +\%Y\%m\%d).log 2>&1
#   */30 * * * * flock -n /tmp/hl_arch_l2.lock bash .../engine/hl_archive/run_daily.sh l2    >> .../logs/l2_$(date +\%Y\%m\%d).log 2>&1
#
# Read-only public endpoints only. No trading/auth calls.
set -uo pipefail

MA=/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset
PY=/root/miniconda3/envs/hsy_v5push/bin/python3
ARC=$MA/exports/hl_archive
LOG=$ARC/logs
mkdir -p "$LOG" "$ARC/klines" "$ARC/funding" "$ARC/roster" "$ARC/l2"

MODE=${1:-pull}
stamp() { date -u +%FT%TZ; }

case "$MODE" in
  pull)
    echo "$(stamp) [hl_archive] incremental pull start"
    "$PY" "$MA/engine/hl_archive/pull_daily.py" --max_seconds 5400
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "$(stamp) [ALARM] hl_archive pull FAILED rc=$rc" | tee -a "$LOG/ALARM.log"
    fi
    echo "$(stamp) [hl_archive] incremental pull done rc=$rc"
    ;;
  l2)
    # relaunched every 30 min by cron; flock means only one instance ever runs. --minutes 1440
    # so a healthy process just keeps going and the relaunch is a no-op.
    echo "$(stamp) [hl_archive] l2 recorder start"
    "$PY" "$MA/engine/hl_archive/record_l2.py" --minutes 1440 --top 60
    echo "$(stamp) [hl_archive] l2 recorder exited rc=$?"
    ;;
  backfill)
    echo "$(stamp) [hl_archive] DEEP funding backfill start (~1171d, hours)"
    "$PY" "$MA/engine/hl_archive/pull_daily.py" --backfill
    echo "$(stamp) [hl_archive] backfill done rc=$?"
    ;;
  *)
    echo "usage: run_daily.sh {pull|l2|backfill}"; exit 2;;
esac
