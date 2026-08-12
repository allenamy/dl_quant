#!/bin/bash
# Launch Track E (Multi-Resolution Pool) on jpline.
#
# Pre-conditions:
#   - Track A (DAQH+TV) has completed or been aborted
#   - /tmp/v5push_tracke_sync/ has the staged code files
#
# Steps:
#   1. Sync staged code files (model + pipeline + backbone) to live paths
#   2. Launch training in background, log to dated dir
#
set -e
SERVER_HOST="${SERVER_HOST:-root@212.50.244.62}"
SERVER_PORT="${SERVER_PORT:-31999}"
WORKDIR="/mnt/storage/private/work_hsy/quant_research"
ENV_NAME="hsy_v5push"

# 1. Promote staged files
ssh -p $SERVER_PORT $SERVER_HOST "
  cd $WORKDIR
  cp /tmp/v5push_tracke_sync/dual_path_model_v3.py src/model/dual_path_model_v3.py
  cp /tmp/v5push_tracke_sync/conformer_backbone.py src/model/backbones/conformer_backbone.py
  cp /tmp/v5push_tracke_sync/run_pipeline_v3.py run_pipeline_v3.py
  echo 'Files promoted.'
"

# 2. Launch
TS=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs/v5push_mrp_${TS}"
ssh -p $SERVER_PORT $SERVER_HOST "
  cd $WORKDIR
  mkdir -p $LOG_DIR
  source /root/miniconda3/etc/profile.d/conda.sh && conda activate $ENV_NAME
  nohup python -u run_pipeline_v3.py \
    --config configs/v5push/singh_alpha0_huber_mrp.json \
    --skip-features --max-folds 3 --start-fold 0 \
    > $LOG_DIR/train.log 2>&1 &
  echo \"Track E launched: PID=\$!\"
  echo \"Log: $WORKDIR/$LOG_DIR/train.log\"
"
