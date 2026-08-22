#!/bin/bash
# 2026-08-22 queue45 (replaces queue4): A2 ammo-merge arm FIRST, then 2026-fold reruns via f26 copy (ARM env-first -> no pred clobber)
while kill -0 3742449 2>/dev/null; do sleep 120; done
cd /mnt/storage/private/work_hsy/dlw_2026-08-22
for S in 42 2027; do
  echo "=== START A2f89_s$S $(date -u)"
  ARM=A2f89 XA=1 HEADS=8 SEED=$S BATCH=4 FOLD_MAX=2025 python -u dlw_train_a2.py > logs/train_A2f89_s$S.log 2>&1
  echo "=== END A2f89_s$S rc=$? $(date -u)"
done
for S in 42 2027 3037; do
  echo "=== START D1h8f26_s$S $(date -u)"
  ARM=D1h8f26 XA=1 HEADS=8 SEED=$S BATCH=2 FOLD_MIN=2026 python -u dlw_train_f26.py > logs/train_D1h8f26_s$S.log 2>&1
  echo "=== END D1h8f26_s$S rc=$? $(date -u)"
done
echo "=== START D0f26_s42 $(date -u)"
ARM=D0f26 XA=0 HEADS=8 SEED=42 BATCH=2 FOLD_MIN=2026 python -u dlw_train_f26.py > logs/train_D0f26_s42.log 2>&1
echo "=== END D0f26_s42 rc=$? $(date -u)"
for S in 42 2027; do
  echo "=== START A2f89f26_s$S $(date -u)"
  ARM=A2f89f26 XA=1 HEADS=8 SEED=$S BATCH=2 FOLD_MIN=2026 python -u dlw_train_a2.py > logs/train_A2f89f26_s$S.log 2>&1
  echo "=== END A2f89f26_s$S rc=$? $(date -u)"
done
echo "QUEUE45_DONE $(date -u)"
