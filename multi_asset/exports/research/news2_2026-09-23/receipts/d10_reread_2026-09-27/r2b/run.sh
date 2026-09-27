#!/bin/bash
RR=/workspace/d10_reread_2026-09-27; L=/dev/shm/news2_reread/r2b_20260927T113701Z; O=$RR/r2b_20260927T113701Z; PY=/workspace/venv/bin/python; DEV=$RR/devices
mkdir -p $O
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> $L/run.log; }
say START pgid=$(ps -o pgid= -p $$ | tr -d ' ')
summ() { $PY -c "import json;d=json.load(open('$1/D10_LEDGER_MS_BUILD.json'));c=d['positive_control_reconciliation'];p=(d.get('rev2_extension') or {}).get('prefix_identity') or {};print(c['verdict'],'fold_removed',c.get('fold_removed'),'derived',c.get('expected_extras_derived_from_ms_key'),'in_window',c.get('rows_in_old_window'),'bitwise',c.get('ALL_BITWISE'),'not_allowed',c.get('not_allowed_differences'),'overlap_unequal',c.get('api_overlap_unequal'),'prefix',p.get('verdict'),p.get('src_upgraded_rows_api_to_both'),'after',p.get('rows_after_prefix'),'last',d['new_ledger']['ft_last'],'mut',d.get('CONTROL_MUTATION'))"; }
nice -n 10 $PY -B $DEV/d10_build_ledger_ms.py --out $O/v1 > $L/v1.log 2>&1; say "V1 rc=$?"
say "V1 $($PY -B $DEV/d10_dryrun_compare.py npz /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz $O/v1/ledger_full_ms.npz $L/v1_npz.json)"
say "V1 $($PY -B $DEV/d10_dryrun_compare.py json $RR/refs_ledger_ms_build_e179071d.json $O/v1/D10_LEDGER_MS_BUILD.json $L/v1_json.json --volatile self_sha256,seconds,new_ledger.path,new_ledger.sha256 --oneway argv,python)"
EXT="--extra-api $RR/r1_api/api_funding_ms_20260831_20260927T08.json.gz --prefix-ledger /dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz --prefix-sha e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88"
nice -n 10 $PY -B $DEV/d10_build_ledger_ms.py --out $O/r2 $EXT --out-name ledger_full_ms_ext_20260927T08.npz > $L/r2.log 2>&1; say "R2 rc=$?"
say "R2 $(summ $O/r2 2>&1)"
nice -n 10 $PY -B $DEV/d10_build_ledger_ms.py --out $O/r2_same_second $EXT --out-name ledger_ss.npz --control-mutation same_second_extra > $L/r2_ss.log 2>&1; say "R2_same_second rc=$?"
say "R2_same_second $(summ $O/r2_same_second 2>&1)"
say DONE
