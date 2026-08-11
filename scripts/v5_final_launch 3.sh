#!/usr/bin/env bash
# Phase C: V5 final 3-fold training using winner config from B.1+B.2.
#
# Generates v5_final.json from B.1 backbone winner and B.2 loss winner, then runs
# 3-fold (or single-train, depending on B.3 outcome).

set -u
cd "$(dirname "$0")/.."

WINNER_BACKBONE="${WINNER_BACKBONE:-attention}"  # override via env
WINNER_LOSS="${WINNER_LOSS:-nll}"                # override via env
N_FOLDS="${N_FOLDS:-3}"
SEED="${SEED:-42}"
OUT_BASE="experiments/v5_final"
mkdir -p "$OUT_BASE" logs

FINAL_CFG=configs/v5/v5_final.json

# Compose final config: backbone winner architecture + loss winner flags
python << PYEOF
import json
import shutil
from pathlib import Path
src = Path("configs/v5/screen/backbone_${WINNER_BACKBONE}.json")
dst = Path("$FINAL_CFG")
shutil.copy(src, dst)
cfg = json.load(open(dst))
loss_winner = "${WINNER_LOSS}"
cfg.setdefault("loss", {})
if loss_winner == "nll":
    cfg["loss"].update({
        "w_gaussian_nll": 1.0,
        "nll_log_sigma_min": -7.0,
        "nll_log_sigma_max": 2.0,
        "w_huber_y": 0.0,
        "w_dir_margin": 0.0,
        "w_mag_huber": 0.0,
        "w_joint_mse": 0.0,
        "head_hidden": 0,
    })
    cfg.setdefault("training", {}).pop("dul_config", None)
elif loss_winner == "huber":
    cfg["loss"].update({
        "w_huber_y": 1.0,
        "huber_y_delta": 1.0,
        "w_gaussian_nll": 0.0,
        "w_dir_margin": 0.0,
        "w_mag_huber": 0.0,
        "w_joint_mse": 0.0,
        "head_hidden": 0,
    })
    cfg.setdefault("training", {}).pop("dul_config", None)
elif loss_winner == "quantile":
    # V4 quantile path — leave loss empty, dul_config retained
    pass
else:
    raise ValueError(f"Unknown WINNER_LOSS: {loss_winner}")
json.dump(cfg, open(dst, "w"), indent=2)
print(f"v5_final config: backbone=${WINNER_BACKBONE}, loss=${WINNER_LOSS} → {dst}")
PYEOF

# Override output_dir for final run
python -c "
import json
c = json.load(open('$FINAL_CFG'))
c['output_dir'] = '$OUT_BASE'
json.dump(c, open('$FINAL_CFG', 'w'), indent=2)
"

LOG="logs/v5_final.log"
echo "[FINAL] === Starting V5 final $N_FOLDS-fold seed=$SEED at $(date -u +%FT%TZ) ==="
PYTHONUNBUFFERED=1 python -u run_pipeline_v3.py \
    --config "$FINAL_CFG" \
    --skip-features \
    --seed "$SEED" \
    --start-fold 0 \
    --max-folds "$N_FOLDS" \
    > "$LOG" 2>&1
RC=$?
echo "[FINAL] === Done rc=$RC at $(date -u +%FT%TZ) ==="

if [ $RC -eq 0 ]; then
    echo "[FINAL] V5 final completed — running comprehensive eval"
    python scripts/v5_eval_comprehensive.py \
        --exp-dir "$OUT_BASE" \
        --n-folds "$N_FOLDS" \
        --out "exports/v5_final_eval.md"
fi

exit $RC
