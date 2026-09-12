#!/bin/bash
# r20 STEP 3 (positive control on REAL data, pod2) — the genuine A1 bundle (/workspace/shadow_bundle_v4) + the genuine A1 judged books through
# v4e_gate_export_v2.py, against an ISOLATED chain dir carrying the PROPOSED2 contract. Then: require mode on the receipt; a real-data
# negative on a COPY of the bundle (one prediction cell changed; the genuine bundle is never written); a v2 signal receipt for XIBLAG50 and
# the v2 gate on XIBLAG50 (informational: XIBLAG50 is not a registered arm).
# Frozen files untouched: /workspace/uplift_2026-09-11/infra2/v4chain/*, /workspace/shadow_bundle_v4/*, every book under health_check.
# Copy this script verbatim to pod2 and run:  bash run_pod2_positive.sh  (logs to $R20/receipts/pod2_run.log)
set -u
R20=/workspace/uplift_2026-09-11/r20_gate_closure
PY=/workspace/venv/bin/python
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
mkdir -p $R20/receipts $R20/scratch
LOG=$R20/receipts/pod2_run.log; exec > >(tee -a $LOG) 2>&1
echo "=== r20 pod2 positive control $(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg)"
echo "--- shas of the device files actually used"
sha256sum $R20/v4e_gate_export_v2.py $R20/gate_signal_parity_v2.py $R20/v4chain_PROPOSED2/v4_gate_common.py $R20/v4chain_PROPOSED2/ELIGIBILITY_CONTRACT.json \
          /workspace/uplift_2026-09-11/infra2/v4chain/ELIGIBILITY_CONTRACT.json /workspace/uplift_2026-09-11/infra2/v4chain/v4_gate_common.py
$PY -c "import sys,numpy,scipy;print('python',sys.version.split()[0],'numpy',numpy.__version__,'scipy',scipy.__version__)"

COMMON="BUNDLE_FEA=/workspace/data/wide_fea_v4.npy BUNDLE_META=/workspace/data/wide_fea_v4_meta.npz BUNDLE_BASE=/workspace/slow_scorer_v4base.json \
EXPORT_PANEL=/workspace/data/wide_panel_4h_v3splice.npz BUNDLE_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz FUND_AUG=/workspace/fund_aug.json.gz \
LIVE_PINS=/workspace/live_pins.json V4CHAIN_DIR=$R20/v4chain_PROPOSED2"

echo; echo "=== [1] GATE v2 on genuine A1 (JUDGE_HC=/workspace/review_scratch/health_check, bundle=/workspace/shadow_bundle_v4)"
t0=$(date +%s)
env $COMMON EXPORT_ARM=A1 BUNDLE_OUT=/workspace/shadow_bundle_v4 JUDGE_HC=/workspace/review_scratch/health_check \
    SIGNAL_RECEIPT=/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json EXPORT_GATE_OUT=$R20/receipts/BUNDLE_export_v2_A1.json \
    $PY $R20/v4e_gate_export_v2.py; rc=$?
echo "[1] rc=$rc ($(( $(date +%s) - t0 ))s)"

echo; echo "=== [2] REQUIRE v2 on that receipt (full floor + content gates re-run from disk)"
env $COMMON EXPORT_ARM=A1 BUNDLE_OUT=/workspace/shadow_bundle_v4 JUDGE_HC=/workspace/review_scratch/health_check \
    SIGNAL_RECEIPT=/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json EXPORT_GATE_OUT=/dev/null REQUIRE_OUT=$R20/receipts/REQUIRE_v2_A1.json \
    $PY $R20/v4e_gate_export_v2.py require $R20/receipts/BUNDLE_export_v2_A1.json; rc=$?
echo "[2] rc=$rc"

