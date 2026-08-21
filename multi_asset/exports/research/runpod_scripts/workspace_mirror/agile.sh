#!/bin/bash
# ★ 敏捷两级漏斗(用户令 2026-08-08): 筛选级 y24(~11min/臂, 3 路并发) → 胜者才进 y4 验证级(~50min)
# 每臂完成【立即】自动打 regime 记分卡并追加一行到 agile_results.tsv, 不需要人工看护。
# 并发上限 3(实测每臂 ~8.9GB / 32GB)。等待按 PID, 不轮询 nvidia-smi 文本。
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
MAXCONC=3
RES=/workspace/agile_results.tsv
[ -f $RES ] || printf "tag\tens_all\tQ0\tQ4\tworst_terc\ty2026\tnote\n" > $RES

run_one() {   # $1=tag  $2=panel  $3=horizon  $4=extra
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path "$2" --target_horizon "$3" --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed 42 --save_tag "$1" --tag "$1" $4 > /workspace/agile_$1.log 2>&1
  python3 /workspace/regime_scorecard.py "$1" 2>/dev/null | \
    awk -v t="$1" '$1==t {printf "%s\t%s\t%s\t%s\t%s\t%s\tOK\n", $1,$3,$4,$8,$9,$11}' >> $RES
  echo "[$(date -u +%H:%M:%SZ)] 完成 $1"
}

while IFS='|' read -r TAG PANEL HZ EXTRA; do
  [ -z "$TAG" ] && continue
  case "$TAG" in \#*) continue;; esac
  while [ $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l) -ge $MAXCONC ]; do sleep 30; done
  echo "[$(date -u +%H:%M:%SZ)] 起跑 $TAG (panel=$PANEL hz=$HZ extra=$EXTRA)"
  run_one "$TAG" "$PANEL" "$HZ" "$EXTRA" &
  sleep 40
done < /workspace/agile_cand.txt
wait
echo "=== agile 批次完成 $(date -u) ==="
