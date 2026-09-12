#!/bin/bash
# r19: isolated replay tree mirroring trackF/dev_v4F by symlink (frozen v4 artifacts never written); device = byte copy of trackF/w10_trackF.py
set -e
H=/workspace/review_scratch/health_check
R19=/workspace/uplift_2026-09-11/r19_trackF_reindex; T=$R19/dev_v4F19
mkdir -p $T/probe_artifacts $T/logs $T/pod_backup_2026-08-21
for f in $H/dev_v4/pod_backup_2026-08-21/*; do ln -sfn "$(readlink -f "$f")" $T/pod_backup_2026-08-21/$(basename "$f"); done
ln -sfn "$(readlink -f $H/dev_v4/dlw_2026-08-22)" $T/dlw_2026-08-22
ln -sfn "$(readlink -f $H/dev_v4/f8_2026-08-22)" $T/f8_2026-08-22
cp -n /workspace/uplift_2026-09-11/trackF/w10_trackF.py $R19/w10_trackF.py
S=$(sha256sum $R19/w10_trackF.py | cut -c1-64); echo "w10_trackF.py sha256 $S"
[ "$S" = "d3aa1ddc2fbe876b87b7bbf26d718ad4038fc55b61274b841f35387159a6dcce" ] || { echo "DEVICE SHA MISMATCH"; exit 9; }
ls -la $T | head
