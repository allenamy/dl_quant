#!/bin/sh
# Determinism probe for GPU-parallel training (lead 2026-09-25).
# Seed 99 is NOT a family member (family = 42 2027 7 11 23 101 3 5), so nothing delivered is touched.
# Run the SAME (arm, seed, fold) repeatedly and keep each scores.npz for a bitwise comparison.
#   A, B = same load level (the driver's seed + this probe = 2 concurrent)  -> run-to-run control
# If A != B then bitwise determinism does not hold even at fixed load, and the "must be identical"
# criterion is unattainable -- parallelism would not be the culprit. That control comes FIRST.
cd /workspace/dlarch_2026-09-24 || exit 9
D=/workspace/dlarch_2026-09-24/T3/T0/f10_s99
KEEP=/workspace/dlarch_2026-09-24/determinism_probe
mkdir -p "$KEEP"
for TAG in A B; do
  rm -rf "$D"
  echo "=== run $TAG start $(date -u +%H:%M:%SZ)  concurrent_trainers=$(pgrep -f 'dlarch_train_f10.py --arm' | wc -l) ===" >> "$KEEP/probe.log"
  nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader >> "$KEEP/probe.log" 2>&1
  env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_train_f10.py \
      --arm T0 --seed 99 --folds 2023 --env-whitelist PATH,HOME,LC_CTYPE >> "$KEEP/run_$TAG.log" 2>&1
  echo "run $TAG rc=$?" >> "$KEEP/probe.log"
  if [ -f "$D/2023/scores.npz" ]; then
    cp "$D/2023/scores.npz" "$KEEP/scores_$TAG.npz"
    cp "$D/2023/FOLD_RECEIPT.json" "$KEEP/receipt_$TAG.json"
    sha256sum "$KEEP/scores_$TAG.npz" >> "$KEEP/probe.log"
  else
    echo "run $TAG produced no scores.npz" >> "$KEEP/probe.log"
  fi
done
rm -rf "$D"
echo "PROBE_DONE" >> "$KEEP/probe.log"
