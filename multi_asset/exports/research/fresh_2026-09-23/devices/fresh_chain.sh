#!/bin/bash
# FRESH chain after King + legs: F10 (both seeds on the GPU, only once NEW_S's chain logged DONE f10) → combo → adapter →
# configs (derived from NEW_S's configs) → engine → R-P readings.  Statistics / extension / report run separately, because
# they need NEW_S's own engine runs to be finished.
# pod2 only; every step logs to logs/chain_<step>.log and the chain stops at the first non-zero exit.
# Own root /dev/shm/fresh_2026-09-23 (noexec tmpfs: python is invoked through the interpreter).
set -e
W=/dev/shm/fresh_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs
N=/dev/shm/news_2026-09-23
PV=/workspace/venv/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
step() { echo "$(date -u +%H:%M:%S) START $1" >> $L/chain.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" >> $L/chain.log; }
cd $D
# 0. two gates, BOTH required before the GPU step:
#    (a) PREREG §6: do not touch the GPU until NEW_S's chain has logged DONE f10;
#    (b) this arm's own legs must exist — fresh_train_f10.py consumes work/legs.npz and receipts/P3_LEGS.json,
#        so starting on (a) alone would run the trainer against a missing input.
step wait_news_f10_and_own_legs
while ! grep -q "DONE f10" $N/logs/chain.log || [ ! -f $W/receipts/P3_LEGS.json ] || [ ! -f $W/work/legs.npz ]; do sleep 30; done
done_ wait_news_f10_and_own_legs
# 1. F10: both seeds concurrently, same interpreter/torch as NEW_S; refuse if someone else is on the GPU
step f10
if [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)" ]; then echo "GPU busy: refuse" >> $L/chain.log; exit 7; fi
unset NPY_DISABLE_CPU_FEATURES
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid $PV -u fresh_train_f10.py --seed 42 > $L/chain_f10_s42.log 2>&1 < /dev/null & P42=$!
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid $PV -u fresh_train_f10.py --seed 2027 > $L/chain_f10_s2027.log 2>&1 < /dev/null & P2027=$!
echo "f10 pgids $P42 $P2027" >> $L/chain.log
R42=0; wait $P42 || R42=$?; R2027=0; wait $P2027 || R2027=$?
echo "f10 rc $R42 $R2027" >> $L/chain.log
[ $R42 -eq 0 ] && [ $R2027 -eq 0 ]
done_ f10
# 1b. deployment-candidate F10 (FINAL fit at the data end) — GPU, after the OOF folds
step final_f10
setsid $PV -u fresh_final_fit.py --leg f10 --seed 42 > $L/chain_final_f10.log 2>&1 < /dev/null & PF=$!
echo "final_f10 pgid $PF" >> $L/chain.log
RF=0; wait $PF || RF=$?; echo "final_f10 rc $RF" >> $L/chain.log; [ $RF -eq 0 ]
done_ final_f10
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
step combo
for s in 42 2027; do OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 8 $PV -u fresh_combo.py --seed $s > $L/chain_combo_s$s.log 2>&1; done
done_ combo
unset NPY_DISABLE_CPU_FEATURES
mkdir -p $W/targets $W/configs $W/receipts/engine $W/scratch $W/runs
step adapter
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/fresh_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/chain_adapter_specs.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter_test.py PATH,HOME,LC_CTYPE $W/configs/ADAPTER_SPEC_FRESH_s42.json $W/scratch/adapter_test_s42 $W/receipts/engine/FRESH_ADAPTER_TEST_s42.json > $L/chain_adapter_test.log 2>&1
for s in 42 2027; do env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE $W/configs/ADAPTER_SPEC_FRESH_s$s.json $W/targets/TARGETS_FRESH_s$s.npz $W/targets/TARGETS_FRESH_s$s.json > $L/chain_adapter_s$s.log 2>&1; done
done_ adapter
# 2. configs are derived from NEW_S's own configs: wait for them
step wait_news_configs
while [ ! -f $N/configs/RUN_CONFIG_NEWS_s2027X_2026-09-23.json ]; do sleep 60; done
done_ wait_news_configs
step configs
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/fresh_make_configs.py PATH,HOME,LC_CTYPE $W/configs $W/targets/TARGETS_FRESH_s42.json $W/targets/TARGETS_FRESH_s2027.json $W/receipts/engine/FRESH_CONFIG_DIFF.json > $L/chain_configs.log 2>&1
done_ configs
step engine
cd $E
for pair in "fresh_s42:RUN_CONFIG_FRESH_s42_2026-09-23.json" "fresh_s2027:RUN_CONFIG_FRESH_s2027_2026-09-23.json" "fresh_s42x:RUN_CONFIG_FRESH_s42X_2026-09-23.json" "fresh_s2027x:RUN_CONFIG_FRESH_s2027X_2026-09-23.json"; do
  LB=${pair%%:*}; C=${pair#*:}
  setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 $PV -B bt_launch.py PATH,HOME,LC_CTYPE $W/configs/$C --resume $LB > $L/chain_launch_$LB.log 2>&1 < /dev/null &
  echo "launch $LB pid $!" >> $L/chain.log; sleep 20
done
wait
grep -h "VERDICT" $L/chain_launch_*.log >> $L/chain.log || true
done_ engine
step readings
B=/workspace/baseline_tables_2026-09-19
for a in "FRESH_s42:FRESH_s42:RUN_CONFIG_FRESH_s42_2026-09-23.json" "FRESH_s2027:FRESH_s2027:RUN_CONFIG_FRESH_s2027_2026-09-23.json"; do
  ARM=$(echo $a | cut -d: -f1); PFX=$(echo $a | cut -d: -f2); CFG=$(echo $a | cut -d: -f3)
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_Preading_A0_2026-09-20.json  $W/configs/$CFG $PFX $W/runs "FRESH $ARM" $W/configs/RUN_CONFIG_Preading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_P2reading_A0_2026-09-20.json $W/configs/$CFG $PFX $W/runs "FRESH $ARM" $W/configs/RUN_CONFIG_P2reading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_reading.py  PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_Preading_$ARM.json  $W/receipts/engine/BT_P_READING_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p2_reading.py PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_P2reading_$ARM.json $W/receipts/engine/BT_P2_READING_$ARM.json >> $L/chain_readings.log 2>&1
done
done_ readings
step export
cd $D; $PV -u fresh_export_models.py > $L/chain_export.log 2>&1
done_ export
echo "CHAIN_DONE_THROUGH_READINGS" >> $L/chain.log
