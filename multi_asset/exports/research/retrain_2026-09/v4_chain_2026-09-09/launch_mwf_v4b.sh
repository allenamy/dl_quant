#!/bin/bash
# launch_mwf_v4b.sh — PREREG_v4 §2.4: one shard of one (TARGET, SEED) chain. usage: launch_mwf_v4b.sh <TARGET: RAW|CLIP> <SEED: 42|2027> <shard> <MONTHS csv>
# monthly (2026-09-12, RUNBOOK_2026-10 §0★ 修订 2 (c)): every locator comes from the month env exported by chain_lib.load_month_env (V4_D device dir,
# V4_DLW_RAW / V4_DLW_CLIP / V4_F8 / V4_BASE_TRAINER, MONTHS_ALL); every default equals the September constant, so a call without the month env
# behaves exactly as the September launcher did (bit-identical command line up to the added V4_* / MONTHS_ALL words, which the trainer only records).
T=$1; SD=$2; K=$3; M=$4; B=${V4_D:-/workspace/review_scratch}; PY=${PY:-/workspace/venv/bin/python}; F8=${V4_F8:-/workspace/f8_v4}; cd $B || exit 2
case $T in RAW) DLW=${V4_DLW_RAW:-/workspace/dlw_v4raw} ;; CLIP) DLW=${V4_DLW_CLIP:-/workspace/dlw_hf3} ;; *) echo "bad target $T"; exit 2 ;; esac
case $SD in 42|2027) ;; *) echo "bad seed $SD"; exit 2 ;; esac
[ -n "$M" ] || { echo "empty MONTHS for shard $K"; exit 2; }
O=$F8/${MWF_ROOT:-mwf}/${T}_s${SD}/shard$K; mkdir -p $O $F8/logs
CMD="env ARM=V2MAIN V2=1 SEED=$SD F10_DLW=$DLW F10_OUT=$F8 F10_GATE_JSON=$F8/gates/F10_GATE_$T.json MWF_OUT=$O EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 MONTHS=$M ${MONTHS_ALL:+MONTHS_ALL=$MONTHS_ALL} V4_DLW_RAW=${V4_DLW_RAW:-/workspace/dlw_v4raw} V4_DLW_CLIP=${V4_DLW_CLIP:-/workspace/dlw_hf3} V4_F8=$F8 V4_BASE_TRAINER=${V4_BASE_TRAINER:-/workspace/pod_f10_train_ext.py} ${V4_MONTH:+V4_MONTH=$V4_MONTH} ${V4_MONTH_ENV:+V4_MONTH_ENV=$V4_MONTH_ENV} $PY $B/pod_f10_train_monthly_v4.py"
T0=$(date +%s); echo "CMD[$T s$SD shard$K] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader 2>/dev/null || echo n/a) : $CMD" >> $F8/logs/commands.txt
$CMD > $F8/logs/train_${T}_s${SD}_shard$K.log 2>&1 & P=$!; echo "PID[$T s$SD shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> $F8/logs/commands.txt; wait $P; rc=$?
echo "END[$T s$SD shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE $F8/logs/train_${T}_s${SD}_shard$K.log)" >> $F8/logs/commands.txt
exit $rc
