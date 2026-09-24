#!/bin/bash
# B8: recompute the seat for a shorter msharpe_look (fa_b8seat.py, G1-gated), rebuild the combo with it, then hand
# over to the already-exercised b_pipe2.sh for adapter -> guard -> engine -> extract -> gated delete.
# PREREG docs/PREREG_fresh_rootcause_B8_2026-09-24.md (38f4c0fbd).
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
ARMROOT=$1; SEED=$2; LOOK=$3
ARMNAME=$(basename $ARMROOT | cut -d_ -f1)
if [ "$ARMNAME" = "fresh" ]; then BASE="FRESH_s${SEED}"; SEATARM=FRESH; else BASE="NEWS_s${SEED}"; SEATARM=NEWS; fi
VAR="B8L${LOOK}"; TAG="${VAR}_${ARMNAME}_s${SEED}"
VDIR=$FA/bvar/${VAR}_$(basename $ARMROOT)_s${SEED}
SEAT=$FA/b8/WL_${SEATARM}_look${LOOK}.npz
[ -s "$SEAT" ] || { echo "[$TAG] seat file missing: $SEAT"; exit 7; }
# stage gate: combo (~60 MiB) + engine cell (~440 MiB) + 1 GiB headroom, news2 has priority
PRED=500
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/logs
# 1. combo with the recomputed seat (asserts the seat actually differs from look=900)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B $W/devices/fa_b8combo.py PATH,HOME,LC_CTYPE \
  --legs-root $ARMROOT --f10-root $ARMROOT --seed $SEED --out $VDIR --seat-npz $SEAT \
  > $FA/logs/combo_$TAG.log 2>&1
tail -1 $FA/logs/combo_$TAG.log
# 2. variant target receipt + combo-level behavioural difference (asserts the seat reached the book)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $ARMROOT/work/combo_s${SEED} $VDIR 2>&1 | tail -1
# 3. adapter -> guard -> engine -> extract -> gated delete (unchanged, already exercised 8x in stage B)
bash $W/devices/b_pipe2.sh $VAR $ARMROOT $SEED
