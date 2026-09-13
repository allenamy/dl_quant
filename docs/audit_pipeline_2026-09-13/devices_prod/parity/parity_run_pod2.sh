#!/bin/bash
# parity_run_pod2.sh -- verbatim pod2 launcher for the AUDIT_PROD parity extraction (CPU only, nice 19, 4 cores, env whitelist).
# Usage on pod2: bash /workspace/aud_prod_2026-09-13/parity/device/parity_run_pod2.sh extract
set -u
P=/workspace/aud_prod_2026-09-13/parity
cd $P
mkdir -p extract
case "$1" in
  extract)
    nice -n 19 taskset -c 60-63 env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 /workspace/venv/bin/python -B device/parity_x0910_extract.py PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS > extract/parity_x0910_extract_stdout.log 2>&1
    rc=$?; echo "EXIT rc=$rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> extract/parity_x0910_extract_stdout.log; exit $rc ;;
  *) echo "unknown mode $1"; exit 2 ;;
esac
