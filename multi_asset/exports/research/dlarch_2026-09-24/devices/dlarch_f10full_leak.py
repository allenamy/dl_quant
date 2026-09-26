#!/usr/bin/env python3
"""dlarch_f10full_leak.py -- F10_FULL prereg section 4 controls 2 and 3 (zero GPU).

WHY NOW AND NOT BEFORE. The delivered T0 family had 36-237 days between the last training label and the
test window, so "strictly OOF, 0 violations" passed with a margin wide enough that a MODERATE look-ahead
would also have passed. --train-frac 1.0 compresses that margin to exactly the embargo (10 days), which
is the first time these two checks have any resolution. Control 1 (shuffle-future) needs a retrain and is
queued for when the GPU frees; these two need none.

CONTROL 3 -- fold-out leakage == 0, as two SEPARATE assertions:
  3a  max_train_label_end <= cutoff        (the trainer already asserts this at L259)
  3b  cutoff + 240h == test_start          (NEW, and the point of the section: with a 180-day margin a
                                            one-anchor error was invisible; at 10 days it is not)
Reported per fold, with the realised lag in days, so "10.0" is a measurement and not an expectation.

CONTROL 2 -- offset spectrum peak at k = 0. For each fold, the cross-sectional Spearman IC between the
fold's own predictions and the labels shifted by k anchors, k in [-K, +K]. The peak must be at k = 0.
A peak at k < 0 means the prediction leads the label, i.e. look-ahead. Two things make this a real test
rather than a formality:
  * the NULL is reported beside it: the IC of the same predictions against labels shifted far away, so a
    reader can see what "no relationship" looks like on this population;
  * a POSITIVE CONTROL is run first -- labels deliberately shifted by -2 anchors must move the measured
    peak to k = -2. An instrument that cannot see a planted 2-anchor lead cannot certify its absence.

Read-only. Loads scores.npz and the label file; writes one receipt.
usage: dlarch_f10full_leak.py <env-whitelist> <arm-dir> <out.json> [max_shift]
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
ARMDIR, OUT = sys.argv[2], sys.argv[3]
K = int(sys.argv[4]) if len(sys.argv) > 4 else 5

LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
LAB_SHA = 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62'
EMBARGO_S = 60 * 14400          # 240 h, the trainer's constant


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''):
            h.update(b)
    return h.hexdigest()


assert sha(LAB) == LAB_SHA, 'the label file changed'
T = np.load(LAB, allow_pickle=True)
A = T['E_ts'].astype(np.int64)
Y = T['y4s']                       # the accounting-caliber label; SCORE-layer use only
SYM = list(T['symbols'])
pos = {t: i for i, t in enumerate(A)}


def xsec_ic(p_rows, y_rows):
    """Mean per-anchor Spearman IC over anchors with >= 20 finite pairs."""
    vals = []
    for pr, yr in zip(p_rows, y_rows):
        ok = np.isfinite(pr) & np.isfinite(yr)
        n = int(ok.sum())
        if n < 20:
            continue
        a = pr[ok].argsort().argsort().astype(np.float64)
        b = yr[ok].argsort().argsort().astype(np.float64)
        a -= a.mean(); b -= b.mean()
        d = float(np.sqrt((a * a).sum() * (b * b).sum()))
        if d > 0:
            vals.append(float((a * b).sum() / d))
    return (float(np.mean(vals)), len(vals)) if vals else (float('nan'), 0)


def spectrum(P, rows_ts, shift_labels_by=0):
    """IC as a function of k: predictions at anchor t vs labels at anchor t+k (in anchor steps)."""
    out = {}
    ai = np.array([pos[t] for t in rows_ts])
    for k in range(-K, K + 1):
        j = ai + k + shift_labels_by
        keep = (j >= 0) & (j < len(A))
        if keep.sum() < 5:
            out[k] = None
            continue
        ic, n = xsec_ic(P[keep], Y[j[keep]])
        out[k] = {'ic': ic, 'n_anchors': n}
    return out


folds, c3 = {}, {}
for tag in sorted(os.listdir(ARMDIR)):
    d = os.path.join(ARMDIR, tag)
    adm, sc = os.path.join(d, 'ADMISSION.json'), os.path.join(d, 'scores.npz')
    if not (os.path.isfile(adm) and os.path.isfile(sc)):
        continue
    a = json.load(open(adm))
    lag_s = a['test_start'] - a['cutoff']
    c3[tag] = {
        '3a_max_train_label_end_le_cutoff': a['max_train_label_end'] <= a['cutoff'],
        '3a_slack_s': a['cutoff'] - a['max_train_label_end'],
        '3b_cutoff_plus_240h_equals_test_start': lag_s == EMBARGO_S,
        '3b_measured_lag_s': lag_s, '3b_measured_lag_days': lag_s / 86400.0,
        'train_anchors': a['train_anchors'], 'accepted_windows': a['accepted_windows']}
    folds[tag] = sc

# ── CONTROL 2. POOLED, because per fold it has no resolution -- and that is a MEASURED statement:
# the first run of this device reported the far-shift null IC at 60-80% of ic(0) on single folds, and its
# positive control (a planted -2 anchor lead) came back as a peak at -3. An instrument that cannot locate
# a lead it was handed cannot certify that none is present, so the per-fold spectra are NOT read. The
# cause is not a coding error: a 4h cross-sectional ranking persists across neighbouring anchors, so
# shifting the labels by a few anchors does not decorrelate them, and a single fold's few hundred anchors
# leave the peak location dominated by noise. Pooling every fold's anchors is the cheap fix; whether it
# is enough is decided by the SAME positive control, re-run on the pooled population.
_ALLP, _ALLTS = [], []
for _t in sorted(folds):
    _z = np.load(folds[_t])
    _ALLP.append(_z['P']); _ALLTS.append(A[_z['rows']])
P = np.concatenate(_ALLP, 0)
rows_ts = np.concatenate(_ALLTS)
assert len(P) == len(rows_ts)

PLANT = -2
# SIGN, derived once and written down because I got it backwards on the first run: spectrum() evaluates
# labels at index ai + k + PLANT, so the true alignment (label index ai) sits at k = -PLANT. Planting -2
# must therefore move the measured peak to k = +2, NOT to -2. My first expectation said -2, the device
# answered +2, and the device was right. Keeping the derivation here so the next reader cannot repeat it.
EXPECT_PEAK = -PLANT
pos_ctl = spectrum(P, rows_ts, shift_labels_by=PLANT)
pc = {k: v['ic'] for k, v in pos_ctl.items() if v}
pos_peak = max(pc, key=lambda k: pc[k]) if pc else None
worst = 'POOLED_%d_folds_%d_anchors' % (len(folds), len(P))

# per-fold resolution, MEASURED rather than asserted: how many single folds locate the planted lead?
perfold_ctl = {}
for _t in sorted(folds):
    _z = np.load(folds[_t])
    _s = spectrum(_z['P'], A[_z['rows']], shift_labels_by=PLANT)
    _v = {k: q['ic'] for k, q in _s.items() if q}
    perfold_ctl[_t] = max(_v, key=lambda k: _v[k]) if _v else None
perfold_hits = sum(1 for v in perfold_ctl.values() if v == EXPECT_PEAK)

spec = {}
_sp = spectrum(P, rows_ts)
_vals = {k: v['ic'] for k, v in _sp.items() if v}
_peak = max(_vals, key=lambda k: _vals[k]) if _vals else None
spec['POOLED'] = {'spectrum': _sp, 'peak_k': _peak, 'peak_at_zero': _peak == 0,
                  'ic_at_0': _vals.get(0), 'ic_at_minus1': _vals.get(-1), 'ic_at_plus1': _vals.get(1),
                  'far_shift_null_ic': _vals.get(-K), 'n_folds_pooled': len(folds),
                  'signal_over_null_at_0': (_vals.get(0) / _vals.get(-K)) if _vals.get(-K) else None}
# per fold kept ONLY as descriptive context, explicitly not read as a verdict
for tag in sorted(folds):
    zz = np.load(folds[tag])
    ss = spectrum(zz['P'], A[zz['rows']])
    vv = {k: v['ic'] for k, v in ss.items() if v}
    pk = max(vv, key=lambda k: vv[k]) if vv else None
    spec['PERFOLD_DESCRIPTIVE_' + tag] = {
        'peak_k': pk, 'ic_at_0': vv.get(0), 'far_shift_null_ic': vv.get(-K),
        'peak_at_zero': pk == 0,
        'NOT_A_VERDICT': 'per-fold resolution is insufficient; see control_2_positive_control'}

rec = {'device': 'dlarch_f10full_leak.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'arm_dir': ARMDIR, 'max_shift_anchors': K,
       'label_file': LAB, 'label_sha256': LAB_SHA,
       'caliber': 'dlw_targets y4s, SCORE layer only; never quote as a return',
       'control_3_foldout_leakage': c3,
       'control_3_all_folds_pass': all(v['3a_max_train_label_end_le_cutoff']
                                       and v['3b_cutoff_plus_240h_equals_test_start']
                                       for v in c3.values()),
       'control_2_positive_control': {
           'population': worst, 'labels_planted_shift_anchors': PLANT,
           'expected_peak_k': EXPECT_PEAK, 'measured_peak_k': pos_peak,
           'PASS': pos_peak == EXPECT_PEAK,
           'per_fold_peak_under_planted_shift': perfold_ctl,
           'per_fold_hits': perfold_hits, 'per_fold_n': len(perfold_ctl),
           'per_fold_resolution_note': (
               'only %d of %d single folds locate a planted %d-anchor lead, which is why the per-fold '
               'spectra below are descriptive and the POOLED one carries the reading.'
               % (perfold_hits, len(perfold_ctl), PLANT)),
           'why': 'an instrument that cannot see a planted 2-anchor lead cannot certify its absence'},
       'control_2_spectra': spec,
       'control_2_pooled_peak_at_zero': spec['POOLED']['peak_at_zero'],
       'control_2_verdict_readable_only_if_positive_control_passes': True,
       'control_1_shuffle_future': 'NOT RUN: needs a retrain (GPU held by the F10_FULL main arm). Queued.',
       'named_limit': ('none of these can exclude features BUILT from future information: the features '
                       'come from NEWS_FEATURES.npz upstream and this arm does not touch them. A smaller '
                       'margin makes that class START to show, which is both the benefit and the risk.')}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)

print('control 3 (fold-out leakage), %d folds:' % len(c3))
for t, v in sorted(c3.items()):
    print('  %-8s 3a=%s slack=%ds  3b=%s lag=%.1f d  train_anchors=%d'
          % (t, v['3a_max_train_label_end_le_cutoff'], v['3a_slack_s'],
             v['3b_cutoff_plus_240h_equals_test_start'], v['3b_measured_lag_days'], v['train_anchors']))
print('control 3 ALL PASS = %s' % rec['control_3_all_folds_pass'])
print('control 2 POSITIVE CONTROL on %s: planted %+d -> expect peak %+d, measured %s  PASS=%s'
      % (worst, PLANT, EXPECT_PEAK, pos_peak, pos_peak == EXPECT_PEAK))
print('  per-fold resolution: %d/%d single folds locate the planted lead' % (perfold_hits, len(perfold_ctl)))
pv = spec['POOLED']
print('control 2 POOLED (%d folds): peak_k=%s ic(0)=%+.5f ic(-1)=%+.5f ic(+1)=%+.5f far_null=%+.5f'
      % (pv['n_folds_pooled'], pv['peak_k'], pv['ic_at_0'], pv['ic_at_minus1'], pv['ic_at_plus1'],
         pv['far_shift_null_ic']))
print('  full pooled spectrum: ' + '  '.join(
    'k=%+d:%+.5f' % (k, v['ic']) for k, v in sorted(pv['spectrum'].items()) if v))
print('control 2 pooled peak at k=0 = %s  (READABLE ONLY IF the positive control above PASSED)'
      % rec['control_2_pooled_peak_at_zero'])
print('DLARCH_F10FULL_LEAK out=%s sha256=%s' % (OUT, sha(OUT)[:16]))
