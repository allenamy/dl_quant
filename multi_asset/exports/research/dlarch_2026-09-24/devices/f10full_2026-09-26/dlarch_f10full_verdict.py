#!/usr/bin/env python3
"""dlarch_f10full_verdict.py -- F10_FULL book-layer verdict under DL-gate revision 7 (2ddf8dada), assembled
from the ALREADY-COMMITTED verdict device plus the three pieces that device leaves out.

ORDERING, STATED PLAINLY (lesson of DL-gate section 10):
  * the gated arithmetic is dlarch_paired_d.py (4e293147), last changed in d308a0ca8 at 06:08Z -- BEFORE the
    first F10_FULL book-layer reading (seed 42 cell, 06:14:57Z). This file runs it UNCHANGED.
  * THIS wrapper is written AFTER all three F10_FULL cells exist (06:14Z / 07:20Z / 08:28Z), and dlarch HAS
    READ their per-seed dbar-vs-NC-s42 lines in the cells driver log while resuming (17:2xZ). The maxdd
    numbers had not been looked at. So this wrapper is NOT blind; it therefore authors NO threshold and NO
    clause -- every rule below is transcribed from a text committed before the readings, with its source:
      (a) drawdown guardrail = DL-gate section 3 condition 4 via revision 4 ("pre-2026 maxdd, fixed 2x
          per-anchor compounded NAV, seed-averaged, not worse than T0 by more than 3 pp"). Revision 7 moved
          the d pairing to NC and is SILENT on the guardrail's comparator, so BOTH are computed: vs T0 (the
          literal text) and vs in-service NC (revision 7's pairing). If they disagree, that is reported as a
          question for lead, not resolved here. Same extraction as the committed dlarch_t3_verdict.py
          (judge_table.pre2026.paths.maxdd_5m.path_mean), which is imported by reading, not retyped.
      (b) the s7 baseline disposition = prereg C1.7 (daf21cc47, 06:19Z; the s2027 identity reading came at
          07:11Z): identical => s7 stays, basis "2 seeds x 2 folds", s7 itself inherited; different => s7
          leaves the gate and n = 2.
      (c) control 1 must precede the verdict (C1.11, lead): the control-1 receipt is REQUIRED and recorded;
          a FAIL there marks the book verdict unusable, because a leak would invalidate the arm's readings.
  * the gate verdict comes from paired_d's GATED column only; the T0 column is reference-only (rev 7).

usage: dlarch_f10full_verdict.py <env-whitelist> <W> <out.json>
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
W, OUT = sys.argv[2], sys.argv[3]
RDIR = os.path.join(W, 'receipts')

PAIRED_D_PIN = '4e2931477654e5cfa006b75c93f85b4333fee92196f2e4ea2fce7f365df0e741'
SIGMA_PIN = 'd4ba45d6cff42d6eb1f18cd1af562c92cc2b2b37b3e45abfed7cc4095ab87eaa'
IDENTITY_PIN = '2d9b9736f6d64c8a9fbb29e65c8165f6788fe27794f97031bac8d7c37f302ad3'
CTL1_VERDICT_DEVICE_PIN = '382bc74df0e3882f3d513e2c9fe0699d51fd16c60b10ba38ea16c05f085c284c'
DD_TOL_PP = 3.0
ENGINE = '/dev/shm/news2_2026-09-23/engine'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ── (c) control 1 first: the verdict waits for it ──────────────────────────────────────────────
C1P = os.path.join(RDIR, 'CTL1_VERDICT_2026-09-26.json')
assert os.path.exists(C1P), 'control 1 has no verdict yet; the book verdict waits for it (C1.11)'
C1 = json.load(open(C1P))
assert C1['self_sha256'] == CTL1_VERDICT_DEVICE_PIN and C1['VERDICT'] in ('PASS', 'FAIL')

# ── (b) C1.7 disposition ────────────────────────────────────────────────────────────────────────
IDP = os.path.join(W, 'f10full_2026-09-26/receipts/S2027_IDENTITY_2026-09-26.json')
assert sha(IDP) == IDENTITY_PIN
ID = json.load(open(IDP))
if ID['all_identical'] is True and ID['positive_control'].startswith('PASS'):
    c17 = {'reading': 'IDENTICAL (2 folds 2023/202609, positive control PASS)', 'receipt_sha256': IDENTITY_PIN,
           'disposition': 's7 baseline KEPT; basis = bitwise identity on 2 seeds (42 via G1, 2027 via C1.7) x '
                          '2 folds; s7 itself remains INHERITED, never verified directly', 'n_gate': 3}
else:
    sys.exit('C1.7 says s7 leaves the gate (n = 2); that branch needs paired_d without the s7 arm cell -- '
             'refusing rather than silently keeping s7')

# ── the gated arithmetic: the committed device, unchanged ──────────────────────────────────────
PD = os.path.join(W, 'dlarch_paired_d.py')
assert sha(PD) == PAIRED_D_PIN, 'paired_d changed since it was committed before the readings'
SIGR = os.path.join(RDIR, 'SIGMA_F10_2026-09-25.json')
assert sha(SIGR) == SIGMA_PIN
pd_out = os.path.join(RDIR, 'PAIRED_D_F10FULL_2026-09-26.json')
cmd = [sys.executable, '-B', PD, ','.join(sorted(WL)), RDIR, SIGR, ENGINE, pd_out,
       '--arm-glob', 'RETAIN_F10FULL_s*_2026-09-26.json', '--arm-tagkey', 'DLARCH_G1_T0_nomask_frac1_s',
       '--base-glob', 'RETAIN_REFNC_s*_2026-09-26.json', '--base-tagkey', 'DLARCH_REF_NC_s',
       '--base-glob', 'RETAIN_s*_2026-09-25.json', '--base-tagkey', 'DLARCH_T0_s']
cp = subprocess.run(cmd, cwd=W, env={k: os.environ[k] for k in WL if k in os.environ},
                    capture_output=True, text=True)
sys.stdout.write(cp.stdout)
sys.stderr.write(cp.stderr)
assert cp.returncode == 0, f'paired_d failed rc={cp.returncode}'
PDR = json.load(open(pd_out))
assert PDR['self_sha256'] == PAIRED_D_PIN
assert sorted(PDR['arm_cells']) == ['2027', '42', '7'], PDR['arm_cells']
gated = PDR['per_baseline']['DLARCH_REF_NC_s']
assert gated['role'] == 'GATED' and gated['stage1_seeds_complete'] is True
assert PDR['routes']['DLARCH_REF_NC_s']['routes_agree'] and PDR['routes']['DLARCH_T0_s']['routes_agree']


# ── (a) drawdown guardrail, both comparators ───────────────────────────────────────────────────
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


dd_arm = maxdd('RETAIN_F10FULL_s*_2026-09-26.json', 'DLARCH_G1_T0_nomask_frac1_s')
guard = {}
for name, pat, key in (('vs_T0_literal_section3', 'RETAIN_s*_2026-09-25.json', 'DLARCH_T0_s'),
                       ('vs_NC_revision7_pairing', 'RETAIN_REFNC_s*_2026-09-26.json', 'DLARCH_REF_NC_s')):
    base = maxdd(pat, key)
    seeds = sorted(set(dd_arm) & set(base))
    assert seeds == [7, 42, 2027], (name, seeds)
    a = 100.0 * sum(dd_arm[s] for s in seeds) / len(seeds)
    b = 100.0 * sum(base[s] for s in seeds) / len(seeds)
    guard[name] = {'seeds': seeds, 'arm_mean_pp': a, 'base_mean_pp': b, 'arm_minus_base_pp': a - b,
                   'per_seed_arm': {s: dd_arm[s] for s in seeds}, 'per_seed_base': {s: base[s] for s in seeds},
                   'passes': (a - b) >= -DD_TOL_PP}
guard['comparators_agree'] = guard['vs_T0_literal_section3']['passes'] == guard['vs_NC_revision7_pairing']['passes']

v = gated['verdict']
# The guardrail can only CHANGE a RECOMMEND/EXTEND (condition 4 is a conjunct of those); a REJECT stands.
if v in ('RECOMMEND_TO_USER', 'EXTEND'):
    if not guard['comparators_agree']:
        v = v + '_PENDING_LEAD_GUARDRAIL_COMPARATOR'
    elif not guard['vs_T0_literal_section3']['passes']:
        v = 'UNDECIDED'
usable = C1['VERDICT'] == 'PASS'
rec = {'device': 'dlarch_f10full_verdict.py', 'self_sha256': sha(os.path.abspath(__file__)),
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'blind': False,
       'blindness_statement': 'paired_d (the gated arithmetic) was committed before any F10_FULL book reading; this '
                              'wrapper was written after all three cells existed and after dlarch read their '
                              'dbar-vs-NC-s42 log lines; it authors no threshold (sources listed in the docstring)',
       'criterion': 'DL-gate revision 4 clauses with revision 7 pairing (d vs in-service NC, same seed)',
       'paired_d_receipt': {'path': pd_out, 'sha256': sha(pd_out)},
       'gated_segments': gated['segments'], 'gated_reject_clauses_fired': gated['reject_clauses_fired'],
       'paired_d_verdict': gated['verdict'],
       'reference_T0_column': PDR['per_baseline']['DLARCH_T0_s'],
       'drawdown_guardrail': guard,
       'C1_7': c17,
       'control_1': {'path': C1P, 'sha256': sha(C1P), 'VERDICT': C1['VERDICT'], 'IC_shuf': C1['IC_shuf'],
                     'null_p97_5': C1['null_p97_5']},
       'VERDICT': v if usable else 'VOID_CONTROL_1_FAILED (paired_d said %s)' % v,
       'not_a_deployment_authorisation': 'any RECOMMEND is a book-behaviour change for the user; seed 42 only'}
y = gated['segments']['2026']
if y['mean_d'] < 0:
    rec['clause_5_note'] = 'still below the in-service NC in 2026 (the gate IS the NC pairing under revision 7)'
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=str)
with open(OUT) as f:
    assert json.load(f)['VERDICT'] == rec['VERDICT']
for n in ('vs_T0_literal_section3', 'vs_NC_revision7_pairing'):
    g = guard[n]
    print('guardrail %-24s arm %.2f pp  base %.2f pp  diff %+.2f pp  passes=%s'
          % (n, g['arm_mean_pp'], g['base_mean_pp'], g['arm_minus_base_pp'], g['passes']))
print('control 1: %s   C1.7: %s' % (C1['VERDICT'], c17['disposition'][:40]))
print('F10FULL_VERDICT=%s out=%s sha256=%s' % (rec['VERDICT'], OUT, sha(OUT)))
