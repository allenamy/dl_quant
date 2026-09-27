#!/bin/sh
# run_seat.sh -- momentum x seat decomposition, one process group. Terminal marker (line start): MOM_SEAT_DECOMP DONE. Traceback / rc!=0 = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/mom_2026-09-27; LOG=$A/seat.log
mkdir "$W/CHAIN/.claim_MOMSEAT" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=momentum_seat_decomp started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_MOMSEAT/owner" > "$A/seat.pgid"
cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /workspace/venv/bin/python -B dlarch_momentum_seat_decomp.py \
    PATH,HOME,LC_CTYPE "$W/receipts/MOM_SEAT_DECOMP_2026-09-27.json" >> "$LOG" 2>&1
echo "rc=$?" >> "$LOG"; rm -rf "$W/CHAIN/.claim_MOMSEAT"
