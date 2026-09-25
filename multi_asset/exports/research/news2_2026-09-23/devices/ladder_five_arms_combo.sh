#!/usr/bin/env bash
# ladder_five_arms_combo.sh -- step 3: combo layer for lead's five single-swap arms (verbatim list).
# Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3.
# Combo layer only; the engine base cell is a separate step so lead can rule on the coverage hole first.
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
S=$EXP/receipts/STEP3_ARMS_COMBO.tsv
: > $S
echo "PGID $$ $(date -u +%H:%M:%SZ)" > $EXP/logs/step3_arms.pgid
for ARM in KZ_res WL_res F10_res FUND_res KZWL_res; do
  AVAIL=$(df -k /dev/shm | tail -1 | awk '{print $4}')
  if [ "$AVAIL" -lt 1105920 ]; then          # 55 MiB arm + 1.0 GiB margin, measured before each arm
    printf "%s\tSKIPPED_DISK\t%s\t-\n" "$ARM" "$AVAIL" >> $S
    echo "$(date -u +%H:%M:%SZ) $ARM SKIPPED: only ${AVAIL}K free" >> $EXP/logs/step3_arms.log
    break
  fi
  t0=$(date -u +%s)
  if bash $EXP/devices/ladder_arm.sh "$ARM" >> $EXP/logs/step3_arms.log 2>&1; then
    t1=$(date -u +%s)
    printf "%s\tOK\t%ds\t%s\n" "$ARM" "$((t1-t0))" \
      "$(/workspace/venv/bin/python -c "import json;r=json.load(open('$EXP/receipts/LADDER_$ARM.json'));print('lit_pub=%d scaled_pub=%d lit_sha=%s'%(r['policies']['literal']['publish_total'],r['policies']['scaled_diagnostic']['publish_total'],r['policies']['literal']['sha'][:16]))")" >> $S
  else
    printf "%s\tFAILED\t-\t-\n" "$ARM" >> $S
    echo "$(date -u +%H:%M:%SZ) $ARM FAILED -- STOPPING" >> $EXP/logs/step3_arms.log
    exit 1
  fi
done
echo "STEP3_ARMS_COMBO_DONE $(date -u +%H:%M:%SZ)" >> $EXP/logs/step3_arms.log
