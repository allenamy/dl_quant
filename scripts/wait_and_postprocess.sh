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
TRAIN_PID="${TRAIN_PID:-19033}"  # override via env var

mkdir -p "$(dirname "$LOG")"

say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# --- 1. Wait for 4 test_results.json on pod ---
say "Waiting for 4 fold test_results.json on pod …"
while true; do
  N=$(ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$HOST" \
        "ls /workspace/quant_research/$EXP_DIR/fold_*/test_results.json 2>/dev/null | wc -l" 2>/dev/null || echo 0)
  PROC=$(ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$HOST" \
        "ps -p $TRAIN_PID -o pid= 2>/dev/null | tr -d ' '" 2>/dev/null || true)
  say "folds_done=$N train_pid_alive=${PROC:-gone}"
  if [ "$N" -ge 4 ]; then
    say "All 4 folds complete. Proceeding."
    break
  fi
  if [ -z "${PROC:-}" ] && [ "$N" -lt 4 ]; then
    say "Training PID gone with only $N folds — still aggregating the partial result so the morning has actionable data."
    break
  fi
  sleep 300
done
PARTIAL=0
if [ "$N" -lt 4 ]; then
  PARTIAL=1
  say "WARNING: partial run (n_folds=$N). Aggregate will still be written but flagged as partial."
fi

# --- 2. Sync results dir from pod to local (skip if no folds) ---
if [ "$N" -eq 0 ]; then
  say "Zero folds produced — nothing to aggregate. Exiting."
  exit 0
fi
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
pooled = summary.get('pooled', {})
pooled_corr = pooled.get('correlation')
pooled_rank = pooled.get('rank_correlation')
pooled_r2 = pooled.get('r2')
delta = pooled.get('delta_vs_baseline')
cross = summary.get('cross_fold', {})
bt = summary.get('pooled_backtest', {})
out = []
out.append('# V4 Results (auto-generated)')
out.append('')
out.append(f'_Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")_')
out.append('')
out.append('## Pooled OOS IC (h=180, primary)')
out.append('')
out.append(f'- Pooled Pearson correlation: **{pooled_corr:.4f}**' if pooled_corr is not None else '- Pooled Pearson: N/A')
if pooled_rank is not None:
    out.append(f'- Pooled rank correlation: {pooled_rank:.4f}')
if delta is not None:
    out.append(f'- Delta vs Ridge 0.099 baseline: {delta:+.4f}')
out.append(f'- Spec primary bar: 0.12')
pass_p = pooled_corr is not None and pooled_corr >= 0.12
out.append(f'- **PRIMARY PASS: {\"YES\" if pass_p else \"NO\"}**')
out.append('')
out.append('## Per-fold')
out.append('')
out.append('| Fold | val_corr | test_corr | Δ vs Ridge | Sharpe | NetPnL(bps) |')
out.append('|------|---------:|----------:|-----------:|-------:|------------:|')
for r in summary.get('per_fold', []):
    vc = r.get('val_corr'); tc = r.get('test_corr')
    d = r.get('delta_vs_baseline')
    sh = r.get('test_sharpe_annual')
    pn = r.get('test_net_pnl_bps')
    out.append(
        f'| {r.get(\"fold\",\"?\")} | '
        f'{vc:+.4f} | {tc:+.4f} | '
        + (f'{d:+.4f} | ' if d is not None else 'N/A | ')
        + (f'{sh:+.2f} | ' if sh is not None else 'N/A | ')
        + (f'{pn:+.2f} |' if pn is not None else 'N/A |')
    )
out.append('')
out.append('## Cross-fold stability')
out.append('')
out.append(f'- mean_corr={cross.get(\"mean_corr\", 0):.4f}, std_corr={cross.get(\"std_corr\", 0):.4f}, IC-IR={cross.get(\"ic_ir\", 0):.4f}')
out.append(f'- t_stat={cross.get(\"t_stat\", 0):.2f}, p_value={cross.get(\"p_value\", 0):.4f}, significant={cross.get(\"significant_at_p05\")}')
out.append('')
out.append('## Backtest (pooled)')
out.append('')
out.append(f'- Net PnL (bps): {bt.get(\"total_net_pnl_bps\", 0):.1f}')
out.append(f'- Gross PnL (bps): {bt.get(\"total_gross_pnl_bps\", 0):.1f}')
out.append(f'- Costs (bps): {bt.get(\"total_cost_bps\", 0):.1f}')
out.append(f'- Weighted avg Sharpe: {bt.get(\"weighted_avg_sharpe\", 0):.3f}')
out.append(f'- n_trades={bt.get(\"n_trades\", 0)}, n_periods={bt.get(\"n_periods\", 0)}')
out.append('')
out.append('## Next step')
out.append('')
out.append('- Ridge + XGBoost baselines on V4 features (h=180) running on pod — see logs/baselines_v4.log.')
out.append('- If PRIMARY PASS = YES AND baseline comparison holds, greenlight the 8-ablation sweep.')
out.append('- If NO, document the negative result honestly and revert production signal to Ridge.')
pathlib.Path('docs/V4_RESULTS_AUTO.md').write_text('\n'.join(out) + '\n')
print('Wrote docs/V4_RESULTS_AUTO.md')
print('PRIMARY PASS:', pass_p)
" 2>&1 | tee -a "$LOG"

say "POSTPROCESS DONE"
