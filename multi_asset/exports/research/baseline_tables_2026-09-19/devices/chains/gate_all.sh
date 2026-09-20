#!/bin/bash
R=/workspace/baseline_tables_2026-09-19
cd $R/devices_v3 || exit 1
: > $R/logs/bt_gate_external_all.log
run() {  # $1 config, $2 run dir, $3 label
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_gate_external.py PATH,HOME,LC_CTYPE \
    $R/APPROVED_INPUTS_2026-09-20.json $R/$1 $R/runs/$2 32 --reproduce all --workers 4 $R/receipts/BT_GATE_EXTERNAL_$3.json > $R/logs/bt_gate_external_$3.log 2>&1
  echo "EXIT $? $3" >> $R/logs/bt_gate_external_all.log
  grep "BT_GATE_EXTERNAL VERDICT" $R/logs/bt_gate_external_$3.log >> $R/logs/bt_gate_external_all.log
}
run RUN_CONFIG_main_A0_2026-09-19.json    OBJB_A0_scaled_rule_raw_UAFE   A0_scaled
run RUN_CONFIG_main_A0ext_2026-09-20.json OBJB_A0X_scaled_rule_raw_UAFE  A0X_scaled
run RUN_CONFIG_main_V4_2026-09-20.json    OBJB_V4_scaled_rule_raw_UAFE   V4_scaled
echo DONE >> $R/logs/bt_gate_external_all.log
