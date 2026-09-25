#!/bin/zsh
# executor full battery on the isolated M3 v2 clone (dd486af, not pushed). Same state rsync excludes as A4 (DEPLOY doc L396).
set -u
XC=~/cc_tmp/m3v2_exec_20260925
[ "$(git -C $XC rev-parse --short HEAD)" = "dd486af" ] || { echo "clone HEAD is not dd486af"; exit 3; }
[ -z "$(git -C $XC status --porcelain --untracked-files=no)" ] || { echo "clone has tracked modifications"; exit 3; }
date -u +"rsync start %T"
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' --exclude anchor.lock ~/dl_quant_live/state/ $XC/state/
echo "rsync rc=$? $(date -u +%T)"
cd $XC && bash ops/run_acceptance_offline.sh > $XC/../m3v2_battery_$(date -u +%Y%m%dT%H%MZ).log 2>&1
echo "battery rc=$? $(date -u +%T)"
