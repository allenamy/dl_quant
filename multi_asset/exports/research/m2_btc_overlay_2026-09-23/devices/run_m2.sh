#!/bin/sh
# M2 (BTC-beta overlay) — prereg docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md Stage 2 (8530d2b7f / 1217d786). VERBATIM commands as
# executed on pod2 2026-09-23 (CPU only). NOT meant to be re-run blindly: /workspace hit its disk quota at 06:04Z, so everything after the OLD
# target build lives under /dev/shm/m2_btc_overlay_2026-09-23 (= $R); the certified runner is baseline_tables devices_v3 (unchanged files).
set -e
W=/workspace/m2_btc_overlay_2026-09-23; R=/dev/shm/m2_btc_overlay_2026-09-23; DEV=/workspace/baseline_tables_2026-09-19/devices_v3
P=/workspace/venv/bin/python; S1=/workspace/old_vs_new_2026-09-23
# ---- 1. tests (pod2 synthetic, then real-table T1R after the OLD build) and the OLD build ----
cd $W/devices
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_tests.py $W/receipts/M2_TESTS_synthetic_pod2.json > $W/logs/m2_tests_synthetic.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_build_targets.py PATH,HOME,LC_CTYPE /workspace/object_b_2026-09-19/work/A0_main/TARGETS_A0_main.npz \
  b9f0dc9f2011f9defaac80b116415de3f4d75ffb497cbb9533cd995879036c41 /workspace/object_b_2026-09-19/receipts/TARGETS_A0_main.json \
  5ebac7205afc2cd0b5a0c85bd3daf2e2210e56dad9b0461fd015025cb4518385 A0 scaled A0_main_M2 $W > $W/logs/build_OLD.log 2>&1
cd $R/devices      # same device files copied to $R/devices (sha-identical, receipts record the shas)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_tests.py $R/receipts/M2_TESTS_real_pod2.json real $W/work/targets/BETA_A0_main_M2.npz > $R/logs/m2_tests_real.log 2>&1
# (Mac) /usr/bin/python3 -B devices/m2_tests.py receipts/M2_TESTS_mac.json
# ---- 2. OLD literal route: config (diff = target paths / tags / pod_root only; base run appended unchanged as a reproduction control) ----
env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config.py /workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0_2026-09-19.json \
  $W/work/targets/TARGETS_A0_main_M2.npz 25e1c3d15f7e763aee85ba0f247483b5a2925d9bea99e0de2f7a6d32b3ca585d $W/receipts/TARGETS_A0_main_M2.json \
  a71016f50ae2c635d16ec8e4fd866c92647c8160185ecf013ce6c6bccb8d1581 $R/RUN_CONFIG_m2_OLD_2026-09-23.json $R/receipts/M2_CONFIG_DIFF_OLD.json $R --with-base-control
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2_OLD_2026-09-23.json "OBJB_A0|scaled|rule|raw|UAFE" \
  "OBJB_A0M2|scaled|rule|raw|UAFE" $W/work/targets/BETA_A0_main_M2.npz $W/work/targets/M2DIAG_A0_main_M2.npz $R/work/EXEC_PATH_OLD.npz $R/receipts/M2_EXEC_PATH_OLD.json
