#!/bin/bash
# run_l2n_net.sh — EXECUTOR for S1 steps 2-3 (AMENDMENT_L2_NC_population_2026-09-27 §5): REPULL then full CHECKSUM (network, public archive
# only). Markers on tmpfs with read-back (E-0926-E); terminal '^STOP ' or '^DONE '. L2 run discipline: env -i whitelist, nice 10, 8 cores.
set -u
D=/workspace/uplift_r3_2026-09-13/L2/devices; S=/dev/shm/alloc_2026-09-26/l2n; LOG=$S/l2n_net.log; PY=/workspace/venv/bin/python
mkdir -p $S || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $S/PGID_net; [ "$(cat $S/PGID_net)" = "$PG" ] || exit 9
mark "START l2n_net $(date -u +%FT%TZ) pgid=$PG"
W=PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS
E="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8"
cd $D || stop "no_devices"
for ph in REPULL CHECKSUM; do
  $E nice -n 10 taskset -c 48-55 $PY -B l2n_pull_verify.py $W $ph > $S/l2n_$ph.log 2>&1 || stop "${ph}_rc"
  grep -q "^L2N_$ph DONE" $S/l2n_$ph.log || stop "${ph}_done_missing"
  mark "GATE_OK $ph $(tail -1 $S/l2n_$ph.log | cut -c1-300)"
done
mark "DONE $(date -u +%FT%TZ)"
