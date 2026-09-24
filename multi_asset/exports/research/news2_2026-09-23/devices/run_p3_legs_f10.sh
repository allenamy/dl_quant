#!/bin/bash
# legs -> re-stage post_king -> F10 both seeds, each step with the environment from
# news_chain_resume.sh. King (run4: PV + NPY_DISABLE set) is already done, OOF a10b8725.
set -e
W=/dev/shm/news2_2026-09-23; D=$W/devices; L=$W/logs; NC=/dev/shm/nc_2026-09-23
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
cd $D
# legs: P314, OMP/OPENBLAS=1, NPY_DISABLE set. NC_W/NC_TREE/NC_WS point at the NC root -- the replay
# core reads $NC_W/work/axes.npz, and this is also the tree NC_FEATURES was built from, so the only
# thing this rerun changes versus the first pass is the environment.
rm -f $W/work/legs.npz $W/work/NC_LEGS_RECEIPT.json $W/receipts/P3_LEGS.json
echo "$(date -u +%H:%M:%S) legs start"
NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws NC_CFG=$W/inputs/bundle_config.json \
  nice -n 10 $P314 -u nc_legs.py $W/work/NEWS_FEATURES.npz $W/work/king/KING_OOF.npz $W/work/legs.npz \
  > $L/chain_legs_corrected.log 2>&1
echo "legs rc=$? $(date -u +%H:%M:%S)"; tail -1 $L/chain_legs_corrected.log
# re-stage post_king (the receipt must bind the NEW legs.npz; the old binding is gone)
echo "$(date -u +%H:%M:%S) re-stage post_king"
nice -n 10 python3 $D/news2_stage_inputs.py $W $W $W/receipts/STAGE_POST_KING.json --phase post_king > $L/chain_stage_post_king.log 2>&1
echo "stage rc=$?"; tail -1 $L/chain_stage_post_king.log
# F10: PV, NPY_DISABLE UNSET, OMP/OPENBLAS=2, both seeds concurrently; refuse if the GPU is busy
if [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)" ]; then echo "GPU busy: refuse"; exit 7; fi
rm -rf $W/work/f10_s42 $W/work/f10_s2027
echo "$(date -u +%H:%M:%S) f10 start"
unset NPY_DISABLE_CPU_FEATURES
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid nice -n 10 $PV -u news2_train_f10.py --seed 42   > $L/chain_f10_s42.log   2>&1 < /dev/null & P42=$!
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid nice -n 10 $PV -u news2_train_f10.py --seed 2027 > $L/chain_f10_s2027.log 2>&1 < /dev/null & P2027=$!
echo "$P42" > $L/f10_s42.pgid; echo "$P2027" > $L/f10_s2027.pgid
echo "f10 pgids $P42 $P2027"
R42=0; wait $P42 || R42=$?; R2027=0; wait $P2027 || R2027=$?
echo "f10 rc $R42 $R2027 $(date -u +%H:%M:%S)"
[ $R42 -eq 0 ] && [ $R2027 -eq 0 ]
echo "P3_CORRECTED_DONE $(date -u +%H:%M:%S)"
