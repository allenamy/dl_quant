#!/bin/zsh
# b7v2_copy_inputs.sh — READ-ONLY copies of the production files B7 v2 needs for ONE anchor A (cp -p only reads the sources; nothing under
# ~/wide_shadow or ~/dl_quant_live is written). Run after A's anchors row is in the ledger (≈ N+45m). The orders / anchors copies stay in
# the scratchpad (live execution data: never committed; only their sha256 and pooled derived quantities leave it); the target_live copy
# (producer output) may be committed.
# usage: zsh b7v2_copy_inputs.sh <inputs_dir> <A>
set -eu
IN=$1; A=$2; mkdir -p $IN/target_live
[ $((A % 14400)) -eq 0 ] || { echo "A=$A not on the 4h grid"; exit 3; }
DAY=$(date -u -r $A +%Y%m%d)
cp -p ~/wide_shadow/state/target_live/$A.json ~/wide_shadow/state/target_live/$A.json.sha256 $IN/target_live/
cp -p ~/dl_quant_live/state/live/pilot_log/$DAY/anchors.jsonl $IN/anchors_$DAY.jsonl
cp -p ~/dl_quant_live/state/live/pilot_log/$DAY/orders.jsonl $IN/orders_$DAY.jsonl
cd $IN && shasum -a 256 target_live/$A.json target_live/$A.json.sha256 anchors_$DAY.jsonl orders_$DAY.jsonl > COPY_SHA256_$A.txt
want=$(cut -c1-64 target_live/$A.json.sha256); got=$(shasum -a 256 target_live/$A.json | cut -c1-64)
[ "$want" = "$got" ] && echo "SIDECAR_OK $A" || { echo "SIDECAR_MISMATCH $A want=$want got=$got"; exit 3; }
date -u +%FT%TZ >> COPY_SHA256_$A.txt; cat COPY_SHA256_$A.txt
