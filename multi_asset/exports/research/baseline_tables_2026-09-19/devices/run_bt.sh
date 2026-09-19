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
# 5. full runs: 4 runs x 32 seeds (reconciliation steps ① and ② on P2-CMB only). AS EXECUTED 2026-09-19:
#   5a 11:17:36Z launcher v1 (bt_launch.py a2f70928, PGID 1265729): wrote 87/128 paths, then its memory gate (v1: max − current + inactive_file)
#      read 15 GiB < 22 GiB because another agent's ACTIVE page cache counted as used (anon was 18.8 of 61 GB); it idled from 1,440 s; stopped by its
#      own PGID at ~11:47Z (kill -TERM -1265729; the group held only that idle parent). Its receipt was never written; the log is kept.
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json > $R/logs/bt_launch_full.log 2>&1
#   5b 11:48Z launcher v2 (bt_launch.py 9f4c29b0: gate = max − anon − shmem; --resume skips sha-consistent existing paths), PGID 1274214: 41 paths,
#      receipt BT_LAUNCH_full_r1.json lists all 128 (resumed_existing true / false). Same bt_driver_lib 6cec5b2e / bt_hist_sim31 8ae6e2a4 for all 128.
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json --resume r1 > $R/logs/bt_launch_full_resume_r1.log 2>&1
# 6. next device versions (bt_driver_lib 1f70029b with the §3.4 cost-cell override, bt_battery 4c3f8729 with D10, bt_run_summary, bt_recon_render,
#    bt_reproduce_path) were run from $R/devices_next (bt_tables 01df8155 identical); they are the versions committed with the result.
cd $R/devices_next
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs_smoke/battery_d7/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_BATTERY_v2_smoke.json > $R/logs/bt_battery_v2_smoke.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_reproduce_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json "S2_A0pred_s42|CMB|rule|old|LEGACY" 0 $R/runs/S2_A0pred_s42_CMB_rule_old_LEGACY/PATH_S2_A0pred_s42_CMB_rule_old_LEGACY_seed_00.npz $R/receipts/BT_REPRODUCE_PATH_v2driver_s42_old_seed00.json > $R/logs/bt_reproduce_path.log 2>&1
# 7. post-run: the battery (incl. D7: the 32-path mean = the average of the per-path files) on every full run directory
for d in S2_A0pred_s42_CMB_rule_old_LEGACY S2_A0pred_s42_CMB_rule_raw_UAFE S2_A0pred_s2027_CMB_rule_old_LEGACY S2_A0pred_s2027_CMB_rule_raw_UAFE; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1
done
# 8. run summary + reconciliation steps ① and ② (table device CLI) + rendering
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_run_summary.py $R/receipts/BT_LAUNCH_full_r1.json $R/runs $R/receipts/BT_RUN_SUMMARY.json
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py recon \
  /workspace/replay_r_2026-09-19/work/runs/S2_A0pred_s42_CMB_rule/SIM_S2_A0pred_s42_CMB_rule.npz /workspace/replay_r_2026-09-19/work/runs/S2_A0pred_s2027_CMB_rule/SIM_S2_A0pred_s2027_CMB_rule.npz \
  $R/runs/S2_A0pred_s42_CMB_rule_old_LEGACY $R/runs/S2_A0pred_s2027_CMB_rule_old_LEGACY $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/runs/S2_A0pred_s2027_CMB_rule_raw_UAFE \
  $R/receipts/BT_RECON_steps12_P2CMB.json > $R/logs/bt_recon.log 2>&1
# (Mac) /usr/bin/python3 devices/bt_recon_render.py receipts/pod2/receipts/BT_RECON_steps12_P2CMB.json receipts/pod2/receipts/BT_RUN_SUMMARY.json receipts/RECON_TABLES_rendered.md
# table-device self-test (Mac): /usr/bin/python3 multi_asset/exports/research/baseline_tables_2026-09-19/devices/bt_tables_selftest.py multi_asset/exports/research/replay_r_2026-09-19/receipts
# table-device self-test (pod2): bt_tables_selftest.py $R/work/rtab  (rtab = symlinks to stream R's R_TABLES.json and the two SIM_*_CMB_rule.npz)
