#!/bin/bash
# 慢腿尺子补齐: y8 基线目前 3 种子且 s42 已标低离群 ⇒ 补到 5 种子再谈任何 y8 变体。
# 依据: 记忆 substratum_noise_needs_own_calibration(种子噪声视界依赖) + f2t/u137 两次"加种子就蒸发"。
set -e
for S in 4047 5051; do
  echo "=== yr8_s$S 起跑 $(date -u +%H:%MZ) ==="
  bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 8 $S yr8_s$S \
    > /workspace/logs/yr8_s$S.log 2>&1 || echo "ARM_FAILED yr8_s$S"
  echo "=== yr8_s$S 完成 $(date -u +%H:%MZ) ==="
done
echo Y8FLOOR_DONE
