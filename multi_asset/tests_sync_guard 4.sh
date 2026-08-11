#!/bin/bash
# Red/green battery for sync_to_server.sh's two-sided pre-check (0C 2026-07-27).
#
# > created 2026-07-27 | Session: 0C | 状态: permanent | 作废条件: 同步通道退役
#
# Runs the REAL script against throwaway local trees (SYNC_SRC / SYNC_DEST / SYNC_DEPLOY_LOG), so a
# case cannot pass against a copy that has drifted from the script that actually deploys.
#
# ★★ B0 IS THE CASE THAT EXISTS BECAUSE I SHIPPED THE BUG IT CATCHES.
# The overwrite half was first written matching `^>f`. On a push the itemize direction character is
# `<`, so the pattern matched NOTHING — and the check reported "✓ no existing file will be
# overwritten (0 created)" on a run where a server-side edit had been deliberately planted. A guard
# whose pattern matches nothing says exactly what a guard confirming safety says. B0 asserts the
# pattern finds SOMETHING on a pair known to differ, which is the only assertion that can tell those
# two states apart.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/sync_to_server.sh"
fails=0
ok()  { echo "  ok    $1"; echo "        red-when: $2"; }
bad() { echo "  FAIL  $1"; echo "        $2"; fails=$((fails+1)); }

run_guard() {   # $1 src, $2 dst, $3 deploylog ; echoes output, returns exit code
  SYNC_SRC="$1/" SYNC_DEST="$2" SYNC_DEPLOY_LOG="$3" bash "$SCRIPT" --check-only 2>&1
}

# ★ `cp -Rp`, not `cp -R`. Without -p the destination copies get fresh mtimes, so rsync's
# size+mtime quick check calls EVERY file changed and the fixture manufactures the very condition
# the cases are trying to isolate. B1 passed anyway on the first attempt — the files happened to
# land in the same clock second — which is worse than failing: a fixture that is right by luck
# makes the battery flaky in whichever direction the machine is fast that day.
mk() {          # $1 dir : a minimal tree the excludes do not swallow
  mkdir -p "$1/multi_asset/engine/live"
  printf 'a=1\n' > "$1/multi_asset/engine/live/mod_a.py"
  printf 'b=1\n' > "$1/multi_asset/engine/live/mod_b.py"
}

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
LOG="$T/deploy.jsonl"

# ── B1 identical trees ────────────────────────────────────────────────────────────────────────────
mk "$T/s1"; cp -Rp "$T/s1/" "$T/d1/"
OUT=$(run_guard "$T/s1" "$T/d1" "$LOG"); RC=$?
if [ $RC -eq 0 ] && echo "$OUT" | grep -q '✓ 无既存文件会被覆盖'; then
  ok "B1 identical trees -> no overwrite, exit 0" \
     "red if the guard reported phantom overwrites on a clean deployment"
else bad "B1 identical trees -> no overwrite, exit 0" "rc=$RC out=$(echo "$OUT" | tail -3)"; fi

# ── B0 ★ known-divergent pair MUST produce a non-empty list ───────────────────────────────────────
mk "$T/s0"; cp -Rp "$T/s0/" "$T/d0/"
printf '# edited ON THE SERVER and never brought back\n' >> "$T/d0/multi_asset/engine/live/mod_a.py"
OUT=$(run_guard "$T/s0" "$T/d0" "$LOG"); RC=$?
if [ $RC -eq 0 ] && echo "$OUT" | grep -q 'mod_a.py' && echo "$OUT" | grep -q '将覆盖 1 个'; then
  ok "B0 ★ a server-side edit IS listed (and does not abort)" \
     "★ THE ORIGINAL BUG: with the wrong direction character the pattern matches nothing and the \
guard prints the same '✓ nothing will be overwritten' it prints when genuinely clean"
else bad "B0 ★ a server-side edit IS listed (and does not abort)" "rc=$RC out=$(echo "$OUT" | tail -5)"; fi

# ── B2 a new local file counts as CREATED, not as an overwrite ────────────────────────────────────
mk "$T/s2"; cp -Rp "$T/s2/" "$T/d2/"
printf 'c=1\n' > "$T/s2/multi_asset/engine/live/mod_c.py"
OUT=$(run_guard "$T/s2" "$T/d2" "$LOG"); RC=$?
if [ $RC -eq 0 ] && echo "$OUT" | grep -q '✓ 无既存文件会被覆盖（新建 1 个）'; then
  ok "B2 a brand-new file is CREATED, not counted as overwritten" \
     "red if creations were folded into the overwrite list — that inflates the warning until \
nobody reads it, which is how a real overwrite hides in the noise"
else bad "B2 a brand-new file is CREATED, not counted as overwritten" "rc=$RC out=$(echo "$OUT" | tail -3)"; fi

# ── B3 the deletion half still aborts ─────────────────────────────────────────────────────────────
mk "$T/s3"; cp -Rp "$T/s3/" "$T/d3/"
printf 'only=1\n' > "$T/d3/multi_asset/engine/live/server_only.py"
OUT=$(run_guard "$T/s3" "$T/d3" "$LOG"); RC=$?
if [ $RC -eq 1 ] && echo "$OUT" | grep -q 'server_only.py'; then
  ok "B3 a server-only file still ABORTS (the original half is intact)" \
     "red if adding the second half had broken the first — the failure mode of every 'while I am \
in here' edit"
else bad "B3 a server-only file still ABORTS" "rc=$RC out=$(echo "$OUT" | tail -3)"; fi

# ── B4 both conditions at once: abort wins, and it is the destructive one ────────────────────────
mk "$T/s4"; cp -Rp "$T/s4/" "$T/d4/"
printf '# server edit\n' >> "$T/d4/multi_asset/engine/live/mod_a.py"
printf 'only=1\n' > "$T/d4/multi_asset/engine/live/server_only.py"
OUT=$(run_guard "$T/s4" "$T/d4" "$LOG"); RC=$?
if [ $RC -eq 1 ]; then
  ok "B4 deletion + overwrite together -> abort (the destructive condition wins)" \
     "red if a non-fatal warning could mask a fatal one by running first"
else bad "B4 deletion + overwrite together -> abort" "rc=$RC"; fi

# ── B5 the deploy log records the manifest BEFORE the transfer ────────────────────────────────────
mk "$T/s5"; cp -Rp "$T/s5/" "$T/d5/"
printf '# server edit\n' >> "$T/d5/multi_asset/engine/live/mod_b.py"
L5="$T/deploy5.jsonl"
SYNC_SRC="$T/s5/" SYNC_DEST="$T/d5" SYNC_DEPLOY_LOG="$L5" bash "$SCRIPT" >/dev/null 2>&1; RC=$?
GOT=$(python3 - "$L5" <<'PY' 2>/dev/null
import json,sys
d=json.loads(open(sys.argv[1]).read().splitlines()[-1])
print(f"{d['n_overwritten']}|{'mod_b.py' in ' '.join(d['overwritten'])}|{bool(d['utc'])}")
PY
)
if [ $RC -eq 0 ] && [ "$GOT" = "1|True|True" ]; then
  ok "B5 the deploy log records what was overwritten, with a timestamp" \
     "red if the manifest were written only on success — it would be missing on exactly the runs \
someone needs it for"
else bad "B5 the deploy log records what was overwritten" "rc=$RC got=$GOT"; fi

echo
[ $fails -eq 0 ] && echo "sync guard battery: all cases behaved as specified" \
                 || echo "sync guard battery: $fails FAILED"
exit $([ $fails -eq 0 ] && echo 0 || echo 1)
