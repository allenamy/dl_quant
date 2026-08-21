#!/bin/bash
# 融合臂队列: 等 mask 臂(按 PID)→ 冒烟(前向+零初始化断言)→ fusion2t s42 → s2027
MQ=$(pgrep -of "bash mask_queue.sh")
[ -n "$MQ" ] && while kill -0 "$MQ" 2>/dev/null; do sleep 20; done
cd /workspace/code
export PYTHONPATH=/workspace/code
python3 - <<'PY' || exit 1
import torch, sys
sys.path.insert(0, "/workspace/code")
from multi_asset.model.wide_harness import FusionTwoTowerEncoder, WideFactorModel
m = WideFactorModel(FusionTwoTowerEncoder(53, split=32, d=64), n_factor_heads=6, xattn=True).cuda()
x = torch.randn(2, 140, 168, 53).cuda(); mask = (torch.rand(2, 140).cuda() > 0.2).float()
o = m(x, mask)["factor_scores"]
assert o.shape == (2, 140, 6), o.shape
# 零初始化断言: alpha=0 时改动塔B输入不得改变输出
x2 = x.clone(); x2[..., 32:] = torch.randn_like(x2[..., 32:])
o2 = m(x2, mask)["factor_scores"]
assert torch.allclose(o, o2, atol=1e-6), "零初始化失败 — 塔B在init时泄入输出"
print(f"冒烟 OK  params={sum(p.numel() for p in m.parameters()):,}  零初始化断言 PASS")
PY
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] f2t_yr24_s${S} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder fusion2t --n_factor_heads 6 --n_xattn 1 --d_model 64 --n_blocks 2 --seed "$S" \
    --save_tag "f2t_yr24_s${S}" --tag "f2t_yr24_s${S}" 2>&1 | tail -6
done
echo "=== fusion 队列完成 $(date -u) ==="
