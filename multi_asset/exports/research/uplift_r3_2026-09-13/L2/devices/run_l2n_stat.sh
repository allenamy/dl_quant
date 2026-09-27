#!/bin/bash
# run_l2n_stat.sh — EXECUTOR for S1 steps 4-6 (AMENDMENT_L2_NC_population_2026-09-27 §5): waits for the network executor's DONE, then
# build -> fit -> judge RESOLUTION (stop unless RESOLUTION_OK) -> judge MAIN. Markers on tmpfs with read-back; terminal '^STOP ' / '^DONE '.
set -u
D=/workspace/uplift_r3_2026-09-13/L2/devices; S=/dev/shm/alloc_2026-09-26/l2n; LOG=$S/l2n_stat.log; NETLOG=$S/l2n_net.log; PY=/workspace/venv/bin/python
mkdir -p $S || exit 9
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $S/PGID_stat; [ "$(cat $S/PGID_stat)" = "$PG" ] || exit 9
mark "START l2n_stat $(date -u +%FT%TZ) pgid=$PG"
NETPG=$(cat $S/PGID_net)
until grep -qE '^(DONE|STOP) ' $NETLOG; do
  ps -eo pgid= | tr -d ' ' | grep -qx "$NETPG" || { grep -qE '^(DONE|STOP) ' $NETLOG || stop "net_executor_gone_without_marker"; }
  sleep 60
done
grep -q '^STOP ' $NETLOG && stop "net_executor_stopped"
mark "NET_DONE_SEEN $(date -u +%FT%TZ)"
W=PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS
E="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8"
cd $D || stop "no_devices"
run() { $E nice -n 10 taskset -c 48-55 $PY -B "$@"; }
run l2n_build.py $W > $S/l2n_build.log 2>&1 || stop "build_rc"; grep -q '^L2N_BUILD DONE' $S/l2n_build.log || stop "build_done_missing"; mark "GATE_OK build"
run l2n_fit.py $W > $S/l2n_fit.log 2>&1 || stop "fit_rc"; grep -q '^L2N_FIT DONE' $S/l2n_fit.log || stop "fit_done_missing"; mark "GATE_OK fit"
run l2n_judge.py $W RESOLUTION > $S/l2n_judge_RESOLUTION.log 2>&1 || stop "judge_resolution_rc"
grep -q 'VERDICT=RESOLUTION_OK' $S/l2n_judge_RESOLUTION.log || stop "RESOLUTION_FAIL_S1_stops"
mark "GATE_OK resolution $(tail -1 $S/l2n_judge_RESOLUTION.log)"
run l2n_judge.py $W MAIN > $S/l2n_judge_MAIN.log 2>&1 || stop "judge_main_rc"
mark "VERDICT_OK $(tail -1 $S/l2n_judge_MAIN.log)"
mark "DONE $(date -u +%FT%TZ)"
