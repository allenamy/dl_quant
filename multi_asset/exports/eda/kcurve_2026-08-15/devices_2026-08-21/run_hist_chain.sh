#!/usr/bin/env bash
# 2020 起三腿 OOS 全链 @pod. 等 hist 缓存建成(pod_build_wide_ext 退出且文件在)再依次跑. 日志 /workspace/hist_chain.log
set -u
cd /workspace
CACHE=/workspace/data/dlnative_5m_wide829_f16_hist.npz
while pgrep -f pod_build_wide_ext >/dev/null || [ ! -f "$CACHE" ]; do sleep 120; done
echo "[$(date -u +%FT%TZ)] cache ready $(du -h $CACHE | cut -f1)"
CACHE_IN=$CACHE PANEL_OUT=/workspace/data/wide_panel_4h_hist.npz python3 pod_panel_wide_hist.py && \
CACHE_IN=$CACHE PANEL_IN=/workspace/data/wide_panel_4h_hist.npz FEA_OUT=/workspace/data/wide_fea_hist.npy META_OUT=/workspace/data/wide_fea_hist_meta.npz python3 pod_fea_wide_hist.py && \
python3 pod_slow_hist_folds.py && \
TAG=hist python3 pod_stop_arms_v3.py && echo "[$(date -u +%FT%TZ)] HIST_CHAIN_DONE" || echo "[$(date -u +%FT%TZ)] HIST_CHAIN_FAILED"
