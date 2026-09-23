#!/bin/bash
set -e
W2=/dev/shm/news2_2026-09-23
export NEWS2_WIDE=$W2/inputs/producer
export NEWS2_BASE_SHADOW=$W2/inputs/shadow_loop_v3.ed11d731.py
export NEWS2_RESEARCH_TREE=$W2/inputs
export NEWS2_CACHE_AXES=$W2/inputs/cache_x0918r_axes.npz
export NEWS2_CACHE_DATA=/workspace/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz
export NEWS2_MASK=/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz
export NEWS2_HOLES=/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz
export NEWS2_FUND=$W2/inputs/fund_replay.npz
export NEWS2_CRYPTO=$W2/inputs/P1_members_2025H2on.npz
export NEWS2_CFG=$W2/inputs/bundle_config.json
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
ps -o pgid= -p $$ | tr -dc "0-9" > "$W2/logs/d7rows.pgid"
echo "pgid=$(cat "$W2/logs/d7rows.pgid") started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
nice -n 10 /root/news_2026-09-23_env/venv314/bin/python -u "$W2/devices/news2_d7_rows_gate.py" "$W2/work/gate" "$W2/receipts/D7_ROWS_GATE.json" "$1"
rc=$?
echo "D7ROWS_RC=$rc finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit $rc
