#!/usr/bin/env bash
# dlarch_run_T0_family.sh — T0 x 8 seeds x 23 folds, strictly SEQUENTIAL (never two on the GPU at once).
# PREREG docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md revision 9 (lead: S before L; the 8 T0 seeds are also
# fresh's "model sampling family"). Seeds are pinned by DECISION_RULE ... 038e8e78f revision 1.
# After EACH seed it prints the artifact path + sha256 so fresh can reference a family member immediately,
# and it re-checks the GPU is not being used by anyone else before starting the next seed.
#
# ── R25-09 (independent review 2026-09-25, reviewed bytes archived as
#    dlarch_run_T0_family.REVIEWED_5cdca606.sh). THREE defects, all fixed below:
#
#    1 A WAIT THAT CANNOT BLOCK. `mem_wait` ended with "proceeding anyway" + `return 0`, so a permanent
#      0 GiB exhaustion PASSED the gate. The GPU yield loop was worse: on timeout it simply fell out of
#      the `for` and carried on WITH NO MESSAGE AT ALL. A wait loop has exactly two legitimate exits --
#      satisfied, or REFUSED BY NAME -- and "fell through" is not one of them.
#      The correct pattern already exists in this campaign: dlarch_chain_run.py's engine gate asserts
#      `time.monotonic() - t0 < max_wait` and states that an unreadable reading is NOT a pass. Copied.
#    2 A FAILED QUERY READ AS GOOD NEWS. `OTHER=$(nvidia-smi ... 2>/dev/null | wc -l)` returns 0 when
#      nvidia-smi FAILS, and 0 means "GPU free". Same class as the waiter that turned an unreadable
#      count into the datum 0. Now fail-closed: a query that does not succeed is NOT a free GPU.
#    3 rc 137 ASSUMED TO BE OOM. 137 is SIGKILL from ANY sender -- including another agent's pattern
#      kill, which has happened on this host. Retrying a kill that was not an OOM re-runs work someone
#      deliberately stopped. The cgroup oom_kill counter is now read BEFORE and AFTER, and the retry is
#      gated on a POSITIVE DELTA; a 137 with delta 0 is named SIGKILL_NOT_ATTRIBUTABLE_TO_OOM and stops.
#
#    Plus a scheduling lock (atomic mkdir): two runs of THIS script can otherwise both observe a free
#    GPU in the same instant and both start. The lock is released on any exit path.
# ─────────────────────────────────────────────────────────────────────────────────────────────────────
set -uo pipefail
EXP=/workspace/dlarch_2026-09-24
D=$EXP
SEEDS="42 2027 7 11 23 101 3 5"
LOG=$EXP/T0_family.log
GUARD=$EXP/receipts/T0_FAMILY_GUARD.jsonl
LOCK=$EXP/lane_claims/t0_family.lock
MEM_NEED_GIB=8
WAIT_TRIES=240            # x 30 s = 2 h
WAIT_SLEEP=30

say(){ echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$LOG"; }
guard(){ mkdir -p "$(dirname "$GUARD")"; printf '{"utc":"%s","event":"%s","detail":"%s"}\n' \
         "$(date -u +%FT%TZ)" "$1" "$2" >> "$GUARD"; }
# A named refusal is the ONLY non-satisfied exit from a wait. It is loud, it is in a receipt, and it
# stops the run -- it never returns success.
refuse(){ say "REFUSING: $1"; guard "REFUSED" "$1"; exit 3; }

oom_kills(){ awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events 2>/dev/null || echo NA; }
memfree_gib(){ awk 'NR==FNR{m=$1;next}{printf "%.2f", (m-$1)/1073741824}' /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current; }

# FAIL-CLOSED GPU predicate: prints "free", "busy:<n>", or "unreadable". Never conflates the last two.
gpu_state(){
  local out rc
  out=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null); rc=$?
  if [ $rc -ne 0 ]; then echo "unreadable"; return; fi
  local n; n=$(printf '%s' "$out" | grep -c '[0-9]')
  if [ "$n" -eq 0 ]; then echo "free"; else echo "busy:$n"; fi
}

