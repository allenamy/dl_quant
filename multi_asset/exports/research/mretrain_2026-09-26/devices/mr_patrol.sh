#!/bin/bash
# mr_patrol.sh -- pod2-side patrol of the family (E-0926-I/J): every 5 min appends ONE line to logs/patrol.log, so a missing line
# means the patrol itself stopped (it proves it is alive), and the line says whether the master PGID is alive, its last line, and the
# engine queue's last line. Exits after a terminal master line (STOP / MASTER_DONE / MASTER_STOPPED) or a dead master without one
# (SILENT_DEATH), with a final PATROL_END line. It never signals anything.
R=/dev/shm/mretrain_2026-09-26; L=$R/logs; P=$L/patrol.log
echo "{\"what\":\"mr_patrol.sh\",\"pgid\":\"$(ps -o pgid= -p $$ | tr -d ' ')\"}" > $L/PGID_patrol.json
while :; do
  G=$(python3 -c "import json;print(json.load(open('$L/PGID_master.json'))['pgid'])" 2>/dev/null)
  alive=0; [ -n "$G" ] && ps -o pid= -g "$G" > /dev/null 2>&1 && alive=1
  last=$(tail -1 $L/master.log 2>/dev/null | cut -c1-200); eq=$(tail -1 $L/engine/queue.log 2>/dev/null | cut -c1-160)
  term=$(grep -E "^[0-9TZ:-]+ (STOP|MASTER_DONE|MASTER_STOPPED)" $L/master.log 2>/dev/null | tail -1 | cut -c1-240)
  echo "PATROL $(date -u +%Y-%m-%dT%H:%M:%SZ) master_pgid=$G alive=$alive last=[$last] engine=[$eq] shm_free=$(df -BM /dev/shm | tail -1 | awk '{print $4}')" >> $P
  if [ -n "$term" ]; then echo "PATROL_END $(date -u +%Y-%m-%dT%H:%M:%SZ) TERMINAL [$term]" >> $P; exit 0; fi
  if [ $alive -eq 0 ]; then echo "PATROL_END $(date -u +%Y-%m-%dT%H:%M:%SZ) SILENT_DEATH master pgid $G gone without a terminal line" >> $P; exit 0; fi
  sleep 300
done
