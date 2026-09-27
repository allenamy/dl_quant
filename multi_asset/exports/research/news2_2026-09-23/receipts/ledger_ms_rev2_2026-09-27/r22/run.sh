#!/bin/bash
T=/workspace/d10_ledgerms_rev2_2026-09-27; L=/dev/shm/news2_ledgerms_rev2_2026-09-27/r22_20260927T065456Z; O=$T/r22_20260927T065456Z; PY=/workspace/venv/bin/python; DEV=$T/devices_r22
mkdir -p $O
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> $L/run.log; }
say START pgid=$(ps -o pgid= -p $$ | tr -d ' ')
EXT="--extra-zips-root /dev/shm/d10_2026-09-25/zips --extra-months 2026-08 --prefix-ledger /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz --prefix-sha e179071d5955"
summ() { $PY -c "import json;d=json.load(open('$1/D10_LEDGER_MS_BUILD.json'));c=d['positive_control_reconciliation'];p=(d.get('rev2_extension') or {}).get('prefix_identity') or {};print(c['verdict'],'not_allowed',c.get('not_allowed_differences'),'allowed',c.get('src_zip_iv_changes_that_are_allowed_upgrades'),'ft_d',c.get('ft_differences'),'rate_d',c.get('rate_differences'),'prefix',p.get('verdict'),p.get('n_symbols_differing'),p.get('src_upgraded_by_month'),'after',p.get('rows_after_prefix'),'mut',d.get('CONTROL_MUTATION'))"; }
nice -n 10 $PY -B $DEV/d10_build_ledger_ms.py --out $O/v1 > $L/v1.log 2>&1; say "V1 rc=$?"
say "V1 $($PY -B $DEV/d10_dryrun_compare.py npz /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz $O/v1/ledger_full_ms.npz $L/v1_npz.json)"
say "V1 $($PY -B $DEV/d10_dryrun_compare.py json $T/refs/D10_LEDGER_MS_BUILD.json $O/v1/D10_LEDGER_MS_BUILD.json $L/v1_json.json --volatile self_sha256,seconds,new_ledger.path,new_ledger.sha256 --oneway argv,python)"
for M in none rate_extra ft_extra rate_prefix; do
  nice -n 10 $PY -B $DEV/d10_build_ledger_ms.py --out $O/v2_$M $EXT --out-name ledger_v2_$M.npz --control-mutation $M > $L/v2_$M.log 2>&1; say "V2_$M rc=$?"
  say "V2_$M $(summ $O/v2_$M 2>&1)"
done
say DONE
