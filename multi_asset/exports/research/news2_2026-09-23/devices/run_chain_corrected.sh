#!/bin/bash
# The corrected P3 chain, with EACH STEP'S ENVIRONMENT COPIED FROM news_chain_resume.sh (the NEW_S
# scheme as actually run, incl. AMENDMENT 2 lead ruling (a) which moved King from P314 to PV).
#
# Why this rerun exists: my first pass launched King and legs with plain `python3` and no
# NPY_DISABLE_CPU_FEATURES, because I read the device names instead of the chain script. The scheme
# pins the environment per step, so the rerun aligns with it.
#
# ★ RETRACTED (2026-09-24): this header used to claim the environment CHANGES the trained model,
# citing three different KING_OOF.npz file shas. That was wrong -- a .npz file sha is not a content
# identity. Comparing the arrays, the predictions `P` are BITWISE IDENTICAL across all three
# environments (8,566,057 cells, 0 different); the file shas differ only through the per-anchor
# `model_sha256` array stored in the same archive. See receipts/KING_ENV_SENSITIVITY.json.
# The reason to align with the scheme is that the scheme says so, NOT that the numbers would move.
set -e
W=/dev/shm/news2_2026-09-23; D=$W/devices; L=$W/logs
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"
cd $D

# keep the two earlier King runs for the record, then clear so the device's mkdir can run
rm -rf $W/work/king_run3_syspy_envset
[ -d $W/work/king ] && mv $W/work/king $W/work/king_run3_syspy_envset
echo "$(date -u +%H:%M:%S) king (PV + NPY_DISABLE set, as news_chain_resume.sh line 14)"
nice -n 10 $PV -u news2_train_king.py > $L/chain_king_corrected.log 2>&1
echo "king rc=$?"
python3 - <<"PY"
import json
r1 = json.load(open("/dev/shm/news2_2026-09-23/work/king_run1_wrongenv/TRAIN_RECEIPT.json"))["predictions_sha256"]
r3 = json.load(open("/dev/shm/news2_2026-09-23/work/king_run3_syspy_envset/TRAIN_RECEIPT.json"))["predictions_sha256"]
r4 = json.load(open("/dev/shm/news2_2026-09-23/work/king/TRAIN_RECEIPT.json"))["predictions_sha256"]
print(f"  run1 syspy  no-env  {r1}")
print(f"  run3 syspy  env-set {r3}")
print(f"  run4 PV     env-set {r4}   <- the scheme")
print("  run3 == run4 (interpreter does not matter, only the env var):", r3 == r4)
print("  run1 == run4 (my first pass was wrong):", r1 == r4)
PY

# legs: P314, OMP/OPENBLAS=1, NPY_DISABLE set (news_chain_resume.sh line 15)
rm -f $W/work/legs.npz $W/work/NC_LEGS_RECEIPT.json $W/receipts/P3_LEGS.json
echo "$(date -u +%H:%M:%S) legs (P314, OMP=1, NPY_DISABLE set)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NC_W=$W NC_TREE=$W/treeNC5_deploy nice -n 10 $P314 -u nc_legs.py \
  $W/work/NEWS_FEATURES.npz $W/work/king/KING_OOF.npz $W/work/legs.npz > $L/chain_legs_corrected.log 2>&1
echo "legs rc=$?"
tail -2 $L/chain_legs_corrected.log
echo "CORRECTED_P3_DONE $(date -u +%H:%M:%S)"
