#!/bin/sh
# M3 (BTC-beta overlay, beta on the EXECUTED target) — prereg docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md (24c3f803f, sha bc550bb5).
# VERBATIM commands as executed on pod2 2026-09-23 (CPU only). Run root R = /dev/shm/m3_2026-09-23 (/workspace is at its quota); /dev/shm is noexec
# ⇒ every device runs through the python / bash binaries. Devices were copied from the Mac (multi_asset/exports/research/m3_2026-09-23/devices/)
# into $R/devices with scp (sha-identical; every receipt records the shas). Only PGIDs recorded here were ever signalled.
set -e
R=/dev/shm/m3_2026-09-23; P=/workspace/venv/bin/python; DEV=/workspace/baseline_tables_2026-09-19/devices_v3
CO=/workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0ext_2026-09-20.json          # OLD base config (certified; Stage 1's OLD extension run OBJB_A0X)
CN=/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json             # NEW_s42 base config (Stage 1)
BO=/workspace/baseline_tables_2026-09-19/runs/OBJB_A0X_scaled_rule_raw_UAFE               # OLD base paths (certified, read only)
BN=/dev/shm/ovn_2026-09-23/runs/OVN_NEW_s42X_scaled_rule_raw_UAFE                         # NEW_s42 base paths (Stage 1, read only)
# (Mac) scp devices/*.py + docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md → $R/devices ; mv the prereg to $R/pins
# ---- 1. the β matrix (both bases share it: same window, same symbols, same price table) ----
cd $R/devices && setsid bash -c "echo \$\$ > $R/logs/build_beta.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_build_beta.py PATH,HOME,LC_CTYPE $CO $CN /workspace/m2_btc_overlay_2026-09-23/work/targets/BETA_A0_main_M2.npz $R > $R/logs/build_beta.log 2>&1; echo \"EXIT \$?\" >> $R/logs/build_beta.log"
#   try 1 (logs/build_beta_try1_crosscheck_expectation.log, receipts/M3_BUILD_BETA_try1.json): EXIT 3 — my cross-check expected M2's β axis to have
#   exactly 9,139 anchors; it has 10,039 (900 rows before 2022-06-30). β bitwise equal on the 9,139 shared anchors already in try 1. Fixed the
#   expectation (shared == 9,139 AND every unshared M2 anchor precedes 2022-06-30), re-ran the same command: PASS, beta sha 6dcf9782.
# ---- 2. configs (diff vs the base config = labels / pod_root / m3_hook only; main scaled run only) ----
BETA=$R/work/BETA_M3_full.npz; PR=$R/pins/PREREG_m3_beta_overlay_executed_book_2026-09-23.md
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CO overlay $R/devices/m3_hook.py $BETA $PR $R/RUN_CONFIG_m3h_OLD.json $R/receipts/M3H_CONFIG_DIFF_OLD.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CO control $R/devices/m3_hook.py $BETA $PR $R/RUN_CONFIG_m3h0_OLD.json $R/receipts/M3H0_CONFIG_DIFF_OLD.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CN overlay $R/devices/m3_hook.py $BETA $PR $R/RUN_CONFIG_m3h_NEW_s42.json $R/receipts/M3H_CONFIG_DIFF_NEW_s42.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CN control $R/devices/m3_hook.py $BETA $PR $R/RUN_CONFIG_m3h0_NEW_s42.json $R/receipts/M3H0_CONFIG_DIFF_NEW_s42.json $R
#   try 1 of the configs (moved to $R/try1_inert_configs/, never run): the OLD base run has arm 'OBJB_A0' but tag 'OBJB_A0X|…', and M2's
#   derivation keyed on the arm, so the OLD tag was NOT renamed and the hook (keyed on the tag prefix) would have been INERT — the diff receipt
#   still said PASS because it only required differing keys ⊆ {tag, arm, role}. Fixed (m3_make_config_hook.py keys on the tag prefix and now
#   requires tag, arm AND role to change and the tag prefix to be a hooked arm; m3_hook.py refuses a config with any unhooked run); the four
#   commands above were re-run as written: PASS, configs 68dc66fa / 7638d536 / 402accbd / 60630f8a.
# ---- 3. debug smoke of the control arm (no M3 number: control never touches the target) ----
setsid bash -c "echo \$\$ > $R/logs/dbg_ctrl_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3h0_OLD.json --smoke 2026-03-01T00:00:00Z 12 0 'OBJB_A0XM3H0|scaled|rule|raw|UAFE' dbg_ctrl_old > $R/logs/dbg_ctrl_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/dbg_ctrl_old.log"
# ==== commit bc9015f80 (devices + frozen rules, before any M3 number) ====
# ---- 4. zero-hedge control, full window, seed 0, both bases (test: bitwise = base; its sidecar feeds feasibility row c) ----
setsid bash -c "echo \$\$ > $R/logs/ctrl0_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3h0_OLD.json --smoke 2022-06-30T00:00:00Z 9252 0 'OBJB_A0XM3H0|scaled|rule|raw|UAFE' ctrl0_old > $R/logs/ctrl0_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_old.log"
setsid bash -c "echo \$\$ > $R/logs/ctrl0_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3h0_NEW_s42.json --smoke 2022-06-30T00:00:00Z 9252 0 'OVN_NEW_s42XM3H0|scaled|rule|raw|UAFE' ctrl0_new > $R/logs/ctrl0_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_new.log"
# ---- 5. flat-book delivery diagnostic (R3 / feasibility row b), 4 workers per base ----
setsid bash -c "echo \$\$ > $R/logs/ep_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3h_OLD.json $R/RUN_CONFIG_m3h0_OLD.json 4 $R/work/EXEC_PATH_M3_OLD.npz $R/receipts/M3_EXEC_PATH_OLD.json > $R/logs/ep_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_old.log"
setsid bash -c "echo \$\$ > $R/logs/ep_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3h_NEW_s42.json $R/RUN_CONFIG_m3h0_NEW_s42.json 4 $R/work/EXEC_PATH_M3_NEW_s42.npz $R/receipts/M3_EXEC_PATH_NEW_s42.json > $R/logs/ep_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_new.log"
# ---- 6. test: zero-hedge control seed 0 vs the base seed 0, every array key bitwise (red control: vs base seed 1) ----
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_old/OBJB_A0XM3H0_scaled_rule_raw_UAFE $BO 0 $R/receipts/M3H0_CONTROL_seed0_OLD_vs_base.json > $R/logs/cmp_ctrl0_old.log 2>&1
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_new/OVN_NEW_s42XM3H0_scaled_rule_raw_UAFE $BN 0 $R/receipts/M3H0_CONTROL_seed0_NEW_s42_vs_base.json > $R/logs/cmp_ctrl0_new.log 2>&1
# ---- 7. red/green tests (one per base: the in-simulator tests use that base's book) ----
EP_O=$R/work/EXEC_PATH_M3_OLD.npz; EP_N=$R/work/EXEC_PATH_M3_NEW_s42.npz
setsid bash -c "echo \$\$ > $R/logs/tests_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3_TESTS_OLD.json $R/RUN_CONFIG_m3h_OLD.json $R/RUN_CONFIG_m3h0_OLD.json $EP_O > $R/logs/tests_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/tests_old.log"
setsid bash -c "echo \$\$ > $R/logs/tests_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3_TESTS_NEW_s42.json $R/RUN_CONFIG_m3h_NEW_s42.json $R/RUN_CONFIG_m3h0_NEW_s42.json $EP_N > $R/logs/tests_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/tests_new.log"
# ---- 8. feasibility rows (a)(b)(c), before any M3 NAV ----
SC0_O=$R/m3_sidecar/smoke_ctrl0_old/M3SC_OBJB_A0XM3H0_scaled_rule_raw_UAFE_seed_00.npz; SC0_N=$R/m3_sidecar/smoke_ctrl0_new/M3SC_OVN_NEW_s42XM3H0_scaled_rule_raw_UAFE_seed_00.npz
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_feasibility.py PATH,HOME,LC_CTYPE $R/receipts/M3_FEASIBILITY.json OLD=$BO,$EP_O,$SC0_O NEW_s42=$BN,$EP_N,$SC0_N > $R/logs/feasibility.log 2>&1
#   try 1 of the tests (receipts/M3_TESTS_{OLD,NEW_s42}_try1.json, logs/tests_*_try1_weak_control.log): OLD 46/46 GREEN, NEW RED 1/46 —
#   T1H's red-capability control added +0.25 UNIFORMLY to row A, which a dollar-neutral executed book cannot see (Σw(β+c) = β_exec + c·net,
#   net ≈ 1e-17): red on NEW (bitwise unchanged), and on OLD "green" only through a 1e-16 float difference, i.e. vacuous on both. Fixed the
#   control (per-name N(0, 0.25) on row A, must move β_exec by > 1e-4); re-ran both commands above unchanged.
#   re-run: M3_TESTS VERDICT=ALL GREEN tests=46 red=0, EXIT 0, both bases.
