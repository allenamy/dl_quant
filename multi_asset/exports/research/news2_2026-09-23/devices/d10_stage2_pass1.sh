#!/usr/bin/env bash
# d10_stage2_pass1.sh -- line D stage 2b (lead approved 2026-09-26): NC pass 1 (King block, nc_p2_build.py p1, UNCHANGED code from the
# NC root) re-run with the D10 funding state, plus a pass-1 identity shard on the NC root's own funding state.
# Executor (protocol s10-f): this script, started by news2 under setsid on pod2; supervisor: news2's waiter on $L/stage2.log.
#
#   R0 = identity root: work/fund_state.npz -> the NC root's a12a8ed3 (the file NEWS_FEATURES 3c886a2b was built from).
#        Runs shard 0 of 24 only; d10_stage2_assemble.py compares it with NEWS_FEATURES row by row, bitwise. Red => stop.
#   R2 = D10 root:     work/fund_state.npz -> lineD/stage2/fund_state_d10.npz (f07e4ebd). All 24 shards, then merge1.
# Every other work input (axes, cache, R, boundary) and tree/ws/inputs are SYMLINKS to the NC root: nothing in the NC root is written.
# Environment copied from nc_build.sh (the build that produced 3c886a2b): venv314, NPY_DISABLE_CPU_FEATURES, single-threaded BLAS.
# At most $MAXP shards run at once (cgroup cpu.max 13.6 CPUs is shared). Stops at the first non-zero exit; names it.
set -u
S=/dev/shm/d10_2026-09-25/lineD/stage2; NCR=/dev/shm/nc_2026-09-23; D=$NCR/devices; L=$S/logs; N=24; MAXP=${MAXP:-12}
PY=/root/news_2026-09-23_env/venv314/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p $L
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> $L/stage2.log; }
say "START pgid=$(ps -o pgid= -p $$ | tr -d ' ') maxp=$MAXP"
mkroot() {   # $1 root, $2 fund_state file
  mkdir -p $1/work
  for x in tree ws inputs; do [ -e $1/$x ] || ln -s $NCR/$x $1/$x; done
  for f in axes.npz cache_crypto.npy R_crypto.npy boundary.npz; do [ -e $1/work/$f ] || ln -s $NCR/work/$f $1/work/$f; done
  [ -e $1/work/fund_state.npz ] || ln -s $2 $1/work/fund_state.npz
  say "root $1 fund_state -> $(readlink -f $1/work/fund_state.npz) sha $(sha256sum $1/work/fund_state.npz | cut -c1-16)"
}
mkroot $S/R0 $NCR/work/fund_state.npz
mkroot $S/R2 $S/fund_state_d10.npz
run_shard() {   # $1 root, $2 k
  NC_W=$1 NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$NCR/inputs/bundle_config.json nice -n 10 $PY -u $D/nc_p2_build.py p1 $2 $N \
    > $L/$(basename $1)_p1_$(printf %03d $2).log 2>&1 < /dev/null
}
export -f run_shard; export PY D N L NCR
# identity shard + the 24 D10 shards through one bounded pool
{ echo "$S/R0 0"; for k in $(seq 0 $((N-1))); do echo "$S/R2 $k"; done; } | \
  xargs -P $MAXP -L 1 bash -c 'run_shard "$0" "$1" || { echo "SHARD_FAILED $0 $1" >> $L/stage2.log; exit 255; }'
rc=$?
if [ $rc != 0 ]; then say "FAILED pass1 rc=$rc (see SHARD_FAILED lines)"; exit 1; fi
say "pass1 done: R0 shards $(ls $S/R0/work/p1_shards/*.npz 2>/dev/null | wc -l), R2 shards $(ls $S/R2/work/p1_shards/*.npz 2>/dev/null | wc -l)"
NC_W=$S/R2 NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$NCR/inputs/bundle_config.json nice -n 10 $PY -u $D/nc_p2_build.py merge1 >> $L/R2_merge1.log 2>&1 \
  || { say "FAILED merge1"; exit 1; }
say "merge1 $(tail -1 $L/R2_merge1.log)"
say "COMPLETE"
