#!/bin/bash
# king_oct_repredict.sh <new features | C0ONLY> <new features sha | -> <tag> -- process executor (§10-f) of the frozen-October-King re-prediction
# (fresh2 2026-09-27; lead: descriptive D10 re-read on extended features). Gate frozen here, before any run:
#   C0 identity: king_oct_repredict.py on the OLD features f1cd3fa2 must reproduce release m0's KING_OOF (274ba08a) P / E_ts / symbols
#      bitwise (king_oct_check.py same). Not PASS => KRP_STOP, the new features are never scored.
#   then the same code on <new features> -> repredict_<tag>/NEW/KING_OOF.npz; described (not gated) against release m0 on the anchors
#   both axes share (KRP_DESC line).
# Nothing under release/ is written (the release root is only read). Registered log: logs/repredict_<tag>.log; terminal line-start
# "<ts> (KRP_STOP|KRP_ALL_DONE)".
set -uo pipefail
NEWF=$1; NEWF_SHA=$2; TAG=$3
K=/workspace/king_oct_2026-09-27; D=$K/devices; PV=/workspace/venv/bin/python; LG=$K/logs/repredict_$TAG.log
OLDF=/workspace/d10_lineD_2026-09-26/stage2/NEWS_FEATURES_D10.npz; OLDF_SHA=f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd
REL=$K/release; MAN=$REL/MANIFEST_RELEASE.json; MAN_SHA=2d0fa3f9ac8f9e23b57cfd89d107e20d1d29ff708b8c1c75176613d3aa48a54b
REF=$REL/m0/KING_OOF.npz; REF_SHA=274ba08a2172a344d48b261a50fc634eaf46d9d16185e3adc593cfb4da507296
O=$K/repredict_$TAG
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "KRP_STOP: $*"; exit 1; }
mkdir -p $K/logs
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"king_oct_repredict.sh $TAG\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $K/logs/PGID_repredict_$TAG.json
say "KRP_START pgid=$PG tag=$TAG new_features=$NEWF"
[ -e $O ] && stop "$O exists (fresh only)"
[ "$(sha256sum $REF | cut -c1-64)" = "$REF_SHA" ] || stop "release m0 KING_OOF is not 274ba08a"
mkdir -p $O/checks
rp() { (cd $D && nice -n 12 $PV -B king_oct_repredict.py --release-root $REL/m0 --manifest $MAN --manifest-sha $MAN_SHA --features $1 --features-sha $2 --out $3 > $4 2>&1); }
rp $OLDF $OLDF_SHA $O/C0_identity $K/logs/repredict_${TAG}_C0.log || stop "C0 re-prediction failed (see $K/logs/repredict_${TAG}_C0.log)"
$PV -B $D/king_oct_check.py same $O/C0_identity/KING_OOF.npz $REF $O/checks/C0_same.json > $K/logs/repredict_${TAG}_C0_check.log 2>&1
say "C0 $(grep -h '^KOC_CHECK' $K/logs/repredict_${TAG}_C0_check.log | cut -c1-240)"
grep -q "^KOC_CHECK same PASS=True" $K/logs/repredict_${TAG}_C0_check.log || stop "C0 identity not PASS: the re-prediction does not reproduce release m0"
[ "$NEWF" = C0ONLY ] && { say "KRP_ALL_DONE c0_only (identity control ahead of the new features; the full run repeats C0)"; exit 0; }
rp $NEWF $NEWF_SHA $O/NEW $K/logs/repredict_${TAG}_NEW.log || stop "re-prediction on the new features failed (see $K/logs/repredict_${TAG}_NEW.log)"
say "NEW $(grep -h '^KRP_DONE' $K/logs/repredict_${TAG}_NEW.log)"
$PV - $O/NEW/KING_OOF.npz $REF > $K/logs/repredict_${TAG}_NEW_describe.log 2>&1 <<'PY' || true
import sys, numpy as np   # described, not gated: the new axis is longer, so compare on the anchors both files have
N, R = np.load(sys.argv[1]), np.load(sys.argv[2])
assert np.array_equal(N["symbols"], R["symbols"]), "symbol axes differ"
en, er = N["E_ts"].astype(np.int64), R["E_ts"].astype(np.int64); com, i_n, i_r = np.intersect1d(en, er, return_indices=True)
pn, pr = N["P"][i_n], R["P"][i_r]; both = np.isfinite(pn) & np.isfinite(pr)
print("KRP_DESC anchors_new=%d anchors_release=%d common=%d only_new=%d cells_finite_in_both=%d cells_differing=%d nan_pattern_differs=%d last_new=%d" % (
      len(en), len(er), len(com), len(np.setdiff1d(en, er)), both.sum(), (both & (pn != pr)).sum(), (np.isfinite(pn) != np.isfinite(pr)).sum(), en[-1]))
PY
say "NEW vs release m0 (described, not gated): $(grep -h '^KRP_DESC' $K/logs/repredict_${TAG}_NEW_describe.log)"
say "KRP_ALL_DONE out=$O/NEW/KING_OOF.npz"
