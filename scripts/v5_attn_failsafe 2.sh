#!/usr/bin/env bash
# Failsafe: if main watchdog finished without running late_fusion_attn / cross_attn
# (because bash already read the script before they were appended), run them now.
set -u
cd "$(dirname "$0")/.."

# Wait for main watchdog to end
echo "[FAILSAFE] waiting for main watchdog to finish"
while pgrep -f 'v5_b1_continue.sh' > /dev/null; do sleep 30; done
echo "[FAILSAFE] main watchdog done at $(date -u +%FT%TZ)"

run_extra() {
  local NAME="$1"; local CFG="$2"
  local PRED="experiments/v5_screen/B1/$NAME/fold_0/test_preds.npz"
  if [ -f "$PRED" ] && [ $(stat -c%s "$PRED") -gt 1000 ]; then
    echo "[FAILSAFE] SKIP $NAME"; return 0
  fi
  rm -rf experiments/v5_screen/B1/$NAME
  echo "[FAILSAFE] running $NAME at $(date -u +%FT%TZ)"
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py --name "$NAME" --config "$CFG" --out-base experiments/v5_screen/B1 > logs/v5_b1_$NAME.log 2>&1
  local RC=$?
  echo "[FAILSAFE] $NAME rc=$RC"
  if [ $RC -eq 0 ]; then
    python scripts/v5_eval_comprehensive.py --exp-dir experiments/v5_screen/B1/$NAME --n-folds 1 --out exports/v5_b1_${NAME}.md 2>&1 | tail -25
  fi
}

run_extra late_fusion_attn configs/v5/screen/backbone_late_fusion_attn.json
run_extra cross_attn configs/v5/screen/backbone_cross_attn.json
run_extra itransformer_retry configs/v5/screen/backbone_itransformer.json

# Re-run post_b1 to include these new candidates
echo "[FAILSAFE] re-running post_b1 for updated B.1 winner"
bash scripts/v5_post_b1.sh
echo "[FAILSAFE] all done at $(date -u +%FT%TZ)"
