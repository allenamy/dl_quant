#!/bin/bash
# stage 12 (lead instruction 09-05, funding-coverage plan): 450-scope reproduction panel via the FUND_SCOPE input patch; receipts vs the masked
# DIAG panel; G1 on it; stage-6 device + G2(a) on it; dev450 layout with F1 hist/pinned log arms; G2(b)(c) on the 450-scope F1 hist series.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_panel_ext.py logs/patches/pod_panel_ext.py.diff src/live_pins.json gates/compare_panels.py
run env CACHE_IN=$ROOT/data/dlnative_5m_wide829_f16_hist.npz PANEL_OUT=$ROOT/data/wide_panel_4h_hist_v2_rebuilt_fund450.npz FUND_SCOPE=$ROOT/src/live_pins.json $PY patched/pod_panel_ext.py
if grep -q "^PANEL_EXT_DONE" logs/12_fund450.log; then :; elif grep -q "^PANEL_EXT_PARITY_FAIL" logs/12_fund450.log && [ -s data/wide_panel_4h_hist_v2_rebuilt_fund450.npz ]; then echo "NOTE: built-in self-check FAILED (amihud tail cells); continuing"; else exit 3; fi
run sha256sum data/wide_panel_4h_hist_v2_rebuilt_fund450.npz
run $PY gates/compare_panels.py
run env G1_A=$ROOT/data/wide_panel_4h_hist_v2_rebuilt_fund450.npz G1_OUT=G1_fund450.json G1_SKIP_B=1 $PY gates/gate_G1.py
run env TAG=histv2f450 META_IN=$ROOT/data/wide_fea_hist_meta_rebuilt.npz PANEL_IN=$ROOT/data/wide_panel_4h_hist_v2_rebuilt_fund450.npz KING_IN=$ROOT/data/slow_pred_hist_oos_rebuilt.npy $PY patched/pod_stop_arms_v3.py
grep -q "^STOP_ARMS_DONE" logs/12_fund450.log || exit 3
run env G2A_TAG=histv2f450 G2A_OUT=G2a_fund450.json $PY gates/gate_G2a.py
d=$ROOT/dev450; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
ln -sfn $ROOT/data/nets_histv2f450_0_0_0.npy $d/pod_backup_2026-08-21/nets_histv2_0_0_0.npy; ln -sfn $ROOT/data/nets_histv2f450_-30_2_42.npy $d/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
ln -sfn $ROOT/data/slow_pred_hist_oos_rebuilt.npy $d/pod_backup_2026-08-21/slow_pred_hist_oos.npy; ln -sfn $ROOT/data/wide_panel_4h_hist_v2_rebuilt_fund450.npz $d/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz; ln -sfn $ROOT/data/wide_fea_hist_meta_rebuilt.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22; ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
for spec in "F1_hist_log|$ROOT/data/slow_pred_hist_oos_rebuilt.npy" "F1_pinned_log|$ROOT/data/slow_pred_pinned_on_hist.npy"; do tag=${spec%%|*}; king=${spec#*|}
  echo "CMD[$STAGE] (cwd=$d) $(date -u +%FT%TZ): env LOOK=900 WRULE=msharpe SLOW_NPY=$king LEGS=111 PHI=0 FSEED=42 CAL=log OUT_TAG=$tag $PY ../w10_universe_recheck.py" >> $CMDLOG
  (cd $d && env LOOK=900 WRULE=msharpe SLOW_NPY=$king LEGS=111 PHI=0 FSEED=42 CAL=log OUT_TAG=$tag $PY ../w10_universe_recheck.py > $d/logs/$tag.log 2>&1) &
done; wait
for tag in F1_hist_log F1_pinned_log; do echo "== $tag"; grep -E "^(CONFIG|RECEIPT d30|DONE|Traceback|AssertionError)" $d/logs/$tag.log | cut -c1-500; grep -q "^DONE" $d/logs/$tag.log || exit 3; done
run env G2_DIR=dev450 G2_TAG=F1_hist_log G2_NETS_TAG=histv2f450 G2_OUT=G2bc_fund450.json $PY gates/gate_G2bc.py
