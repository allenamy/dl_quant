#!/usr/bin/env bash
# pnoise_step2_driver.sh -- step 2: refit arms (a) and (b) through the full pipeline, then dbar.
# Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 2 (lead's criteria).
# Stops on the first failure. Frees each arm's engine outputs after the dbar receipt is written.
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
PV=/workspace/venv/bin/python
TAGD=NEWS2_s42_scaled_rule_raw_UAFE
NCRUN=/dev/shm/news2_2026-09-23/runs/$TAGD
S=$EXP/receipts/STEP2_SUMMARY.tsv
: > $S

for ARM in a b; do
  t0=$(date -u +%s)
  echo "=== $(date -u +%H:%M:%S) ARM $ARM START ===" >> $EXP/logs/step2.log
  # Build the arm's KING_OOF from the archived structure with P replaced, so every key the
  # downstream devices expect is present (they read P, but the file must look like a KING_OOF).
  rm -rf $EXP/work/king; mkdir -p $EXP/work/king
  $PV - "$ARM" <<'PY' >> $EXP/logs/step2.log 2>&1
import numpy as np, sys
arm=sys.argv[1]
A=np.load("/dev/shm/news2_2026-09-23/work/king/KING_OOF.npz", allow_pickle=False)
B=np.load(f"/dev/shm/pnoise_2026-09-24/work/refit_p/REFIT_P_{arm}.npz", allow_pickle=False)
assert A["P"].shape==B["P"].shape, (A["P"].shape, B["P"].shape)
assert (A["E_ts"]==B["E_ts"]).all() and (A["symbols"]==B["symbols"]).all()
out={k:(np.asarray(B["P"]) if k=="P" else np.asarray(A[k])) for k in A.files}
np.savez("/dev/shm/pnoise_2026-09-24/work/king/KING_OOF.npz", **out)
print("arm", arm, "KING_OOF built; keys", sorted(out))
PY
  if ! bash $EXP/devices/pnoise_run_from_king.sh "refit_$ARM" >> $EXP/logs/step2.log 2>&1; then
    printf "%s\tCHAIN_FAILED\t-\t-\n" "$ARM" >> $S
    echo "ARM $ARM CHAIN FAILED -- STOPPING" >> $EXP/logs/step2.log
    exit 1
  fi
  if ! $PV -B $EXP/devices/pnoise_dbar.py --news-devices /dev/shm/news2_2026-09-23/engine \
       --new-dir $EXP/runs/$TAGD --new-tag $TAGD --nc-dir $NCRUN --nc-tag $TAGD \
       --random-state "refit_$ARM" --out $EXP/receipts/STEP2_DBAR_$ARM.json >> $EXP/logs/step2.log 2>&1; then
    printf "%s\tDBAR_FAILED\t-\t-\n" "$ARM" >> $S
    exit 1
  fi
  PRE=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP2_DBAR_$ARM.json'))['dbar_vs_nc']['pre2026']['mean_bps_per_day'])")
  Y26=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP2_DBAR_$ARM.json'))['dbar_vs_nc']['2026']['mean_bps_per_day'])")
  t1=$(date -u +%s)
  printf "%s\tOK\t%s\t%s\t%dmin\n" "$ARM" "$PRE" "$Y26" "$(( (t1-t0)/60 ))" >> $S
  rm -rf $EXP/runs/*
  echo "=== $(date -u +%H:%M:%S) ARM $ARM DONE pre2026=$PRE 2026=$Y26 ===" >> $EXP/logs/step2.log
done
echo "STEP2_ALL_DONE" >> $EXP/logs/step2.log
