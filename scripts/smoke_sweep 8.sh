#!/usr/bin/env bash
# Fast-smoke sweep over V4 variants.
# For each config in $1 (default configs/v4_smoke)/*.json run fold 0 only,
# collect test corr into $2 (default logs/smoke_sweep_summary.tsv).
set -euo pipefail

cd /workspace/quant_research

CFG_DIR="${1:-configs/v4_smoke}"
OUT="${2:-logs/smoke_sweep_summary.tsv}"
mkdir -p logs
printf "variant\twall_min\tbest_epoch\tval_corr\ttest_pearson\ttest_spearman\n" > "$OUT"

for cfg in "$CFG_DIR"/*.json; do
    name=$(basename "$cfg" .json)
    log="logs/smoke_${name}.log"
    exp_dir="experiments/v4_smoke_${name}"

    echo "===== [$(date +%T)] Launching $name =====" | tee -a logs/smoke_driver.log
    START=$(date +%s)

    # Clean prior artifacts so cache is fresh per variant
    rm -rf "$exp_dir"

    timeout 30m python3 -u run_pipeline_v3.py \
        --config "$cfg" --skip-features --model V3 --max-folds 1 \
        > "$log" 2>&1 || echo "  [WARN] $name timed out or errored" | tee -a logs/smoke_driver.log

    END=$(date +%s)
    WALL=$(( (END - START) / 60 ))

    # Parse best val_corr from log
    best_line=$(grep -E "Fold 0 best:" "$log" | head -1 || true)
    best_epoch=$(echo "$best_line" | grep -oE "best_epoch': [0-9]+" | awk -F': ' '{print $2}' || echo "")
    val_corr=$(echo "$best_line" | grep -oE "val_corr': np\.float64\([0-9.e+-]+\)" | grep -oE "[0-9.e+-]+" | head -1 || echo "")

    # Compute test corr directly
    if [ -f "$exp_dir/fold_0/test_preds.npz" ]; then
        test_metrics=$(python3 -c "
import numpy as np
d = np.load('$exp_dir/fold_0/test_preds.npz')
p = d['predictions']; t = d['targets']; m = d['mask'].astype(bool)
q50 = p[:,1] if p.ndim==2 and p.shape[-1]>=3 else p.ravel()
tgt = t.ravel()
mk = m.ravel()
if mk.any():
    from scipy.stats import rankdata
    pc = float(np.corrcoef(q50[mk], tgt[mk])[0,1])
    rc = float(np.corrcoef(rankdata(q50[mk]), rankdata(tgt[mk]))[0,1])
    print(f'{pc:.4f}\t{rc:.4f}')
else:
    print('nan\tnan')
" 2>/dev/null || echo "err	err")
    else
        test_metrics="noeval	noeval"
    fi

    printf "%s\t%d\t%s\t%s\t%s\n" "$name" "$WALL" "${best_epoch:-}" "${val_corr:-}" "$test_metrics" >> "$OUT"
    echo "  [done] $name wall=${WALL}min val=${val_corr:-N/A} test=${test_metrics}" | tee -a logs/smoke_driver.log
done

echo "===== Sweep complete =====" | tee -a logs/smoke_driver.log
cat "$OUT"
