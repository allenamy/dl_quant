#!/bin/bash
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/gate_G2bc.py
run $PY gates/gate_G2bc.py
