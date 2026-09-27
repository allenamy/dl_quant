#!/bin/bash
# run_reread_cells.sh -- executor (10-f) of the descriptive D10 re-read book cells (lead 11:1xZ; verdict UNDECIDED unchanged).
# Needs 'RESCORE_REREAD_DONE rc=0' in /dev/shm/dlarch_f10d10/rescore.log (the frozen F10 re-scored on news2's rebuilt features) and env
# RR_FEATURES RR_LEGS RR_LEGS_RECEIPT RR_KING_OOF (the rebuilt features / legs / the King OOF those legs were built from; recorded).
# Per seed 42 2027 7: dlarch_chain_run.py --share-json <rr share> --f10-src rescore/reread/f10_s<seed> --arm-name DLARCH_D10RR_s<seed>
#   --label d10rr_s<seed> --engine (1.4 GiB write probe first), dlarch_cell_retain.py vs DLARCH_REF_NC_s42X (verify then --delete);
# then dlarch_paired_d.py (4e293147, unchanged; bases REF_NC same seed [gated] and T0 [reference]) and dlarch_f10d10_table.py D10RR.
# Terminal: 'REREAD_CELLS_DONE rc=<n>' / 'REREAD_STOP <why>' in /dev/shm/dlarch_f10d10/reread.log.
set -u
W=/workspace/dlarch_2026-09-24; C=$W/f10d10_2026-09-27; M=/dev/shm/dlarch_f10d10; LOG=$M/reread.log; PY=/workspace/venv/bin/python
REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE; REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE; ENG=/dev/shm/news2_2026-09-23/engine
CL=$W/CHAIN/.claim_REREAD; mkdir "$CL" 2>/dev/null || { echo "REREAD_STOP claim exists" >> $LOG; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=reread_cells started=$(date -u +%FT%TZ)" | tee $CL/owner > $M/reread.pgid
say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }; stop(){ echo "REREAD_STOP $1" >> $LOG; rm -rf "$CL"; exit 1; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
grep -q "^RESCORE_REREAD_DONE rc=0" $M/rescore.log || stop "re-score not done"
for v in RR_FEATURES RR_LEGS RR_LEGS_RECEIPT RR_KING_OOF; do [ -n "${!v:-}" ] || stop "env $v not set"; done
$PY - "$C/share_d10rr.json" <<PYJ || stop "share json"
import json, sys, os
t = json.dumps({"work/NEWS_FEATURES.npz": "$RR_FEATURES", "work/legs.npz": "$RR_LEGS", "receipts/P3_LEGS.json": "$RR_LEGS_RECEIPT", "work/king/KING_OOF.npz": "$RR_KING_OOF"}, indent=1)
open(sys.argv[1] + ".tmp", "w").write(t)  # durable-exempt: tiny config, re-read and compared before the replace
assert open(sys.argv[1] + ".tmp").read() == t; os.replace(sys.argv[1] + ".tmp", sys.argv[1])
PYJ
say "REREAD_START share $(sha256sum $C/share_d10rr.json | cut -c1-16)"
for S in 42 2027 7; do
  dd if=/dev/zero of=$C/.probe bs=1M count=1434 conv=fsync status=none && [ "$(stat -c %s $C/.probe)" = $((1434*1048576)) ] || { rm -f $C/.probe; stop "write probe failed before s$S"; }
  rm -f $C/.probe
  ( cd $C && $ENV $PY -B dlarch_chain_run.py PATH,HOME,LC_CTYPE $C/receipts/chain_rr_s$S --seed $S --share-json $C/share_d10rr.json \
      --f10-src $C/rescore/reread/f10_s$S --arm-name DLARCH_D10RR_s$S --label d10rr_s$S --engine > $C/rescore/cell_rr_s$S.log 2>&1 ) || stop "chain s$S"
  TAG=DLARCH_D10RR_s${S}_scaled_rule_raw_UAFE
  ( cd $C && $ENV $PY -B $W/dlarch_cell_retain.py --env-whitelist PATH,HOME,LC_CTYPE --cell $W/chain/d10rr_s$S/runs/$TAG --tag $TAG \
      --control-cell $REF --control-tag $REFTAG --engine $ENG --out $W/receipts/RETAIN_D10RR_s${S}_2026-09-27.json --delete --cell-root $W/chain/d10rr_s$S \
      > $C/rescore/retain_rr_s$S.log 2>&1 ) || stop "retain s$S"
  say "REREAD_CELL_DONE s$S $(grep -h DLARCH_CELL_RETAIN $C/rescore/retain_rr_s$S.log | tail -1)"
done
( cd $W && $ENV $PY -B dlarch_paired_d.py PATH,HOME,LC_CTYPE $W/receipts $W/receipts/SIGMA_F10_2026-09-25.json $ENG $W/receipts/PAIRED_D_D10RR_2026-09-27.json \
    --arm-glob 'RETAIN_D10RR_s*_2026-09-27.json' --arm-tagkey DLARCH_D10RR_s --base-glob 'RETAIN_REFNC_s*_2026-09-26.json' --base-tagkey DLARCH_REF_NC_s \
    --base-glob 'RETAIN_s*_2026-09-25.json' --base-tagkey DLARCH_T0_s > $C/rescore/read_rr.log 2>&1 ) || stop "paired_d"
( cd $C && $ENV $PY -B dlarch_f10d10_table.py PATH,HOME,LC_CTYPE $W/receipts $W/receipts/PAIRED_D_D10RR_2026-09-27.json $W/receipts/F10D10RR_TABLE_2026-09-27.json D10RR \
    >> $C/rescore/read_rr.log 2>&1 ) || stop "table"
RC=0; grep -q Traceback $C/rescore/*rr*.log && RC=1
echo "REREAD_CELLS_DONE rc=$RC" >> $LOG; rm -rf "$CL"
