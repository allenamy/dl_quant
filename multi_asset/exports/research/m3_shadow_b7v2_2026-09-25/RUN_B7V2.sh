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

# ==== step 1: per-anchor devices (committed BEFORE any m3_beta_v2 shadow anchor exists) ====
# b7v2_copy_inputs.sh (read-only copies for one anchor) · b7v2_fetch.py (1 exchangeInfo + n klines, lead envelope: ≤500 requests, weight ≤300
# abort / ≥240 soft brake, 429/418 abort, quiet window at start and before every request) · b7v2_compare.py (rule b80f52b39: gate (0),
# (i) reported with named reasons, (ii) gate; instrument checks ⇒ UNDECIDED).
# 2026-09-25T04:45Z offline self-test (fake transport / quiet window / clock; synthetic market; no network, no production file):
#   (cwd $D) S=~/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/b7v2_selftest; mkdir -p receipts/selftest_2026-09-25; /usr/bin/python3 -B devices/b7v2_selftest.py $S > receipts/selftest_2026-09-25/selftest_stdout.log 2>&1; echo "selftest rc=$?"
#     → selftest rc=0 · B7V2_SELFTEST VERDICT=ALL GREEN tests=31 red=0   (Mac /usr/bin/python3 3.9.6, numpy 1.26.4)
# ==== per v2 shadow anchor A (template; quiet window after A, i.e. from N+60m; commands to be copied here verbatim when run) ====
#   zsh $D/devices/b7v2_copy_inputs.sh $S/b7v2/in_$A $A
#   ~/wide_shadow/venv/bin/python -B /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/nc_2026-09-23/devices/nc_m3_selfcheck.py ~/cc_tmp/nc_20260923/package_NC $A --out $S/b7v2/in_$A/M3_SELFCHECK_$A.txt
#   /usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json
#   /usr/bin/python3 -B $D/devices/b7v2_fetch.py $S/b7v2/in_$A $A $S/b7v2/fetch_$A
#   /usr/bin/python3 -B $D/devices/b7v2_compare.py $S/b7v2/in_$A $S/b7v2/fetch_$A $S/b7v2/in_$A/M3_SELFCHECK_$A.txt $A $D/receipts/anchor_$A
# ==== anchor 1790352000 (2026-09-25T16:00Z, first m3_beta_v2 shadow anchor), run 2026-09-25T17:00:14Z..17:04:45Z (quiet window OPEN, 159.7 min left) ====
#   zsh $D/devices/b7v2_copy_inputs.sh $S/b7v2/in_1790352000 1790352000
#   ~/wide_shadow/venv/bin/python -B /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/nc_2026-09-23/devices/nc_m3_selfcheck.py ~/cc_tmp/nc_20260923/package_v2c_20260925 1790352000 --out $S/b7v2/in_1790352000/M3_SELFCHECK_1790352000.txt
#     → M3_SELFCHECK 1790352000 OK n=0   (the template above named package_NC — the pre-v2 contract; v2 needs package_v2c_20260925, corrected here)
#   /usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json   → open, remaining 159.7
#   /usr/bin/python3 -B $D/devices/b7v2_fetch.py $S/b7v2/in_1790352000 1790352000 $S/b7v2/fetch_1790352000
#     → B7V2_FETCH VERDICT=COMPLETE n_requests=451 ok=450 failed=0 max_used_weight_1m=208 soft_brakes=0 (envelope: <=500 requests, weight <=300)
#   /usr/bin/python3 -B $D/devices/b7v2_compare.py $S/b7v2/in_1790352000 $S/b7v2/fetch_1790352000 $S/b7v2/in_1790352000/M3_SELFCHECK_1790352000.txt 1790352000 $D/receipts/anchor_1790352000
#     → B7V2 STATUS=CLEAN gate0=True ii_abs_usdt=3.19 ii_tol_usdt=109.51 ii_pass=True n_over_band=1 n_unexplained=0 undecided=[]
# ==== anchor 1790366400 (2026-09-25T20:00Z, second m3_beta_v2 shadow anchor), run 2026-09-25T21:00:13Z..21:04:44Z (quiet window OPEN, 159.7 min left) ====
#   zsh $D/devices/b7v2_copy_inputs.sh $S/b7v2/in_1790366400 1790366400
#   ~/wide_shadow/venv/bin/python -B /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/nc_2026-09-23/devices/nc_m3_selfcheck.py ~/cc_tmp/nc_20260923/package_v2c_20260925 1790366400 --out $S/b7v2/in_1790366400/M3_SELFCHECK_1790366400.txt
#     → M3_SELFCHECK 1790366400 OK n=0
#   /usr/bin/python3 /Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py --json   → open, remaining 159.7
#   /usr/bin/python3 -B $D/devices/b7v2_fetch.py $S/b7v2/in_1790366400 1790366400 $S/b7v2/fetch_1790366400
#     → B7V2_FETCH VERDICT=COMPLETE n_requests=451 ok=450 failed=0 max_used_weight_1m=214 soft_brakes=0 (envelope: <=500 requests, weight <=300)
#   /usr/bin/python3 -B $D/devices/b7v2_compare.py $S/b7v2/in_1790366400 $S/b7v2/fetch_1790366400 $S/b7v2/in_1790366400/M3_SELFCHECK_1790366400.txt 1790366400 $D/receipts/anchor_1790366400
#     → B7V2 STATUS=CLEAN gate0=True ii_abs_usdt=3.06 ii_tol_usdt=109.38 ii_pass=True n_over_band=1 n_unexplained=0 undecided=[]
