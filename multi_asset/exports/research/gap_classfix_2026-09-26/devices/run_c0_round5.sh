#!/bin/bash
# round 5 (lead ruling 2026-09-27): C0 only on a same-host (arm64) production anchor: current base + patched base replays, then gap_fix_judge_c0.py.
# usage: EXPECT_MH=t1,t2,.. run_c0_round5.sh <new root> <A> <receipt out>      (tree GAP4 = the package files, so no scratch tree is needed)
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
# lead ruling (P5 clarification 05:5xZ, before any 08Z reading; mhfill vetoed): base replays only, both codes; then
#   (i)   the frozen C0 section (gap_fix_judge_c0.py) read ONLY for current_vs_archived: weights and beta_overlay bitwise vs the arm64 archive
#   (ii)  cited: run 4 (arm64) current == patched bitwise on 3 gap-free anchors (receipts/GAPFIX_JUDGE_run4_arm64.json)
#   (iii) c0_round5_attrib.py: every current/patched difference at A attributed to the MH_RECOMPUTED anchors (literal EXPECT_MH)
for code in current patched; do sbr="$ROOT/${code}_base"; mkdir -p "$sbr"; echo "=== $(date -u +%FT%TZ) $code base $A"
  bash "$D/gap_fix_replay.sh" "$A" - "$sbr" base "$code" "$TREE" 2>&1 | tail -4; done
~/wide_shadow/venv/bin/python "$D/gap_fix_judge_c0.py" "$ROOT" "$A" --out "${OUT%.json}_c0_section.json"; echo "JUDGE_C0_SECTION_RC=$? (whole-section verdict is informational; round 5 reads (i) and (iii))"
~/wide_shadow/venv/bin/python "$D/c0_round5_attrib.py" "$ROOT" "$A" "${OUT%.json}_c0_section.json" "${EXPECT_MH:?EXPECT_MH=t1,t2,.. required}" --out "$OUT"; echo "ROUND5_RC=$?"
