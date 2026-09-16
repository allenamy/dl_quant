#!/bin/bash
# FX-EXEC2 full battery runner — every precondition of the FIXPROGRAM §8 / §14.1 battery rule, checked and RECORDED
# rather than remembered. Refuses rather than proceeds when any of them fails.
#
# §14.1 restated the rule by TRANSITIVE CLOSURE: any suite that directly or indirectly runs run_acceptance.sh, or
# makes any venue request, is bound by the window and the lock. run_acceptance.sh is the whole battery, so this
# script is squarely inside it.
#
#   1. window        N+65min .. N+3h15m for anchors at 00/04/08/12/16/20Z
#   2. the LIVE anchor of that slot has actually finished   <- stronger than the window alone, and the reason the
#                                                              09-16 03:16Z incident mattered: the window is a proxy
#                                                              for "the anchor is not running", so check the thing
#   3. BATTERY.lock  taken atomically (set -o noclobber), released on exit including on failure
#   4. no .env in the clone, LIVE_MODE unset or DRY_RUN
#   5. state/ clean before; restored after, deleting ONLY files the battery itself created
#   6. request weight recorded from the clone's own rate_budget lines
#
# Usage: run_battery_fx_exec2.sh <clone> <live_anchor_runs.log> <out_dir> [--force-window-reason "<why>"]
set -u
CLONE="$1"; LIVELOG="$2"; OUT="$3"; shift 3 || true
LOCK=/Users/haosiyu/cc_tmp/BATTERY.lock
mkdir -p "$OUT"
STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
LOG="$OUT/battery_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

say() { echo "[$(date -u '+%H:%M:%SZ')] $*"; }
fail() { say "REFUSED: $*"; exit 2; }

say "clone=$CLONE"
say "head=$(git -C "$CLONE" rev-parse HEAD)  branch=$(git -C "$CLONE" rev-parse --abbrev-ref HEAD)"

# ── 1. window ────────────────────────────────────────────────────────────────────────────────
NOW=$(date -u '+%s')
SLOT=$(( NOW / 14400 * 14400 ))
OFF=$(( NOW - SLOT ))
say "now=$(date -u -r $NOW '+%Y-%m-%dT%H:%M:%SZ') slot=$(date -u -r $SLOT '+%H:%MZ') offset=${OFF}s (window 3900..11700)"
if [ "$OFF" -lt 3900 ] || [ "$OFF" -gt 11700 ]; then
  fail "outside the battery window (N+65min..N+3h15m); offset ${OFF}s"
fi

# ── 2. the live anchor of this slot has finished ─────────────────────────────────────────────
SLOT_HH=$(date -u -r $SLOT '+%Y-%m-%dT%H')
if [ -r "$LIVELOG" ]; then
  LAST=$(grep -n 'anchor done' "$LIVELOG" | tail -1 | cut -d: -f2- | awk '{print $1}')
  say "live log last 'anchor done' at: ${LAST:-<none>}"
  LAST_S=$(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "${LAST%Z}Z" '+%s' 2>/dev/null || echo 0)
  if [ "$LAST_S" -lt "$SLOT" ]; then
    fail "the live ${SLOT_HH}Z anchor has not printed 'anchor done' yet (last done ${LAST:-none}) — the window is a proxy for this, and this is the thing"
  fi
else
  fail "cannot read the live anchor log at $LIVELOG — refusing rather than assuming the anchor is done"
fi

# ── 3. lock ──────────────────────────────────────────────────────────────────────────────────
set -o noclobber
if ! { echo "fx-exec2 pid=$$ started=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$LOCK"; } 2>/dev/null; then
  fail "BATTERY.lock is held: $(cat "$LOCK" 2>/dev/null)"
fi
set +o noclobber
trap 'rm -f "$LOCK"; say "lock released"' EXIT
say "lock taken: $LOCK"

# ── 4. credentials and mode ──────────────────────────────────────────────────────────────────
[ -e "$CLONE/.env" ] && fail ".env exists in the clone"
case "${LIVE_MODE:-}" in ""|DRY_RUN) : ;; *) fail "LIVE_MODE=${LIVE_MODE} is not DRY_RUN" ;; esac
[ -n "${BINANCE_API_KEY:-}" ] && fail "BINANCE_API_KEY is set in this environment"
say "no .env · LIVE_MODE=${LIVE_MODE:-<unset, defaults DRY_RUN>} · no BINANCE_API_KEY"

# ── 5. state/ baseline ───────────────────────────────────────────────────────────────────────
git -C "$CLONE" status --porcelain state > "$OUT/state_before_${STAMP}.txt"
BEFORE_N=$(wc -l < "$OUT/state_before_${STAMP}.txt" | tr -d ' ')
say "state/ dirty entries before: $BEFORE_N (expect 0)"
[ "$BEFORE_N" != "0" ] && say "WARNING: state/ was already dirty before this battery; the restore below will not invent a clean baseline"
( cd "$CLONE" && find state -type f | sort ) > "$OUT/state_files_before_${STAMP}.txt"

# ── 6. run ───────────────────────────────────────────────────────────────────────────────────
say "running run_acceptance.sh ..."
( cd "$CLONE" && /bin/bash run_acceptance.sh ) > "$OUT/acceptance_${STAMP}.log" 2>&1
RC=$?
say "run_acceptance.sh rc=$RC"
grep -cE '^(PASS|FAIL|OK|rc=)' "$OUT/acceptance_${STAMP}.log" >/dev/null 2>&1 || true
say "--- summary lines ---"
tail -25 "$OUT/acceptance_${STAMP}.log"

# ── request weight actually spent ────────────────────────────────────────────────────────────
say "--- request weight recorded by the clone during this battery ---"
grep -hoE 'rate_budget: peak/min weight=[0-9]+[^|]*' "$CLONE"/state/anchor_runs.log 2>/dev/null | tail -3 \
  | tee "$OUT/request_weight_${STAMP}.txt" || say "(no rate_budget line written by this battery)"
grep -hoE 'venue_rate:[^|]*HEADROOM[^|]*' "$CLONE"/state/anchor_runs.log 2>/dev/null | tail -3 \
  | tee -a "$OUT/request_weight_${STAMP}.txt" || true

# ── 7. restore state/ ────────────────────────────────────────────────────────────────────────
say "--- restoring state/ ---"
git -C "$CLONE" status --porcelain state > "$OUT/state_after_${STAMP}.txt"
say "state/ dirty entries after: $(wc -l < "$OUT/state_after_${STAMP}.txt" | tr -d ' ')"
git -C "$CLONE" checkout -- state
( cd "$CLONE" && find state -type f | sort ) > "$OUT/state_files_after_${STAMP}.txt"
# delete ONLY files this battery created; never `git clean`, which would take pre-existing untracked evidence too
comm -13 "$OUT/state_files_before_${STAMP}.txt" "$OUT/state_files_after_${STAMP}.txt" > "$OUT/state_new_${STAMP}.txt"
NEW_N=$(wc -l < "$OUT/state_new_${STAMP}.txt" | tr -d ' ')
say "files created under state/ by this battery: $NEW_N (deleting exactly these)"
while IFS= read -r f; do [ -n "$f" ] && rm -f "$CLONE/$f"; done < "$OUT/state_new_${STAMP}.txt"
FINAL=$(git -C "$CLONE" status --porcelain state | wc -l | tr -d ' ')
say "state/ dirty entries after restore: $FINAL (expect 0)"
say "DONE rc=$RC"
exit $RC
