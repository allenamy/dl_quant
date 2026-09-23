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
