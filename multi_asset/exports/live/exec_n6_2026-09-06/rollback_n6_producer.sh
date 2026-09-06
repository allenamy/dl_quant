#!/bin/bash
# PREREG_deploy_exec_n6_2026-09-06 §3.4 — producer side rollback: plist env back to 16, code file restored from backup, bootout/bootstrap.
# Usage: rollback_n6_producer.sh <backup_ts>   (the TS printed in swap RECEIPT). Executor config rollback is separate (safe_commit).
set -euo pipefail
TS=${1:?backup_ts}; W=/Users/haosiyu/wide_shadow; PL=$HOME/Library/LaunchAgents/com.hsy.shadowloop.plist; UID_=$(id -u)
[ -f "$PL.pre_n6_$TS" ] && [ -f "$W/shadow_loop_v3.py.pre_n6_$TS" ] || { echo "ABORT: backups for $TS not found"; exit 2; }
echo "utc=$(date -u +%FT%TZ) restoring from $TS"
cp "$PL.pre_n6_$TS" "$PL"; cp "$W/shadow_loop_v3.py.pre_n6_$TS" "$W/shadow_loop_v3.py"
echo "plist SHADOW_OFFSET_MIN=$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:SHADOW_OFFSET_MIN' "$PL") code sha=$(shasum -a 256 $W/shadow_loop_v3.py | cut -c1-16) pattern240=$(grep -c 'if self.win_weight + weight > 240:' $W/shadow_loop_v3.py)"
launchctl bootout gui/$UID_/com.hsy.shadowloop || true; sleep 3; launchctl bootstrap gui/$UID_ "$PL"; sleep 5
lpid=$(launchctl list | awk '$3=="com.hsy.shadowloop"{print $1}'); echo "launchd pid=$lpid shadow.lock=$(cat $W/shadow.lock 2>/dev/null)"; tail -n 1 $W/loop.out
