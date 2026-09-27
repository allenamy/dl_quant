#!/bin/bash
# run_neutral_step0.sh — pod2 driver for neutral_step0.py (zero-return step 0, DESIGN_net_neutrality_fix §3). nice 19 (yields to news2 D10 re-read and KSR),
# 4 threads, env whitelist. Markers on tmpfs with read-back; terminal '^STOP ' / '^DONE '.
set -u
D=/dev/shm/alloc_2026-09-26/neutral; LOG=$D/step0.log; PY=/workspace/venv/bin/python
mkdir -p $D || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $D/PGID_step0; [ "$(cat $D/PGID_step0)" = "$PG" ] || exit 9
mark "START neutral_step0 $(date -u +%FT%TZ) pgid=$PG"
cd $D || stop "no_dir"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  nice -n 19 taskset -c 40-43 $PY -B neutral_step0.py > $D/step0.out 2> $D/step0.err; rc=$?
L=$(grep -E '^NEUTRAL_STEP0 ' $D/step0.out | tail -1); [ -n "$L" ] || stop "no_final_line_rc_$rc"
[ $rc -eq 0 ] || stop "rc_$rc $L"
mark "GATE_OK $L"
mark "DONE $(date -u +%FT%TZ)"
