#!/bin/bash
# 通宵队列: ① 四视界第二种子(定案稳定性论断) ② 45ch 装配 ③ book 族塔双种子(G4)
HZ=$(pgrep -of "bash /workspace/hz_queue.sh"); [ -n "$HZ" ] && while kill -0 "$HZ" 2>/dev/null; do sleep 30; done
cd /workspace && export PYTHONPATH=/workspace/code
R() { cd /workspace/code; python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$1" --target_horizon "$2" --encoder "$3" --n_factor_heads 6 --xattn --n_xattn 1 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 --seed "$4" \
  --save_tag "$5" --tag "$5" 2>&1 | tail -4; }
for H in 4 8 12 24; do
  echo "=== [$(date -u +%H:%M:%SZ)] hz${H}_s2027 ==="
  R /workspace/data/wide_dl_pm32_hz.npz "$H" conformer 2027 "hz${H}_s2027"
done
cd /workspace && python3 -u night.py || exit 1
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] bk45_yr24_s${S} (book 族塔) ==="
  R /workspace/data/wide_dl_45ch.npz 24 fusion2t "$S" "bk45_yr24_s${S}"
  echo "=== [$(date -u +%H:%M:%SZ)] bk45flat_yr24_s${S} (对照: 扁平) ==="
  R /workspace/data/wide_dl_45ch.npz 24 conformer "$S" "bk45flat_yr24_s${S}"
done
echo "=== 通宵队列完成 $(date -u) ==="
