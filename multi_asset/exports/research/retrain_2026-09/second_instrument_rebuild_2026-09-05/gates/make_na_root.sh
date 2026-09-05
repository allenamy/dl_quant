#!/bin/bash
# make_na_root.sh — assemble a judge root holding the pinned artifacts (main G5) and the NOT-ADMITTED hist-king artifacts (dev_na/dev_alt_na)
set -e; ROOT=/workspace/review_scratch/jpline_rebuild; NA=$ROOT/na_root
mkdir -p $NA/dev/probe_artifacts $NA/dev_alt/probe_artifacts $NA/results
for f in $ROOT/dev/probe_artifacts/w10_ablation_series_*pinned*.npz $ROOT/dev/probe_artifacts/w10_ablation_series_F1_hist_log.npz $ROOT/dev_na/probe_artifacts/w10_ablation_series_*.npz; do ln -sfn $f $NA/dev/probe_artifacts/$(basename $f); done
for f in $ROOT/dev_alt/probe_artifacts/w10_ablation_series_*pinned*.npz $ROOT/dev_alt_na/probe_artifacts/w10_ablation_series_*.npz; do ln -sfn $f $NA/dev_alt/probe_artifacts/$(basename $f); done
ls -la $NA/dev/probe_artifacts $NA/dev_alt/probe_artifacts
