#!/bin/bash
# ksr_master.sh [preflight|run] -- process executor (§10-f) of the King-serving-refresh (KSR) book cells (fresh2 2026-09-27;
# DECISION_RULE_king_serving_refresh_2026-09-27.md 5b4fc6cda + rev 1 c1f9571b5; interface agreed with dlarch, lead-approved: gate 4 run
# by this process with the pinned device, gate-4 FAIL => whole family stops (rule §0), S0 m_k prepped before S1 m_k, prep concurrency 1,
# wait while /dev/shm < 4 GiB). Start time is the lead's (after the October D10 reading).
#   cells (18 labels x F10 s42/s2027 = 36 engine cells, PREP_LIST_ksr.txt / ORDER_ksr.txt): KSR_S1_m0..7, KSR_S0_m1..7, KSR_RED_m0
#   (descriptive), KSR_SEAT_ONLY_m0 / KSR_COMP_ONLY_m0 (rule §4 channels: S0_m0 legs with S1_m0's WL / KZ, rc_hybrid_legs.py).
#   KSR_S0_m0 = the in-service arm A0_m0: its legs (9ee5886f) and targets are exported, its series hardlinked, nothing re-run.
# King OOFs come from dlarch's KSR_OOF_MANIFEST.json (schema checked below; every file sha checked before use, paths never trusted).
# Per cell mr_prep.sh runs with MR_HOOK=ksr_hooks.sh: legs exported to $KSR_ROOT/legs, gate 4 (S1 / RED / hybrids), targets stats.
# Registered log: logs/ksr.log; terminal line-start "<ts> (STOP|KSR_DONE)"; preflight mode ends with KSR_PREFLIGHT_OK (or STOP).
set -uo pipefail
MODE=${1:-run}
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; L=$R/logs; LG=$L/ksr.log
export PV=/workspace/venv/bin/python KSR_ROOT=/workspace/ksr_2026-09-27
MAN=${KSR_MANIFEST:-/workspace/dlarch_2026-09-24/ksr_2026-09-27/splice/KSR_OOF_MANIFEST.json}
export KSR_SPLICE_DEV=$D/dlarch_ksr_splice.py KSR_SPLICE_SHA=9557d128585a9d4ff1a8f25daa5d2a91454a87ecc2cd9e129d4f948e705bd267
A0K_SHA=a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a; A0L_SHA=9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65
mkdir -p $L
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "STOP: $*"; exit 1; }
. $D/mr_stop.sh; mr_scope_begin $LG   # stop scope = STOP lines in ksr.log after this byte (inherited by preps / queue)
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"ksr_master.sh $MODE\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $L/PGID_ksr.json
say "KSR_START pgid=$PG mode=$MODE"
# ---- preflight: every input identity, before anything is created
[ "$(sha256sum $KSR_SPLICE_DEV | cut -c1-64)" = "$KSR_SPLICE_SHA" ] || stop "gate-4 device $KSR_SPLICE_DEV is not the pinned 9557d128 (239741547)"
[ -s $MAN ] || stop "KSR_OOF_MANIFEST missing: $MAN"
$PV - $MAN > $L/ksr_cells.txt 2> $L/ksr_cells.err <<'PY' || stop "manifest schema: $(tail -1 $L/ksr_cells.err)"
import json, sys
m = json.load(open(sys.argv[1]))["cells"]
need = ["KSR_S0_m%d" % k for k in range(8)] + ["KSR_S1_m%d" % k for k in range(8)] + ["KSR_RED_m0"]
missing = [n for n in need if n not in m]; assert not missing, "cells missing: %s" % missing
for n in need:
    c = m[n]; role = c["role"]; assert role == n.split("_")[1], (n, role)
    rc, rs = c.get("splice_receipt"), c.get("splice_receipt_sha256")
    assert (role == "S0") == (rc is None), "%s: S0 cells have no splice receipt, S1/RED must" % n
    print(n, role, c["oof"], c["oof_sha256"], rc or "-", rs or "-")
