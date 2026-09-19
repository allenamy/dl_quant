#!/bin/sh
# C0 step 3 (2026-09-19): literal command line; this file IS the transcription of how C0_ATTRIB.json / C0_TABLES.md / RECEIPT_c0_attrib.json were produced.
cd /workspace/c0_attrib_2026-09-19 || exit 3
mkdir -p logs out
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  nice -n 19 /workspace/venv/bin/python -B devices/c0_attrib.py out out/c0_chars.npz > logs/c0_attrib.log 2>&1
rc=$?
echo "c0_attrib rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
exit $rc
