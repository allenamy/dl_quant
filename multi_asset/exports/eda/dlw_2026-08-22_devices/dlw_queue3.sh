#!/bin/bash
# DLW · GPU 队列 v3(取代 v2; 臂集合 = xattn 预注册 7 臂 + D2 多视界预注册 2 臂; 臂序把 D2 主臂排在 D1h8 三种子之后、头数敏感臂之前)
# 臂序: D0 s42 → D1h8 s42 → D1h8 s2027 → D1h8 s3037 → D2aux12 s42 → D1h4 s42 → D1h1 s42 → D0 s2027 → D2aux12 s2027
# 完成判定: results/dlw_<tag>.DONE 或 results/dlw_<tag>.json 含 "total_sec" ⇒ 跳过。单卡一任务: GPU 有进程则等待。D2 需 data/dlw_targets_y12.npz, 缺则跳过并记录。
# 用法: setsid nohup bash dlw_queue3.sh > logs/queue3.log 2>&1 < /dev/null &
cd /mnt/storage/private/work_hsy/dlw_2026-08-22 || exit 1
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
echo "QUEUE3_PID $$ start $(date -u)"
done_tag() { [ -f "results/dlw_$1.DONE" ] || grep -q '"total_sec"' "results/dlw_$1.json" 2>/dev/null; }
wait_gpu() { while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)" ]; do sleep 60; done; }
run() {  # XA HEADS SEED
  local tag
  if [ "$1" = "0" ]; then tag="D0_s$3"; else tag="D1h$2_s$3"; fi
  if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  wait_gpu; if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  echo "=== START ${tag} $(date -u)"
  XA=$1 HEADS=$2 SEED=$3 python -u dlw_train.py > "logs/train_${tag}.log" 2>&1
  local rc=$?; echo "=== END ${tag} rc=${rc} $(date -u)"
  if [ $rc -eq 0 ] && grep -q TRAIN_DONE "logs/train_${tag}.log"; then touch "results/dlw_${tag}.DONE"; fi
}
run_aux() {  # SEED
  local tag="D2aux12_s$1"
  if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  if [ ! -f data/dlw_targets_y12.npz ]; then echo "skip ${tag} (no y12 targets yet) $(date -u)"; return; fi
  wait_gpu; if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  echo "=== START ${tag} $(date -u)"
  SEED=$1 python -u dlw_train_aux.py > "logs/train_${tag}.log" 2>&1
  local rc=$?; echo "=== END ${tag} rc=${rc} $(date -u)"
  if [ $rc -eq 0 ] && grep -q TRAIN_DONE "logs/train_${tag}.log"; then touch "results/dlw_${tag}.DONE"; fi
}
run 0 8 42
run 1 8 42
run 1 8 2027
run 1 8 3037
run_aux 42
run 1 4 42
run 1 1 42
run 0 8 2027
run_aux 2027
echo "QUEUE3_DONE $(date -u)"
