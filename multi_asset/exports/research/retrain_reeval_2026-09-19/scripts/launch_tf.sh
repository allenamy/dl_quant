#!/bin/bash
# launch_tf.sh — PREREG_retrain_reeval_corrected_pipeline_2026-09-19 (9b403aad) stream T: one shard of one F10 arm.
# usage: launch_tf.sh <ARM tag dir> <SEED 42|2027> <TRAIN_FRAC 0.85|1.0> <shard> <MONTHS csv>
# The env is the A1 command line of the FP2-8 chain (/workspace/fp2_2026-09/f8_v4/logs/commands.txt, 2026-09-17T10:45:22Z) word for word, except:
#   MWF_OUT -> under /workspace/retrain_reeval_2026-09-19/mwf (the only write location), MONTHS -> this shard, + TRAIN_FRAC, trainer -> the research copy.
# Inputs (read-only): /workspace/fp2_2026-09/{dlw_v4raw,f8_v4} = the A1 training inputs (F10_GATE_RAW.json identity gate asserted by the trainer).
set -u
A=$1; SD=$2; TF=$3; K=$4; M=$5; W=/workspace/retrain_reeval_2026-09-19; PY=/workspace/venv/bin/python; R=/workspace/fp2_2026-09
case $SD in 42|2027) ;; *) echo "bad seed $SD"; exit 2 ;; esac
case $TF in 0.85|1.0) ;; *) echo "bad TRAIN_FRAC $TF"; exit 2 ;; esac
[ -n "$M" ] || { echo "empty MONTHS"; exit 2; }
O=$W/mwf/${A}_s${SD}/shard$K; mkdir -p $O $W/logs
CMD="env ARM=V2MAIN V2=1 SEED=$SD F10_DLW=$R/dlw_v4raw F10_OUT=$R/f8_v4 F10_GATE_JSON=$R/f8_v4/gates/F10_GATE_RAW.json MWF_OUT=$O EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 MONTHS=$M MONTHS_ALL=202501,202502,202503,202504,202505,202506,202507,202508,202509,202510,202511,202512,202601,202602,202603,202604,202605,202606,202607,202608 V4_DLW_RAW=$R/dlw_v4raw V4_DLW_CLIP=$R/dlw_hf3 V4_F8=$R/f8_v4 V4_BASE_TRAINER=/workspace/pod_f10_train_ext.py V4_MONTH=2026-09 V4_MONTH_ENV=$R/v4_month_2026-09_fp2.env TRAIN_FRAC=$TF $PY $W/device/pod_f10_train_monthly_v4_tf.py"
T0=$(date +%s); echo "CMD[$A s$SD shard$K] $(date -u +%FT%TZ) pgid=$(ps -o pgid= $$ | tr -d ' ') gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) cg_mem=$(cat /sys/fs/cgroup/memory.current) : $CMD" >> $W/logs/commands.txt
$CMD > $W/logs/train_${A}_s${SD}_shard$K.log 2>&1 & P=$!; echo "PID[$A s$SD shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> $W/logs/commands.txt; wait $P; rc=$?
echo "END[$A s$SD shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE $W/logs/train_${A}_s${SD}_shard$K.log)" >> $W/logs/commands.txt
exit $rc
