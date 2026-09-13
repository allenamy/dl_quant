#!/bin/bash
# run_pod2.sh — FX-MODEL pod2 runner: <device.py> <expected_sha256> <log> [KEY=VAL ...]
# refuses unless the device on pod2 has the committed sha; env -i with an explicit allowlist; nice 19; writes "rc=<n>" as the last log line.
DEV=$1; EXP=$2; LOG=$3; shift 3
GOT=$(sha256sum "$DEV" | cut -d' ' -f1)
[ "$GOT" = "$EXP" ] || { echo "REFUSE sha $GOT != $EXP for $DEV" | tee -a "$LOG"; exit 9; }
echo "START $(date -u +%FT%TZ) dev=$DEV sha=$GOT args=$*" >> "$LOG"
nice -n 19 env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 "$@" /workspace/venv/bin/python -B "$DEV" >> "$LOG" 2>&1
rc=$?
echo "END $(date -u +%FT%TZ) rc=$rc" >> "$LOG"
echo "rc=$rc" >> "$LOG"
exit $rc
