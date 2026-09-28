"""Read existing pooled simulation paths under the user's new evaluation priority.

This is retrospective description, not a re-registration or release decision.
Uses the frozen economic reader and cross-checks its September results first.
No training, simulation, exchange calls, or production writes.
"""
import argparse
import gc
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'


def run(contract_path, out):
    c = json.loads(contract_path.read_text())
    spec = importlib.util.spec_from_file_location('economic', c['reader_path'])
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    if E.sha(c['reader_path']) != c['reader_sha256']:
        raise ValueError('reader identity')
    if E.sha(E.ENGINE / 'news_stats.py') != E.STATS_SHA:
        raise ValueError('stats identity')
    sys.path.insert(0, str(E.ENGINE))
    import news_stats as S
    import bt_tables as BT
    import bt_driver_lib as DL
    import numpy as np
    for name, digest in S.DEV.items():
        if E.sha(E.ENGINE / name) != digest:
            raise ValueError('dependency changed: ' + name)
    S.BT, S.DL = BT, DL
    result = dict(status='RETROSPECTIVE_NEW_OBJECTIVE_NO_RELEASE',
        utc=time.strftime('%FT%TZ', time.gmtime()), source_sha256=E.sha(__file__),
        contract_sha256=E.sha(contract_path), reader_sha256=c['reader_sha256'],
        python=sys.executable, numpy=np.__version__, windows=c['windows'], results={})
    for name, obj in c['candidates'].items():
        if E.sha(obj['receipt_path']) != obj['receipt_sha256']:
            raise ValueError('old receipt identity: ' + name)
        old = json.loads(Path(obj['receipt_path']).read_text())
        for seed in (42, 2027):
            at = f"ALLOC_{obj['rule']}_shared_s{seed}X_scaled_rule_raw_UAFE"
            rt = f'DLARCH_REF_NC_s{seed}X_scaled_rule_raw_UAFE'
            pa, fa = S.load_cell(f"{obj['root']}/cells/{obj['rule']}_shared_s{seed}/runs/{at}", at)
            pb, fb = S.load_cell(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{seed}X/runs/{rt}', rt)
            previous = old['results'][str(seed)]
            if fa != previous['candidate_paths'] or fb != previous['baseline_paths']:
                raise ValueError('path identity drift: ' + name)
            if len(pa) != 32 or len(pb) != 32:
                raise ValueError('missing paths')
            A = pa[0]['A']
            for p in pa + pb:
                if not np.array_equal(A, p['A']) or not np.isfinite(p['nav5']).all() or BT.g_identity_err(p) > 1e-5:
                    raise ValueError('axis/finite/cash identity')
            row = dict(candidate_paths=fa, baseline_paths=fb, results={})
            for label, bounds in c['windows'].items():
                m0 = S.seg_mask(A, *bounds)
                days = S.full_days(A, m0)
                mask = m0 & np.isin(A // 86400 * 86400, days)
                if mask.sum() != 6 * len(days) or len(days) < 2:
                    raise ValueError('incomplete dates')
                am, bm, diffs = [], [], []
                for a, b in zip(pa, pb):
                    ar, ad, _ = E.path_metrics(a, mask, days, S, BT)
                    br, bd, _ = E.path_metrics(b, mask, days, S, BT)
                    am.append(ar); bm.append(br); diffs.append(ad - bd)
                d = np.stack(diffs).mean(0)
                r = dict(n_days=len(days), first_anchor=int(A[mask][0]), last_anchor=int(A[mask][-1]),
                    candidate={k:E.dist([x[k] for x in am]) for k in am[0]},
                    baseline={k:E.dist([x[k] for x in bm]) for k in bm[0]},
                    paired_daily_bps=float(1e4*d.mean()), ci95_bps=E.ci30(d,S))
                if label == 'Sep01_18_descriptive':
                    prev = previous['results'][label]
                    for arm in ('candidate','baseline'):
                        for metric in r[arm]:
                            for agg in r[arm][metric]:
                                if abs(r[arm][metric][agg]-prev[arm][metric][agg]) > 1e-12:
                                    raise ValueError('original September reproduction failed')
                    r['original_September_all_metrics_reproduced'] = True
                row['results'][label] = r
            result['results'][f'{name}_s{seed}'] = row
            print('DONE', name, seed, flush=True)
            del pa, pb
            gc.collect()
    with out.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False); f.flush(); os.fsync(f.fileno())
    print('READOUT_COMPLETE', E.sha(out), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    run(a.contract,a.out)
