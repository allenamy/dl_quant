#!/bin/bash
# stage 06: 08-21 authoritative book device pod_stop_arms_v3.py, TAG=histv2, inputs = stages 3/4/5 (prereg §1 row 6). Output paths patched only.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_stop_arms_v3.py logs/patches/pod_stop_arms_v3.py.diff src/pod_stop_arms_v3.py
run env TAG=histv2 META_IN=$ROOT/data/wide_fea_hist_meta_rebuilt.npz PANEL_IN=$ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz KING_IN=$ROOT/data/slow_pred_hist_oos_rebuilt.npy $PY patched/pod_stop_arms_v3.py
grep -q "^STOP_ARMS_DONE" logs/06_stop_arms.log || exit 3
run sha256sum data/nets_histv2_0_0_0.npy data/nets_histv2_-30_2_42.npy data/nets_histv2_-25_2_42.npy data/nets_histv2_-25_1_42.npy data/stop_arms_pod_v3_histv2.json
