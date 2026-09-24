#!/bin/bash
# Regression of test_nc_install_rehearsal.py after the model-args change (lead 2026-09-24): SAME inputs as the pre-change run
# (receipt install_rehearsal_machinery/TEST_NC_INSTALL_REHEARSAL.json, 19:47:04Z: treeNC4, synthetic machine seed pack, snapshot 1790179200,
# NEW_S stand-in models). Local heavy work ⇒ only inside the Mac quiet window; refuses to start otherwise.
set -u
QW=~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py
/usr/bin/python3 $QW --json > /dev/null; rc=$?
if [ $rc -ne 0 ]; then echo "REFUSED: not inside the quiet window (venue_quiet_window.py rc=$rc)"; /usr/bin/python3 $QW --json | grep -E '"reason"|remaining'; exit 78; fi
W=~/cc_tmp/nc_20260923; OUT=$W/release_tests/install_rehearsal_regression_$(date -u +%Y%m%dT%H%MZ)
echo "quiet window open; out $OUT; loadavg $(uptime | sed 's/.*averages: //')"
~/wide_shadow/venv/bin/python -u $W/src/test_nc_install_rehearsal.py $W/treeNC4 $W/release $W/dryrun/seedtest/synth_seed_pack.npz 1790179200 $OUT
echo "rc=$?"
