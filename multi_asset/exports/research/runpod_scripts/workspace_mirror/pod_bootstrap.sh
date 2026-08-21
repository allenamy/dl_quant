#!/bin/bash
# ★ Pod 重启自举 — stop 后容器盘全失(torch/.ssh/挂载点), volume 幸存。
# 新 pod/重启后经 web 终端跑一次: bash /workspace/pod_bootstrap.sh
set -e
echo "[1/4] SSH 通道恢复"
mkdir -p /root/.ssh && cp /workspace/.authorized_keys_backup /root/.ssh/authorized_keys
chmod 700 /root/.ssh && chmod 600 /root/.ssh/authorized_keys
echo "[2/4] python 环境(容器镜像若已带 torch 会跳过)"
python3 -c "import torch" 2>/dev/null || pip install torch numpy pandas scipy --quiet
python3 -c "import numpy, pandas, scipy" 2>/dev/null || pip install numpy pandas scipy --quiet
echo "[3/4] 挂载点符号链接(训练产物写大盘)"
E=/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports
mkdir -p "$(dirname $E)" 2>/dev/null || true
mkdir -p "$E" 2>/dev/null || true
[ -L "$E/train" ] || { rm -rf "$E/train"; ln -s /workspace/exports_train "$E/train"; }
echo "[4/4] 自检"
python3 -c "import torch; print('  torch', torch.__version__, 'cuda', torch.cuda.is_available())"
ls /workspace/code/multi_asset/train/train_wide_harness.py /workspace/champion_run.sh
echo "READY — 训练可直接用 /workspace/champion_run.sh"
