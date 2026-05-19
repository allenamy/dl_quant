#!/bin/bash
# Overnight sequencer: wait TV v3 → launch Track R → wait → launch Track S
# Local script polling remote PIDs and launching downstream tracks
set -e
SSH_FLAGS="-o ConnectTimeout=15 -o ServerAliveInterval=30 -p 31999"
HOST="root@212.50.244.62"
WORKDIR="/mnt/storage/private/work_hsy/quant_research"
ENV="hsy_v5push"
LOG_LOCAL="/tmp/v5push_track_r_s_seq.log"

log() { echo "[seq $(date +%H:%M:%S)] $1" >> $LOG_LOCAL; }

wait_for_build_v3() {
  log "Waiting for TV v3 build..."
  while true; do
    count=$(ssh $SSH_FLAGS $HOST "ls $WORKDIR/data/npz_v4_tv_overlay_v3/ 2>/dev/null | wc -l")
    if [ "$count" -ge "991" ]; then
      log "TV v3 build complete ($count days)"
      return
    fi
    sleep 60
  done
}

wait_for_remote_pid_exit() {
  local pid_pattern=$1
  local label=$2
  log "Waiting for $label to exit (pattern: $pid_pattern)..."
  while true; do
    pid=$(ssh $SSH_FLAGS $HOST "pgrep -f '$pid_pattern' | head -1")
    if [ -z "$pid" ]; then
      log "$label exited."
      return
    fi
    sleep 60
  done
}

launch_track() {
  local config_name=$1
  local log_tag=$2
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
    pgrep -f '${config_name}' | head -1
    echo \"[remote] $log_tag launched, log: $logdir/train.log\"
  "
}

# 1. Wait for TV v3 build
wait_for_build_v3

# 2. Launch Track R
log "Launching Track R (GLU + β-calib + TV v3)"
launch_track "singh_alpha0_huber_track_r.json" "v5push_track_r"
sleep 30  # let process register

# 3. Wait for Track R
wait_for_remote_pid_exit "singh_alpha0_huber_track_r" "Track R"

# 4. Launch Track S (must have config ready by now)
log "Launching Track S (Track R + tail-focal BCE)"
launch_track "singh_alpha0_huber_track_s.json" "v5push_track_s"
sleep 30

# 5. Wait for Track S
wait_for_remote_pid_exit "singh_alpha0_huber_track_s" "Track S"

log "All tracks complete."
