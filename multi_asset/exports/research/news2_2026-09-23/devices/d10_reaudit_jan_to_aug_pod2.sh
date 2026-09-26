#!/usr/bin/env bash
# d10_reaudit_jan_to_aug_pod2.sh -- rev 1 of d10_reaudit_jan_to_aug.sh (4239158b9), run ENTIRELY on pod2 under setsid.
#
# What changed vs rev 0 and why:
#  * runs on pod2 as one detached process (rev 0 ran each audit in an ssh session's foreground -- the same shape that
#    killed the May-July pull at 2026-09-25T18:51:08Z, rc 255);
#  * the legs audit gets --features (NEWS_FEATURES 3c886a2b): rev 0 omitted it, which silently downgrades the
#    "legs NaN where the archive has a value" direction from decidable to undecidable -- the last receipt
#    (D10_LEGS_RN8_VS_ARCHIVE.json) was run WITH it, so rev 0 would not even reproduce its own predecessor;
#  * the P2 audit runs on BOTH ledgers: old P2 ledger_full.npz (continuity with the 01..04+08 receipts) and
#    ledger_full_ms.npz e179071d5955 (the adopted truth source, DECISION_RULE_D10 rev 2);
#  * outputs get a _JAN_AUG suffix: earlier receipts are never overwritten.
# Months are NOT hardcoded: the manifest gate decides; a month that is not VERIFIED is left out BY NAME.
set -u
EXP=/dev/shm/d10_2026-09-25
PY=/workspace/venv/bin/python
LOG=$EXP/logs/reaudit_jan_aug.log
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }
say "START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
MONTHS=""; SKIPPED=""
for M in 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08; do
  V=$($PY -B $EXP/devices/d10_manifest_gate.py $EXP/zips/$M $M 2>&1 | head -1)
  case "$V" in
    *" VERIFIED "*) MONTHS="${MONTHS:+$MONTHS,}$M";;
    *) SKIPPED="${SKIPPED:+$SKIPPED }$M(${V:-no-gate-output})";;
  esac
done
say "months VERIFIED and audited: $MONTHS"
say "months LEFT OUT by name:     ${SKIPPED:-none}"
[ -n "$MONTHS" ] || { say "no verified month: FAILED"; exit 1; }
cd $EXP
rc_all=0
run() { local tag=$1; shift; say "$tag start"; nice -n 10 $PY -B "$@" >> $EXP/logs/reaudit_$tag.log 2>&1; local rc=$?; say "$tag rc=$rc $(tail -1 $EXP/logs/reaudit_$tag.log)"; [ $rc = 0 ] || rc_all=$rc; }
run p2_old devices/d10_p2_ledger_vs_archive.py --ledger /workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz \
  --ledger-sha bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad --zips-root $EXP/zips --months $MONTHS \
  --out $EXP/receipts/D10_P2_LEDGER_VS_ARCHIVE_JAN_AUG.json
run p2_ms devices/d10_p2_ledger_vs_archive.py --ledger $EXP/ms/ledger_full_ms.npz \
  --ledger-sha e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88 --zips-root $EXP/zips --months $MONTHS \
  --out $EXP/receipts/D10_LEDGER_MS_VS_ARCHIVE_JAN_AUG.json
run legs devices/d10_legs_rn8_vs_archive.py --legs /dev/shm/news2_2026-09-23/work/legs.npz --legs-sha 9ee5886f \
  --features /dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz --zips-root $EXP/zips --months $MONTHS \
  --out $EXP/receipts/D10_LEGS_RN8_VS_ARCHIVE_JAN_AUG.json
[ $rc_all = 0 ] && say "COMPLETE" || say "FAILED rc=$rc_all"
