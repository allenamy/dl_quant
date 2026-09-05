#!/bin/bash
# run_arm.sh — one device run under review_scratch/f10_caliber (PREREG_f10_caliber_sensitivity_2026-09-05 §2). Copied from health_check/run_arm.sh; ROOT changed, third caliber added.
# usage: run_arm.sh <TAG> <log|prod|sum1> <DEVICE_FILE (relative to f10_caliber/)> <ENV assignments...>
#   log  -> cwd dev/      (meta = /workspace/data/wide_fea_v2ext_meta.npz = label (i) Σ-simple [E,E+47], CAL=log = no transform)
#   prod -> cwd dev_alt/  (meta = refute_C6_2/altrun/meta_newprod.npz = label (iii) Π(1+r5)−1 [E+1,E+48], CAL=log)
#   sum1 -> cwd dev_alt2/ (meta = f10_caliber/meta/meta_newsum_f10cal.npz = label (ii) Σ-simple [E+1,E+48], CAL=log)
# Every command is appended verbatim to logs/commands.txt; stdout/stderr -> <cwd>/logs/<TAG>.log; artifact -> <cwd>/probe_artifacts/w10_ablation_series_<TAG>.npz
TAG=$1; CAL=$2; DEV=$3; shift 3
[ -n "$DEV" ] || { echo "usage: run_arm.sh <TAG> <log|prod|sum1> <DEVICE_FILE> <ENV...>"; exit 2; }
ROOT=/workspace/review_scratch/f10_caliber; PY=/workspace/venv/bin/python
case $CAL in log) d=$ROOT/dev ;; prod) d=$ROOT/dev_alt ;; sum1) d=$ROOT/dev_alt2 ;; *) echo "bad cal $CAL"; exit 2 ;; esac
[ -f "$ROOT/$DEV" ] || { echo "missing device $ROOT/$DEV"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=$TAG $PY ../$DEV"
echo "CMD[$TAG] (cwd=$d) $(date -u +%FT%TZ): $CMD" >> $ROOT/logs/commands.txt
cd $d && $CMD > $d/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
grep -E "^(CONFIG|SLOW override|F10 OOS|F10 leg|MEMBERS_TOPN|UMASK|COSTB|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError|NOTE)" $d/logs/$TAG.log | cut -c1-700
exit $rc
