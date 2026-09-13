#!/bin/bash
# Attempt 2. Attempt 1 read "not respawned" 3 s after kill while launchd showed "spawn scheduled": launchd throttles respawn of a job that ran < ThrottleInterval (10 s) — the dummy had run ~3 s; the live job has run 14 days. Fix: let the dummy run 15 s before kill; poll 1/3/6/12/15 s after kill; "spawn scheduled" counts as respawn pending (NOT a rollback).
SP="$1"; L=com.hsy.test_rollback_verb_20260913; U=$(id -u); P="$SP/$L.plist"
st(){ echo "  [$(date -u +%H:%M:%SZ)] $(launchctl print gui/$U/$L 2>&1 | grep -E '^\s*(state|pid|runs|last exit code) =' | head -4 | tr -s ' \t' ' ' | tr '\n' ';') pidfile=$(cat $SP/test.pid 2>/dev/null) procs=$(pgrep -f "sleep 3600" | tr '\n' ',')"; }
echo "DRILL2 start $(date -u +%FT%TZ); live combolive before: $(launchctl print gui/$U/com.hsy.combolive | grep -E '^\s*pid =' | tr -s ' \t' ' ')"
launchctl bootstrap gui/$U "$P"; echo "1) bootstrap rc=$?"; sleep 15; st
P1=$(cat $SP/test.pid); kill "$P1"; echo "2) kill $P1 rc=$?"
for w in 1 2 3 6 3; do sleep $w; st; done
P2=$(cat $SP/test.pid); S=$(launchctl print gui/$U/$L 2>&1 | grep -m1 -E '^\s*state =' | tr -s ' \t' ' ')
if [ "$P2" != "$P1" ] && pgrep -f "sleep 3600" >/dev/null; then echo "  RESULT kill: RESPAWNED old=$P1 new=$P2 => kill is NOT a rollback"; elif echo "$S" | grep -q 'spawn scheduled'; then echo "  RESULT kill: RESPAWN PENDING ($S) => kill is NOT a rollback"; else echo "  RESULT kill: no respawn within 15 s ($S)"; fi
launchctl bootout gui/$U/$L; echo "3) bootout rc=$?"; for w in 2 5 8; do sleep $w; st; done
if launchctl print gui/$U/$L >/dev/null 2>&1; then echo "  RESULT bootout: STILL LOADED"; elif pgrep -f "sleep 3600" >/dev/null; then echo "  RESULT bootout: unloaded but process alive $(pgrep -f 'sleep 3600')"; else echo "  RESULT bootout: unloaded, no process, no respawn over 15 s => bootout IS a rollback"; fi
launchctl bootstrap gui/$U "$P"; echo "4) restore bootstrap rc=$?"; sleep 3; st
if pgrep -f "sleep 3600" >/dev/null; then echo "  RESULT restore: running again => bootstrap restores"; else echo "  RESULT restore: NOT running"; fi
launchctl bootout gui/$U/$L; echo "5) cleanup bootout rc=$?"; sleep 3; pkill -f "sleep 3600" 2>/dev/null; rm -f "$P"; st
echo "DRILL2 end $(date -u +%FT%TZ); live combolive after: $(launchctl print gui/$U/com.hsy.combolive | grep -E '^\s*pid =' | tr -s ' \t' ' ')"
