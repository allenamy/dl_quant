#!/bin/sh
# FX-DATA FND-01/02 + HOL-01 run 24 (2026-09-16): the one merged rebuild. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_fnd_hol_rebuild.py \
    P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz \
    366763a4aae854b2415fb461334efe95c1a74f93fc9e81c112c6138b16ec3197 \
    out/fndhol \
    out/fndhol/RECEIPT_fx_fnd_hol_rebuild.json
