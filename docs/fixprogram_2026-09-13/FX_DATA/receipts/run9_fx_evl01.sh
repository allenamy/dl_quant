#!/bin/sh
# FX-DATA EVL-01 run 9 (2026-09-16): what a forgotten CAL would cost on the price channel. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_evl01_cal.py out/trd/RECEIPT_fx_evl01_cal.json
