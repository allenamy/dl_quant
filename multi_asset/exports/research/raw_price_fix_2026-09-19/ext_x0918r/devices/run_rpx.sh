#!/bin/bash
# R5-02 extension to the x0918r axis — VERBATIM transcript of the commands run on pod2 on 2026-09-19 (each issued as `ssh pod2 '<command>'`).
# Devices in /workspace/raw_price_fix_2026-09-19/ext_x0918r/devices/ (byte-identical to this directory; sha256 in
# ext_x0918r/receipts/SHA256SUMS_pod2_ext_x0918r.txt). rp_lib.py is imported from the base devices/ (sha f802036f, asserted by each device).
# Memory: every heavy step runs through rpx_guard.py (king-job priority check, then stream D's ax_memguard.py 689f72e6: >= 20 GiB spare after the
# declared peak, host and cgroup; yield watchdog). Each guard writes ext_x0918r/logs/guard_<step>.json and guard_<step>.memguard.json.

# 1. census (rpx_census.py) -> receipts/RPX_CENSUS.json PASS
cd /workspace/raw_price_fix_2026-09-19/ext_x0918r/devices && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_guard.py ../logs/guard_rpx_census.json 4 -- /workspace/venv/bin/python -B rpx_census.py PATH,HOME,LC_CTYPE 2>&1 | tee ../receipts/rpx_census.log | tail -25; echo "rc=${PIPESTATUS[0]}" | tee -a ../receipts/rpx_census.log

# 2. official archives (rpx_fetch.py = rp_fetch.py with ext_x0918r paths; network only, < 100 MB memory, no guard) -> receipts/RPX_FETCH.json PASS
cd /workspace/raw_price_fix_2026-09-19/ext_x0918r/devices && (setsid nohup env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_fetch.py PATH,HOME,LC_CTYPE > ../receipts/rpx_fetch.log 2>&1; echo "rc=$?" >> ../receipts/rpx_fetch.log) </dev/null >/dev/null 2>&1 &

# 3. restore + extension patch (rpx_restore.py) -> receipts/RPX_RESTORE.json PASS, r_prices_raw_patch_x0918r_ext.npz 01d234c7…
cd /workspace/raw_price_fix_2026-09-19/ext_x0918r/devices && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_guard.py ../logs/guard_rpx_restore.json 3 -- /workspace/venv/bin/python -B rpx_restore.py PATH,HOME,LC_CTYPE 2>&1 | tee ../receipts/rpx_restore.log | tail -40; echo "rc=${PIPESTATUS[0]}" | tee -a ../receipts/rpx_restore.log

# 4. extended table + prefix proof (r_prices_raw_x0918r.py) -> receipts/R_PRICES_RAW_X0918R.json PASS
cd /workspace/raw_price_fix_2026-09-19/ext_x0918r/devices && env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B rpx_guard.py ../logs/guard_r_prices_raw_x0918r.json 6 -- /workspace/venv/bin/python -B r_prices_raw_x0918r.py PATH,HOME,LC_CTYPE 2>&1 | tee ../receipts/r_prices_raw_x0918r.log | grep -v "block" | tail -40; echo "rc=${PIPESTATUS[0]}" | tee -a ../receipts/r_prices_raw_x0918r.log

# 5. regression tests, pod interpreter (Mac: python3 tests/test_rp_x0918r.py > ext_x0918r/receipts/test_rp_x0918r_mac.log); the new test runs the base test first
cd /workspace/raw_price_fix_2026-09-19 && env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B tests/test_rp_x0918r.py > ext_x0918r/receipts/test_rp_x0918r_pod2.log 2>&1; echo "rc=$? python=$(/workspace/venv/bin/python -c "import sys,numpy;print(sys.version.split()[0],numpy.__version__)")" >> ext_x0918r/receipts/test_rp_x0918r_pod2.log
