#!/bin/bash
# stage 07: DL targets (y4s = Π(1+r5)-1 over [E+1,E+48], y4old = Σ over [E,E+47]) on the hist cache + rebuilt panel (prereg §1 row 7). Verbatim script, env paths.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum src/pod_dlw_targets_ext.py
run env DLWT_CACHE=$ROOT/data/dlnative_5m_wide829_f16_hist.npz DLWT_PANEL=$ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz DLWT_OUT=$ROOT/data/dlw_hist $PY src/pod_dlw_targets_ext.py
grep -q "TARGETS_DONE" logs/07_targets.log || exit 3
run sha256sum data/dlw_hist/data/dlw_targets.npz data/dlw_hist/results/dlw_targets_report.json
