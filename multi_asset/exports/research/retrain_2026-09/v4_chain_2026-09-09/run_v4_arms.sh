#!/bin/bash
# run_v4_arms.sh — PREREG_v4 §2.5 book-layer arms on the dev_v4 tree (RAW accounting). usage: run_v4_arms.sh <ARM: A0|A0p|A1|A1s|A1e|A2|A3> [seeds="42 2027"]
# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (c); review R3 step 6): the dev tree and the king SLOW files are locators from the month env
# (V4_HC / V4_KING_DIR; defaults = the September constants), and every arm process is waited on BY PID with its rc collected — the old bare
# `wait; grep ... | tail -4` could read a previous run's END lines as this run's result. Non-zero rc of any arm ⇒ exit 1 (no silent success).
ARM=$1; SEEDS=${2:-"42 2027"}; H=${V4_HC:-/workspace/review_scratch/health_check}; KD=${V4_KING_DIR:-/workspace/review_scratch/king_v4}; cd $H || exit 2
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json; K3=$KD/SLOW_v3_on_v4axis.npy; K4=$KD/SLOW_v4.npy; K4E=$KD/SLOW_v4e.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
pids=(); names=()
for s in $SEEDS; do
  case $ARM in A0) SL=$K3; FP=f10_A0_s$s.npy ;; A1) SL=$K4; FP=f10_v4RAW_s$s.npy ;; A2) SL=$K4; FP=f10_v4CLIP_s$s.npy ;; A3) SL=$K4; FP=f10_A0_s$s.npy ;; A1s) SL=$K4; FP=f10_v4sRAW_s$s.npy ;; A1e) SL=$K4E; FP=f10_v4RAW_s$s.npy ;; *) echo "bad arm $ARM"; exit 2 ;; esac
  [ -f $H/dev_v4/f8_2026-08-22/preds/$FP ] || { echo "missing FPRED $FP"; exit 3; }
  [ -f $SL ] || { echo "missing SLOW $SL"; exit 3; }
  bash run_arm.sh V4_${ARM}_dyn_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP > $H/dev_v4/logs/V4_${ARM}_dyn_s$s.out 2>&1 & pids+=($!); names+=("dyn_s$s")
  bash run_arm.sh V4_${ARM}_fix_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP W3FIX=0.21,0,0.79 > $H/dev_v4/logs/V4_${ARM}_fix_s$s.out 2>&1 & pids+=($!); names+=("fix_s$s")
done
rcs=(); k=0; bad=0
for p in "${pids[@]}"; do wait $p; rc=$?; rcs+=($rc); [ $rc -eq 0 ] || bad=1; echo "arm V4_${ARM}_${names[$k]} pid $p rc=$rc"; k=$((k + 1)); done
echo "ARMS ${ARM} seeds [$SEEDS] rc=[${rcs[*]}]"
grep -a -E "^END\[V4_${ARM}_" $H/logs/commands.txt | tail -$(( ${#pids[@]} ))
[ $bad -eq 0 ] || { echo "ARMS_FAIL ${ARM} rc=[${rcs[*]}]"; exit 1; }
echo "ARMS_DONE ${ARM}"
