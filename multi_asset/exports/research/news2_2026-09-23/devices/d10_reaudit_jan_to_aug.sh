#!/usr/bin/env bash
# d10_reaudit_jan_to_aug.sh -- re-run both funding audits over every month that is VERIFIED, Jan..Aug.
#
# Months are NOT hardcoded: the gate decides. A month that is not VERIFIED under the R25-11 gate is left out
# BY NAME, so a partial pull produces a smaller honest table rather than a silent hole -- and the two audits
# always run over the same month set, which is what makes their numbers comparable to each other.
set -u
EXP=/dev/shm/d10_2026-09-25
PY=/workspace/venv/bin/python
MONTHS=""
SKIPPED=""
for M in 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08; do
  V=$(ssh pod2 "$PY -B $EXP/devices/d10_manifest_gate.py $EXP/zips/$M $M 2>/dev/null | head -1" || true)
  case "$V" in
    *" VERIFIED "*) MONTHS="${MONTHS:+$MONTHS,}$M";;
    *) SKIPPED="${SKIPPED:+$SKIPPED }$M(${V:-no-gate-output})";;
  esac
done
echo "months VERIFIED and audited: $MONTHS"
echo "months LEFT OUT by name:     ${SKIPPED:-none}"
[ -n "$MONTHS" ] || { echo "no verified month: nothing to audit"; exit 1; }

echo
echo "########## P2 ledger_full.npz vs archive"
ssh pod2 "cd $EXP && nice -n 10 $PY -B devices/d10_p2_ledger_vs_archive.py \
  --ledger /workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz \
  --ledger-sha bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad \
  --zips-root $EXP/zips --months $MONTHS \
  --out $EXP/receipts/D10_P2_LEDGER_VS_ARCHIVE_full.json" 2>&1 | tail -6

echo
echo "########## legs.npz 9ee5886f RN8 vs archive as-of"
ssh pod2 "cd $EXP && nice -n 10 $PY -B devices/d10_legs_rn8_vs_archive.py \
  --legs /dev/shm/news2_2026-09-23/work/legs.npz --legs-sha 9ee5886f \
  --zips-root $EXP/zips --months $MONTHS \
  --out $EXP/receipts/D10_LEGS_RN8_VS_ARCHIVE.json" 2>&1 | tail -5
