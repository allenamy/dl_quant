#!/bin/bash
# FP3 item C part 2 (2026-09-17): production whole-book PARITY for one anchor. Rebuilds the producer's world for anchor A in a sandbox HOME from
# (i) the current producer tree (code, xfer files, mini, shadow_bundle, per-anchor state files state/weights/<A-4h>.npz + fea171/state_H_*_<A-4h>.npz),
# (ii) the rolling-state snapshot state/snap/<A>/ (aux.json, rolling.npz, leg_returns_live.json — the files combo_stage read for A), and
# (iii) the archived pre-combo king file target_live_king/<A>.json (what combo_stage read, validated and backed up before rewriting);
# runs combo_stage.py exactly as the daemon does (COMBO_LIVE=1) but with COMBO_LIVE_DIR pointing into the sandbox (rehearsal branch: the production
# target_live is never touched; the pager is a stub that records), then compares the replayed target with the archived target_live/<A>.json.
# usage: combo_parity_replay.sh <anchor_ts> <out_receipt.json> [sandbox_root]     exit 0 = PARITY, 2 = MISMATCH, 3 = cannot replay (named)
set -u
A=${1:?anchor_ts}; OUT=${2:?receipt}; SBR=${3:-"$HOME/cc_tmp/parity"}; WS="$HOME/wide_shadow"; SNAP="$WS/state/snap/$A"; HERE=$(cd "$(dirname "$0")" && pwd -P)
[ -f "$SNAP/COMPLETE" ] || { echo "CANNOT_REPLAY no complete snapshot for $A"; exit 3; }
[ -f "$WS/state/target_live_king/$A.json" ] || { echo "CANNOT_REPLAY no archived king file for $A"; exit 3; }
[ -f "$WS/state/target_live/$A.json" ] || { echo "CANNOT_REPLAY no archived target for $A"; exit 3; }
( cd "$SNAP" && shasum -a 256 -c SHA256SUMS --quiet ) || { echo "CANNOT_REPLAY snapshot sha mismatch"; exit 3; }
SB="$SBR/$A"; rm -rf "$SB"; mkdir -p "$SB/wide_shadow/state" "$SB/dl_quant_live/live" || exit 3
rsync -a --exclude venv --exclude 'state/snap' --exclude '__pycache__' --exclude 'shadow_bundle.aug*' --exclude 'shadow_bundle*.tar.gz' --exclude 'shadow_bundle_ref' \
      --exclude 'loop.out*' --exclude 'shadow_log.jsonl' --exclude 'state/target_live_REHEARSAL' --exclude 'state/target_live/*' --exclude 'state/target_live_king/*' \
      --exclude 'state/target_blend*/*' --exclude 'state/target_combo/*' --exclude 'state/weights_combo/*' --exclude 'fea171/combo_live.log' "$WS/" "$SB/wide_shadow/" || exit 3
ln -s "$WS/venv" "$SB/wide_shadow/venv" || exit 3
cp "$SNAP/aux.json" "$SNAP/rolling.npz" "$SNAP/leg_returns_live.json" "$SB/wide_shadow/state/" || exit 3
mkdir -p "$SB/wide_shadow/state/target_live" && cp "$WS/state/target_live_king/$A.json" "$SB/wide_shadow/state/target_live/$A.json" && cp "$WS/state/target_live_king/$A.json.sha256" "$SB/wide_shadow/state/target_live/$A.json.sha256" || exit 3
rsync -a --exclude '__pycache__' "$HOME/dl_quant_live/live/" "$SB/dl_quant_live/live/" || exit 3
cat > "$SB/dl_quant_live/live/telegram_notify.py" <<'PY'
# PARITY STUB: never sends; records calls
import json, os, time
class TelegramNotifier:
    def __init__(self, token=None, chat_id=None): self.calls = []
    def alarm(self, sev, msg):
        open(os.path.join(os.path.dirname(__file__), "STUB_PAGES.log"), "a").write(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "sev": sev, "msg": msg}) + "\n"); return {"status": "STUBBED"}
    def send(self, *a, **k): return self.alarm("INFO", str(a))
PY
printf 'TELEGRAM_BOT_TOKEN="stub"\nTELEGRAM_CHAT_ID="0"\n' > "$SB/dl_quant_live/.env"
PAR="$SB/wide_shadow/state/target_live_PARITY"; mkdir -p "$PAR"
( cd "$SB/wide_shadow/fea171" && HOME="$SB" COMBO_LIVE=1 COMBO_LIVE_DIR="$PAR" "$WS/venv/bin/python" -u combo_stage.py > "$SB/run.log" 2>&1 ); RC=$?
echo "combo_stage rc=$RC (sandbox $SB)"; tail -3 "$SB/run.log" | cut -c1-200
"$WS/venv/bin/python" "$HERE/combo_parity_compare.py" "$A" "$WS/state/target_live/$A.json" "$PAR/$A.json" "$SB" "$RC" "$OUT"
