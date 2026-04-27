#!/usr/bin/env bash
# y_1800 12-hour autonomous research push — runs ON THE POD.
#
# Goal: y_1800 pooled clean Pearson ≥ 0.025 AND Spearman ≥ 0.045
#       (both must improve over phase3c EMA P=0.021 S=0.037).
#
# Resource model: RTX 4090, ~3.5h per 3-fold, ~1h per fold-0 screen.
# Total budget: 12h.
#
# Sequence:
#   STAGE 0  build LC overlay 991 days (multi-proc CPU on pod)
#   STAGE 1  Phase 5 seed=7 phase3c 3-fold — verify winner
#   STAGE 2  A3 iTransformer + A4 MoE + F1 LC fold-0 screens
#   STAGE 3  Best screen → 3-fold extension (only if any passed gate)
#   STAGE 4  Aggregate + emit summary
#
# Pass gate (any candidate moving to 3-fold extension):
#   fold-0 EMA (P+S)/2 ≥ phase3c-fold0 EMA (P+S)/2 + 0.005
#
# Final pass criterion (the 12h goal):
#   3-fold pooled EMA P ≥ 0.025 AND S ≥ 0.045
#
# Hard wallclock caps below; trainer's own patience handles graceful early stop.
#
# Usage on pod:
#   cd /workspace/quant_research
#   nohup bash scripts/y1800_autonomous_12h_push.sh > logs/y1800_12h_push.log 2>&1 &
#   echo $! > /tmp/y1800_orch.pid
#
# Live monitor from laptop:
#   ssh ... "tail -f /workspace/quant_research/logs/y1800_12h_push.log"
#   ssh ... "cat /workspace/quant_research/experiments/y1800_calib/PROGRESS_12H.txt"

set -uo pipefail   # NOT -e: keep going on individual experiment failures

REPO=/workspace/quant_research
cd "$REPO" || { echo "FATAL: cannot cd to $REPO"; exit 1; }

PYTHON=${PYTHON:-python}
PROG=experiments/y1800_calib/PROGRESS_12H.txt
mkdir -p "$(dirname $PROG)" logs

CAP_OVERLAY=$((45*60))         # 45 min
CAP_3FOLD_FULL=$((4*3600))     # 4 h
CAP_FOLD0_SCREEN=$((90*60))    # 90 min

ts() { date +"%Y-%m-%dT%H:%M:%S"; }
log_p() { echo "[$(ts)] $*" >> "$PROG"; echo "[$(ts)] $*"; }
log_p "=== y_1800 12h autonomous push START ==="

# Run a command with a wallclock cap (kills child group on overrun).
run_capped() {
  local cap=$1; shift
  local label=$1; shift
  log_p "RUN  $label (cap=${cap}s)"
  ( "$@" ) &
  local pid=$!
  local elapsed=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 30
    elapsed=$((elapsed + 30))
    if [[ $elapsed -ge $cap ]]; then
      log_p "KILL $label — exceeded ${cap}s wallclock cap"
      pkill -P "$pid" 2>/dev/null || true
      kill -9 "$pid" 2>/dev/null || true
      return 124
    fi
  done
  wait "$pid"
  local rc=$?
  log_p "DONE $label rc=$rc elapsed=${elapsed}s"
  return $rc
}

# Pool metrics — outputs ONLY the metric line on stdout.
pool_metrics() {
  local exp_root=$1
  local fold_glob=$2
  local mode=$3   # "ema" or "best"
  $PYTHON - "$exp_root" "$fold_glob" "$mode" <<'PY' 2>/dev/null
import sys, numpy as np
from pathlib import Path
from scipy.stats import pearsonr, spearmanr
exp_root, fold_glob, mode = sys.argv[1], sys.argv[2], sys.argv[3]
folds = sorted(Path(exp_root).glob(fold_glob))
preds, tgts = [], []
for f in folds:
    p = f / ("ema_test_preds.npz" if mode == "ema" else "test_preds.npz")
    if not p.exists():
        continue
    d = np.load(p, allow_pickle=True)
    pr = np.asarray(d["predictions"]); tg = np.asarray(d["targets"]).ravel()
    mk = np.asarray(d.get("mask", np.ones_like(tg))).astype(bool).ravel()
    pt = pr[:,1] if (pr.ndim == 2 and pr.shape[-1] >= 3) else pr.ravel()
    k = 3
    idx = np.arange(0, len(tg), k)
    pt = pt[idx][mk[idx]]; tg = tg[idx][mk[idx]]
    if len(pt) < 10 or pt.std() == 0 or tg.std() == 0:
        continue
    preds.append(pt); tgts.append(tg)
if not preds:
    print("NO_DATA")
else:
    pa = np.concatenate(preds); ta = np.concatenate(tgts)
    pp,_ = pearsonr(pa, ta); ps,_ = spearmanr(pa, ta)
    sr = pa.std() / ta.std()
    print(f"P={pp:+.4f} S={ps:+.4f} sigma_ratio={sr:.3f} N={len(pa)}")
PY
}

