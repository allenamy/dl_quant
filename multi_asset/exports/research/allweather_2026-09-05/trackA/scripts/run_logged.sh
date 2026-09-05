#!/bin/bash
# run_logged.sh — Track A command runner (pod2). usage: run_logged.sh <TAG> <ENV assignments and command...>
# Every command goes verbatim to logs/commands.txt with UTC start/end and rc; stdout/stderr -> logs/<TAG>.log. Writes only under ROOT.
ROOT=/workspace/review_scratch/allweather_trackA
TAG=$1; shift
cd $ROOT || exit 2
echo "CMD[$TAG] (cwd=$PWD) $(date -u +%FT%TZ): env $*" >> $ROOT/logs/commands.txt
env "$@" > $ROOT/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
exit $rc