# THE ONE WAIT PRIMITIVE. Every wait in this script goes through it, so a wait added tomorrow inherits
# the named-refusal contract instead of re-inventing a silent fall-through.
# usage: wait_for <name> <predicate-command> <need-description>
wait_for(){
  local name="$1" pred="$2" need="$3" i
  for i in $(seq 1 $WAIT_TRIES); do
    if eval "$pred"; then
      [ "$i" -gt 1 ] && say "  $name: satisfied after $(( (i-1) * WAIT_SLEEP ))s"
      guard "SATISFIED" "$name after $(( (i-1) * WAIT_SLEEP ))s"
      return 0
    fi
    [ "$i" -eq 1 ] && { say "  $name: waiting ($need)"; guard "WAITING" "$name ($need)"; }
    sleep $WAIT_SLEEP
  done
  refuse "$name never satisfied after $(( WAIT_TRIES * WAIT_SLEEP ))s ($need). NOT proceeding: a wait that proceeds anyway is not a gate."
}

mem_ok(){ awk -v f="$(memfree_gib)" -v n="$MEM_NEED_GIB" 'BEGIN{exit !(f+0>=n+0)}'; }

# THE 137 attribution rule, as a function, because the selftest must reach THE CODE THE BRANCH RUNS --
# a test that re-implements the comparison proves the rule and nothing about the wiring.
# prints IS_OOM | NOT_OOM | UNDECIDABLE
attribute_sigkill(){
  if [ "$1" = NA ] || [ "$2" = NA ]; then echo UNDECIDABLE
  elif [ "$2" -gt "$1" ]; then echo IS_OOM
  else echo NOT_OOM; fi
}
gpu_ok(){ [ "$(gpu_state)" = "free" ]; }        # "unreadable" is NOT ok -- fail closed

# ── SELFTEST. Exercises the guards IN THIS FILE (not a copy of them), then exits. Runs no training and
# touches no GPU. `--selftest` is the whole argument list, so a real run cannot accidentally enter it.
if [ "${1:-}" = "--selftest" ]; then
  fail=0
  ck(){ if [ "$2" = "$3" ]; then echo "  PASS $1 ($2)"; else echo "  FAIL $1: got '$2' want '$3'"; fail=1; fi; }

  echo "== gpu_state returns one of the three named states, never a bare count =="
  st=$(gpu_state); case "$st" in free|busy:*|unreadable) echo "  PASS gpu_state=$st";; *) echo "  FAIL gpu_state=$st"; fail=1;; esac

  echo "== a FAILED query is 'unreadable', not 'free' (the defect: wc -l made it 0 == free) =="
  ck "nvidia-smi absent" "$(PATH=/nonexistent gpu_state)" "unreadable"
  ck "unreadable is not gpu_ok" "$(PATH=/nonexistent gpu_ok && echo ok || echo blocked)" "blocked"

  echo "== GREEN BASELINE: a satisfiable wait must return 0 (a wait that never passes hides min/max bugs) =="
  WAIT_TRIES=2 WAIT_SLEEP=1 ck "wait_for(true)" "$(wait_for probe_true true "always true" >/dev/null 2>&1 && echo 0 || echo nonzero)" "0"

  echo "== REFUSAL: an unsatisfiable wait must exit 3 by name, NOT return success =="
  out=$( (WAIT_TRIES=1 WAIT_SLEEP=1 GUARD=/dev/null LOG=/dev/null wait_for probe_false false "never true") 2>&1 ); rc=$?
  ck "wait_for(false) exit code" "$rc" "3"
  case "$out" in *REFUSING*"not a gate"*) echo "  PASS refusal is named";; *) echo "  FAIL refusal text: $out"; fail=1;; esac

  echo "== 137 attribution: only a POSITIVE oom_kill delta may be called an OOM =="
  echo "   (calls attribute_sigkill, the SAME function the rc=137 branch calls -- not a copy of the rule)"
  ck "delta +1"       "$(attribute_sigkill 3 4)"   "IS_OOM"
  ck "delta 0"        "$(attribute_sigkill 4 4)"   "NOT_OOM"
  ck "counter absent" "$(attribute_sigkill NA NA)" "UNDECIDABLE"
  ck "branch retries ONLY on IS_OOM" "$(for pair in '3 4' '4 4' 'NA NA'; do set -- $pair; case "$(attribute_sigkill $1 $2)" in IS_OOM) printf retry;; *) printf stop;; esac; done)" "retrystopstop"

  echo "== scheduling lock: a second claim must be refused =="
  T=$(mktemp -d); LOCK="$T/l"
  mkdir "$LOCK" 2>/dev/null && echo "  PASS first claim taken" || { echo "  FAIL first claim"; fail=1; }
  mkdir "$LOCK" 2>/dev/null && { echo "  FAIL second claim succeeded"; fail=1; } || echo "  PASS second claim refused"
  rm -rf "$T"

  echo "SELFTEST $([ $fail -eq 0 ] && echo ALL_PASS || echo HAS_FAILURES)"
  exit $fail
