#!/bin/bash
# Receipt-gated janitor for the FX queue. Frees an arm-seed combo npz ONLY when its saved series exists AND loads.
# Never touches a directory whose series is missing, never another agent's root, never the receipts. The combo arrays
# are deterministically regenerable from fa_fx.py + the pinned inputs, and the only consumers (ovn_adapter,
# fa_b8trcpt) have already run by the time the series exists.
# news2 2026-09-25: this file is written locally and copied with a sha comparison, NOT generated inline through ssh --
# a quote-hostile channel silently mangles scripts, and "generated" is the same event as "transferred".
FA=/dev/shm/fanom_2026-09-24
for i in $(seq 1 240); do
  for arm in FX1 FX2 FX3; do
    for s in 42 2027; do
      D=$FA/fx/${arm}_s${s}
      SER=$FA/receipts/SER_${arm}_s${s}.npz
      ls "$D"/*.npz >/dev/null 2>&1 || continue
      [ -s "$SER" ] || continue
      /workspace/venv/bin/python -c "import numpy,sys;numpy.load(sys.argv[1])" "$SER" 2>/dev/null || continue
      [ -f "$D/FA_FX_RECEIPT.json" ] || continue
      sz=$(du -sh "$D" | cut -f1)
      rm -f "$D"/*.npz
      echo "$(date -u +%H:%M:%SZ) freed $D ($sz) -- series present and loadable"
    done
  done
  sleep 60
done
