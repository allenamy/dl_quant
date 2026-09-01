#!/bin/bash
# 战役链式跑批 @pod: 等 fund_aug 就绪 → panel_ext → fea_ext(逐步日志, 任一步败即停)
cd /workspace
until [ -s fund_aug.json.gz ] && ! pgrep -f fund_pull_pod >/dev/null; do sleep 30; done
echo "[chain] fund_aug ready $(date -u +%H:%M)" 
python3 -u pod_panel_ext.py > panel_ext.log 2>&1 || { echo CHAIN_FAIL_panel; exit 1; }
echo "[chain] panel_ext done $(date -u +%H:%M)"
python3 -u pod_fea_ext.py > fea_ext.log 2>&1 || { echo CHAIN_FAIL_fea; exit 1; }
echo "[chain] CHAIN_DONE $(date -u +%H:%M)"
