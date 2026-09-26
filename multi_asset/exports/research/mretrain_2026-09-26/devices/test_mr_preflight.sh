#!/bin/bash
# test_mr_preflight.sh — red tests of the family's pre-flight (fresh2 2026-09-27; the 18:35Z STOP came 25 min in because the vendored
# combo_stage.py sat under the arm while combo_target reads it from devices/..). Runs on pod2 in a throw-away sandbox root; big inputs
# are HARDLINKED and only ever read; every mutated file is a fresh COPY (a write to a hardlink would change the in-service original).
# The baseline must be green FIRST (a red test that never saw green proves nothing). Prints one line per case and
# TEST_MR_PREFLIGHT ALL_OK=True|False; rc 0 only when every case matched its expectation.
set -uo pipefail
R=/dev/shm/mretrain_2026-09-26; D=$R/devices; N=/dev/shm/news2_2026-09-23
P314=/root/news_2026-09-23_env/venv314/bin/python; PV=/workspace/venv/bin/python; NPY="X86_V4 AVX512_ICL AVX512_SPR"
T=/dev/shm/mr_pftest_$$; trap 'rm -rf $T' EXIT
ok=1
build() {   # fresh sandbox: T/devices (copies), T/arms/X (links + copies), T/vendor_live at the path combo_target reads
  rm -rf $T; mkdir -p $T/devices $T/arms/X/{work,receipts,inputs} $T/vendor_live/fea171
  cp $D/{mr_combo.py,combo_target.py,continuous_combo.py,book_universe.py,mr_preflight_refs.py,mr_gates.py,mr_read.py,news2_adapter_specs.py,mr_prep.sh,mr_engine_queue.sh} $T/devices/
  ln $N/work/NEWS_FEATURES.npz $T/arms/X/work/NEWS_FEATURES.npz; ln $N/receipts/P1_members_2025H2on.npz $T/arms/X/receipts/
  cp $N/inputs/bundle_config.json $T/arms/X/inputs/
  ln $N/vendor_live/fea171/combo_stage.py $T/vendor_live/fea171/combo_stage.py
}
combo() { (cd $T/devices && MR_W=$T/arms/X NPY_DISABLE_CPU_FEATURES="$NPY" OMP_NUM_THREADS=1 $P314 -B -u mr_combo.py --preflight 2>&1 | tail -1); }
refs() { $PV -B $T/devices/mr_preflight_refs.py $T/devices 2>/dev/null | tail -1; }
expect() {  # expect <case> <PASS|FAIL> <output>
  local got=FAIL; echo "$3" | grep -qE "^MR_(COMBO_PREFLIGHT|PREFLIGHT_REFS) PASS" && got=PASS
  local v=OK; [ "$got" = "$2" ] || { v=MISMATCH; ok=0; }
  echo "CASE $1 expect=$2 got=$got $v :: $(echo "$3" | cut -c1-230)"
}
t0=$(date +%s)
build; expect C0_baseline_combo PASS "$(combo)"
[ $ok -eq 1 ] || { echo "TEST_MR_PREFLIGHT ALL_OK=False (baseline not green: no red case is meaningful)"; exit 1; }
build; expect R0_baseline_refs PASS "$(refs)"
[ $ok -eq 1 ] || { echo "TEST_MR_PREFLIGHT ALL_OK=False (baseline not green: no red case is meaningful)"; exit 1; }
# C1 = the 18:35Z shape: vendor file only under the arm, none where combo_target reads it
build; rm $T/vendor_live/fea171/combo_stage.py; mkdir -p $T/arms/X/vendor_live/fea171
ln $N/vendor_live/fea171/combo_stage.py $T/arms/X/vendor_live/fea171/; expect C1_vendor_missing_at_kernel_root FAIL "$(combo)"
build; rm $T/vendor_live/fea171/combo_stage.py; cp $N/vendor_live/fea171/combo_stage.py $T/vendor_live/fea171/; echo "# x" >> $T/vendor_live/fea171/combo_stage.py
expect C2_vendor_bytes_changed FAIL "$(combo)"
build; rm $T/arms/X/inputs/bundle_config.json; cp $N/inputs/bundle_config.json $T/arms/X/inputs/; echo " " >> $T/arms/X/inputs/bundle_config.json
expect C3_arm_static_input_changed FAIL "$(combo)"
build; rm $T/arms/X/work/NEWS_FEATURES.npz; expect C4_arm_static_input_missing FAIL "$(combo)"
build; sed -i 's#/dev/shm/fanom_2026-09-24/receipts/SER_EXT_NEWS2_s42X.npz#/dev/shm/fanom_2026-09-24/receipts/NO_SUCH.npz#' $T/devices/mr_read.py
expect R1_read_reference_missing FAIL "$(refs)"
build; sed -i 's#^KING_SHA = "a10b#KING_SHA = "b10b#' $T/devices/mr_gates.py; expect R2_gate_reference_sha_changed FAIL "$(refs)"
build; sed -i 's#GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh#GATE=/dev/shm/fresh_2026-09-23/devices/NO_SUCH.sh#' $T/devices/mr_engine_queue.sh
expect R3_engine_queue_helper_missing FAIL "$(refs)"
build; sed -i 's#^LEGS_SHA = #LEGS_SHA_RENAMED = #' $T/devices/mr_gates.py; expect R4_parser_cannot_find_constant FAIL "$(refs)"
echo "TEST_MR_PREFLIGHT ALL_OK=$([ $ok -eq 1 ] && echo True || echo False) seconds=$(( $(date +%s) - t0 )) sandbox_removed_on_exit"
[ $ok -eq 1 ]
