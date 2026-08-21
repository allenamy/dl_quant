#!/bin/bash
# A1 冠军联合双种子 — champion_run.sh + 恰一个变量(--seq5m_path)
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
for SD in 42 2027; do
  echo "=== A1 s$SD start $(date -u) ==="
  bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 4 $SD a1_5m_s$SD conformer --seq5m_path /workspace/data/dlnative_5m_k7_f16.npz > /workspace/a1_s$SD.log 2>&1
  tail -4 /workspace/a1_s$SD.log
done
echo A1_QUEUE_DONE
