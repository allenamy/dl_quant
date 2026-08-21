#!/bin/bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
for F in film inter add; do
  echo "=== A1v3 $F +aux0.2 s42 $(date -u) ==="
  bash /workspace/champion_run.sh /workspace/data/wide_dl_pm32_hz.npz 4 42 a1v3_${F}_s42 conformer --seq5m_path /workspace/data/dlnative_5m_k7_f16.npz --seq5m_fusion $F --seq5m_aux 0.2 > /workspace/a1v3_${F}_s42.log 2>&1
  grep ENSEMBLE /workspace/a1v3_${F}_s42.log | tail -5
done
echo "=== ctxk s42 $(date -u) ==="
/usr/bin/python3 -u /workspace/pod_fast2.py ctxk > /workspace/fast2_ctxk.log 2>&1
tail -2 /workspace/fast2_ctxk.log
echo "=== nullck (DL空值) $(date -u) ==="
/usr/bin/python3 -u /workspace/pod_fast2.py nullck > /workspace/fast2_nullck.log 2>&1
tail -2 /workspace/fast2_nullck.log
for SPEC in 'film2 24 1e-3 0.2 r1' 'film2 24 6e-4 0.2 r2' 'film2 32 1e-3 0.3 r3'; do
  set -- $SPEC
  echo "=== RECIPE $1 E=$2 LR=$3 D=$4 $5 $(date -u) ==="
  env EPOCHS=$2 LR=$3 DROP=$4 /usr/bin/python3 -u /workspace/pod_fast2.py $1 > /workspace/recipe_$5.log 2>&1
  tail -2 /workspace/recipe_$5.log
done
echo A1V3_ALL_DONE
