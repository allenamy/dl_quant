#!/bin/bash
# Plan B (lead 2026-09-23 23:5xZ): King determinism / environment sensitivity on NC_FEATURES 3c886a2b, using news2's trainer
# news2_train_king.py (b19459a5) COPIED with ONLY line 13 (root W) changed to a per-run root on the container disk (not /dev/shm).
# Runs one at a time, nice 10, CUDA_VISIBLE_DEVICES empty; each run's outputs are deleted after its sha is recorded.
set -u
R=/root/nc_king_env_2026-09-23; SRC=/dev/shm/news2_2026-09-23/devices/news2_train_king.py; FOLDS=/dev/shm/news_2026-09-23/devices/king_folds.py
FEAT=/dev/shm/nc_2026-09-23/work/NC_FEATURES.npz; FREC=/dev/shm/nc_2026-09-23/receipts/NC_FEATURES.json
PV=/workspace/venv/bin/python; NPYV="X86_V4 AVX512_ICL AVX512_SPR"
mkdir -p $R; OUT=$R/RESULTS.jsonl; [ -e $OUT ] && mv $OUT $R/RESULTS_attempt1_rc127.jsonl
[ "$(sha256sum $SRC | cut -c1-16)" = b19459a54eed64af ] || { echo "trainer sha changed"; exit 3; }
[ "$(sha256sum $FOLDS | cut -c1-16)" = 4886c278c12b0f51 ] || { echo "folds sha changed"; exit 3; }
setup() {  # $1 run name, $2 optional sed for the thread-pin line
  local d=$R/$1; rm -rf $d; mkdir -p $d/work $d/receipts $d/devices
  ln -s $FEAT $d/work/NEWS_FEATURES.npz; cp $FREC $d/receipts/P2B_FEATURES.json; cp $FOLDS $d/devices/king_folds.py
  sed "s#^W = pathlib.Path('/dev/shm/news2_2026-09-23')#W = pathlib.Path('$d')#" $SRC > $d/devices/news2_train_king.py
  [ -n "${2:-}" ] && sed -i "$2" $d/devices/news2_train_king.py
  diff $SRC $d/devices/news2_train_king.py > $d/trainer.diff
}
run() {  # $1 name, $2 interpreter, $3 NPY (set|unset), $4 outer OMP ('' = unset), $5 outer OPENBLAS, $6 note
  local d=$R/$1; cd $d/devices; local t0=$(date -u +%H:%M:%S)
  local E=(PATH=/usr/bin:/bin HOME=/root CUDA_VISIBLE_DEVICES=)
  [ "$3" = set ] && E+=("NPY_DISABLE_CPU_FEATURES=$NPYV")
  [ -n "$4" ] && E+=("OMP_NUM_THREADS=$4"); [ -n "$5" ] && E+=("OPENBLAS_NUM_THREADS=$5")
  echo "env: ${E[*]}" > $d/king.env
  env -i "${E[@]}" nice -n 10 $2 -u news2_train_king.py > $d/king.log 2>&1
  local rc=$?; local s=$(sha256sum $d/work/king/KING_OOF.npz 2>/dev/null | cut -d' ' -f1)
  local rs=$($PV -c "import json;print(json.load(open('$d/work/king/TRAIN_RECEIPT.json'))['predictions_sha256'])" 2>/dev/null)
  echo "{\"run\":\"$1\",\"start\":\"$t0\",\"end\":\"$(date -u +%H:%M:%S)\",\"rc\":$rc,\"interpreter\":\"$2\",\"NPY\":\"$3\",\"outer_OMP\":\"$4\",\"outer_OPENBLAS\":\"$5\",\"trainer_diff_lines\":$(grep -c '^[<>]' $d/trainer.diff),\"predictions_sha256\":\"$rs\",\"file_sha256\":\"$s\",\"note\":\"$6\"}" | tee -a $OUT
  cp $d/trainer.diff $R/$1.trainer.diff; cp $d/king.log $R/$1.king.log; cp $d/king.env $R/$1.king.env; rm -rf $d
}
setup b1; run b1 $PV set "" "" "baseline: driver pins (venv path + NPY set, outer threads unset)"
setup b2; run b2 $PV set "" "" "baseline repeat (determinism)"
setup w1; run w1 $PV set 1 1 "wiring check: OUTER OMP=OPENBLAS=1 (the trainer overwrites both at L8 before numpy import)"
setup t1 "s#^os.environ\['OMP_NUM_THREADS'\] = '8'; os.environ\['OPENBLAS_NUM_THREADS'\] = '2'#os.environ['OMP_NUM_THREADS'] = '1'; os.environ['OPENBLAS_NUM_THREADS'] = '1'#"
run t1 $PV set "" "" "real thread sensitivity: IN-CODE pin changed to OMP=1 OPENBLAS=1 (L8)"
echo DONE
