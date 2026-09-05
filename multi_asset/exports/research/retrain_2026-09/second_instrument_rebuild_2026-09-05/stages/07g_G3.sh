#!/bin/bash
# gate G3: (a) static expm1/log1p/log census on the 4 scripts; (b) Y4 == Σ ret5 bitwise; y4s vs raw zip closes (>=1000 anchors, >=300 in 2020-21); Σ vs Π info.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G3.py
run $PY gates/gate_G3.py
