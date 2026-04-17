#!/usr/bin/env bash
# Overnight monitor: poll training pod every 5 min, append snapshot to log.
# Usage: ./scripts/overnight_monitor.sh LOGFILE [TRAIN_PID]
set -euo pipefail

LOG="${1:-logs/overnight_monitor.log}"
TRAIN_PID="${2:-17303}"
HOST="213.192.2.108"
PORT="40087"
KEY="$HOME/.ssh/runpod_ed25519"

mkdir -p "$(dirname "$LOG")"

# Infinite loop — caller kills when done
while true; do
  TS=$(date +"%Y-%m-%dT%H:%M:%S")
  {
    echo "=== $TS ==="
    ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$HOST" \
      "cd /workspace/quant_research && \
       echo PROC: \$(ps -p $TRAIN_PID -o pid,pcpu,rss,etime 2>/dev/null | tail -1 || echo GONE); \
       echo GPU: \$(nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader | head -1); \
       echo EPOCHS: \$(grep -c '^Epoch' logs/train_v4_full.log 2>/dev/null || echo 0); \
       echo LAST: \$(grep '^Epoch' logs/train_v4_full.log 2>/dev/null | tail -1 || echo '-'); \
       echo FOLDS_DONE: \$(ls experiments/v4_full/fold_*/test_results.json 2>/dev/null | wc -l)" \
      2>/dev/null || echo "SSH FAIL at $TS"
    echo ""
  } >> "$LOG"
  sleep 300
done
