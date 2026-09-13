#!/bin/bash
# FX-W6C battery driver: runs run_acceptance.sh in the clone, binds the result to the tree at launch.
set -u
C=/Users/haosiyu/cc_tmp/fx_w6c
TAG=$1
D=/Users/haosiyu/cc_tmp/fx_w6c_receipts
HH=$((10#$(date -u +%H))); MIN=$((10#$(date -u +%M)))
if [ $((HH % 4)) -eq 0 ] && [ "$MIN" -ge 10 ] && [ "$MIN" -le 50 ]; then echo "REFUSE: inside anchor window ($(date -u +%H:%M)Z)"; exit 3; fi
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$D/battery_${TAG}_${TS}.log
META=$D/battery_${TAG}_${TS}.meta
{
echo "START $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "head_at_start $(git -C $C rev-parse HEAD)"
echo "tree_at_start $(git -C $C rev-parse HEAD^{tree})"
echo "tracked_changes_outside_state_at_start $(git -C $C status --porcelain -- . ':!state' | wc -l | tr -d ' ')"
echo "env_file_present $( [ -e $C/.env ] && echo YES || echo no )"
} > $META
(cd $C && bash run_acceptance.sh > $LOG 2>&1); BRC=$?
{
echo "END $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "battery_rc $BRC"
echo "head_at_end $(git -C $C rev-parse HEAD)"
echo "tracked_changes_outside_state_at_end $(git -C $C status --porcelain -- . ':!state' | wc -l | tr -d ' ')"
echo "summary_line: $(grep -E 'ACCEPTANCE' $LOG | tail -1)"
} >> $META
cat $META
