#!/bin/bash
# chain_king_e.sh — PREREG_king_clock_E_2026-09-09: E-version king features -> G1 parity gate -> export v4e (env verbatim AMD2 run2) -> guard band -> align + arm A1e -> judge.
# Every stage checks its rc AND its completion marker; any failure exits non-zero and writes FAIL_* to the receipt log (no silent DONE).
set -o pipefail
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4e_commands.txt; cd $R || exit 2
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
C=/workspace/data/dlnative_5m_wide829_f16_holefix2.npz
if [ "${START_STAGE:-1}" -le 1 ]; then
say "E-0909-F stage1 build king features (E version)"
CACHE_IN=$C PANEL_IN=/workspace/data/wide_panel_4h_v2ext.npz FEA_OUT=/workspace/data/wide_fea_v4e.npy META_OUT=/workspace/data/wide_fea_v4e_meta.npz $PY pod_fea_ext_e.py > $R/fea_v4e.log 2>&1; rc=$?
say "stage1 rc=$rc $(tail -1 $R/fea_v4e.log | cut -c1-120)"; { [ $rc -eq 0 ] && grep -q FEA_EXT_E_DONE $R/fea_v4e.log; } || { say FAIL_stage1_features; exit 1; }
else say "stage1 skipped (START_STAGE=$START_STAGE), reusing $(tail -1 $R/fea_v4e.log | cut -c1-60)"; grep -q FEA_EXT_E_DONE $R/fea_v4e.log || { say FAIL_stage1_marker_missing; exit 1; }; fi
say "stage2 G1 parity gate (production wstat AST, 6 anchors)"
$PY v4e_gate_parity.py > $R/g1_v4e_parity.log 2>&1; rc=$?
say "stage2 rc=$rc $(grep G1_KING_CLOCK_PARITY $R/g1_v4e_parity.log | cut -c1-200)"; [ $rc -eq 0 ] || { say FAIL_stage2_G1_parity; exit 3; }
say "stage3 export bundle v4e (guard band ${BUNDLE_GUARD_LO:-2.27}..${BUNDLE_GUARD_HI:-2.57}, AMENDMENT 2 if overridden)"
env BUNDLE_OUT=/workspace/shadow_bundle_v4e BUNDLE_BASE=/workspace/slow_scorer_v4base.json BUNDLE_FEA=/workspace/data/wide_fea_v4e.npy BUNDLE_META=/workspace/data/wide_fea_v4e_meta.npz BUNDLE_CACHE=$C BUNDLE_TAR=/workspace/shadow_bundle_v4e.tar.gz EXPORT_PANEL=/workspace/data/wide_panel_4h_v3splice.npz EMA_STATE_JSON=/workspace/fund_state_canoncont.json $PY pod_export_bundle_v4.py > $R/export_v4e.log 2>&1; rc=$?
say "stage3 rc=$rc $(tail -1 $R/export_v4e.log | cut -c1-120)"; { [ $rc -eq 0 ] && grep -q BUNDLE_DONE $R/export_v4e.log; } || { say FAIL_stage3_export; exit 1; }
say "stage4 guard band (v3 must reproduce 2.284 first)"
$PY guard_reconcile_v4e.py > $R/guard_v4e.log 2>&1; rc=$?
say "stage4 rc=$rc $(grep -a 'panel=v3splice' $R/guard_v4e.log | cut -c1-90 | tr '\n' ';')"; [ $rc -eq 0 ] || { say FAIL_stage4_guard_band; exit 3; }
say "stage5 align SLOW_v4e + arms A1e (dyn/fix x s42/s2027)"
$PY align_king_v4e.py > $R/align_v4e.log 2>&1; rc=$?; { [ $rc -eq 0 ] && grep -q ALIGN_V4E_DONE $R/align_v4e.log; } || { say FAIL_stage5_align; exit 1; }
bash run_v4_arms.sh A1e > $R/arms_A1e.log 2>&1; rc=$?
say "stage5 arms rc=$rc ended=$(grep -a -c '^END\[V4_A1e_.*rc=0' $R/health_check/logs/commands.txt)/4"; [ $rc -eq 0 ] && [ "$(grep -a -c '^END\[V4_A1e_.*rc=0' $R/health_check/logs/commands.txt)" -ge 4 ] || { say FAIL_stage5_arms; exit 1; }
say "stage6 judge (frozen §4; A1e-A1, A1e-A0 added)"
JUDGE_OUT=$R/v4_gates/JUDGE_v4e.json $PY judge_v4.py > $R/judge_v4e.log 2>&1; rc=$?
say "stage6 rc=$rc $(grep -a 'A1e-A' $R/judge_v4e.log | tail -4 | tr '\n' ';' | cut -c1-200)"; { [ $rc -eq 0 ] && grep -q JUDGE_V4_DONE $R/judge_v4e.log; } || { say FAIL_stage6_judge; exit 1; }
say "CHAIN_KING_E_DONE"
