#!/bin/bash
# s2_chain.sh — S2 (book level) for an S1-admitted family: the device king with the new columns replaces the pinned king in the health-check
# main-arm form (rider device copy with SPOTSUP_B=0 == w10_health.py bitwise, identity receipts rider_identity_b0_s*.json), prod caliber,
# paired against the same device's BASE king (same seed), 2024->26 per gross, UTC-day-block bootstrap 2000 seed 20260905, RULE=s2
# (CI lower > 0 AND turnover <= +25%). usage: s2_chain.sh <ARM (A1|A1A2)> <seed list e.g. "42 2027">
set -u
ROOT=/workspace/review_scratch/allweather_trackA; PY=/workspace/venv/bin/python; ARM=$1; SEEDS=$2; DEV=${3:-dev_alt}; SFX=${4:-}
# DEV = dev_alt (prod caliber, meta_newprod y4 = Π(1+r)-1 over the meta window) | dev_exec (secondary caliber: meta_exec25 y4 over rows E+6..E+48)
cd $ROOT
echo "S2_CHAIN_START $ARM $DEV $(date -u +%FT%TZ)" >> logs/chain.log
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade SPOTSUP_B=0"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz; CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
for s in $SEEDS; do for k in BASE $ARM; do
  TAG=S2${SFX}_${k}_s${s}; NPY=$ROOT/results/preds/pred_${k}_s${s}.npy
  [ "$k" = BASE ] && [ -f $ROOT/rider/$DEV/probe_artifacts/w10_ablation_series_$TAG.npz ] && continue   # BASE replay shared across arms
  CMD="env $COMMON SLOW_NPY=$NPY FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB OUT_TAG=$TAG $PY ../w10_health_spotsup.py"
  echo "CMD[$TAG] (cwd=$ROOT/rider/$DEV) $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
  (cd $ROOT/rider/$DEV && $CMD > $ROOT/rider/$DEV/logs/$TAG.log 2>&1; echo "END[$TAG] rc=$? $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt) &
done; done
wait
for s in $SEEDS; do
  echo "CMD[s2${SFX}_paired_${ARM}_s${s}] $(date -u +%FT%TZ): RULE=s2 s2_paired_delta.py S2${SFX}_BASE_s${s} S2${SFX}_${ARM}_s${s} ($DEV)" >> logs/commands.txt
  RULE=s2 $PY scripts/s2_paired_delta.py rider/$DEV/probe_artifacts/w10_ablation_series_S2${SFX}_BASE_s${s}.npz rider/$DEV/probe_artifacts/w10_ablation_series_S2${SFX}_${ARM}_s${s}.npz results/s2${SFX}_paired_${ARM}_s${s}.json > logs/s2${SFX}_paired_${ARM}_s${s}.log 2>&1
  grep -E "SLOW override|RECEIPT_EX|Traceback|Assertion" rider/$DEV/logs/S2${SFX}_BASE_s${s}.log rider/$DEV/logs/S2${SFX}_${ARM}_s${s}.log | cut -c1-300
  cat logs/s2${SFX}_paired_${ARM}_s${s}.log
done
sha256sum results/s2${SFX}_paired_${ARM}_s*.json rider/$DEV/probe_artifacts/w10_ablation_series_S2${SFX}_*.npz >> logs/SHA256SUMS_S2.txt
echo "S2_CHAIN_DONE $ARM $DEV $(date -u +%FT%TZ)" >> logs/chain.log
