#!/bin/bash
# run_rescore.sh <identity|reread> -- executor (10-f) of the frozen-F10 re-score (lead 11:1xZ; descriptive D10 re-read; no retraining).
#   identity : old D10 features f1cd3fa2 + October legs 383e3ddc -> each seed must reproduce its frozen F10_OOF bitwise -> RESCORE_IDENTITY PASS|FAIL
#   reread   : env RR_FEATURES / RR_FEATURES_SHA / RR_FEATURES_RECEIPT / RR_LEGS / RR_LEGS_SHA / RR_LEGS_RECEIPT (all required, never defaulted);
#              refuses unless 'RESCORE_IDENTITY PASS code=<rescore>,<trainer>' for the CURRENT code is in the marker log.
# Marker log /dev/shm/dlarch_f10d10/rescore.log; terminal 'RESCORE_<MODE>_DONE rc=<n>' / 'RESCORE_STOP <why>'.
set -u
C=/workspace/dlarch_2026-09-24/f10d10_2026-09-27; M=/dev/shm/dlarch_f10d10; LOG=$M/rescore.log; PY=/workspace/venv/bin/python
MODE=${1:?identity|reread}; FZ=$C/runs/d10/G1_T0_nomask
CL=/workspace/dlarch_2026-09-24/CHAIN/.claim_F10RESCORE
mkdir "$CL" 2>/dev/null || { echo "RESCORE_STOP claim exists" >> $LOG; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=rescore_$MODE started=$(date -u +%FT%TZ)" | tee $CL/owner > $M/rescore_$MODE.pgid
stop(){ echo "RESCORE_STOP $MODE: $1" >> $LOG; rm -rf "$CL"; exit 1; }
CODE=$(cd $C && sha256sum dlarch_f10_rescore.py dlarch_train_f10.py | awk '{print substr($1,1,16)}' | paste -sd, -)
echo "$(date -u +%FT%TZ) RESCORE_${MODE}_START code=$CODE" >> $LOG
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
if [ $MODE = identity ]; then
  FE=/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz; FS=f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd; FR=/dev/shm/d10_2026-09-25/lineD/stage2/NEWS_FEATURES_D10_RECEIPT.json
  LE=/workspace/d10_legs_oct_2026-09-27/october_20260927T071518Z/legs.npz; LS=383e3ddcd36260c66345d2cd4ae2bee74010fa13ca8f9e20e382ebca8230cb25; LR=/workspace/d10_legs_oct_2026-09-27/october_20260927T071518Z/NC_LEGS_RECEIPT.json
  OUT=$C/rescore/identity; EXTRA=--identity
else
  grep -qx "RESCORE_IDENTITY PASS code=$CODE" $LOG || stop "no identity PASS for the current code ($CODE)"
  for v in RR_FEATURES RR_FEATURES_SHA RR_FEATURES_RECEIPT RR_LEGS RR_LEGS_SHA RR_LEGS_RECEIPT; do [ -n "${!v:-}" ] || stop "env $v not set"; done
  FE=$RR_FEATURES; FS=$RR_FEATURES_SHA; FR=$RR_FEATURES_RECEIPT; LE=$RR_LEGS; LS=$RR_LEGS_SHA; LR=$RR_LEGS_RECEIPT; OUT=$C/rescore/reread; EXTRA=
fi
mkdir -p $(dirname $OUT/x)
RC=0
for S in 42 2027 7; do
  ( cd $C && $ENV $PY -B dlarch_f10_rescore.py --frozen $FZ/f10_s$S --out $OUT/f10_s$S --features $FE --features-sha $FS --features-receipt $FR \
      --legs $LE --legs-sha $LS --legs-receipt $LR $EXTRA > $C/rescore/${MODE}_s$S.log 2>&1 ) || RC=1
  echo "$(date -u +%FT%TZ) $(grep -hE '^F10_RESCORE_(IDENTITY|DONE)' $C/rescore/${MODE}_s$S.log || echo "s$S no result line")" >> $LOG
done
grep -q Traceback $C/rescore/${MODE}_s*.log && RC=1
if [ $MODE = identity ]; then
  [ $RC -eq 0 ] && [ "$(grep -c 'F10_RESCORE_IDENTITY seed=.* PASS' $LOG)" -ge 3 ] && echo "RESCORE_IDENTITY PASS code=$CODE" >> $LOG || { echo "RESCORE_IDENTITY FAIL code=$CODE" >> $LOG; RC=1; }
fi
echo "RESCORE_${MODE^^}_DONE rc=$RC" >> $LOG; rm -rf "$CL"