echo; echo "=== [3] REAL-DATA NEGATIVE: copy of the bundle with ONE prediction cell changed (genuine bundle untouched)"
rm -rf $R20/scratch/bundle_mut; cp -r /workspace/shadow_bundle_v4 $R20/scratch/bundle_mut
$PY - <<'EOF'
import numpy as np
p="/workspace/uplift_2026-09-11/r20_gate_closure/scratch/bundle_mut/slow_pred_pinned.npy"; a=np.load(p); i=np.argwhere(np.isfinite(a))[0]
a[tuple(i)] += np.float32(1e-4); np.save(p, a); print("mutated cell", tuple(int(x) for x in i))
EOF
echo "[3a] require the A1 receipt against the mutated copy (must FAIL: bundle/slow_pred_pinned.npy changed)"
env $COMMON EXPORT_ARM=A1 BUNDLE_OUT=$R20/scratch/bundle_mut JUDGE_HC=/workspace/review_scratch/health_check \
    SIGNAL_RECEIPT=/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json EXPORT_GATE_OUT=/dev/null REQUIRE_OUT=$R20/receipts/REQUIRE_v2_A1_mutated_bundle.json \
    $PY $R20/v4e_gate_export_v2.py require $R20/receipts/BUNDLE_export_v2_A1.json; echo "[3a] rc=$?"
echo "[3b] gate on the mutated copy (must FAIL E1_manifest; E3 IC tolerance is blind to one cell)"
env $COMMON EXPORT_ARM=A1 BUNDLE_OUT=$R20/scratch/bundle_mut JUDGE_HC=/workspace/review_scratch/health_check \
    SIGNAL_RECEIPT=/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json EXPORT_GATE_OUT=$R20/receipts/BUNDLE_export_v2_A1_mutated_bundle.json \
    $PY $R20/v4e_gate_export_v2.py; echo "[3b] rc=$?"

echo; echo "=== [4] SIGNAL GATE v2 for XIBLAG50 (bound receipt; panel = the one the device reads, v2ext)"
env SIG_PANEL=/workspace/data/wide_panel_4h_v2ext.npz SIG_FEMAT=/workspace/uplift_2026-09-11/infra2/dev/sig/XIBLAG50.npz SIG_ARM=XIBLAG50 \
    V4CHAIN_DIR=$R20/v4chain_PROPOSED2 SIGGATE_OUT=$R20/receipts/S_BITWISE_signal_v2_XIBLAG50.json $PY $R20/gate_signal_parity_v2.py; echo "[4] rc=$?"

echo; echo "=== [5] GATE v2 on XIBLAG50 (INFORMATIONAL — unregistered arm; JHC as the INFRA2 run used)"
env $COMMON EXPORT_ARM=XIBLAG50 BUNDLE_OUT=/workspace/shadow_bundle_v4 JUDGE_HC=/workspace/uplift_2026-09-11/infra2/JHC \
    SIGNAL_RECEIPT=$R20/receipts/S_BITWISE_signal_v2_XIBLAG50.json EXPORT_GATE_OUT=$R20/receipts/BUNDLE_export_v2_XIBLAG50.json \
    $PY $R20/v4e_gate_export_v2.py; echo "[5] rc=$?"

echo; echo "=== [6] ORIGINAL gate (f814c728) on genuine A1 for the side-by-side (its own receipt; frozen chain dir read only)"
env $COMMON EXPORT_ARM=A1 BUNDLE_OUT=/workspace/shadow_bundle_v4 JUDGE_HC=/workspace/review_scratch/health_check V4CHAIN_DIR=/workspace/uplift_2026-09-11/infra2/v4chain \
    SIGNAL_RECEIPT=/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json EXPORT_GATE_OUT=$R20/receipts/BUNDLE_export_ORIGINAL_A1.json \
    $PY /workspace/uplift_2026-09-11/infra2/v4e_gate_export.py; echo "[6] rc=$?"

echo; echo "=== shas of every receipt written"; sha256sum $R20/receipts/*.json
echo "=== DONE $(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg)"