cd $DEV && setsid bash -c "echo \$\$ > $R/logs/full_m2old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B bt_launch.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2_OLD_2026-09-23.json --resume m2old > $R/logs/bt_launch_full_m2old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_m2old.log"   # PGID 2213655
# ---- 3. OLD overlay-hook route (named deviation): hedge tables, configs, zero-hedge control (2 seeds, full window), overlay runs ----
cd $R/devices
env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_hook.py table $W/work/targets/M2DIAG_A0_main_M2.npz $R/work/M2H_TABLE_A0_main.npz
env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_hook.py table $W/work/targets/M2DIAG_A0_main_M2.npz $R/work/M2H0_TABLE_A0_main_zero.npz --zero
env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config_hook.py /workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0_2026-09-19.json overlay $R/devices/m2_hook.py $R/work/M2H_TABLE_A0_main.npz $R/RUN_CONFIG_m2h_OLD_2026-09-23.json $R/receipts/M2H_CONFIG_DIFF_OLD.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config_hook.py /workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0_2026-09-19.json control $R/devices/m2_hook.py $R/work/M2H0_TABLE_A0_main_zero.npz $R/RUN_CONFIG_m2h0_OLD_2026-09-23.json $R/receipts/M2H0_CONFIG_DIFF_OLD.json $R
setsid bash -c "echo \$\$ > $R/logs/m2h0_ctrl.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2h0_OLD_2026-09-23.json --smoke 2022-06-30T00:00:00Z 9139 0,31 \"OBJB_A0M2H0|scaled|rule|raw|UAFE\" m2h0_ctrl > $R/logs/m2h0_ctrl.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m2h0_ctrl.log"   # PGID 2214174
$P -B m2_path_compare.py $R/runs_smoke/m2h0_ctrl/OBJB_A0M2H0_scaled_rule_raw_UAFE /workspace/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE 0,31 $R/receipts/M2H0_CONTROL_vs_certified_A0.json
setsid bash -c "echo \$\$ > $R/logs/full_m2h.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2h_OLD_2026-09-23.json --resume m2h > $R/logs/bt_launch_full_m2h.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_m2h.log"   # PGID 2215176
# ---- 4. NEW (Stage 1's certified-format targets; round trip in $S1/receipts/IDENTITY_DISCLOSURE.json) ----
for s in s42 s2027; do   # N / J = the Stage-1 npz / receipt shas (s42 5c18bab2… / 6147cff7…, s2027 897387aa… / dcfeab6d…)
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_build_targets.py PATH,HOME,LC_CTYPE /dev/shm/ovn_2026-09-23/targets/TARGETS_NEW_$s.npz $N /dev/shm/ovn_2026-09-23/targets/TARGETS_NEW_$s.json $J NEW_$s scaled NEW_${s}_M2 $R > $R/logs/build_NEW_$s.log 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config.py $S1/RUN_CONFIG_OVN_NEW_${s}_2026-09-23.json $R/work/targets/TARGETS_NEW_${s}_M2.npz $TN $R/receipts/TARGETS_NEW_${s}_M2.json $TJ $R/RUN_CONFIG_m2_NEW_${s}_2026-09-23.json $R/receipts/M2_CONFIG_DIFF_NEW_${s}.json $R
  env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_hook.py table $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/work/M2H_TABLE_NEW_${s}.npz
  env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_hook.py table $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/work/M2H0_TABLE_NEW_${s}_zero.npz --zero
  env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config_hook.py $S1/RUN_CONFIG_OVN_NEW_${s}_2026-09-23.json overlay $R/devices/m2_hook.py $R/work/M2H_TABLE_NEW_${s}.npz $R/RUN_CONFIG_m2h_NEW_${s}_2026-09-23.json $R/receipts/M2H_CONFIG_DIFF_NEW_${s}.json $R
  env -i PATH=/usr/bin:/bin HOME=/root $P -B m2_make_config_hook.py $S1/RUN_CONFIG_OVN_NEW_${s}_2026-09-23.json control $R/devices/m2_hook.py $R/work/M2H0_TABLE_NEW_${s}_zero.npz $R/RUN_CONFIG_m2h0_NEW_${s}_2026-09-23.json $R/receipts/M2H0_CONFIG_DIFF_NEW_${s}.json $R
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2_NEW_${s}_2026-09-23.json "OVN_NEW_${s}|scaled|rule|raw|UAFE" "OVN_NEW_${s}M2|scaled|rule|raw|UAFE" $R/work/targets/BETA_NEW_${s}_M2.npz $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/work/EXEC_PATH_NEW_${s}.npz $R/receipts/M2_EXEC_PATH_NEW_${s}.json > $R/logs/exec_path_NEW_${s}.log 2>&1
  setsid bash -c "echo \$\$ > $R/logs/full_m2h_new_${s}.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m2h_NEW_${s}_2026-09-23.json --resume m2h_new_${s} > $R/logs/bt_launch_full_m2h_new_${s}.log 2>&1; echo \"EXIT \$?\" >> $R/logs/bt_launch_full_m2h_new_${s}.log"   # PGIDs 2217294 / 2217295
