#!/bin/bash
# rebuild fea89 with the stable trend builder on holefix2 (-> f8_v4s) and holefix (-> f8_hf2s); then G2 closure gates: stable(hf2s vs v4s) [REQUIRED] and, for the record, global(f8_hf2 vs f8_v4).
# HARDENED 2026-09-09 (review b0a573a1 P1-PIPE): build markers checked; the REQUIRED G2 gate's rc decides (hardened gate exits 3 on FAIL); the record-only gate's rc is logged, not fatal; DONE only on success.
set -o pipefail; R=/workspace/review_scratch; . $R/chain_lib.sh; cd $R || exit 2
mkdir -p /workspace/f8_v4s/data /workspace/f8_v4s/results /workspace/f8_hf2s/data /workspace/f8_hf2s/results $R/v4_gates
say "fea89 stable build holefix2 -> f8_v4s"; F8_DLW=/workspace/dlw_hf3 F8_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz F8_OUT=/workspace/f8_v4s $PY pod_f8_build_stable.py build > $R/f8_stable_v4s.log 2>&1 || die "f8_stable_v4s" 1
check_marker $R/f8_stable_v4s.log "F8_BUILD_DONE"
say "fea89 stable build holefix -> f8_hf2s"; F8_DLW=/workspace/dlw_hf2 F8_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix.npz F8_OUT=/workspace/f8_hf2s $PY pod_f8_build_stable.py build > $R/f8_stable_hf2s.log 2>&1 || die "f8_stable_hf2s" 1
check_marker $R/f8_stable_hf2s.log "F8_BUILD_DONE"
say "G2 closure gate stable (REQUIRED)"; $PY v4_gate_closure.py /workspace/f8_v4s/data/f8_fea89.npz /workspace/f8_hf2s/data/f8_fea89.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_hf2/data/dlw_targets.npz $R/v4_gates/G2_closure_stable.json > $R/G2_stable.log 2>&1; rc=$?
say "G2 stable rc=$rc $(tail -1 $R/G2_stable.log | cut -c1-100)"; [ $rc -eq 0 ] || die "G2_closure_stable_rc_$rc" 3
say "G2 closure gate global (record only)"; $PY v4_gate_closure.py /workspace/f8_v4/data/f8_fea89.npz /workspace/f8_hf2/data/f8_fea89.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_hf2/data/dlw_targets.npz $R/v4_gates/G2_closure_global.json > $R/G2_global.log 2>&1; rc=$?
say "G2 global rc=$rc (record only) $(tail -1 $R/G2_global.log | cut -c1-100)"
say "CHAIN_FEA89_STABLE_DONE (builds + required G2 PASS)"
