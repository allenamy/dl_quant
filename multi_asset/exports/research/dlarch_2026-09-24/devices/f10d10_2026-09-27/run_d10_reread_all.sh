#!/bin/bash
# run_d10_reread_all.sh -- one executor (10-f) for the whole D10 descriptive re-read, so that yielding pod2 and giving it back are done
# by a process, not by a session remembering (lead 13:0xZ; fresh2's PAUSE protocol): touch /dev/shm/mretrain_2026-09-26/PAUSE (fresh2's
# KSR driver starts no new prep / cell while it exists; the running one finishes), then run_rescore.sh reread, then run_reread_cells.sh,
# and remove PAUSE on EVERY exit path (trap), success or failure. Needs env RR_FEATURES RR_FEATURES_SHA RR_FEATURES_RECEIPT RR_LEGS
# RR_LEGS_SHA RR_LEGS_RECEIPT RR_KING_OOF. Terminal: 'D10RR_ALL_DONE rc=<n>' in /dev/shm/dlarch_f10d10/reread_all.log.
set -u
C=/workspace/dlarch_2026-09-24/f10d10_2026-09-27; M=/dev/shm/dlarch_f10d10; LOG=$M/reread_all.log; PAUSE=/dev/shm/mretrain_2026-09-26/PAUSE
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=d10_reread_all started=$(date -u +%FT%TZ)" > $M/reread_all.pgid
say(){ echo "$(date -u +%FT%TZ) $*" >> $LOG; }
MINE=0
release(){ if [ $MINE = 1 ] && grep -q "dlarch D10 reread" $PAUSE 2>/dev/null; then rm -f $PAUSE && say "PAUSE removed"; fi; }
trap 'release' EXIT
if [ -e $PAUSE ]; then say "PAUSE already present (not mine): $(cat $PAUSE)"; else echo "dlarch D10 reread $(date -u +%H:%MZ) pgid $(ps -o pgid= -p $$ | tr -d ' ')" > $PAUSE && MINE=1 && say "PAUSE placed"; fi
RC=0
bash $C/run_rescore.sh reread || RC=1
grep -q "^RESCORE_REREAD_DONE rc=0" $M/rescore.log || RC=1
if [ $RC = 0 ]; then bash $C/run_reread_cells.sh || RC=1; grep -q "^REREAD_CELLS_DONE rc=0" $M/reread.log || RC=1; fi
say "D10RR_ALL_DONE rc=$RC"; echo "D10RR_ALL_DONE rc=$RC" >> $LOG
