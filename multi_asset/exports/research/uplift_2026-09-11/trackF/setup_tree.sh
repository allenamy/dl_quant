#!/bin/bash
# Track F: build an isolated replay tree that MIRRORS dev_v4 by symlink (frozen v4 artifacts are never written to).
set -e
H=/workspace/review_scratch/health_check
T=/workspace/uplift_2026-09-11/trackF/dev_v4F
mkdir -p $T/probe_artifacts $T/logs $T/pod_backup_2026-08-21
for f in $H/dev_v4/pod_backup_2026-08-21/*; do ln -sfn "$(readlink -f "$f")" $T/pod_backup_2026-08-21/$(basename "$f"); done
ln -sfn "$(readlink -f $H/dev_v4/dlw_2026-08-22)" $T/dlw_2026-08-22
ln -sfn "$(readlink -f $H/dev_v4/f8_2026-08-22)" $T/f8_2026-08-22
cp -n $H/w10_health.py /workspace/uplift_2026-09-11/trackF/w10_health_copy.py
sha256sum $H/w10_health.py /workspace/uplift_2026-09-11/trackF/w10_health_copy.py
ls -la $T
