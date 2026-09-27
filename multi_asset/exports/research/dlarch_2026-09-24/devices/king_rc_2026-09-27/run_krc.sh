#!/bin/sh
# run_krc.sh -- King root cause (1)(2)(3a), one process group. Terminal marker (line start): KING_RC DONE. Traceback / rc!=0 = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/king_rc_2026-09-27; LOG=$A/krc.log
mkdir "$W/CHAIN/.claim_KRC" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=king_rootcause started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_KRC/owner" > "$A/krc.pgid"
cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /workspace/venv/bin/python -B dlarch_king_rootcause.py \
    PATH,HOME,LC_CTYPE "$W/receipts/KING_RC_2026-09-27.json" >> "$LOG" 2>&1
echo "rc=$?" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KRC"
