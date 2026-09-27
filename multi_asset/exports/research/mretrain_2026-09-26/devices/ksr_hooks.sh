#!/bin/bash
# ksr_hooks.sh <after_legs|after_targets> <LBL> <W> -- the KSR steps mr_prep.sh runs at two points when MR_HOOK points here
# (fresh2 2026-09-27; interface agreed with dlarch, lead-approved 07:0xZ). Both run BEFORE mr_prep deletes legs / targets.
#   after_legs    : (1) export the cell's legs to $KSR_ROOT/legs/<LBL>.npz (copy -> sha of copy == sha of source -> rename; line appended
#                   to legs/SHA256SUMS); (2) if KSR_GATE4_REF is set: gate 4 of DECISION_RULE_king_serving_refresh §0 by dlarch's
#                   dlarch_ksr_splice.py legs (sha pinned: KSR_SPLICE_SHA) -> $KSR_ROOT/gate4/<LBL>.json; PASS only on rc 0 AND a
#                   line-start "KSR_SPLICE PASS=True". Any failure => non-zero => mr_prep fail() => STOP in the family log => the family
#                   stops (rule §0: any gate fails => stop).
#   after_targets : ksr_targets_stats.py -> $KSR_ROOT/targets_stats/<LBL>_s{42,2027}.{npz,json} (guardrail §3 inputs).
# env: KSR_ROOT, PV, and for gate 4: KSR_GATE4_REF (reference S0 legs), KSR_SPLICE_RECEIPT, KSR_SPLICE_DEV, KSR_SPLICE_SHA.
set -uo pipefail
PH=$1; LBL=$2; W=$3; D=$(cd "$(dirname "$0")" && pwd)
: "${KSR_ROOT:?}" "${PV:?}"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
case $PH in
after_legs)
  mkdir -p $KSR_ROOT/legs $KSR_ROOT/gate4
  src=$W/work/legs.npz; dst=$KSR_ROOT/legs/$LBL.npz
  [ -s $src ] || { echo "$(ts) HOOK FAIL: no legs at $src"; exit 1; }
  [ -e $dst ] && { echo "$(ts) HOOK FAIL: $dst exists (a cell's legs are exported once)"; exit 1; }
  s1=$(sha256sum $src | cut -c1-64); cp $src $dst.tmp; s2=$(sha256sum $dst.tmp | cut -c1-64)
  [ -n "$s1" ] && [ "$s1" = "$s2" ] || { rm -f $dst.tmp; echo "$(ts) HOOK FAIL: legs copy sha $s2 != source $s1"; exit 1; }
  mv $dst.tmp $dst && echo "$s1  $LBL.npz" >> $KSR_ROOT/legs/SHA256SUMS
  grep -q "^$s1  $LBL.npz$" $KSR_ROOT/legs/SHA256SUMS || { echo "$(ts) HOOK FAIL: SHA256SUMS line not written"; exit 1; }
  echo "$(ts) HOOK legs exported $LBL sha=$s1"
  if [ -n "${KSR_GATE4_REF:-}" ]; then
    : "${KSR_SPLICE_RECEIPT:?}" "${KSR_SPLICE_DEV:?}" "${KSR_SPLICE_SHA:?}"
    [ "$(sha256sum $KSR_SPLICE_DEV | cut -c1-64)" = "$KSR_SPLICE_SHA" ] || { echo "$(ts) HOOK FAIL: gate-4 device is not the pinned $KSR_SPLICE_SHA"; exit 1; }
    out=$KSR_ROOT/gate4/$LBL.json; log=$KSR_ROOT/gate4/$LBL.log
    $PV -B $KSR_SPLICE_DEV legs $KSR_GATE4_REF $dst $KSR_SPLICE_RECEIPT $out > $log 2>&1; rc=$?
    if [ $rc -eq 0 ] && grep -q "^KSR_SPLICE PASS=True mode=legs" $log; then echo "$(ts) HOOK GATE4 PASS $LBL $(grep -h '^KSR_SPLICE' $log)"
    else echo "$(ts) HOOK GATE4 FAIL $LBL rc=$rc $(grep -h '^KSR_SPLICE\|Error' $log | tail -1)"; exit 1; fi
  fi ;;
after_targets)
  mkdir -p $KSR_ROOT/targets_stats; tl=$KSR_ROOT/targets_stats/$LBL.log   # the hook creates what it writes into (not its caller)
  $PV -B $D/ksr_targets_stats.py $W $W/work/legs.npz $LBL $KSR_ROOT/targets_stats > $tl 2>&1
  grep -q "^KSR_TSTATS_DONE $LBL$" $tl || { echo "$(ts) HOOK FAIL: targets stats $LBL (see $tl)"; exit 1; }
  echo "$(ts) HOOK targets_stats $LBL done" ;;
*) echo "unknown phase $PH"; exit 1 ;;
esac
