#!/bin/bash
# run_t7nc_real.sh — pod2 driver for the T7 real reading (lead 10:1xZ: after both controls met expectations -> G3b -> judge).
# Step 1 t7nc_g3b.py (exit 0 PASS / 2 STOP); step 2 t7nc_judge.py (reviewed, sha d915b4c3). Markers on tmpfs with read-back; terminal '^STOP ' / '^DONE '.
# The judge's stdout goes to judge.log; the marker line carries only the judge's final 'T7NC_JUDGE DONE/STOP ...' line.
set -u
D=/dev/shm/alloc_2026-09-26/t7nc; LOG=$D/real.log; PY=/workspace/venv/bin/python
IDX_SHA=2ef1685f95a75953ead9ed915057886c77fad1e2d72116af735a15fc2fe7a137
JUDGE_SHA=d915b4c3274f09cd6bc033797081a82ad8ef4bbcd2ded0f275cff62d653b1401
G3B_SHA=7ed04f2ea73f65a9689cb6ce9652e866b0125e23f0e8241e821e2b369c74af26
mark() { printf '%s\n' "$*" >> $LOG; tail -1 $LOG | grep -qxF -- "$*" || { printf 'MARK_WRITE_FAILED %s\n' "$*" >&2; exit 4; }; }
stop() { mark "STOP $1 $(date -u +%FT%TZ)"; exit 3; }
PG=$(ps -o pgid= $$ | tr -d ' '); echo "$PG" > $D/PGID_real; [ "$(cat $D/PGID_real)" = "$PG" ] || exit 9
mark "START t7nc_real $(date -u +%FT%TZ) pgid=$PG"
cd $D || stop "no_dir"
[ "$(sha256sum t7nc_judge.py | cut -d' ' -f1)" = "$JUDGE_SHA" ] || stop "judge_sha"
[ "$(sha256sum t7nc_g3b.py | cut -d' ' -f1)" = "$G3B_SHA" ] || stop "g3b_sha"
[ -e T7NC_JUDGE.json ] && stop "judge_receipt_already_exists"
E="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8"
$E nice -n 10 taskset -c 40-47 $PY -B t7nc_g3b.py $IDX_SHA > $D/g3b.log 2>&1; rc=$?
[ $rc -eq 0 ] || stop "g3b_rc_$rc"
mark "GATE_OK g3b $(tail -1 $D/g3b.log)"
$E nice -n 10 taskset -c 40-47 $PY -B t7nc_judge.py > $D/judge.log 2>&1; rc=$?
L=$(grep -E '^T7NC_JUDGE (DONE|STOP)' $D/judge.log | tail -1); [ -n "$L" ] || stop "judge_rc_${rc}_no_final_line"
[ $rc -eq 0 ] || stop "judge_rc_$rc $L"
mark "VERDICT_OK $L"
mark "DONE $(date -u +%FT%TZ)"
