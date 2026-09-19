#!/bin/bash
# Object B · S2 (PREREG §3 S2): in-service F10 recipe on GPU — F-REPRO reproduction run, then yearly folds 2023..2026 (s42 only), each followed by
# the np export (+ gate V1). Before EVERY GPU run the GPU must be idle (no compute process, memory.used < 500 MiB); if anyone else is on it, the
# remaining runs are NOT started (status file says why). Launched with setsid; the PGID is recorded by the caller. Writes only under $R.
set -u
R=/workspace/object_b_2026-09-19; D=$R/devices; M=$R/models; L=$R/logs; RC=$R/receipts
PY=/workspace/venv/bin/python
ENVB="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext"
STATUS=$L/F10_GPU_STATUS.txt
echo "start $(date -u +%FT%TZ) pgid $(ps -o pgid= $$ | tr -d ' ')" > $STATUS
gpu_idle() {
  local apps used
  apps=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c .)
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
  [ "$apps" = "0" ] && [ -n "$used" ] && [ "$used" -lt 500 ]
}
run_one() {   # $1 tag, $2 cutoff epoch or empty
  local tag=$1 cut=$2
  if ! gpu_idle; then echo "STOP before $tag: GPU not idle $(date -u +%FT%TZ) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | tr '\n' ';')" >> $STATUS; exit 4; fi
  echo "run $tag cutoff=${cut:-none} start $(date -u +%FT%TZ)" >> $STATUS
  if [ -n "$cut" ]; then
    $ENVB F10_CUTOFF=$cut F10_SAVE=$M/f10_ins_$tag.pt nice -n 5 $PY -B $D/f10_refit_fold.py > $L/f10_$tag.log 2>&1
  else
    $ENVB F10_SAVE=$M/f10_ins_$tag.pt nice -n 5 $PY -B $D/f10_refit_fold.py > $L/f10_$tag.log 2>&1
  fi
  local rc=$?; echo "run $tag rc=$rc end $(date -u +%FT%TZ)" >> $STATUS
  [ $rc -eq 0 ] || exit 5
}
export_one() {   # CPU np export + V1
  local tag=$1
  $ENVB F10_CK=$M/f10_ins_$tag.pt F10_NPOUT=$M/f10_ins_${tag}_np.npz CUDA_VISIBLE_DEVICES= nice -n 10 $PY -B $D/f10_np_export_fold.py > $L/f10_export_$tag.log 2>&1
  echo "export $tag rc=$? $(date -u +%FT%TZ) $(tail -1 $L/f10_export_$tag.log)" >> $STATUS
}
# 1) reproduction run (no cutoff) + comparator (+ negative control on the two in-service seeds)
run_one repro_full ""
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 CUDA_VISIBLE_DEVICES= nice -n 10 $PY -B $D/f10_repro_compare.py /workspace/f8_ext/models/f10_live_s42.pt $M/f10_ins_repro_full.pt $RC/F_REPRO.json > $L/f_repro.log 2>&1
echo "F_REPRO rc=$? $(tail -1 $L/f_repro.log)" >> $STATUS
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 CUDA_VISIBLE_DEVICES= nice -n 10 $PY -B $D/f10_repro_compare.py /workspace/f8_ext/models/f10_live_s42.pt /workspace/f8_ext/models/f10_live_s2027.pt $RC/F_REPRO_NEGCTRL.json --expect-different > $L/f_repro_neg.log 2>&1
echo "F_REPRO_NEGCTRL rc=$? $(tail -1 $L/f_repro_neg.log)" >> $STATUS
# 2) yearly folds: label end (E + 4h) < Y-01-01 00Z
for Y in 2023 2024 2025 2026; do
  CUT=$(date -u -d "$Y-01-01T00:00:00Z" +%s)
  run_one fold${Y}_s42 $CUT
  export_one fold${Y}_s42
done
echo "DONE $(date -u +%FT%TZ)" >> $STATUS
