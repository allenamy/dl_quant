#!/bin/sh
# run_d2.sh -- D2 pre-gates, one process group. Terminal marker (line start): D2_PREGATES DONE|STOPPED. Traceback = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/d2_2026-09-26; LOG=$A/d2.log
mkdir "$W/CHAIN/.claim_D2" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=d2_pregates started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_D2/owner" > "$A/d2.pgid"
cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 /workspace/venv/bin/python -B dlarch_d2_pregates.py \
    PATH,HOME,LC_CTYPE "$W/receipts/D2_PREGATES_2026-09-26.json" >> "$LOG" 2>&1
echo "rc=$?" >> "$LOG"; rm -rf "$W/CHAIN/.claim_D2"
