#!/bin/bash
# gate G2(a): rebuilt nets_histv2_* vs the real 08-21 files (ref/, Mac backup of the 08-21 pod, sha in ref/SHA256SUMS_ref); pod port copies are 144-byte stubs.
# Then DIAGNOSTIC (not a gate/arm): diag_g2a.py = stage-6 device with (A) funding masked to the 08-21 coverage + real 08-21 king, (B) rebuilt panel + real 08-21 king.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G2a.py gates/diag_g2a.py; ls -la /workspace/port_w10/pod_backup_2026-08-21/nets_histv2_*.npy
run $PY gates/gate_G2a.py
run $PY gates/diag_g2a.py
