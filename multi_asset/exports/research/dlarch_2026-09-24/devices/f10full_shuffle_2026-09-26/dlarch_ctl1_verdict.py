#!/usr/bin/env python3
"""dlarch_ctl1_verdict.py -- control 1 (shuffle-future) verdict, prereg C1.11.2 + C1.12 (lead-confirmed).

WRITTEN AND COMMITTED WHILE THE SHUFFLED ARM HAS PRODUCED NOTHING (resume inventory 7faae4332:
control1_shuffle = NEVER_STARTED, zero outputs, zero logs). The runner run_ctl1.sh records the same
fact again, as a field, at the moment it starts.

CRITERION (frozen, lead-confirmed; not authored here):
    PASS  iff  IC_shuf <= p97.5( null built from the SHUFFLED model's OWN predictions )
    FAIL  otherwise.  One-sided: leakage shows as IC ABOVE the null.
The null is B = 2000 draws of the frozen news2_diag1_score_ic.ic_series `rng` branch, seeds 20260926 + b,
which permutes each anchor's finite cells only (the population does not move).

WHY THIS CALLS dlarch_ctl1_power.py INSTEAD OF REIMPLEMENTING IT: that committed device (4e18a002,
bdb0cb7bc) computes exactly "mean IC of the given fold's P against the real labels, and its own null with
B draws and seeds 20260926 + b". Pointed at the shuffled fold it produces the numbers the criterion needs.
Its field names say `unshuffled_*` because it was written for the power step; this wrapper RE-LABELS them
(IC_shuf = its `unshuffled_mean_ic`) and never edits the frozen device.

Must-report fields that are NOT gates (C1.11.2): IC_shuf, its z vs its own null, the unshuffled reference
(+0.050910, z +10.32, from CTL1_POWER_202609_2026-09-26.json, read not retyped), and the per-anchor IC sd
of the shuffled model against the per-anchor sd under the null (descriptive part of lead's "distributed
like the null"). The latter uses the first NULL_SD_DRAWS null draws with the SAME seeds, to bound cost.

Preconditions asserted on the shuffled fold before anything is computed:
  FOLD_RECEIPT says shuffle_labels=True with a census proving the population did not move; train_frac=1.0;
  seed 42; fold 202609; arm name carries _SHUFFLED; trainer source sha == the pinned shuffle trainer.

usage: dlarch_ctl1_verdict.py <env-whitelist> <shuffled-fold-dir> <power-receipt.json> <power-device.py>
                              <out.json>
"""
import hashlib
import json
import os
import subprocess
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
FOLD, POWR, POWDEV, OUT = sys.argv[2:6]

B = 2000
NULL_SD_DRAWS = 200
SHUF_TRAINER_PIN = '526794e8dceefff2e35f290c6aadc99074edcc7a7468bda81aee15ab6a69af77'
POWER_DEVICE_PIN = '4e18a002da681ab2d1bb8ca0a9ee79b21ad677458750072c7bfab1aeece14386'
POWER_RECEIPT_PIN = '54c9fa765b9b708ca4d9a13b44b7d210e909e04ceaa68f5617f8a81ad7df33f4'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ── preconditions on the object under test ──────────────────────────────────────────────────────
assert sha(POWDEV) == POWER_DEVICE_PIN, 'the frozen power/null device changed'
assert sha(POWR) == POWER_RECEIPT_PIN, 'the unshuffled power receipt changed'
fr = json.load(open(os.path.join(FOLD, 'FOLD_RECEIPT.json')))
assert fr['shuffle_labels'] is True, 'this fold was NOT trained on shuffled labels'
cen = fr['shuffle_census']
assert cen['finiteness_pattern_identical'] and cen['per_anchor_member_multiset_identical'], cen
assert fr['train_params']['train_frac'] == 1.0 and fr['train_params']['no_mask'] is True
assert fr['seed'] == 42 and fr['fold'] == '202609', (fr['seed'], fr['fold'])
assert '_SHUFFLED' in fr['arm'], fr['arm']
tsrc = [v for k, v in fr['sources'].items() if k.endswith('dlarch_train_f10.py')]
assert tsrc == [SHUF_TRAINER_PIN], f'trainer that produced this fold is not the pinned shuffle trainer: {tsrc}'
assert sha(os.path.join(FOLD, 'scores.npz')) == fr['score_sha256'], 'scores.npz does not match its receipt'

