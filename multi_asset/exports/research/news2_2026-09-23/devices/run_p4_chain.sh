#!/bin/bash
# NEW_S2 P4: combo -> adapter -> configs -> engine (4 runs x 32 paths) -> R-P readings -> verdict -> ext.
#
# Derived step by step from /dev/shm/news_2026-09-23/devices/news_chain_resume.sh, changing ONLY:
#   root        /dev/shm/news_2026-09-23      -> /dev/shm/news2_2026-09-23
#   devices     news_*.py                     -> news2_*.py
#   arm labels  NEWS / news_s*                -> NEWS2 / news2_s*
# Each step keeps that script's interpreter and environment verbatim, because the environment changes
# the numbers (see receipts/KING_ENV_SENSITIVITY.json: three environments, three different King OOFs,
# with identical version strings).
set -e
W=/dev/shm/news2_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs
NS=/dev/shm/news_2026-09-23; S1=/dev/shm/ovn_2026-09-23; B=/workspace/baseline_tables_2026-09-19
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
step() { echo "$(date -u +%H:%M:%S) START $1" | tee -a $L/chain2.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" | tee -a $L/chain2.log; }

export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
cd $D
step combo
for s in 42 2027; do
  rm -rf $W/work/combo_s$s
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 $P314 -u news2_combo.py --seed $s > $L/chain_combo_s$s.log 2>&1
done
done_ combo
unset NPY_DISABLE_CPU_FEATURES

step adapter
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/chain_adapter_specs.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter_test.py PATH,HOME,LC_CTYPE \
  $W/configs/ADAPTER_SPEC_NEWS2_s42.json $W/scratch/adapter_test_s42 $W/receipts/engine/NEWS2_ADAPTER_TEST_s42.json > $L/chain_adapter_test.log 2>&1
for s in 42 2027; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
    $W/configs/ADAPTER_SPEC_NEWS2_s$s.json $W/targets/TARGETS_NEWS2_s$s.npz $W/targets/TARGETS_NEWS2_s$s.json > $L/chain_adapter_s$s.log 2>&1
done
done_ adapter
# the s42 combo target, for lead (M3c needs it the moment it exists)
echo "S42_TARGET_PATH=$W/targets/TARGETS_NEWS2_s42.npz" | tee -a $L/chain2.log
echo "S42_TARGET_SHA256=$(sha256sum $W/targets/TARGETS_NEWS2_s42.npz | cut -d" " -f1)" | tee -a $L/chain2.log

step configs
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_make_configs.py PATH,HOME,LC_CTYPE \
  $W/configs $W/targets/TARGETS_NEWS2_s42.json $W/targets/TARGETS_NEWS2_s2027.json \
  $W/receipts/engine/NEWS2_CONFIG_DIFF.json > $L/chain_configs.log 2>&1
done_ configs

step engine
for pair in "news2_s42:RUN_CONFIG_NEWS2_s42_2026-09-23.json" "news2_s2027:RUN_CONFIG_NEWS2_s2027_2026-09-23.json" "news2_s42x:RUN_CONFIG_NEWS2_s42X_2026-09-23.json" "news2_s2027x:RUN_CONFIG_NEWS2_s2027X_2026-09-23.json"; do
  LB=${pair%%:*}; C=${pair#*:}
  setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE $W/configs/$C --resume $LB > $L/chain_launch_$LB.log 2>&1 < /dev/null &
  echo "launch $LB pid $!" | tee -a $L/chain2.log; sleep 20
done
wait
grep -h "VERDICT" $L/chain_launch_*.log >> $L/chain2.log || true
done_ engine

step readings
for a in "NEWS2_s42:NEWS2_s42:RUN_CONFIG_NEWS2_s42_2026-09-23.json" "NEWS2_s2027:NEWS2_s2027:RUN_CONFIG_NEWS2_s2027_2026-09-23.json"; do
  ARM=$(echo $a | cut -d: -f1); PFX=$(echo $a | cut -d: -f2); CFG=$(echo $a | cut -d: -f3)
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_Preading_A0_2026-09-20.json  $W/configs/$CFG $PFX $W/runs "NEWS2 $ARM" $W/configs/RUN_CONFIG_Preading_$ARM.json  >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_P2reading_A0_2026-09-20.json $W/configs/$CFG $PFX $W/runs "NEWS2 $ARM" $W/configs/RUN_CONFIG_P2reading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_reading.py  PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_Preading_$ARM.json  $W/receipts/engine/BT_P_READING_$ARM.json  >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p2_reading.py PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_P2reading_$ARM.json $W/receipts/engine/BT_P2_READING_$ARM.json >> $L/chain_readings.log 2>&1
done
done_ readings

step stats
cp -p $NS/devices/news_stats.py $E/          # the pinned AMENDMENT 2 statistics news2_stats imports
cp -p $D/news2_stats.py $D/news2_ext.py $E/
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news2_stats.py PATH,HOME,LC_CTYPE \
  $S1/runs $NS/runs $W/runs $B/runs \
  $S1/receipts/BT_P_READING_OVN_OLD.json $S1/receipts/BT_P_READING_OVN_OLD_HOLD.json \
  $NS/receipts/engine/BT_P_READING_NEWS_s42.json $NS/receipts/engine/BT_P_READING_NEWS_s2027.json \
  $W/receipts/engine/BT_P_READING_NEWS2_s42.json $W/receipts/engine/BT_P_READING_NEWS2_s2027.json \
  $W/receipts/engine/NEWS2_STATS.json > $L/chain_stats.log 2>&1
done_ stats

step ext
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news2_ext.py PATH,HOME,LC_CTYPE $W/runs $B/runs $W/receipts/engine/NEWS2_EXT.json > $L/chain_ext.log 2>&1
done_ ext
echo "P4_CHAIN_DONE $(date -u +%H:%M:%S)" | tee -a $L/chain2.log
