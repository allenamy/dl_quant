#!/bin/bash
# launch_pod2.sh <device.py> — detached, niced launch of a T5d pod2 device with the enumerated env whitelist (no kill logic here, by design)
set -u
cd /workspace/uplift_r2_2026-09-13/T5d || exit 2
dev="$1"; tag=$(basename "$dev" .py)
nohup env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python "devices/$dev" PATH,HOME,LC_CTYPE > "receipts/${tag}_stdout.log" 2>&1 < /dev/null &
echo "launched $dev pid $!"
