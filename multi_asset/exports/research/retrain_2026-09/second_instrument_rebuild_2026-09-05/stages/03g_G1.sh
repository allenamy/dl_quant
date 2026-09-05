#!/bin/bash
# gate G1 (panel bitwise vs v1) + G1b (cache 2022+ vs _ext cache, informational). Never halts the chain on FAIL (prereg §2 G1: classify, continue).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G1.py
run $PY gates/gate_G1.py
