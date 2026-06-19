#!/bin/bash
# Sync local multi-asset repo -> jpline training server.
# Local is source of truth; server is for training/eval only.
# NEVER touches /mnt/storage/share (read-only data).
set -euo pipefail

DEST="jpline:/mnt/storage/private/work_hsy/quant_research_multi_asset"

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
  /Users/haosiyu/Desktop/quant_research/ "$DEST/"

echo "✓ synced → $DEST"
