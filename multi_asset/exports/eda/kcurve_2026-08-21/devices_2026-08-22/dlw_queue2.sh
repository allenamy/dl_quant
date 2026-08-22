#!/bin/bash
# DLW · GPU 队列 v2(取代 dlw_queue.sh 的臂序; 臂集合与预注册 §P.2/P.3 完全相同, 只把噪声标定种子提前, 使 D1−D0 判据(≥2×种子 sd)更早可判)
# 臂序: D0 s42 → D1h8 s42 → D1h8 s2027 → D1h8 s3037 → D1h4 s42 → D1h1 s42 → D0 s2027
# 完成判定: results/dlw_<tag>.DONE 或 results/dlw_<tag>.json 含 "total_sec"(四折齐) ⇒ 跳过。单卡一任务: GPU 有进程则等待。
# 用法: setsid nohup bash dlw_queue2.sh > logs/queue2.log 2>&1 < /dev/null &
cd /mnt/storage/private/work_hsy/dlw_2026-08-22 || exit 1
source /root/miniconda3/etc/profile.d/conda.sh && conda activate hsy_v5push
echo "QUEUE2_PID $$ start $(date -u)"
done_tag() { [ -f "results/dlw_$1.DONE" ] || grep -q '"total_sec"' "results/dlw_$1.json" 2>/dev/null; }
run() {  # XA HEADS SEED
  local tag
  if [ "$1" = "0" ]; then tag="D0_s$3"; else tag="D1h$2_s$3"; fi
  if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)" ]; do sleep 60; if done_tag "$tag"; then echo "skip ${tag} (done while waiting)"; return; fi; done
  if done_tag "$tag"; then echo "skip ${tag} (done)"; return; fi
  echo "=== START ${tag} $(date -u)"
  XA=$1 HEADS=$2 SEED=$3 python -u dlw_train.py > "logs/train_${tag}.log" 2>&1
  local rc=$?
  echo "=== END ${tag} rc=${rc} $(date -u)"
  if [ $rc -eq 0 ] && grep -q TRAIN_DONE "logs/train_${tag}.log"; then touch "results/dlw_${tag}.DONE"; fi
}
run 0 8 42
run 1 8 42
run 1 8 2027
run 1 8 3037
run 1 4 42
run 1 1 42
run 0 8 2027
echo "QUEUE2_DONE $(date -u)"
