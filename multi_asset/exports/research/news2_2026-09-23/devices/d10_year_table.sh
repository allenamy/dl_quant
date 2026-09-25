#!/usr/bin/env bash
# d10_year_table.sh <year> -- run the per-year event table on pod2 and bring the receipt back.
# lead: "每完成一年, 出该年的逐事件计数表(账本有 / 归档有 / 两侧费率不同 / 两侧间隔不同), 先入库再报".
# The git commit is deliberately NOT done here: a background driver committing would race the shared
# index with the other agents (an iCloud-stalled `git add` already held index.lock once today). The
# receipt is produced and copied; news2 commits it in-turn before reporting the year.
set -uo pipefail
Y="${1:?usage: d10_year_table.sh <year>}"
EXP=/dev/shm/d10_2026-09-25
REPO=/Users/haosiyu/Desktop/quant_research
DEST=$REPO/multi_asset/exports/research/news2_2026-09-23/receipts/d10_2026-09-25
scp -q $REPO/multi_asset/exports/research/news2_2026-09-23/devices/d10_year_event_table.py pod2:$EXP/devices/
ssh pod2 "nice -n 15 /workspace/venv/bin/python -B $EXP/devices/d10_year_event_table.py \
  --year $Y --zips-root $EXP/zips \
  --ledger /workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz \
  --inventory $EXP/receipts/D10_S1_ARCHIVE_INVENTORY.json \
  --out $EXP/receipts/D10_S1_YEAR_${Y}.json"
rc=$?
if [ "$rc" = "0" ]; then
  mkdir -p "$DEST"
  scp -q pod2:$EXP/receipts/D10_S1_YEAR_${Y}.json "$DEST/"
  echo "YEAR_TABLE_READY $Y -> $DEST/D10_S1_YEAR_${Y}.json (news2 commits in-turn before reporting)"
else
  echo "YEAR_TABLE_FAILED $Y rc=$rc"
fi
exit $rc
