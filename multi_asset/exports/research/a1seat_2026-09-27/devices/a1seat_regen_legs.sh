#!/bin/bash
# a1seat_regen_legs.sh -- A1 seat/composition split (rule b41ac9985 + rev 1 552475325): regenerate A1_m0's legs (deleted by mr_prep's
# space cleanup in fresh2's root) from the kingfam A1_m0 King OOF, with the SAME device and env as rc_regen_red_legs.sh / mr_prep, and
# assert by literal constants: (i) the OOF's score arrays equal fresh2's A1_m0 (P 3498659b, via mr_gates --identity), (ii) the legs
# container reproduces fresh2's A1_m0 legs f3702ff0 (NC_LEGS_RECEIPT of /dev/shm/mretrain_2026-09-26/arms/A1_m0, 01:11:15Z).
# Reads fresh2's root and kingfam read-only; writes only under $R/a1legs. Log: $R/a1legs/regen.log (terminal A1LEGS DONE / FAILED).
set -euo pipefail
R=/dev/shm/a1seat_2026-09-27; FD=/dev/shm/mretrain_2026-09-26/devices; N=/dev/shm/news2_2026-09-23; NC=/dev/shm/nc_2026-09-23
O=$R/a1legs; PV=/workspace/venv/bin/python; P314=/root/news_2026-09-23_env/venv314/bin/python; NPY="X86_V4 AVX512_ICL AVX512_SPR"
OOF=/workspace/kingfam_2026-09-27/arms/A1_m0/KING_OOF.npz
OOF_SHA=11bbaeb1bdb1b85ecaa097e7c66ab5e151a8a779c128e2b8ad99aa6b705ada1c; P_SHA=3498659b09520ca9067d22e52a96ab9f6a285baacbe752a08911ed0bffcbf008
LEGS_SHA=f3702ff0c9886a6977ecbebda0ae319af47f599ddcad4b99d90e29e2d0dc754a
mkdir -p $O/king_A1
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $O/regen.log; }
trap 'say "A1LEGS FAILED rc=$? line $LINENO"' ERR
say "A1LEGS_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
if [ -s $O/legs_A1.npz ] && [ "$(sha256sum $O/legs_A1.npz | cut -c1-64)" = $LEGS_SHA ]; then say "A1LEGS DONE (already present, sha $LEGS_SHA)"; exit 0; fi
[ "$(sha256sum $OOF | cut -c1-64)" = $OOF_SHA ] || { say "A1LEGS FAILED kingfam A1_m0 OOF sha != $OOF_SHA"; exit 1; }
cp $OOF $O/king_A1/KING_OOF.npz
$PV -B $FD/mr_gates.py --identity $O/king_A1/KING_OOF.npz $O/king_A1/KING_IDENTITY.json > $O/identity.log 2>&1
grep -q "\"P\": \"$P_SHA\"" $O/king_A1/KING_IDENTITY.json || { say "A1LEGS FAILED A1 scores P != $P_SHA"; exit 1; }
say "A1 King OOF scores reproduce fresh2 A1_m0 P ${P_SHA:0:16}"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NPY_DISABLE_CPU_FEATURES="$NPY" NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws NC_CFG=$N/inputs/bundle_config.json \
  nice -n 12 $P314 -B -u $FD/nc_legs.py $N/work/NEWS_FEATURES.npz $O/king_A1/KING_OOF.npz $O/legs_A1.npz > $O/legs.log 2>&1
grep -q "^NC_LEGS_DONE" $O/legs.log || { say "A1LEGS FAILED legs no DONE line"; exit 1; }
h=$(sha256sum $O/legs_A1.npz | cut -c1-64)
[ "$h" = $LEGS_SHA ] || { say "A1LEGS FAILED legs sha $h != fresh2 A1_m0 $LEGS_SHA"; exit 1; }
say "A1LEGS DONE legs_A1 reproduces fresh2 A1_m0 container ${LEGS_SHA:0:16}"
