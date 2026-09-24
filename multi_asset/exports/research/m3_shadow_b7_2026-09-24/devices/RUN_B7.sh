#!/bin/zsh
# M3 shadow acceptance B7 (AMENDMENT_2 §3 step 4 item 2: β_exec vs a research-side recomputation at the same anchor, ≤ 1 %) — research side.
# VERBATIM commands, in order. Mac: /usr/bin/python3 3.9.6 + numpy 1.26.4; pod2 only for the certified control row (read-only inputs).
# Production files are only READ (cp -p copies); nothing under ~/wide_shadow or ~/dl_quant_live is written; no exchange call except the
# public klines pull of step 3, inside the 13:00Z quiet window, guarded (weight > 1200/min ⇒ abort; 429 / 418 ⇒ abort, no retry).
set -eu
D=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_shadow_b7_2026-09-24
S=/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/b7
IN=$S/inputs; FD=$S/fetch; OUT=$S/out
# ---- 0. (done 2026-09-24 05:3xZ, before any B7 number) positive-control row from the certified β matrix, pod2 ----
#   scp devices/b7_ctrl_extract.py pod2:/root/m3c_2026-09-24/b7/
#   ssh pod2 'cd /root/m3c_2026-09-24/b7 && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B b7_ctrl_extract.py /root/m3c_2026-09-24/work/BETA_M3_full.npz /root/m3c_2026-09-24/b7/CTRL_certified_beta_1789761600.npz'
#   → B7_CTRL_EXTRACT DONE (829 symbols, 797 estimated, 0 with a UA bar in the window); npz sha 1a35f9da
# ---- 1. (done 05:4xZ) offline self-test of the fetch guards and the comparison (fake transport, synthetic market) ----
#   /usr/bin/python3 -B devices/b7_selftest.py $S/../b7_selftest   → run 1: 3 RED, all from my fixture (the synthetic control had only 93 clean
#   names < the gate's 100; the device verdicts were right for that input); fixture enlarged to 40 replicas, run 2: B7_SELFTEST VERDICT=ALL GREEN tests=15 red=0
# ==== commit (devices + operationalisation, before any B7 number) ====
# ---- 2. after the 12Z anchor row is in the ledger (≈ 12:45Z): read-only copies ----
zsh $D/devices/b7_copy_inputs.sh $IN
# ---- 3. inside the 13:00Z quiet window: self-check, then the guarded pull ----
/usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json
/usr/bin/python3 -B $D/devices/b7_fetch_klines.py $IN $FD
# ---- 4. comparison ----
/usr/bin/python3 -B $D/devices/b7_compare.py $IN $FD $D/receipts/pod2/CTRL_certified_beta_1789761600.npz $OUT

# ==================== ACTUAL RUN 2026-09-24 (commands VERBATIM as executed; outputs → receipts/run_2026-09-24T13Z/) ====================
# 13:01:00Z  step 2 (copy):
#   S=.../scratchpad/b7; mkdir -p $S && D=... && zsh $D/devices/b7_copy_inputs.sh $S/inputs 2>&1 | tail -8; echo "copy rc=$?"
#   printed SIDECAR_OK 1790236800 / SIDECAR_OK 1790251200; the echoed "copy rc=0" is the rc of `tail` (pipe), NOT of the script — the
#   script's completion is evidenced by its last step (the UTC line 2026-09-24T13:01:00Z appended to COPY_SHA256.txt under set -eu).
# 13:01Z  step 3 (self-check + pull):
#   /usr/bin/python3 .../common/venue_quiet_window.py --json > $S/VQW_SELFCHECK_at_start.json; echo "vqw rc=$?"   → vqw rc=0, open
#   /usr/bin/python3 -B $D/devices/b7_fetch_klines.py $S/inputs $S/fetch > $S/fetch_stdout.log 2>&1; echo "fetch rc=$?"   → fetch rc=0
#   B7_FETCH VERDICT=COMPLETE ok=450 failed=0 max_used_weight_1m=252 manifest_sha256=d78d4a499d06c08ec383ccb490538afca31655e43fb28a3b02b432a472ed9ad8
# 13:04:50Z  step 4 (compare):
#   /usr/bin/python3 -B $D/devices/b7_compare.py $S/inputs $S/fetch $D/receipts/pod2/CTRL_certified_beta_1789761600.npz $S/out > $S/compare_stdout.log 2>&1; echo "compare rc=$?"   → compare rc=1
#   B7_PARITY VERDICT=UNDECIDED rel_exec_A08=0.03418645326122071 rel_exec_A12=0.03351512096299784 control_max_dbeta=0.0007639494921789503 n_rel_over_1pct_A08=7 n_rel_over_1pct_A12=10 undecided=['positive control failed'] out_sha256=85babee4dcbeebedc8432b8bd305e48e5d28b3d2e018d766470bae1ee3c81b36
# ---- POST-HOC, DESCRIPTIVE, NON-GATING (written after the verdict line was read; the frozen rule and verdict are unchanged) ----
# 13:07Z  /usr/bin/python3 -B $D/devices/b7_descriptive_diag.py $S/inputs $S/out $S/out/B7_DESCRIPTIVE_DIAG.json > $S/diag_stdout.log 2>&1   → diag rc=0
# 13:1xZ  closes subset for the table probe (Mac): python3 -c (KLINES_RAW.jsonl.gz → probe/closes_all.json {symbol: {boundary_ts: close}}, sort_keys) sha 4e736066…
#   scp devices/b7_ctrl_table_probe.py probe/closes_all.json pod2:/root/m3c_2026-09-24/b7/
#   ssh pod2 'cd /root/m3c_2026-09-24/b7 && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B b7_ctrl_table_probe.py closes_all.json CTRL_TABLE_PROBE.json'   → probe rc=0
