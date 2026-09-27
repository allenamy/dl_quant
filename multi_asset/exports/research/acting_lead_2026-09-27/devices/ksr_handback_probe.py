"""Read-only, descriptive KSR handback diagnostic. No fitting or candidate gate.

Uses archived legs and target summaries, never treats a HOLD target zero as a
zero position. Run on Pod with OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=1.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path('/workspace/ksr_2026-09-27')
ROLES = {'BASE': 'KSR_S0_m0', 'COMP': 'KSR_COMP_ONLY_m0',
         'SEAT': 'KSR_SEAT_ONLY_m0', 'FULL': 'KSR_S1_m0'}
STATS_SHA = '21ae14c455b2c2295fab5e4828b28fe4724a405a990c97c0cf180599e365e6b2'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def same(x, y):
    return x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()


def month_mask(axis, year, month):
    lo = int(dt.datetime(year, month, 1, tzinfo=dt.timezone.utc).timestamp())
    hi = int(dt.datetime(year, month + 1, 1, tzinfo=dt.timezone.utc).timestamp())
    mask = (axis >= lo) & (axis < hi)
    assert np.array_equal(axis[mask], np.arange(lo, hi, 14400)), 'incomplete 4h month'
    return mask


def main():
    pins, stats, metadata = {}, {}, {}
    for seed in (42, 2027):
        stats[seed] = {}
        for role, label in ROLES.items():
            p = ROOT / 'targets_stats' / f'{label}_s{seed}.npz'
            r = p.with_suffix('.json'); rec = json.loads(r.read_text())
            assert (rec['label'], rec['seed'], rec['self_sha256']) == (label, str(seed), STATS_SHA)
            pins[str(r)] = sha(r); pins[str(p)] = sha(p)
            assert pins[str(p)] == rec['out_sha256']
            metadata[f'{role}_s{seed}'] = rec
            with np.load(p, allow_pickle=False) as z:
                stats[seed][role] = {k: z[k] for k in z.files}
    base = stats[42]['BASE']; axis = base['anchors']; legaxis = base['legs_E_ts']
    for cell in [v for seed in stats.values() for v in seed.values()]:
        assert same(cell['anchors'], axis) and same(cell['legs_E_ts'], legaxis)
        assert set(np.unique(cell['scaled_kind'])) <= {0, 1, 2}, 'unknown publication kind'
        assert np.isfinite(cell['gross']).all() and (cell['gross'] >= 0).all()
    lp = {role: ROOT / 'legs' / f'{label}.npz' for role, label in ROLES.items() if role in ('BASE', 'COMP')}
    for role, p in lp.items():
        pins[str(p)] = sha(p)
        for seed in (42, 2027):
            assert pins[str(p)] == metadata[f'{role}_s{seed}']['legs_sha256']
    leg_months = {}; equal_arrays = []; differing_arrays = []
    with np.load(lp['BASE'], allow_pickle=False) as a, np.load(lp['COMP'], allow_pickle=False) as b:
        assert set(a.files) == set(b.files)
        assert same(a['E_ts'], legaxis) and same(a['E_ts'], b['E_ts'])
        for key in a.files:
            x, y = a[key], b[key]
            (equal_arrays if same(x, y) else differing_arrays).append(key)
            if key == 'KZ':
                for year in (2024, 2025, 2026):
                    for month in (1, 2):
                        m = month_mask(legaxis, year, month)
                        # Equality includes missing patterns and IEEE signed-zero bytes.
                        leg_months[f'{year}-{month:02d}'] = same(x[m], y[m])
        assert set(differing_arrays) <= {'KZ'}, differing_arrays
    months = {}
    for year in (2024, 2025, 2026):
        for month in (1, 2):
            m = month_mask(axis, year, month); label = f'{year}-{month:02d}'
            rows = {}
            for seed in (42, 2027):
                bb = stats[seed]['BASE']; rr = {}
                for role, v in stats[seed].items():
                    assert not v['pad_before_new_axis'][m].any(), 'padded diagnostic month'
                    k = v['scaled_kind'][m]; gross = v['gross'][m]
                    assert set(np.unique(k)) <= {0, 2}, 'King fallback in declared HOLD-contract month'
                    rr[role] = {'anchors': int(m.sum()), 'kind_counts': {str(int(a)): int(b) for a, b in zip(*np.unique(k, return_counts=True))},
                        'gross_mean_target_encoding': float(gross.mean()),
                        'kind_diff_from_base': int(np.count_nonzero(k != bb['scaled_kind'][m])),
                        'gross_diff_from_base_max': float(np.max(np.abs(gross - bb['gross'][m]))),
                        'published_target_gross_mean': float(gross[k == 2].mean()) if (k == 2).any() else None}
                rows[str(seed)] = rr
            months[label] = {'COMP_KZ_equals_BASE': leg_months[label], 'by_seed': rows}
    for p, h in pins.items():
        assert sha(p) == h, 'input mutated during read: ' + p
    print(json.dumps({'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'DESCRIPTIVE_NOT_CANDIDATE_GATE',
        'input_sha256': pins, 'metadata': metadata, 'COMP_vs_BASE_equal_leg_arrays': equal_arrays,
        'COMP_vs_BASE_differing_leg_arrays': differing_arrays, 'months': months,
        'limits': ['HOLD target zeros are absence of published target, not zero position.',
                   'Deleted candidate per-path inventories were not reconstructed.',
                   'Post-hoc diagnostic; no new significance or deployment claim.']}, allow_nan=False))


if __name__ == '__main__':
    main()
