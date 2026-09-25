#!/bin/bash
# FIX-D engine arm (lead 2026-09-25): NC s42X, ALL 32 seeds, patched mirror COPY (fixd_mirror.py), read-only hook on (post-clamp net),
# team run gate + at most ONE other engine group (dlarch first). Outputs under /dev/shm/c4hook_2026-09-25/fixD.
set -u
NC=/dev/shm/news2_2026-09-23; ME=/dev/shm/c4hook_2026-09-25; DEV=$ME/devices; FD=$ME/fixD; GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh
mkdir -p $FD/logs $FD/receipts $FD/hook
BASE=$NC/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json
SRC=$(/workspace/venv/bin/python -c "import json;print(json.load(open('$BASE'))['paths']['exec_mirror'])")
[ -d $FD/exec_mirror ] || /workspace/venv/bin/python -B $DEV/fixd_mirror.py $SRC $FD/exec_mirror $DEV/fixD_anchor_loop.diff $BASE $FD/RUN_CONFIG_fixD.json $FD > $FD/logs/mirror.log 2>&1
grep -q FIXD_MIRROR_OK $FD/logs/mirror.log || { echo "mirror build FAILED" >> $FD/logs/gate.log; exit 3; }
while true; do
  OTHERS=$(ps -eo pgid=,args= | grep -E "bt_launch.py" | grep -v grep | grep -v "$ME" | awk '{print $1}' | sort -u | wc -l)
  G=$(bash $GATE 2>&1); GR=$?
  echo "$(date -u +%FT%TZ) others=$OTHERS memgate_rc=$GR $(echo "$G" | tail -1)" >> $FD/logs/gate.log
  if [ "$GR" -eq 0 ] && [ "$OTHERS" -le 1 ]; then break; fi
  sleep 60
done
cd $NC/engine
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B $DEV/hook_prelude.py $FD/hook $NC/engine/bt_launch.py PATH,HOME,LC_CTYPE \
  $FD/RUN_CONFIG_fixD.json > $FD/logs/engine.log 2>&1
echo "engine rc=$? $(date -u +%FT%TZ)" >> $FD/logs/gate.log
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $DEV/fixd_read.py $FD/runs/NEWS2_s42X_scaled_rule_raw_UAFE $FD/hook /dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s42X.npz $FD/FIXD_READ.json > $FD/logs/read.log 2>&1
echo "read rc=$? $(date -u +%FT%TZ)" >> $FD/logs/gate.log
