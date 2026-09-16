#!/bin/sh
# FX-DATA HOL-01 run 15 (2026-09-16): provenance of the one hole-fixed panel + the 136 away-from-hole cells. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_hol01_provenance.py out/trd/RECEIPT_fx_hol01_provenance.json
