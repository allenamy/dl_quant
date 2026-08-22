#!/bin/bash
# F-8 队列 @jpline: 等 build(PID $1)结束 → run ridge → run lgbm → judge; 每段日志独立; 标记文件 results/f8_<stage>.DONE
cd /mnt/storage/private/work_hsy/f8_2026-08-22 || exit 1
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
BUILD_PID=$1
echo "QUEUE_PID $$ waiting build ${BUILD_PID} $(date -u)"
while kill -0 "$BUILD_PID" 2>/dev/null; do sleep 20; done
if ! grep -q BUILD_DONE logs/build.log; then echo "BUILD_FAILED $(date -u)"; exit 2; fi
touch results/f8_build.DONE
echo "=== RUN ridge $(date -u)"; python -u f8_higher_order_features.py run --models ridge > logs/run_ridge.log 2>&1; rc=$?; echo "ridge rc=$rc $(date -u)"
grep -q RUN_DONE_ridge logs/run_ridge.log && touch results/f8_run_ridge.DONE
echo "=== JUDGE(ridge only) $(date -u)"; python -u f8_higher_order_features.py judge > logs/judge_ridge.log 2>&1; echo "judge1 rc=$? $(date -u)"
echo "=== RUN lgbm $(date -u)"; python -u f8_higher_order_features.py run --models lgbm > logs/run_lgbm.log 2>&1; rc=$?; echo "lgbm rc=$rc $(date -u)"
grep -q RUN_DONE_lgbm logs/run_lgbm.log && touch results/f8_run_lgbm.DONE
echo "=== JUDGE(full) $(date -u)"; python -u f8_higher_order_features.py judge > logs/judge.log 2>&1; echo "judge rc=$? $(date -u)"
grep -q JUDGE_DONE logs/judge.log && touch results/f8_judge.DONE
echo "QUEUE_DONE $(date -u)"
