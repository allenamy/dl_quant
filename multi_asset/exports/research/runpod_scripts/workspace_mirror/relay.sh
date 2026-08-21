#!/bin/bash
cd /workspace
# 等孤儿 spotKlines1h 退出(轮询 PID, 不用 pkill)
while kill -0 6889 2>/dev/null; do sleep 20; done
echo "=== [$(date -u +%H:%M:%SZ)] bookDepth 全史 1313 天 ==="
python3 rp_fetch.py bookDepth 1313
# 等基差队列退出后补 fundingRate
while kill -0 7398 2>/dev/null; do sleep 20; done
echo "=== [$(date -u +%H:%M:%SZ)] fundingRate ==="
python3 rp_basis.py fundingRate
echo "=== relay 完成 $(date -u) ==="
