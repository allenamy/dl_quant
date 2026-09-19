#!/bin/sh
# G0 step 2 (2026-09-19): literal command line; this file IS the transcription of how the G0 tables were produced (needs step 1 = run_g0_state.sh).
cd /workspace/regime_g0_2026-09-19 || exit 3
mkdir -p logs out
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  nice -n 19 /workspace/venv/bin/python -B devices/g0_regime_tables.py out out > logs/g0_regime_tables.log 2>&1
rc=$?
echo "g0_regime_tables rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
exit $rc
