#!/bin/sh
# baseline tables (prereg docs/PREREG_baseline_tables_certified_2026-09-19.md) — VERBATIM commands, pod2, CPU only.
# cwd = /workspace/baseline_tables_2026-09-19/devices ; writes only under /workspace/baseline_tables_2026-09-19/ and /dev/shm/bt_*.
# 0. copies (sha-checked by every device): replay_exec_2026-09-19/{exec_sim.py,simlib.py,v1b_gate.py,v1_gate.py,CALIBRATION_v3_POOLED_20260826_20260910.json,
#    INPUT_MANIFEST.json} -> devices/exec_copy/ ; the executor mirror is read in place at /workspace/replay_r_2026-09-19/work/exec_mirror (manifest-checked).
set -e
R=/workspace/baseline_tables_2026-09-19
cd $R/devices
# 1. full 5-minute price grids (old stream-R table and restored raw table), bitwise-gated against the pinned tables at every pinned sample
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_prices_full.py PATH,HOME,LC_CTYPE > $R/logs/bt_prices_full.log 2>&1
# 2. G0 state variables + labels extended to 2026-09-18T20Z (prefix proof bitwise vs the published files)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_g0_extend.py PATH,HOME,LC_CTYPE $R/g0x > $R/logs/bt_g0_extend.log 2>&1
# 3. smoke for the battery's D7 (3 seeds, 60 anchors; code check, not results)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json --smoke 2025-03-01T00:00:00Z 60 0,1,2 "S2_A0pred_s42|CMB|rule|raw|UAFE" battery_d7 > $R/logs/smoke_battery_d7.log 2>&1
# 4. driver battery (exit 0 only if every baseline is green and every mutation red)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs_smoke/battery_d7/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_BATTERY.json > $R/logs/bt_battery.log 2>&1
# 5. full runs: 4 runs x 32 seeds (reconciliation steps ① and ② on P2-CMB only)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json > $R/logs/bt_launch_full.log 2>&1
# 6. post-run: D7 on every full run directory (the 32-path mean = the average of the per-path files)
for d in S2_A0pred_s42_CMB_rule_old_LEGACY S2_A0pred_s42_CMB_rule_raw_UAFE S2_A0pred_s2027_CMB_rule_old_LEGACY S2_A0pred_s2027_CMB_rule_raw_UAFE; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1
done
# 7. reconciliation steps ① and ② (table device CLI)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py recon \
  /workspace/replay_r_2026-09-19/work/runs/S2_A0pred_s42_CMB_rule/SIM_S2_A0pred_s42_CMB_rule.npz /workspace/replay_r_2026-09-19/work/runs/S2_A0pred_s2027_CMB_rule/SIM_S2_A0pred_s2027_CMB_rule.npz \
  $R/runs/S2_A0pred_s42_CMB_rule_old_LEGACY $R/runs/S2_A0pred_s2027_CMB_rule_old_LEGACY $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/runs/S2_A0pred_s2027_CMB_rule_raw_UAFE \
  $R/receipts/BT_RECON_steps12_P2CMB.json > $R/logs/bt_recon.log 2>&1
# table-device self-test (Mac): /usr/bin/python3 multi_asset/exports/research/baseline_tables_2026-09-19/devices/bt_tables_selftest.py multi_asset/exports/research/replay_r_2026-09-19/receipts
