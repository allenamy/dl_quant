#!/bin/bash
# Stacked landing battery, round 6. Usage: stacked_landing_r5.sh <w6ab.diff> <w2.diff> <w1.diff> <w9.diff> [extra suite paths...]
# Read-only against ~/dl_quant_live (clone + state copy). Writes only under /Users/haosiyu/cc_tmp and docs/receipts.
set -u
W6=$1; W2=$2; W1=$3; W9=$4; shift 4; EXTRA="$*"
Q=/Users/haosiyu/Desktop/quant_research; TS=$(date -u +%Y%m%dT%H%M%SZ); C=/Users/haosiyu/cc_tmp/exec_land_stack_$TS
LOG=$Q/docs/receipts/stacked_landing_r6_driver_$TS.log
h() { shasum -a 256 "$1" | cut -c1-16; }
hm=$(date -u +%H%M); if [ "$hm" -ge 2000 ] 2>/dev/null; then :; fi
HH=$((10#$(date -u +%H))); MIN=$((10#$(date -u +%M))); if [ $((HH % 4)) -eq 0 ] && [ "$MIN" -ge 15 ] && [ "$MIN" -le 50 ]; then echo "REFUSE: inside 4h anchor window HH:15-50 on anchor hours (now $(date -u +%H:%M)Z)" | tee $LOG; exit 3; fi
{
echo "START $(date -u +%H:%M:%SZ) w6ab=$(h $W6) w2=$(h $W2) w1=$(h $W1) w9=$(h $W9)"
git clone -q --no-hardlinks /Users/haosiyu/dl_quant_live $C && git -C $C checkout -q 918559f && echo "clone at $(git -C $C rev-parse --short HEAD)" || { echo "CLONE FAILED"; exit 4; }
for d in $W6 $W2 $W1 $W9; do echo "== apply $(basename $d) sha $(shasum -a 256 $d | cut -c1-12)"; git -C $C apply --check "$d" && git -C $C apply "$d" || { echo "APPLY FAILED $d"; exit 5; }; done
echo "changed files: $(git -C $C status --short | grep -v '^?? state' | wc -l | tr -d ' ')"
rm -rf $C/state && cp -R /Users/haosiyu/dl_quant_live/state $C/state && echo "state snapshot copied at $(date -u +%H:%M:%SZ): pilot_log days=$(ls $C/state/live/pilot_log | wc -l | tr -d ' ')"
CH=$(git -C $C diff --name-only 918559f -- '*.py'; git -C $C ls-files --others --exclude-standard -- '*.py' | grep -v '^state/')
(cd $C && /usr/bin/python3 -m py_compile $CH) && echo "compile-ok" || echo "COMPILE FAILED"
for t in live/tests_reduce_only_clamp.py live/tests_ic_monitor.py live/tests_readers_three_bucket.py live/tests_daily_summary.py $EXTRA; do
  if [ -f $C/$t ]; then out=$(cd $C && /usr/bin/python3 $t 2>&1); rc=$?; echo "$t: rc=$rc :: $(echo "$out" | grep -E 'ALL PASS|FAILURES|passed|FAIL' | tail -1 | cut -c1-160)"; else echo "$t: MISSING"; fi
done
BL=$Q/docs/receipts/stacked_landing_battery_$TS.log
(cd $C && bash run_acceptance.sh > $BL 2>&1); brc=$?
echo "battery → $BL"; echo "battery rc=$brc"
awk 'NF>=3 && $2 ~ /^[0-9]+$/ && $2 != "0" {print "RED", $1}' $BL
echo "clone: $C"
echo "END $(date -u +%H:%M:%SZ) w6ab=$(h $W6) w2=$(h $W2) w1=$(h $W1) w9=$(h $W9)"
} 2>&1 | tee $LOG
