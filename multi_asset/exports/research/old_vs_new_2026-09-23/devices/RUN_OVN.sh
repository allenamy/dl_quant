#!/bin/sh
# OVN Stage 1 (docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md 8530d2b7f + docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md 70adc6cac)
# VERBATIM commands as executed on pod2, 2026-09-23 (CPU only). cwd = /workspace/old_vs_new_2026-09-23/devices. Run outputs on /dev/shm/ovn_2026-09-23
# (the /workspace volume is at its quota). ovn_detach.sh LABEL -- CMD runs CMD in its own session, log logs/LABEL.log (+ EXIT line), PGID logs/LABEL.pgid.
# Certified devices were copied from /workspace/baseline_tables_2026-09-19/devices_v3 (bt_launch 393a8dc8, bt_driver_lib ba3bc261, bt_hist_sim31 8ae6e2a4,
# bt_objb_targets 05cc5dc2, bt_tables 892ba66b, bt_run_summary 1aa522e8) and from the repo (bt_p_reading a7cb9c4d, bt_p2_reading fa67ae29, bt_agg 43fe1092,
# bt_p_config_for dead5e4b).
set -e
R=/workspace/old_vs_new_2026-09-23; S=/dev/shm/ovn_2026-09-23
# 1. NEW targets from /tmp to the persistent volume (sha-equal to the local backup before and after)
for s in combo_s42 combo_s2027; do cp -p /tmp/codex_combo_20260923/$s/TARGET_RECEIPT.json /tmp/codex_combo_20260923/$s/literal.npz /tmp/codex_combo_20260923/$s/scaled_diagnostic.npz $R/new_targets/$s/; done
cd $R/new_targets && sha256sum combo_s42/* combo_s2027/* | tee $R/receipts/NEW_TARGETS_COPY_SHA256SUMS.txt
cd $R/devices
# 2. adapter red/green test (try 1 was cut off by an ssh alarm and is kept as logs/ovn_adapter_test_s42_try1_killed_by_ssh_alarm.log)
$R/devices/ovn_detach.sh ovn_adapter_test_s42 -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter_test.py PATH,HOME,LC_CTYPE ADAPTER_SPEC_NEW_s42.json $S/scratch/adapter_test_s42 $R/receipts/OVN_ADAPTER_TEST_s42.json
# 3. adapter (NEW -> certified object-B CSR format, bitwise round trip through bt_objb_targets)
for s in 42 2027; do $R/devices/ovn_detach.sh ovn_adapter_s$s -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_adapter.py PATH,HOME,LC_CTYPE ADAPTER_SPEC_NEW_s$s.json $S/targets/TARGETS_NEW_s$s.npz $S/targets/TARGETS_NEW_s$s.json; done
# 4. frozen configs + asserted leaf diff
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_make_configs.py PATH,HOME,LC_CTYPE $R $S/targets/TARGETS_NEW_s42.json $S/targets/TARGETS_NEW_s2027.json $R/receipts/OVN_CONFIG_DIFF.json
# 5. identity disclosure (try 1 IndexError kept as logs/ovn_identity_try1_indexerror.log)
$R/devices/ovn_detach.sh ovn_identity -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_identity.py PATH,HOME,LC_CTYPE $R/receipts/IDENTITY_DISCLOSURE.json $S/targets/TARGETS_NEW_s42.json $S/targets/TARGETS_NEW_s2027.json $R/receipts/OVN_CONFIG_DIFF.json
# 6. runs (06:19Z); the four main launchers were stopped from outside at 08:25:55-08:26Z (logs/OVN_INCIDENTS.log) and resumed as *_r2 at 08:29Z
for pair in "ovn_old:RUN_CONFIG_OVN_OLD_2026-09-23.json" "ovn_new_s42:RUN_CONFIG_OVN_NEW_s42_2026-09-23.json" "ovn_new_s2027:RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json" "ovn_new_s42x:RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json" "ovn_new_s2027x:RUN_CONFIG_OVN_NEW_s2027X_2026-09-23.json"; do L=${pair%%:*}; C=${pair#*:}; $R/devices/ovn_detach.sh launch_$L -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/$C --resume $L; done
# 7. AMENDMENT 1 arm OLD_HOLD (08:10Z)
$R/devices/ovn_detach.sh ovn_old_hold -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B ovn_old_hold.py PATH,HOME,LC_CTYPE $R/receipts/IDENTITY_DISCLOSURE.json $S/targets/TARGETS_OLD_HOLD.npz $S/targets/TARGETS_OLD_HOLD.json
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_make_config_old_hold.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json $S/targets/TARGETS_OLD_HOLD.json $R/receipts/OVN_CONFIG_DIFF_OLD_HOLD.json
$R/devices/ovn_detach.sh launch_ovn_old_hold -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json --resume ovn_old_hold
# 6b. resume after the external stop (08:29Z)
for pair in "ovn_new_s2027_r2:RUN_CONFIG_OVN_NEW_s2027_2026-09-23.json" "ovn_new_s42_r2:RUN_CONFIG_OVN_NEW_s42_2026-09-23.json" "ovn_old_r2:RUN_CONFIG_OVN_OLD_2026-09-23.json" "ovn_old_hold_r2:RUN_CONFIG_OVN_OLD_HOLD_2026-09-23.json"; do L=${pair%%:*}; C=${pair#*:}; $R/devices/ovn_detach.sh launch_$L -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_launch.py PATH,HOME,LC_CTYPE $R/$C --resume $L; done
# 8. statistics-device dry runs on PUBLISHED certified runs (device test only; not OVN numbers)
$R/devices/ovn_detach.sh stats_dryrun -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ovn_stats.py PATH,HOME,LC_CTYPE /workspace/baseline_tables_2026-09-19/runs /workspace/baseline_tables_2026-09-19/runs $S/scratch/STATS_DRYRUN_A0_V4.json --dryrun-arms OLD=OBJB_A0,NEW_s42=OBJB_V4,NEW_s2027=OBJB_V4
$R/devices/ovn_detach.sh stats_dryrun2 -- env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 /workspace/venv/bin/python -B ovn_stats.py PATH,HOME,LC_CTYPE /workspace/baseline_tables_2026-09-19/runs /workspace/baseline_tables_2026-09-19/runs $S/scratch/STATS_DRYRUN2_A0_V4.json --dryrun-arms OLD=OBJB_A0,OLD_HOLD=OBJB_V4,NEW_s42=OBJB_V4,NEW_s2027=OBJB_A0
# 9. post chain: R-P / R-P2 configs + readings for the four arms, prereg statistics + verdict, describe-only extension (09:21Z)
$R/devices/ovn_detach.sh ovn_post -- sh $R/devices/ovn_post.sh
# (Mac) /usr/bin/python3 devices/ovn_render.py receipts/pod2/OVN_STATS.json receipts/pod2/OVN_EXT.json receipts/pod2 receipts/OVN_TABLES_rendered.md
