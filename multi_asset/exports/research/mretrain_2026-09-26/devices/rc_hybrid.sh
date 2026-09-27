#!/bin/bash
# rc_hybrid.sh -- (3b) executor (§10-f) of the King root-cause single-condition cells SEAT_ONLY / COMP_ONLY x F10 seeds 42/2027
# (dlarch's request, fresh2 2026-09-27; DESCRIPTIVE, no gate): hybrid legs -> mr_prep (combo/specs/adapter/configs; King and legs
# pre-placed so neither is retrained) -> mr_engine_queue.sh in rootcause mode (no family red/family reading) -> rc_read.py.
# Registered log: logs/rootcause.log; terminal lines ^\S+ (STOP|RC_HYBRID_DONE).
set -uo pipefail
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; PV=/workspace/venv/bin/python; O=/workspace/mretrain_2026-09-26/redcause
LG=$R/logs/rootcause.log
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
stop() { say "STOP: $*"; exit 1; }
. $D/mr_stop.sh; mr_scope_begin $LG   # stop scope = STOP lines in rootcause.log after this byte (inherited by preps / queue)
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"rc_hybrid.sh\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"self_reported\":true}" > $R/logs/PGID_rootcause.json
say "RC_HYBRID_START pgid=$PG"
grep -q "RC_REGEN DONE" $O/regen.log || stop "RED legs regeneration not DONE (see $O/regen.log)"
$PV -B $D/rc_hybrid_legs.py $R/arms/A0_m0/work/legs.npz $O/legs_RED.npz $R/arms/SEAT_ONLY_m0 $R/arms/COMP_ONLY_m0 > $R/logs/rc_hybrid_legs.log 2>&1
grep -q "^RC_HYBRID_LEGS DONE" $R/logs/rc_hybrid_legs.log || stop "hybrid legs: $(grep RC_HYBRID_LEGS $R/logs/rc_hybrid_legs.log | tail -1)"
say "$(grep 'differing arrays' $R/logs/rc_hybrid_legs.log)"
for H in SEAT_ONLY COMP_ONLY; do
  W=$R/arms/${H}_m0; mkdir -p $W/work/king
  K=$R/arms/A0_m0/work/king/KING_OOF.npz; [ $H = COMP_ONLY ] && K=$O/king_RED/KING_OOF.npz   # the King scores the book of this cell ranks by
  [ -s $W/work/king/KING_OOF.npz ] || cp $K $W/work/king/KING_OOF.npz
  mr_guard "prep ${H}_m0" || stop "family STOP before prep ${H}_m0"; MR_MASTER_LOG=$LG bash $D/mr_prep.sh $H 0 train > $R/logs/prep_${H}_m0.out 2>&1 || stop "prep ${H}_m0 failed (see $R/logs/${H}_m0/prep.log)"
  say "prep ${H}_m0 READY $(grep -h 'combo done\|PREP_DONE' $R/logs/${H}_m0/prep.log | tail -1)"
done
mr_guard "engine queue (rootcause)" || stop "family STOP before the engine queue"; bash $D/mr_engine_queue.sh $D/ORDER_rc.txt rootcause > $R/logs/engine_queue_rc.out 2>&1 || stop "engine queue (rootcause) rc!=0 (see $R/logs/engine/queue.log)"
mkdir -p $R/receipts
$PV -B $D/rc_read.py $R/receipts/RC_READ_hybrid.json > $R/logs/rc_read.log 2>&1 || stop "rc_read failed (see $R/logs/rc_read.log)"
say "$(grep '^RC_READ' $R/logs/rc_read.log | head -1)"
say "RC_HYBRID_DONE"
