#!/bin/sh
# FX-DATA TRD-01 run 4 (2026-09-16): descriptive distribution of the state-without-finite-ret5 cells. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_trd_probe_ret5nan.py out/trd/RECEIPT_fx_trd_probe_ret5nan.json
