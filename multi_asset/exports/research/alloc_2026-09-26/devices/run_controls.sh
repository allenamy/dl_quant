#!/bin/bash
# device controls for DESIGN_combination_layer_2026-09-26 (NO candidate arm): identity s42 end-to-end, identity s2027 combo-only,
# red control (fund sign flip) s42 end-to-end. Sequential: one engine cell of mine at a time.
cd /workspace/alloc_2026-09-26/devices || exit 9
R=/workspace/alloc_2026-09-26/receipts
PY=/workspace/venv/bin/python
echo "START $(date -u +%FT%TZ) pgid=$(ps -o pgid= $$ | tr -d ' ')"
env -i PATH=/usr/bin:/bin HOME=/root $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule inservice --mix shared --engine --engine-identity; echo "RC identity_s42=$?"
env -i PATH=/usr/bin:/bin HOME=/root $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 2027 --rule inservice --mix shared; echo "RC identity_s2027_combo=$?"
env -i PATH=/usr/bin:/bin HOME=/root $PY -B alloc_chain_run.py PATH,HOME,LC_CTYPE $R --seed 42 --rule inservice --mix fundflip --engine; echo "RC red_s42=$?"
echo "END $(date -u +%FT%TZ)"
