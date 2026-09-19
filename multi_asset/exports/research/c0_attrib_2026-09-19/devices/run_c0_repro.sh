#!/bin/sh
# C0 step 1 (2026-09-19): literal command line; this file IS the transcription of how RECEIPT_c0_repro.json was produced.
cd /workspace/c0_attrib_2026-09-19 || exit 3
mkdir -p logs out
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  nice -n 19 /workspace/venv/bin/python -B devices/c0_repro.py out > logs/c0_repro.log 2>&1
rc=$?
echo "c0_repro rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
exit $rc
