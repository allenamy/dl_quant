#!/bin/sh
# F10_FULL main arm: --train-frac 1.0, three pre-declared seeds, sequential.
# Fail-closed: `set -e` stops the chain on the first red, so a later seed can never mask an earlier
# failure. Each seed goes through dlarch_f10full_launch.py, which certifies the trainer that executes.
set -e

D=/workspace/dlarch_2026-09-24
A=$D/f10full_2026-09-26
PIN=db6771e30fb7d1befcf9bb77f4c0504131fc0d491e02dc45bab15ed04e5d8e61
PY=/workspace/venv/bin/python

for S in 42 2027 7; do
  echo "=== SEED $S start $(date -u +%FT%TZ) ==="
  env -u PWD -u _ $PY $D/dlarch_f10full_launch.py PATH,HOME,LC_CTYPE "$A" "$PIN" \
      "$A/PREFLIGHT_F10FULL.json" "$A/receipts/LAUNCH_MAIN_s$S.json" \
      -- --arm T0 --no-mask --train-frac 1.0 --seed "$S"
  echo "=== SEED $S done $(date -u +%FT%TZ) ==="
done
echo "F10FULL_MAIN_ALL_SEEDS_DONE $(date -u +%FT%TZ)"
