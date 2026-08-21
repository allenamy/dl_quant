#!/bin/bash
# 有控并行: 实测 23GB 空闲 / 128 核 load 5.9 / GPU util 0% ⇒ 串行纯浪费。
# 与"单一串行队列"教训的区别: 那是【两个等待器失控同时放行】; 这里是显式并发 + 逐 PID 记录 + 已杀链防重复。
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24   --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   --seed "$1" --save_tag f2t_lam0_s$1 --tag f2t_lam0_s$1 2>&1 | tail -3; }
R 42 > /workspace/f2t_s42.log 2>&1 &
echo $! > /workspace/f2t_s42.pid
sleep 45
R 2027 > /workspace/f2t_s2027.log 2>&1 &
echo $! > /workspace/f2t_s2027.pid
wait
echo "=== f2t 并行完成 $(date -u)"
