#!/bin/bash
# Positive control for the combo rollback verb, on a dummy launchd job with the SAME KeepAlive/RunAtLoad/bash -c 'echo $$ > pid; exec ...' shape as com.hsy.combolive. Touches no live job.
SP="$1"; L=com.hsy.test_rollback_verb_20260913; U=$(id -u); P="$SP/$L.plist"
st(){ echo "  [$(date -u +%H:%M:%SZ)] launchctl: $(launchctl print gui/$U/$L 2>&1 | grep -E '^\s*(state|pid|runs|last exit code) =' | tr -s ' \t' ' ' | tr '\n' ';') pidfile=$(cat $SP/test.pid 2>/dev/null) live_proc=$(pgrep -f "sleep 3600" | tr '\n' ',')"; }
echo "DRILL start $(date -u +%FT%TZ); live combolive before: $(launchctl print gui/$U/com.hsy.combolive | grep -E '^\s*pid =' | tr -s ' \t' ' ')"
echo "1) bootstrap dummy"; launchctl bootstrap gui/$U "$P"; echo "  rc=$?"; sleep 2; st
P1=$(cat $SP/test.pid)
echo "2) kill \$(cat pidfile) = kill $P1  (the documented rollback verb)"; kill "$P1"; echo "  rc=$?"; sleep 3; st
P2=$(cat $SP/test.pid); if [ "$P2" != "$P1" ] && launchctl print gui/$U/$L | grep -q 'state = running'; then echo "  RESULT kill: RESPAWNED (old $P1 -> new $P2) => kill is NOT a rollback"; else echo "  RESULT kill: not respawned"; fi
echo "3) launchctl bootout gui/$U/$L (candidate rollback verb)"; launchctl bootout gui/$U/$L; echo "  rc=$?"; sleep 5; st
if launchctl print gui/$U/$L >/dev/null 2>&1; then echo "  RESULT bootout: STILL LOADED"; else echo "  RESULT bootout: unloaded"; fi
if pgrep -f "sleep 3600" >/dev/null; then echo "  RESULT bootout: process still alive: $(pgrep -f 'sleep 3600')"; else echo "  RESULT bootout: no process, no respawn after 5s"; fi
echo "4) restore verb: launchctl bootstrap gui/$U <plist>"; launchctl bootstrap gui/$U "$P"; echo "  rc=$?"; sleep 2; st
echo "5) cleanup: bootout + remove dummy plist"; launchctl bootout gui/$U/$L; echo "  rc=$?"; sleep 2; pkill -f "sleep 3600" 2>/dev/null; rm -f "$P"; st
echo "DRILL end $(date -u +%FT%TZ); live combolive after: $(launchctl print gui/$U/com.hsy.combolive | grep -E '^\s*pid =' | tr -s ' \t' ' ')"
