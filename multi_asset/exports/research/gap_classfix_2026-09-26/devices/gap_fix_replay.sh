#!/bin/bash
# gap_fix_replay.sh (integ 2026-09-26) = the lead's gap_arm_replay.sh (itself combo_parity_replay.sh) with: arg 5 CODE current|patched (patched = the
# gap-class-fix tree's combo_stage.py + prev_state.py copied into the SANDBOX copy only), the hook gap_fix_hook.py, and no archived-parity
# compare (verdicts across sandboxes are gap_fix_judge.py's). usage: gap_fix_replay.sh <A> <unused> <sandbox root> <arm> <current|patched> [tree]
# FP3 item C part 2 (2026-09-17): production whole-book PARITY for one anchor. Rebuilds the producer's world for anchor A in an isolated directory from
# (i) the current producer tree (code, xfer files, shadow_bundle; NOT the live mini cache — combo_stage skips the full-tail 171 pipeline when mini/data targets already reach A, so a replay of an older anchor would reuse features built in a later 40-day window (found 2026-09-18 re-verification: 1e-4 drift on 12Z/16Z/20Z, exact only on the newest anchor); excluded ⇒ rebuilt from the snapshot rolling.npz, per-anchor state files state/weights/<A-4h>.npz + fea171/state_H_*_<A-4h>.npz),
# (ii) the rolling-state snapshot state/snap/<A>/ (aux.json, rolling.npz, leg_returns_live.json, generation.json — the files combo_stage read for A), and
# (iii) the archived pre-combo king file target_live_king/<A>.json (what combo_stage read, validated and backed up before rewriting);
# runs combo_stage.py exactly as the daemon does (COMBO_LIVE=1) but with COMBO_LIVE_DIR pointing into the sandbox (rehearsal branch: the production
# target_live is never touched; the pager is a stub that records), then compares the replayed target with the archived target_live/<A>.json.
# usage: combo_parity_replay.sh <anchor_ts> <out_receipt.json> [sandbox_root]     exit 0 = PARITY, 2 = MISMATCH, 3 = cannot replay (named)
set -uo pipefail
A=${1:?anchor_ts}; OUT=${2:?receipt}; SBR=${3:?sbr}; ARM=${4:?arm}; CODE=${5:?code current|patched}; TREE=${6:-}; WS="${WIDE_SHADOW_HOME:-$HOME/wide_shadow}"; LIVE_REPO="${DL_QUANT_LIVE_ROOT:-$HOME/dl_quant_live}"; SNAP="$WS/state/snap/$A"; HERE="$HOME/wide_shadow/fea171/combosnap"; HOOKDIR=$(cd "$(dirname "$0")" && pwd -P)
# Refuse unsupported isolation and dangerous deletion targets before any copy/write.
[ "$(/usr/bin/uname -s)" = Darwin ] && [ -x /usr/bin/sandbox-exec ] || { echo "UNAVAILABLE kernel network isolation"; exit 3; }
SB=$(/usr/bin/python3 "$HERE/replay_paths.py" "$WS" "$LIVE_REPO" "$SBR" "$A") || exit 3
[ -f "$SNAP/COMPLETE" ] || { echo "CANNOT_REPLAY no complete snapshot for $A"; exit 3; }
[ -f "$SNAP/RETENTION_TRIMMED.json" ] && { echo "CANNOT_REPLAY TRIMMED_BY_RETENTION $A (rolling.npz removed by snap_retention; see RETENTION_TRIMMED.json)"; exit 3; }
"$WS/venv/bin/python" "$HERE/check_snapshot_generation.py" "$SNAP" "$A" || exit 3
[ -f "$WS/state/target_live_king/$A.json" ] || { echo "CANNOT_REPLAY no archived king file for $A"; exit 3; }
[ -f "$WS/state/target_live/$A.json" ] || { echo "CANNOT_REPLAY no archived target for $A"; exit 3; }
( cd "$SNAP" && shasum -a 256 -c SHA256SUMS --quiet ) || { echo "CANNOT_REPLAY snapshot sha mismatch"; exit 3; }
rm -rf "$SB"; mkdir -p "$SB/wide_shadow/state" "$SB/dl_quant_live/live" || exit 3
rsync -a --exclude venv --exclude '.env*' --exclude '.git' --exclude 'state/generation.json' --exclude 'state/snap' --exclude '__pycache__' --exclude 'shadow_bundle.aug*' --exclude 'shadow_bundle*.tar.gz' --exclude 'shadow_bundle_ref' \
      --exclude 'fea171/mini/cache.npz' --exclude 'fea171/mini/data/*' --exclude 'fea171/mini/preds/*' --exclude 'fea171/mini/results/*' --exclude 'loop.out*' --exclude 'shadow_log.jsonl' --exclude 'state/target_live_REHEARSAL' --exclude 'state/target_live/*' --exclude 'state/target_live_king/*' \
      --exclude 'state/target_blend*/*' --exclude 'state/target_combo/*' --exclude 'state/weights_combo/*' --exclude 'fea171/combo_live.log' "$WS/" "$SB/wide_shadow/" || exit 3
