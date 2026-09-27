#!/bin/sh
# run_kic.sh -- executor (protocol 10-f) for the King-family IC readout: waits on fresh2's manifest executor, bound to its
# PGID (argv 1) AND the line-start marker in its log; then reads KN and A1 through dlarch_king_ic.py PAIRED mode (addendum 1:
# the manifest must carry an "A0" list of 8 members m0..m7; m0 = in-service rs=0).
# Terminal line (line start): 'KIC_DONE rc=<n>' ; 'KIC_STOP <why>' on any failure. Traceback anywhere = failure.
set -u
W=/workspace/dlarch_2026-09-24; A=$W/king_fam_2026-09-27; LOG=$A/kic.log; PY=/workspace/venv/bin/python
FL=/workspace/kingfam_2026-09-27/logs/kingfam.log; FPG=${1:?usage: run_kic.sh <fresh2 paired-manifest executor PGID>}
mkdir "$W/CHAIN/.claim_KIC" 2>/dev/null || { echo "KIC_STOP claim exists or cannot be created" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=king_ic_readout started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_KIC/owner" > "$A/kic.pgid"
stop(){ echo "KIC_STOP $1" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KIC"; exit 1; }
for i in $(seq 1 720); do                                    # bound 720 x 10 s = 2 h
  if grep -qE '^\S+ KF_MANIFEST_IC_PAIRED_DONE ' "$FL" 2>/dev/null; then break; fi
  if grep -qE '^\S+ KF_MANIFEST_IC STOP|^\S+ STOP:' "$FL" 2>/dev/null; then stop "fresh2 wrote STOP"; fi
  if ! ps -eo pgid= | grep -qx " *$FPG"; then
    grep -qE '^\S+ KF_MANIFEST_IC_PAIRED_DONE ' "$FL" 2>/dev/null && break
    stop "fresh2 manifest executor PGID $FPG gone without a DONE line"
  fi
  sleep 10
done
L=$(grep -E '^\S+ KF_MANIFEST_IC_PAIRED_DONE ' "$FL" | tail -1); [ -n "$L" ] || stop "bound expired without DONE"
MP=$(echo "$L" | sed -E 's/^\S+ KF_MANIFEST_IC_PAIRED_DONE (\S+) sha=([0-9a-f]{64}).*/\1/'); MS=$(echo "$L" | sed -E 's/^\S+ KF_MANIFEST_IC_PAIRED_DONE (\S+) sha=([0-9a-f]{64}).*/\2/')
[ "$(sha256sum "$MP" | cut -c1-64)" = "$MS" ] || stop "manifest sha differs from the DONE line"
echo "$(date -u +%T) manifest $MP sha $MS verified" >> "$LOG"
RC=0
for ARM in KN A1; do
  cd "$A" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 $PY -B dlarch_king_ic.py PATH,HOME,LC_CTYPE \
      "$A/T_NET.npz" "$W/receipts/T_NET_2026-09-27.json" /dev/shm/news2_2026-09-23/work/king/KING_OOF.npz \
      "$W/receipts/KING_IC_${ARM}_2026-09-27.json" paired "$ARM" "$MP" >> "$LOG" 2>&1 || RC=1
done
grep -q Traceback "$LOG" && RC=1
echo "KIC_DONE rc=$RC" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KIC"
