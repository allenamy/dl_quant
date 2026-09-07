#!/bin/bash
# run_ftrim_iso.sh <cal:log|prod> <seed> <cost:ccal|cdef>
# FTRIM 孤立臂: 与既有 M1_UPIT_<cal>_s<seed>_<cost> 逐字相同, 只改 FTRIM=zero -> off。
# PREREG_king_window_ftrim_cap_2026-09-07 §5.2 B1。只写 health_check/ 下, 输入只读。
set -e
CAL=$1; SEED=$2; COST=$3
H=/workspace/review_scratch/health_check
d=$H/dev; [ "$CAL" = prod ] && d=$H/dev_alt
CB=""; [ "$COST" = ccal ] && CB="COSTB_JSON=$H/calib/costb_fee_steady.json"
TAG=NOFTRIM_M1_UPIT_${CAL}_s${SEED}_${COST}
CMD="env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=off PHI=0.45 FSEED=$SEED UMASK_SCOPE=m1 UMASK_NPZ=$H/masks/umask_UPIT.npz $CB OUT_TAG=$TAG /workspace/venv/bin/python ../w10_health.py"
mkdir -p $H/logs_ftrim
echo "CMD[$TAG] (cwd=$d) $(date -u +%Y-%m-%dT%H:%M:%SZ): $CMD" >> $H/logs_ftrim/commands.txt
cd $d
$CMD > $H/logs_ftrim/$TAG.log 2>&1 &
P=$!
PEAK=0
while kill -0 $P 2>/dev/null; do
  R=$(ps -o rss= -p $P 2>/dev/null | tr -d " "); [ -n "$R" ] && [ "$R" -gt "$PEAK" ] && PEAK=$R
  sleep 3
done
wait $P; RC=$?
echo "END[$TAG] rc=$RC peak_rss_GB=$(echo $PEAK | awk "{printf \"%.2f\", \$1/1048576}") $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $H/logs_ftrim/commands.txt
