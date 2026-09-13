#!/bin/bash
# t7_pull_launch.sh <root> — launch the three host workers detached (each under caffeinate -i so the Mac does not idle-sleep mid-pull).
# Liveness: run/pids.txt; completion: run/exits_<venue>.jsonl (written by the worker itself, including crashes).
set -u
ROOT="$1"
mkdir -p "$ROOT/run" "$ROOT/manifest" "$ROOT/logs"   # the stdout redirect below needs run/ to exist before python starts
cd "$ROOT/devices" || exit 2
for v in upbit bithumb binance; do
  nohup /usr/bin/caffeinate -i /usr/local/bin/python3 t7_pull.py --venue "$v" --root "$ROOT" > "$ROOT/run/stdout_$v.log" 2>&1 < /dev/null &
  echo "$v $! $(date -u +%FT%TZ)" >> "$ROOT/run/pids.txt"
done
cat "$ROOT/run/pids.txt"
