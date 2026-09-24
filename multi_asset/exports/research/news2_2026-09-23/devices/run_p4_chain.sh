#!/bin/bash
# NEW_S2 P4: combo -> adapter -> configs -> engine (4 runs x 32 paths) -> R-P readings -> verdict -> ext.
#
# Derived step by step from /dev/shm/news_2026-09-23/devices/news_chain_resume.sh, changing ONLY:
#   root        /dev/shm/news_2026-09-23      -> /dev/shm/news2_2026-09-23
#   devices     news_*.py                     -> news2_*.py
#   arm labels  NEWS / news_s*                -> NEWS2 / news2_s*
#
# * Every step opens with news2_env_gate.py --check <step>, which refuses to start (rc 9) unless the
#   interpreter and the numerical environment match the NEW_S pin for that step (lead 2026-09-24: getting
#   it right once by hand is not a fix, the pin has to be enforced at the entry point).
#   Selftest: receipts/ENV_GATE_SELFTEST.json, 8/8 = five baseline-green cells + three refused mutations.
set -e
W=/dev/shm/news2_2026-09-23; D=$W/devices; E=$W/engine; L=$W/logs; R=$W/receipts/engine
NS=/dev/shm/news_2026-09-23; S1=/dev/shm/ovn_2026-09-23; B=/workspace/baseline_tables_2026-09-19
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
NPY="X86_V4 AVX512_ICL AVX512_SPR"
GATE=$D/news2_env_gate.py
step() { echo "$(date -u +%H:%M:%S) START $1" | tee -a $L/chain2.log; }
done_() { echo "$(date -u +%H:%M:%S) DONE $1" | tee -a $L/chain2.log; }

cd $D
step combo
for s in 42 2027; do
  rm -rf $W/work/combo_s$s
  NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $P314 $GATE --check combo $R/ENV_GATE_combo.json | tee -a $L/chain2.log
  NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 $P314 -u news2_combo.py --seed $s > $L/chain_combo_s$s.log 2>&1
done
done_ combo

step adapter
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check adapter $R/ENV_GATE_adapter.json | tee -a $L/chain2.log
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_adapter_specs.py PATH,HOME,LC_CTYPE $W > $L/chain_adapter_specs.log 2>&1
cd $E
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter_test.py PATH,HOME,LC_CTYPE \
  $W/configs/ADAPTER_SPEC_NEWS2_s42.json $W/scratch/adapter_test_s42 $R/NEWS2_ADAPTER_TEST_s42.json > $L/chain_adapter_test.log 2>&1
for s in 42 2027; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B ovn_adapter.py PATH,HOME,LC_CTYPE \
    $W/configs/ADAPTER_SPEC_NEWS2_s$s.json $W/targets/TARGETS_NEWS2_s$s.npz $W/targets/TARGETS_NEWS2_s$s.json > $L/chain_adapter_s$s.log 2>&1
done
done_ adapter
# the combo targets, for lead (M3c needs s42 the moment it exists) -- FULL sha, both seeds
for s in 42 2027; do
  echo "TARGET_s$s PATH=$W/targets/TARGETS_NEWS2_s$s.npz SHA256=$(sha256sum $W/targets/TARGETS_NEWS2_s$s.npz | cut -d" " -f1)" | tee -a $L/chain2.log
done

step configs
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check configs $R/ENV_GATE_configs.json | tee -a $L/chain2.log
env -i PATH=/usr/bin:/bin HOME=/root $PV -B $D/news2_make_configs.py PATH,HOME,LC_CTYPE \
  $W/configs $W/targets/TARGETS_NEWS2_s42.json $W/targets/TARGETS_NEWS2_s2027.json \
  $R/NEWS2_CONFIG_DIFF.json > $L/chain_configs.log 2>&1
done_ configs

# * /dev/shm headroom, MEASURED here, before the engine step (lead via the integrator: the 4.1 GiB figure
#   was measured on NEW_S inputs; nobody has measured the NC inputs). Below target -> STOP and report.
#   No other agent files are ever deleted to get under it.
step shm_gate
FREE_KIB=$(df -k /dev/shm | tail -1 | awk '{print $4}')
FREE_GIB=$(awk -v k="$FREE_KIB" 'BEGIN{printf "%.2f", k/1048576}')
echo "SHM_FREE_GIB=$FREE_GIB (target >= 6.00 before the engine step)" | tee -a $L/chain2.log
python3 - "$FREE_GIB" "$R/SHM_HEADROOM_BEFORE_ENGINE.json" <<'PYEOF'
import json, subprocess, sys, time
free = float(sys.argv[1])
json.dump({"receipt": "SHM_HEADROOM_BEFORE_ENGINE.json",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "measured_free_gib": free, "target_gib": 6.0, "meets_target": free >= 6.0,
           "why": "the 4.1 GiB engine figure was measured on NEW_S inputs; the NC inputs (NC_FEATURES 2.96 GB) "
                  "have never been measured, so the headroom is measured here rather than assumed.",
           "df_k": subprocess.run(["df", "-k", "/dev/shm"], capture_output=True, text=True).stdout,
           "rule": "below target -> stop and report to lead; never delete another agent files to get under it"},
          open(sys.argv[2], "w"), indent=1)
