#!/bin/zsh
# Launch gate for anything heavy on the PRODUCTION Mac (lead, 2026-09-23, after E-0923-F: I ran the
# global gate at 16:21Z, outside the silent window, from misreading the clock by an hour).
#
# The gate is the FIRST thing this script does, and it is a CALL, not a clock reading: the window is
# whatever venue_quiet_window.py says it is. Not open -> refuse to start, non-zero exit, nothing runs.
#
# usage: run_local_gated.sh <command> [args...]
set -e
GATE=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py
J=$(/usr/bin/python3 "$GATE" --json)
OPEN=$(printf '%s' "$J" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["open"])')
if [ "$OPEN" != "True" ]; then
  echo "REFUSED: silent window closed -- nothing was started."
  printf '%s\n' "$J"
  exit 9
fi
printf 'GATE open=%s remaining_min=%s\n' "$OPEN" \
  "$(printf '%s' "$J" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["remaining_min"])')"
printf '%s\n' "$J" > "${GATE_RECEIPT:-/tmp/venue_quiet_window_last.json}"
exec "$@"
