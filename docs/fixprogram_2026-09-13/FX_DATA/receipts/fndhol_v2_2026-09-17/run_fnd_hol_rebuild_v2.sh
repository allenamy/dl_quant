#!/bin/sh
# FX-DATA FP2-1 (E): the v2 rebuild device (F05/R01/R02: no-source and no-seed names never counted as REPRODUCED) on the SAME inputs as run 24. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 /workspace/venv/bin/python -B devices/fx_fnd_hol_rebuild_v2.py \
    P9_declared_interval_table_2026-07-01_2026-09-13T12Z_zipszips_2026-08.csv.gz \
    366763a4aae854b2415fb461334efe95c1a74f93fc9e81c112c6138b16ec3197 \
    out/fndhol_v2 \
    out/fndhol_v2/RECEIPT_fx_fnd_hol_rebuild_v2.json
echo "FND_HOL_V2_RC=$?"
