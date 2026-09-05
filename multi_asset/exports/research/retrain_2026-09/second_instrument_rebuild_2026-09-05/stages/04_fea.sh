#!/bin/bash
# stage 04: 82-column feature panel + meta (prereg §1 row 4). pod_fea_wide_hist.py patched only in the zload import path.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_fea_wide_hist.py logs/patches/pod_fea_wide_hist.py.diff src/pod_fea_wide_hist.py
run env CACHE_IN=$ROOT/data/dlnative_5m_wide829_f16_hist.npz PANEL_IN=$ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz FEA_OUT=$ROOT/data/wide_fea_hist_rebuilt.npy META_OUT=$ROOT/data/wide_fea_hist_meta_rebuilt.npz $PY patched/pod_fea_wide_hist.py
grep -q "^FEA_DONE" logs/04_fea.log || exit 3
run sha256sum data/wide_fea_hist_rebuilt.npy data/wide_fea_hist_meta_rebuilt.npz
sha256sum gates/compare_meta.py
run $PY gates/compare_meta.py
