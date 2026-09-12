#!/bin/bash
# Read-only copy of the producer's state right after an anchor closes (PREREG_producer_parity_replay §2). Usage: snapshot_producer_state.sh <anchor_ts>
# Never writes under ~/wide_shadow. Refuses if the producer's last_anchor != <anchor_ts> (snapshot must belong to that anchor).
set -u; A=$1; W=/Users/haosiyu/wide_shadow; D=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/live/producer_state_snapshots/$A
LA=$(python3 -c "import json;print(json.load(open('$W/state/aux.json'))['last_anchor'])"); [ "$LA" = "$A" ] || { echo "REFUSE: producer last_anchor=$LA != $A"; exit 2; }
mkdir -p "$D" && cp -p $W/state/aux.json $W/state/leg_returns_live.json $W/state/combo_live_status.json "$D/" && cp -p $W/state/rolling.npz "$D/rolling.npz" \
 && (cd "$D" && shasum -a 256 aux.json leg_returns_live.json combo_live_status.json rolling.npz > SHA256SUMS.txt) && echo "SNAPSHOT_OK $A $(date -u +%FT%TZ) $(wc -l < $D/SHA256SUMS.txt) files"
