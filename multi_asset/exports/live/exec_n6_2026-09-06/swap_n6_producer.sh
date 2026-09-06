#!/bin/bash
# PREREG_deploy_exec_n6_2026-09-06 §3.1 — producer side swap (offset 16→1, budget 240→480) with backups and receipts.
# DEFAULT = dry-run (prints what it would do, touches nothing). `--apply` performs it. Executor config is NOT touched here
# (that goes through ~/dl_quant_live ops/safe_commit.sh separately). Rollback: rollback_n6_producer.sh <backup_ts>.
set -euo pipefail
MODE=${1:-dry-run}; W=/Users/haosiyu/wide_shadow; PL=$HOME/Library/LaunchAgents/com.hsy.shadowloop.plist
SB=/Users/haosiyu/cc_tmp/exec_n6_sandbox; TS=$(date -u +%Y%m%dT%H%M%SZ); UID_=$(id -u)
V2=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/exec_n6_2026-09-06/v2/shadow_loop_v3_v2.py; V2SHA_EXPECT=9df64f64f6f7326b
KNOBS="FETCH_WORKERS=6 FETCH_BUDGET=720 FUND_BULK=1 HTTP_TIMEOUT=10"
echo "mode=$MODE utc=$(date -u +%FT%TZ) backup_ts=$TS"
# ---- preconditions (printed in both modes; enforced in --apply) ----
off=$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:SHADOW_OFFSET_MIN' "$PL"); echo "plist SHADOW_OFFSET_MIN=$off (expect 16)"
v2sha=$(shasum -a 256 $V2 | cut -c1-16); echo "v2 file sha=$v2sha (expect $V2SHA_EXPECT)"; n_pat=$([ "$v2sha" = "$V2SHA_EXPECT" ] && echo 1 || echo 0)
sha0=$(shasum -a 256 $W/shadow_loop_v3.py | cut -c1-16); echo "shadow_loop_v3.py sha=$sha0"
lock=$(cat $W/shadow.lock 2>/dev/null || echo none); echo "live shadow.lock pid=$lock alive=$(ps -p "$lock" -o pid= 2>/dev/null | wc -l | tr -d ' ')"
m=$(( ($(date -u +%s) % 14400) / 60 )); echo "minutes since anchor=$m (quiet window 60..235)"
sbpid=$(cat $SB/shadow.lock 2>/dev/null || echo none); sbalive=$(ps -p "$sbpid" -o pid= 2>/dev/null | wc -l | tr -d ' '); echo "sandbox pid=$sbpid alive=$sbalive (must be stopped before apply)"
if [ "$MODE" != "--apply" ]; then
  echo "DRY-RUN would: 1) touch $SB/KILL and wait for sandbox pid $sbpid to exit (kill by that exact pid after 120s)"
  echo "               2) cp $PL $PL.pre_n6_$TS ; PlistBuddy Set SHADOW_OFFSET_MIN 1"
  echo "               3) cp $W/shadow_loop_v3.py $W/shadow_loop_v3.py.pre_n6_$TS ; install v2 file ($V2SHA_EXPECT) ; plist env add $KNOBS"
  echo "               4) launchctl bootout gui/$UID_/com.hsy.shadowloop ; launchctl bootstrap gui/$UID_ $PL"
  echo "               5) verify: launchctl pid == shadow.lock pid ; loop.out last line 'next …:01:00'"; exit 0
fi
[ "$off" = "16" ] || { echo "ABORT: offset is $off, not 16"; exit 2; }
[ "$n_pat" = "1" ] || { echo "ABORT: v2 file sha mismatch"; exit 2; }
[ $m -ge 60 ] && [ $m -le 235 ] || { echo "ABORT: not in quiet window"; exit 3; }
# 1) stop sandbox (never the live pid)
if [ "$sbalive" = "1" ]; then
  [ "$sbpid" != "$lock" ] || { echo "ABORT: sandbox pid equals live pid?!"; exit 4; }
  touch $SB/KILL; for i in $(seq 1 24); do ps -p "$sbpid" >/dev/null 2>&1 || break; sleep 5; done
  ps -p "$sbpid" >/dev/null 2>&1 && { echo "sandbox still alive after 120s; kill -TERM $sbpid"; kill -TERM "$sbpid"; sleep 3; }
fi
ps -p "$sbpid" >/dev/null 2>&1 && { echo "ABORT: sandbox pid $sbpid still alive"; exit 4; }; echo "sandbox stopped"
# 2) plist
cp "$PL" "$PL.pre_n6_$TS"; /usr/libexec/PlistBuddy -c 'Set :EnvironmentVariables:SHADOW_OFFSET_MIN 1' "$PL"
for kv in $KNOBS; do k=${kv%%=*}; v=${kv#*=}; /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:$k string $v" "$PL" 2>/dev/null || /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:$k $v" "$PL"; done
/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables' "$PL"
echo "plist SHADOW_OFFSET_MIN now=$(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:SHADOW_OFFSET_MIN' "$PL") backup=$PL.pre_n6_$TS"
# 3) code file: install v2 (verbatim original + fetch-layer knobs; knobs come from plist env)
cp $W/shadow_loop_v3.py $W/shadow_loop_v3.py.pre_n6_$TS; cp "$V2" $W/shadow_loop_v3.py
sha1=$(shasum -a 256 $W/shadow_loop_v3.py | cut -c1-16); echo "shadow_loop_v3.py sha $sha0 -> $sha1 backup=$W/shadow_loop_v3.py.pre_n6_$TS"
# 4) reload launchd job (env change needs bootout/bootstrap; kickstart keeps old env — E-0904-A)
launchctl bootout gui/$UID_/com.hsy.shadowloop || true; sleep 3; launchctl bootstrap gui/$UID_ "$PL"; sleep 5
# 5) verify
lpid=$(launchctl list | awk '$3=="com.hsy.shadowloop"{print $1}'); newlock=$(cat $W/shadow.lock 2>/dev/null || echo none)
echo "launchd pid=$lpid shadow.lock=$newlock $( [ "$lpid" = "$newlock" ] && echo MATCH || echo MISMATCH)"
tail -n 1 $W/loop.out; tail -n 1 $W/loop.out | grep -q ':01:00' && echo "loop.out next …:01:00 ✓" || echo "loop.out next line NOT :01:00 ← check"
echo "RECEIPT ts=$TS plist_backup=$PL.pre_n6_$TS code_backup=$W/shadow_loop_v3.py.pre_n6_$TS sha_before=$sha0 sha_after=$sha1 old_live_pid=$lock new_pid=$lpid"
