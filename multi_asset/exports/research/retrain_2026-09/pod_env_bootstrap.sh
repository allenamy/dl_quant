#!/bin/bash
# pod 环境引导(月度重训前置, 幂等; RUNBOOK_monthly_retrain_2026-10 §1)。
# 09-01 教训: fresh 镜像缺 pandas/sklearn; torch 2.4+cu124 不支持 Blackwell sm_120 → 需 >=2.7 cu128。
set -e
pip install -q pandas lightgbm scikit-learn scipy
python3 - <<'EOF'
import torch
need = "sm_120"
if need not in torch.cuda.get_arch_list():
    raise SystemExit(f"TORCH_ARCH_MISSING {need} (当前 {torch.__version__} {torch.cuda.get_arch_list()}); 执行: pip install --upgrade 'torch>=2.7' --index-url https://download.pytorch.org/whl/cu128")
x = torch.randn(256, 256, device="cuda")
assert float((x @ x).sum()) != 0
print("GPU_OK", torch.__version__, torch.cuda.get_device_name(0))
EOF
python3 -c "import pandas,sklearn,lightgbm,scipy,numpy; print('PY_STACK_OK', numpy.__version__, lightgbm.__version__)"
for f in /workspace/data/dlnative_5m_wide829_f16_ext.npz /workspace/data/wide_panel_4h_v3splice.npz \
         /workspace/fund_state_canoncont.json /workspace/panel_symbols_wide.txt /workspace/zload.py; do
  [ -e "$f" ] || { echo "MISSING $f"; exit 3; }
done
echo ENV_BOOTSTRAP_OK
