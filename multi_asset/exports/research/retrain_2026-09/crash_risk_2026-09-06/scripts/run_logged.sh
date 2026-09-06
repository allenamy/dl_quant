#!/bin/bash
# crash_risk run_logged.sh — every command verbatim to logs/commands.txt with UTC start/end and rc; stdout/stderr -> logs/<TAG>.log
R=/workspace/review_scratch/crash_risk; TAG=$1; shift; cd $R || exit 2
echo "CMD[$TAG] (cwd=$PWD) $(date -u +%FT%TZ): env $*" >> $R/logs/commands.txt
env "$@" > $R/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $R/logs/commands.txt; exit $rc
