#!/bin/bash
# rebuild fea89 with the stable trend builder on holefix2 (-> f8_v4s) and holefix (-> f8_hf2s); then G2 closure gates: stable(hf2s vs v4s) and, for the record, global(f8_hf2 vs f8_v4).
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4_commands.txt; cd $R; say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
mkdir -p /workspace/f8_v4s/data /workspace/f8_v4s/results /workspace/f8_hf2s/data /workspace/f8_hf2s/results
say "fea89 stable build holefix2 -> f8_v4s"; F8_DLW=/workspace/dlw_hf3 F8_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz F8_OUT=/workspace/f8_v4s $PY pod_f8_build_stable.py build > $R/f8_stable_v4s.log 2>&1 || { say FAIL_f8_v4s; exit 1; }
say "fea89 stable build holefix -> f8_hf2s"; F8_DLW=/workspace/dlw_hf2 F8_CACHE=/workspace/data/dlnative_5m_wide829_f16_holefix.npz F8_OUT=/workspace/f8_hf2s $PY pod_f8_build_stable.py build > $R/f8_stable_hf2s.log 2>&1 || { say FAIL_f8_hf2s; exit 1; }
say "G2 closure gate stable"; $PY v4_gate_closure.py /workspace/f8_v4s/data/f8_fea89.npz /workspace/f8_hf2s/data/f8_fea89.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_hf2/data/dlw_targets.npz $R/v4_gates/G2_closure_stable.json > $R/G2_stable.log 2>&1; say "G2 stable rc=$? $(tail -1 $R/G2_stable.log)"
say "G2 closure gate global (record)"; $PY v4_gate_closure.py /workspace/f8_v4/data/f8_fea89.npz /workspace/f8_hf2/data/f8_fea89.npz /workspace/dlw_hf3/data/dlw_targets.npz /workspace/dlw_hf2/data/dlw_targets.npz $R/v4_gates/G2_closure_global.json > $R/G2_global.log 2>&1; say "G2 global rc=$? $(tail -1 $R/G2_global.log)"
say CHAIN_FEA89_STABLE_DONE
