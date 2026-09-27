#!/bin/bash
# run_t7nc_controls.sh — pod2 driver: t7nc_judge_control.py POS then NEG (lead 10:1xZ). Markers on tmpfs with read-back; terminal '^STOP ' / '^DONE '.
# Each control prints exactly one 'T7NC_CONTROL {...}' verdict line (synthetic world; no real reading). env whitelist, nice 10, 8 cores.
set -u
D=/dev/shm/alloc_2026-09-26/t7nc; LOG=$D/controls.log; PY=/workspace/venv/bin/python
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $D/PGID_controls; [ "$(cat $D/PGID_controls)" = "$PG" ] || exit 9
mark "START t7nc_controls $(date -u +%FT%TZ) pgid=$PG"
cd $D || stop "no_dir"
for M in POS NEG; do
  env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
    nice -n 10 taskset -c 40-47 $PY -B t7nc_judge_control.py $M > $D/control_$M.out 2> $D/control_$M.err || stop "control_${M}_rc"
  L=$(grep '^T7NC_CONTROL ' $D/control_$M.out | tail -1); [ -n "$L" ] || stop "control_${M}_no_verdict_line"
  echo "$L" | grep -q '"EXPECTATION_MET": true' || { mark "CONTROL_$M EXPECTATION_NOT_MET"; stop "control_${M}_expectation_not_met"; }
  mark "GATE_OK control_$M $(date -u +%FT%TZ)"
done
mark "DONE $(date -u +%FT%TZ)"
