#!/bin/bash
# DLW · GPU 队列(3090 单卡单任务串行)@jpline — 预注册 §P.2/P.3 臂序: D0 s42 → D1h8 s42 → D1h4 s42 → D1h1 s42 → D1h8 s2027 → D1h8 s3037 → D0 s2027
# 用法: nohup bash dlw_queue.sh > logs/queue.log 2>&1 &   (记录 PID); 跳过已 DONE 的臂; 每臂日志 logs/train_<tag>.log
cd /mnt/storage/private/work_hsy/dlw_2026-08-22 || exit 1
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
echo "QUEUE_PID $$ start $(date -u)"
run() {  # XA HEADS SEED
  local tag
  if [ "$1" = "0" ]; then tag="D0_s$3"; else tag="D1h$2_s$3"; fi
  if [ -f "results/dlw_${tag}.DONE" ]; then echo "skip ${tag} (DONE)"; return; fi
  # 单卡一任务纪律: 若有别的进程占 GPU, 等待(每 60s 查一次)
  while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)" ]; do echo "GPU busy, wait 60s $(date -u)"; sleep 60; done
  echo "=== START ${tag} $(date -u)"
  XA=$1 HEADS=$2 SEED=$3 python -u dlw_train.py > "logs/train_${tag}.log" 2>&1
  local rc=$?
  echo "=== END ${tag} rc=${rc} $(date -u)"
  if [ $rc -eq 0 ] && grep -q TRAIN_DONE "logs/train_${tag}.log"; then touch "results/dlw_${tag}.DONE"; fi
}
run 0 8 42
run 1 8 42
run 1 4 42
run 1 1 42
run 1 8 2027
run 1 8 3037
run 0 8 2027
echo "QUEUE_DONE $(date -u)"
