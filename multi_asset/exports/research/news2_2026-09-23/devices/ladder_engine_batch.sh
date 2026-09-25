#!/usr/bin/env bash
# ladder_engine_batch.sh -- step 3 engine layer, ONLY the arms that are free of the coverage artifact.
# Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3.
#
# Order is deliberate, controls first:
#   none     ENGINE RED CONTROL   -- combo is bitwise the archived NC combo, so dbar vs NC must be 0
#   all_new  ENGINE POSITIVE CTL  -- combo is bitwise NEW's, so dbar vs NC must reproduce the known gap
#   WL_res   arm (no novel refusal reason)
#   FUND_res arm (no novel refusal reason)
#
# KZ_res / KZWL_res / F10_res are DELIBERATELY NOT RUN: they emit a refusal reason neither end can
# emit ('King scores incomplete' on 1486 anchors; scaled 'F10 coverage' on 744), because NEW's KZ/P
# is NaN on exactly the names NEW's member screen excludes (42889 cells, 100% of them absent from
# NEW's member set). Their 2026 book is 93% blanked by the swap itself. Awaiting lead's ruling.
set -uo pipefail
EXP=/dev/shm/pnoise_2026-09-24
: > $EXP/receipts/STEP3_DBAR_SUMMARY.tsv
echo "PGID $$ $(date -u +%H:%M:%SZ)" > $EXP/logs/step3_engine.pgid
for ARM in none all_new WL_res FUND_res; do
  if ! bash $EXP/devices/ladder_engine_arm.sh "$ARM"; then
    printf "%s\tFAILED\t-\t-\n" "$ARM" >> $EXP/receipts/STEP3_DBAR_SUMMARY.tsv
    echo "$(date -u +%H:%M:%SZ) $ARM FAILED -- STOPPING (lead: 不自动重试)" >> $EXP/logs/step3_engine.log
    exit 1
  fi
done
echo "STEP3_ENGINE_DONE $(date -u +%H:%M:%SZ)" >> $EXP/logs/step3_engine.log
