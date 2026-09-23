#!/bin/sh
# M3b — docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md (912788743, sha be8e5c18) to prereg docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md
# (24c3f803f). VERBATIM commands as executed on pod2 2026-09-23 (CPU only). Run root R = /dev/shm/m3b_2026-09-23. Devices: copies of M3's
# (multi_asset/exports/research/m3_2026-09-23/devices) — sha-identical except m3_hook.py (the M3b change), m3_make_config_hook.py (labels /
# amendment pin), m3_readout.py (cause 7 counted as applied in the in-path report), m3_render.py ('-' for no feasibility receipt); new: m3b_tests.py.
# Scheduling (lead): light work (flat-book R3, tests, seed-0 control) first with few workers; the 32-path runs only after NEW_S's CPU-heavy
# phase (/dev/shm/news_2026-09-23) has ended, <= 6 workers (the launchers run one after the other, max_parallel 4 each).
set -e
R=/dev/shm/m3b_2026-09-23; R3=/dev/shm/m3_2026-09-23; P=/workspace/venv/bin/python
CO=/workspace/baseline_tables_2026-09-19/RUN_CONFIG_main_A0ext_2026-09-20.json; CN=/workspace/old_vs_new_2026-09-23/RUN_CONFIG_OVN_NEW_s42X_2026-09-23.json
BO=/workspace/baseline_tables_2026-09-19/runs/OBJB_A0X_scaled_rule_raw_UAFE; BN=/dev/shm/ovn_2026-09-23/runs/OVN_NEW_s42X_scaled_rule_raw_UAFE
# (Mac) scp devices/*.py + docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md → $R/devices ; mv the amendment to $R/pins ; cp M3's prereg pin
# ---- 1. β matrix: M3's, copied (sha 6dcf9782 checked by the config maker's pin) ----
cp $R3/work/BETA_M3_full.npz $R/work/BETA_M3_full.npz; cp $R3/pins/PREREG_m3_beta_overlay_executed_book_2026-09-23.md $R/pins/
# ---- 2. configs ----
BETA=$R/work/BETA_M3_full.npz; PR=$R/pins/PREREG_m3_beta_overlay_executed_book_2026-09-23.md; AM=$R/pins/AMENDMENT_1_m3_beta_overlay_2026-09-23.md
cd $R/devices
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CO overlay $R/devices/m3_hook.py $BETA $PR $AM $R/RUN_CONFIG_m3bh_OLD.json $R/receipts/M3BH_CONFIG_DIFF_OLD.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CO control $R/devices/m3_hook.py $BETA $PR $AM $R/RUN_CONFIG_m3bh0_OLD.json $R/receipts/M3BH0_CONFIG_DIFF_OLD.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CN overlay $R/devices/m3_hook.py $BETA $PR $AM $R/RUN_CONFIG_m3bh_NEW_s42.json $R/receipts/M3BH_CONFIG_DIFF_NEW_s42.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $CN control $R/devices/m3_hook.py $BETA $PR $AM $R/RUN_CONFIG_m3bh0_NEW_s42.json $R/receipts/M3BH0_CONFIG_DIFF_NEW_s42.json $R
#   configs: PASS — 83d7dcab / 8b3585e5 / cbeaeb75 / e39c91c6 (hook 873769b9, β 6dcf9782)
# ---- 3. light work while NEW_S runs: flat-book R3 (1 worker per base) and the M3b red/green tests (OLD first) ----
setsid bash -c "echo \$\$ > $R/logs/ep_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh_OLD.json $R/RUN_CONFIG_m3bh0_OLD.json 1 $R/work/EXEC_PATH_M3B_OLD.npz $R/receipts/M3B_EXEC_PATH_OLD.json > $R/logs/ep_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_old.log"
setsid bash -c "echo \$\$ > $R/logs/ep_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh_NEW_s42.json $R/RUN_CONFIG_m3bh0_NEW_s42.json 1 $R/work/EXEC_PATH_M3B_NEW_s42.npz $R/receipts/M3B_EXEC_PATH_NEW_s42.json > $R/logs/ep_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_new.log"
setsid bash -c "echo \$\$ > $R/logs/m3btests_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3b_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3B_TESTS_OLD.json $R/RUN_CONFIG_m3bh_OLD.json $R/RUN_CONFIG_m3bh0_OLD.json $R3/work/EXEC_PATH_M3_OLD.npz $R3/devices/m3_hook.py > $R/logs/m3btests_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3btests_old.log"
#   m3btests_old: M3B_TESTS VERDICT=ALL GREEN tests=12 red=0, EXIT 0 ⇒ NEW_s42:
setsid bash -c "echo \$\$ > $R/logs/m3btests_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3b_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3B_TESTS_NEW_s42.json $R/RUN_CONFIG_m3bh_NEW_s42.json $R/RUN_CONFIG_m3bh0_NEW_s42.json $R3/work/EXEC_PATH_M3_NEW_s42.npz $R3/devices/m3_hook.py > $R/logs/m3btests_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3btests_new.log"
#   m3btests_new: ALL GREEN 12/12, EXIT 0; ep_old / ep_new: M3_EXEC_PATH VERDICT=DONE, EXIT 0
# ---- 4. regression: M3's 46 tests (byte-identical m3_tests.py) on the M3b hook; zero-hedge control seed 0, full window (2 at a time) ----
setsid bash -c "echo \$\$ > $R/logs/m3tests_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3_TESTS_on_M3B_OLD.json $R/RUN_CONFIG_m3bh_OLD.json $R/RUN_CONFIG_m3bh0_OLD.json $R/work/EXEC_PATH_M3B_OLD.npz > $R/logs/m3tests_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3tests_old.log"
setsid bash -c "echo \$\$ > $R/logs/ctrl0_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh0_OLD.json --smoke 2022-06-30T00:00:00Z 9252 0 'OBJB_A0XM3BH0|scaled|rule|raw|UAFE' ctrl0_old > $R/logs/ctrl0_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_old.log"
#   m3tests_old: M3_TESTS VERDICT=ALL GREEN tests=46 red=0, EXIT 0; ctrl0_old: BT_LAUNCH VERDICT=PASS, EXIT 0
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_old/OBJB_A0XM3BH0_scaled_rule_raw_UAFE $BO 0 $R/receipts/M3BH0_CONTROL_seed0_OLD_vs_base.json > $R/logs/cmp_ctrl0_old.log 2>&1
setsid bash -c "echo \$\$ > $R/logs/m3tests_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3_TESTS_on_M3B_NEW_s42.json $R/RUN_CONFIG_m3bh_NEW_s42.json $R/RUN_CONFIG_m3bh0_NEW_s42.json $R/work/EXEC_PATH_M3B_NEW_s42.npz > $R/logs/m3tests_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3tests_new.log"
setsid bash -c "echo \$\$ > $R/logs/ctrl0_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh0_NEW_s42.json --smoke 2022-06-30T00:00:00Z 9252 0 'OVN_NEW_s42XM3BH0|scaled|rule|raw|UAFE' ctrl0_new > $R/logs/ctrl0_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_new.log"
#   m3tests_new: ALL GREEN 46/46, EXIT 0; ctrl0_new: BT_LAUNCH VERDICT=PASS, EXIT 0
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_new/OVN_NEW_s42XM3BH0_scaled_rule_raw_UAFE $BN 0 $R/receipts/M3BH0_CONTROL_seed0_NEW_s42_vs_base.json > $R/logs/cmp_ctrl0_new.log 2>&1
# ==== commit (tests + R3 flat book + seed-0 controls; before any M3b NAV) ====
# ==== commit 0f42996e8 (tests + R3 + seed-0 controls, before any M3b NAV) ====
# ---- 5. 32-path overlay runs. Started 12:4xZ after NEW_S's p2b feature workers had all exited (pod2 loadavg 1.23 at 12:39Z; the only
#         other heavy process was NEW_S's news_train_king.py at ~4 cores). My waiter's "0 workers" test never fired because `pgrep -fc`
#         counted its own ssh shell (whose command line contains the pattern) — observed by hand instead. One launcher at a time
#         (max_parallel 4 ⇒ <= 4 workers of mine at any moment) ----
setsid bash -c "echo \$\$ > $R/logs/full_m3bh_old.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh_OLD.json --resume m3bh_old > $R/logs/full_m3bh_old.log 2>&1; echo \"EXIT \$?\" >> $R/logs/full_m3bh_old.log"
#   full_m3bh_old: BT_LAUNCH VERDICT=PASS (32 seeds), EXIT 0 ⇒ NEW_s42:
setsid bash -c "echo \$\$ > $R/logs/full_m3bh_new.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3bh_NEW_s42.json --resume m3bh_new > $R/logs/full_m3bh_new.log 2>&1; echo \"EXIT \$?\" >> $R/logs/full_m3bh_new.log"
# ---- 6. readouts (R4's control arm = M3's 32-seed zero-hedge control, bitwise the base, receipts M3H0_CONTROL_32_*) ----
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_readout.py PATH,HOME,LC_CTYPE OLD $BO $R/runs/OBJB_A0XM3BH_scaled_rule_raw_UAFE $R3/runs/OBJB_A0XM3H0_scaled_rule_raw_UAFE $R/m3_sidecar/full_m3bh_old $R3/m3_sidecar/full_m3h0_old $R/work/EXEC_PATH_M3B_OLD.npz $R3/receipts/M3H0_CONTROL_32_OLD_vs_base.json $R/receipts/M3B_READOUT_OLD.json > $R/logs/readout_old.log 2>&1
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_readout.py PATH,HOME,LC_CTYPE NEW_s42 $BN $R/runs/OVN_NEW_s42XM3BH_scaled_rule_raw_UAFE $R3/runs/OVN_NEW_s42XM3H0_scaled_rule_raw_UAFE $R/m3_sidecar/full_m3bh_new $R3/m3_sidecar/full_m3h0_new $R/work/EXEC_PATH_M3B_NEW_s42.npz $R3/receipts/M3H0_CONTROL_32_NEW_s42_vs_base.json $R/receipts/M3B_READOUT_NEW_s42.json > $R/logs/readout_new.log 2>&1
# (Mac) /usr/bin/python3 devices/m3_render.py - receipts/pod2/M3B_READOUT_OLD.json receipts/pod2/M3B_READOUT_NEW_s42.json > receipts/M3B_TABLES_rendered.md
# ---- PGIDs recorded by the launch wrappers (logs/*.pgid; no signal was ever sent to any): ep_old 2256063 · ep_new 2256064 · m3btests_old
#      2256065 · m3btests_new 2256297 · m3tests_old 2257110 · ctrl0_old 2257111 · m3tests_new 2258012 · ctrl0_new 2258013 · full_m3bh_old 2281227 ·
#      full_m3bh_new 2282725
# ---- 7. after the RESULT commit: rm -rf /dev/shm/m3_2026-09-23 (lead: keep M3's run root until the M3b comparison is done) ----
