#!/bin/bash
# run_ksr.sh <PHASE> -- executor (protocol 10-f) of the King serving-refresh family (DECISION_RULE_king_serving_refresh_2026-09-27.md,
# lead 5b4fc6cda). NOT LAUNCHED until the lead gives the start time (October D10 F10 training has priority; rule §5).
# PHASE gates : gate 1 (S0 retrain == in-service a10b8725) + gate 2 (S1 2025 m0 duplicate) -> KSR_GATES PASS|STOP
#       arms  : S1 / S2R / S2T x windows 2023 2024 2025 2026F x m0..m7, and the RED arm (S0 permuted within anchor in the windows)
#       read  : IC reader (S1, S2R, S2T, RED) + offset spectrum
#       h2    : monthly-cutoff models 2022-08 .. 2026-08 (m0..m3), each scoring 12 months -> h2 reader
#       splice: spliced KING_OOF per member for the book cells (S1 m0..m7 and RED m0) -> handed to the book-cell owner; gate 4 is
#               dlarch_ksr_splice.py legs on the legs those cells build
# Gate order: phases after 'gates' refuse to start unless KSR_GATES PASS is in the log. Any failure -> 'KSR_STOP <why>' (line
# start); each phase ends with 'KSR_<PHASE>_DONE rc=<n>'. Writes: compressed OOFs; a 1 GiB write probe runs first (protocol, quota).
set -u
W=/workspace/dlarch_2026-09-24; A=$W/ksr_2026-09-27; LOG=$A/ksr.log; PY=/workspace/venv/bin/python; R=$W/receipts
PHASE=${1:?usage: run_ksr.sh gates|arms|read|h2|splice|book}
mkdir -p $A/arms $A/logs $A/splice
mkdir "$W/CHAIN/.claim_KSR" 2>/dev/null || { echo "KSR_STOP claim exists or cannot be created ($PHASE)" >> "$LOG"; exit 4; }
echo "pgid=$(ps -o pgid= -p $$ | tr -d ' ') pid=$$ owner=dlarch job=ksr_$PHASE started=$(date -u +%FT%TZ)" | tee "$W/CHAIN/.claim_KSR/owner" > "$A/ksr.pgid"
say(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
stop(){ echo "KSR_STOP $PHASE: $1" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KSR"; exit 1; }
ENV="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C"
declare -A START=([2023]=2023-10-01 [2024]=2024-10-01 [2025]=2025-10-01 [2026F]=2026-07-01)
declare -A END=([2023]=2024-01-01 [2024]=2025-01-01 [2025]=2026-01-01 [2026F]=2026-10-01)
declare -A N0Y=([2023]=2023 [2024]=2024 [2025]=2025 [2026F]=2026)
train(){ # <label> <args...>   (re-entrant: KING_OOF + KING_DONE => skip)
  local L=$1; shift
  if [ -s $A/arms/$L/KING_OOF.npz ] && grep -q KING_DONE $A/logs/train_$L.log 2>/dev/null; then return 0; fi
  rm -rf $A/arms/$L
  ( cd $A && $ENV nice -n 12 $PY -B dlarch_ksr_train.py --out $A/arms/$L --label y4s "$@" > $A/logs/train_$L.log 2>&1 )
  grep -q KING_DONE $A/logs/train_$L.log || { echo "FAIL $L" > $A/logs/FAIL_$L; return 1; }
}
pool(){ # run the queued "label args" lines 3 at a time
  rm -f $A/logs/FAIL_*
  while read -r L ARGS; do
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do sleep 5; done
    ls $A/logs/FAIL_* > /dev/null 2>&1 && break
    train $L $ARGS &
  done
  wait; ls $A/logs/FAIL_* > /dev/null 2>&1 && return 1; return 0
}
probe(){ dd if=/dev/zero of=$A/.probe bs=1M count=1024 conv=fsync status=none && [ "$(stat -c %s $A/.probe)" = 1073741824 ]; local rc=$?; rm -f $A/.probe; return $rc; }
say "KSR_${PHASE}_START devices train=$(sha256sum $A/dlarch_ksr_train.py | cut -c1-16) read=$(sha256sum $A/dlarch_ksr_read.py | cut -c1-16) splice=$(sha256sum $A/dlarch_ksr_splice.py | cut -c1-16)"
probe || stop "1 GiB write probe failed on /workspace (quota)"
[ "$PHASE" != gates ] && ! grep -q "^KSR_GATES PASS" "$LOG" && stop "gates not passed"
case $PHASE in
gates)
  printf "S0R --arm A0 --rs 0\nS1_2025_m0 --arm S1 --rs 0 --start 2025-10-01 --end 2026-01-01\nS1_2025_m0_dup --arm S1 --rs 0 --start 2025-10-01 --end 2026-01-01\n" | pool || stop "gate trainings failed"
  ( cd $A && $ENV OMP_NUM_THREADS=4 $PY -B dlarch_ksr_read.py gate12 $R/KSR_GATES12_2026-09-27.json $A/arms/S0R $A/arms/S1_2025_m0 $A/arms/S1_2025_m0_dup ${KSR_SERVING_RECEIPT:-} >> "$LOG" 2>&1 ) || stop "gate reader failed"
  grep -q "KSR_READ gate12 GATE1_PASS=True GATE2_PASS=True" "$LOG" && echo "KSR_GATES PASS" >> "$LOG" || stop "gate 1 or 2 failed" ;;
arms)
  { for Wn in 2023 2024 2025 2026F; do for m in 0 1 2 3 4 5 6 7; do
      echo "S1_${Wn}_m$m --arm S1 --rs $m --start ${START[$Wn]} --end ${END[$Wn]}"
      echo "S2R_${Wn}_m$m --arm S2R --rs $m --start ${START[$Wn]} --end ${END[$Wn]} --n0-year ${N0Y[$Wn]}"
      echo "S2T_${Wn}_m$m --arm S2T --rs $m --start ${START[$Wn]} --end ${END[$Wn]} --n0-year ${N0Y[$Wn]}"
    done; done; } | pool || stop "arm trainings failed"
  $PY -B - $A <<'PY' >> "$LOG" 2>&1 || stop "RED arm build failed"