run_pipeline() {
  local cfg=$1; shift
  local extra="$*"
  $PYTHON run_pipeline_v3.py --config "$cfg" --skip-features --model V3 $extra
}

# STAGE 0: LC overlay --------------------------------------------------------
log_p "STAGE 0: build LC overlay (data/npz_v4_smooth_y1800)"
if [[ -d data/npz_v4_smooth_y1800 ]] && \
   [[ $(ls data/npz_v4_smooth_y1800 2>/dev/null | wc -l) -ge 900 ]]; then
  log_p "  overlay already built ($(ls data/npz_v4_smooth_y1800 | wc -l) days), skip"
else
  run_capped $CAP_OVERLAY "lc_overlay_build" \
    $PYTHON scripts/build_long_context_overlay_y1800.py \
      --src-npz-dir data/npz_v4_y1800 \
      --mid-dir data/midprice_per_day \
      --out-dir data/npz_v4_smooth_y1800 \
      --workers 8
fi
log_p "STAGE 0 overlay days = $(ls data/npz_v4_smooth_y1800 2>/dev/null | wc -l)"

# STAGE 1: Phase 5 seed=7 phase3c 3-fold -------------------------------------
log_p "STAGE 1: Phase 5 seed=7 phase3c 3-fold"
PHASE5_OUT=experiments/y1800_calib/phase5_seed7_phase3c
PHASE5_CFG=configs/y1800_calib/phase5_seed7_phase3c.json
$PYTHON - "$PHASE5_OUT" "$PHASE5_CFG" <<'PY'
import json, pathlib, sys
out_dir, out_cfg = sys.argv[1], sys.argv[2]
src = json.loads(pathlib.Path("configs/y1800_calib/phase3c_val90_embargo30.json").read_text())
src["output_dir"] = out_dir
src["_comment"] = "Phase 5 multi-seed verification (seed=7) of phase3c. Auto-generated by y1800_autonomous_12h_push.sh"
pathlib.Path(out_cfg).write_text(json.dumps(src, indent=2))
PY
run_capped $CAP_3FOLD_FULL "phase5_seed7_3fold" \
  run_pipeline "$PHASE5_CFG" --seed 7

PHASE5_EMA=$(pool_metrics "$PHASE5_OUT" "fold_*" "ema")
PHASE5_BEST=$(pool_metrics "$PHASE5_OUT" "fold_*" "best")
PHASE3C_EMA=$(pool_metrics "experiments/y1800_calib/phase3c_val90_embargo30" "fold_*" "ema")
PHASE3C_F0=$(pool_metrics "experiments/y1800_calib/phase3c_val90_embargo30" "fold_0" "ema")
log_p "STAGE 1 RESULTS:"
log_p "  phase3c (seed=42) EMA pooled : $PHASE3C_EMA"
log_p "  phase5  (seed=7)  EMA pooled : $PHASE5_EMA"
log_p "  phase5  (seed=7)  best pooled: $PHASE5_BEST"
log_p "  phase3c fold0 EMA (baseline for STAGE 2 gate): $PHASE3C_F0"

# Safety abort: if STAGE 1 produced no metrics, the pipeline is broken
# (config / flags / install issue). Bailing here saves the next ~7h of
# cascading failed stages.
if [[ "$PHASE5_EMA" == "NO_DATA" ]] || [[ -z "$PHASE5_EMA" ]]; then
  log_p "FATAL: STAGE 1 produced NO_DATA. Aborting before cascade. Inspect logs/y1800_12h_push.log."
  exit 1
fi

# STAGE 2: fold-0 screens ----------------------------------------------------
log_p "STAGE 2: fold-0 screens A3 iTransformer / A4 MoE / F1 LC"

