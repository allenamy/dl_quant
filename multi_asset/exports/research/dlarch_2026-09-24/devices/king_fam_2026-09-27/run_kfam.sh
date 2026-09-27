#!/bin/sh
# run_kfam.sh -- King-family devices, one process group: T_net (+controls) then the IC red control.
# Terminal markers (line start): 'T_NET DONE|REFUSED_CONTROLS', then 'KING_IC RED_PASS=True|False'; final line 'KFAM_DONE rc=<n>'.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/king_fam_2026-09-27; LOG=$A/kfam.log; PY=/workspace/venv/bin/python
mkdir "$W/CHAIN/.claim_KFAM" 2>/dev/null || { echo "REFUSING: claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=king_family_tnet_red started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_KFAM/owner" > "$A/kfam.pgid"
cd "$A"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 $PY -B dlarch_t_net.py PATH,HOME,LC_CTYPE \
    "$A/T_NET.npz" "$W/receipts/T_NET_2026-09-27.json" >> "$LOG" 2>&1; RC=$?
if [ $RC -eq 0 ]; then
  env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 $PY -B dlarch_king_ic.py PATH,HOME,LC_CTYPE \
      "$A/T_NET.npz" "$W/receipts/T_NET_2026-09-27.json" /dev/shm/news2_2026-09-23/work/king/KING_OOF.npz \
      "$W/receipts/KING_IC_RED_2026-09-27.json" red >> "$LOG" 2>&1; RC=$?
fi
echo "KFAM_DONE rc=$RC" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KFAM"
