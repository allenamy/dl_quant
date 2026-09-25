#!/usr/bin/env bash
# d10_pull_driver_mac.sh -- D10 stage 1 question 2 archive pull, driven FROM THE MAC.
# Pre-registration: docs/PREREG_D10_funding_truth_audit_stage1_2026-09-25.md @ 496142901.
#
# WHY THE DRIVER IS ON THE MAC AND NOT ON POD2 -- a finding, not a preference:
# venue_quiet_window.py reads the executor's anchor log (~/dl_quant_live/state/anchor_runs.log) to test
# conditions (2) and (3). That log exists on the MAC. Run on pod2 the guard returns
#   "reason": "anchor log unreadable (FileNotFoundError) -- unknown is not open",  exit 3
# at N+65m, i.e. PERMANENTLY CLOSED, which is the guard being CORRECT ("unknown is not open"), not
# broken. The tempting fix is VENUE_QUIET_WINDOW_OVERRIDE, which would silently disable the gate for all
# pod2 work. The correct architecture is to evaluate the gate WHERE ITS EVIDENCE IS READABLE and drive the
# remote work from there. So: window checked locally, puller executed on pod2 over ssh, one month at a time.
#
# Reuses FX-PROD's puller unmodified (sha ed33dfbb...): sequential, <=5 req/s, sha of in-memory bytes plus
# the served .CHECKSUM, write-probe before first write, never overwrites, 404 recorded not retried.
# Resumable by construction, so a window boundary costs nothing.
#
# PULL ORDER frozen before the first request: YEAR-INTERLEAVED (2020-01, 2021-01, ... 2026-01, 2020-02, ...)
# so every year has coverage after seven months rather than after sixty; a partial pull is then already
# per-year informative. data.binance.vision does not consume fapi weight (the guard's docstring says so),
# but lead's "local heavy work only in the quiet window" rule still applies to a multi-hour pull.
set -uo pipefail
REPO=/Users/haosiyu/Desktop/quant_research
QW=$REPO/multi_asset/exports/research/common/venue_quiet_window.py
EXP=/dev/shm/d10_2026-09-25
LLOG=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/d10/pull_mac.log
mkdir -p "$(dirname "$LLOG")"
say() { echo "$(date -u +%H:%M:%SZ) $*" | tee -a "$LLOG"; }

MONTHS=$(python3 - <<'PY'
out = []
for m in range(1, 13):
    for y in range(2020, 2027):
        if (y, m) <= (2026, 9):
            out.append("%04d-%02d" % (y, m))
print(" ".join(out))
PY
)
say "frozen year-interleaved order, $(echo $MONTHS | wc -w | tr -d ' ') months"

for M in $MONTHS; do
  if ssh pod2 "test -s $EXP/zips/$M/MANIFEST_$M.json" 2>/dev/null; then
    say "$M already complete, skipping"; continue
  fi
  # RE-MEASURE the window before every month, on the machine that can read the anchor log.
  # Never assert it in prose; the four values go into the log.
  if ! python3 -B "$QW" --json > /tmp/d10_win_$M.json 2>&1; then
    say "WINDOW CLOSED before $M -> stopping cleanly (resumable)"
    python3 -c "import json;d=json.load(open('/tmp/d10_win_$M.json'));print('   now=%s open=%s remaining=%s reason=%s'%(d['now_utc'],d['open'],d['remaining_min'],d['reason']))" | tee -a "$LLOG"
    exit 0
  fi
  REM=$(python3 -c "import json;print(int(json.load(open('/tmp/d10_win_$M.json'))['remaining_min']))")
  NOW=$(python3 -c "import json;print(json.load(open('/tmp/d10_win_$M.json'))['now_utc'])")
  if [ "$REM" -lt 8 ]; then say "only ${REM} min left -> stopping before $M (resumable)"; exit 0; fi
  say "$M START  window now=$NOW open=True remaining=${REM}min"
  scp -q /tmp/d10_win_$M.json pod2:$EXP/logs/window_$M.json
  t0=$(date +%s)
  if ! ssh pod2 "nice -n 10 /workspace/venv/bin/python -B $EXP/devices/p9_pull_monthly_funding_zips.py $M /workspace/fx_prod_p9/symbols_for_zip_pull.txt $EXP/zips/$M >> $EXP/logs/pull_$M.log 2>&1"; then
    say "$M PULL FAILED -- stopping, not retrying"
    ssh pod2 "tail -5 $EXP/logs/pull_$M.log" | tee -a "$LLOG"
    exit 1
  fi
  t1=$(date +%s)
  SUM=$(ssh pod2 "/workspace/venv/bin/python -c \"
import json,collections
m=json.load(open('$EXP/zips/$M/MANIFEST_$M.json'))
c=collections.Counter(str(v.get('status')) for v in m.values())
rows=sum(v.get('rows') or 0 for v in m.values())
print('symbols=%d statuses=%s rows=%d'%(len(m),dict(c),rows))\"")
  say "$M DONE in $(( t1 - t0 ))s  $SUM"
done
say "ALL_MONTHS_DONE"
