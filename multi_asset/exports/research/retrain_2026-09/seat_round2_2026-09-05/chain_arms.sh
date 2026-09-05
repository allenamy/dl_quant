#!/bin/bash
# chain_arms.sh — seat_round2 step 2: B1..B6 × {prod (dev_alt), log (dev)} × FSEED {42, 2027} = 24 runs, 4 in parallel (OMP 4 threads each).
# Arm switches exactly as PREREG_seat_round2 §1: B1 SEATF10=1 | B2 SEATNET=1 | B3 SEATNET=1 SEATCOST_BPS=2.035 | B4 PHIDYN=1 | B5 SEATF10=1 PHIDYN=1 | B6 SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1
set -u
ROOT=/workspace/review_scratch/seat_round2; cd $ROOT
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz
CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
arm_env() { case $1 in
  B1) echo "SEATF10=1" ;; B2) echo "SEATNET=1" ;; B3) echo "SEATNET=1 SEATCOST_BPS=2.035" ;; B4) echo "PHIDYN=1" ;;
  B5) echo "SEATF10=1 PHIDYN=1" ;; B6) echo "SEATNET=1 SEATCOST_BPS=2.035 SEATF10=1 PHIDYN=1" ;; *) echo "BAD"; return 1 ;; esac; }
JOBS=()
for arm in B1 B2 B3 B4 B5 B6; do for cal in prod log; do for s in 42 2027; do
  JOBS+=("$arm $cal $s")
done; done; done
echo "ARMS_START n=${#JOBS[@]} $(date -u +%FT%TZ)" >> logs/chain_arms.log
i=0
for job in "${JOBS[@]}"; do
  set -- $job; arm=$1; cal=$2; s=$3
  bash run_arm.sh ${arm}_${cal}_s${s} $cal w10_seat2.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB $(arm_env $arm) > logs/${arm}_${cal}_s${s}.out 2>&1 &
  i=$((i+1))
  if [ $((i % 4)) = 0 ]; then wait; fi
done
wait
grep -c "rc=0" logs/commands.txt >> logs/chain_arms.log
sha256sum dev/probe_artifacts/w10_ablation_series_B*.npz dev_alt/probe_artifacts/w10_ablation_series_B*.npz >> logs/chain_arms.log
echo "CHAIN_ARMS_DONE $(date -u +%FT%TZ)" >> logs/chain_arms.log
