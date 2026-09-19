#!/bin/sh
# stream R — verbatim commands (pod2, CPU only; cwd = /workspace/replay_r_2026-09-19/devices; nothing outside /workspace/replay_r_2026-09-19 is written)
# 0. copies (from the Mac research repo, sha-verified by r_launch.py): replay_exec_2026-09-19/{exec_sim.py,simlib.py,CALIBRATION_FROZEN_2026-09-19.json,INPUT_MANIFEST.json}
#    -> devices/replay_exec_copy/ ; the stream-E mirror's exec_tree_409ea16/ + state/exchange_info_cache.json -> work/exec_mirror/
set -e
cd /workspace/replay_r_2026-09-19/devices
# 1. gate R0: S2 published numbers from the S2 vec targets with S2's own accounting (exit 3 = RED)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r0_repro.py PATH,HOME,LC_CTYPE > ../logs/r0_repro.log 2>&1
# 2. price chain (RAW-restored, gated vs meta RAW y4 <= 1e-6)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_prices.py PATH,HOME,LC_CTYPE > ../logs/r_prices.log 2>&1
# 3. the 12 frozen runs (RUN_CONFIG_replay_r_2026-09-19.json)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_launch.py PATH,HOME,LC_CTYPE /workspace/replay_r_2026-09-19/RUN_CONFIG_replay_r_2026-09-19.json > ../logs/r_launch.log 2>&1
# 4. tables
env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B r_tables.py PATH,HOME,LC_CTYPE /workspace/replay_r_2026-09-19/RUN_CONFIG_replay_r_2026-09-19.json > ../logs/r_tables.log 2>&1
# smoke (short windows, code check only; not results):
#   ... r_launch.py PATH,HOME,LC_CTYPE <config> --smoke 2025-03-01T00:00:00Z 60 "S2_v4_s42|CMB|rule,S2_A0pred_s42|LIT|rule"
