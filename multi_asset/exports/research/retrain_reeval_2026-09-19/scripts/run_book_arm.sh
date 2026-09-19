#!/bin/bash
# run_book_arm.sh — one real-cost replay of one book arm (PREREG_retrain_reeval_corrected_pipeline_2026-09-19 §3), same cfg as
# /workspace/fp2_2026-09/realcost/run_realcost.sh (the A1 receipts of PER_YEAR_TABLE_REALCOST_2026-09-17): the COMMON words verbatim, only
# SLOW_NPY / FPRED / FSEED name this arm's prediction files. The runner is the chain device copy of run_arm.sh (executed, not modified);
# RUN_ARM_ROOT = this stream's private tree, so every write lands under /workspace/retrain_reeval_2026-09-19/hc.
# usage: run_book_arm.sh <ARM> <SEED> <SLOW_NPY abs path> <FPRED basename in hc/dev_v4/f8_2026-08-22/preds>
A=$1; s=$2; SLOW=$3; FP=$4; W=/workspace/retrain_reeval_2026-09-19; H=$W/hc; D=/workspace/fp2_2026-09/devices_v4chain
UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
export RUN_ARM_ROOT=$H RUN_ARM_PY=/workspace/venv/bin/python
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=/workspace/fp2_2026-09/realcost/costb_fee_real_0907.json"
[ -f "$SLOW" ] || { echo "missing SLOW $SLOW"; exit 3; }; [ -f "$H/dev_v4/f8_2026-08-22/preds/$FP" ] || { echo "missing FPRED $FP"; exit 3; }
bash $D/run_arm.sh V4_${A}_dyn_s${s} v4 w10_health.py $COMMON SLOW_NPY=$SLOW FSEED=$s FPRED=$FP; rc=$?
mkdir -p $W/arms; [ $rc -eq 0 ] && cp $H/dev_v4/probe_artifacts/w10_ablation_series_V4_${A}_dyn_s${s}.npz $W/arms/w10_ablation_series_V4_${A}_dyn_s${s}.npz
echo "BOOK_ARM[$A s$s] rc=$rc $(date -u +%FT%TZ)" >> $W/logs/commands.txt
exit $rc
