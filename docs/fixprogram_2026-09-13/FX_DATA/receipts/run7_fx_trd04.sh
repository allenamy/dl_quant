#!/bin/sh
# FX-DATA TRD-04 run 7 (2026-09-16): T1 / T8 / r19 state columns recomputed with the causal flag. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_trd04_states.py \
    out/trd/tradability_v1.npz \
    54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302 \
    out/trd/RECEIPT_fx_trd04_states.json \
    out/trd/trd04_states_series.npz
