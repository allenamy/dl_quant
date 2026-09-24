#!/bin/zsh
# b7_copy_inputs.sh — READ-ONLY copies of the production files B7 needs (no write under ~/wide_shadow or ~/dl_quant_live; cp -p only reads
# the sources). Run after the 12Z anchor row is in the ledger (≈ 12:45Z). The orders / anchors copies stay in the scratchpad (live execution
# data: never committed; only their sha256 and pooled derived quantities leave it); the target_live copies (producer output) are committed.
# usage: zsh b7_copy_inputs.sh <inputs_dir>
set -eu
IN=$1; mkdir -p $IN/target_live
for A in 1790236800 1790251200; do
  cp -p ~/wide_shadow/state/target_live/$A.json ~/wide_shadow/state/target_live/$A.json.sha256 $IN/target_live/
done
cp -p ~/dl_quant_live/state/live/pilot_log/20260924/anchors.jsonl $IN/anchors_20260924.jsonl
cp -p ~/dl_quant_live/state/live/pilot_log/20260924/orders.jsonl $IN/orders_20260924.jsonl
cd $IN && shasum -a 256 target_live/*.json target_live/*.sha256 anchors_20260924.jsonl orders_20260924.jsonl > COPY_SHA256.txt
for A in 1790236800 1790251200; do
  want=$(cut -c1-64 target_live/$A.json.sha256); got=$(shasum -a 256 target_live/$A.json | cut -c1-64)
  [ "$want" = "$got" ] && echo "SIDECAR_OK $A" || { echo "SIDECAR_MISMATCH $A want=$want got=$got"; exit 3; }
done
date -u +%FT%TZ >> COPY_SHA256.txt; cat COPY_SHA256.txt
