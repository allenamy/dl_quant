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
# ---- after AMENDMENT 1 (f6a2a909e): adapter for object-B targets (fixtures only), extended prices, funding splice; run from $R/devices_v3 ----
cd $R/devices_v3
# 9. adapter test on fixtures built from the S2 books (try1 receipt kept: three test-code errors), then again on driver-lib v3b
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_objb_adapter_test.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/work/objb_fixture $R/receipts/BT_OBJB_ADAPTER_TEST.json > $R/logs/bt_objb_adapter_test.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs_smoke/battery_d7/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_BATTERY_v3_smoke.json > $R/logs/bt_battery_v3_smoke.log 2>&1
# 10. funding: overlap proof P2 ledger vs stream D ledger, then the explicit splice (P2 <= 2026-09-01T02:00Z, stream D after)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_funding_overlap.py PATH,HOME,LC_CTYPE $R/funding > $R/logs/bt_funding_overlap.log 2>&1
# 11. extended restored prices (1a1e221b4) on the full 5-minute grid to 2026-09-19T00:00Z
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_prices_full_x0918r.py PATH,HOME,LC_CTYPE > $R/logs/bt_prices_full_x0918r.log 2>&1
# 12. driver-lib v3b: adapter test + battery again
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_objb_adapter_test.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/work/objb_fixture $R/receipts/BT_OBJB_ADAPTER_TEST_v3b.json > $R/logs/bt_objb_adapter_test_v3b.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs_smoke/battery_d7/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_BATTERY_v3b_smoke.json > $R/logs/bt_battery_v3b_smoke.log 2>&1
# main tables: RUN_CONFIG_main_TEMPLATE_2026-09-19.json is refused by the driver until the lead's go fills the PENDING fields (object-B A0 / v4 targets, full-recipe start)
# ---- A0 part (lead 2026-09-19): EXECUTED after object-B A0_main targets landed (21:41Z); run from $R/devices_v3 ----
cd $R/devices_v3
# a. pre-run checks + frozen A0 config (gate F lineage, universe, full-recipe start; the universe part also ran earlier: BT_OBJB_PRERUN_universe.json)
#    G = sha256 of `git show d3596aced:multi_asset/exports/research/object_b_2026-09-19/receipts/GATE_F.json` = 916b109f181103191efff915923d1647e35e7a7dbdfc6caffa42077e7fc65b9c
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_objb_prerun.py PATH,HOME,LC_CTYPE full $R/receipts/BT_OBJB_PRERUN_A0.json $R/RUN_CONFIG_main_TEMPLATE_2026-09-19.json $R/RUN_CONFIG_main_A0_2026-09-19.json 916b109f181103191efff915923d1647e35e7a7dbdfc6caffa42077e7fc65b9c A0_main
# b. the adapter against the real target-file layout (lead's go, "before running" item 1)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_objb_layout_check.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_A0_2026-09-19.json $R/work/objb_fixture/TARGETS_FIX_full.npz $R/receipts/BT_OBJB_PRERUN_A0.json $R/work/objb_layout_fixture $R/receipts/BT_OBJB_LAYOUT_CHECK_A0.json > $R/logs/bt_objb_layout_check_A0.log 2>&1
# c. memory probe (launcher v2): one full-window path, sampled every 5 s by memsample.sh (Σ Pss of the process group, cgroup anon, memory PSI)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_A0_2026-09-19.json --smoke 2022-06-30T00:00:00Z 9139 0 "OBJB_A0|scaled|rule|raw|UAFE" memprobe > $R/logs/bt_launch_smoke_memprobe.log 2>&1
$R/memsample.sh <PGID of the probe> $R/logs/memprobe_samples.log
# d. launcher v3 (governor: own total <= 6 GB; PSI avg10 > 20 % for > 60 s => halve workers) — test
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch_governor_test.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_A0_2026-09-19.json 2023-06-30T04:00:00Z 3000 5 2.0 $R/receipts/BT_LAUNCH_GOVERNOR_TEST.json > $R/logs/bt_launch_governor_test.log 2>&1
# e. the five A0 runs x 32 seeds (max 4 workers), PGID recorded in $R/logs/full_a0.pgid; sampler alongside
setsid bash -c "env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_A0_2026-09-19.json --resume a0 > $R/logs/bt_launch_full_a0.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_a0.log"
$R/memsample.sh $(cat $R/logs/full_a0.pgid) $R/logs/full_a0_memsamples.log
# f. battery (D0-D11 on its own config; D7 on each A0 run directory), run summary, A0 tables
for d in OBJB_A0_scaled_rule_raw_UAFE OBJB_A0_lit_rule_raw_UAFE OBJB_A0_scaled_rule_raw_UAFE_fee_x1.25 OBJB_A0_scaled_rule_raw_UAFE_slip_x1.5 OBJB_A0_scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_battery.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_bt_2026-09-19.json $R/runs/$d $R/receipts/BT_BATTERY_post_$d.json > $R/logs/bt_battery_post_$d.log 2>&1; echo "EXIT $?" >> $R/logs/bt_battery_post_$d.log
done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_run_summary.py $R/receipts/BT_LAUNCH_full_a0.json $R/runs $R/receipts/BT_RUN_SUMMARY_A0.json
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_tables.py main_a0 $R/RUN_CONFIG_main_A0_2026-09-19.json $R/runs $R/g0x/g0_labels_x0918.npz $R/runs/S2_A0pred_s42_CMB_rule_raw_UAFE $R/receipts/BT_RECON_steps12_P2CMB.json $R/receipts/BT_MAIN_A0.json > $R/logs/bt_main_a0.log 2>&1
# (Mac) /usr/bin/python3 devices/bt_main_render.py receipts/pod2/receipts/BT_MAIN_A0.json receipts/pod2/receipts/BT_RUN_SUMMARY_A0.json receipts/A0_TABLES_rendered.md
# ---- EXTENSION run (lead 2026-09-20): object-B A0_ext targets 085d8858 (2022-01-31 -> 2026-09-18T20Z); its own run tags OBJB_A0X|* ----
# g. pre-run checks again on the ext targets + the frozen ext config (run_tag_suffix X keeps the published runs untouched)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_objb_prerun.py PATH,HOME,LC_CTYPE full $R/receipts/BT_OBJB_PRERUN_A0ext.json $R/RUN_CONFIG_main_TEMPLATE_2026-09-19.json $R/RUN_CONFIG_main_A0ext_2026-09-20.json 916b109f181103191efff915923d1647e35e7a7dbdfc6caffa42077e7fc65b9c A0_ext X > $R/logs/bt_objb_prerun_a0ext.log 2>&1
# h. the bitwise control device, self-tested first on an IDENTITY comparison (the same directory on both sides; try 1 went red and is kept)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_ext_control.py PATH,HOME,LC_CTYPE $R/runs/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0_scaled_rule_raw_UAFE 32 9139 $R/receipts/BT_EXT_CONTROL_selftest_identity.json > $R/logs/bt_ext_control_selftest.log 2>&1
# i. the five extended runs x 32 seeds, started after object B's v4 scoring went quiet (fast_exec workers 0, load 0.85); PGID in $R/logs/full_a0x.pgid
setsid bash -c "env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_A0ext_2026-09-20.json --resume a0x > $R/logs/bt_launch_full_a0x.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_a0x.log"
$R/memsample.sh $(cat $R/logs/full_a0x.pgid) $R/logs/full_a0x_memsamples.log
# j. post-run: the control on all five run pairs (9,139 shared anchors x 32 seeds), battery on each extended run directory, run summary, tables
bash $R/post_a0ext.sh > $R/logs/post_a0ext.log 2>&1
# (Mac) /usr/bin/python3 devices/bt_main_render.py receipts/pod2/receipts/BT_MAIN_A0X.json receipts/pod2/receipts/BT_RUN_SUMMARY_A0X.json receipts/A0EXT_TABLES_rendered.md
# k. after the lead's ruling (accept and name the junction-bar exception): the control device carries the pre-declared criterion
#    (bitwise except block-boundary bars, <= 4 ulp AND zero effect on every published quantity); the five controls and the identity
#    self-test were re-run under it (the strict-bitwise receipts are kept as *_try2_strict_bitwise.json)
for f in scaled_rule_raw_UAFE lit_rule_raw_UAFE scaled_rule_raw_UAFE_fee_x1.25 scaled_rule_raw_UAFE_slip_x1.5 scaled_rule_raw_UAFE_fill_x0.9; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_ext_control.py PATH,HOME,LC_CTYPE $R/runs/OBJB_A0_$f $R/runs/OBJB_A0X_$f 32 9139 $R/receipts/BT_EXT_CONTROL_$f.json > $R/logs/bt_ext_control_$f.log 2>&1
done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_ext_control.py PATH,HOME,LC_CTYPE $R/runs/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0_scaled_rule_raw_UAFE 32 9139 $R/receipts/BT_EXT_CONTROL_selftest_identity.json > $R/logs/bt_ext_control_selftest.log 2>&1
# l. reading P (AMENDMENT 2) on the published window and on the extended window; and the g-convention reconciliation
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_A0_2026-09-20.json $R/receipts/BT_P_READING_A0.json > $R/logs/bt_p_reading_a0.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_A0ext_2026-09-20.json $R/receipts/BT_P_READING_A0X.json >> $R/logs/post_a0ext.log 2>&1
for w in "2023-06-30T04:00:00Z 2025-12-31T20:00:00Z HIST" "2023-06-30T04:00:00Z 2023-12-31T20:00:00Z H2_2023" "2024-01-01T00:00:00Z 2024-12-31T20:00:00Z Y2024" "2025-01-01T00:00:00Z 2025-12-31T20:00:00Z Y2025" "2026-01-01T00:00:00Z 2026-08-31T00:00:00Z Y2026"; do
  set -- $w; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_g_convention.py PATH,HOME,LC_CTYPE $R/runs/OBJB_A0_scaled_rule_raw_UAFE 32 $1 $2 $R/receipts/BT_G_CONVENTION_$3.json
