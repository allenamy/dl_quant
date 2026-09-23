#!/bin/bash
# NEW_S2 global gate on pod2 (PREREG §6.2). Records its own PGID first, so it can be stopped with
# `kill -TERM -<pgid>` and never with a name scan (E: pattern_kill_on_shared_host).
# usage: bash run_gate_pod2.sh [n_anchors]
set -e
W2=/dev/shm/news2_2026-09-23
export NEWS2_WIDE=$W2/inputs/producer
export NEWS2_BASE_SHADOW=$W2/inputs/shadow_loop_v3.ed11d731.py
export NEWS2_RESEARCH_TREE=$W2/inputs
export NEWS2_PAR=$W2/inputs
export NEWS2_CRYPTO=$W2/inputs/P1_members_2025H2on.npz
export NEWS2_CFG=$W2/inputs/bundle_config.json
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
P314=/root/news_2026-09-23_env/venv314/bin/python
mkdir -p "$W2/logs" "$W2/work" "$W2/receipts"
ps -o pgid= -p $$ | tr -dc '0-9' > "$W2/logs/gate.pgid"
echo "pgid=$(cat "$W2/logs/gate.pgid") started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
nice -n 10 $P314 -u "$W2/devices/news2_global_gate.py" "$W2/work/gate" "$W2/receipts/GLOBAL_GATE.json" "${1:-3}"
rc=$?
echo "GATE_RC=$rc finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
exit $rc
