#!/bin/bash
# stage 03: 4h panel (prereg §1 row 3). pod_panel_ext.py patched only in the zload import path; its L172 self-check reads the read-only
# /workspace/data/wide_panel_4h_v1.npz (exists on pod2, sha f14bc33d…). The panel is written (L169) before the self-check (L172-194).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_panel_ext.py logs/patches/pod_panel_ext.py.diff src/pod_panel_ext.py src/zload.py /workspace/fund_aug.json.gz /workspace/data/wide_panel_4h_v1.npz
echo "funding dirs: $(ls /workspace/wide_multisrc/funding | wc -l)  funding zips: $(find /workspace/wide_multisrc/funding -name '*.zip' | wc -l)  404s: $(find /workspace/wide_multisrc/funding -name '*.404' | wc -l)"
run env CACHE_IN=$ROOT/data/dlnative_5m_wide829_f16_hist.npz PANEL_OUT=$ROOT/data/wide_panel_4h_hist_v2_rebuilt.npz $PY patched/pod_panel_ext.py
rc=$?
if grep -q "^PANEL_EXT_DONE" logs/03_panel.log; then :
elif grep -q "^PANEL_EXT_PARITY_FAIL" logs/03_panel.log && [ -s data/wide_panel_4h_hist_v2_rebuilt.npz ]; then echo "NOTE: built-in 7-column parity self-check FAILED (recorded as a finding; G1 classifies); continuing"
else exit 3; fi
run sha256sum data/wide_panel_4h_hist_v2_rebuilt.npz
