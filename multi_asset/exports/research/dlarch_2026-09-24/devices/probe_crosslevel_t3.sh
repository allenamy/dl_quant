#!/bin/sh
# probe_crosslevel_t3.sh -- does a T3 fold train BITWISE identically under 2-way GPU load?
# Run this BEFORE parallelising T3 (lead ruling 2026-09-25: T3 only after a lane frees AND after a
# T3 cross-load check). It also measures T3's per-fold wall cost, which is what turns "T3 verdict"
# into a date.
#
# THREE THINGS IT DOES DIFFERENTLY FROM probe_crosslevel.sh (the T0 one), each for a stated reason:
#
# 1. IT NEVER TOUCHES A DELIVERED TREE. The T0 probe deleted and rebuilt the delivered fold
#    T3/T0/f10_s42/202506, restoring on mismatch. Delivered trees are read-only as of lead's ruling,
#    and "restores correctly on failure" is not the same as "cannot damage". Here both runs write to
#    throwaway roots under $K, so there is nothing to restore and nothing to lose.
#
# 2. IT DOES NOT HARDCODE THE REFERENCE SHA. The T0 probe carried REF_SCORE as a literal, which is
#    only correct for one fold of one seed of one arm. Here run A (solo) PRODUCES the reference and
#    run B (loaded) is compared to it, so the device works for any fold and cannot compare against a
#    stale constant. Coupled constants drift; derive one from the other.
#
# 3. IT DOES NOT USE `pgrep -f` TO COUNT PROCESSES. My own devices/README.md §3 bans it and the T0
#    probe used it anyway: `pgrep -fc 'dlarch_train_f10.py'` self-matches when the pattern appears in
#    an ssh command line, and it missed launchers because argv order differed. Counting is done from
#    `ps -eo pid,pgid,args` filtered to the interpreter invocation, and from nvidia-smi for the device.
#
# PRECONDITION: the trainer copy under $DEV must accept --out-root. The delivered
# dlarch_train_f10.py hardcodes OUT_ROOT, and it MUST NOT be edited while any lane is running: every
# fold receipt pins the trainer's sha in `sources`, and the resume guard asserts
# old['sources'] == sources, so editing it mid-family makes the in-flight seeds fail on their next
# fold. So: copy the device dir to a probe copy, add --out-root THERE, and run this against it.
#
# usage: DEV=/workspace/dlarch_2026-09-24/probe_<ts> SEED=42 FOLD=202506 LOAD_SEED=2027 \
#        sh probe_crosslevel_t3.sh
set -u
W=/workspace/dlarch_2026-09-24
DEV="${DEV:?set DEV to the probe copy of the device dir (never the delivered tree)}"
SEED="${SEED:?}"; FOLD="${FOLD:?}"; LOAD_SEED="${LOAD_SEED:?}"
ARM=T3
K=$W/crosslevel_t3_$(date -u +%Y%m%dT%H%M%SZ)
PY=/workspace/venv/bin/python
mkdir -p "$K/solo" "$K/loaded" "$K/load_arm"
log(){ echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$K/crosslevel_t3.log"; }

# SELF-ATTRIBUTION, unconditional, before any work (same rule as dlarch_run_T0_lane.sh; news2's
# class-shaped fix). Without this the only way to find "is the probe still alive?" is a name scan, and
# `pgrep -f <pattern>` self-matches whenever the pattern sits in the watching command's own argv -- I did
# exactly that while watching this probe, and the watcher would have failed to notice a death.
MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch probe=t3_crossload started=%s dev=%s seed=%s fold=%s load_seed=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" "$DEV" "$SEED" "$FOLD" "$LOAD_SEED" > "$K/probe.pgid"

case "$DEV" in "$W/probe_"*) : ;; *) log "REFUSING: DEV=$DEV is not a probe copy under $W/probe_*"; exit 9;; esac
[ -f "$DEV/dlarch_train_f10.py" ] || { log "REFUSING: no trainer in $DEV"; exit 9; }
grep -q -- "--out-root" "$DEV/dlarch_train_f10.py" || { log "REFUSING: $DEV trainer has no --out-root; it would write into the delivered tree"; exit 9; }

