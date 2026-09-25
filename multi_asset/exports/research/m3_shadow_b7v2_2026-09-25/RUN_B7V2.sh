#!/bin/zsh
# B7 v2 method (a), research-side β_res. Rule: docs/DECISION_RULE_B7_v2_m3_shadow_2026-09-25.md (b80f52b39, frozen before any v2 shadow anchor).
# VERBATIM commands in execution order; outputs under receipts/. Nothing under ~/wide_shadow or ~/dl_quant_live is written.
set -eu
D=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_shadow_b7v2_2026-09-25
V1=/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/m3_shadow_b7_2026-09-24/receipts/run_2026-09-24T13Z

# ==== step 0: why the v1 positive control missed 1e-6 (diagnostic, non-gating; device committed a315ccc38 BEFORE it ran) ====
# 2026-09-25T04:32Z (Mac → pod2; pod2 CPU, one thread, nice 10; inputs read-only):
#   ssh pod2 'mkdir -p /root/m3c_2026-09-24/b7v2/in /root/m3c_2026-09-24/b7v2/out; nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader; uptime'
#   scp -q $D/devices/b7v2_ctrl_diag.py $D/devices/m2_lib.py pod2:/root/m3c_2026-09-24/b7v2/
#   scp -q $V1/fetch/KLINES_RAW.jsonl.gz $V1/out/B7_CONTROL_per_name.csv pod2:/root/m3c_2026-09-24/b7v2/in/
#   ssh pod2 'cd /root/m3c_2026-09-24/b7v2 && sha256sum b7v2_ctrl_diag.py m2_lib.py in/*'
#     → 8c6146f1… b7v2_ctrl_diag.py (== Mac copy) · 93f8e760… m2_lib.py · 3c0fee8b… B7_CONTROL_per_name.csv · 78a7656c… KLINES_RAW.jsonl.gz
#   ssh pod2 'cd /root/m3c_2026-09-24/b7v2 && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B b7v2_ctrl_diag.py in/KLINES_RAW.jsonl.gz in/B7_CONTROL_per_name.csv /root/m3c_2026-09-24/b7/CTRL_certified_beta_1789761600.npz out > out/diag_stdout.log 2>&1; echo "diag rc=$?"; tail -8 out/diag_stdout.log | cut -c1-600'
#     → diag rc=0
#     → B7V2_CTRL_DIAG READING=H_SUPPORTED n_pure=80812 n_viol=0 red_div10=31135 M2_bitwise=449/449 max_gap=0.0007639494921789503 max_path=0.0 M4_band_exceed=0 out_sha256=fd8d22d7f3fc37e33781eaa1484495413eea3ea704d98bd9635dc4127528b258
#   R=$D/receipts/ctrl_diag_2026-09-25; mkdir -p $R; scp -q pod2:/root/m3c_2026-09-24/b7v2/out/B7V2_CTRL_DIAG.json pod2:/root/m3c_2026-09-24/b7v2/out/B7V2_CTRL_DIAG_per_name.csv pod2:/root/m3c_2026-09-24/b7v2/out/diag_stdout.log $R/
#     → fd8d22d7… B7V2_CTRL_DIAG.json · 2a8b1788… B7V2_CTRL_DIAG_per_name.csv · f3da1219… diag_stdout.log
# READING (plain): the certified table is built from float16 5-minute returns, not from closes; its 4h returns differ from the kline
#   closes' by the float16 rounding (80,812 clean bars, every one inside the rounding bound; a bound 10× tighter is broken by 31,135 ⇒ the
#   test can fail). The v1 research path fed the table's own values reproduces the certified β bitwise on all 449 names ⇒ the whole
#   control gap (max 7.64e-4) is that input rounding, 0 from the formula/path. The v1 1e-6 gate compared two different inputs; the
#   instrument is correct. Production v2 β is computed from rr (the same float16 storage + raw restore of clipped bars), so the same
#   rounding separates it from a kline-based β_res; at the control anchor it stays inside the frozen rule (i) band on all 449 names (M4 = 0).
