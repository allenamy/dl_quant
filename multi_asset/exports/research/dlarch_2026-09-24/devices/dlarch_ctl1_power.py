#!/usr/bin/env python3
"""dlarch_ctl1_power.py -- can control 1 (shuffle-future) say anything on fold 202609? Zero GPU.

WHY THIS RUNS BEFORE THE GPU. Control 1 retrains one fold on shuffled labels and asks whether the IC
collapses "to near zero, distributed like the null". That question is only answerable if the UNSHUFFLED
model's IC on the same fold is clearly ABOVE the null. If it is not, then "IC sits at the null" is an
instrument ceiling and would be true whether or not leakage exists -- the same shape as the saturated G4
census and the unreachable condition-2 threshold. So the power is measured first, and the criterion is
written against the measured null, before any shuffled result exists.

THE NULL IS THE FROZEN ONE. news2_diag1_score_ic.ic_series takes an `rng` and shuffles `yy` -- the finite
subset within each anchor -- which is exactly "permute the name axis inside each anchor's eligible cells
WITHOUT moving the population". That is the shuffle lead specified, and it is already frozen code, so it
is called rather than re-implemented (null_randomisation_must_not_move_the_population).

usage: dlarch_ctl1_power.py <env-whitelist> <fold-dir> <out.json> [B]
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
FOLD, OUT = sys.argv[2], sys.argv[3]
B = int(sys.argv[4]) if len(sys.argv) > 4 else 2000

LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
LAB_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


assert sha(LAB) == LAB_SHA, 'the label file changed'
sys.path.insert(0, '/dev/shm/news2_2026-09-23/devices')
import news2_diag1_score_ic as DIAG                                   # noqa: E402

T = np.load(LAB, allow_pickle=True)
A = T['E_ts'].astype(np.int64)
Y = T['y4s']
pos = {int(t): i for i, t in enumerate(A)}

z = np.load(os.path.join(FOLD, 'scores.npz'))
P, ts = z['P'], z['E_ts'].astype(np.int64)
ai = np.array([pos.get(int(t), -1) for t in ts])
ok = ai >= 0
# absolute alignment, asserted -- not inferred from a peak shape (protocol 10-d)
assert np.array_equal(np.asarray(ts)[ok].astype(np.int64), A[ai[ok]].astype(np.int64)), \
    'label timestamps do not equal prediction timestamps; refusing to measure power on a shifted pairing'
rows_p, rows_y = np.flatnonzero(ok), ai[ok]

ics_real, nn, skipped = DIAG.ic_series(P, Y, rows_p, rows_y)
real = float(ics_real.mean())

null_means = []
for b in range(B):
    rng = np.random.default_rng(20260926 + b)
    ics, _n, _s = DIAG.ic_series(P, Y, rows_p, rows_y, rng=rng)
    if ics.size:
        null_means.append(float(ics.mean()))
nm = np.array(null_means)

q = {f'p{p}': float(np.percentile(nm, p)) for p in (2.5, 5, 50, 95, 97.5)}
sd = float(nm.std(ddof=1))
rec = {
    'device': 'dlarch_ctl1_power.py', 'self_sha256': sha(os.path.abspath(__file__)),
    'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'fold_dir': FOLD, 'scores_sha256': sha(os.path.join(FOLD, 'scores.npz')),
    'frozen_ic_device': '/dev/shm/news2_2026-09-23/devices/news2_diag1_score_ic.py',
    'frozen_ic_sha256': sha('/dev/shm/news2_2026-09-23/devices/news2_diag1_score_ic.py'),
    'min_names': DIAG.MIN_NAMES, 'n_anchors_scored': int(ics_real.size), 'n_anchors_skipped': int(skipped),
    'caliber': 'dlw_targets y4s, SCORE layer only; never quote as a return',
    'unshuffled_mean_ic': real,
    'null_B': int(nm.size), 'null_mean': float(nm.mean()), 'null_sd': sd, 'null_percentiles': q,
    'z_unshuffled_vs_null': (real - float(nm.mean())) / sd if sd > 0 else None,
    'unshuffled_above_null_p97_5': real > q['p97.5'],
    'POWER': None, 'why': None,
}
z_ = rec['z_unshuffled_vs_null']
if rec['unshuffled_above_null_p97_5'] and z_ is not None and z_ >= 3.0:
    rec['POWER'] = 'HAS_RESOLUTION'
    rec['why'] = ('the unshuffled model sits %.1f null sd above the null mean and above its 97.5th '
                  'percentile, so "collapsed to the null" is a reachable and meaningful outcome' % z_)
else:
    rec['POWER'] = 'NO_RESOLUTION'
    rec['why'] = ('the unshuffled model is NOT clearly above the null on this fold, so a shuffled run '
                  'landing at the null would be uninformative -- it would happen with or without '
                  'leakage. Spending GPU on control 1 for this fold is not justified as written.')
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)

print('fold            : %s' % os.path.basename(FOLD.rstrip('/')))
print('anchors scored  : %d (skipped %d, MIN_NAMES=%d)' % (ics_real.size, skipped, DIAG.MIN_NAMES))
print('unshuffled IC   : %+.6f' % real)
print('null (B=%d)   : mean %+.6f  sd %.6f  [p2.5 %+.6f, p97.5 %+.6f]'
      % (nm.size, nm.mean(), sd, q['p2.5'], q['p97.5']))
print('z vs null       : %+.2f' % (z_ if z_ is not None else float('nan')))
print('POWER           : %s' % rec['POWER'])
print('  %s' % rec['why'])
print('receipt=%s sha256=%s' % (OUT, sha(OUT)[:16]))
