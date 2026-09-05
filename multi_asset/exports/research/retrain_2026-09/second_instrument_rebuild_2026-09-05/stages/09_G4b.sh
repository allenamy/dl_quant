#!/bin/bash
# gate G4 items (iii) shuffle-future null (3 seeds x 5 folds), (iv) offset spectrum, (v) embargo invariance (2024/2025 folds, 60 anchors).
# Writes results/G4b.json and results/G4_verdict.json (hist king admitted to G5 iff G4a and G4b all pass).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G4b.py
run $PY gates/gate_G4b.py
test -f results/G4_verdict.json || exit 3
cat results/G4_verdict.json
