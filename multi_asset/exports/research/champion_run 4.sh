#!/bin/bash
# ★ 冠军配置正典脚本 — BASELINE_champion_config_2026-08-08.md §2 的可执行形态。
# 用法: champion_run.sh <panel.npz> <horizon> <seed> <tag> [encoder] [extra args...]
# 一切升级 = 本脚本 + 恰一个变量(通过 extra args 或换 encoder/panel)。
# 三陷阱在此固化: --xattn 显式开 / --lam_orth 显式 0 / 面板必须显式传。
set -e
PANEL="${1:?必须显式传面板路径 — 默认面板歧义是三陷阱之②}"
H="${2:?horizon}"; SEED="${3:?seed}"; TAG="${4:?tag}"; ENC="${5:-conformer}"; shift 5 || shift $#
[ -f "$PANEL" ] || { echo "面板不存在: $PANEL"; exit 1; }
echo "[champion] panel=$PANEL sha256=$(sha256sum "$PANEL" | cut -c1-16)"
echo "[champion] argv: horizon=$H seed=$SEED encoder=$ENC extra=[$*]"
cd /workspace/code && export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$PANEL" --target_horizon "$H" --aux_horizons 1,24 \
  --encoder "$ENC" --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 \
  --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed "$SEED" --save_tag "$TAG" --tag "$TAG" "$@"
