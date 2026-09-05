#!/bin/bash
# stage 05: king walk-forward OOS folds 2022..2026, train = years < YV, no embargo (08-21 as-is; prereg §1 row 5). Output path patched only.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_slow_hist_folds.py logs/patches/pod_slow_hist_folds.py.diff src/pod_slow_hist_folds.py
$PY -c "import lightgbm, numpy, scipy; print('lightgbm', lightgbm.__version__, 'numpy', numpy.__version__, 'scipy', scipy.__version__)"; nproc
run env FEA_IN=$ROOT/data/wide_fea_hist_rebuilt.npy META_IN=$ROOT/data/wide_fea_hist_meta_rebuilt.npz $PY patched/pod_slow_hist_folds.py
grep -q "^FOLDS_DONE" logs/05_king.log || exit 3
run sha256sum data/slow_pred_hist_oos_rebuilt.npy data/slow_hist_folds_rebuilt.json
cat data/slow_hist_folds_rebuilt.json
sha256sum gates/compare_king.py
run $PY gates/compare_king.py
