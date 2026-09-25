#!/usr/bin/env bash
# ladder_rev1_arms_combo.sh -- combo layer for revision-1 arms.
# Pre-registration revision 1: docs/PREREG_gap_carrier_ladder_2026-09-25.md @ dd57ac30f
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
S=$EXP/receipts/STEP3_REV1_ARMS_COMBO.tsv
: > $S
echo "PGID $$ $(date -u +%H:%M:%SZ)" > $EXP/logs/rev1_arms.pgid
for ARM in LEGAL_res MEM_res KZ_res_ncfill KZWL_res_ncfill F10_res_ncfill all_new_nclegal; do
  AVAIL=$(df -k /dev/shm | tail -1 | awk "{print \$4}")
  if [ "$AVAIL" -lt 1105920 ]; then
    printf "%s\tSKIPPED_DISK\t%s\n" "$ARM" "$AVAIL" >> $S; break
  fi
  t0=$(date -u +%s)
  if bash $EXP/devices/ladder_arm.sh "$ARM" >> $EXP/logs/rev1_arms.log 2>&1; then
    t1=$(date -u +%s)
    printf "%s\tOK\t%ds\t%s\n" "$ARM" "$((t1-t0))" \
      "$(/workspace/venv/bin/python -c "import json;r=json.load(open(\"$EXP/receipts/LADDER_$ARM.json\"));print(\"lit_pub=%d scaled_pub=%d lit_sha=%s fill=%s\"%(r[\"policies\"][\"literal\"][\"publish_total\"],r[\"policies\"][\"scaled_diagnostic\"][\"publish_total\"],r[\"policies\"][\"literal\"][\"sha\"][:16],r.get(\"cells_filled_with_nc_because_new_had_no_score\")))")" >> $S
  else
    printf "%s\tFAILED\n" "$ARM" >> $S
    echo "$(date -u +%H:%M:%SZ) $ARM FAILED -- STOPPING" >> $EXP/logs/rev1_arms.log
    exit 1
  fi
done
echo "REV1_ARMS_COMBO_DONE $(date -u +%H:%M:%SZ)" >> $EXP/logs/rev1_arms.log
