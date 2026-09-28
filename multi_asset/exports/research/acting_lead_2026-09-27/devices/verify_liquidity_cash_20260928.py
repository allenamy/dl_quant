"""Independent raw-array readout check; does not import the tested readout."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(root, out):
    ep = root / 'receipts/ECONOMIC_FULL_BOOK.json'
    e = json.loads(ep.read_text())
    checks, hashes, largest = 0, {}, 0.0
    pairs = {}

    def equal(got, expected, context):
        nonlocal checks, largest
        a, b = np.asarray(got, float), np.asarray(expected, float)
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('shape/nonfinite ' + context)
        err = float(np.max(np.abs(a - b)))
        largest = max(largest, err)
        if not np.allclose(a, b, atol=1e-9, rtol=1e-10):
            raise ValueError(f'{context}: {err}')
        checks += 1

    for seed in (42, 2027):
        rec = e['results'][str(seed)]
        items = {w: {'baseline': [], 'candidate': [], 'stress': []} for w in e['windows']}
        axes = None
        for kind, tag, base in (
            ('candidate', f'ALLOC_xib_shared_s{seed}X_scaled_rule_raw_UAFE', root / f'cells/xib_shared_s{seed}/runs'),
            ('baseline', f'DLARCH_REF_NC_s{seed}X_scaled_rule_raw_UAFE', Path(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{seed}X/runs')),
        ):
            facts = rec[kind + '_paths']
            assert [x['seed'] for x in facts] == list(range(32))
            for k in range(32):
                p = base / tag / f'PATH_{tag}_seed_{k:02d}.npz'
                h = sha(p)
                assert h == facts[k]['npz_sha256']
                hashes[str(p)] = h
                j = json.loads(p.with_suffix('.json').read_text())
                assert j['seed'] == k and j['npz_sha256'] == h
                with np.load(p) as z:
                    a = z['A']
                    assert np.isfinite(a).all() and np.array_equal(a, a.astype(np.int64))
                    a = a.astype(np.int64)
                    assert np.all(a % 14400 == 0) and np.all(np.diff(a) == 14400)
                    if axes is None: axes = a.copy()
                    else: assert np.array_equal(axes, a)
                    r = z['navm1'] / z['navm0'] - 1
                    tau = z['turnover'] / (2 * z['nav0'])
                    assert np.isfinite(r).all() and np.isfinite(tau).all() and np.all(tau >= 0)
                    cash = z['price_trade'] + z['funding'] - z['fee'] - z['unk_excluded'] * (z['unk_price'] + z['unk_funding'])
                    equal(r, cash / z['nav0'], f'cash/{seed}/{kind}/{k}')
                    for w, (lo, hi) in e['windows'].items():
                        lo, hi = (int(datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()) for t in (lo, hi))
                        mask = (a >= lo) & (a <= hi)
                        day, counts = np.unique(a[mask] // 86400, return_counts=True)
                        days = day[counts == 6]
                        idx = np.where(mask & np.isin(a // 86400, days))[0]
                        aa = a[idx].reshape(-1, 6)
                        assert np.array_equal(aa, days[:, None] * 86400 + np.arange(6)[None, :] * 14400)
                        rr = r[idx].reshape(-1, 6)
                        rd = np.prod(1 + rr, axis=1) - 1
                        start5 = (a[idx[0]] - int(z['nav5_t0'])) // 300
                        end5 = (a[idx[-1]] + 14400 - int(z['nav5_t0'])) // 300
                        nav = z['nav5_main'][start5:end5 + 1]
                        assert len(nav) == len(idx) * 48 + 1
                        assert np.isfinite(nav).all() and np.all(nav > 0)
                        m = {'return_compound': np.prod(1 + rd) - 1,
                             'cagr': np.prod(1 + rd) ** (365 / len(rd)) - 1,
                             'sharpe_daily': rd.mean() / rd.std(ddof=1) * math.sqrt(365),
                             'maxdd_5m': np.min(nav / np.maximum.accumulate(nav) - 1),
                             'mean_daily_bps': rd.mean() * 1e4,
                             'worst_day': rd.min(),
                             'turnover_over_sizing_gross_per_anchor': tau[idx].mean()}
                        items[w][kind].append((m, rd))
                        if kind == 'candidate':
                            sr = r[idx] - z['turnover'][idx] / z['nav0'][idx] * .0005
                            items[w]['stress'].append(np.prod(1 + sr.reshape(-1, 6), axis=1) - 1)
                        row = rec['results'][w]
                        equal([len(days), len(idx), a[idx[0]], a[idx[-1]]],
                              [row['n_days'], row['n_anchors'], row['first_anchor'], row['last_anchor']], f'population/{seed}/{w}')
        pairs[str(seed)] = {}
        for w, s in items.items():
            row = rec['results'][w]
            for kind in ('candidate', 'baseline'):
                for metric in s[kind][0][0]:
                    equal(np.mean([m[metric] for m, _ in s[kind]]), row[kind][metric]['mean'], f'metric/{seed}/{w}/{kind}/{metric}')
            d = np.mean([x[1] - y[1] for x, y in zip(s['candidate'], s['baseline'])], axis=0)
            ds = np.mean([x - y[1] for x, y in zip(s['stress'], s['baseline'])], axis=0)
            equal(d, row['paired_daily_returns'], f'daily/{seed}/{w}')
            equal(d.mean() * 1e4, row['paired_daily_bps'], f'paired/{seed}/{w}')
            equal(ds.mean() * 1e4, row['extra5bps_candidate_only_paired_daily_bps'], f'stress/{seed}/{w}')
            pairs[str(seed)][w] = {'base_daily_bps': float(d.mean()*1e4), 'stress_daily_bps': float(ds.mean()*1e4)}
    result = {'status': 'RAW_ARRAY_RECALCULATION_PASS', 'source_sha256': sha(__file__),
              'economic_sha256': sha(ep), 'n_path_files': len(hashes), 'comparisons': checks,
              'largest_absolute_difference': largest, 'paths': hashes, 'paired': pairs,
              'limits': 'Arithmetic/identity validation only. Shared raw simulator outputs, not independent validation of simulator economics or live parity.'}
    with open(out, 'x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k,v in result.items() if k not in ('paths','paired')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    x = p.parse_args()
    main(x.root, x.out)
