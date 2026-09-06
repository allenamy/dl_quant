#!/bin/bash
# run_arm_vc.sh — one w10_volcap.py run under /workspace/review_scratch/tail_aware_sizing (copied from health_check/run_arm.sh; ROOT changed; grep adds VOLCAP_DEF).
# usage: run_arm_vc.sh <TAG> <log|prod> <VOLCAP_GAMMA> <FSEED>
#   caliber log  -> cwd dev/     (meta = wide_fea_v2ext_meta.npz, Σ-simple y4, CAL=log)   caliber prod -> cwd dev_alt/ (meta_newprod, Π(1+r5)-1 over [E+1,E+48], CAL=log)
# Main-arm env verbatim = health_check M1_UPIT_<cal>_s<seed>_ccal (commands.txt 2026-09-05T05:19Z): LEGS=101 CAL=log SLOW_NPY=pinned WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45
#   UMASK_SCOPE=m1 UMASK_NPZ=masks/umask_UPIT.npz COSTB_JSON=calib/costb_fee_steady.json; OMP 4 threads. Every command verbatim -> logs/commands.txt.
TAG=$1; CAL=$2; G=$3; S=$4
ROOT=/workspace/review_scratch/tail_aware_sizing; PY=/workspace/venv/bin/python; HC=/workspace/review_scratch/health_check
case $CAL in log) d=$ROOT/dev ;; prod) d=$ROOT/dev_alt ;; *) echo "bad cal $CAL"; exit 2 ;; esac
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=$S UMASK_SCOPE=m1 UMASK_NPZ=$HC/masks/umask_UPIT.npz COSTB_JSON=$HC/calib/costb_fee_steady.json VOLCAP_GAMMA=$G OUT_TAG=$TAG $PY ../w10_volcap.py"
echo "CMD[$TAG] (cwd=$d) $(date -u +%FT%TZ): $CMD" >> $ROOT/logs/commands.txt
cd $d && $CMD > $d/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
grep -E "^(CONFIG|VOLCAP_DEF|SLOW override|UMASK|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $d/logs/$TAG.log | cut -c1-600
exit $rc
