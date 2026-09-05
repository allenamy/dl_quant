#!/bin/bash
# stage 01: paced download of 5m kline zips (prereg §1 step 1). Idempotent; re-runs only request missing files.
source /workspace/review_scratch/jpline_rebuild/lib.sh
cd $ROOT
sha256sum patched/dl_klines_paced.py logs/patches/dl_klines_paced.diff src/panel_symbols_wide.txt
for attempt in 1 2 3; do
  run env DL_RATE=4.0 DL_THREADS=8 $PY patched/dl_klines_paced.py
  last=$(grep -E "^DL_DONE" logs/01_download.log | tail -1)
  echo "attempt $attempt: $last"
  nerr=$(echo "$last" | sed -E 's/.* err ([0-9]+) .*/\1/')
  [ "$nerr" = "0" ] && break
  echo "retrying failed requests after 120 s"; sleep 120
done
grep -q "^DL_DONE" logs/01_download.log || exit 3
[ "$nerr" = "0" ] || exit 4
echo "zip files: $(find klines5m -name '*.zip' | wc -l)  404 sentinels: $(find klines5m -name '*.404' | wc -l)  bytes: $(du -sb klines5m | cut -f1)"
