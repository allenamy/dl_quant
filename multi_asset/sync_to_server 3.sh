#!/bin/bash
# Sync local multi-asset repo -> jpline training server.
# Local is source of truth; server is for training/eval only.
# NEVER touches /mnt/storage/share (read-only data).
set -euo pipefail

# ★ Overridable so the guard can be exercised against throwaway trees. The script already argues
# (see --check-only) that a guard must be safely testable; hardcoded endpoints make the only
# available test "run the real destructive thing", which is how guards end up never tested at all.
DEST="${SYNC_DEST:-jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset}"

# ── 保护：本地是唯一真相源，server 只执行 (CLAUDE.md 约束 #6)。
# --delete 只有在"服务器上没有本地缺失的文件"时才安全。若服务器上有本地没有的东西，
# 说明有人直接在服务器上改了 —— 违反原则，且同步会销毁它。预检发现即中止。
# 注意：必须用 -i (itemize)，删除行才会以 "*deleting" 开头；--out-format='%n' 不带该前缀。
# ★ ONE LIST, READ TWICE — NEVER TWO LISTS THAT AGREE TODAY (0C audit, 2026-07-27).
# The pre-check and the real sync used to carry SEPARATE hand-maintained copies of these 22
# excludes. They were byte-identical when measured, which is exactly what makes the arrangement
# dangerous: nothing enforced it, and the two failure directions are not symmetric —
#   * an exclude present only in the PRE-CHECK makes the guard blind to files the sync would
#     delete, i.e. the guard clears a destructive sync. This is the direction that loses data.
#   * an exclude present only in the REAL SYNC merely causes a false abort.
# A guard and the action it guards must read the SAME list, not two copies of it. (Same rule as
# `factor_version_registry`: reference the symbol, never restate it.)
EXCLUDES=(
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store'
  --exclude='/data/' --exclude='crypto_data/' --exclude='experiments/'
  --exclude='exports/' --exclude='/logs/' --exclude='midprice_per_day/'
  --exclude='multi_asset/exports/'
  --exclude='*.md' --exclude='/docs/' --exclude='multi_asset/handoff/'
  --exclude='*.ipynb' --exclude='*.tar.gz' --exclude='*.zip'
  --exclude='.claude/' --exclude='.cctmp/' --exclude='.pytest_cache/'
  --exclude='AGENTS.md' --exclude='.mcp.json'
)

SRC="${SYNC_SRC:-/Users/haosiyu/Desktop/quant_research/}"
# ★ ONE DRY RUN, READ THREE WAYS. Both halves of the pre-check and the overwrite manifest come from
# the SAME itemized output — running rsync twice would recreate, inside the guard, exactly the
# two-lists-that-agree-today defect the EXCLUDES array was collapsed to remove.
_DRY=$(rsync -ain --delete "${EXCLUDES[@]}" "$SRC" "$DEST/")

echo "→ 预检 (1/2)：服务器上是否存在本地缺失的文件…"
_ORPHANS=$(echo "$_DRY" | grep '^\*deleting' || true)

if [ -n "$_ORPHANS" ]; then
  echo "✗ 中止：同步会从服务器删除以下文件（本地不存在）："
  echo "$_ORPHANS" | sed 's/^\*deleting *//' | sed 's/^/    /'
  echo
  echo "  这意味着有内容只存在于服务器上，违反 CLAUDE.md #6（本地开发，server 只执行）。"
  echo "  先拉回本地并入 git 再同步。"
  exit 1
fi
echo "✓ 预检通过：服务器上无本地缺失的文件"