done
# (Mac) /usr/bin/python3 devices/bt_p_render.py receipts/pod2/receipts/BT_P_READING_A0.json  receipts/A0_P_TABLES_rendered.md
# (Mac) /usr/bin/python3 devices/bt_p_render.py receipts/pod2/receipts/BT_P_READING_A0X.json receipts/A0EXT_P_TABLES_rendered.md
# (Mac) /usr/bin/python3 devices/bt_p_reading_test.py <scratch> receipts/BT_P_READING_TEST_mac.json
# ---- EXECUTED: the v4 retrain arm (object B wrote TARGETS_V4_main at 2026-09-20T04:17Z; the lead's standing GO) ----
# m. pre-run checks with the arm parameter (device v3), then the frozen v4 config
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_objb_prerun.py PATH,HOME,LC_CTYPE full $R/receipts/BT_OBJB_PRERUN_V4.json $R/RUN_CONFIG_main_TEMPLATE_2026-09-19.json $R/RUN_CONFIG_main_V4_2026-09-20.json 916b109f181103191efff915923d1647e35e7a7dbdfc6caffa42077e7fc65b9c V4_main "" V4 > $R/logs/bt_objb_prerun_v4.log 2>&1
# n. the five v4 runs x 32 seeds, started after object B's v4 scoring went quiet (fast_exec 0, load 1.55); PGID in $R/logs/full_v4.pgid
setsid bash -c "env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_main_V4_2026-09-20.json --resume v4 > $R/logs/bt_launch_full_v4.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_v4.log"
$R/memsample.sh $(cat $R/logs/full_v4.pgid) $R/logs/full_v4_memsamples.log
# o. post-run chain: battery x5, run summary, v4 tables (incl. step 3), the §3.5 pairing table, the v4 reading-P config + reading P
bash $R/post_v4.sh > $R/logs/post_v4.log 2>&1
# (Mac) /usr/bin/python3 devices/bt_main_render.py receipts/pod2/receipts/BT_MAIN_V4.json receipts/pod2/receipts/BT_RUN_SUMMARY_V4.json receipts/V4_TABLES_rendered.md
# (Mac) /usr/bin/python3 devices/bt_pair_render.py receipts/pod2/receipts/BT_MAIN_PAIR_A0_vs_V4.json receipts/PAIR_A0_vs_V4_rendered.md
# (Mac) /usr/bin/python3 devices/bt_p_render.py receipts/pod2/receipts/BT_P_READING_V4.json receipts/V4_P_TABLES_rendered.md
# ---- round-6 review (R6-02 provenance gate, R6-03 halt/resume) — lead 2026-09-20 ----
# p. the approved-inputs table (cross-checked across the three frozen configs, every entry re-hashed from its own path)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_approved_inputs.py PATH,HOME,LC_CTYPE $R/APPROVED_INPUTS_2026-09-20.json $R/RUN_CONFIG_main_A0_2026-09-19.json $R/RUN_CONFIG_main_A0ext_2026-09-20.json $R/RUN_CONFIG_main_V4_2026-09-20.json
# q. the tamper cases against BOTH gates (copies only; nothing in runs/ is touched)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_gate_tamper_test.py PATH,HOME,LC_CTYPE $R/APPROVED_INPUTS_2026-09-20.json $R/RUN_CONFIG_main_A0_2026-09-19.json $R/runs_smoke/gov0_215215/OBJB_A0_scaled_rule_raw_UAFE 4 $R/work/tamper $R/receipts/BT_GATE_TAMPER_TEST.json > $R/logs/bt_gate_tamper_test.log 2>&1
# r. the external-provenance gate at FULL coverage on the three main-reading run directories (devices/chains/gate_all.sh)
bash $R/gate_all.sh          # writes receipts/BT_GATE_EXTERNAL_{A0,A0X,V4}_scaled.json and logs/bt_gate_external_all.log
# s. reading P2 (AMENDMENT 3): the three configs are the frozen P configs plus the pre-declared p2_reading block
for a in A0 A0ext V4; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p2_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_P2reading_${a}_2026-09-20.json $R/receipts/BT_P2_READING_${a}.json
done
# (Mac) /usr/bin/python3 devices/bt_p2_reading_test.py <scratch> receipts/BT_P2_READING_TEST_mac.json
# (Mac) for a in A0 A0ext V4; do /usr/bin/python3 devices/bt_p2_render.py receipts/pod2/receipts/BT_P2_READING_$a.json receipts/${a}_P2_TABLES_rendered.md; done
# t. E-0920-C 修复 + AMENDMENT 4(聚合合同 + 窗口切片语义): bt_agg.py 新增, bt_p_reading.py / bt_p2_reading.py 改走合同。
#    装置测试先跑(基线绿在前, 每条变异红), 再重出三条 P 与三条 P2; 任一退出码非 0 即停。
cd $R/devices_v3
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_agg_test.py $R/receipts/BT_AGG_TEST.json > $R/logs/bt_agg_test.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p_reading_test.py $R/work/pfix_scr $R/receipts/BT_P_READING_TEST_pod2.json > $R/logs/bt_p_reading_test.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p2_reading_test.py $R/work/p2fix_scr $R/receipts/BT_P2_READING_TEST_pod2.json > $R/logs/bt_p2_reading_test.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_A0_2026-09-20.json    $R/receipts/BT_P_READING_A0.json  > $R/logs/bt_p_reading_A0_amd4.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_A0ext_2026-09-20.json $R/receipts/BT_P_READING_A0X.json > $R/logs/bt_p_reading_A0X_amd4.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_Preading_V4_2026-09-20.json    $R/receipts/BT_P_READING_V4.json  > $R/logs/bt_p_reading_V4_amd4.log 2>&1
for a in A0 A0ext V4; do
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B bt_p2_reading.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_P2reading_${a}_2026-09-20.json $R/receipts/BT_P2_READING_${a}.json > $R/logs/bt_p2_reading_${a}_amd4.log 2>&1
done
# (Mac) 三个装置测试 + 渲染 + 对账。对账的 <old_dir> 里放 `git show ec00bbb75:.../BT_P2_READING_{A0,A0ext,V4}.json` 取出的三份旧收据。
# /usr/bin/python3 devices/bt_agg_test.py        receipts/BT_AGG_TEST_mac.json
# /usr/bin/python3 devices/bt_p_reading_test.py  <scratch>/pscr  receipts/BT_P_READING_TEST_mac.json
# /usr/bin/python3 devices/bt_p2_reading_test.py <scratch>/p2scr receipts/BT_P2_READING_TEST_mac.json
# /usr/bin/python3 devices/bt_p_render.py  receipts/pod2/receipts/BT_P_READING_A0.json  receipts/A0_P_TABLES_rendered.md
# /usr/bin/python3 devices/bt_p_render.py  receipts/pod2/receipts/BT_P_READING_A0X.json receipts/A0EXT_P_TABLES_rendered.md
# /usr/bin/python3 devices/bt_p_render.py  receipts/pod2/receipts/BT_P_READING_V4.json  receipts/V4_P_TABLES_rendered.md
# for a in A0 A0ext V4; do /usr/bin/python3 devices/bt_p2_render.py receipts/pod2/receipts/BT_P2_READING_$a.json receipts/${a}_P2_TABLES_rendered.md; done
# /usr/bin/python3 devices/bt_p2_amd4_delta.py <old_dir> receipts/pod2/receipts receipts/BT_P2_AMD4_DELTA.json
