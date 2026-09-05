#!/bin/bash
# stage 02: 5m cache from the re-pulled zips (prereg §1 row 2). pod_build_wide_ext.py patched only in paths (diff in logs/patches/).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/pod_build_wide_ext.py logs/patches/pod_build_wide_ext.py.diff src/pod_build_wide_ext.py
rm -f data/wide_ext.lock
run env EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=$ROOT/data/dlnative_5m_wide829_f16_hist.npz $PY patched/pod_build_wide_ext.py
grep -q "^EXT_CACHE_DONE" logs/02_cache.log || exit 3
run sha256sum data/dlnative_5m_wide829_f16_hist.npz
ls -la data/dlnative_5m_wide829_f16_hist.npz