PYEOF
if awk -v f="$FREE_GIB" 'BEGIN{exit !(f < 6.0)}'; then
  echo "STOP: /dev/shm free ${FREE_GIB} GiB < 6.00 GiB target. Not starting the engine step; reporting to lead." | tee -a $L/chain2.log
  echo "P4_STOPPED_AT_SHM_GATE $(date -u +%H:%M:%S)" | tee -a $L/chain2.log
  exit 8
fi
done_ shm_gate

step engine
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check engine $R/ENV_GATE_engine.json | tee -a $L/chain2.log
for pair in "news2_s42:RUN_CONFIG_NEWS2_s42_2026-09-23.json" "news2_s2027:RUN_CONFIG_NEWS2_s2027_2026-09-23.json" "news2_s42x:RUN_CONFIG_NEWS2_s42X_2026-09-23.json" "news2_s2027x:RUN_CONFIG_NEWS2_s2027X_2026-09-23.json"; do
  LB=${pair%%:*}; C=${pair#*:}
  setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $PV -B bt_launch.py PATH,HOME,LC_CTYPE $W/configs/$C --resume $LB > $L/chain_launch_$LB.log 2>&1 < /dev/null &
  echo "launch $LB pid $!" | tee -a $L/chain2.log; sleep 20
done
wait
grep -h "VERDICT" $L/chain_launch_*.log >> $L/chain2.log || true
done_ engine

step readings
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check readings $R/ENV_GATE_readings.json | tee -a $L/chain2.log
for a in "NEWS2_s42:NEWS2_s42:RUN_CONFIG_NEWS2_s42_2026-09-23.json" "NEWS2_s2027:NEWS2_s2027:RUN_CONFIG_NEWS2_s2027_2026-09-23.json"; do
  ARM=$(echo $a | cut -d: -f1); PFX=$(echo $a | cut -d: -f2); CFG=$(echo $a | cut -d: -f3)
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_Preading_A0_2026-09-20.json  $W/configs/$CFG $PFX $W/runs "NEWS2 $ARM" $W/configs/RUN_CONFIG_Preading_$ARM.json  >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_config_for.py PATH,HOME,LC_CTYPE $B/RUN_CONFIG_P2reading_A0_2026-09-20.json $W/configs/$CFG $PFX $W/runs "NEWS2 $ARM" $W/configs/RUN_CONFIG_P2reading_$ARM.json >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p_reading.py  PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_Preading_$ARM.json  $R/BT_P_READING_$ARM.json  >> $L/chain_readings.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B bt_p2_reading.py PATH,HOME,LC_CTYPE $W/configs/RUN_CONFIG_P2reading_$ARM.json $R/BT_P2_READING_$ARM.json >> $L/chain_readings.log 2>&1
done
done_ readings

step stats
cp -p $NS/devices/news_stats.py $E/
cp -p $D/news2_stats.py $D/news2_ext.py $D/news2_env_gate.py $E/
cd $E
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check stats $R/ENV_GATE_stats.json | tee -a $L/chain2.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news2_stats.py PATH,HOME,LC_CTYPE \
  $S1/runs $NS/runs $W/runs $B/runs \
  $S1/receipts/BT_P_READING_OVN_OLD.json $S1/receipts/BT_P_READING_OVN_OLD_HOLD.json \
  $NS/receipts/engine/BT_P_READING_NEWS_s42.json $NS/receipts/engine/BT_P_READING_NEWS_s2027.json \
  $R/BT_P_READING_NEWS2_s42.json $R/BT_P_READING_NEWS2_s2027.json \
  $R/NEWS2_STATS.json > $L/chain_stats.log 2>&1
done_ stats

step ext
env -i PATH=/usr/bin:/bin HOME=/root $PV $GATE --check ext $R/ENV_GATE_ext.json | tee -a $L/chain2.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B news2_ext.py PATH,HOME,LC_CTYPE $W/runs $B/runs $R/NEWS2_EXT.json > $L/chain_ext.log 2>&1
done_ ext
echo "P4_CHAIN_DONE $(date -u +%H:%M:%S)" | tee -a $L/chain2.log
