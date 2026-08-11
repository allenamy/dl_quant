#!/bin/bash
# Auto-launch the Alpha-101/GTJA-191 sweep the moment the OHLCV panel finishes building.
# Survives agent turn-end / rate-limit (nohup'd, server-side). 0B, 2026-07-08.
set -u
until grep -q "\[ohlcv\] cached" /tmp/ohlcv_panel.log 2>/dev/null; do sleep 20; done
cd /mnt/storage/private/work_hsy/quant_research_multi_asset
source /root/miniconda3/etc/profile.d/conda.sh
conda activate hsy_v5push
echo "[orch] ohlcv panel ready -> launching sweep $(date)" > /tmp/alpha_sweep.log
PYTHONPATH=. python -u multi_asset/alpha/alpha_sweep.py --horizon 3600 --nperm 20 --zbar 3.0 >> /tmp/alpha_sweep.log 2>&1
echo "[orch] SWEEP EXIT $?" >> /tmp/alpha_sweep.log
