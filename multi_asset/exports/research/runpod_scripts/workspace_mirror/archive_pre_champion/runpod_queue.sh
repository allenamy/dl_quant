#!/bin/bash
# RunPod GPU 队列 —— 数据就位后一次性排满, GPU 不留空窗。
# 纪律: 每臂完成立即起下一臂; 日志分文件; 全部 nohup(ssh 断不影响)。
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code:$PYTHONPATH
P=/workspace/data/panel_0731.npz
L=/workspace/exports/train/logs
mkdir -p $L /workspace/exports/train

run() {  # run <save_tag> <extra args...>
  tag=$1; shift
  [ -d "/workspace/exports/train/$tag" ] && [ $(ls /workspace/exports/train/$tag/*model.pt 2>/dev/null | wc -l) -ge 5 ] && { echo "[skip] $tag 已完成"; return; }
  echo "[$(date -u +%H:%M:%SZ)] 起 $tag"
  python3 multi_asset/train/train_wide_harness.py --encoder conformer --n_factor_heads 6 \
    --xattn --lam_orth 0 --wide_dl_path $P --year_folds --embargo 8 \
    --save_tag $tag --tag $tag "$@" > $L/$tag.log 2>&1
  echo "[$(date -u +%H:%M:%SZ)] 完 $tag rc=$?"
}

# ── 队列(按证据强度排序) ─────────────────────────────────────────────
# 1. y24 换装候选补种子 —— 最接近部署, 当前仅 2 种子且塌陷周分化
run rp_h24_s3 --target_horizon 24 --seed 2027
run rp_h24_s4 --target_horizon 24 --seed 3037
run rp_h24_s5 --target_horizon 24 --seed 4047
# 2. 基线对照(同 pod 同环境, 供公平比较)
run rp_ctrl   --target_horizon 4  --seed 1337
echo "[$(date -u +%H:%M:%SZ)] 队列完成"
