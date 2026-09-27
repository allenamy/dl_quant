#!/bin/bash
# rc_regen_red_legs.sh -- root-cause support (lead 2026-09-27 01:4xZ, dlarch leads): regenerate RED_m0's shuffled King OOF and legs
# (deleted by mr_prep's space cleanup after its targets existed) on /workspace, with the SAME devices and env as mr_prep, and
# assert they reproduce the run-3 receipts by content: shuffled P array sha b63e8c0c... and legs container sha 7f40e476...
set -euo pipefail
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; N=/dev/shm/news2_2026-09-23; NC=/dev/shm/nc_2026-09-23
O=/workspace/mretrain_2026-09-26/redcause; PV=/workspace/venv/bin/python; P314=/root/news_2026-09-23_env/venv314/bin/python
NPY="X86_V4 AVX512_ICL AVX512_SPR"; mkdir -p $O; cd $D
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $O/regen.log; }
trap 'say "RC_REGEN FAILED rc=$? line $LINENO"' ERR
say "RC_REGEN_START pgid=$(ps -o pgid= -p $$ | tr -d ' ')"
[ -s $O/king_RED/KING_OOF.npz ] || $PV -B mr_shuffle_king.py $R/arms/A0_m0/work/king/KING_OOF.npz $O/king_RED > $O/shuffle.log 2>&1
$PV -B mr_gates.py --identity $O/king_RED/KING_OOF.npz $O/king_RED/KING_IDENTITY.json > $O/identity.log 2>&1
grep -q '"P": "b63e8c0c2106c6cb' $O/identity.log || { say "RC_REGEN FAILED shuffled P does not reproduce b63e8c0c"; exit 1; }
say "shuffled King reproduces P b63e8c0c"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NPY_DISABLE_CPU_FEATURES="$NPY" NC_W=$NC NC_TREE=$NC/tree NC_WS=$NC/ws NC_CFG=$N/inputs/bundle_config.json \
  nice -n 12 $P314 -B -u nc_legs.py $N/work/NEWS_FEATURES.npz $O/king_RED/KING_OOF.npz $O/legs_RED.npz > $O/legs.log 2>&1
grep -q "^NC_LEGS_DONE" $O/legs.log || { say "RC_REGEN FAILED legs no DONE line"; exit 1; }
h=$(sha256sum $O/legs_RED.npz | cut -c1-64)
[ "$h" = 7f40e476cd879bdfd6339aa62342e6f50055598f13ed0c98c4aa33485f58dd46 ] || { say "RC_REGEN FAILED legs sha $h != run-3 7f40e476"; exit 1; }
say "RC_REGEN DONE legs_RED reproduces run-3 container 7f40e476"