import json, subprocess, sys, os
A = sys.argv[1]; man = json.load(open('/workspace/kingfam_2026-09-27/MANIFEST_IC.json'))['arms']['A0']
S = {'2023': ('2023-10-01', '2024-01-01'), '2024': ('2024-10-01', '2025-01-01'), '2025': ('2025-10-01', '2026-01-01'), '2026F': ('2026-07-01', '2026-10-01')}
for k, e in enumerate(man):
    for w, (s, t) in S.items():
        d = f'{A}/arms/RED_{w}_m{k}'
        if os.path.exists(f'{d}/KING_OOF.npz'): continue
        subprocess.run(['/workspace/venv/bin/python', '-B', f'{A}/dlarch_ksr_splice.py', 'red', e['path'], d, s, t, str(20260927 + k)], check=True)
PY
  say "arms built" ;;
read)
  $PY -B - $A <<'PY' || stop "manifest"
import json, sys
A = sys.argv[1]; a0 = json.load(open('/workspace/kingfam_2026-09-27/MANIFEST_IC.json'))['arms']['A0']
man = {'S0': {f'm{k}': e['path'] for k, e in enumerate(a0)}, 'arms': {}}
for arm in ('S1', 'S2R', 'S2T', 'RED'):
    man['arms'][arm] = {w: {f'm{k}': f'{A}/arms/{arm}_{w}_m{k}/KING_OOF.npz' for k in range(8)} for w in ('2023', '2024', '2025', '2026F')}
json.dump(man, open(f'{A}/MANIFEST_KSR.json', 'w'), indent=1)
PY
  ( cd $A && $ENV OMP_NUM_THREADS=4 $PY -B dlarch_ksr_read.py ic $R/KSR_IC_2026-09-27.json $A/MANIFEST_KSR.json >> "$LOG" 2>&1 ) || stop "ic reader failed"
  ( cd $A && $ENV OMP_NUM_THREADS=4 $PY -B dlarch_ksr_read.py spectrum $R/KSR_SPECTRUM_2026-09-27.json $A/MANIFEST_KSR.json >> "$LOG" 2>&1 ) || stop "spectrum reader failed" ;;
h2)
  { for m in 0 1 2 3; do $PY -c "
import calendar
y, mo = 2022, 8
while (y, mo) <= (2026, 8):
    ny, nm = y + (mo + 11) // 12, (mo + 11) % 12 + 1
    print(f'H2_{y}{mo:02d}_m$m --arm S1 --rs $m --start {y}-{mo:02d}-01 --end {ny}-{nm:02d}-01')
    y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
"; done; } | pool || stop "H2 trainings failed"
  $PY -B - $A <<'PY' || stop "h2 manifest"
import json, sys, glob, os
A = sys.argv[1]; man = {}
for m in range(4):
    man[f'm{m}'] = sorted([[d.split('_')[-2], f'{d}/KING_OOF.npz'] for d in glob.glob(f'{A}/arms/H2_*_m{m}')])
json.dump(man, open(f'{A}/MANIFEST_H2.json', 'w'), indent=1)
PY
  ( cd $A && $ENV OMP_NUM_THREADS=4 $PY -B dlarch_ksr_read.py h2 $R/KSR_H2_2026-09-27.json $A/MANIFEST_H2.json >> "$LOG" 2>&1 ) || stop "h2 reader failed" ;;
splice)
  $PY -B - $A <<'PY' >> "$LOG" 2>&1 || stop "splice build failed"