PY
while read -r n role oof osha rc rsha; do
  [ "$(sha256sum $oof 2>/dev/null | cut -c1-64)" = "$osha" ] || stop "$n OOF $oof sha != manifest $osha"
  [ "$rc" = - ] || [ "$(sha256sum $rc 2>/dev/null | cut -c1-64)" = "$rsha" ] || stop "$n splice receipt sha != manifest"
done < $L/ksr_cells.txt
grep -q "^KSR_S0_m0 S0 [^ ]* $A0K_SHA " $L/ksr_cells.txt || stop "manifest KSR_S0_m0 is not the in-service OOF a10b8725"
[ "$(sha256sum $R/arms/A0_m0/work/legs.npz | cut -c1-64)" = "$A0L_SHA" ] || stop "A0_m0 legs are not the in-service 9ee5886f"
for s in 42 2027; do [ -s $R/series/SER_A0_m0_s$s.npz ] && [ -s $R/arms/A0_m0/targets/TARGETS_NEWS2_s$s.npz ] || stop "A0_m0 s$s series/targets missing"; done
[ "$(wc -l < $D/PREP_LIST_ksr.txt)" = 18 ] && [ "$(wc -l < $D/ORDER_ksr.txt)" = 36 ] || stop "PREP_LIST_ksr / ORDER_ksr not 18 / 36 lines"
fresh=yes; ls -d $R/arms/KSR_* > /dev/null 2>&1 && fresh=no; [ -e $KSR_ROOT/legs ] && fresh=no
say "KSR_PREFLIGHT_OK cells=$(wc -l < $L/ksr_cells.txt) fresh=$fresh shm_avail_kb=$(df -k --output=avail /dev/shm | tail -1)"
[ "$MODE" = preflight ] && exit 0
[ $fresh = yes ] || stop "KSR arms or $KSR_ROOT/legs exist (a run starts fresh; archive them first)"
cell() { awk -v n=$1 -v f=$2 '$1 == n {print $f}' $L/ksr_cells.txt; }   # field 3 = OOF, 5 = splice receipt
# ---- S0 m0 = in-service A0_m0 (exported, not re-run)
mkdir -p $KSR_ROOT
KSR_GATE4_REF= bash $D/ksr_hooks.sh after_legs KSR_S0_m0 $R/arms/A0_m0 >> $L/ksr_hooks.log 2>&1 || stop "S0_m0 legs export (see $L/ksr_hooks.log)"
bash $D/ksr_hooks.sh after_targets KSR_S0_m0 $R/arms/A0_m0 >> $L/ksr_hooks.log 2>&1 || stop "S0_m0 targets stats"
for s in 42 2027; do ln -f $R/series/SER_A0_m0_s$s.npz $R/series/SER_KSR_S0_m0_s$s.npz || stop "S0_m0 series link"; done
say "S0_m0 = A0_m0 exported (legs, targets stats, series hardlinks)"
# ---- King pre-placed per cell (mr_prep then skips training); copy -> sha of the copy == manifest
place() {  # <LBL> <src> <sha>
  mkdir -p $R/arms/$1/work/king && cp $2 $R/arms/$1/work/king/KING_OOF.npz &&
  [ "$(sha256sum $R/arms/$1/work/king/KING_OOF.npz | cut -c1-64)" = "$3" ] || stop "$1 King copy sha != $3"; }
for n in KSR_S1_m0 KSR_S1_m1 KSR_S1_m2 KSR_S1_m3 KSR_S1_m4 KSR_S1_m5 KSR_S1_m6 KSR_S1_m7 KSR_S0_m1 KSR_S0_m2 KSR_S0_m3 KSR_S0_m4 KSR_S0_m5 KSR_S0_m6 KSR_S0_m7 KSR_RED_m0; do
  place $n $(cell $n 3) $(cell $n 4); done
