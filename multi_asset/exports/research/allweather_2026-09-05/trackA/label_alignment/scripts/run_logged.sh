#!/bin/bash
# label_alignment run_logged.sh — every command verbatim to label_alignment/logs/commands.txt with UTC start/end and rc; stdout/stderr -> logs/<TAG>.log
L=/workspace/review_scratch/allweather_trackA/label_alignment; TAG=$1; shift
cd /workspace/review_scratch/allweather_trackA || exit 2
echo "CMD[$TAG] (cwd=$PWD) $(date -u +%FT%TZ): env $*" >> $L/logs/commands.txt
env "$@" > $L/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $L/logs/commands.txt
exit $rc
