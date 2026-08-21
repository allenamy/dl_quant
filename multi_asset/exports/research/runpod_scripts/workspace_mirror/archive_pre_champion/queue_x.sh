#!/bin/bash
# 修正队列(全臂开 xattn — 生产口径):
# 1 recon2 = rb32 + h24_C 全配置(xattn+年折2022+emb10) → 0.0466 终局闭环
# 2 rb32_x = 3折+xattn → 新标准对照
# 3 f2t_x ×2 seeds = fusion+xattn (冒烟已修 m.eval)
# 4 判别重测 = ch53_x 年折2024(这次真引燃 --year_folds)
cd /workspace/code
export PYTHONPATH=/workspace/code
run() { python3 -u multi_asset/train/train_wide_harness.py "$@" 2>&1 | tail -6; }
echo "=== [$(date -u +%H:%M:%SZ)] recon2: h24_C 全配置 ==="
run --wide_dl_path /workspace/data/wide_dl_rebuilt32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
  --year_folds --year_folds_from 2022 --embargo_days 10 --seed 42 \
  --save_tag rb32_recon2_full --tag rb32_recon2_full
echo "=== [$(date -u +%H:%M:%SZ)] rb32_x s42: 3折+xattn 新对照 ==="
run --wide_dl_path /workspace/data/wide_dl_rebuilt32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 --seed 42 \
  --save_tag rb32_x_s42 --tag rb32_x_s42
python3 - <<'PY' || exit 1
import torch,sys
sys.path.insert(0,"/workspace/code")
from multi_asset.model.wide_harness import FusionTwoTowerEncoder, WideFactorModel
m=WideFactorModel(FusionTwoTowerEncoder(53,split=32,d=64),n_factor_heads=6,xattn=True).cuda().eval()
x=torch.randn(2,140,168,53).cuda();k=(torch.rand(2,140).cuda()>0.2).float()
with torch.no_grad():
    o=m(x,k)["factor_scores"];x2=x.clone();x2[...,32:]=torch.randn_like(x2[...,32:])
    o2=m(x2,k)["factor_scores"]
assert torch.allclose(o,o2,atol=1e-6),"零初始化断言失败"
print("fusion smoke + 零断言 PASS  params=%s"%sum(p.numel() for p in m.parameters()))
PY
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] f2t_x s${S} ==="
  run --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 --seed "$S" \
    --save_tag "f2t_x_s${S}" --tag "f2t_x_s${S}"
done
echo "=== [$(date -u +%H:%M:%SZ)] 判别重测: ch53_x 年折2024 ==="
run --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
  --year_folds --year_folds_from 2024 --embargo_days 10 --seed 42 \
  --save_tag ch53_x_yf24 --tag ch53_x_yf24
echo "=== queue_x 完成 $(date -u) ==="
