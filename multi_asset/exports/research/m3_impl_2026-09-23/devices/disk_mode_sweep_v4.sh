#!/bin/bash
# Disk-independence sweep: the suites that derive fixtures from the REAL config/book.json must be green whatever the operator sets
# beta_overlay.mode to. Temporarily rewrites ONLY the clone's config/book.json beta_overlay.mode, restores it byte for byte after.
set -u
M3=$HOME/cc_tmp/m3_impl_20260923; E=$M3/exec_b7; OUT=$M3/targeted/disk_sweep_v4; mkdir -p "$OUT"
cp "$E/config/book.json" "$OUT/book.json.orig"
ORIG_SHA=$(shasum -a 256 "$E/config/book.json" | cut -c1-64)
SUITES="live/tests_external_book.py live/tests_gross_ladder_retired.py live/tests_per_name_stop.py live/tests_signal_and_loop.py live/tests_beta_overlay.py"
for mode in off shadow on; do
  /usr/bin/python3 - "$OUT/book.json.orig" "$E/config/book.json" "$mode" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["beta_overlay"]["mode"] = sys.argv[3]
open(sys.argv[2], "w").write(json.dumps(d, ensure_ascii=False, indent=1))
PY
  for s in $SUITES; do
    log="$OUT/${mode}__$(basename $s .py).log"
    ( cd "$E/live" && /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=$HOME LIVE_MODE=DRY_RUN PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 nice -n 10 /usr/bin/python3 "$(basename $s)" ) > "$log" 2>&1
    echo "disk_mode=$mode $s EXIT=$?"
  done
done
cp "$OUT/book.json.orig" "$E/config/book.json"
[ "$(shasum -a 256 "$E/config/book.json" | cut -c1-64)" = "$ORIG_SHA" ] && echo "config restored byte-identical" || echo "CONFIG NOT RESTORED"
