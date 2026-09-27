#!/bin/bash
# a1seat_driver.sh -- process executor of docs/DECISION_RULE_A1_seat_decomp_2026-09-27.md (b41ac9985 + rev 1 552475325; DESCRIPTIVE,
# the verdict is the lead's). A1_m0 vs A0_m0, F10 seeds 42/2027, three cells FULL (= A1_m0) / SEAT_ONLY / COMP_ONLY, same devices as
# (3b): fresh2's rc_hybrid_legs.py / mr_combo / nc_legs / mr_stop verbatim (sha literals below); mr_prep.sh and mr_engine_queue.sh
# with ONLY the root relocated (a1seat_prep.DIFF.txt / a1seat_engine_queue.DIFF.txt); reading rc_read_a1.py (rc_read.py + DIFF).
# fresh2's root /dev/shm/mretrain_2026-09-26 and kingfam are READ ONLY. Working root $R on /dev/shm (mr_prep hard-links the 2.8 GB
# NEWS_FEATURES, which cannot cross into /workspace); every product is mirrored to $W2 = /workspace/a1seat_2026-09-27 at the end.
# Phases: P (prep + identity controls, no engine, no reading) -> G (leak gate: A1LEAK_DONE rc=0 AND $W2/LEAK_CLEARED written by the
# lead; $W2/LEAK_FOUND or A1LEAK_STOP or rc!=0 => STOP, not run) -> E (6 engine cells) -> R (reader identity control vs 3b 2e75f1b3,
# then block 30 = judged, block 7 = reference). Registered log $LG; terminal lines ^\S+ (STOP|A1SEAT_DONE).
set -uo pipefail
R=/dev/shm/a1seat_2026-09-27; F=/dev/shm/mretrain_2026-09-26; FD=$F/devices; W2=/workspace/a1seat_2026-09-27; AD=$W2/devices
PV=/workspace/venv/bin/python; KF=/workspace/kingfam_2026-09-27/arms; LEAKLOG=/workspace/dlarch_2026-09-24/a1leak_2026-09-27/a1leak.log
LG=$R/logs/rootcause.log   # the name mr_engine_queue.sh gives the registered log of any non-family queue
mkdir -p $R/logs $R/arms $R/series $R/receipts $R/gate $W2/receipts $W2/logs
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $LG; }
mirror() { mkdir -p $W2/mirror && cp -r $R/logs $R/receipts $R/series $W2/mirror/ 2>/dev/null; cp -f $R/a1legs/regen.log $R/a1legs/NC_LEGS_RECEIPT.json $W2/mirror/ 2>/dev/null; true; }
stop() { say "STOP: $*"; mirror; exit 1; }
. $FD/mr_stop.sh; mr_scope_begin $LG
PG=$(ps -o pgid= -p $$ | tr -d ' ')
echo "{\"what\":\"a1seat_driver.sh\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"self_sha256\":\"$(sha256sum $0 | cut -c1-64)\"}" > $R/logs/PGID_a1seat.json
say "A1SEAT_START pgid=$PG driver=$(sha256sum $0 | cut -c1-16)"
# ---- literal constants: devices (fresh2's verbatim + mine) and inputs; any mismatch => STOP before anything is written
chk() { local h; h=$(sha256sum "$2" 2>/dev/null | cut -c1-64); [ "$h" = "$1" ] || stop "sha mismatch $2: ${h:-unreadable} != $1"; }
chk 1b8d96437c573f30db2d7f2c885a71345ed025d771ae6cb3a8344371442562df $FD/rc_hybrid_legs.py
chk 18387627f8426a45135b348dd4508281b4811894c91eb50af87751760609c0a0 $FD/nc_legs.py
chk f722ab2e16e344155c4b80c1e67899958a008e4d56559bc2e9fb3aefec26bb03 $FD/mr_combo.py
chk d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544 $FD/combo_target.py
chk 084fbf8df3bcffd45681c42333b2e8b672f2fe25ec9ebd47ff843a306bbb1e26 $FD/mr_stop.sh
chk 0245f1682eac2ee10b751bd3b2ee699d0ba41845bbc0ae9fe0035fb5c93ea013 $FD/mr_gates.py
chk 3d0ca94ad93da3fa73c8a78222141c475c0cadf6ad39de838c468c8ed3673dc5 $FD/news2_adapter_specs.py
chk 3dd2d635d053ab121884e31b0ee3b7b48b4e9a1f502246ae461413a1f51db5ff $FD/rc_read.py
chk a2dccf15a232a546c886e12fb2e1cd5522762509f42edd324eb3df4e57d17855 /dev/shm/fresh_2026-09-23/devices/fa_ladsave.py
chk 6ab6846e7116f441704c2de87d9e4f84564547d667c4487e629c5183c361aec4 /dev/shm/fresh_2026-09-23/devices/memgate.sh
chk 3c4073061b42a4a52db3bda817a9cc15dcb2a8bea3b97448cc825b5fe41d4af5 $AD/a1seat_prep.sh
chk 3a30dbfc0762b10c1172bac07063cf7f83f20f3c4b2055e49a214994d8c5bacb $AD/a1seat_engine_queue.sh
chk 00be5aae052d10aa0a09c9d80a5b1144fb4e347ae55bcf9a91063f149ce15e39 $AD/a1seat_regen_legs.sh
chk 1a474b194c1b4774c1179a6fcf62e2c8297ca565192358d743879bed85194083 $AD/rc_read_a1.py
chk 9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65 $F/arms/A0_m0/work/legs.npz
chk 2e42cabf424a52c80fcc2fd1508734b9934c32e86a859c711555f3cac46c073d $F/arms/A0_m0/work/king/KING_OOF.npz
chk 11bbaeb1bdb1b85ecaa097e7c66ab5e151a8a779c128e2b8ad99aa6b705ada1c $KF/A1_m0/KING_OOF.npz
chk 011607e2d0663c44d71957d22365a9fe7d43fa974994e89940a75dd31735db05 $F/gate/A1_m0_dup/DUP_CHECK.json
chk 074e8fb25238e5a2b036bf98e105b33d7a7c6bd82a98a009320749e09b330564 $F/series/SER_A0_m0_s42.npz
chk 421ff513a07befd812ca285102de8693038bdf7da09790fcc762a84dbf13c039 $F/series/SER_A0_m0_s2027.npz
chk 2e75f1b38fe3888985aa7b0f94cfea85e03b43facb0dccd88470e59e778ed685 $F/receipts/RC_READ_hybrid.json
say "literal constants: 21/21 match"
# ======== phase P: prep + identity controls (no engine cell, no reading)
bash $AD/a1seat_regen_legs.sh > $R/logs/regen_legs.out 2>&1 || stop "A1 legs regeneration (see $R/a1legs/regen.log)"
say "$(tail -1 $R/a1legs/regen.log)"
# FULL = A1_m0: King OOF + legs pre-placed (so mr_prep neither retrains nor recomputes legs); fresh2's A1_m0 duplicate-training PASS copied
W=$R/arms/A1_m0; mkdir -p $W/work/king $W/receipts $R/gate/A1_m0_dup
[ -e $W/READY_s42 ] && [ -e $W/READY_s2027 ] || {
  cp -n $R/a1legs/king_A1/KING_OOF.npz $W/work/king/KING_OOF.npz; cp -n $R/a1legs/legs_A1.npz $W/work/legs.npz
  cp -n $R/a1legs/NC_LEGS_RECEIPT.json $W/work/NC_LEGS_RECEIPT.json; cp -n $R/a1legs/NC_LEGS_RECEIPT.json $W/receipts/P3_LEGS.json
  cp -n $F/gate/A1_m0_dup/DUP_CHECK.json $R/gate/A1_m0_dup/DUP_CHECK.json; }
