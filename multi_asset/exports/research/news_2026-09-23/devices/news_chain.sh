#!/bin/bash
# NEWS P2 merge → P3 (King, legs, F10 s42 ∥ s2027 on GPU) → P4 (combo, adapter + red/green test, configs, engine runs,
# R-P readings, S1–S5 statistics). pod2 only; every step logs to logs/chain_<step>.log and the chain stops at the first
# non-zero exit. Own root /dev/shm/news_2026-09-23 (noexec tmpfs: python is invoked through the interpreter).
set -e
W=/dev/shm/news_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
step() { echo "$(date -u +%H:%M:%S) START $1" >> $L/chain.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" >> $L/chain.log; }
# 0. wait for all 104 P2 shards
step wait_shards
while [ "$(ls $W/work/p2_shards/*.npz.json 2>/dev/null | wc -l)" -lt 104 ]; do sleep 30; done
done_ wait_shards
cd $D
step merge;  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 5 $P314 -u news_p2_build.py merge > $L/chain_merge.log 2>&1; done_ merge
step king;   nice -n 5 $P314 -u news_train_king.py > $L/chain_king.log 2>&1; done_ king
step legs;   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 5 $P314 -u news_legs.py > $L/chain_legs.log 2>&1; done_ legs
# F10: both seeds concurrently on the (idle) GPU, same interpreter/torch as the NEW recipe; refuse if the GPU is busy
step f10
if [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)" ]; then echo "GPU busy: refuse" >> $L/chain.log; exit 7; fi
unset NPY_DISABLE_CPU_FEATURES
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid $PV -u news_train_f10.py --seed 42 > $L/chain_f10_s42.log 2>&1 < /dev/null & P42=$!
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid $PV -u news_train_f10.py --seed 2027 > $L/chain_f10_s2027.log 2>&1 < /dev/null & P2027=$!
echo "f10 pgids $P42 $P2027" >> $L/chain.log
R42=0; wait $P42 || R42=$?; R2027=0; wait $P2027 || R2027=$?
echo "f10 rc $R42 $R2027" >> $L/chain.log
[ $R42 -eq 0 ] && [ $R2027 -eq 0 ]
done_ f10
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
step combo
for s in 42 2027; do OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 5 $P314 -u news_combo.py --seed $s > $L/chain_combo_s$s.log 2>&1; done
done_ combo
rm -f $W/work/cache_x0918r_data.npy   # free 5.8 GB of shmem before the engine's memory gate (re-creatable from the npz)
unset NPY_DISABLE_CPU_FEATURES
mkdir -p $W/targets $W/configs $W/receipts/engine $W/scratch
step adapter
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/chain_adapter_specs.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter_test.py PATH,HOME,LC_CTYPE $W/configs/ADAPTER_SPEC_NEWS_s42.json $W/scratch/adapter_test_s42 $W/receipts/engine/NEWS_ADAPTER_TEST_s42.json > $L/chain_adapter_test.log 2>&1
for s in 42 2027; do env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE $W/configs/ADAPTER_SPEC_NEWS_s$s.json $W/targets/TARGETS_NEWS_s$s.npz $W/targets/TARGETS_NEWS_s$s.json > $L/chain_adapter_s$s.log 2>&1; done
done_ adapter
step configs
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news_make_configs.py PATH,HOME,LC_CTYPE $W/configs $W/targets/TARGETS_NEWS_s42.json $W/targets/TARGETS_NEWS_s2027.json $W/receipts/engine/NEWS_CONFIG_DIFF.json > $L/chain_configs.log 2>&1
done_ configs
step engine
for pair in "news_s42:RUN_CONFIG_NEWS_s42_2026-09-23.json" "news_s2027:RUN_CONFIG_NEWS_s2027_2026-09-23.json" "news_s42x:RUN_CONFIG_NEWS_s42X_2026-09-23.json" "news_s2027x:RUN_CONFIG_NEWS_s2027X_2026-09-23.json"; do
  LB=${pair%%:*}; C=${pair#*:}
  setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE $W/configs/$C --resume $LB > $L/chain_launch_$LB.log 2>&1 < /dev/null &
  echo "launch $LB pid $!" >> $L/chain.log; sleep 20
done
wait
grep -h "VERDICT" $L/chain_launch_*.log >> $L/chain.log || true
done_ engine
step readings
B=/workspace/baseline_tables_2026-09-19
for a in "NEWS_s42:NEWS_s42:RUN_CONFIG_NEWS_s42_2026-09-23.json" "NEWS_s2027:NEWS_s2027:RUN_CONFIG_NEWS_s2027_2026-09-23.json"; do
  ARM=$(echo $a | cut -d: -f1); PFX=$(echo $a | cut -d: -f2); CFG=$(echo $a | cut -d: -f3)
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_Preading_A0_2026-09-20.json  $W/configs/$CFG $PFX $W/runs "NEWS $ARM" $W/configs/RUN_CONFIG_Preading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_P2reading_A0_2026-09-20.json $W/configs/$CFG $PFX $W/runs "NEWS $ARM" $W/configs/RUN_CONFIG_P2reading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_reading.py  PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_Preading_$ARM.json  $W/receipts/engine/BT_P_READING_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p2_reading.py PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_P2reading_$ARM.json $W/receipts/engine/BT_P2_READING_$ARM.json >> $L/chain_readings.log 2>&1
done
done_ readings
step stats
cp -p $D/news_stats.py $E/
S1=/dev/shm/ovn_2026-09-23
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news_stats.py PATH,HOME,LC_CTYPE $S1/runs $W/runs $B/runs $S1/receipts/BT_P_READING_OVN_OLD_HOLD.json \
  $W/receipts/engine/BT_P_READING_NEWS_s42.json $W/receipts/engine/BT_P_READING_NEWS_s2027.json $S1/receipts/BT_P_READING_OVN_OLD.json $W/receipts/engine/NEWS_STATS.json > $L/chain_stats.log 2>&1
done_ stats
step ext
cp -p $D/news_ext.py $E/
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news_ext.py PATH,HOME,LC_CTYPE $W/runs $B/runs $W/receipts/engine/NEWS_EXT.json > $L/chain_ext.log 2>&1
done_ ext
echo "CHAIN_DONE" >> $L/chain.log
