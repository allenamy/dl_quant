#!/bin/bash
# post-run chain for the v4 arm: battery, run summary, v4 tables (incl. step 3), the pairing table, reading P
set -u
R=/workspace/baseline_tables_2026-09-19
cd $R/devices_v3 || exit 1
for d in OBJB_V4_scaled_rule_raw_UAFE OBJB_V4_lit_rule_raw_UAFE OBJB_V4_scaled_rule_raw_UAFE_fee_x1.25 OBJB_V4_scaled_rule_raw_UAFE_slip_x1.5 OBJB_V4_scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1
  echo "BATTERY EXIT $? $d"; grep "BT_BATTERY VERDICT" $R/logs/bt_battery_post_$d.log
done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_run_summary.py $R/receipts/BT_LAUNCH_full_v4.json $R/runs $R/receipts/BT_RUN_SUMMARY_V4.json > $R/logs/bt_run_summary_v4.log 2>&1
echo "RUN_SUMMARY EXIT $?"; tail -1 $R/logs/bt_run_summary_v4.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py main_a0 $R/RUN_CONFIG_main_V4_2026-09-20.json $R/runs $R/g0x/g0_labels_x0918.npz $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_RECON_steps12_P2CMB.json $R/receipts/BT_MAIN_V4.json > $R/logs/bt_main_v4.log 2>&1
echo "MAIN_V4 EXIT $?"; tail -1 $R/logs/bt_main_v4.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py main_pair $R/RUN_CONFIG_main_A0_2026-09-19.json $R/RUN_CONFIG_main_V4_2026-09-20.json $R/runs $R/receipts/BT_MAIN_PAIR_A0_vs_V4.json > $R/logs/bt_main_pair.log 2>&1
echo "MAIN_PAIR EXIT $?"; tail -1 $R/logs/bt_main_pair.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_p_config_for.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_A0_2026-09-20.json $R/RUN_CONFIG_main_V4_2026-09-20.json OBJB_V4 $R/runs "the v4 retrain arm" $R/RUN_CONFIG_Preading_V4_2026-09-20.json
echo "P_CONFIG EXIT $?"
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_V4_2026-09-20.json $R/receipts/BT_P_READING_V4.json
echo "P_READING EXIT $?"
