#!/bin/bash
# ★ Scaling 阶梯(用户令: 5 年数据+5090, 加大容量深挖) — champion 配置 + 恰一个容量变量
# 现基线 d64×2blk=255k 参数. 阶梯: d128×2 / d128×4 / d256×4 / 窗 336。判据: Δ≥+0.005 双种子。
OLD=$(pgrep -of "bash /workspace/bk4.sh"); [ -n "$OLD" ] && while kill -0 "$OLD" 2>/dev/null; do sleep 20; done
OLD2=$(pgrep -of "bash /workspace/lam0.sh"); [ -n "$OLD2" ] && while kill -0 "$OLD2" 2>/dev/null; do sleep 20; done
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --year_folds --year_folds_from 2022 --embargo_days 10 \
  "$@" 2>&1 | tail -4; }
for CFG in "--d_model 128 --n_blocks 2 :: d128b2" "--d_model 128 --n_blocks 4 :: d128b4" "--d_model 256 --n_blocks 4 :: d256b4"; do
  ARGS="${CFG%% ::*}"; TAG="${CFG##*:: }"
  for S in 42 2027; do
    echo "=== [$(date -u +%H:%M:%SZ)] scale_${TAG}_s${S} ==="
    R $ARGS --seed "$S" --save_tag "scale_${TAG}_s${S}" --tag "scale_${TAG}_s${S}"
  done
done
echo "=== scaling 阶梯完成 $(date -u) ==="
