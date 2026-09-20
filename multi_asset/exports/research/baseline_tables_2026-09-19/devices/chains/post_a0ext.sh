#!/bin/bash
# post-run chain for the extended A0 run: bitwise control vs the published runs, battery, run summary, tables
set -u
R=/workspace/baseline_tables_2026-09-19
cd $R/devices_v3 || exit 1
for t in scaled_rule_raw_UAFE lit_rule_raw_UAFE scaled_rule_raw_UAFE_fee_x1.25 scaled_rule_raw_UAFE_slip_x1.5 scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_ext_control.py PATH,HOME,LC_CTYPE $R/runs/OBJB_A0_$t $R/runs/OBJB_A0X_$t 32 9139 $R/receipts/BT_EXT_CONTROL_$t.json > $R/logs/bt_ext_control_$t.log 2>&1
  echo "CONTROL EXIT $? $t"; grep "BT_EXT_CONTROL VERDICT" $R/logs/bt_ext_control_$t.log
done
for d in OBJB_A0X_scaled_rule_raw_UAFE OBJB_A0X_lit_rule_raw_UAFE OBJB_A0X_scaled_rule_raw_UAFE_fee_x1.25 OBJB_A0X_scaled_rule_raw_UAFE_slip_x1.5 OBJB_A0X_scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1
  echo "BATTERY EXIT $? $d"; grep "BT_BATTERY VERDICT" $R/logs/bt_battery_post_$d.log
done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_run_summary.py $R/receipts/BT_LAUNCH_full_a0x.json $R/runs $R/receipts/BT_RUN_SUMMARY_A0X.json > $R/logs/bt_run_summary_a0x.log 2>&1
echo "RUN_SUMMARY EXIT $?"; tail -1 $R/logs/bt_run_summary_a0x.log
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py main_a0 $R/RUN_CONFIG_main_A0ext_2026-09-20.json $R/runs $R/g0x/g0_labels_x0918.npz $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_RECON_steps12_P2CMB.json $R/receipts/BT_MAIN_A0X.json > $R/logs/bt_main_a0x.log 2>&1
echo "MAIN_A0X EXIT $?"; tail -2 $R/logs/bt_main_a0x.log
