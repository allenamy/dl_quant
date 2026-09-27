#!/bin/bash
T=/workspace/d10_ledgerms_rev2_2026-09-27; L=/dev/shm/news2_ledgerms_rev2_2026-09-27/r21; PY=/workspace/venv/bin/python
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> $L/run.log; }
say START pgid=$(ps -o pgid= -p $$ | tr -d ' ')
rm -rf $T/v1 $T/v2
nice -n 10 $PY -B $T/devices/d10_build_ledger_ms.py --out $T/v1b > $L/v1.log 2>&1; say "V1 rc=$?"
say "V1 $($PY -B $T/devices/d10_dryrun_compare.py npz /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz $T/v1b/ledger_full_ms.npz $L/v1_npz.json)"
say "V1 $($PY -B $T/devices/d10_dryrun_compare.py json $T/refs/D10_LEDGER_MS_BUILD.json $T/v1b/D10_LEDGER_MS_BUILD.json $L/v1_json.json --volatile self_sha256,seconds,new_ledger.path,new_ledger.sha256 --oneway argv,python)"
nice -n 10 $PY -B $T/devices/d10_build_ledger_ms.py --out $T/v2b --extra-zips-root /dev/shm/d10_2026-09-25/zips --extra-months 2026-08 --prefix-ledger /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz --prefix-sha e179071d5955 --out-name ledger_full_ms_v2test.npz > $L/v2.log 2>&1; say "V2 rc=$?"
say "V2 $($PY -c "import json;d=json.load(open('$T/v2b/D10_LEDGER_MS_BUILD.json'));c=d['positive_control_reconciliation'];p=d['rev2_extension']['prefix_identity'];print(c['verdict'],c.get('src_zip_iv_changes'),c.get('src_zip_iv_changes_that_are_allowed_upgrades'),c.get('src_zip_iv_changes_not_allowed'),p['verdict'],p['src_upgraded_rows_api_to_both'],p['src_upgraded_by_month'],p['rows_after_prefix'])")"
say DONE