trainers(){ ps -eo pid,pgid,args | awk '$3 ~ /\/python$/ && /dlarch_train_f10\.py/' | grep -c . ; }
gpu_procs(){ nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c . ; }
mem_avail_gib(){ awk 'NR==FNR{m=$1;next}/^anon /{a=$2}/^shmem /{s=$2}END{printf "%.2f",(m-a-s)/1073741824}' \
  /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.stat; }

run(){  # run <out-root> <seed> <fold> <logfile>
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 "$PY" -B "$DEV/dlarch_train_f10.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --arm "$ARM" --seed "$2" --folds "$3" --out-root "$1" >> "$4" 2>&1
}

log "=== T3 CROSS-LOAD DETERMINISM PROBE  arm=$ARM seed=$SEED fold=$FOLD load_seed=$LOAD_SEED ==="
log "dev copy      : $DEV (trainer sha $(sha256sum "$DEV/dlarch_train_f10.py" | cut -c1-16))"
log "state before  : trainers=$(trainers) gpu_procs=$(gpu_procs) avail=$(mem_avail_gib) GiB"
[ "$(trainers)" -eq 0 ] || log "NOTE: a trainer is already running; run A will NOT be solo -- read the verdict accordingly"

# ---- run A: SOLO. this also measures T3's per-fold wall cost, ungated by contention ----
A0=$(date +%s)
run "$K/solo" "$SEED" "$FOLD" "$K/run_solo.log"; RA=$?
A1=$(date +%s)
SOLO_SEC=$((A1-A0))
SOLO=$(sha256sum "$K/solo/$ARM/f10_s$SEED/$FOLD/scores.npz" 2>/dev/null | cut -d' ' -f1)
log "run A (solo)  : rc=$RA  ${SOLO_SEC}s  scores.npz sha $SOLO"
[ -n "$SOLO" ] || { log "run A produced no scores.npz -- cannot form a reference; STOP"; exit 1; }

# ---- background load: a DIFFERENT seed, so the two runs never contend for one output dir ----
log "starting background load: seed $LOAD_SEED, same arm, into $K/load_arm"
run "$K/load_arm" "$LOAD_SEED" "$FOLD" "$K/run_load.log" &
LOADPID=$!
echo "$LOADPID" > "$K/load.pid"           # record it: the only safe kill target is one I wrote down
for i in $(seq 1 60); do [ "$(trainers)" -ge 2 ] && break; sleep 5; done
log "load up       : trainers=$(trainers) gpu_procs=$(gpu_procs) avail=$(mem_avail_gib) GiB"
[ "$(trainers)" -ge 2 ] || log "WARNING: load did not come up; run B is not actually loaded -- verdict has no power"

# ---- run B: SAME fold, SAME seed, under load ----
B0=$(date +%s)
run "$K/loaded" "$SEED" "$FOLD" "$K/run_loaded.log"; RB=$?
B1=$(date +%s)
LOAD_SEC=$((B1-B0))
LOADED=$(sha256sum "$K/loaded/$ARM/f10_s$SEED/$FOLD/scores.npz" 2>/dev/null | cut -d' ' -f1)
log "run B (loaded): rc=$RB  ${LOAD_SEC}s  scores.npz sha $LOADED"

wait "$LOADPID" 2>/dev/null; log "background load finished (pid $LOADPID)"

# ---- verdict ----
log "solo   sha : $SOLO"
log "loaded sha : $LOADED"
if [ -n "$LOADED" ] && [ "$SOLO" = "$LOADED" ]; then V=IDENTICAL; else V=DIFFERENT; fi
log "T3_CROSSLOAD_VERDICT=$V  solo=${SOLO_SEC}s loaded=${LOAD_SEC}s  slowdown=$(awk -v a=$SOLO_SEC -v b=$LOAD_SEC 'BEGIN{if(a>0)printf "%.2fx",b/a; else print "n/a"}')"
log "per-fold cost for scheduling: solo ${SOLO_SEC}s, under 2-way ${LOAD_SEC}s"
if [ "$V" = DIFFERENT ]; then
  log "DO NOT parallelise T3: bitwise reproducibility is MEASURED here, not configured (the trainer sets"
  log "only manual_seed; no cudnn.deterministic, no use_deterministic_algorithms), so a DIFFERENT result"
  log "is the expected way this can fail and it is a stop, not a warning."
fi
log "artifacts in $K (throwaway; no delivered tree was read or written)"
log "CROSSLEVEL_T3_DONE"
