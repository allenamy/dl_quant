#!/bin/bash
# post-run chain on pod2: battery on each A0 run dir, run summary, A0 tables
set -u
R=/workspace/baseline_tables_2026-09-19
cd $R/devices_v3 || exit 1
for d in OBJB_A0_scaled_rule_raw_UAFE OBJB_A0_lit_rule_raw_UAFE OBJB_A0_scaled_rule_raw_UAFE_fee_x1.25 OBJB_A0_scaled_rule_raw_UAFE_slip_x1.5 OBJB_A0_scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1
  echo "EXIT $? $d" >> $R/logs/bt_battery_post_$d.log
  tail -1 $R/logs/bt_battery_post_$d.log
  grep -E "BT_BATTERY VERDICT" $R/logs/bt_battery_post_$d.log
done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_run_summary.py $R/receipts/BT_LAUNCH_full_a0.json $R/runs $R/receipts/BT_RUN_SUMMARY_A0.json > $R/logs/bt_run_summary_a0.log 2>&1
echo "RUN_SUMMARY EXIT $?"; tail -2 $R/logs/bt_run_summary_a0.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py main_a0 $R/RUN_CONFIG_main_A0_2026-09-19.json $R/runs $R/g0x/g0_labels_x0918.npz $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_RECON_steps12_P2CMB.json $R/receipts/BT_MAIN_A0.json > $R/logs/bt_main_a0.log 2>&1
echo "MAIN_A0 EXIT $?"; tail -3 $R/logs/bt_main_a0.log
