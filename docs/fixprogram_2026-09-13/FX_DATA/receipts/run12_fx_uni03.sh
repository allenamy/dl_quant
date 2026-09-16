#!/bin/sh
# FX-DATA UNI-03 run 12 (2026-09-16): the 2026-09 U-PIT / CRYPTO mask row. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_uni03_sep_mask.py out/uni03 out/uni03/RECEIPT_fx_uni03_sep_mask.json
