#!/usr/bin/env bash
# d10_stage2_pass1_ext.sh --fund-state PATH --fund-state-sha SHA256 --root NEW_DIR
# Descriptive re-read, step R5 (docs/PLAN_d10_reread_past_cut_2026-09-27.md): NC pass 1 (nc_p2_build.py p1, UNCHANGED NC-root code) on
# a fund_state rebuilt from the ledger extended past the cut. Exactly d10_stage2_pass1.sh's R2 half -- same environment (venv314,
# NPY_DISABLE_CPU_FEATURES, single-threaded BLAS), same symlinked NC-root inputs, 24 shards through a bounded pool, then merge1 --
# with three differences: the fund_state path and its sha are arguments (checked before anything runs), the root must be a NEW directory
# (never overwrite evidence), and no identity shard is re-run (line D's R0 identity shard stays the reference; assemble re-checks it).
# Log on /dev/shm (the failure signal must not sit on the volume it reports on). Last line anchored: PASS1_EXT COMPLETE | PASS1_EXT FAILED.
set -u
FS=""; FSHA=""; R=""
while [ $# -gt 0 ]; do
  case "$1" in --fund-state) FS=$2; shift 2;; --fund-state-sha) FSHA=$2; shift 2;; --root) R=$2; shift 2;;
    *) echo "PASS1_EXT FAILED unknown argument $1"; exit 2;; esac
done
NCR=/dev/shm/nc_2026-09-23; D=$NCR/devices; N=24; MAXP=${MAXP:-12}
PY=/root/news_2026-09-23_env/venv314/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
[ -n "$FS" ] && [ -n "$FSHA" ] && [ -n "$R" ] || { echo "PASS1_EXT FAILED usage"; exit 2; }
[ -e "$R" ] && { echo "PASS1_EXT FAILED $R exists -- refusing to overwrite evidence"; exit 1; }
L=/dev/shm/news2_reread/pass1_$(basename $R); mkdir -p $L
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> $L/pass1.log; }
fail() { say "PASS1_EXT FAILED $*"; exit 1; }
say "START pgid=$(ps -o pgid= -p $$ | tr -d ' ') maxp=$MAXP root=$R"
[ "$(sha256sum "$FS" | cut -c1-64)" = "$FSHA" ] || fail "fund_state sha $(sha256sum "$FS" | cut -c1-64) != $FSHA"
mkdir -p $R/work
for x in tree ws inputs; do ln -s $NCR/$x $R/$x; done
for f in axes.npz cache_crypto.npy R_crypto.npy boundary.npz; do ln -s $NCR/work/$f $R/work/$f; done
ln -s "$FS" $R/work/fund_state.npz
say "root $R fund_state -> $(readlink -f $R/work/fund_state.npz) sha $(sha256sum $R/work/fund_state.npz | cut -c1-16)"
run_shard() {
  NC_W=$1 NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$NCR/inputs/bundle_config.json nice -n 10 $PY -u $D/nc_p2_build.py p1 $2 $N \
    > $L/p1_$(printf %03d $2).log 2>&1 < /dev/null
}
export -f run_shard; export PY D N L NCR
for k in $(seq 0 $((N-1))); do echo "$R $k"; done | \
  xargs -P $MAXP -L 1 bash -c 'run_shard "$0" "$1" || { echo "SHARD_FAILED $0 $1" >> $L/pass1.log; exit 255; }'
rc=$?
[ $rc = 0 ] || fail "pass1 rc=$rc (see SHARD_FAILED lines)"
say "pass1 done: shards $(ls $R/work/p1_shards/*.npz 2>/dev/null | wc -l)"
NC_W=$R NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$NCR/inputs/bundle_config.json nice -n 10 $PY -u $D/nc_p2_build.py merge1 >> $L/merge1.log 2>&1 \
  || fail "merge1 rc=$?"
say "merge1 $(tail -1 $L/merge1.log)"
say "PASS1_EXT COMPLETE"