place KSR_SEAT_ONLY_m0 $(cell KSR_S0_m0 3) $(cell KSR_S0_m0 4)   # SEAT_ONLY: the book ranks by S0's King, only the seats move
place KSR_COMP_ONLY_m0 $(cell KSR_S1_m0 3) $(cell KSR_S1_m0 4)   # COMP_ONLY: the book ranks by S1's King, the seats stay S0's
say "King placed for 18 cells"
# ---- engine queue (one cell at a time, team gates inside), started now; it waits for each READY in ORDER_ksr order
mr_guard "ksr engine queue" || stop "STOP before the engine queue"; bash $D/mr_engine_queue.sh $D/ORDER_ksr.txt ksr > $L/engine_queue_ksr.out 2>&1 &
PE=$!
# ---- preps, one at a time, S0 m_k before S1 m_k (PREP_LIST_ksr order)
while read -r LBL; do
  [ -z "$LBL" ] && continue
  while [ "$(df -k --output=avail /dev/shm | tail -1)" -lt 4194304 ]; do mr_stopped && stop "STOP while waiting for /dev/shm >= 4 GiB before $LBL"; sleep 60; done
  ARM=${LBL%_m*}; M=${LBL##*_m}
  case $LBL in
    KSR_S0_*) REF=""; RCP="" ;;
    KSR_S1_*) REF=$KSR_ROOT/legs/KSR_S0_m$M.npz; RCP=$(cell $LBL 5) ;;
    KSR_RED_m0) REF=$KSR_ROOT/legs/KSR_S0_m0.npz; RCP=$(cell KSR_RED_m0 5) ;;
    KSR_SEAT_ONLY_m0|KSR_COMP_ONLY_m0) REF=$KSR_ROOT/legs/KSR_S0_m0.npz; RCP=$(cell KSR_S1_m0 5)
      if [ ! -s $R/arms/KSR_SEAT_ONLY_m0/receipts/P3_LEGS.json ]; then
        $PV -B $D/rc_hybrid_legs.py $KSR_ROOT/legs/KSR_S0_m0.npz $KSR_ROOT/legs/KSR_S1_m0.npz $R/arms/KSR_SEAT_ONLY_m0 $R/arms/KSR_COMP_ONLY_m0 > $L/ksr_hybrid_legs.log 2>&1
        grep -q "^RC_HYBRID_LEGS DONE" $L/ksr_hybrid_legs.log || stop "hybrid legs: $(grep RC_HYBRID_LEGS $L/ksr_hybrid_legs.log | tail -1)"
        say "$(grep 'differing arrays' $L/ksr_hybrid_legs.log)"
      fi ;;
    *) stop "unknown cell $LBL" ;;
  esac
  [ -z "$REF" ] || [ -s $REF ] || stop "gate-4 reference $REF missing before $LBL (order)"
  mr_guard "prep $LBL" || stop "STOP before prep $LBL"; KSR_GATE4_REF=$REF KSR_SPLICE_RECEIPT=$RCP MR_HOOK=$D/ksr_hooks.sh bash $D/mr_prep.sh $ARM $M train > $L/prep_$LBL.out 2>&1 || { touch $R/PREP_QUEUE_ksr_STOPPED; stop "prep $LBL failed (see $L/$LBL/prep.log and $L/$LBL/hook.log)"; }
  say "prep $LBL READY $(grep -h 'GATE4' $L/$LBL/hook.log 2>/dev/null | tail -1 | cut -c1-120)"
done < $D/PREP_LIST_ksr.txt
touch $R/PREP_QUEUE_ksr_DONE; say "PREP_QUEUE_ksr_DONE"
wait $PE; rc=$?
say "engine queue rc=$rc"
[ $rc -eq 0 ] || stop "engine queue (ksr) rc=$rc (see $L/engine/queue.log)"
n=0; while read -r LBL S; do [ -s $R/series/SER_${LBL}_s$S.npz ] || stop "series SER_${LBL}_s$S missing after the queue"; n=$((n + 1)); done < $D/ORDER_ksr.txt
say "KSR_DONE series=$n (+ KSR_S0_m0 x2 hardlinked) legs=$KSR_ROOT/legs gate4=$KSR_ROOT/gate4 targets_stats=$KSR_ROOT/targets_stats"
