#!/bin/bash
cd /mnt/storage/private/work_hsy/f8_2026-08-22
until grep -q "DEPLOY_QUEUE_DONE" logs/deploy_queue.log 2>/dev/null; do sleep 120; done
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
python -u legs2_export.py > logs/legs2.log 2>&1
for CFG in "V2E 42 e4 0" "V2E 2027 e4 0" "V2L 42 lob38 0" "V2L 2027 lob38 0" "V2P 42 - 0.3" "V2P 2027 - 0.3" "V2C 42 cc3 0" "V2C 2027 cc3 0"; do
  set -- $CFG
  EX=$3; [ "$EX" = "-" ] && EX=""
  echo "=== START $1 s$2 $(date -u)"
  V2=1 ARM=$1 SEED=$2 COST=3.52 LDD=0.25 AFIX=0 EXTRA=$EX LPP=$4 python -u f10_train.py > logs/f10_$1_s$2.log 2>&1
  echo "=== END $1 s$2 rc=$? $(date -u)"
done
echo "ARMS_QUEUE_DONE $(date -u)"
