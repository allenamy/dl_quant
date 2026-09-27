#!/bin/bash
# run_f10d10.sh <PHASE> -- executor (protocol 10-f) of the October D10 F10 retrain (RUNBOOK_october_rebuild_D10_2026-09-27.md §3, option (ii);
# owner dlarch). Code dir on pod2: /workspace/dlarch_2026-09-24/f10d10_2026-09-27 (trainer + its local imports + the vendored news2 tree,
# shas checked against the repo commit before any run). Marker log on /dev/shm (protocol: a different volume than the products).
#   g1    : contract identity -- the modified trainer with its DEFAULT (NC) inputs, --arm T0 --no-mask --seed 42, folds 2023,202609, must
#           reproduce the in-service NC F10 s42 fold artifacts (/dev/shm/news2_2026-09-23/work/f10_s42) BITWISE (dlarch_identity_compare.py:
#           every array of scores.npz and every tensor of model.pt; positive control first).  -> 'F10D10_G1 PASS|FAIL'
#   train : seeds 42 2027 7 in sequence on the D10 inputs given by env (all REQUIRED, never defaulted): F10D10_FEATURES, F10D10_FEATURES_SHA,
#           F10D10_FEATURES_RECEIPT, F10D10_LEGS, F10D10_LEGS_SHA, F10D10_LEGS_RECEIPT; --train-cut-utc 2026-09-01T02:00:00Z. Refuses unless
#           'F10D10_G1 PASS' is in the marker log.
# rev 1 (07:0xZ): the G1 PASS line now carries the shas of the code it certified ('F10D10_G1 PASS code=<t>,<c>,<s>'), and 'train'
# requires a PASS line whose code shas equal the CURRENT files -- a PASS left in the log by an earlier code version (run 1, before
# the safe_io fsync change) must not admit a later one. Found while re-running G1 after the C1 fix: the log still held run 1's PASS.
# rev 2: phase 'cells' (own claim, started beside 'train'): for each seed whose D10 F10 training has FINISHED (TRAIN_RECEIPT status
#   ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED), build the joint-arm book cell through dlarch_chain_run.py (copy in this dir) with
#   --share-json $C/share_d10.json (D10 features, the October-King legs + their receipt, the October King OOF; written by 'train'
#   from the same env it trained on) --f10-src <that seed> --arm-name DLARCH_D10_s<seed> --label d10_s<seed> --engine, then
#   dlarch_cell_retain.py against DLARCH_REF_NC_s42X (verify, then --delete after its four preconditions). A write probe of 1.4 GiB
#   (a cell is ~0.36 GB, plus 1 GiB) precedes every cell. Bound 6 h. Needs env F10D10_KING_OOF too (recorded, not read by combo).
# rev 3: RETAIN receipts go to $W/receipts (beside the NC references, so one receipts dir serves the paired reading); phase 'read':
#   dlarch_paired_d.py (pinned 4e293147 family, unchanged) -- arm RETAIN_D10_s*_2026-09-27.json (DLARCH_D10_s), bases RETAIN_REFNC
#   (DLARCH_REF_NC_s, the gated same-seed pairing, DL-gate rev 7 §13) and RETAIN_s*_2026-09-25 (DLARCH_T0_s, reference only), sigma
#   receipt SIGMA_F10_2026-09-25.json. Transcribes revision 4/5; the October verdict is lead's.
# Terminal line (line start): 'F10D10_<PHASE>_DONE rc=<n>' ; 'F10D10_STOP <why>'.
set -u
C=/workspace/dlarch_2026-09-24/f10d10_2026-09-27; M=/dev/shm/dlarch_f10d10; LOG=$M/f10d10.log; PY=/workspace/venv/bin/python
PHASE=${1:?usage: run_f10d10.sh g1|train|cells|read}
mkdir -p $M $C/runs $C/receipts
CL=/workspace/dlarch_2026-09-24/CHAIN/.claim_F10D10; [ "$PHASE" = cells ] && CL=${CL}_CELLS; [ "$PHASE" = read ] && CL=${CL}_READ
mkdir "$CL" 2>/dev/null || { echo "F10D10_STOP claim exists ($PHASE)" >> $LOG; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=f10d10_$PHASE started=$(date -u +%FT%TZ)" | tee $CL/owner > $M/f10d10_$PHASE.pgid
say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }
stop(){ echo "F10D10_STOP $PHASE: $1" >> $LOG; rm -rf "$CL"; exit 1; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
CODE=$(cd $C && sha256sum dlarch_train_f10.py dlarch_chain_torch.py dlarch_safe_io.py | awk '{print substr($1,1,16)}' | paste -sd, -)
say "F10D10_${PHASE}_START shas $(cd $C && sha256sum dlarch_train_f10.py dlarch_chain_torch.py dlarch_safe_io.py dlarch_identity_compare.py | awk '{print substr($1,1,16)}' | tr '\n' ' ')"
[ "$PHASE" != cells ] && [ "$PHASE" != read ] && nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q . && stop "GPU busy (another compute process present)"
case $PHASE in
g1)
  ( cd $C && $ENV $PY -B dlarch_train_f10.py --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --no-mask --seed 42 --folds 2023,202609 \
        --out-root $C/runs/g1 > $C/runs/g1_train.log 2>&1 ) || stop "g1 training rc!=0 (see $C/runs/g1_train.log)"
  grep -q "^DLARCH_TRAIN_DONE" $C/runs/g1_train.log || stop "g1 training no DONE line"
  ( cd $C && $ENV $PY -B dlarch_identity_compare.py --a /dev/shm/news2_2026-09-23/work/f10_s42 --b $C/runs/g1/G1_T0_nomask/f10_s42 --folds 2023,202609 \
        --label "F10D10_G1 modified trainer (NC defaults) vs in-service NC F10 s42" --out $C/receipts/F10D10_G1_IDENTITY.json \
        --env-whitelist PATH,HOME,LC_CTYPE > $C/runs/g1_compare.log 2>&1 ) || stop "g1 compare rc!=0 (see $C/runs/g1_compare.log)"
  $PY -c "import json,sys; d=json.load(open('$C/receipts/F10D10_G1_IDENTITY.json')); sys.exit(0 if d['all_identical'] and d['positive_control'].startswith('PASS') else 1)" \
    && echo "F10D10_G1 PASS code=$CODE" >> $LOG || { echo "F10D10_G1 FAIL" >> $LOG; stop "G1 not identical"; } ;;
