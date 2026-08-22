#!/bin/bash
# F-8 P2 标度曲线队列 @jpline: build2 → ridge_grid 全档 → judge → ridge_fixed base → lgbm 全档 → judge; BLAS 线程限 8
cd /mnt/storage/private/work_hsy/f8_2026-08-22 || exit 1
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
echo "QUEUE2_PID $$ start $(date -u)"
python -u f8_scaling_curve.py build > logs/build2.log 2>&1; echo "build2 rc=$? $(date -u)"
grep -q BUILD2_DONE logs/build2.log || { echo "BUILD2_FAILED $(date -u)"; exit 2; }
echo "=== RUN2 ridge_grid $(date -u)"; python -u f8_scaling_curve.py run --models ridge_grid > logs/run2_ridge.log 2>&1; echo "ridge_grid rc=$? $(date -u)"
python -u f8_scaling_curve.py judge > logs/judge2_ridge.log 2>&1; echo "judge2(ridge) rc=$? $(date -u)"
python -u f8_scaling_curve.py run --models ridge_fixed --arms base > logs/run2_ridgefixed.log 2>&1; echo "ridge_fixed rc=$? $(date -u)"
echo "=== RUN2 lgbm $(date -u)"; python -u f8_scaling_curve.py run --models lgbm > logs/run2_lgbm.log 2>&1; echo "lgbm rc=$? $(date -u)"
python -u f8_scaling_curve.py judge > logs/judge2.log 2>&1; echo "judge2 rc=$? $(date -u)"
grep -q JUDGE2_DONE logs/judge2.log && touch results/f8s_judge.DONE
echo "QUEUE2_DONE $(date -u)"