mr_guard "prep A1_m0" || stop "STOP before prep A1_m0"; MR_MASTER_LOG=$LG bash $AD/a1seat_prep.sh A1 0 train > $R/logs/prep_A1_m0.out 2>&1 || stop "prep A1_m0 failed (see $R/logs/A1_m0/prep.log)"
# identity control P: the relocated prep reproduces fresh2's A1_m0 engine targets bitwise
chk 7cb8dbf42d47c9d9213e33f0517fc3cd907fd2fd0253766ad418fc6b4e4d108f $W/targets/TARGETS_NEWS2_s42.npz
chk db47157fcb27b26134eacc4c3edd33b4b3a347d324f41e21592c4ebc0f0e75c4 $W/targets/TARGETS_NEWS2_s2027.npz
say "IDCTRL_PREP PASS: relocated prep reproduces fresh2 A1_m0 targets s42 7cb8dbf4 / s2027 db47157f"
# hybrids: fresh2's rc_hybrid_legs.py verbatim, A1 legs in the RED slot (the device's names; arrays other than KZ/LR/WL differing => it stops)
$PV -B $FD/rc_hybrid_legs.py $F/arms/A0_m0/work/legs.npz $R/a1legs/legs_A1.npz $R/arms/SEAT_ONLY_m0 $R/arms/COMP_ONLY_m0 > $R/logs/rc_hybrid_legs.log 2>&1
grep -q "^RC_HYBRID_LEGS DONE" $R/logs/rc_hybrid_legs.log || stop "hybrid legs: $(grep RC_HYBRID_LEGS $R/logs/rc_hybrid_legs.log | tail -1)"
say "$(grep 'differing arrays' $R/logs/rc_hybrid_legs.log)"
for H in SEAT_ONLY COMP_ONLY; do
  W=$R/arms/${H}_m0; mkdir -p $W/work/king
  K=$F/arms/A0_m0/work/king/KING_OOF.npz; [ $H = COMP_ONLY ] && K=$R/a1legs/king_A1/KING_OOF.npz   # the King scores the book of this cell ranks by
  [ -s $W/work/king/KING_OOF.npz ] || cp $K $W/work/king/KING_OOF.npz
  mr_guard "prep ${H}_m0" || stop "STOP before prep ${H}_m0"; MR_MASTER_LOG=$LG bash $AD/a1seat_prep.sh $H 0 train > $R/logs/prep_${H}_m0.out 2>&1 || stop "prep ${H}_m0 failed (see $R/logs/${H}_m0/prep.log)"
  say "prep ${H}_m0 READY $(grep -h 'PREP_DONE\|already READY' $R/logs/${H}_m0/prep.log | tail -1)"
