#!/bin/bash
# test_ksr_hooks.sh <devices dir> -- red tests of ksr_hooks.sh with the REAL pinned gate-4 device (dlarch_ksr_splice.py 9557d128) on the
# REAL in-service legs (A0_m0, 9ee5886f), in a /workspace sandbox (fresh2 2026-09-27). The positive case must be green first-class, not assumed:
#   B0  gate 4 PASS: cell legs = S0 legs with WL changed only at/after the window's first anchor           -> hook rc 0, GATE4 PASS
#   T1  splice did not reach the legs: cell legs == S0 legs                                                  -> hook rc != 0
#   T2  a legs array differs BEFORE the window (the splice leaked backwards)                                  -> hook rc != 0
#   T3  gate-4 device is not the pinned sha                                                                  -> hook rc != 0, device not run
#   T4  a cell's legs exported twice                                                                         -> hook rc != 0
#   B1  after_targets on A0_m0 writes both seeds' stats                                                       -> rc 0, 2 npz + 2 json
set -u
# sandbox on /workspace, never /tmp: pod2's /tmp is the 5 GB container root overlay, and uncompressed legs fixtures (~170 MB each)
# filled it to 100% on the first run of this test (07:2xZ). The fixtures are written compressed as well.
DEV=$(cd "$1" && pwd); mkdir -p /workspace/fresh2_scratch; T=$(mktemp -d /workspace/fresh2_scratch/ksrhook.XXXXXX); A0=/dev/shm/mretrain_2026-09-26/arms/A0_m0
export PV=/workspace/venv/bin/python KSR_SPLICE_DEV=$DEV/dlarch_ksr_splice.py KSR_SPLICE_SHA=9557d128585a9d4ff1a8f25daa5d2a91454a87ecc2cd9e129d4f948e705bd267
np=0; nf=0; ok() { echo "PASS $*"; np=$((np + 1)); }; bad() { echo "FAIL $*"; nf=$((nf + 1)); }
[ "$(sha256sum $KSR_SPLICE_DEV | cut -c1-64)" = "$KSR_SPLICE_SHA" ] || { echo "the devices dir under test does not hold the pinned gate-4 device"; exit 9; }
# fixtures: S0 legs, three cell legs, a splice receipt whose first window is the anchor at row 6000
$PV - $A0/work/legs.npz $T <<'PY'
import sys, json, numpy as np
src, T = sys.argv[1], sys.argv[2]
z = np.load(src); d = {k: z[k] for k in z.files}; E = d["E_ts"]; w0 = int(E[6000])
np.savez_compressed(T + "/S0.npz", **d)
json.dump({"windows": [{"first_anchor": w0}]}, open(T + "/SPLICE_RECEIPT.json", "w"))  # durable-exempt: test fixture in a temp dir
for name, row in (("post", 6000), ("pre", 5999)):
    e = {k: v.copy() for k, v in d.items()}; e["WL"][row:row + 3] = e["WL"][row:row + 3][::-1] + 0.125; np.savez_compressed(T + "/cell_%s.npz" % name, **e)
np.savez_compressed(T + "/cell_same.npz", **d)
print("fixtures w0", w0)
PY
mkw() { rm -rf $T/W_$1; mkdir -p $T/W_$1/work; cp $2 $T/W_$1/work/legs.npz; }
run() {  # <case> <cell legs> [extra env...]
  local c=$1 legs=$2; shift 2; mkw $c $legs
  env KSR_ROOT=$T/root_$c KSR_GATE4_REF=$T/S0.npz KSR_SPLICE_RECEIPT=$T/SPLICE_RECEIPT.json "$@" bash $DEV/ksr_hooks.sh after_legs CELL_$c $T/W_$c > $T/$c.log 2>&1; rc=$?
  echo "  [$c] rc=$rc $(tail -1 $T/$c.log | cut -c1-160)"; }
run B0 $T/cell_post.npz;  [ $rc = 0 ] && grep -q "HOOK GATE4 PASS" $T/B0.log && ok "B0 post-window change passes gate 4" || bad "B0 rc=$rc"
run T1 $T/cell_same.npz;  [ $rc != 0 ] && grep -q "HOOK GATE4 FAIL" $T/T1.log && ok "T1 unreached splice refused" || bad "T1 rc=$rc"
run T2 $T/cell_pre.npz;   [ $rc != 0 ] && grep -q "HOOK GATE4 FAIL" $T/T2.log && ok "T2 pre-window difference refused" || bad "T2 rc=$rc"
run T3 $T/cell_post.npz KSR_SPLICE_SHA=0000000000000000000000000000000000000000000000000000000000000000
[ $rc != 0 ] && grep -q "not the pinned" $T/T3.log && [ ! -e $T/root_T3/gate4/CELL_T3.json ] && ok "T3 unpinned device refused, not run" || bad "T3 rc=$rc"
env KSR_ROOT=$T/root_B0 KSR_GATE4_REF= bash $DEV/ksr_hooks.sh after_legs CELL_B0 $T/W_B0 > $T/T4.log 2>&1; rc=$?
[ $rc != 0 ] && grep -q "exported once" $T/T4.log && ok "T4 second export refused" || bad "T4 rc=$rc"
env KSR_ROOT=$T/root_B1 bash $DEV/ksr_hooks.sh after_targets CELL_B1 $A0 > $T/B1.log 2>&1; rc=$?
[ $rc = 0 ] && [ "$(ls $T/root_B1/targets_stats/CELL_B1_s*.npz $T/root_B1/targets_stats/CELL_B1_s*.json 2>/dev/null | wc -l)" = 4 ] && ok "B1 targets stats both seeds" || bad "B1 rc=$rc"
echo "TEST_KSR_HOOKS devices=$DEV pass=$np fail=$nf sandbox=$T"
[ $nf -eq 0 ] && rm -rf $T
[ $nf -eq 0 ]
