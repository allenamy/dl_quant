#!/bin/bash
cd /workspace
for job in "metrics 2050" "klines1h 2050" "spotKlines1h 2050"; do
  set -- $job
  echo "=== [$(date -u +%H:%M:%SZ)] $1 补到 $2 天 ==="
  python3 rp_fetch.py "$1" "$2"
done
echo "=== 补齐完成 $(date -u) ==="
