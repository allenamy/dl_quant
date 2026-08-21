#!/bin/bash
while ! grep -q A1_QUEUE_DONE /workspace/a1_main.log 2>/dev/null; do sleep 180; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== A1-CTRL 纯冠军对照 s42 $(date -u) ==="
bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 4 42 a1_ctrl_s42 conformer > /workspace/a1_ctrl_s42.log 2>&1
grep ENSEMBLE /workspace/a1_ctrl_s42.log | tail -5
for SPEC in 'film' 'inter' 'add'; do
  echo "=== A1v2 $SPEC +aux0.2 s42 $(date -u) ==="
  bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 4 42 a1v2_${SPEC}_s42 conformer --seq5m_path /workspace/data/dlnative_5m_k7_f16.npz --seq5m_fusion $SPEC --seq5m_aux 0.2 > /workspace/a1v2_${SPEC}_s42.log 2>&1
  grep ENSEMBLE /workspace/a1v2_${SPEC}_s42.log | tail -5
done
echo A1F_DONE
