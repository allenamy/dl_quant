#!/bin/bash
# Sequential: wait REG_arch → launch REG_feat → wait → launch REG_loss
set -e
SSH_FLAGS="-o ConnectTimeout=15 -o ServerAliveInterval=30 -p 31999"
HOST="root@212.50.244.62"
WORKDIR="/mnt/storage/private/work_hsy/quant_research"
ENV="hsy_v5push"
LOG="/tmp/v5push_reg_seq.log"

log() { echo "[seq $(date +%H:%M:%S)] $1" | tee -a $LOG; }

wait_pid() {
  local pattern=$1; local label=$2
  log "Waiting for $label..."
  while ssh $SSH_FLAGS $HOST "pgrep -f '$pattern' > /dev/null"; do sleep 60; done
  log "$label exited."
}

wait_build_v4() {
  log "Waiting for TV v4 build..."
  while true; do
    n=$(ssh $SSH_FLAGS $HOST "ls $WORKDIR/data/npz_v4_tv_overlay_v4/ 2>/dev/null | wc -l")
    [ "$n" -ge 991 ] && log "TV v4 build complete ($n days)" && return
    sleep 60
  done
}

launch() {
  local config_name=$1; local log_tag=$2
  local ts=$(date +%Y%m%d_%H%M%S)
  local logdir="logs/${log_tag}_${ts}"
  ssh $SSH_FLAGS $HOST "
    cd $WORKDIR && mkdir -p $logdir &&
    source /root/miniconda3/etc/profile.d/conda.sh && conda activate $ENV &&
    nohup python -u run_pipeline_v3.py \
      --config configs/v5push/${config_name} \
      --skip-features --max-folds 3 --start-fold 0 \
      > $logdir/train.log 2>&1 &
    sleep 3
    echo [launched] $logdir/train.log
  "
}

# Step 1: wait REG_arch
wait_pid "singh_alpha0_huber_track_reg_arch" "REG_arch"
# Step 2: wait TV v4 build (must be ready before REG_feat)
wait_build_v4
# Step 3: launch REG_feat
log "Launching REG_feat"
launch "singh_alpha0_huber_track_reg_feat.json" "v5push_track_reg_feat"
sleep 30
# Step 4: wait REG_feat
wait_pid "singh_alpha0_huber_track_reg_feat" "REG_feat"
# Step 5: launch REG_loss
log "Launching REG_loss"
launch "singh_alpha0_huber_track_reg_loss.json" "v5push_track_reg_loss"
sleep 30
# Step 6: wait REG_loss
wait_pid "singh_alpha0_huber_track_reg_loss" "REG_loss"

log "All REG tracks complete."
