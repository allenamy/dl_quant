#!/bin/sh
# M3c — docs/AMENDMENT_3_m3_beta_overlay_2026-09-24.md §2-1 (80c6c3e4b) / AMENDMENT_2 §3-2 (4530892bc): M3b hook + combined leverage 2.5 on the
# NC s42 targets (s2027 side report). VERBATIM commands as executed on pod2 2026-09-24 (CPU only). Run root R = /root/m3c_2026-09-24 (container
# overlay): /dev/shm is closed to M3c (lead), /workspace is at its quota. NC targets, news2's configs and base paths are only READ.
# Devices copied from the Mac (multi_asset/exports/research/m3c_2026-09-24/devices) with scp; M3b's hook (873769b9) from the M3b devices dir.
set -e
R=/root/m3c_2026-09-24; P=/workspace/venv/bin/python; N2=/dev/shm/news2_2026-09-23
C42=$N2/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json; C27=$N2/configs/RUN_CONFIG_NEWS2_s2027X_2026-09-23.json
B42=$N2/runs/NEWS2_s42X_scaled_rule_raw_UAFE; B27=$N2/runs/NEWS2_s2027X_scaled_rule_raw_UAFE
# ---- 1. β matrix: rebuilt (M3's /dev/shm copy is gone) with M3's m3_build_beta.py (8b531801, unchanged) — must reproduce sha 6dcf9782 ----
cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_build_beta.py PATH,HOME,LC_CTYPE $C42 $C27 /workspace/m2_btc_overlay_2026-09-23/work/targets/BETA_A0_main_M2.npz $R > $R/logs/build_beta.log 2>&1
#   → M3_BUILD_BETA VERDICT=PASS beta_sha256=6dcf97824f4b… (= M3's), EXIT 0
# ---- 2. configs (s42 first; s2027 after the s42 readout) ----
BETA=$R/work/BETA_M3_full.npz; PR=$R/pins/PREREG_m3_beta_overlay_executed_book_2026-09-23.md; A1=$R/pins/AMENDMENT_1_m3_beta_overlay_2026-09-23.md
A2=$R/pins/AMENDMENT_2_m3_beta_overlay_2026-09-23.md; A3=$R/pins/AMENDMENT_3_m3_beta_overlay_2026-09-24.md
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $C42 overlay $R/devices/m3_hook.py $BETA $PR $A1 $A2 $A3 $R/RUN_CONFIG_m3ch_s42.json $R/receipts/M3CH_CONFIG_DIFF_s42.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $C42 control $R/devices/m3_hook.py $BETA $PR $A1 $A2 $A3 $R/RUN_CONFIG_m3ch0_s42.json $R/receipts/M3CH0_CONFIG_DIFF_s42.json $R
#   → both PASS (588603d5 / 2f488834), max_combined_leverage 2.5, hook 95ff9632
# ---- 3. flat-book R3 diagnostic (s42), 2 workers ----
setsid bash -c "echo \$\$ > $R/logs/ep_s42.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch_s42.json $R/RUN_CONFIG_m3ch0_s42.json 2 $R/work/EXEC_PATH_M3C_s42.npz $R/receipts/M3C_EXEC_PATH_s42.json > $R/logs/ep_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_s42.log"
# ---- 4. zero-hedge control seed 0, full window (s42) → bitwise vs news2's base seed 0 ----
setsid bash -c "echo \$\$ > $R/logs/ctrl0_s42.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch0_s42.json --smoke 2022-06-30T00:00:00Z 9252 0 'NEWS2_s42XM3CH0|scaled|rule|raw|UAFE' ctrl0_s42 > $R/logs/ctrl0_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_s42.log"
#   → ep_s42: M3_EXEC_PATH VERDICT=DONE, EXIT 0; ctrl0_s42: BT_LAUNCH VERDICT=PASS, EXIT 0; no entry of mine under /dev/shm afterwards
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_s42/NEWS2_s42XM3CH0_scaled_rule_raw_UAFE $B42 0 $R/receipts/M3CH0_CONTROL_seed0_s42_vs_news2_base.json > $R/logs/cmp_ctrl0_s42.log 2>&1
# ---- 5. tests (s42): M3c red/green + M3's 46 as regression (one after the other) ----
EP=$R/work/EXEC_PATH_M3C_s42.npz
setsid bash -c "echo \$\$ > $R/logs/m3ctests_s42.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3c_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3C_TESTS_s42.json $R/RUN_CONFIG_m3ch_s42.json $R/RUN_CONFIG_m3ch0_s42.json $EP $R/pins/m3_hook_M3b.py > $R/logs/m3ctests_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3ctests_s42.log; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_tests.py PATH,HOME,LC_CTYPE $R/receipts/M3_TESTS_on_M3C_s42.json $R/RUN_CONFIG_m3ch_s42.json $R/RUN_CONFIG_m3ch0_s42.json $EP > $R/logs/m3tests_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/m3tests_s42.log"
#   → cmp: M2_PATH_COMPARE BITWISE_EQUAL control_differs True; M3C_TESTS VERDICT=ALL GREEN tests=16 red=0 unexercised=1 (C3a: the budget does not
#     bind on any MAIN flat-book anchor) EXIT 0; M3_TESTS VERDICT=ALL GREEN tests=46 red=0 EXIT 0
# ==== commit (tests, R3, control seed 0 — before any M3c NAV) ====
# ==== commit 0e6d6b7c4 ====
# ---- 6. s42 overlay, 32 paths (one launcher, max_parallel 4) ----
setsid bash -c "echo \$\$ > $R/logs/full_m3ch_s42.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch_s42.json --resume m3ch_s42 > $R/logs/full_m3ch_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/full_m3ch_s42.log"
#   → BT_LAUNCH VERDICT=PASS label=full_m3ch_s42 runs=1 seeds=32, EXIT 0
$P -B m3c_compact.py $R/runs/NEWS2_s42XM3CH_scaled_rule_raw_UAFE > $R/logs/compact_m3ch_s42.log 2>&1
# ---- 7. s42 zero-hedge control, 32 paths; bitwise vs news2's base on all 32 seeds; then compact ----
setsid bash -c "echo \$\$ > $R/logs/full_m3ch0_s42.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch0_s42.json --resume m3ch0_s42 > $R/logs/full_m3ch0_s42.log 2>&1; echo \"EXIT \$?\" >> $R/logs/full_m3ch0_s42.log"
S32=$(seq -s, 0 31)
$P -B m2_path_compare.py $R/runs/NEWS2_s42XM3CH0_scaled_rule_raw_UAFE $B42 $S32 $R/receipts/M3CH0_CONTROL_32_s42_vs_news2_base.json > $R/logs/cmp_ctrl32_s42.log 2>&1
$P -B m3c_compact.py $R/runs/NEWS2_s42XM3CH0_scaled_rule_raw_UAFE > $R/logs/compact_m3ch0_s42.log 2>&1
#   → full_m3ch0_s42 BT_LAUNCH VERDICT=PASS 32 seeds; cmp BITWISE_EQUAL (32 seeds) control_differs True; compact DONE
# ---- 8. s42 readout (base = news2's NEWS2_s42X paths, read only; overlay / control = the COMPACT dirs) ----
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_readout.py PATH,HOME,LC_CTYPE NC_s42 $B42 $R/runs/NEWS2_s42XM3CH_scaled_rule_raw_UAFE/COMPACT $R/runs/NEWS2_s42XM3CH0_scaled_rule_raw_UAFE/COMPACT $R/m3_sidecar/full_m3ch_s42 $R/m3_sidecar/full_m3ch0_s42 $R/work/EXEC_PATH_M3C_s42.npz $R/receipts/M3CH0_CONTROL_32_s42_vs_news2_base.json $R/receipts/M3C_READOUT_s42.json > $R/logs/readout_s42.log 2>&1
#   → M3_READOUT NC_s42 VERDICT=PASS failing=[] undecided=[], EXIT 0
# ---- 9. make room for s2027: the s42 compact paths, sidecars and the seed-0 smoke were pulled to the Mac (199 files, sha-identical), then removed ----
cd $R && rm -rf runs/NEWS2_s42XM3CH_scaled_rule_raw_UAFE runs/NEWS2_s42XM3CH0_scaled_rule_raw_UAFE m3_sidecar/full_m3ch_s42 m3_sidecar/full_m3ch0_s42 m3_sidecar/smoke_ctrl0_s42 runs_smoke/ctrl0_s42
# ---- 10. s2027 side report (not part of the verdict): configs, flat book, control seed 0, overlay 32, control 32, readout — as for s42 ----
cd $R/devices
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $C27 overlay $R/devices/m3_hook.py $BETA $PR $A1 $A2 $A3 $R/RUN_CONFIG_m3ch_s2027.json $R/receipts/M3CH_CONFIG_DIFF_s2027.json $R
env -i PATH=/usr/bin:/bin HOME=/root $P -B m3_make_config_hook.py $C27 control $R/devices/m3_hook.py $BETA $PR $A1 $A2 $A3 $R/RUN_CONFIG_m3ch0_s2027.json $R/receipts/M3CH0_CONFIG_DIFF_s2027.json $R
setsid bash -c "echo \$\$ > $R/logs/ep_s2027.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_exec_path.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch_s2027.json $R/RUN_CONFIG_m3ch0_s2027.json 2 $R/work/EXEC_PATH_M3C_s2027.npz $R/receipts/M3C_EXEC_PATH_s2027.json > $R/logs/ep_s2027.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ep_s2027.log"
setsid bash -c "echo \$\$ > $R/logs/ctrl0_s2027.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch0_s2027.json --smoke 2022-06-30T00:00:00Z 9252 0 'NEWS2_s2027XM3CH0|scaled|rule|raw|UAFE' ctrl0_s2027 > $R/logs/ctrl0_s2027.log 2>&1; echo \"EXIT \$?\" >> $R/logs/ctrl0_s2027.log"
#   → configs PASS (2414388f / 6643a55f); ep_s2027 DONE EXIT 0; ctrl0_s2027 PASS EXIT 0
$P -B m2_path_compare.py $R/runs_smoke/ctrl0_s2027/NEWS2_s2027XM3CH0_scaled_rule_raw_UAFE $B27 0 $R/receipts/M3CH0_CONTROL_seed0_s2027_vs_news2_base.json > $R/logs/cmp_ctrl0_s2027.log 2>&1
setsid bash -c "echo \$\$ > $R/logs/full_m3ch_s2027.pgid; env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 $P -B m3_hook.py PATH,HOME,LC_CTYPE $R/RUN_CONFIG_m3ch_s2027.json --resume m3ch_s2027 > $R/logs/full_m3ch_s2027.log 2>&1; echo \"EXIT \$?\" >> $R/logs/full_m3ch_s2027.log"