train)
  grep -qx "F10D10_G1 PASS code=$CODE" $LOG || stop "no G1 PASS for the current code ($CODE)"
  for v in F10D10_FEATURES F10D10_FEATURES_SHA F10D10_FEATURES_RECEIPT F10D10_LEGS F10D10_LEGS_SHA F10D10_LEGS_RECEIPT F10D10_KING_OOF; do [ -n "${!v:-}" ] || stop "env $v not set"; done
  [ "$(sha256sum $F10D10_LEGS | cut -c1-64)" = "$F10D10_LEGS_SHA" ] || stop "legs sha differs from F10D10_LEGS_SHA"
  $PY - "$C/share_d10.json" <<PYJ || stop "share json"
import json, sys
json.dump({"work/NEWS_FEATURES.npz": "$F10D10_FEATURES", "work/legs.npz": "$F10D10_LEGS", "receipts/P3_LEGS.json": "$F10D10_LEGS_RECEIPT",
           "work/king/KING_OOF.npz": "$F10D10_KING_OOF"}, open(sys.argv[1] + ".tmp", "w"), indent=1)  # durable-exempt: tiny config, re-read and compared on the next line
import os; os.replace(sys.argv[1] + ".tmp", sys.argv[1]); assert json.load(open(sys.argv[1]))["work/legs.npz"] == "$F10D10_LEGS"
PYJ
  say "share_d10.json $(sha256sum $C/share_d10.json | cut -c1-16)"
  for S in 42 2027 7; do
    ( cd $C && $ENV $PY -B dlarch_train_f10.py --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --no-mask --seed $S \
        --features $F10D10_FEATURES --features-sha $F10D10_FEATURES_SHA --features-receipt $F10D10_FEATURES_RECEIPT \
        --legs $F10D10_LEGS --legs-sha $F10D10_LEGS_SHA --legs-receipt $F10D10_LEGS_RECEIPT \
        --train-cut-utc 2026-09-01T02:00:00Z --out-root $C/runs/d10 > $C/runs/train_s$S.log 2>&1 ) || stop "seed $S rc!=0 (see $C/runs/train_s$S.log)"
    grep -q "^DLARCH_TRAIN_DONE" $C/runs/train_s$S.log || stop "seed $S no DONE line"
    say "F10D10_SEED_DONE s$S $(grep '^DLARCH_TRAIN_DONE' $C/runs/train_s$S.log)"
  done ;;
