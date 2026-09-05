#!/bin/bash
R=/workspace/review_scratch/dl_monthly_wf; cd $R
echo "=== $(date -u +%FT%TZ) done folds: E60 $(ls models/mE60_*_config.json 2>/dev/null | wc -l)/20  E1 $(ls models/mE1_*_config.json 2>/dev/null | wc -l)/20"
tail -3 logs/commands.txt
for f in logs/train_mE60.log logs/train_mE1.log; do [ -f $f ] && { echo "--- $f"; grep -E "^\[.*\] (==|CAUSALITY|MWF)" $f | tail -4; grep -E "ep[0-9]+ va" $f | tail -1; }; done
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