fi

# ── scheduling lock: atomic, and released on every exit path
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  say "REFUSING: another run of this script holds $LOCK (started $(cat "$LOCK/started" 2>/dev/null || echo '?'))"
  guard "REFUSED" "scheduling lock held"
  exit 4
fi
date -u +%FT%TZ > "$LOCK/started"; echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

say "=== T0 FAMILY START (8 seeds x 23 folds, sequential) ==="
for S in $SEEDS; do
  # yield to anyone else holding the GPU (news2 / fresh have priority)
  wait_for "gpu_free(seed $S)" gpu_ok "GPU state is $(gpu_state); need free. An unreadable query counts as NOT free."
  wait_for "memory(seed $S)"   mem_ok "$(memfree_gib) GiB free, need $MEM_NEED_GIB"
  OOM_BEFORE=$(oom_kills)
  say "seed $S: start  gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader)  mem_free=$(memfree_gib) GiB  oom_kill_so_far=$OOM_BEFORE"
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 /workspace/venv/bin/python -B "$D/dlarch_train_f10.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
      > "$EXP/logs_T0_s$S.log" 2>&1
  RC=$?
  if [ $RC -ne 0 ]; then
    OOM_AFTER=$(oom_kills)
    say "seed $S: FAILED rc=$RC  oom_kill before=$OOM_BEFORE after=$OOM_AFTER  mem_free=$(memfree_gib) GiB"
    tail -5 "$EXP/logs_T0_s$S.log" | tee -a "$LOG"
    if [ $RC -eq 137 ]; then
      # 137 is SIGKILL from ANY sender. Only a POSITIVE cgroup oom_kill delta makes it an OOM.
      ATTRIB=$(attribute_sigkill "$OOM_BEFORE" "$OOM_AFTER")
      if [ "$ATTRIB" = UNDECIDABLE ]; then
        guard "SIGKILL_OOM_UNDECIDABLE" "seed $S: cgroup memory.events unreadable, cannot attribute 137"
        say "seed $S: rc=137 but the oom_kill counter is unreadable -- NOT attributing it to OOM, NOT retrying"
      elif [ "$ATTRIB" = IS_OOM ]; then
        guard "SIGKILL_IS_OOM" "seed $S: oom_kill $OOM_BEFORE -> $OOM_AFTER"
        say "seed $S: rc=137 WITH oom_kill delta $((OOM_AFTER-OOM_BEFORE)) -- genuine OOM, waiting for headroom and retrying ONCE (per-fold resume keeps finished folds)"
        MEM_NEED_GIB=12 wait_for "memory(retry seed $S)" mem_ok "need 12 GiB before a retry"
        env -i PATH=/usr/bin:/bin HOME=/root nice -n 5 /workspace/venv/bin/python -B "$D/dlarch_train_f10.py" \
            --env-whitelist PATH,HOME,LC_CTYPE --arm T0 --seed "$S" --folds all \
            >> "$EXP/logs_T0_s$S.log" 2>&1
        RC=$?
        say "seed $S: retry rc=$RC"
      else
        # Someone else killed it. Retrying would re-run work that was deliberately stopped.
        guard "SIGKILL_NOT_ATTRIBUTABLE_TO_OOM" "seed $S: oom_kill unchanged at $OOM_AFTER"
        say "seed $S: rc=137 but oom_kill did NOT change ($OOM_AFTER) -- this was a SIGKILL from something else, NOT an OOM. Not retrying; a kill someone else issued must not be silently undone."
      fi
    fi
    [ $RC -ne 0 ] && { say "seed $S: giving up, stopping the family run"; guard "STOP" "seed $S rc=$RC"; exit $RC; }
  fi
  OOF=$EXP/T3/T0/f10_s$S/F10_OOF.npz
  TR=$EXP/T3/T0/f10_s$S/TRAIN_RECEIPT.json
  say "seed $S: DONE  oof=$OOF  oof_sha256=$(sha256sum "$OOF" | cut -d' ' -f1)  receipt_sha256=$(sha256sum "$TR" | cut -d' ' -f1)  folds=$(/workspace/venv/bin/python -c "import json;print(len(json.load(open('$TR'))['folds']))")"
done
say "=== T0 FAMILY ALL DONE ==="
guard "ALL_DONE" "8 seeds"
