#!/bin/bash
# DEPLOY manual §P2: install / rollback rehearsal with the REAL package (lead 2026-09-24, user ruling RULING_user_NC_s42_override_2026-09-24.md).
# Inputs are asserted, never typed: treeNC5 PATCH_RECEIPT sha = 3135cf8b (DEPLOY header); seed pack sha = receipts/build_2026-09-23/NC_SEED_PACK.json
# sha256 (600d760e); model shas = news2's HANDOFF_deploy_s42.json via nc_handoff_check.py; snapshot = the newest state/snap/<A>/ with COMPLETE.
# Local heavy work ⇒ only inside the Mac quiet window with >= 15 min left; refuses (rc 78) otherwise. Reads ~/wide_shadow only (fake HOME copy).
# usage: bash run_install_rehearsal_p2.sh <models dir: HANDOFF_deploy_s42.json P5_DEPLOY_MANIFEST.json slow2026.txt f10_live_s42_np.npz>
set -u
QR=~/Desktop/quant_research; RC=$QR/multi_asset/exports/research/nc_2026-09-23; QW=$QR/multi_asset/exports/research/common/venue_quiet_window.py
W=~/cc_tmp/nc_20260923; MD=${1:?models dir}; RUL=$QR/docs/RULING_user_NC_s42_override_2026-09-24.md; PYP=~/wide_shadow/venv/bin/python
QJ=$(/usr/bin/python3 $QW --json); qrc=$?
REM=$(echo "$QJ" | /usr/bin/python3 -c "import json,sys;print(int(json.load(sys.stdin).get('remaining_min') or 0))")
if [ $qrc -ne 0 ] || [ "$REM" -lt 15 ]; then echo "REFUSED: quiet window rc=$qrc remaining_min=$REM (need rc 0 and >= 15)"; exit 78; fi
TREE_SHA=3135cf8bbfad4b2715c6d6a9fd36a92b3058be95ac011d77ae792135a155089d
SEED_SHA=$(/usr/bin/python3 -c "import json;print(json.load(open('$RC/receipts/build_2026-09-23/NC_SEED_PACK.json'))['sha256'])")
[ "$(shasum -a 256 $W/treeNC5/PATCH_RECEIPT.json | cut -d' ' -f1)" = "$TREE_SHA" ] || { echo "REFUSED: treeNC5 PATCH_RECEIPT sha"; exit 3; }
[ "$(shasum -a 256 $W/seed_pack_0919.npz | cut -d' ' -f1)" = "$SEED_SHA" ] || { echo "REFUSED: seed pack sha != NC_SEED_PACK.json"; exit 3; }
A=$(for d in $(ls ~/wide_shadow/state/snap | grep -E '^[0-9]{10}$' | sort -n); do [ -f ~/wide_shadow/state/snap/$d/COMPLETE ] && [ -f ~/wide_shadow/state/snap/$d/generation.json ] && echo $d; done | tail -1)
[ -n "$A" ] || { echo "REFUSED: no COMPLETE snapshot"; exit 3; }
OUT=$W/release_tests/install_rehearsal_real_$(date -u +%Y%m%dT%H%MZ); mkdir -p $(dirname $OUT)
HC=$(/usr/bin/python3 $W/src/nc_handoff_check.py $MD/HANDOFF_deploy_s42.json $MD/P5_DEPLOY_MANIFEST.json $MD/slow2026.txt $MD/f10_live_s42_np.npz $RUL --out $OUT.handoff_check.json); hrc=$?
echo "$HC" | cut -c1-400
[ $hrc -eq 0 ] || { echo "REFUSED: handoff check rc=$hrc"; exit 3; }
KSHA=$(/usr/bin/python3 -c "import json;print(json.load(open('$OUT.handoff_check.json'))['executor_pins']['booster_sha_pin'])")
FSHA=$(/usr/bin/python3 -c "import json;print(json.load(open('$OUT.handoff_check.json'))['executor_pins']['f10_sha_pin'])")
echo "quiet window open (remaining ${REM} min); snapshot $A; seed pack ${SEED_SHA:0:8}; tree ${TREE_SHA:0:8}; king ${KSHA:0:8}; f10 ${FSHA:0:8}; out $OUT; loadavg $(uptime | sed 's/.*averages: //')"
echo "started $(date -u +%H:%M:%SZ)"
$PYP -u $W/src/test_nc_install_rehearsal.py $W/treeNC5 $W/release $W/seed_pack_0919.npz $A $OUT \
  --king $MD/slow2026.txt --king-sha $KSHA --f10 $MD/f10_live_s42_np.npz --f10-sha $FSHA --export-manifest $MD/P5_DEPLOY_MANIFEST.json --ruling $RUL
trc=$?
echo "rc=$trc ended $(date -u +%H:%M:%SZ)"
exit $trc
