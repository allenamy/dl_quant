#!/bin/sh
# run_mom.sh -- momentum-loading description, one process group. Terminal marker (line start): MOM_LOADING DONE. Traceback / rc!=0 = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/mom_2026-09-27; LOG=$A/mom.log
mkdir "$W/CHAIN/.claim_MOM" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=momentum_loading started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_MOM/owner" > "$A/mom.pgid"
cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /workspace/venv/bin/python -B dlarch_momentum_loading.py \
    PATH,HOME,LC_CTYPE "$W/receipts/MOM_LOADING_2026-09-27.json" >> "$LOG" 2>&1
echo "rc=$?" >> "$LOG"; rm -rf "$W/CHAIN/.claim_MOM"
