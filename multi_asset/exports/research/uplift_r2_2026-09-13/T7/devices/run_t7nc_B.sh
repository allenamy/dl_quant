#!/bin/bash
# run_t7nc_B.sh — T7 NC zero-return stage B on the Mac (AMENDMENT 21ecc60f5 + AMENDMENT-2 435559a61; lead 09:0xZ: GAP4 window cancelled, run now at
# nice 19, frozen devices unchanged, must end before 11:40Z; past 11:30Z stop at a whole-step boundary). Steps, in the frozen order:
#   1 t7_s1_guards.py (G1-G5; exit 0 = PASS, 2 = STOP)   2 t7_s1_build.py (candidates, no returns)   3 t7nc_zero.py B (coverage + eval-year assertion)
# Markers on /Users/haosiyu/cc_tmp/t7_nc/logs/B.log with read-back; terminal '^STOP ' / '^DONE '. No return is read by any step.
set -u
DEV=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices
LD=/Users/haosiyu/cc_tmp/t7_nc/logs; LOG=$LD/B.log; PY=/opt/homebrew/bin/python3
mkdir -p $LD || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $LD/PGID_B; [ "$(cat $LD/PGID_B)" = "$PG" ] || exit 9
mark "START t7nc_B $(date -u +%FT%TZ) pgid=$PG py=$($PY -c 'import sys,numpy;print(sys.version.split()[0],numpy.__version__)')"
deadline() { [ "$(date -u +%H%M)" \< "1130" ] || stop "deadline_1130Z_reached_before_step_$1"; }
cd $DEV || stop "no_devices"
deadline guards
nice -n 19 $PY -B t7_s1_guards.py > $LD/guards.log 2>&1; rc=$?
[ $rc -eq 0 ] || stop "guards_rc_$rc"
mark "GATE_OK guards $(date -u +%FT%TZ)"
deadline build
nice -n 19 $PY -B t7_s1_build.py > $LD/build.log 2>&1 || stop "build_rc"
mark "GATE_OK build $(date -u +%FT%TZ)"
deadline zeroB
nice -n 19 $PY -B t7nc_zero.py B > $LD/zeroB.log 2>&1; rc=$?
[ $rc -eq 0 ] || stop "zeroB_rc_$rc"
grep -q '^T7NC_ZERO_B DONE' $LD/zeroB.log || stop "zeroB_done_line_missing"
mark "GATE_OK zeroB $(tail -1 $LD/zeroB.log)"
mark "DONE $(date -u +%FT%TZ)"
