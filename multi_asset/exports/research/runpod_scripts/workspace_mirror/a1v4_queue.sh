#!/bin/bash
while ! grep -q A1V3_ALL_DONE /workspace/a1v3_main.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
for SPEC in 'film 0.5 aux05' 'filmv 0.2 vgate'; do
  set -- $SPEC
  echo "=== A1v4 $3 (fusion=$1 aux=$2) s42 $(date -u) ==="
  bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 4 42 a1v4_$3_s42 conformer --seq5m_path /workspace/data/dlnative_5m_k7_f16.npz --seq5m_fusion $1 --seq5m_aux $2 > /workspace/a1v4_$3_s42.log 2>&1
  grep ENSEMBLE /workspace/a1v4_$3_s42.log | tail -5
done
echo A1V4_DONE
