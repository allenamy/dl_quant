#!/bin/bash
# run_iso2.sh <tag> <cal> <seed> <cost> <extra env...>
# 通用孤立臂运行器: 与既有 M1_UPIT 逐字相同, 只覆盖传入的旋钮。PREREG §5.2 B1 功效补全。
set -e
TAG=$1; CAL=$2; SEED=$3; COST=$4; shift 4; EXTRA="$@"
H=/workspace/review_scratch/health_check
d=$H/dev; [ "$CAL" = prod ] && d=$H/dev_alt
CB=""; [ "$COST" = ccal ] && CB="COSTB_JSON=$H/calib/costb_fee_steady.json"
OT=${TAG}_${CAL}_s${SEED}_${COST}
CMD="env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=$SEED UMASK_NPZ=$H/masks/umask_UPIT.npz $CB $EXTRA OUT_TAG=$OT /workspace/venv/bin/python ../w10_health.py"
mkdir -p $H/logs_iso2
echo "CMD[$OT] (cwd=$d) $(date -u +%Y-%m-%dT%H:%M:%SZ): $CMD" >> $H/logs_iso2/commands.txt
cd $d
$CMD > $H/logs_iso2/$OT.log 2>&1 &
P=$!; PEAK=0
while kill -0 $P 2>/dev/null; do R=$(ps -o rss= -p $P 2>/dev/null | tr -d " "); [ -n "$R" ] && [ "$R" -gt "$PEAK" ] && PEAK=$R; sleep 3; done
wait $P; RC=$?
echo "END[$OT] rc=$RC peak_rss_GB=$(echo $PEAK | awk "{printf \"%.2f\", \$1/1048576}") $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $H/logs_iso2/commands.txt
