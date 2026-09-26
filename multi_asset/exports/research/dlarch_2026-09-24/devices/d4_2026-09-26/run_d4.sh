#!/bin/sh
# run_d4.sh -- D4 pre-gates, one process group. Terminal marker (line start): D4_PREGATES DONE|STOPPED. Traceback = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/d4_2026-09-26; LOG=$A/d4.log
mkdir "$W/CHAIN/.claim_D4" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=d4_pregates started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_D4/owner" > "$A/d4.pgid"
cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /workspace/venv/bin/python -B dlarch_d4_pregates.py \
    PATH,HOME,LC_CTYPE "$W/receipts/D4_PREGATES_2026-09-26.json" >> "$LOG" 2>&1
echo "rc=$?" >> "$LOG"; rm -rf "$W/CHAIN/.claim_D4"
