#!/usr/bin/env python3
"""Receipt lead's confirmation of control 1's threshold, BEFORE the shuffled run exists.

WHY NOW AND NOT WITH THE RESULT. A threshold confirmed in the same receipt as the number it judges cannot
be shown to have preceded it. This is written while the shuffled run has NOT been started -- proven below
by recording that the shuffled arm's output directory does not exist and that the shuffle-arm trainer has
never produced a fold receipt. So the ordering is a fact in the file, not a claim in a message.
"""
import glob
import hashlib
import json
import os
import time

R = '/workspace/dlarch_2026-09-24/receipts/'
POWER = 'CTL1_POWER_202609_2026-09-26.json'
SHUF_TRAINER = '/workspace/dlarch_2026-09-24/f10full_shuffle_2026-09-26/dlarch_train_f10.py'
SHUF_OUT_GLOB = '/workspace/dlarch_2026-09-24/T3/*_SHUFFLED*/**'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


existing = glob.glob(SHUF_OUT_GLOB, recursive=True)
rec = {
    'device': "lead's ruling transcribed by dlarch; no measurement here",
    'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'subject': 'control 1 (shuffle-future) decision threshold, prereg C1.11.2',
    'threshold': 'IC_shuf <= p97.5 of the null built from the SHUFFLED model\'s OWN predictions => PASS',
    'sided': 'one-sided; leakage shows as IC ABOVE the null, so no lower gate',
    'threshold_confirmed_by_lead': True,
    'confirmation_text': ("lead 2026-09-26: IC_shuf <= p97.5(the shuffled model's own null) is PASS, "
                          "one-sided; this is the correct operationalisation of my wording. Change "
                          "threshold_pending_lead_confirmation to confirmed_by_lead."),
    'authorship': ('threshold confirmed by lead, who has no stake in what this arm admits. dlarch '
                   'operationalised the wording and explicitly declined to own the threshold '
                   '(criterion_author_must_have_no_stake).'),
    'supersedes': 'prereg C1.11.2 field threshold_pending_lead_confirmation: true',

    # the ordering, as a fact rather than an assertion
    'ordering_proof': {
        'shuffled_run_started': bool(existing),
        'shuffled_output_paths_found': existing[:5],
        'shuffle_arm_trainer': SHUF_TRAINER,
        'shuffle_arm_trainer_sha256': sha(SHUF_TRAINER),
        'shuffle_arm_fold_receipts': len(glob.glob(
            '/workspace/dlarch_2026-09-24/T3/*_SHUFFLED*/f10_s*/*/FOLD_RECEIPT.json')),
        'note': ('this receipt is written while the shuffled arm has produced NOTHING, so the threshold '
                 'demonstrably precedes the reading it will judge'),
    },
    'power_receipt': {'path': R + POWER, 'sha256': sha(R + POWER)},
    'power_summary': {k: json.load(open(R + POWER))[k] for k in
                      ('unshuffled_mean_ic', 'null_mean', 'null_sd', 'z_unshuffled_vs_null', 'POWER')},
}
p = R + 'CTL1_THRESHOLD_CONFIRMED_2026-09-26.json'
with open(p, 'w') as f:
    json.dump(rec, f, indent=2, sort_keys=True)
print('threshold:', rec['threshold'])
print('confirmed_by_lead:', rec['threshold_confirmed_by_lead'])
print('shuffled run started yet:', rec['ordering_proof']['shuffled_run_started'],
      '| shuffle-arm fold receipts:', rec['ordering_proof']['shuffle_arm_fold_receipts'])
print('receipt:', p, 'sha', sha(p)[:16])