# ── 预检 (2/2)：对称的另一半 —— 会被【覆盖】的文件 ──────────────────────────────────────────────
# ★ WHY THIS HALF EXISTS (0C, 2026-07-27, team-lead approved).
# The half above guards DELETION: server-only files that `--delete` would destroy. It says nothing
# about OVERWRITE: a file that exists on both sides, was modified ON THE SERVER, and is about to be
# silently replaced by the local copy. The risk memory this guard was built from covers both, and
# only the louder half had been implemented — the guard followed the loudest sentence rather than
# the whole text. Found the honest way: a routine deployment transferred eight core daily-chain
# modules (build_tail / signal_loop / monitor / paper_pnl / …) that had never been individually
# verified on the server, and the pre-check was green throughout.
#
# ⇒ IT DOES NOT ABORT, DELIBERATELY. Local IS the single source of truth (CLAUDE.md #6), so
#   overwriting is the sync's whole job; aborting on it would make the normal case red and the
#   guard would be switched off within a week. What it must be is VISIBLE: if someone broke
#   "server = compute-only" and edited something there without bringing it back, this listing is
#   that change's ONE appearance before it is destroyed.
# ⇒ The list is retained in the deploy log so a deployment with count > 0 can answer, afterwards,
#   exactly what it overwrote. A warning nobody can look up later is a warning that was never given.
echo "→ 预检 (2/2)：本次同步会【覆盖】服务器上哪些既存文件…"
# ★★ THE DIRECTION CHARACTER DEPENDS ON THE TRANSPORT, AND BOTH SINGLE-CHARACTER PATTERNS ARE
# WRONG SOMEWHERE. rsync itemizes `<f` when the file is SENT to a remote host and `>f` when it is
# RECEIVED by the local host — so a push to jpline emits `<`, while a local-to-local copy (which is
# how the battery runs) emits `>`. Both mistakes were made here, in order:
#   1. `>f`  — correct locally, matched NOTHING in production. The check then printed
#              "✓ no existing file will be overwritten (0 created)" on a run with a deliberately
#              planted server-side edit. A pattern that matches nothing says exactly what a guard
#              confirming safety says.
#   2. `<f`  — correct in production, matched nothing in the battery, so the battery's B0/B2/B5
#              went red for a reason unrelated to the logic under test.
# ⇒ The direction is not information this guard wants. It wants "a file is being transferred TO the
#   destination", whichever transport carries it. Hence `[<>]`. Do not "tidy" it back to one
#   character: whichever you pick, the guard becomes silently inert on the other transport, and the
#   silence is indistinguishable from good news.
# A newly created file has ALL-'+' attribute flags; anything else is an existing file that differs
# and will be replaced.
# ★ AND THE NUMBER OF FLAG CHARACTERS IS NOT A CONSTANT. The first version matched a literal
#   `+++++++++` (nine). This rsync emits `>f+++++++` (seven), so every creation fell through to the
#   overwrite list — the third pattern defect in this one guard, after the direction character twice.
#   ⇒ Stop tuning literals: test the SHAPE. `flags ~ /^\++$/` says "every remaining flag is a plus"
#     without asserting how many there are, so it survives an rsync that reports one more or one
#     fewer attribute. A count baked into a pattern is a constant nobody will re-derive.
# ★ The filename is everything after the FIRST space, not `$2` — a path containing a space would
#   otherwise be silently truncated, and a truncated path in a warning list is worse than absent.
_ITEMS=$(echo "$_DRY" | awk '
  $1 ~ /^[<>]f/ {
    flags = substr($1, 3)
    name  = substr($0, index($0, " ") + 1)
    if (flags ~ /^\++$/) n_new++; else print "OVER " name
  }
  END { print "NEWCOUNT " n_new + 0 }')
_OVERWRITE=$(echo "$_ITEMS" | sed -n 's/^OVER //p' || true)
_CREATE_N=$(echo "$_ITEMS" | sed -n 's/^NEWCOUNT //p' || true)
_OVERWRITE_N=$(test -n "$_OVERWRITE" && echo "$_OVERWRITE" | wc -l | tr -d ' ' || echo 0)
if [ "$_OVERWRITE_N" -gt 0 ]; then
  echo "⚠ 将覆盖 $_OVERWRITE_N 个服务器上的既存文件（新建 $_CREATE_N 个，不列出）："
  echo "$_OVERWRITE" | sed 's/^/    /'
  echo "  本地是唯一真相源，覆盖是同步的本职 —— 但若其中任何一个是【只在服务器上改过、"
  echo "  从未回传】的修改，这是它被摧毁前唯一一次露面。看一眼再往下走。"
else
  echo "✓ 无既存文件会被覆盖（新建 $_CREATE_N 个）"
fi

DEPLOY_LOG="${SYNC_DEPLOY_LOG:-/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/deploy_log.jsonl}"

# --check-only: 只跑预检就退出，不执行任何同步。
# 存在理由：守卫本身必须可被安全测试。用"实跑真同步"来测守卫，等于用真实爆炸
# 测试防爆门 —— 守卫若失效，测试动作本身就是破坏。有了这个出口，测守卫时
# 守卫失效的最坏后果只是退出码不对，不会删任何东西。
if [ "${1:-}" = "--check-only" ]; then
  echo "(--check-only：不执行同步)"
  exit 0
fi


# ★ The overwrite manifest is written BEFORE the sync, not after: if the transfer dies halfway the
# evidence of what it was about to replace must already exist. A record written only on success
# is missing on exactly the runs someone will need it for.
mkdir -p "$(dirname "$DEPLOY_LOG")"
DEPLOY_LOG="$DEPLOY_LOG" OVERWRITE_N="$_OVERWRITE_N" CREATE_N="$_CREATE_N" \
OVERWRITE_LIST="$_OVERWRITE" python3 -c '
import json, os, time
files = [l.strip() for l in os.environ["OVERWRITE_LIST"].splitlines() if l.strip()]
with open(os.environ["DEPLOY_LOG"], "a") as f:
    f.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "n_overwritten": int(os.environ["OVERWRITE_N"]),
                        "n_created": int(os.environ["CREATE_N"]),
                        "overwritten": files,
                        "_why": "files that existed on the server and were replaced by the local "
                                "copy; local is the source of truth, but a server-side edit that "
                                "was never brought back appears here once, then is gone"}) + "\n")
'

rsync -avz --delete "${EXCLUDES[@]}" "$SRC" "$DEST/"

echo "✓ synced → $DEST"