ln -s "$WS/venv" "$SB/wide_shadow/venv" || exit 3
if [ "$CODE" = patched ]; then
  [ -f "$TREE/PATCH_RECEIPT.json" ] || { echo "CANNOT_REPLAY no patched tree $TREE"; exit 3; }
  for f in combo_stage.py prev_state.py; do cp "$TREE/fea171/$f" "$SB/wide_shadow/fea171/$f" || exit 3; done
elif [ "$CODE" != current ]; then echo "CANNOT_REPLAY code must be current|patched"; exit 3; fi
echo "CODE=$CODE combo_stage sha $(shasum -a 256 "$SB/wide_shadow/fea171/combo_stage.py" | cut -c1-12)" > "$SB/CODE"
SF=$("$WS/venv/bin/python" "$HERE/generation_files.py" "$SNAP/generation.json") || exit 3   # NC release (§A7 addendum): exactly the files the snapshot's marker commits
for f in $SF generation.json; do cp "$SNAP/$f" "$SB/wide_shadow/state/" || exit 3; done
"$WS/venv/bin/python" "$SB/wide_shadow/fea171/combosnap/check_snapshot_generation.py" "$SB/wide_shadow/state" "$A" || exit 3
mkdir -p "$SB/wide_shadow/state/target_live" && cp "$WS/state/target_live_king/$A.json" "$SB/wide_shadow/state/target_live/$A.json" && cp "$WS/state/target_live_king/$A.json.sha256" "$SB/wide_shadow/state/target_live/$A.json.sha256" || exit 3
SCR_ROOT="$SBR" "$WS/venv/bin/python" "$HOOKDIR/gap_fix_hook.py" "$SB" "$A" "$ARM" > "$SB/HOOK" || exit 3; cat "$SB/HOOK"
rsync -a --exclude '__pycache__' --exclude '.env*' "$LIVE_REPO/live/" "$SB/dl_quant_live/live/" || exit 3
cat > "$SB/dl_quant_live/live/telegram_notify.py" <<'PY'
# PARITY STUB: never sends; records calls
import json, os, time
class TelegramNotifier:
    def __init__(self, token=None, chat_id=None): self.calls = []
    def alarm(self, sev, msg):
        open(os.path.join(os.path.dirname(__file__), "STUB_PAGES.log"), "a").write(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "sev": sev, "msg": msg}) + "\n"); return {"status": "STUBBED"}
    def send(self, *a, **k): return self.alarm("INFO", str(a))
PY
PAR="$SB/wide_shadow/state/target_live_PARITY"; mkdir -p "$PAR"
mkdir -p "$SB/tmp" || exit 3
printf 'synthetic credential canary\n' > "$SB/credential-canary" || exit 3
cat > "$SB/offline.sb" <<'PROFILE'
(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath (param "SANDBOX")) (literal "/dev/null"))
(deny file-read* file-write* (regex #"(^|/)[.]env([^/]*$|/)")
  (subpath (param "SOURCE_STATE")) (subpath (param "SOURCE_LIVE"))
  (literal (param "CANARY"))
  (subpath (param "SSH")) (subpath (param "KEYCHAINS"))
  (subpath (param "AWS")) (subpath (param "AZURE")) (subpath (param "GCLOUD"))
  (literal (param "NETRC")) (literal (param "GIT_CREDENTIALS")))
PROFILE
# Clear inherited credentials; HOME is neither changed nor required by the stage.
( cd "$SB/wide_shadow/fea171" && /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin PYTHONDONTWRITEBYTECODE=1 \
  "TMPDIR=$SB/tmp" "WIDE_SHADOW_HOME=$SB/wide_shadow" "DL_QUANT_LIVE_ROOT=$SB/dl_quant_live" \
  COMBO_LIVE=1 "COMBO_LIVE_DIR=$PAR" \
  /usr/bin/sandbox-exec -D "SANDBOX=$SB" -D "SOURCE_STATE=$WS/state" -D "SOURCE_LIVE=$LIVE_REPO" \
  -D "CANARY=$SB/credential-canary" -D "SSH=$HOME/.ssh" -D "KEYCHAINS=$HOME/Library/Keychains" \
  -D "AWS=$HOME/.aws" -D "AZURE=$HOME/.azure" -D "GCLOUD=$HOME/.config/gcloud" \
  -D "NETRC=$HOME/.netrc" -D "GIT_CREDENTIALS=$HOME/.git-credentials" -f "$SB/offline.sb" \
  "$WS/venv/bin/python" -u "$SB/wide_shadow/fea171/combosnap/offline_stage.py" \
  "$SB/wide_shadow/fea171/combo_stage.py" "$SB" > "$SB/run.log" 2>&1 )
RC=$?
[ -f "$SB/ISOLATION_OK" ] || { echo "UNAVAILABLE kernel isolation probe failed rc=$RC"; tail -3 "$SB/run.log"; exit 3; }
echo "combo_stage rc=$RC (sandbox $SB)"; tail -3 "$SB/run.log" | cut -c1-200
echo "$RC" > "$SB/RC"; echo "GAP_FIX_REPLAY_DONE anchor=$A arm=$ARM code=$CODE rc=$RC sandbox=$SB"