done
say "PHASE_P_DONE"
# ======== phase G: leak gate (the executor does not judge leakage; the lead's marker does)
waited=0
while :; do
  [ -e $W2/LEAK_FOUND ] && stop "lead marker LEAK_FOUND ($(head -c 300 $W2/LEAK_FOUND | tr '\n' ' ')) -> not run (rule rev 1 item 3)"
  grep -qE '^A1LEAK_STOP' $LEAKLOG 2>/dev/null && stop "leak audit ended A1LEAK_STOP -> not run"
  L=$(grep -E '^A1LEAK_DONE rc=' $LEAKLOG 2>/dev/null | tail -1)
  if [ -n "$L" ]; then
    [ "$L" = "A1LEAK_DONE rc=0" ] || stop "leak audit ended '$L' -> not run"
    [ -s $W2/LEAK_CLEARED ] && break
  fi
  [ $waited = 0 ] && say "WAITING leak gate (audit terminal: ${L:-none}; LEAK_CLEARED absent)"; waited=1
  mr_stopped && stop "STOP during leak-gate wait"
  sleep 300
done
say "LEAK_GATE PASS: '$L' + LEAK_CLEARED sha $(sha256sum $W2/LEAK_CLEARED | cut -c1-16): $(head -c 300 $W2/LEAK_CLEARED | tr '\n' ' ')"
# ======== phase E: engine cells (control A0_m0 series = fresh2's, literal-checked above, copied)
cp -n $F/series/SER_A0_m0_s42.npz $F/series/SER_A0_m0_s2027.npz $R/series/
printf 'A1_m0 42\nA1_m0 2027\nSEAT_ONLY_m0 42\nSEAT_ONLY_m0 2027\nCOMP_ONLY_m0 42\nCOMP_ONLY_m0 2027\n' > $R/ORDER_a1seat.txt
mr_guard "engine queue" || stop "STOP before the engine queue"; bash $AD/a1seat_engine_queue.sh $R/ORDER_a1seat.txt rootcause > $R/logs/engine_queue.out 2>&1 || stop "engine queue rc!=0 (see $R/logs/engine/queue.log)"
say "PHASE_E_DONE"
# ======== phase R: reader identity control (3b configuration must reproduce 2e75f1b3 exactly), then the readings
RD="$PV -B $AD/rc_read_a1.py"
$RD $R/receipts/IDCTRL_3b_config.json --series $F/series --control A0 --full RED --seat SEAT_ONLY --comp COMP_ONLY --members 0 --block 30 > $R/logs/idctrl.log 2>&1 || stop "reader identity control run failed"
$PV - $R/receipts/IDCTRL_3b_config.json $F/receipts/RC_READ_hybrid.json <<'PY' >> $LG 2>&1 || stop "reader identity control: segments differ from 3b 2e75f1b3 -> no reading (rule rev 1 item 1)"
import json, sys
a, b = (json.load(open(p))["segments"] for p in sys.argv[1:3]); assert a == b, "segments differ"
print("IDCTRL_READER PASS: all %d segments equal RC_READ_hybrid 2e75f1b3 exactly" % len(b))
PY
$RD $R/receipts/RC_READ_A1SEAT_block30.json --series $R/series --control A0 --full A1 --seat SEAT_ONLY --comp COMP_ONLY --members 0 --block 30 > $R/logs/read_block30.log 2>&1 || stop "reading block 30 failed"
$RD $R/receipts/RC_READ_A1SEAT_block7_REFERENCE.json --series $R/series --control A0 --full A1 --seat SEAT_ONLY --comp COMP_ONLY --members 0 --block 7 > $R/logs/read_block7.log 2>&1 || stop "reading block 7 failed"
say "$(head -1 $R/logs/read_block30.log) (judged, block 30)"; say "$(head -1 $R/logs/read_block7.log) (reference, block 7)"
mirror
say "A1SEAT_DONE"
