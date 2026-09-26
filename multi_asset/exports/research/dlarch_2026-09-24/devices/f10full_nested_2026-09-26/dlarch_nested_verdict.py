#!/usr/bin/env python3
"""dlarch_nested_verdict.py -- R1.4 (F10_FULL + per-fold nested epoch calibration) book-layer verdict.

WRITTEN AND COMMITTED BEFORE ANY R1.4 READING: at commit time no R1.4 trainer output, cell or receipt exists
(the arm has never run). It authors no threshold; every rule is transcribed:
  * gated arithmetic   = dlarch_paired_d.py (4e293147) UNCHANGED, gate column = in-service NC at the same
                         seed (DL gate revision 7); reference columns = T0 and F10_FULL (never gates);
  * drawdown guardrail = revision 8 (lead 2026-09-26): comparator = in-service NC; T0 comparator reported
                         beside it, not used;
  * s7 baseline        = C1.7 disposition (identity GREEN at s2027 => s7 stays, inherited);
  * preconditions      = (a) the R1.4 identity control GREEN (dlarch_nested_identity.py, pinned receipt);
                         (b) fold-out leakage 0 for every fold of every seed: final-pass max_train_label_end
                         <= cutoff, test_start - cutoff == 240 h, and the calibration slice's last label end
                         <= cutoff (the validation slice sits entirely before the embargo). Any red => VOID.
Must-report (not gates, prereg C1.5/C1.6): per seed per fold E*_L370, E*_L428, agreement, the disagreeing
folds by name with both va values; the E* histogram; and the DEGENERATE-OUTCOME check declared in C1.5 --
if every fold of a seed picked epoch 7, that seed's F10_OOF must be bitwise the F10_FULL one (asserted and
reported), because then R1.4 degenerates to F10_FULL by construction.

usage: dlarch_nested_verdict.py <env-whitelist> <W> <identity-receipt.json> <out.json>
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL)
assert not _x, f'env outside whitelist: {_x}'
W, IDR, OUT = sys.argv[2], sys.argv[3], sys.argv[4]
RDIR = os.path.join(W, 'receipts')
ARM = 'G1_T0_nomask_frac1_nestep'
SEEDS = (42, 2027, 7)
PAIRED_D_PIN = '4e2931477654e5cfa006b75c93f85b4333fee92196f2e4ea2fce7f365df0e741'
SIGMA_PIN = 'd4ba45d6cff42d6eb1f18cd1af562c92cc2b2b37b3e45abfed7cc4095ab87eaa'
C17_PIN = '2d9b9736f6d64c8a9fbb29e65c8165f6788fe27794f97031bac8d7c37f302ad3'
DD_TOL_PP = 3.0
ENGINE = '/dev/shm/news2_2026-09-23/engine'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ── preconditions ─────────────────────────────────────────────────────────────────────────────
ID = json.load(open(IDR))
assert ID['device'] == 'dlarch_nested_identity.py' and ID['GREEN'] is True, 'R1.4 identity control is not GREEN'
C17 = os.path.join(W, 'f10full_2026-09-26/receipts/S2027_IDENTITY_2026-09-26.json')
assert sha(C17) == C17_PIN and json.load(open(C17))['all_identical'] is True

foldout, nested = {}, {}
for s in SEEDS:
    d = os.path.join(W, 'T3', ARM, f'f10_s{s}')
    tr = json.load(open(os.path.join(d, 'TRAIN_RECEIPT.json')))
    assert tr['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED', (s, tr['status'])
    fo, ne = {}, {}
    for f in tr['folds']:
        adm = json.load(open(os.path.join(d, f, 'ADMISSION.json')))
        nep = json.load(open(os.path.join(d, f, 'NESTED_EPOCH.json')))
        assert nep['force_epoch'] == -1, 'a forced-epoch (control) fold inside the arm'
        fo[f] = {'label_end_le_cutoff': adm['max_train_label_end'] <= adm['cutoff'],
                 'embargo_240h': adm['test_start'] - adm['cutoff'] == 864000,
                 'val_slice_before_cutoff': nep['val_last_label_end'] <= adm['cutoff']}
        ne[f] = {k: nep[k] for k in ('epoch_L370', 'epoch_L428', 'selectors_agree', 'epoch_used', 'va_raw',
                                     'va_curve_rounded4', 'val_unobservable_anchors_per_epoch')}
    foldout[s] = fo; nested[s] = ne
FOLDOUT_OK = all(all(all(v.values()) for v in fo.values()) for fo in foldout.values())
disagree = [{'seed': s, 'fold': f, 'L370': v['epoch_L370'], 'L428': v['epoch_L428'],
             'va_L370': v['va_raw'][v['epoch_L370']], 'va_L428': v['va_raw'][v['epoch_L428']]}
            for s, ne in nested.items() for f, v in ne.items() if not v['selectors_agree']]
hist = {}
for ne in nested.values():
    for v in ne.values():
        hist[v['epoch_used']] = hist.get(v['epoch_used'], 0) + 1
degenerate = {}
for s, ne in nested.items():
    if all(v['epoch_used'] == 7 for v in ne.values()):
        a = sha(os.path.join(W, 'T3', ARM, f'f10_s{s}', 'F10_OOF.npz'))
        b = sha(os.path.join(W, 'T3', 'G1_T0_nomask_frac1', f'f10_s{s}', 'F10_OOF.npz'))
        degenerate[s] = {'all_folds_epoch_7': True, 'oof_sha_equal_to_F10_FULL': a == b}
    else:
        degenerate[s] = {'all_folds_epoch_7': False}

# ── gated arithmetic: the committed device, unchanged ───────────────────────────────────────────
PD = os.path.join(W, 'dlarch_paired_d.py')
assert sha(PD) == PAIRED_D_PIN
SIGR = os.path.join(RDIR, 'SIGMA_F10_2026-09-25.json')
assert sha(SIGR) == SIGMA_PIN
pd_out = os.path.join(RDIR, 'PAIRED_D_NESTEP.json')
cmd = [sys.executable, '-B', PD, ','.join(sorted(WL)), RDIR, SIGR, ENGINE, pd_out,
       '--arm-glob', 'RETAIN_NESTEP_s*.json', '--arm-tagkey', f'DLARCH_{ARM}_s',
       '--base-glob', 'RETAIN_REFNC_s*_2026-09-26.json', '--base-tagkey', 'DLARCH_REF_NC_s',
       '--base-glob', 'RETAIN_s*_2026-09-25.json', '--base-tagkey', 'DLARCH_T0_s',
       '--base-glob', 'RETAIN_F10FULL_s*_2026-09-26.json', '--base-tagkey', 'DLARCH_G1_T0_nomask_frac1_s']
cp = subprocess.run(cmd, cwd=W, env={k: os.environ[k] for k in WL if k in os.environ}, capture_output=True, text=True)
sys.stdout.write(cp.stdout); sys.stderr.write(cp.stderr)
assert cp.returncode == 0, f'paired_d failed rc={cp.returncode}'
PDR = json.load(open(pd_out))
assert PDR['self_sha256'] == PAIRED_D_PIN and sorted(PDR['arm_cells']) == ['2027', '42', '7'], PDR['arm_cells']
gated = PDR['per_baseline']['DLARCH_REF_NC_s']
assert gated['role'] == 'GATED' and gated['stage1_seeds_complete'] is True
assert all(v['routes_agree'] for v in PDR['routes'].values())


def maxdd(pattern, tagkey):
    out = {}
    for d in sorted(glob.glob(os.path.join(RDIR, pattern))):
        fs = glob.glob(os.path.join(d, 'RETAIN_*.json'))
        if not fs:
            continue
        r = json.load(open(fs[0]))
        if tagkey not in r['tag']:
            continue
        s = int(''.join(c for c in r['tag'].split(tagkey)[1].split('_')[0] if c.isdigit()))
        out[s] = r['judge_table']['pre2026']['paths']['maxdd_5m']['path_mean']
    return out


dd_arm = maxdd('RETAIN_NESTEP_s*.json', f'DLARCH_{ARM}_s')
guard = {}
for name, pat, key in (('vs_NC_revision8_GATE', 'RETAIN_REFNC_s*_2026-09-26.json', 'DLARCH_REF_NC_s'),
                       ('vs_T0_reported_only', 'RETAIN_s*_2026-09-25.json', 'DLARCH_T0_s')):
    base = maxdd(pat, key)
    ss = sorted(set(dd_arm) & set(base)); assert ss == [7, 42, 2027], (name, ss)
    a = 100.0 * sum(dd_arm[s] for s in ss) / 3; b = 100.0 * sum(base[s] for s in ss) / 3
    guard[name] = {'arm_mean_pp': a, 'base_mean_pp': b, 'arm_minus_base_pp': a - b, 'passes': (a - b) >= -DD_TOL_PP}

v = gated['verdict']
if v in ('RECOMMEND_TO_USER', 'EXTEND') and not guard['vs_NC_revision8_GATE']['passes']:
    v = 'UNDECIDED'                               # condition 4 is a conjunct of RECOMMEND/EXTEND; REJECT stands
if not FOLDOUT_OK:
    v = 'VOID_FOLDOUT_LEAKAGE (paired_d said %s)' % gated['verdict']
rec = {'device': 'dlarch_nested_verdict.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'blind': True,
       'criterion': 'DL gate revision 4 clauses, revision 7 pairing (d vs in-service NC, same seed), revision 8 guardrail vs NC',
       'identity_receipt': {'path': IDR, 'sha256': sha(IDR)}, 'C1_7_receipt_sha256': C17_PIN,
       'foldout_leakage': foldout, 'FOLDOUT_OK': FOLDOUT_OK,
       'nested_epochs': nested, 'epoch_histogram': hist, 'selector_disagreements': disagree,
       'n_selector_disagreements': len(disagree), 'degenerate_outcome_check': degenerate,
       'paired_d_receipt': {'path': pd_out, 'sha256': sha(pd_out)},
       'gated_segments': gated['segments'], 'paired_d_verdict': gated['verdict'],
       'gated_reject_clauses_fired': gated['reject_clauses_fired'],
       'reference_T0': PDR['per_baseline']['DLARCH_T0_s'],
       'reference_F10FULL': PDR['per_baseline']['DLARCH_G1_T0_nomask_frac1_s'],
       'drawdown_guardrail': guard, 'VERDICT': v,
       'stage_2_note': 'EXTEND would need NC reference cells at seeds 11/23/101, which do not exist; lead decides.',
       'not_a_deployment_authorisation': 'any RECOMMEND is a book-behaviour change for the user; seed 42 only'}
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=str)
with open(OUT) as f:
    assert json.load(f)['VERDICT'] == v
print('epoch histogram %s  selector disagreements %d  foldout_ok %s  degenerate %s'
      % (dict(sorted(hist.items())), len(disagree), FOLDOUT_OK, degenerate))
for n, g in guard.items():
    print('guardrail %-22s arm %.2f pp base %.2f pp diff %+.2f pp passes=%s'
          % (n, g['arm_mean_pp'], g['base_mean_pp'], g['arm_minus_base_pp'], g['passes']))
print('NESTEP_VERDICT=%s out=%s sha256=%s' % (v, OUT, sha(OUT)))
