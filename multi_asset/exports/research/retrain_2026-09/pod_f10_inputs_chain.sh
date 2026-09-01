#!/bin/bash
# f10 输入链 @pod: targets_ext → 平价门 → fea82_ext → fea89_ext(build)。任一步败即停并落 FAIL 标记。
set -u
cd /workspace
echo "[f10chain] targets $(date -u +%H:%M)"
python3 pod_dlw_targets_ext.py >> f10_targets.log 2>&1 || { echo F10CHAIN_FAIL_targets; exit 1; }
python3 pod_gate_dlw_ext.py >> f10_gate_dlw.log 2>&1 || { echo F10CHAIN_FAIL_gate_dlw; exit 1; }
echo "[f10chain] fea82 $(date -u +%H:%M)"
F171_CACHE=/workspace/data/dlnative_5m_wide829_f16_ext.npz F171_OUT=/workspace/dlw_ext \
  python3 pod_dlw_features_ext.py >> f10_fea82.log 2>&1 || { echo F10CHAIN_FAIL_fea82; exit 1; }
echo "[f10chain] fea89 $(date -u +%H:%M)"
python3 pod_f8_build_ext.py build >> f10_fea89.log 2>&1 || { echo F10CHAIN_FAIL_fea89; exit 1; }
echo F10CHAIN_DONE $(date -u +%H:%M)
