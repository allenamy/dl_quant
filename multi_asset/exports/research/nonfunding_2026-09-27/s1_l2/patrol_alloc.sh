#!/bin/bash
# patrol_alloc.sh — alloc's 10-minute patrol (session cron) for alloc_S1_l2n_net / alloc_S1_l2n_stat (pod2) and
# alloc_S3_xvenue_collector (this Mac). Prints one PATROL line plus every marker line not seen by the previous patrol.
# Silence has one meaning only (TEAM_PROTOCOL §10-c): each job is classified RUNNING / TERMINAL / DEAD_SILENT / LOG_MISSING,
# ssh failure prints SSH_FAIL (never read as "no news"). PGIDs are the registered ones, compared against the tmpfs PGID files.
# usage: bash patrol_alloc.sh <state_dir>
set -u
ST=${1:?state_dir}; mkdir -p "$ST" || exit 9
NOW=$(date -u +%FT%TZ)
REG_NET=${REG_NET:-3360852}; REG_STAT=${REG_STAT:-3362766}
OUT=$(ssh -o ConnectTimeout=20 -o BatchMode=yes ${POD_HOST:-pod2} "
S=/dev/shm/alloc_2026-09-26/l2n; R=/workspace/uplift_r3_2026-09-13/L2/receipts
for x in net stat; do
  L=\$S/l2n_\$x.log
  if [ ! -f \$L ]; then echo \"JOB \$x LOG_MISSING\"; continue; fi
  PF=\$(cat \$S/PGID_\$x 2>/dev/null || echo NA)
  N=\$(ps -eo pgid= | tr -d ' ' | grep -cx \"\$PF\")
  T=\$(grep -cE '^(STOP|DONE) ' \$L)
  echo \"JOB \$x pgid_file=\$PF alive=\$N terminal=\$T\"
  grep -E '^(START|GATE_OK|VERDICT_OK|NET_DONE_SEEN|NOTE|STOP|DONE|MARK_WRITE_FAILED)' \$L | sed \"s/^/MARK \$x /\"
done
tail -1 \$S/l2n_CHECKSUM.log 2>/dev/null | sed 's/^/PROG /'
ls -1 \$R 2>/dev/null | grep L2N | sed 's/^/RECEIPT /'
" 2>&1); RC=$?
if [ $RC -ne 0 ]; then echo "PATROL $NOW SSH_FAIL rc=$RC $(echo "$OUT" | tail -1)"; POD=SSH_FAIL; else POD=OK; fi
STATES=""
if [ $POD = OK ]; then
  for x in net stat; do
    J=$(echo "$OUT" | grep "^JOB $x ")
    REG=$REG_NET; [ $x = stat ] && REG=$REG_STAT
    if echo "$J" | grep -q LOG_MISSING; then s=LOG_MISSING
    else
      pf=$(echo "$J" | sed -E 's/.*pgid_file=([^ ]*).*/\1/'); al=$(echo "$J" | sed -E 's/.*alive=([0-9]+).*/\1/'); te=$(echo "$J" | sed -E 's/.*terminal=([0-9]+).*/\1/')
      if [ "$te" -gt 0 ]; then s=TERMINAL; elif [ "$al" -gt 0 ]; then s=RUNNING; else s=DEAD_SILENT; fi
      [ "$pf" = "$REG" ] || s="$s(PGID_FILE_$pf!=REG_$REG)"
    fi
    STATES="$STATES $x=$s"
  done
  echo "$OUT" | grep '^MARK ' > "$ST/marks.now"
  touch "$ST/marks.seen"; NEW=$(grep -vxF -f "$ST/marks.seen" "$ST/marks.now" || true)
  cp "$ST/marks.now" "$ST/marks.seen"
  echo "$OUT" | grep '^RECEIPT ' > "$ST/receipts.now"; touch "$ST/receipts.seen"
  NEWR=$(grep -vxF -f "$ST/receipts.seen" "$ST/receipts.now" || true); cp "$ST/receipts.now" "$ST/receipts.seen"
fi
# S3 collector (local): heartbeat age <= 180 s and every venue ok
HB=${HB_FILE:-$HOME/xvenue_collector/state/heartbeat.json}
S3=$(/usr/bin/python3 - "$HB" <<'EOF' 2>&1
import json, sys, time
try:
    h = json.load(open(sys.argv[1])); age = time.time() - h["run_ms"] / 1000; res = h["result"]
    bad = {k: v for k, v in res.items() if not str(v).startswith("ok")}
    print(("OK" if age <= 180 and not bad and len(res) == 3 else "BAD") + f" age_s={age:.0f} {' '.join(f'{k}={v}' for k, v in res.items())} free_gb={h.get('free_gb')}")
except Exception as e:
    print(f"BAD read_error={type(e).__name__}:{e}")
EOF
)
echo "PATROL $NOW pod2=$POD$STATES s3=$S3 $(echo "$OUT" | grep '^PROG ' | cut -c1-90)"
[ $POD = OK ] && [ -n "$NEW" ] && echo "$NEW" | sed 's/^/NEW /'
[ $POD = OK ] && [ -n "$NEWR" ] && echo "$NEWR" | sed 's/^/NEW /'
exit 0
