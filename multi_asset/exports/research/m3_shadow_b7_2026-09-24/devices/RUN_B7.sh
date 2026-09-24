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
