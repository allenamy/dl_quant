#!/usr/bin/env python3
"""dlarch_c19_rejudge.py -- prereg C1.9 / C1.10: re-judge the k > 0 side of the offset spectrum with
F10_FULL's OWN cross-seed dispersion, now that its three seeds exist.

WHAT WAS ALREADY READ WHEN THIS WAS WRITTEN (stated, not hidden): the pooled spectra of F10_FULL s42 and of
the in-service NC s42 / s2027 (LEAK_SPECTRUM_COMPARISON_2026-09-26.json, daf21cc47). The F10_FULL s2027 and
s7 spectra DO NOT EXIST at commit time (resume inventory 7faae4332: C1_9_spectra 2027 = [], 7 = []); they
are produced by the frozen dlarch_f10full_leak.py (26c9ff6e) only after this device is committed.

WHAT C1.9 FIXED, AND WHAT IT DID NOT. C1.9 (lead) asked that the k > 0 point-wise difference between
F10_FULL and the in-service NC be "within seed noise", and named that its only noise scale was ONE
pairwise difference between two NC seeds; C1.10 ruled control 2 PASS-by-intent and ordered this re-judge
"with F10_FULL's own cross-seed dispersion". C1.9's own table marked a point as within when
|difference| / scale <= 1 (0.4x ticked, 3.9-5.8x flagged). This device keeps exactly that form and only
swaps the scale:
    D_k      = mean over s in {42, 2027} of [ FULL_s(k) - NC_s(k) ]       (same-seed; the in-service NC
                                                                           exists only at 42 and 2027)
    sigma_k  = sd over s in {42, 2027, 7} of FULL_s(k), ddof = 1           (F10_FULL's own dispersion)
    within_k = |D_k| <= sigma_k                                            (C1.9 table convention, 1x)
    safe_k   = D_k < 0      (less correlation with FUTURE labels than NC: the opposite of look-ahead)
The 1x multiple is INHERITED from C1.9's table, not authored here, and dlarch has a stake in this arm, so
the receipt marks it `multiple_inherited_from_C1_9_table_lead_to_confirm`. No disposition is written here:
the disposition belongs to lead (C1.10). Reported beside it, not gating: the 3-seed mean of FULL minus the
2-seed mean of NC, each seed's own difference, and the NC-pair spread C1.9 used, so the two scales can be
compared.

Convention (unchanged from daf21cc47): IC(k) = corr(P at anchor t, Y at anchor t+k); k > 0 = look-ahead side.

usage: dlarch_c19_rejudge.py <env-whitelist> <out.json> FULL42 FULL2027 FULL7 NC42 NC2027
       (each a receipt written by dlarch_f10full_leak.py)
"""
import hashlib
import json
import os
import statistics as st
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL)
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]
PATHS = dict(zip(('FULL42', 'FULL2027', 'FULL7', 'NC42', 'NC2027'), sys.argv[3:8]))
assert len(PATHS) == 5
LEAK_DEVICE_PIN = '26c9ff6e53a5fa977f0b9b42633c0bf28b616a4ec47f7584fda0477a764f0753'
KPOS = (1, 2, 3, 4, 5)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


R, SP = {}, {}
for name, p in PATHS.items():
    r = json.load(open(p))
    assert r['self_sha256'] == LEAK_DEVICE_PIN, f'{name}: not written by the frozen leak device'
    assert r['control_2_positive_control']['PASS'] is True, f'{name}: its positive control did not pass'
    assert r['control_2_absolute_alignment']['timestamp_mismatches_at_k0'] == 0, f'{name}: misaligned'
    seed = name[4:] if name.startswith('FULL') else name[2:]
    assert r['arm_dir'].rstrip('/').endswith(f'f10_s{seed}'), (name, r['arm_dir'])
    if name.startswith('FULL'):
        assert '/G1_T0_nomask_frac1/' in r['arm_dir'], (name, r['arm_dir'])
    else:
        assert r['arm_dir'].startswith('/dev/shm/news2_2026-09-23/work/'), (name, r['arm_dir'])
    R[name] = {'path': p, 'sha256': sha(p), 'arm_dir': r['arm_dir']}
    SP[name] = {int(k): v['ic'] for k, v in r['control_2_spectra']['POOLED']['spectrum'].items()}

per_k = {}
for k in KPOS:
    full = [SP['FULL42'][k], SP['FULL2027'][k], SP['FULL7'][k]]
    d42, d2027 = SP['FULL42'][k] - SP['NC42'][k], SP['FULL2027'][k] - SP['NC2027'][k]
    D = (d42 + d2027) / 2
    sig = st.stdev(full)
    per_k[k] = {'FULL_s42': full[0], 'FULL_s2027': full[1], 'FULL_s7': full[2],
                'NC_s42': SP['NC42'][k], 'NC_s2027': SP['NC2027'][k],
                'd_same_seed_s42': d42, 'd_same_seed_s2027': d2027,
                'D_k_mean_same_seed': D, 'sigma_k_FULL_3seed_sd': sig,
                'abs_D_over_sigma': abs(D) / sig if sig > 0 else None,
                'within_1x': abs(D) <= sig, 'D_negative_safe_direction': D < 0,
                'descriptive_mean3FULL_minus_mean2NC': sum(full) / 3 - (SP['NC42'][k] + SP['NC2027'][k]) / 2,
                'descriptive_C1_9_scale_NC_pair_spread': abs(SP['NC42'][k] - SP['NC2027'][k])}

rec = {'device': 'dlarch_c19_rejudge.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'inputs': R,
       'form': 'D_k = mean_s{42,2027}(FULL_s - NC_s); sigma_k = sd_s{42,2027,7}(FULL_s), ddof 1; within iff |D_k| <= sigma_k',
       'multiple_inherited_from_C1_9_table_lead_to_confirm': 1.0,
       'already_read_when_written': ['F10_FULL s42 pooled spectrum', 'NC s42 / s2027 pooled spectra'],
       'per_k': per_k,
       'all_k_positive_within_1x': all(v['within_1x'] for v in per_k.values()),
       'all_k_positive_D_negative': all(v['D_negative_safe_direction'] for v in per_k.values()),
       'n_within': sum(v['within_1x'] for v in per_k.values()),
       'disposition': 'NOT WRITTEN HERE -- lead (C1.10). This receipt only replaces the noise scale.',
       'named_limit': 'sigma from n=3 seeds has a wide sampling band (a 1-sided 80% upper bound is ~1.8x the '
                      'point value); D_k averages only 2 same-seed pairs because in-service NC exists at 42 and 2027 only.'}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
for k, v in per_k.items():
    print('k=+%d  D %+.5f  sigma %.5f  |D|/sigma %.2f  within=%s  negative=%s  (NC-pair %.5f)'
          % (k, v['D_k_mean_same_seed'], v['sigma_k_FULL_3seed_sd'], v['abs_D_over_sigma'], v['within_1x'],
             v['D_negative_safe_direction'], v['descriptive_C1_9_scale_NC_pair_spread']))
print('C19_REJUDGE all_within=%s all_negative=%s n_within=%d/5 out=%s sha256=%s'
      % (rec['all_k_positive_within_1x'], rec['all_k_positive_D_negative'], rec['n_within'], OUT, sha(OUT)))
