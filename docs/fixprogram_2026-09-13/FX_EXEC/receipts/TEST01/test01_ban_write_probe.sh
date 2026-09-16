#!/bin/bash
# TEST-01 red/green probe: which suites can write a VENUE BAN into the real state root?
#
# THE DEFECT (FX-W6C bisect; lead 2026-09-16). `rate_budget.ban_path()` falls back to
# `state_root.paths_for(mode)["root"]/venue_ban.json` unless `LIVE_VENUE_BAN_STATE` redirects it.
# `live/tests_transport_resilience.py:662` feeds a 429 / -1003 "Too many requests" into a real
# `submit()`, and that file sets NO env redirects — so the ban lands in the shared tree. It is
# EXEC'd as a fixture by three other suites, so the affected set is not one suite but four.
# Live proof: ~/dl_quant_live/state/venue_ban.json carries
#   testnet.binancefuture.com / "Too many requests" / until_epoch null / 2026-09-13T11:58:21Z
# written during the 09-13 acceptance battery on the RUNNING tree.
#
# This probe deletes the CLONE's (untracked, test-written) copy, runs one suite, and reports
# whether the suite recreated it. It never touches ~/dl_quant_live.
set -uo pipefail
TREE=/Users/haosiyu/cc_tmp/fx_exec
BAN="$TREE/state/venue_ban.json"
RUN1=/Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/FX_EXEC/receipts/common/run1.sh
W=/Users/haosiyu/cc_tmp/fx_exec_work/new02/test01; mkdir -p "$W"
LABEL="${1:-probe}"

echo "# TEST-01 ban-write probe [$LABEL]  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "# tree head=$(git -C "$TREE" rev-parse HEAD)"
echo "# live file is NEVER touched by this probe: $(shasum -a 256 /Users/haosiyu/dl_quant_live/state/venue_ban.json 2>/dev/null | cut -c1-16) (before)"
printf '%-38s %-10s %s\n' SUITE WROTE_BAN DETAIL
for s in tests_transport_resilience tests_reduce_only_clamp tests_request_identity_unknown tests_flatten_fee_backfill; do
  rm -f "$BAN"
  bash "$RUN1" "$TREE" "live/$s.py" "$W/${LABEL}_$s.log" >/dev/null 2>&1
  rc=$?
  if [ -f "$BAN" ]; then
    hosts=$(/usr/bin/python3 -c "import json;print(','.join(json.load(open('$BAN')).get('hosts',{}).keys()))" 2>/dev/null)
    printf '%-38s %-10s rc=%s hosts=[%s]\n' "$s" "YES" "$rc" "$hosts"
  else
    printf '%-38s %-10s rc=%s\n' "$s" "no" "$rc"
  fi
done
rm -f "$BAN"
echo "# live file after: $(shasum -a 256 /Users/haosiyu/dl_quant_live/state/venue_ban.json 2>/dev/null | cut -c1-16) (must equal 'before')"
