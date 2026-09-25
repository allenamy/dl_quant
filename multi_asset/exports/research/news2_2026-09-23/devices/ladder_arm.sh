#!/usr/bin/env bash
# ladder_arm.sh <arm>  -- step 3 one arm through the UNCHANGED evolve.
# Pre-registration: docs/PREREG_gap_carrier_ladder_2026-09-25.md (be4a013a8), step 3 (lead's criteria).
set -uo pipefail
ARM="$1"
EXP=/dev/shm/pnoise_2026-09-24
NEWR=/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d
nice -n 10 /workspace/venv/bin/python -B $EXP/devices/pnoise_ladder_combo.py \
  --arm "$ARM" \
  --devices    $EXP/devices \
  --nc-legs    /dev/shm/news2_2026-09-23/work/legs.npz \
  --nc-f10     /dev/shm/news2_2026-09-23/work/f10_s42/F10_OOF.npz \
  --new-legs   $NEWR/data/f10v2_legs.npz \
  --new-f10    $NEWR/f10_s42/F10_OOF.npz \
  --new-funding $NEWR/data/funding_state.npz \
  --new-targets $NEWR/data/dlw_targets.npz \
  --features   /dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz \
  --mask       /workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz \
  --crypto-axis $EXP/receipts/P1_members_2025H2on.npz \
  --config     $EXP/inputs/bundle_config.json \
  --out-dir    $EXP/work/ladder_$ARM \
  --receipt    $EXP/receipts/LADDER_$ARM.json
rc=$?
echo "LADDER_ARM_EXIT arm=$ARM rc=$rc"
exit $rc