done
setsid bash -c "echo \$\$ > $R/logs/chain_new_literal.pgid; $R/devices/m2_chain_new_literal.sh"   # PGID 2217487: DIED AT ONCE, launched nothing — /dev/shm is mounted noexec
#   (found 07:51Z; the first v2 start the same way died the same way). Executed instead: v2 = both seeds in parallel, run through bash:
setsid bash -c "echo \$\$ > $R/logs/chain_new_literal_v2.pgid; bash $R/devices/m2_chain_new_literal_v2.sh" > $R/logs/chain_new_literal_v2.out 2>&1   # PGID 2225329
# ---- 5. readouts (after the runs) — appended below as executed ----
cd $R/devices; C=/workspace/baseline_tables_2026-09-19/runs; B=/dev/shm/ovn_2026-09-23/runs; DO=$W/work/targets/M2DIAG_A0_main_M2.npz
# 5a. readout self-test (certified OLD base vs itself, all Δ = 0) and the Stage-1 OLD cross-check (32 seeds, bitwise)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_readout.py SELFTEST_base_vs_base $C/OBJB_A0_scaled_rule_raw_UAFE $C/OBJB_A0_scaled_rule_raw_UAFE \
  fee_x1.25=$C/OBJB_A0_scaled_rule_raw_UAFE_fee_x1.25:$C/OBJB_A0_scaled_rule_raw_UAFE_fee_x1.25,slip_x1.5=$C/OBJB_A0_scaled_rule_raw_UAFE_slip_x1.5:$C/OBJB_A0_scaled_rule_raw_UAFE_slip_x1.5,fill_x0.9=$C/OBJB_A0_scaled_rule_raw_UAFE_fill_x0.9:$C/OBJB_A0_scaled_rule_raw_UAFE_fill_x0.9 \
  $DO $R/receipts/M2_READOUT_SELFTEST.json > $R/logs/readout_selftest.log 2>&1
$P -B m2_path_compare.py $B/OBJB_A0_scaled_rule_raw_UAFE $C/OBJB_A0_scaled_rule_raw_UAFE $(seq -s, 0 31) $R/receipts/STAGE1_OLD_vs_certified_A0.json
# 5b. interim readouts on the main runs only (cost pairs empty ⇒ H2.4 UNDECIDED by rule): OLD L / H at ~06:57Z, NEW H at ~07:40Z
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_readout.py OLD_L_interim_main_only $C/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0M2_scaled_rule_raw_UAFE "" $DO $R/receipts/M2_READOUT_OLD_L_interim.json
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_readout.py OLD_H_interim_main_only $C/OBJB_A0_scaled_rule_raw_UAFE $R/runs/OBJB_A0M2H_scaled_rule_raw_UAFE "" $DO $R/receipts/M2_READOUT_OLD_H_interim.json
for s in s42 s2027; do env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_readout.py NEW_${s}_H_interim_main_only $B/OVN_NEW_${s}_scaled_rule_raw_UAFE $R/runs/OVN_NEW_${s}M2H_scaled_rule_raw_UAFE "" $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/receipts/M2_READOUT_NEW_${s}_H_interim.json; done
# 5c. final NEW s2027 H readout (by hand, 08:33Z: its Stage-1 cost-cell bases were complete), then the readout chain for everything else
s=s2027; CP=""; for c in fee_x1.25 slip_x1.5 fill_x0.9; do CP="$CP${CP:+,}$c=$B/OVN_NEW_${s}_scaled_rule_raw_UAFE_$c:$R/runs/OVN_NEW_${s}M2H_scaled_rule_raw_UAFE_$c"; done
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m2_readout.py NEW_${s}_H_hook $B/OVN_NEW_${s}_scaled_rule_raw_UAFE $R/runs/OVN_NEW_${s}M2H_scaled_rule_raw_UAFE $CP $R/work/targets/M2DIAG_NEW_${s}_M2.npz $R/receipts/M2_READOUT_NEW_${s}_H.json > $R/logs/readout_NEW_${s}_H.log 2>&1
setsid bash -c "echo \$\$ > $R/logs/chain_readouts.pgid; bash $R/devices/m2_chain_readouts.sh" > $R/logs/chain_readouts.out 2>&1   # PGID 2232722: OLD_H, OLD_L + base control, NEW_s42_H, NEW L x2 + NEW zero-hedge controls
# (Mac) /usr/bin/python3 devices/m2_render.py receipts/pod2/M2_READOUT_{OLD_L,OLD_H,NEW_s42_H,NEW_s2027_H,NEW_s42_L,NEW_s2027_L}.json  → tables in docs/RESULT_m2_btc_overlay_2026-09-23.md
