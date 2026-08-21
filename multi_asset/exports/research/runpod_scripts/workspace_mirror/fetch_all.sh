#!/bin/bash
# 多源原始数据全量拉取 — 按【体积小且价值高】优先, 大块在后。
cd /workspace
for job in "metrics 1160" "liquidationSnapshot 1160" "klines1h 1160" "spotKlines1h 1160" "bookDepth 950" "aggTrades 400"; do
  set -- $job
  echo "=== [$(date -u +%H:%M:%SZ)] $1 ($2 天) ==="
  python3 rp_fetch.py $1 $2
  du -sh /workspace/data/raw/$1 2>/dev/null
  df -h /workspace | tail -1
done
echo "=== [$(date -u +%H:%M:%SZ)] 全部完成 ==="