import json, subprocess, sys, os
A = sys.argv[1]; a0 = json.load(open('/workspace/kingfam_2026-09-27/MANIFEST_IC.json'))['arms']['A0']
jobs = [(arm, k) for arm in ('S1',) for k in range(8)] + [('RED', 0)]
for arm, k in jobs:
    d = f'{A}/splice/{arm}_m{k}'
    if os.path.exists(f'{d}/SPLICE_RECEIPT.json'): continue
    wins = [f'{A}/arms/{arm}_{w}_m{k}/KING_OOF.npz' for w in ('2023', '2024', '2025', '2026F')]
    subprocess.run(['/workspace/venv/bin/python', '-B', f'{A}/dlarch_ksr_splice.py', 'build', a0[k]['path'], d] + wins, check=True)
PY
  $PY -B - $A <<'PY' >> "$LOG" 2>&1 || stop "KSR_OOF_MANIFEST build failed"
# fresh2's driver schema (65df8b070): 17 cells, role == second name field, S0 without splice receipt, S1/RED with; KSR_S0_m0 = a10b8725
import json, sys, os, hashlib
A = sys.argv[1]
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()
a0 = json.load(open('/workspace/kingfam_2026-09-27/MANIFEST_IC.json'))['arms']['A0']
cells = {}
for k, e in enumerate(a0):
    assert sha(e['path']) == e['sha256']
    cells[f'KSR_S0_m{k}'] = {'role': 'S0', 'oof': e['path'], 'oof_sha256': e['sha256'], 'splice_receipt': None, 'splice_receipt_sha256': None}
for arm, ks in (('S1', range(8)), ('RED', [0])):
    for k in ks:
        d = f'{A}/splice/{arm}_m{k}'; o, r = f'{d}/KING_OOF.npz', f'{d}/SPLICE_RECEIPT.json'
        rr = json.load(open(r)); assert rr['out_sha256'] == sha(o)
        cells[f'KSR_{arm}_m{k}'] = {'role': arm, 'oof': o, 'oof_sha256': sha(o), 'splice_receipt': r, 'splice_receipt_sha256': sha(r),
                                   'S0_base': rr['S0'], 'windows': rr['windows']}
assert len(cells) == 17 and cells['KSR_S0_m0']['oof_sha256'].startswith('a10b872506ca60af')
p = f'{A}/splice/KSR_OOF_MANIFEST.json'; txt = json.dumps({'cells': cells}, indent=1)
open(p + '.tmp', 'w').write(txt)  # durable-exempt: small manifest, read back and compared before the atomic replace
assert open(p + '.tmp').read() == txt; os.replace(p + '.tmp', p)
print('KSR_OOF_MANIFEST', sha(p))
PY
  say "spliced OOFs + KSR_OOF_MANIFEST.json ready under $A/splice (fresh2 schema 65df8b070; gate 4 run by fresh2's driver)" ;;
book)
  # after fresh2's driver (65df8b070) wrote ^KSR_DONE in /dev/shm/mretrain_2026-09-26/logs/ksr.log; cell names from its
  # PREP_LIST_ksr.txt / ORDER_ksr.txt: KSR_S1_m*, KSR_S0_m* (m0 = hard link of SER_A0_m0), KSR_RED_m0, KSR_SEAT_ONLY_m0, KSR_COMP_ONLY_m0
  grep -q "^\S* *KSR_DONE" /dev/shm/mretrain_2026-09-26/logs/ksr.log || stop "fresh2 KSR driver has not written KSR_DONE"
  $PY -c "
import json
m = {'S1': {f'm{k}': f'KSR_S1_m{k}' for k in range(8)}, 'S0': {f'm{k}': f'KSR_S0_m{k}' for k in range(8)}, 'RED': {'m0': 'KSR_RED_m0'},
     'HYB': {'SEAT_ONLY': 'KSR_SEAT_ONLY_m0', 'COMP_ONLY': 'KSR_COMP_ONLY_m0'}}
json.dump(m, open('$A/cell_map.json', 'w'), indent=1)  # durable-exempt: tiny config written once, sha recorded by the reader
" || stop "cell map"
  ( cd $A && $ENV OMP_NUM_THREADS=4 $PY -B dlarch_ksr_book.py PATH,HOME,LC_CTYPE $A/cell_map.json /dev/shm/mretrain_2026-09-26/series \
      /workspace/ksr_2026-09-27/targets_stats $R/KSR_BOOK_2026-09-27.json >> "$LOG" 2>&1 ) || stop "book reader failed" ;;
*) stop "unknown phase" ;;
esac
RC=0; grep -q Traceback "$LOG" $A/logs/*.log 2>/dev/null && RC=1
echo "KSR_${PHASE^^}_DONE rc=$RC" >> "$LOG"; rm -rf "$W/CHAIN/.claim_KSR"
