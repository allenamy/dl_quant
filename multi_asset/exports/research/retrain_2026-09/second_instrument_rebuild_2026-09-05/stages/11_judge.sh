#!/bin/bash
# stage 11: G5 judge (adapted from rolling_king judge.py: paired anchors, UTC-day blocks, 2000 resamples, seed 20260905; yearly 2022..2026 + 2024->26 + 2025->26; worst month; σ_fund terciles).
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum gates/judge_rebuild.py src/judge.py
run $PY gates/judge_rebuild.py
test -f results/judge_rebuild.json || exit 3
run sha256sum results/judge_rebuild.json results/REPORT_tables.md
