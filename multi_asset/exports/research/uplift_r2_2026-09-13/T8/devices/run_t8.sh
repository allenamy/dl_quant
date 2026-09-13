#!/bin/bash
# run_t8.sh <device.py> [args...] — FOREGROUND run of one T8 pod2 device under PREREG_T8 §10 (env -i whitelist, nice 10, 8 cores 40-47).
# Writes receipts/<tag>_stdout.log and receipts/RC_<tag>.txt (rc + last log line + utc). A run without both did not pass. No kill logic, by design.
set -u
cd /workspace/uplift_r2_2026-09-13/T8 || exit 2
dev="$1"; shift
tag=$(basename "$dev" .py); for a in "$@"; do tag="${tag}_$a"; done
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
  nice -n 10 taskset -c 40-47 /workspace/venv/bin/python "devices/$dev" PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS "$@" \
  > "receipts/${tag}_stdout.log" 2>&1
rc=$?
last=$(tail -n 1 "receipts/${tag}_stdout.log")
printf 'rc=%s\nsummary=%s\nutc=%s\n' "$rc" "$last" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "receipts/RC_${tag}.txt"
cat "receipts/RC_${tag}.txt"
exit $rc
