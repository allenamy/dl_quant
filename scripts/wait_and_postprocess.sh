#!/usr/bin/env bash
# Wait for V4 training to complete (4 fold_*/test_results.json on pod), then:
#   1. Sync results dir from pod to local
#   2. Run aggregate_folds.py
#   3. Run Ridge + XGBoost baselines on V4 NPZ (pod-side, CPU)
#   4. Write experiments/v4_full/V4_RESULTS_AUTO.md
#   5. Mark done — do NOT auto-kick ablations (human decides)
set -euo pipefail

HOST="213.192.2.108"
PORT="40087"
KEY="$HOME/.ssh/runpod_ed25519"
EXP_DIR="experiments/v4_full"
LOG="logs/postprocess.log"

mkdir -p "$(dirname "$LOG")"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# --- 1. Wait for 4 test_results.json on pod ---
say "Waiting for 4 fold test_results.json on pod …"
while true; do
  N=$(ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$HOST" \
        "ls /workspace/quant_research/$EXP_DIR/fold_*/test_results.json 2>/dev/null | wc -l" 2>/dev/null || echo 0)
  PROC=$(ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$HOST" \
        "ps -p 17303 -o pid= 2>/dev/null | tr -d ' '" 2>/dev/null || true)
  say "folds_done=$N train_pid_alive=${PROC:-gone}"
  if [ "$N" -ge 4 ]; then
    say "All 4 folds complete. Proceeding."
    break
  fi
  if [ -z "${PROC:-}" ] && [ "$N" -lt 4 ]; then
    say "Training process exited without producing 4 folds. Investigate — aborting auto-postprocess."
    exit 1
  fi
  sleep 300
done

# --- 2. Sync results dir from pod to local ---
say "Syncing $EXP_DIR from pod …"
rsync -avz --include='fold_*/' --include='*.json' --include='*.npz' --include='*.log' \
  --exclude='*' \
  -e "ssh -i $KEY -p $PORT -o StrictHostKeyChecking=no" \
  "root@$HOST:/workspace/quant_research/$EXP_DIR/" "./$EXP_DIR/" 2>&1 | tail -5 | tee -a "$LOG"

# --- 3. Aggregate folds ---
say "Running aggregate_folds.py …"
python scripts/aggregate_folds.py \
  --exp-dir "$EXP_DIR" \
  --out "$EXP_DIR/SUMMARY.json" \
  --baseline-corr 0.099 \
  2>&1 | tee -a "$LOG"

# --- 4. Run baselines on V4 NPZ (pod, CPU) ---
say "Kicking off Ridge+XGB baselines on V4 NPZ (pod, CPU — GPU free for ablation if desired) …"
ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no root@"$HOST" \
  "cd /workspace/quant_research && \
   nohup python3 -m src.baselines.evaluate_baselines \
     --npz-dir data/npz_v4 \
     --output-dir experiments/baselines_v4 \
     --device cpu \
     --train-days 700 --val-days 30 --test-days 90 --fold-stride 60 \
     --horizon-key y_180 --mask-key y_mask_180 \
     > logs/baselines_v4.log 2>&1 & echo baselines_pid=\$!" 2>&1 | tee -a "$LOG"

# --- 5. Snapshot a preliminary V4_RESULTS_AUTO.md ---
say "Writing V4_RESULTS_AUTO.md (preliminary — baselines still running) …"
python -c "
import json, pathlib
summary = json.loads(pathlib.Path('$EXP_DIR/SUMMARY.json').read_text())
out = [
  '# V4 Results (auto-generated)',
  f'_Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")_',
  '',
  '## Pooled OOS IC',
  '',
  f'- **Pooled Pearson corr:** {summary.get(\"pooled_corr\", \"N/A\")}',
  f'- **Pass bar (spec):** 0.12 (vs Ridge 0.099)',
  f'- **Pass (primary):** {\"YES\" if summary.get(\"pooled_corr\", 0) >= 0.12 else \"NO\"}',
  '',
  '## Per-fold',
  '',
]
for f in summary.get('folds', []):
    out.append(f'- {f.get(\"fold_dir\", \"?\")}: test_corr={f.get(\"test_corr\", \"?\"):.4f} (val_corr={f.get(\"val_corr\", \"?\"):.4f})')
out.append('')
out.append('## Next step')
out.append('')
out.append('- Baselines (Ridge/XGB on V4 features) still running on pod; see logs/baselines_v4.log')
out.append('- If V4 passes primary AND the fair-baseline comparison holds, greenlight the 8-ablation sweep.')
pathlib.Path('docs/V4_RESULTS_AUTO.md').write_text('\n'.join(out))
print('Wrote docs/V4_RESULTS_AUTO.md')
" 2>&1 | tee -a "$LOG"

say "POSTPROCESS DONE"
