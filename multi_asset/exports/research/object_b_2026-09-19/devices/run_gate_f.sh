#!/bin/bash
# GATE F over every staged snapshot anchor (4 in parallel), then the summary. Writes only under /workspace/object_b_2026-09-19.
set -u
R=/workspace/object_b_2026-09-19; cd $R/devices
echo "start $(date -u +%FT%TZ) pgid $(ps -o pgid= $$ | tr -d ' ')" > $R/logs/GATE_F_STATUS.txt
rm -f $R/receipts/gate_f/GATE_F_1*.json
ls $R/gate_inputs/snap | sort -n | xargs -P 4 -I{} sh -c "env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /workspace/venv/bin/python -B gate_f.py --anchor {} > $R/logs/gate_f_{}.log 2>&1; echo \"{} rc=\$?\" >> $R/logs/GATE_F_STATUS.txt"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 /workspace/venv/bin/python -B gate_f.py --summarize > $R/logs/gate_f_summary.log 2>&1
echo "DONE $(date -u +%FT%TZ) $(head -1 $R/logs/gate_f_summary.log)" >> $R/logs/GATE_F_STATUS.txt