cells)
  W=/workspace/dlarch_2026-09-24; REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE; REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
  ENG=/dev/shm/news2_2026-09-23/engine; LEFT="42 2027 7"
  for round in $(seq 1 360); do
    NEWLEFT=""
    for S in $LEFT; do
      TR=$C/runs/d10/G1_T0_nomask/f10_s$S/TRAIN_RECEIPT.json
      if [ ! -f "$TR" ] || ! grep -q '"ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED"' "$TR"; then NEWLEFT="$NEWLEFT $S"; continue; fi
      [ -s $C/share_d10.json ] || stop "share_d10.json missing (train phase writes it)"
      dd if=/dev/zero of=$C/.probe bs=1M count=1434 conv=fsync status=none && [ "$(stat -c %s $C/.probe)" = $((1434*1048576)) ] || { rm -f $C/.probe; stop "write probe 1.4 GiB failed (quota) before seed $S"; }
      rm -f $C/.probe
      say "cell s$S start"
      ( cd $C && $ENV $PY -B dlarch_chain_run.py PATH,HOME,LC_CTYPE $C/receipts/chain_s$S --seed $S --share-json $C/share_d10.json \
          --f10-src $C/runs/d10/G1_T0_nomask/f10_s$S --arm-name DLARCH_D10_s$S --label d10_s$S --engine > $C/runs/cell_s$S.log 2>&1 ) || stop "chain s$S rc!=0 (see $C/runs/cell_s$S.log)"
      TAG=DLARCH_D10_s${S}_scaled_rule_raw_UAFE
      ( cd $C && $ENV $PY -B $W/dlarch_cell_retain.py --env-whitelist PATH,HOME,LC_CTYPE --cell $W/chain/d10_s$S/runs/$TAG --tag $TAG \
          --control-cell $REF --control-tag $REFTAG --engine $ENG --out $W/receipts/RETAIN_D10_s${S}_2026-09-27.json --delete --cell-root $W/chain/d10_s$S \
          > $C/runs/retain_s$S.log 2>&1 ) || stop "retain s$S rc!=0 (see $C/runs/retain_s$S.log)"
      say "F10D10_CELL_DONE s$S $(grep -h DLARCH_CELL_RETAIN $C/runs/retain_s$S.log | tail -1)"
    done
    LEFT=$(echo "$NEWLEFT" | sed 's/^ *//'); [ -z "$LEFT" ] && break; sleep 60
  done
  [ -z "$LEFT" ] || stop "bound expired, seeds without cells: $LEFT" ;;
read)
  W=/workspace/dlarch_2026-09-24
  for S in 42 2027 7; do [ -s $W/receipts/RETAIN_D10_s${S}_2026-09-27.json ] || stop "no RETAIN_D10 for s$S"; done
  ( cd $W && $ENV $PY -B dlarch_paired_d.py PATH,HOME,LC_CTYPE $W/receipts $W/receipts/SIGMA_F10_2026-09-25.json /dev/shm/news2_2026-09-23/engine \
      $W/receipts/PAIRED_D_D10_2026-09-27.json --arm-glob 'RETAIN_D10_s*_2026-09-27.json' --arm-tagkey DLARCH_D10_s \
      --base-glob 'RETAIN_REFNC_s*_2026-09-26.json' --base-tagkey DLARCH_REF_NC_s --base-glob 'RETAIN_s*_2026-09-25.json' --base-tagkey DLARCH_T0_s \
      > $C/runs/read.log 2>&1 ) || stop "paired_d rc!=0 (see $C/runs/read.log)"
  say "F10D10_READ $(tail -1 $C/runs/read.log | cut -c1-200)" ;;
*) stop "unknown phase" ;;
esac
RC=0; grep -q Traceback $C/runs/*.log 2>/dev/null && RC=1
echo "F10D10_${PHASE^^}_DONE rc=$RC" >> $LOG; rm -rf "$CL"
