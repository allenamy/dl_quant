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
# DO NOT reconstruct the output path from ARM: the trainer's arm name is 'T3_clamp' (the clamp mode is
# part of it), so `$K/solo/$ARM/...` pointed at a directory that never existed and the probe reported
# "produced no scores.npz" for a run that had in fact succeeded (rc=0, 282 s). Two constants that must
# agree, written in two places, drift. Read the path from the producer's own DLARCH_TRAIN_DONE line.
outdir(){ sed -n 's/.*DLARCH_TRAIN_DONE .* out=\([^ ]*\).*/\1/p' "$1" | tail -1; }
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
SOLO_DIR=$(outdir "$K/run_solo.log")
log "run A out dir (from the trainer's own line): ${SOLO_DIR:-<none announced>}"
SOLO=$(sha256sum "$SOLO_DIR/$FOLD/scores.npz" 2>/dev/null | cut -d' ' -f1)
log "run A (solo)  : rc=$RA  ${SOLO_SEC}s  scores.npz sha $SOLO"
[ -n "$SOLO" ] || { log "run A produced no scores.npz -- cannot form a reference; STOP"; exit 1; }

# ---- background load: a DIFFERENT seed, so the two runs never contend for one output dir ----
# TWO BUGS FIXED HERE, both of which silently destroyed the verdict's power on the 2026-09-25 12:28Z run:
#
# (1) THE READINESS CONDITION WAS IMPOSSIBLE. It waited for `trainers() -ge 2` BEFORE starting run B --
#     but at that moment only ONE trainer can exist (the load); run B is what makes it two. So the loop
#     burned its full 300 s timeout on a condition that could never be true, logged "load did not come
#     up", and started run B at 12:38:11 -- 38 s AFTER the load had finished at 12:37:33. Run B then ran
#     unloaded and came out FASTER than solo (250 s vs 277 s), which is the tell. Wait for `-ge 1` (the
#     load is up) and assert it, then run B makes it two.
#
# (2) ONE LOAD FOLD IS SHORTER THAN RUN B. The load fold takes ~225 s and run B ~250-280 s, so even with
#     correct sequencing the load expires mid-comparison. The load now LOOPS until run B signals done, so
#     it cannot run out underneath the measurement.
#
# And the verdict now carries EVIDENCE that it was loaded: concurrency is sampled throughout run B and
# the minimum is required to be >= 2. "I started a load" is not the same as "it was loaded the whole
# time", and only the sampled minimum can tell those apart.
log "starting background load: seed $LOAD_SEED, same arm, looping into $K/load_arm until run B is done"
rm -f "$K/runB.done"
( while [ ! -f "$K/runB.done" ]; do
    rm -rf "$K/load_arm"                 # the trainer does mkdir(exist_ok=False), so clear between passes
    run "$K/load_arm" "$LOAD_SEED" "$FOLD" "$K/run_load.log"
  done ) &
LOADPID=$!
echo "$LOADPID" > "$K/load.pid"           # record it: the only safe kill target is one I wrote down
for i in $(seq 1 60); do [ "$(trainers)" -ge 1 ] && break; sleep 5; done
LOAD_UP=$(trainers)
log "load up       : trainers=$LOAD_UP gpu_procs=$(gpu_procs) avail=$(mem_avail_gib) GiB"
if [ "$LOAD_UP" -lt 1 ]; then
  log "REFUSING to report a verdict: the load never started, so a cross-load check is not what would be measured"
  touch "$K/runB.done"; kill "$LOADPID" 2>/dev/null; exit 1
fi

