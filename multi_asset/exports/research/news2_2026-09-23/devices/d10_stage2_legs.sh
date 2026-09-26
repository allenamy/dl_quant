#!/usr/bin/env bash
# d10_stage2_legs.sh {identity|d10} -- line D stage 2d: nc_legs.py (news2 root copy, 18387627) UNCHANGED, environment copied from
# run_p3_legs_f10.sh (the run that produced legs 9ee5886f): venv314, NPY_DISABLE_CPU_FEATURES, single-threaded BLAS.
#   identity : NC root funding + NEWS_FEATURES 3c886a2b + KING_OOF a10b8725  => must equal legs.npz 9ee5886f BITWISE (every key).
#   d10      : R2 funding (fund_state_d10 f07e4ebd, RN8 comes from it) + NEWS_FEATURES_D10 + KING_OOF_SWAP (stage 1).
#              Refuses unless the identity receipt says BITWISE and the stage-2c assemble receipt exists.
# Executor (protocol s10-f): this script under setsid on pod2, started by news2; supervisor: news2's waiter on $S/logs/legs_*.log.
set -u
MODE=${1:?identity|d10}
S=/dev/shm/d10_2026-09-25/lineD/stage2; W=/dev/shm/news2_2026-09-23; NCR=/dev/shm/nc_2026-09-23
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p $S/logs
if [ "$MODE" = identity ]; then
  O=$S/legs_id; mkdir -p $O
  NC_W=$NCR NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$W/inputs/bundle_config.json \
    nice -n 10 $P314 -u $W/devices/nc_legs.py $W/work/NEWS_FEATURES.npz $W/work/king/KING_OOF.npz $O/legs.npz > $S/logs/legs_identity.log 2>&1 \
    || { echo "LEGS_IDENTITY FAILED rc=$?" >> $S/logs/legs_identity.log; exit 1; }
  $PV - "$O/legs.npz" "$W/work/legs.npz" "$O/LEGS_IDENTITY.json" <<'PY' >> $S/logs/legs_identity.log 2>&1
import sys, json, hashlib, numpy as np
a, b, out = sys.argv[1:4]
A, B = np.load(a), np.load(b)
res = {"got": [a, hashlib.sha256(open(a, "rb").read()).hexdigest()], "ref": [b, hashlib.sha256(open(b, "rb").read()).hexdigest()], "keys": {}}
assert sorted(A.files) == sorted(B.files), (A.files, B.files)
for k in A.files:
    x, y = A[k], B[k]
    if x.shape != y.shape or x.dtype != y.dtype: res["keys"][k] = "shape/dtype"; continue
    if x.dtype.kind == "f":
        same = (x.view(np.uint64 if x.itemsize == 8 else np.uint32) == y.view(np.uint64 if y.itemsize == 8 else np.uint32)) | (np.isnan(x) & np.isnan(y))
    else:
        same = x == y
    res["keys"][k] = int((~same).sum())
res["VERDICT"] = "BITWISE" if all(v == 0 for v in res["keys"].values()) else "DIFFERS"
open(out, "w").write(json.dumps(res, indent=1)); print("LEGS_IDENTITY", res["VERDICT"], res["keys"])
PY
  exit 0
fi
[ "$MODE" = d10 ] || { echo "unknown mode"; exit 2; }
grep -q '"VERDICT": "BITWISE"' $S/legs_id/LEGS_IDENTITY.json || { echo "REFUSED: legs identity not BITWISE" > $S/logs/legs_d10.log; exit 3; }
[ -s $S/NEWS_FEATURES_D10_RECEIPT.json ] || { echo "REFUSED: stage 2c assemble receipt missing" > $S/logs/legs_d10.log; exit 3; }
O=$S/legs_d10; mkdir -p $O
NC_W=$S/R2 NC_TREE=$NCR/tree NC_WS=$NCR/ws NC_CFG=$W/inputs/bundle_config.json \
  nice -n 10 $P314 -u $W/devices/nc_legs.py $S/NEWS_FEATURES_D10.npz /dev/shm/d10_2026-09-25/lineD/KING_OOF_SWAP.npz $O/legs.npz > $S/logs/legs_d10.log 2>&1 \
  || { echo "LEGS_D10 FAILED rc=$?" >> $S/logs/legs_d10.log; exit 1; }
echo "LEGS_D10 DONE $(sha256sum $O/legs.npz | cut -c1-16)" >> $S/logs/legs_d10.log
