#!/bin/bash
# stage 13: POST-HOC DIAGNOSTIC of G4 (iii) — 10-seed shuffle-future null on every fold (not a gate).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/null_multiseed.py
run env NULL_SEEDS=10 $PY gates/null_multiseed.py
test -f results/G4b_multiseed.json || exit 3
