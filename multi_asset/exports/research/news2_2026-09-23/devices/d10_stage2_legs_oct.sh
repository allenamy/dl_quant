#!/usr/bin/env bash
# d10_stage2_legs_oct.sh --king-oof PATH --king-oof-sha SHA256 --out DIR [--label TEXT]
# October stage 2d (lead ruling 2026-09-27): legs rebuilt from the OCTOBER King OOF (fresh2's retrained King, not the in-service booster
# re-predicted on D10 features -- that was line D's KING_OOF_SWAP ac2fad4d, which built legs_d10 104af853). Everything else is exactly
# d10_stage2_legs.sh mode d10: nc_legs.py (news2 root copy) UNCHANGED, venv314, NPY_DISABLE_CPU_FEATURES, single-threaded BLAS, NC_W = the
# D10 pass-1 root R2 (fund_state_d10 f07e4ebd), NEWS_FEATURES_D10 f1cd3fa2.
# Differences from d10_stage2_legs.sh, and why:
#  * the King OOF is an argument, and its sha256 must equal --king-oof-sha before anything runs (the receipt then names it);
#  * --out must be a NEW directory: it refuses to write into an existing one (evidence is never overwritten; lead 2026-09-27);
#  * the same preconditions as mode d10 (line D's legs identity BITWISE, stage-2c assemble receipt present) are checked, not assumed;
#  * the last log line is anchored: `LEGS_OCT DONE <sha256>` or `LEGS_OCT FAILED <reason>`; exit 0 only for DONE.
# Control run (before the October OOF exists): --king-oof KING_OOF_SWAP ac2fad4d must reproduce legs_d10 104af853 bitwise.
set -u
KOOF=""; KSHA=""; O=""; LABEL=""; NF_ARG=""; NF_SHA_ARG=""; NCW_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --king-oof) KOOF=$2; shift 2;; --king-oof-sha) KSHA=$2; shift 2;; --out) O=$2; shift 2;; --label) LABEL=$2; shift 2;;
    # rev 1 (descriptive re-read, PLAN_d10_reread_past_cut R7): features, their sha and the pass-1 root may be given; defaults = line D
    --features) NF_ARG=$2; shift 2;; --features-sha) NF_SHA_ARG=$2; shift 2;; --nc-w) NCW_ARG=$2; shift 2;;
    *) echo "LEGS_OCT FAILED unknown argument $1"; exit 2;;
  esac
done
S=/dev/shm/d10_2026-09-25/lineD/stage2; W=/dev/shm/news2_2026-09-23; NCR=/dev/shm/nc_2026-09-23
NF=${NF_ARG:-/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz}; NF_SHA=${NF_SHA_ARG:-f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd}
NCW=${NCW_ARG:-$S/R2}
P314=/root/news_2026-09-23_env/venv314/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
fail() { echo "LEGS_OCT FAILED $*" | tee -a "${LOG:-/dev/stderr}"; exit 1; }
[ -n "$KOOF" ] && [ -n "$KSHA" ] && [ -n "$O" ] || { echo "LEGS_OCT FAILED usage: --king-oof --king-oof-sha --out required"; exit 2; }
[ -e "$O" ] && { echo "LEGS_OCT FAILED $O already exists -- refusing to overwrite evidence"; exit 1; }
mkdir -p "$O"; LOG=$O/legs_oct.log
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START pgid=$(ps -o pgid= -p $$ | tr -d ' ') label='$LABEL' king_oof=$KOOF" >> $LOG
[ "$(sha256sum "$KOOF" | cut -c1-64)" = "$KSHA" ] || fail "king OOF sha $(sha256sum "$KOOF" | cut -c1-64) != --king-oof-sha $KSHA"
[ "$(sha256sum "$NF" | cut -c1-64)" = "$NF_SHA" ] || fail "features sha is not $NF_SHA"
grep -q '"VERDICT": "BITWISE"' $S/legs_id/LEGS_IDENTITY.json || fail "line D legs identity receipt is not BITWISE"
[ -s $S/NEWS_FEATURES_D10_RECEIPT.json ] || fail "stage 2c assemble receipt missing"
NC_W=$NCW NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$W/inputs/bundle_config.json \
  nice -n 10 $P314 -u $W/devices/nc_legs.py "$NF" "$KOOF" "$O/legs.npz" >> $LOG 2>&1 || fail "nc_legs rc=$?"
[ -s "$O/legs.npz" ] || fail "no legs.npz written"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) king_oof_sha256=$KSHA features_sha256=$NF_SHA nc_w=$NCW" >> $LOG
echo "LEGS_OCT DONE $(sha256sum "$O/legs.npz" | cut -c1-64)" >> $LOG
exit 0
