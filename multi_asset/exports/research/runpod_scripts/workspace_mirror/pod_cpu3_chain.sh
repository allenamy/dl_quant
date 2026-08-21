#!/bin/bash
# CPU 三件链: ① §29 legweight 臂 → ② §30 rank-only → (并行: §28 历史下载) → ③ §28 扩轴链+终判.
cd /workspace
L="/workspace/cpu3_$(date -u +%s).log"
ln -sf "$L" /workspace/cpu3.log
echo "=== cpu3 start $(date -u +%FT%TZ)" >> "$L"

# 历史下载先行(网络型, 与 CPU 任务并行)
nohup python3 pod_hist_dl.py > hist_dl.log 2>&1 &

# ① §29
python3 pod_legweight_arms.py >> "$L" 2>&1
grep -q LEGWEIGHT_DONE "$L" || echo ABORT_LEGWEIGHT >> "$L"

# ② §30
python3 pod_rankonly.py >> "$L" 2>&1
grep -q RANKONLY_DONE "$L" || echo ABORT_RANKONLY >> "$L"

# ③ §28: 等下载完 → hist 缓存 → 面板 → 特征 → 终判
for i in $(seq 1 360); do
  grep -q HIST_DL_DONE hist_dl.log 2>/dev/null && break
  sleep 30
done
grep -q HIST_DL_DONE hist_dl.log || { echo ABORT_HIST_DL >> "$L"; exit 1; }
rm -f /workspace/wide_ext.lock
EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=/workspace/data/dlnative_5m_wide829_f16_hist.npz \
  python3 pod_build_wide_ext.py >> "$L" 2>&1
grep -q EXT_CACHE_DONE "$L" || { echo ABORT_HIST_CACHE >> "$L"; exit 1; }
CACHE_IN=/workspace/data/dlnative_5m_wide829_f16_hist.npz PANEL_OUT=/workspace/data/wide_panel_4h_hist.npz \
  python3 pod_panel_ext.py >> "$L" 2>&1
grep -q PANEL_EXT_DONE "$L" || { echo ABORT_HIST_PANEL >> "$L"; exit 1; }
CACHE_IN=/workspace/data/dlnative_5m_wide829_f16_hist.npz PANEL_IN=/workspace/data/wide_panel_4h_hist.npz \
  FEA_OUT=/workspace/data/wide_fea_hist.npy META_OUT=/workspace/data/wide_fea_hist_meta.npz \
  python3 pod_fea_ext.py >> "$L" 2>&1
grep -q FEA_EXT_DONE "$L" || { echo ABORT_HIST_FEA >> "$L"; exit 1; }
FEA_IN=/workspace/data/wide_fea_hist.npy META_IN=/workspace/data/wide_fea_hist_meta.npz \
  PANEL_IN=/workspace/data/wide_panel_4h_hist.npz \
  python3 pod_slow_hist_judge.py >> "$L" 2>&1
grep -q HIST_JUDGE_DONE "$L" || { echo ABORT_HIST_JUDGE >> "$L"; exit 1; }
echo "=== cpu3 ALL_DONE $(date -u +%FT%TZ)" >> "$L"
