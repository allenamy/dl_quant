#!/bin/sh
# C0 SUPPLEMENT, post-freeze (2026-09-19): literal command line; this file IS the transcription of how C0_SUPP.json / C0_SUPP_TABLES.md / RECEIPT_c0_supp.json were produced.
cd /workspace/c0_attrib_2026-09-19 || exit 3
mkdir -p logs out
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  nice -n 19 /workspace/venv/bin/python -B devices/c0_supp.py out out/c0_chars.npz > logs/c0_supp.log 2>&1
rc=$?
echo "c0_supp rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
exit $rc
