#!/bin/sh
# FX-DATA FXR-DATA-1 run 21 (2026-09-16): instantiate the unresolved-holdings register on the A0 C0 book. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_fxrdata1_register.py \
    out/trd/tradability_v1.npz \
    54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302 \
    out/arms \
    out/arms/RECEIPT_fxrdata1_register.json \
    out/arms/unresolved_holdings_register.csv
