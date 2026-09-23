#!/bin/bash
# NC training-feature build driver (pod2). pass 1 (King block) sharded -> merge1 (member history) -> pass 2 (F10 mini) sharded -> merge2.
# Own PGIDs are recorded in logs/nc_build_pgids.txt; nothing is killed by name. Stops at the first non-zero exit.
set -e
W=/dev/shm/nc_2026-09-23; D=$W/devices; L=$W/logs; N=${NC_WORKERS:-24}
PY=/root/news_2026-09-23_env/venv314/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NC_W=$W NC_TREE=$W/tree NC_WS=$W/ws NC_CFG=$W/inputs/bundle_config.json
step() { echo "$(date -u +%H:%M:%S) START $1" >> $L/nc_build.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" >> $L/nc_build.log; }
run_sharded() {   # $1 = p1|p2
  local pids=()
  for k in $(seq 0 $((N-1))); do
    setsid nice -n 10 $PY -u $D/nc_p2_build.py $1 $k $N > $L/nc_$1_$(printf %03d $k).log 2>&1 < /dev/null &
    pids+=($!); echo "$1 shard $k pid $!" >> $L/nc_build_pgids.txt
  done
  local rc=0
  for p in "${pids[@]}"; do wait $p || rc=1; done
  [ $rc -eq 0 ]
}
cd $W
PHASE=${1:-all}
if [ "$PHASE" = "p1" ] || [ "$PHASE" = "all" ]; then
  step p1; run_sharded p1; done_ p1
  step merge1; $PY -u $D/nc_p2_build.py merge1 >> $L/nc_merge.log 2>&1; done_ merge1
fi
if [ "$PHASE" = "p2" ] || [ "$PHASE" = "all" ]; then
  step p2; run_sharded p2; done_ p2
  step merge2; $PY -u $D/nc_p2_build.py merge2 >> $L/nc_merge.log 2>&1; done_ merge2
  echo "$(date -u +%H:%M:%S) BUILD_DONE" >> $L/nc_build.log
fi