run_screen() {
  # $1 cfg path  $2 label
  local cfg=$1; local label=$2
  run_capped $CAP_FOLD0_SCREEN "$label" \
    run_pipeline "$cfg" --max-folds 1
  local exp_root=$($PYTHON -c "import json; print(json.load(open('$cfg'))['output_dir'])")
  pool_metrics "$exp_root" "fold_0" "ema"
}

A3_RES=$(run_screen configs/y1800_calib/phase_A3_itransformer_3c.json "A3_iTransformer")
log_p "  A3 iTransformer fold0 EMA: $A3_RES"
A4_RES=$(run_screen configs/y1800_calib/phase_A4_moe_3c.json "A4_MoE")
log_p "  A4 MoE          fold0 EMA: $A4_RES"
F1_RES=$(run_screen configs/y1800_calib/phase_F1_lc_3c.json "F1_LongContext")
log_p "  F1 LC           fold0 EMA: $F1_RES"

# STAGE 3: pick winner + 3-fold extend ---------------------------------------
log_p "STAGE 3: select winner from screens"
WINNER_CFG=$($PYTHON - "$PHASE3C_F0" "$A3_RES" "$A4_RES" "$F1_RES" <<'PY'
import re, sys
def parse(s):
    if not s or "NO_DATA" in s: return None
    m = re.match(r"P=([+-][\d.]+) S=([+-][\d.]+)", s)
    return (float(m.group(1)), float(m.group(2))) if m else None
base = parse(sys.argv[1])
cands = [
    ("configs/y1800_calib/phase_A3_itransformer_3c.json", parse(sys.argv[2])),
    ("configs/y1800_calib/phase_A4_moe_3c.json",          parse(sys.argv[3])),
    ("configs/y1800_calib/phase_F1_lc_3c.json",           parse(sys.argv[4])),
]
winners = []
if base is not None:
    base_avg = (base[0] + base[1]) / 2
    for cfg, ps in cands:
        if ps is None: continue
        avg = (ps[0] + ps[1]) / 2
        if avg >= base_avg + 0.005:
            winners.append((avg - base_avg, cfg))
winners.sort(reverse=True)
print(winners[0][1] if winners else "NONE")
PY
)
log_p "  WINNER selected: $WINNER_CFG"

if [[ "$WINNER_CFG" != "NONE" ]] && [[ -f "$WINNER_CFG" ]]; then
  run_capped $CAP_3FOLD_FULL "winner_3fold" \
    run_pipeline "$WINNER_CFG"
  WIN_OUT=$($PYTHON -c "import json; print(json.load(open('$WINNER_CFG'))['output_dir'])")
  WIN_EMA=$(pool_metrics "$WIN_OUT" "fold_*" "ema")
  WIN_BEST=$(pool_metrics "$WIN_OUT" "fold_*" "best")
  log_p "STAGE 3 WINNER 3-fold EMA pooled : $WIN_EMA"
  log_p "STAGE 3 WINNER 3-fold best pooled: $WIN_BEST"
else
  log_p "STAGE 3: no screen passed +0.005 gate; skip 3-fold extension"
  WIN_EMA="(skipped)"
  WIN_BEST="(skipped)"
fi

# STAGE 4: summary ----------------------------------------------------------
log_p "STAGE 4: write summary"
SUMMARY=experiments/y1800_calib/PUSH_12H_SUMMARY.md
{
  echo "# y_1800 12h autonomous push — summary"
  echo
  echo "**Finished:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## Results"
  echo "| Stage | Result |"
  echo "|---|---|"
  echo "| phase3c (seed=42, frozen) EMA pooled | $PHASE3C_EMA |"
  echo "| phase5 (seed=7) EMA pooled            | $PHASE5_EMA |"
  echo "| phase5 (seed=7) best pooled           | $PHASE5_BEST |"
  echo "| A3 iTransformer fold0 EMA             | $A3_RES |"
  echo "| A4 MoE fold0 EMA                      | $A4_RES |"
  echo "| F1 LC fold0 EMA                       | $F1_RES |"
  echo "| Winner cfg                            | $WINNER_CFG |"
  echo "| Winner 3-fold EMA pooled              | $WIN_EMA |"
  echo "| Winner 3-fold best pooled             | $WIN_BEST |"
  echo
  echo "Goal was P ≥ 0.025 AND S ≥ 0.045 on the winner 3-fold pooled EMA."
  echo "See logs/y1800_12h_push.log + experiments/y1800_calib/PROGRESS_12H.txt for the timeline."
} > "$SUMMARY"
log_p "Wrote $SUMMARY"
log_p "=== y_1800 12h autonomous push DONE ==="
