#!/bin/bash
# S6 of the recovery step list: a FRESH isolated clone of the running executor tree + a full state copy, then the resume gate
# (`resume_from_trip.sh --check`) and its per-condition verdicts, both under sandbox-exec (network denied, production unreadable,
# writes only inside the clone and the system temp dirs). Touches nothing in ~/dl_quant_live. usage: bash recheck_clone.sh
# last line: RECHECK RESUMABLE | RECHECK NOT_RESUMABLE (rc 0 | 1); rc 2 = could not run
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd -P); T=$(date -u +%Y%m%dT%H%M%SZ); XC="$HOME/cc_tmp/recovery_recheck_$T"
git clone -q "$HOME/dl_quant_live" "$XC" || { echo "RECHECK could not clone"; exit 2; }
echo "clone $XC HEAD $(git -C "$XC" rev-parse --short HEAD) (running tree HEAD $(git -C "$HOME/dl_quant_live" rev-parse --short HEAD))"
rsync -a --exclude acceptance/ --exclude quarantine/ --exclude __pycache__/ --exclude pycache_void/ --exclude '/*.log' --exclude '/*.out' \
      --exclude anchor.lock "$HOME/dl_quant_live/state/" "$XC/state/" || { echo "RECHECK rsync failed"; exit 2; }
[ -e "$XC/.env" ] && { echo "RECHECK refused: the clone has a .env"; exit 2; }
SB="$XC.sb"
cat > "$SB" <<PROFILE
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "$XC") (subpath "/private/var/folders") (subpath "/private/tmp") (literal "/dev/null"))
(deny file-read* (subpath "$HOME/dl_quant_live") (subpath "$HOME/.ssh") (subpath "$HOME/Library/Keychains") (literal "$HOME/.quant_readonly.env"))
PROFILE
( cd "$XC" && LIVE_MODE=LIVE /usr/bin/sandbox-exec -f "$SB" bash ops/resume_from_trip.sh --check ); RC=$?
( cd "$XC" && /usr/bin/sandbox-exec -f "$SB" /usr/bin/python3 "$D/gate_conditions.py" "$XC" )
if [ $RC -eq 0 ]; then echo "RECHECK RESUMABLE"; exit 0; else echo "RECHECK NOT_RESUMABLE (resume --check rc=$RC)"; exit 1; fi
