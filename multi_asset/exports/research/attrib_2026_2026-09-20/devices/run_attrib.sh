#!/bin/sh
# run_attrib.sh — the verbatim command sequence for docs/RESULT_attribution_2026_vs_history_2026-09-20.md.
# pod2, CPU only, read-only on every input, writes only /workspace/attrib_2026_2026-09-20/.
# The env whitelist is passed to every device and asserted there (E-0826-D): any variable outside it refuses.
#
# staging (from the mac, repo root):
#   rsync -a multi_asset/exports/research/attrib_2026_2026-09-20/devices/ pod2:/workspace/attrib_2026_2026-09-20/devices/
#   cp multi_asset/exports/research/c0_attrib_2026-09-19/devices/c0_chars.py \
#      /tmp/c0_chars_f4c13d76_REFERENCE.py && rsync /tmp/c0_chars_f4c13d76_REFERENCE.py \
#      pod2:/workspace/attrib_2026_2026-09-20/devices/
set -e
D=/workspace/attrib_2026_2026-09-20/devices
R=/workspace/attrib_2026_2026-09-20/receipts
LG=/workspace/attrib_2026_2026-09-20/logs
PY=/workspace/venv/bin/python
ENVW=PATH,HOME,LC_CTYPE,LANG,PWD,SHLVL,_

# a. battery (baselines green first, every mutation red) — before anything reads the data
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_selftest.py "$ENVW" $R 2>&1 | tee $LG/at_selftest.log

# b. before-running gate: every input sha, the layout facts, then the frozen run config
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_prerun.py "$ENVW" $R 2>&1 | tee $LG/at_prerun.log

# c. the CONTROL: reproduce the published per-period table from the 32 raw fill paths
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_control.py "$ENVW" $R 2>&1 | tee $LG/at_control.log

# d. the L2 paper panel (books, returns, funding, characteristics, conditions)
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_build.py "$ENVW" $R 2>&1 | tee $LG/at_build.log

# e. blocks R, A, B, C, D, E, F + the 30-test Holm family
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_attrib.py "$ENVW" $R 2>&1 | tee $LG/at_attrib.log

# f. block G: run lengths, persistence frequencies, conditional performance, where the book stands
env -i PATH=/usr/bin:/bin HOME=$HOME $PY -B $D/at_regime.py "$ENVW" $R 2>&1 | tee $LG/at_regime.log

# g. rendering runs on the mac, from the receipts:
#   python multi_asset/exports/research/attrib_2026_2026-09-20/devices/at_render.py \
#          multi_asset/exports/research/attrib_2026_2026-09-20/receipts
