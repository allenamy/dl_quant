#!/bin/bash
# round 5 (lead ruling 2026-09-27): C0 only on a same-host (arm64) production anchor: current base + patched base replays, then gap_fix_judge_c0.py.
# usage: run_c0_round5.sh <new root> <A> <receipt out>      (tree GAP4 = the package files, so no scratch tree is needed)
set -uo pipefail
ROOT=${1:?}; A=${2:?}; OUT=${3:?}; D=$(cd "$(dirname "$0")" && pwd -P); PKG="$D/../package_GAP4"; TREE="$ROOT/treeGAP4"
[ -e "$ROOT" ] && { echo "REFUSED root exists: $ROOT"; exit 2; }
mkdir -p "$TREE/fea171"; echo "HOST $(uname -m)"
# the patched tree = the package's files, each checked against the contract's candidate sha (never a scratch copy of unknown provenance)
cp "$PKG/PATCH_RECEIPT.json" "$TREE/PATCH_RECEIPT.json" || exit 2
~/wide_shadow/venv/bin/python - "$PKG" "$TREE" <<'PY' || exit 2
import hashlib, json, shutil, sys
pkg, tree = sys.argv[1], sys.argv[2]; C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json"))
for it in C["files"]:
    src = f"{pkg}/files/{it['dest']}"; h = hashlib.sha256(open(src, "rb").read()).hexdigest()
    assert h == it["candidate_sha256"], (src, h); shutil.copy(src, f"{tree}/fea171/{it['dest'].split('/')[-1]}")
    print("TREE", it["dest"], h[:12])
PY
# part i: hook base (the anchor exactly as production ran it)  -> the frozen C0 section, read for current_vs_archived (same-host reference)
# part ii: hook mhfill for BOTH codes (member-history holes filled in the sandbox) -> the frozen C0 section, read for current == patched
for part in i ii; do hk=base; [ $part = ii ] && hk=mhfill; mkdir -p "$ROOT/$part"
  for code in current patched; do sbr="$ROOT/$part/${code}_base"; mkdir -p "$sbr"; echo "=== $(date -u +%FT%TZ) part $part $code hook=$hk $A"
    bash "$D/gap_fix_replay.sh" "$A" - "$sbr" "$hk" "$code" "$TREE" 2>&1 | tail -4; done
  ~/wide_shadow/venv/bin/python "$D/gap_fix_judge_c0.py" "$ROOT/$part" "$A" --out "${OUT%.json}_part_$part.json"; echo "JUDGE_C0_PART_${part}_RC=$?"; done
~/wide_shadow/venv/bin/python "$D/c0_round5_verdict.py" "$ROOT" "$A" "${OUT%.json}_part_i.json" "${OUT%.json}_part_ii.json" --out "$OUT"; echo "ROUND5_RC=$?"
