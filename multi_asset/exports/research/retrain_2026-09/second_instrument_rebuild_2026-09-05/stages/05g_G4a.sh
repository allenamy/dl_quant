#!/bin/bash
# gate G4 items (i) causality assert per fold, (ii) fold-out leakage, (vi) feature window max row == E-1. Verdict to results/G4a.json.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G4a.py
run $PY gates/gate_G4a.py
