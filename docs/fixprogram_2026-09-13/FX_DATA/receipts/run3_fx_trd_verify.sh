#!/bin/sh
# FX-DATA TRD-01 run 3 (2026-09-16): verify the run-2 artifact against the AUDIT_DATA census. Literal command line.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_trd_verify.py \
    out/trd/tradability_v1.npz \
    54d409d0ddf695f497d8b27fb5bdee960deda763250d530a16bd7cf506205302 \
    AD_H_tradability.json \
    529df8b3cc66918e53db497156df4718ed5c09138ede8829144023dc2cbdd2a0 \
    out/trd/RECEIPT_fx_trd_verify.json
