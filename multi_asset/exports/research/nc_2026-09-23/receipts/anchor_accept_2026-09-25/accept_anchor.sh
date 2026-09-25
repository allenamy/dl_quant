#!/bin/zsh
# per-anchor acceptance (read-only): inspect_anchor, B0 version probe, selfcheck (production is still m3_beta_v1), B4/B5/B6 pooled, freshness.
A=${1:?anchor}; OUT=${2:?out file}
QR=~/Desktop/quant_research; RC=$QR/multi_asset/exports/research/nc_2026-09-23; PKG=~/cc_tmp/nc_20260923/package_NC
{
echo "## inspect_anchor.py $A $(date -u +%T)"; /usr/bin/python3 $QR/multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py $A; echo "inspect rc=$?"
echo "## B0 version probe $(date -u +%T)"; /usr/bin/python3 ~/cc_tmp/nc_20260923/src/nc_version_probe.py --out /dev/null first-anchor $PKG $A | grep -E "^  (BAD|OK)|VERSION_PROBE"; echo "probe rc=${pipestatus[1]}"
echo "## B7(b) selfcheck [v1 clipped input: production still m3_beta_v1] $(date -u +%T)"; ~/wide_shadow/venv/bin/python -B $RC/devices/nc_m3_selfcheck.py $PKG $A --expect-version m3_beta_v1 | grep -E "BAD|M3_SELFCHECK|B7v2 \(ii\)|c3 "; echo "selfcheck rc=${pipestatus[1]}"
echo "## B5 snapshot / parity"; ls ~/wide_shadow/state/snap/$A | tr '\n' ' '; echo; grep "parity $A " ~/wide_shadow/state/snap/parity.log | tail -1
echo "## B6 dashboard / anchor_report"; tail -1 ~/regime_dash/regime_dash.jsonl | /usr/bin/python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print('B6 last row', d.get('anchor_ts') or d.get('anchor_utc'), d.get('w3_masked_king'), d.get('w3_masked_fund'))"
echo "## B4 + B6 anchor_report (pooled)"; /usr/bin/python3 $RC/devices/nc_b4_pooled.py $A; echo "b4 rc=$?"
echo "## watchdog state"; /usr/bin/python3 -c "import json; d=json.load(open('$HOME/dl_quant_live/state/live/watchdog/state.json')); print({k: d.get(k) for k in ('reduce_only','tripped_at','_mode')})"
echo "## forward-log freshness $(date -u +%T)"; /usr/bin/python3 $RC/devices/nc_forward_freshness.py ~/parabolic_onset_forward_short/run_log.jsonl $QR/multi_asset/exports/live/parabolic_onset_forward/run_log.jsonl; echo "freshness rc=$?"
echo "DONE $(date -u +%T)"
} > $OUT 2>&1
