#!/usr/bin/env bash
# ladder_engine_batch_rev1.sh -- step 3 revision-1 engine queue, ONE CELL AT A TIME.
# Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
# (sha256 893abd37cfa87a0d07457bbdd62a5ccab804579605e1bac73244af1bdcf1ac03).
#
# Queue (7 cells). LEGAL_res and all_new_nclegal are DELIBERATELY ABSENT: both are structural no-ops
# whose combo output is bitwise identical to none / all_new respectively (align_universe absorbs every
# legal difference), so an engine cell would only reproduce a run already in hand.
#
#   MEM_res            lead's new arm -- itself contaminated (King scores incomplete 1486 anchors),
#                      so path-1 reading only: pre-2026 main, 2026 UNAVAILABLE
#   KZ_res KZWL_res F10_res            path-1 main readings (combo already in hand)
#   KZ_res_ncfill KZWL_res_ncfill F10_res_ncfill   lead's path-2 sensitivity
#
# After each cell: lead's supplementary 911-day reading (ex4d) over the SAME paths, then the run dir is
# freed. The memory gate (memory.max - anon - shmem) is measured inside ladder_engine_arm.sh and lands
# in STEP3_MEMGATE_<arm>.json before the engine starts.
#
# Any failure stops the queue (lead: 任一次失败就停下报告, 不自动重试).
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
SRC=/dev/shm/news2_2026-09-23
TAGD=NEWS2_s42_scaled_rule_raw_UAFE
PV=/workspace/venv/bin/python
: > $EXP/receipts/STEP3_DBAR_SUMMARY_REV1.tsv
echo "PGID $$ $(date -u +%H:%M:%SZ)" > $EXP/logs/step3_engine_rev1.pgid

for ARM in MEM_res KZ_res KZWL_res F10_res KZ_res_ncfill KZWL_res_ncfill F10_res_ncfill; do
  echo "$(date -u +%H:%M:%SZ) ==== $ARM START ====" >> $EXP/logs/step3_engine.log
  if ! bash $EXP/devices/ladder_engine_arm.sh "$ARM"; then
    printf "%s\tFAILED\n" "$ARM" >> $EXP/receipts/STEP3_DBAR_SUMMARY_REV1.tsv
    echo "$(date -u +%H:%M:%SZ) $ARM FAILED -- STOPPING QUEUE" >> $EXP/logs/step3_engine.log
    exit 1
  fi
  # lead's supplementary 911-day reading, over the same paths, before the run dir is freed
  if ! $PV -B $EXP/devices/ladder_dbar_ex4d.py --news-devices $SRC/engine \
        --new-dir $EXP/runs/$TAGD --new-tag $TAGD --nc-dir $SRC/runs/$TAGD --nc-tag $TAGD \
        --arm "$ARM" --main-receipt $EXP/receipts/STEP3_DBAR_$ARM.json \
        --out $EXP/receipts/STEP3_DBAR_EX4D_$ARM.json >> $EXP/logs/step3_engine.log 2>&1; then
    printf "%s\tEX4D_FAILED\n" "$ARM" >> $EXP/receipts/STEP3_DBAR_SUMMARY_REV1.tsv
    echo "$(date -u +%H:%M:%SZ) $ARM EX4D FAILED -- STOPPING QUEUE" >> $EXP/logs/step3_engine.log
    exit 1
  fi
  EX=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP3_DBAR_EX4D_$ARM.json'))['supplementary_pre2026_ex4d']['mean_bps_per_day'])")
  PRE=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP3_DBAR_$ARM.json'))['dbar_vs_nc']['pre2026']['mean_bps_per_day'])")
  Y26=$($PV -c "import json;print('%.6f'%json.load(open('$EXP/receipts/STEP3_DBAR_$ARM.json'))['dbar_vs_nc']['2026']['mean_bps_per_day'])")
  HEAD=$($PV -c "import json;print(json.load(open('$EXP/receipts/STEP3_MEMGATE_$ARM.json'))['headroom_GiB'])")
  printf "%s\tOK\tpre2026=%s\t2026=%s\tex4d_911d=%s\theadroom_GiB=%s\n" \
    "$ARM" "$PRE" "$Y26" "$EX" "$HEAD" >> $EXP/receipts/STEP3_DBAR_SUMMARY_REV1.tsv
  rm -rf $EXP/runs/*
  echo "$(date -u +%H:%M:%SZ) ==== $ARM DONE pre2026=$PRE 2026=$Y26 ex4d=$EX (runs freed) ====" >> $EXP/logs/step3_engine.log
done
echo "STEP3_ENGINE_REV1_DONE $(date -u +%H:%M:%SZ)" >> $EXP/logs/step3_engine.log
