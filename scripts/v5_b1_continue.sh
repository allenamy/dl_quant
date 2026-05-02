#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
EMAPOOL_PRED=experiments/v5_screen/B1/emapool/fold_0/test_preds.npz
echo "[CONTINUE] waiting for emapool: $EMAPOOL_PRED"
while [ ! -f "$EMAPOOL_PRED" ]; do sleep 30; done
echo "[CONTINUE] emapool done at $(date -u +%FT%TZ)"

run_extra() {
  local NAME="$1"; local CFG="$2"
  local LOG="logs/v5_b1_${NAME}.log"
  local PRED="experiments/v5_screen/B1/$NAME/fold_0/test_preds.npz"
  if [ -f "$PRED" ] && [ $(stat -c%s "$PRED") -gt 1000 ]; then
    echo "[CONTINUE] SKIP $NAME"; return 0
  fi
  rm -rf experiments/v5_screen/B1/$NAME
  echo "[CONTINUE] running $NAME at $(date -u +%FT%TZ)"
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py --name "$NAME" --config "$CFG" --out-base experiments/v5_screen/B1 > "$LOG" 2>&1
  local RC=$?
  echo "[CONTINUE] $NAME rc=$RC at $(date -u +%FT%TZ)"
  if [ $RC -eq 0 ] && [ -f "$PRED" ]; then
    python scripts/v5_eval_comprehensive.py --exp-dir experiments/v5_screen/B1/$NAME --n-folds 1 --out exports/v5_b1_${NAME}.md 2>&1 | tail -25
  fi
}

# Phase 1: retry mamba (mamba-ssm 2.3.1 installed)
run_extra mamba configs/v5/screen/backbone_mamba.json
# Phase 2: alternate architectures user requested (longer TCN + GRU + iTransformer + larger-patch attention)
run_extra gru          configs/v5/screen/backbone_gru.json
run_extra itransformer configs/v5/screen/backbone_itransformer.json
run_extra conv_deep    configs/v5/screen/backbone_conv_deep.json
run_extra conv_deeper  configs/v5/screen/backbone_conv_deeper.json
run_extra attention_p20 configs/v5/screen/backbone_attention_p20.json
# Phase 3: stretch (longer input)
run_extra mamba_long      configs/v5/screen/backbone_mamba_long.json
run_extra attention_long  configs/v5/screen/backbone_attention_long.json
run_extra attention_wide  configs/v5/screen/backbone_attention_wide.json
# Phase 4: post-B.1 (winner ID + B.2 loss screen)
echo "[CONTINUE] launching post_b1 at $(date -u +%FT%TZ)"
bash scripts/v5_post_b1.sh
echo "[CONTINUE] all done at $(date -u +%FT%TZ)"
