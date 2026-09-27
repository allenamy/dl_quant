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
# Terminal line (line start): 'F10D10_<PHASE>_DONE rc=<n>' ; 'F10D10_STOP <why>'.
set -u
C=/workspace/dlarch_2026-09-24/f10d10_2026-09-27; M=/dev/shm/dlarch_f10d10; LOG=$M/f10d10.log; PY=/workspace/venv/bin/python
PHASE=${1:?usage: run_f10d10.sh g1|train}
mkdir -p $M $C/runs $C/receipts
mkdir "/workspace/dlarch_2026-09-24/CHAIN/.claim_F10D10" 2>/dev/null || { echo "F10D10_STOP claim exists ($PHASE)" >> $LOG; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=f10d10_$PHASE started=$(date -u +%FT%TZ)" | tee /workspace/dlarch_2026-09-24/CHAIN/.claim_F10D10/owner > $M/f10d10.pgid
say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }
stop(){ echo "F10D10_STOP $PHASE: $1" >> $LOG; rm -rf /workspace/dlarch_2026-09-24/CHAIN/.claim_F10D10; exit 1; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
CODE=$(cd $C && sha256sum dlarch_train_f10.py dlarch_chain_torch.py dlarch_safe_io.py | awk '{print substr($1,1,16)}' | paste -sd, -)
say "F10D10_${PHASE}_START shas $(cd $C && sha256sum dlarch_train_f10.py dlarch_chain_torch.py dlarch_safe_io.py dlarch_identity_compare.py | awk '{print substr($1,1,16)}' | tr '\n' ' ')"
nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q . && stop "GPU busy (another compute process present)"
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
  for v in F10D10_FEATURES F10D10_FEATURES_SHA F10D10_FEATURES_RECEIPT F10D10_LEGS F10D10_LEGS_SHA F10D10_LEGS_RECEIPT; do [ -n "${!v:-}" ] || stop "env $v not set"; done
  for S in 42 2027 7; do
    ( cd $C && $ENV $PY -B dlarch_train_f10.py --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --no-mask --seed $S \
        --features $F10D10_FEATURES --features-sha $F10D10_FEATURES_SHA --features-receipt $F10D10_FEATURES_RECEIPT \
        --legs $F10D10_LEGS --legs-sha $F10D10_LEGS_SHA --legs-receipt $F10D10_LEGS_RECEIPT \
        --train-cut-utc 2026-09-01T02:00:00Z --out-root $C/runs/d10 > $C/runs/train_s$S.log 2>&1 ) || stop "seed $S rc!=0 (see $C/runs/train_s$S.log)"
    grep -q "^DLARCH_TRAIN_DONE" $C/runs/train_s$S.log || stop "seed $S no DONE line"
    say "F10D10_SEED_DONE s$S $(grep '^DLARCH_TRAIN_DONE' $C/runs/train_s$S.log)"
  done ;;
*) stop "unknown phase" ;;
esac
RC=0; grep -q Traceback $C/runs/*.log 2>/dev/null && RC=1
echo "F10D10_${PHASE^^}_DONE rc=$RC" >> $LOG; rm -rf /workspace/dlarch_2026-09-24/CHAIN/.claim_F10D10
