#!/bin/bash
# members_run_pod2.sh -- verbatim pod2 launcher for members_audit.py (CPU only, nice 19, cores 56-63, env whitelist).
# Use on pod2:  bash /workspace/aud_prod_2026-09-13/members/device/members_run_pod2.sh
set -u
P=/workspace/aud_prod_2026-09-13/members
cd $P
mkdir -p receipts
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > receipts/gpu_before.txt 2>&1
nice -n 19 taskset -c 56-63 env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 /workspace/venv/bin/python -B device/members_audit.py PATH,HOME,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS > receipts/members_audit_stdout.log 2>&1
rc=$?
echo "EXIT rc=$rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> receipts/members_audit_stdout.log
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader > receipts/gpu_after.txt 2>&1
exit $rc
