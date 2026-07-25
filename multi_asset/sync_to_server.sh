#!/bin/bash
# Sync local multi-asset repo -> jpline training server.
# Local is source of truth; server is for training/eval only.
# NEVER touches /mnt/storage/share (read-only data).
set -euo pipefail

DEST="jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset"

# ── 保护：本地是唯一真相源，server 只执行 (CLAUDE.md 约束 #6)。
# --delete 只有在"服务器上没有本地缺失的文件"时才安全。若服务器上有本地没有的东西，
# 说明有人直接在服务器上改了 —— 违反原则，且同步会销毁它。预检发现即中止。
# 注意：必须用 -i (itemize)，删除行才会以 "*deleting" 开头；--out-format='%n' 不带该前缀。
echo "→ 预检：服务器上是否存在本地缺失的文件…"
_ORPHANS=$(rsync -ain --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  --exclude='/data/' --exclude='crypto_data/' --exclude='experiments/' \
  --exclude='exports/' --exclude='/logs/' --exclude='midprice_per_day/' \
  --exclude='multi_asset/exports/' \
  --exclude='*.md' --exclude='/docs/' --exclude='multi_asset/handoff/' \
  --exclude='*.ipynb' --exclude='*.tar.gz' --exclude='*.zip' \
  --exclude='.claude/' --exclude='.cctmp/' --exclude='.pytest_cache/' \
  --exclude='AGENTS.md' --exclude='.mcp.json' \
  /Users/haosiyu/Desktop/quant_research/ "$DEST/" \
  | grep '^\*deleting' || true)

if [ -n "$_ORPHANS" ]; then
  echo "✗ 中止：同步会从服务器删除以下文件（本地不存在）："
  echo "$_ORPHANS" | sed 's/^\*deleting *//' | sed 's/^/    /'
  echo
  echo "  这意味着有内容只存在于服务器上，违反 CLAUDE.md #6（本地开发，server 只执行）。"
  echo "  先拉回本地并入 git 再同步。"
  exit 1
fi
echo "✓ 预检通过：服务器上无本地缺失的文件"

# --check-only: 只跑预检就退出，不执行任何同步。
# 存在理由：守卫本身必须可被安全测试。用"实跑真同步"来测守卫，等于用真实爆炸
# 测试防爆门 —— 守卫若失效，测试动作本身就是破坏。有了这个出口，测守卫时
# 守卫失效的最坏后果只是退出码不对，不会删任何东西。
if [ "${1:-}" = "--check-only" ]; then
  echo "(--check-only：不执行同步)"
  exit 0
fi


rsync -avz --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='/data/' \
  --exclude='crypto_data/' \
  --exclude='experiments/' \
  --exclude='exports/' \
  --exclude='/logs/' \
  --exclude='midprice_per_day/' \
  --exclude='multi_asset/exports/' \
  --exclude='*.md' \
  --exclude='/docs/' \
  --exclude='multi_asset/handoff/' \
  --exclude='*.ipynb' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  --exclude='.claude/' \
  --exclude='.cctmp/' \
  --exclude='.pytest_cache/' \
  --exclude='AGENTS.md' \
  --exclude='.mcp.json' \
  /Users/haosiyu/Desktop/quant_research/ "$DEST/"

echo "✓ synced → $DEST"
