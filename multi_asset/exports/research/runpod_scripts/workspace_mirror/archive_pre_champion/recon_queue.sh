#!/bin/bash
# 终局对账队列: 杀旧 fusion 等待器 → 同装置臂(n_xattn=2+年折+emb10) → fusion 双臂
OLD=$(pgrep -of "bash fusion_queue.sh"); [ -n "$OLD" ] && kill "$OLD" 2>/dev/null
MQ=$(pgrep -of "bash mask_queue.sh")
[ -n "$MQ" ] && while kill -0 "$MQ" 2>/dev/null; do sleep 20; done
TW=$(pgrep -of "train_wide_harness"); [ -n "$TW" ] && while kill -0 "$TW" 2>/dev/null; do sleep 20; done
cd /workspace/code
export PYTHONPATH=/workspace/code
echo "=== [$(date -u +%H:%M:%SZ)] rb32_recon: n_xattn=2 + 年折2022 + emb10 s42 ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_rebuilt32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --n_xattn 2 --d_model 64 --n_blocks 2 \
  --year_folds_from 2022 --embargo_days 10 --seed 42 \
  --save_tag rb32_recon_yf2 --tag rb32_recon_yf2 2>&1 | tail -8
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] f2t_yr24_s${S} ==="
  python3 - <<'PY' || exit 1
import torch,sys
sys.path.insert(0,"/workspace/code")
from multi_asset.model.wide_harness import FusionTwoTowerEncoder, WideFactorModel
m=WideFactorModel(FusionTwoTowerEncoder(53,split=32,d=64),n_factor_heads=6,xattn=True).cuda()
x=torch.randn(2,140,168,53).cuda();k=(torch.rand(2,140).cuda()>0.2).float()
o=m(x,k)["factor_scores"];x2=x.clone();x2[...,32:]=torch.randn_like(x2[...,32:])
assert torch.allclose(o,m(x2,k)["factor_scores"],atol=1e-6),"零初始化断言失败"
print("smoke+零断言 OK")
PY
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder fusion2t --n_factor_heads 6 --n_xattn 1 --d_model 64 --n_blocks 2 --seed "$S" \
    --save_tag "f2t_yr24_s${S}" --tag "f2t_yr24_s${S}" 2>&1 | tail -6
done
echo "=== recon+fusion 队列完成 $(date -u) ==="
