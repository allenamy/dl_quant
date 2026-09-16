#!/bin/bash
set -uo pipefail
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02
TREE=/Users/haosiyu/cc_tmp/fx_exec
RUN1=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EXEC/receipts/common/run1.sh
VF="$TREE/live/venue_fills.py"; BF="$TREE/ops/backfill_fills.py"
echo "### PART 1 — FINAL red on OLD code, with the SHIPPED test file"
cp "$VF" "$W/.vf.f"; cp "$BF" "$W/.bf.f"
git -C "$TREE" checkout -- live/venue_fills.py ops/backfill_fills.py
bash "$RUN1" "$TREE" live/tests_flatten_fee_backfill.py "$W/N2_red_FINALTESTS_oldcode.log"; echo "old-code rc=$?"
grep -cE '^  FAIL' "$W/N2_red_FINALTESTS_oldcode.log" | sed 's/^/red_cells=/'
grep -E 'checks passed' "$W/N2_red_FINALTESTS_oldcode.log"
grep -cE 'Traceback' "$W/N2_red_FINALTESTS_oldcode.log" | sed 's/^/tracebacks=/'
cp "$W/.vf.f" "$VF"; cp "$W/.bf.f" "$BF"; rm -f "$W/.vf.f" "$W/.bf.f"
echo "### PART 2 — mutants (all 9) on the shipped test file"
bash "$W/mutants.sh"
echo "### PART 3 — green re-confirm"
bash "$RUN1" "$TREE" live/tests_flatten_fee_backfill.py "$W/N2_green_FIXED.log"; echo "fixed rc=$?"
tail -2 "$W/N2_green_FIXED.log"
echo "### clone source status"
git -C "$TREE" status --porcelain -- . ':(exclude)state'
