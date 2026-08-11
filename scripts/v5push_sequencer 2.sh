#!/bin/bash
# Overnight sequencer: Track A → Track E → Track G.
# Polls Track A pid; when it exits, promotes Track E code + launches; when E exits, launches G.
# Runs locally — issues SSH commands to remote.

set -e
SSH_FLAGS="-o ConnectTimeout=10 -o ServerAliveInterval=30 -p 31999"
HOST="root@212.50.244.62"
WORKDIR="/mnt/storage/private/work_hsy/quant_research"
ENV="hsy_v5push"

wait_for_pid_exit() {
  local pid=$1
  local label=$2
  echo "[seq] Waiting for $label (pid $pid) to exit..."
  while ssh $SSH_FLAGS $HOST "kill -0 $pid 2>/dev/null"; do
    sleep 60
  done
  echo "[seq] $label exited."
}

launch_remote() {
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
    sleep 2
    pgrep -f 'configs/v5push/${config_name}' | head -1
    echo \"[remote] $log_tag log: $logdir/train.log\"
  "
}

promote_track_e() {
  ssh $SSH_FLAGS $HOST "
    cd $WORKDIR &&
    cp /tmp/v5push_tracke_sync/dual_path_model_v3.py src/model/dual_path_model_v3.py &&
    cp /tmp/v5push_tracke_sync/conformer_backbone.py src/model/backbones/conformer_backbone.py &&
    cp /tmp/v5push_tracke_sync/run_pipeline_v3.py run_pipeline_v3.py &&
    echo '[remote] Promoted Track E code files.'
  "
}

# Initial state: Track A is running, pid 21369
TRACK_A_PID=21369
wait_for_pid_exit $TRACK_A_PID "Track A (DAQH+TV)"

# Promote Track E code
promote_track_e

# Launch Track E
echo "[seq] Launching Track E (MRP)"
TRACK_E_PID=$(launch_remote "singh_alpha0_huber_mrp.json" "v5push_mrp" | grep -E '^[0-9]+$' | head -1)
echo "[seq] Track E PID: $TRACK_E_PID"

# Wait for Track E
wait_for_pid_exit $TRACK_E_PID "Track E (MRP)"

# Launch Track G (MRP + TV)
echo "[seq] Launching Track G (MRP+TV)"
TRACK_G_PID=$(launch_remote "singh_alpha0_huber_mrp_tv.json" "v5push_mrp_tv" | grep -E '^[0-9]+$' | head -1)
echo "[seq] Track G PID: $TRACK_G_PID"

wait_for_pid_exit $TRACK_G_PID "Track G (MRP+TV)"
echo "[seq] All tracks complete."
