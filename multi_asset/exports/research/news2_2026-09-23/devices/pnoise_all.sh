#!/usr/bin/env bash
# pnoise_all.sh <first> <last> -- run the perturbation chains sequentially, dbar after each.
# STOPS on the first failure (lead 2026-09-24: "任一次失败就停下报告,不自动重试").
# Writes one line per run to SUMMARY.tsv so the caller can report without re-deriving anything.
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
NCRUN=/dev/shm/news2_2026-09-23/runs/NEWS2_s42_scaled_rule_raw_UAFE
TAGD=NEWS2_s42_scaled_rule_raw_UAFE
PV=/workspace/venv/bin/python
S=$EXP/receipts/SUMMARY.tsv
for R in $(seq "$1" "$2"); do
  t0=$(date -u +%s)
  echo "=== $(date -u +%H:%M:%S) RUN $R START ===" >> $EXP/logs/all.log
  if ! bash $EXP/devices/pnoise_run.sh "$R" >> $EXP/logs/all.log 2>&1; then
    echo -e "$R\tCHAIN_FAILED\t-\t-\t-" >> $S
    echo "RUN $R CHAIN FAILED -- STOPPING" >> $EXP/logs/all.log
    exit 1
  fi
  if ! $PV -B $EXP/devices/pnoise_dbar.py --news-devices /dev/shm/news2_2026-09-23/engine \
       --new-dir $EXP/runs/$TAGD --new-tag $TAGD --nc-dir $NCRUN --nc-tag $TAGD \
       --random-state "$R" --out $EXP/receipts/PNOISE_DBAR_r$R.json >> $EXP/logs/all.log 2>&1; then
    echo -e "$R\tDBAR_FAILED\t-\t-\t-" >> $S
    echo "RUN $R DBAR FAILED -- STOPPING" >> $EXP/logs/all.log
    exit 1
  fi
  PRE=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/PNOISE_DBAR_r$R.json'))['dbar_vs_nc']['pre2026']['mean_bps_per_day'])")
  Y26=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/PNOISE_DBAR_r$R.json'))['dbar_vs_nc']['2026']['mean_bps_per_day'])")
  t1=$(date -u +%s); FREE=$(df -k /dev/shm | tail -1 | awk '{printf "%.2f", $4/1048576}')
  echo -e "$R\tOK\t$PRE\t$Y26\t$(( (t1-t0)/60 ))min\tshm_free_${FREE}GiB" >> $S
  rm -rf $EXP/runs/*          # free as we go; the dbar receipt is already written
  echo "=== $(date -u +%H:%M:%S) RUN $R DONE pre2026=$PRE 2026=$Y26 ===" >> $EXP/logs/all.log
done
echo "ALL_RUNS_DONE" >> $EXP/logs/all.log
