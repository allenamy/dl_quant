#!/usr/bin/env python3
"""dlarch_nested_identity.py -- the identity control for the R1.4 trainer (prereg C1.3: new code path =>
transcription + identity control). Run on the --force-epoch 7 control output.

Two identities, both BITWISE on the arrays (P with NaN pattern, rows, E_ts):
  I1  pass 2 (final, 100%, 8 epochs because K=7)  ==  the F10_FULL fold (db6771e3, delivered)
      => the final pass is the F10_FULL recipe exactly; the only thing R1.4 can change is the epoch.
  I2  pass 1 terminal model (85%, epoch 7)         ==  the IN-SERVICE NC fold (news2 f10_s<seed>)
      => the calibration pass is the in-service recipe exactly, AND the per-epoch validation passes do not
         perturb training (they run between epochs; if they consumed RNG or touched state, I2 would fail).
  I3  pass 1 per-epoch train_loss  ==  the in-service NC fold's recorded curve, all 8 epochs, exact float.
Positive control: a copy with ONE finite cell moved by 1e-6 must read DIFFER in the same comparator.
Absolute alignment is part of the comparison (rows and E_ts equal), not inferred from shapes.

usage: dlarch_nested_identity.py <env-whitelist> <control-arm-dir f10_s<seed>> <f10full-dir f10_s<seed>>
                                 <inservice-nc-dir f10_s<seed>> <folds csv> <out.json>
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
CTL, FULL, NC, FOLDS, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(','), sys.argv[6]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def same(za, zb):
    for k in ('rows', 'E_ts'):
        if not np.array_equal(za[k], zb[k]):
            return False, f'{k} differs (alignment)'
    pa, pb = za['P'], zb['P']
    if pa.shape != pb.shape:
        return False, f'shape {pa.shape} vs {pb.shape}'
    fa, fb = np.isfinite(pa), np.isfinite(pb)
    if not np.array_equal(fa, fb):
        return False, f'finiteness differs in {int((fa != fb).sum())} cells'
    d = int((pa[fa] != pb[fb]).sum())
    return d == 0, f'{d} finite cells differ; max|d|={float(np.max(np.abs(pa[fa] - pb[fb]))) if fa.any() else 0.0:.3e}'


res = {}
for f in FOLDS:
    ctl_final = np.load(os.path.join(CTL, f, 'scores.npz'))
    ctl_calib = np.load(os.path.join(CTL, f, 'calib_terminal_scores.npz'))
    full = np.load(os.path.join(FULL, f, 'scores.npz'))
    nc = np.load(os.path.join(NC, f, 'scores.npz'))
    i1, w1 = same(ctl_final, full)
    i2, w2 = same(ctl_calib, nc)
    ne = json.load(open(os.path.join(CTL, f, 'NESTED_EPOCH.json')))
    ncr = json.load(open(os.path.join(NC, f, 'FOLD_RECEIPT.json')))
    c_loss = [c['train_loss'] for c in ne['calib_curve']]
    n_loss = [c['train_loss'] for c in ncr['curve']]
    i3 = c_loss == n_loss
    res[f] = {'I1_final_eq_F10FULL': i1, 'I1_detail': w1, 'I2_calib_terminal_eq_inservice_NC': i2, 'I2_detail': w2,
              'I3_calib_train_loss_eq_NC_curve': i3, 'calib_train_loss': c_loss, 'nc_train_loss': n_loss,
              'epoch_used': ne['epoch_used'], 'force_epoch': ne['force_epoch'],
              'epoch_L370': ne['epoch_L370'], 'epoch_L428': ne['epoch_L428'], 'va_curve_rounded4': ne['va_curve_rounded4'],
              'val_unobservable_anchors_per_epoch': ne['val_unobservable_anchors_per_epoch'],
              'sha': {'ctl_final': sha(os.path.join(CTL, f, 'scores.npz')), 'f10full': sha(os.path.join(FULL, f, 'scores.npz')),
                      'ctl_calib': sha(os.path.join(CTL, f, 'calib_terminal_scores.npz')), 'nc': sha(os.path.join(NC, f, 'scores.npz'))}}
    assert ne['force_epoch'] == 7 and ne['epoch_used'] == 7, 'this control must be run with --force-epoch 7'

# positive control: one finite cell moved by 1e-6 must be seen by the same comparator
f0 = FOLDS[-1]
za = dict(np.load(os.path.join(FULL, f0, 'scores.npz')))
zb = {k: v.copy() for k, v in za.items()}
fin = np.argwhere(np.isfinite(zb['P']))[0]
zb['P'][tuple(fin)] += np.float32(1e-6)
pc_same, pc_detail = same(za, zb)
pc = {'cell': fin.tolist(), 'comparator_says_identical': pc_same, 'detail': pc_detail, 'PASS': not pc_same}

green = pc['PASS'] and all(v['I1_final_eq_F10FULL'] and v['I2_calib_terminal_eq_inservice_NC'] and v['I3_calib_train_loss_eq_NC_curve']
                           for v in res.values())
rec = {'device': 'dlarch_nested_identity.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'control_dir': CTL, 'f10full_dir': FULL, 'nc_dir': NC,
       'folds': res, 'positive_control': pc, 'GREEN': green}
with open(OUT, 'w') as fh:
    json.dump(rec, fh, indent=1, sort_keys=True, default=str)
with open(OUT) as fh:
    assert json.load(fh)['GREEN'] == green
for f, v in res.items():
    print('  %-7s I1 final==F10_FULL %s (%s) | I2 calib==NC %s (%s) | I3 loss curve %s | E370 %s E428 %s va %s'
          % (f, v['I1_final_eq_F10FULL'], v['I1_detail'], v['I2_calib_terminal_eq_inservice_NC'], v['I2_detail'],
             v['I3_calib_train_loss_eq_NC_curve'], v['epoch_L370'], v['epoch_L428'], v['va_curve_rounded4']))
print('  positive control PASS=%s (%s)' % (pc['PASS'], pc['detail']))
print('NESTED_IDENTITY GREEN=%s out=%s sha256=%s' % (green, OUT, sha(OUT)))