# ---- concurrency sampler: proves run B was loaded FOR ITS DURATION, not just at the start ----
# CRITERION DECLARED BEFORE THE NEXT RUN (the previous one was brittle by construction): require the
# FRACTION of samples with >=2 trainers to be >= 95%, not min >= 2. Why the change is not criterion-
# shopping: the sampler starts just BEFORE run B launches, so its FIRST sample necessarily sees only the
# load's trainer -- `min >= 2` therefore cannot be satisfied even when the load is perfect, which is the
# same defect as welding an arithmetic identity to a population expectation. Measured on the 12:53Z run:
# 34/35 = 97.1% at two trainers, the single 1 being exactly that first sample, with an independent
# corroboration that the load was real (loaded 345 s vs solo 247 s = 1.40x). A fraction criterion still
# fails loudly if the load dies mid-run, which is the thing being guarded against.
( while [ ! -f "$K/runB.done" ]; do trainers >> "$K/concurrency.samples"; sleep 10; done ) &
SAMPPID=$!
echo "$SAMPPID" > "$K/sampler.pid"

# ---- run B: SAME fold, SAME seed, under load ----
B0=$(date +%s)
run "$K/loaded" "$SEED" "$FOLD" "$K/run_loaded.log"; RB=$?
B1=$(date +%s)
LOAD_SEC=$((B1-B0))
touch "$K/runB.done"
CMIN=$(sort -n "$K/concurrency.samples" 2>/dev/null | head -1)
CMAX=$(sort -n "$K/concurrency.samples" 2>/dev/null | tail -1)
CN=$(grep -c . "$K/concurrency.samples" 2>/dev/null || echo 0)
CGE2=$(awk '$1>=2' "$K/concurrency.samples" 2>/dev/null | grep -c . || echo 0)
CPCT=$(awk -v a="$CGE2" -v b="$CN" 'BEGIN{if(b>0)printf "%.1f",100*a/b; else print "0.0"}')
log "concurrency during run B: n=$CN  >=2 in $CGE2 ($CPCT%)  min=${CMIN:-?} max=${CMAX:-?}  (need >= 95% for power)"
LOADED_DIR=$(outdir "$K/run_loaded.log")
log "run B out dir (from the trainer's own line): ${LOADED_DIR:-<none announced>}"
LOADED=$(sha256sum "$LOADED_DIR/$FOLD/scores.npz" 2>/dev/null | cut -d' ' -f1)
log "run B (loaded): rc=$RB  ${LOAD_SEC}s  scores.npz sha $LOADED"

wait "$LOADPID" 2>/dev/null; kill "$SAMPPID" 2>/dev/null   # only pids this script recorded itself
log "background load loop and sampler stopped (recorded pids $LOADPID / $SAMPPID)"

# ---- verdict ----
log "solo   sha : $SOLO"
log "loaded sha : $LOADED"
if [ -n "$LOADED" ] && [ "$SOLO" = "$LOADED" ]; then V=IDENTICAL; else V=DIFFERENT; fi
if awk -v p="$CPCT" 'BEGIN{exit !(p>=95)}'; then POWER=HAS_POWER; else POWER=NO_POWER_run_B_was_not_loaded_enough; fi
log "T3_CROSSLOAD_VERDICT=$V  power=$POWER  solo=${SOLO_SEC}s loaded=${LOAD_SEC}s  slowdown=$(awk -v a=$SOLO_SEC -v b=$LOAD_SEC 'BEGIN{if(a>0)printf "%.2fx",b/a; else print "n/a"}')"
[ "$POWER" = HAS_POWER ] || log "IDENTICAL under NO_POWER means only run-to-run determinism, NOT cross-load determinism -- do not read it as the latter"
log "per-fold cost for scheduling: solo ${SOLO_SEC}s, under 2-way ${LOAD_SEC}s"
if [ "$V" = DIFFERENT ]; then
  log "DO NOT parallelise T3: bitwise reproducibility is MEASURED here, not configured (the trainer sets"
  log "only manual_seed; no cudnn.deterministic, no use_deterministic_algorithms), so a DIFFERENT result"
  log "is the expected way this can fail and it is a stop, not a warning."
fi
log "artifacts in $K (throwaway; no delivered tree was read or written)"
log "CROSSLEVEL_T3_DONE"
