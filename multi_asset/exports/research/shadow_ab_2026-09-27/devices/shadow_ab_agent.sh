#!/bin/bash
# shadow_ab_agent.sh -- launchd agent com.hsy.shadowab (every 300 s). Forward shadow A/B of combo-layer arms (design:
# docs/DESIGN_forward_shadow_ab_2026-09-27.md). Read-only on ~/wide_shadow and ~/dl_quant_live (same sandbox isolation as the
# in-service parity replay); writes ONLY under $AB (default ~/shadow_ab) and the sandbox root ~/cc_tmp/shadow_ab.
# Each run: heartbeat -> terminal-state check -> CPU window gate -> replay new anchors (<=2) -> price anchors whose next snapshot exists.
# Terminal states (files, never deleted by the agent): $AB/STOP (fail-closed, with reason) and $AB/DONE (END_ANCHOR reached).
set -u
AB="${SHADOW_AB_HOME:-$HOME/shadow_ab}"; WS="${WIDE_SHADOW_HOME:-$HOME/wide_shadow}"; LIVE="${DL_QUANT_LIVE_ROOT:-$HOME/dl_quant_live}"
SBR="$HOME/cc_tmp/shadow_ab"; D="$AB/devices"; PY="$WS/venv/bin/python"; SNAP="$WS/state/snap"; L="$AB/logs"
mkdir -p "$L" "$AB/state" "$AB/skipped"
log() { echo "$(date -u +%FT%TZ) $*" >> "$L/agent.log"; }
hb() {  # atomic heartbeat: utc, pid, status, last replayed / priced anchors
  local last_r last_p
  last_r=$(ls "$AB/state" 2>/dev/null | grep -E '^[0-9]+$' | sort -n | tail -1); last_p=$(tail -1 "$AB/ledger.jsonl" 2>/dev/null | /usr/bin/python3 -c 'import sys,json; l=sys.stdin.read().strip(); print(json.loads(l)["anchor"] if l else "")' 2>/dev/null)
  printf '{"utc":"%s","pid":%s,"status":"%s","last_replayed":"%s","last_priced":"%s"}\n' "$(date -u +%FT%TZ)" $$ "$1" "$last_r" "$last_p" > "$AB/HEARTBEAT.json.tmp" && mv "$AB/HEARTBEAT.json.tmp" "$AB/HEARTBEAT.json"
}
stop() { printf '{"utc":"%s","reason":"%s"}\n' "$(date -u +%FT%TZ)" "$1" > "$AB/STOP"; log "STOP $1"; hb "STOPPED: $1"; exit 0; }
mkdir "$AB/.lock" 2>/dev/null || { hb "SKIP_LOCKED"; exit 0; }
trap 'rmdir "$AB/.lock" 2>/dev/null' EXIT
[ -f "$AB/STOP" ] && { hb "STOPPED (terminal)"; exit 0; }
[ -f "$AB/DONE" ] && { hb "DONE (terminal)"; exit 0; }
# config: START_ANCHOR / END_ANCHOR (epoch seconds, multiples of 14400), written at install
. "$AB/config.sh" || stop "no config.sh"
# fail-closed checks every run
FREE_KB=$(df -k "$HOME" | tail -1 | awk '{print $4}'); [ "$FREE_KB" -lt 2000000 ] && stop "disk free < 2 GB"
"$PY" -B "$D/shadow_ab_verify_ledger.py" "$AB/ledger.jsonl" >> "$L/agent.log" 2>&1 || stop "ledger chain broken"
# CPU window (team rule: heavy local work only in [N+1:00, N+3:40] after each 4h anchor)
NOW=$(date -u +%s); OFF=$(( NOW % 14400 )); if [ $OFF -lt 3600 ] || [ $OFF -gt 13200 ]; then hb "IDLE_OUTSIDE_WINDOW"; exit 0; fi
# ---- replay: snapshots that are complete AND already parity-checked by the in-service agent, from START_ANCHOR on, oldest first
n=0
for d in $(ls -d "$SNAP"/1[0-9]* 2>/dev/null | sort); do
  A=$(basename "$d"); [ "$A" -lt "$START_ANCHOR" ] && continue; [ "$A" -gt "$END_ANCHOR" ] && continue
  [ -f "$d/COMPLETE" ] && [ -f "$d/PARITY.json" ] || continue
  [ -f "$AB/state/$A/COLLECT.json" ] || [ -f "$AB/skipped/$A" ] && continue
  [ $n -ge 2 ] && break
  bash "$D/shadow_ab_replay.sh" "$A" "$L/REPLAY_$A.json" "$SBR" > "$L/replay_$A.log" 2>&1; RC=$?
  SB=$(/usr/bin/python3 "$WS/fea171/combosnap/replay_paths.py" "$WS" "$LIVE" "$SBR" "$A") && rm -rf "$SB"
  log "replay $A rc=$RC $(tail -1 "$L/replay_$A.log" | cut -c1-160)"
  case $RC in
    0) : ;;
    2) echo "VOID identity" > "$AB/skipped/$A"
       PREV=$((A - 14400)); [ -f "$AB/skipped/$PREV" ] && grep -q "VOID identity" "$AB/skipped/$PREV" && stop "identity control failed at two consecutive anchors ($PREV, $A)" ;;
    *) grep -q "UNAVAILABLE hook insertion" "$L/replay_$A.log" && stop "in-service combo_stage changed: hook insertion point/names not found ($A)"
       echo "UNAVAILABLE rc=$RC" > "$AB/skipped/$A" ;;
  esac
  n=$((n + 1))
done
# ---- price: stored anchors whose next snapshot is complete and that are not yet in the ledger (ascending, append-only)
for s in $(ls "$AB/state" | grep -E '^[0-9]+$' | sort -n); do
  [ -f "$AB/state/$s/COLLECT.json" ] || continue
  "$PY" -B "$D/shadow_ab_pnl.py" "$s" "$AB" "$WS" >> "$L/pnl.log" 2>&1; RC=$?
  case $RC in 0) log "priced $s" ;; 3|4) : ;; *) stop "pnl device error rc=$RC at $s" ;; esac
done
LASTP=$(tail -1 "$AB/ledger.jsonl" 2>/dev/null | /usr/bin/python3 -c 'import sys,json; l=sys.stdin.read().strip(); print(json.loads(l)["anchor"] if l else 0)')
[ "${LASTP:-0}" -ge "$END_ANCHOR" ] && { printf '{"utc":"%s","end_anchor":%s}\n' "$(date -u +%FT%TZ)" "$END_ANCHOR" > "$AB/DONE"; log "DONE"; hb "DONE"; exit 0; }
hb "OK"
