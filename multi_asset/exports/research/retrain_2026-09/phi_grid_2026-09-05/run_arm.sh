#!/bin/bash
# run_arm.sh — one device run under review_scratch/phi_grid (PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §B). Copied from f10_caliber/run_arm.sh; ROOT changed; prod layout only.
# usage: run_arm.sh <TAG> <prod> <DEVICE_FILE (relative to phi_grid/)> <ENV assignments...>
#   prod -> cwd dev_alt/ (meta = refute_C6_2/altrun/meta_newprod.npz = label (iii) Π(1+r5)−1 [E+1,E+48] = dlw y4s, CAL=log = no transform)
# Every command is appended verbatim to logs/commands.txt; stdout/stderr -> <cwd>/logs/<TAG>.log; artifact -> <cwd>/probe_artifacts/w10_ablation_series_<TAG>.npz
TAG=$1; CAL=$2; DEV=$3; shift 3
[ -n "$DEV" ] || { echo "usage: run_arm.sh <TAG> <prod> <DEVICE_FILE> <ENV...>"; exit 2; }
ROOT=/workspace/review_scratch/phi_grid; PY=/workspace/venv/bin/python
case $CAL in prod) d=$ROOT/dev_alt ;; *) echo "bad cal $CAL (phi_grid runs the accounting caliber (iii) only)"; exit 2 ;; esac
[ -f "$ROOT/$DEV" ] || { echo "missing device $ROOT/$DEV"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=$TAG $PY ../$DEV"
echo "CMD[$TAG] (cwd=$d) $(date -u +%FT%TZ): $CMD" >> $ROOT/logs/commands.txt
cd $d && $CMD > $d/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
grep -E "^(CONFIG|SLOW override|F10 OOS|F10 leg|MEMBERS_TOPN|UMASK|COSTB|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError|NOTE)" $d/logs/$TAG.log | cut -c1-700
exit $rc
