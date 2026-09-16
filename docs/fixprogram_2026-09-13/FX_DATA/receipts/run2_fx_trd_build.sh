#!/bin/sh
# FX-DATA TRD-01 run 2 (2026-09-16). Literal command line; this file IS the transcription.
# Run 1 (2026-09-13 15:13Z) ended rc=1 in the reload roundtrip; its literal command line was never recorded
# (only paraphrased in FX_DATA/STATE_PAUSE.md), so run 2 is the authoritative command for this artifact.
cd /workspace/fx_data_2026-09-13
env -i \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HOME=/root \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  PYTHONPATH=/workspace/fx_data_2026-09-13/common \
  nice -n 19 python -B devices/fx_trd_build.py out/trd t7_klines_1h PERP_KLINES_RECEIPT.json
