#!/bin/bash
# make_manifest.sh — pod-side MANIFEST of Track A products (path, bytes, sha256) written to results/MANIFEST_pod.txt; read-only except that file.
ROOT=/workspace/review_scratch/allweather_trackA
cd $ROOT || exit 2
OUT=$ROOT/results/MANIFEST_pod.txt
echo "# Track A pod manifest $(date -u +%FT%TZ) host $(hostname) root $ROOT" > $OUT
for f in scripts/*.py scripts/*.sh features/*.npy features/*.npz features/*.json results/*.json results/preds/*.npy rider/w10_health_spotsup.py rider/w10_health_spotsup.diff rider/spotsup_qvr24h.npz rider/dev_alt/probe_artifacts/*.npz rider/dev_alt/probe_artifacts/*.json spot/perp_to_spot_map.json spot/s3_spot_symbols.json spot/a1_manifest.jsonl premidx/a2_manifest.jsonl logs/*.log logs/commands.txt logs/chain.log logs/SHA256SUMS_*.txt logs/SCRIPTS_SHA256_*.txt; do
  [ -f "$f" ] || continue
  printf "%s\t%s\t%s\n" "$ROOT/$f" "$(stat -c %s "$f")" "$(sha256sum "$f" | cut -d" " -f1)" >> $OUT
done
echo "MANIFEST_DONE $(wc -l < $OUT) lines $(du -sh $ROOT | cut -f1) total"
