#!/usr/bin/env python3
"""Transcribe lead's control-2 ruling into its OWN receipt. No measurement happens here.

WHY A SEPARATE RECEIPT: the measurement receipt is already committed (daf21cc47). Editing it after the
fact would put the numbers and the verdict in one mutable object, so that a later change to the verdict
would silently look like a change to the measurement. This receipt PINS the measurement by sha and adds
only the ruling and its grounds.
"""
import hashlib
import json
import time

R = '/workspace/dlarch_2026-09-24/receipts/'
MEAS = 'LEAK_SPECTRUM_COMPARISON_2026-09-26.json'
UP = ('F10FULL_LEAK_s42_23folds_2026-09-26.json',
      'LEAK_NC_INSERVICE_s42_2026-09-26.json',
      'LEAK_NC_INSERVICE_s2027_2026-09-26.json')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


m = json.load(open(R + MEAS))
neg = [k for k in m['per_k'] if int(k) < 0]
max_neg_ratio = max(m['per_k'][k]['abs_diff_over_spread'] for k in neg)

rec = {
    'device': 'lead ruling transcribed by dlarch; NO measurement is performed here',
    'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'why_a_separate_receipt': (
        'the measurement receipt is already committed (daf21cc47); editing it after the fact would put '
        'the numbers and the verdict in ONE mutable object, so a later change to the verdict would look '
        'like a change to the measurement. This receipt pins that one by sha and adds only the ruling.'),
    'measurement_receipt': {'path': R + MEAS, 'sha256': sha(R + MEAS)},
    'upstream_receipts': {k: {'sha256': sha(R + k)} for k in UP},
    'criterion_source': ('PREREG_dlarch_F10_FULL_2026-09-26.md section 4 control 2; '
                         'ruling by lead 2026-09-26 06:2xZ'),
    'ruling_author': ('lead, who has no stake in what this arm admits; dlarch has a stake and did not '
                      'author the ruling (criterion_author_must_have_no_stake)'),

    'VERDICT_literal': 'FAIL',
    'VERDICT_literal_basis': ('the pre-registered wording requires the offset-spectrum peak at k=0; '
                              'the pooled peak is at k=-3'),
    'VERDICT_by_intent': 'PASS',
    'VERDICT_by_intent_meaning': ('no NEWLY INTRODUCED look-ahead relative to the in-service recipe. '
                                  'This is NOT a claim that no look-ahead exists anywhere, and NOT a '
                                  'claim about features built upstream from future information.'),
    'VERDICT_by_intent_grounds': {
        'i_literal_criterion_also_rejects_the_in_service_recipe': {
            'NC_s42_peak_k': m['peaks']['NC_s42'],
            'NC_s2027_peak_k': m['peaks']['NC_s2027'],
            'FULL_s42_peak_k': m['peaks']['FULL_s42'],
            'all_three_fail_peak_at_0': not any(m['literal_criterion_peak_at_0'].values())},
        'ii_k_negative_shape_is_shared': {
            'max_ratio_to_seed_pair_spread_over_k_lt_0': max_neg_ratio,
            'reading': 'every k<0 point sits within %.1fx the NC seed-pair spread' % max_neg_ratio},
        'iii_every_k_positive_exceedance_is_negative': {
            'all_k_ge_2_differences_negative': m['k_positive_all_differences_negative'],
            'k_positive_within_seed_spread': m['k_positive_within_seed_spread'],
            'meaning': ('lower correlation with FUTURE labels than the in-service NC, i.e. the opposite '
                        'direction to look-ahead. The exceedances are real (3.9-5.8x) and are reported '
                        'as exceedances, not as passes.')}},
    'named_limit_carried_forward': m['named_limit'],
    'pending_rejudge': (
        "C1.9: once F10_FULL has all three seeds (42/2027/7), re-judge the k>0 condition using "
        "F10_FULL's OWN across-seed dispersion instead of the single NC seed-pair difference. Until then "
        'every k>0 multiple has a one-observation denominator.'),
    'what_this_verdict_does_NOT_cover': (
        'control 1 (shuffle-future) has NOT been run -- it needs a one-fold retrain and its place in the '
        'GPU queue is not yet assigned. So section 4 is satisfied by controls 2 and 3 only.'),
}
p = R + 'LEAK_CONTROL2_VERDICT_2026-09-26.json'
with open(p, 'w') as f:
    json.dump(rec, f, indent=2, sort_keys=True)
print('literal: %s | by intent: %s' % (rec['VERDICT_literal'], rec['VERDICT_by_intent']))
g = rec['VERDICT_by_intent_grounds']
print('  i   all three fail peak-at-0 :', g['i_literal_criterion_also_rejects_the_in_service_recipe']
      ['all_three_fail_peak_at_0'])
print('  ii  max k<0 ratio to spread  : %.2fx' % max_neg_ratio)
print('  iii all k>=2 diffs negative  :', g['iii_every_k_positive_exceedance_is_negative']
      ['all_k_ge_2_differences_negative'])
print('receipt: %s  sha256=%s' % (p, sha(p)[:16]))