# ── the gated number: frozen device, pointed at the shuffled fold ──────────────────────────────
null_out = OUT[:-5] + '_NULL_B%d.json' % B
env = {k: os.environ[k] for k in WL if k in os.environ}
cp = subprocess.run([sys.executable, '-B', POWDEV, ','.join(sorted(WL)), FOLD, null_out, str(B)],
                    env=env, capture_output=True, text=True)
sys.stdout.write(cp.stdout)
sys.stderr.write(cp.stderr)
assert cp.returncode == 0, f'frozen null device failed rc={cp.returncode}'
NR = json.load(open(null_out))
assert NR['self_sha256'] == POWER_DEVICE_PIN and NR['null_B'] == B
assert NR['scores_sha256'] == fr['score_sha256'], 'the null device read a different scores.npz'
ic_shuf = NR['unshuffled_mean_ic']          # re-labelled: this IS the shuffled model's IC
p975 = NR['null_percentiles']['p97.5']
verdict = 'PASS' if ic_shuf <= p975 else 'FAIL'

# ── descriptive: per-anchor dispersion vs the null's (not a gate) ───────────────────────────────
import numpy as np                                                     # noqa: E402
sys.path.insert(0, '/dev/shm/news2_2026-09-23/devices')
import news2_diag1_score_ic as DIAG                                   # noqa: E402
T = np.load('/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz',
            allow_pickle=True)
A, Y = T['E_ts'].astype(np.int64), T['y4s']
pos = {int(t): i for i, t in enumerate(A)}
z = np.load(os.path.join(FOLD, 'scores.npz'))
P, ts = z['P'], z['E_ts'].astype(np.int64)
ai = np.array([pos.get(int(t), -1) for t in ts])
ok = ai >= 0
assert np.array_equal(ts[ok], A[ai[ok]]), 'absolute alignment failed'
rp, ry = np.flatnonzero(ok), ai[ok]
ics, _n, _s = DIAG.ic_series(P, Y, rp, ry)
assert abs(float(ics.mean()) - ic_shuf) < 1e-12, 'descriptive path disagrees with the frozen device'
null_sds = [float(DIAG.ic_series(P, Y, rp, ry, rng=np.random.default_rng(20260926 + b))[0].std(ddof=1))
            for b in range(NULL_SD_DRAWS)]

PW = json.load(open(POWR))
rec = {'device': 'dlarch_ctl1_verdict.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'criterion': 'IC_shuf <= p97.5(null of the shuffled model own predictions, B=2000, seeds 20260926+b) '
                    '=> PASS; one-sided. Authored/confirmed by lead (C1.12, CTL1_THRESHOLD_CONFIRMED sha 9eb2cbd1)',
       'shuffled_fold': FOLD, 'fold_receipt_sha256': sha(os.path.join(FOLD, 'FOLD_RECEIPT.json')),
       'scores_sha256': fr['score_sha256'], 'shuffle_census': cen, 'train_params': fr['train_params'],
       'null_receipt': {'path': null_out, 'sha256': sha(null_out)},
       'IC_shuf': ic_shuf, 'null_mean': NR['null_mean'], 'null_sd': NR['null_sd'],
       'null_p97_5': p975, 'null_percentiles': NR['null_percentiles'],
       'z_shuf_vs_own_null': NR['z_unshuffled_vs_null'],
       'n_anchors_scored': NR['n_anchors_scored'], 'n_anchors_skipped': NR['n_anchors_skipped'],
       'reference_unshuffled': {'receipt_sha256': POWER_RECEIPT_PIN, 'mean_ic': PW['unshuffled_mean_ic'],
                                'z': PW['z_unshuffled_vs_null']},
       'descriptive_per_anchor_sd': {'shuffled_model': float(ics.std(ddof=1)),
                                     'null_mean_of_per_anchor_sd': float(np.mean(null_sds)),
                                     'null_draws_used': NULL_SD_DRAWS},
       'VERDICT': verdict,
       'scope_not_covered': 'a PASS does not prove no leakage anywhere; it says the model cannot learn a '
                            'cross-sectional signal from shuffled labels on this fold. Features built with '
                            'future information (upstream NEWS_FEATURES.npz) are outside this control (prereg §4).'}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)
with open(OUT) as f:
    assert json.load(f)['VERDICT'] == verdict          # read back through the same reader
print('IC_shuf %+.6f  own-null p97.5 %+.6f  z %+.2f  (unshuffled ref %+.6f z %+.2f)'
      % (ic_shuf, p975, NR['z_unshuffled_vs_null'], PW['unshuffled_mean_ic'], PW['z_unshuffled_vs_null']))
print('CTL1_VERDICT=%s out=%s sha256=%s' % (verdict, OUT, sha(OUT)))
