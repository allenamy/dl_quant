#!/usr/bin/env python3
"""Monthly 2026 seat means on the RESEARCH axis, for reconciliation against the live record.

WHY MONTHLY AND WHY EXTENDED: seat_weights_probe.py froze SEG["2026"] at 2026-08-31T00:00Z, while the
append-only live record (~/regime_dash/regime_dash.jsonl) starts 2026-09-02T08:00Z. Compared as
written, the two windows DO NOT OVERLAP AT ALL, so a year-pooled research number beside a
September-only live number would be two different populations wearing one label. This device therefore
  * runs to the axis's LAST anchor, and
  * reports the frozen truncation alongside, so the dropped tail is visible rather than silent,
  * and prints the overlap window explicitly, because that is the only window where the two can be
    compared at all.
Read-only: loads legs.npz, prints, writes one receipt.
"""
import calendar
import collections
import json
import os
import sys
import time

import numpy as np

W = os.environ.get('NEWS2_ROOT', '/dev/shm/news2_2026-09-23')
OUT = sys.argv[1] if len(sys.argv) > 1 else None

leg = np.load(W + '/work/legs.npz')
a = leg['E_ts'].astype(np.int64)
WL = leg['WL']
ready = leg['ready']
FROZEN_2026_HI = calendar.timegm(time.strptime('2026-08-31T00:00:00Z', '%Y-%m-%dT%H:%M:%SZ'))


def masked(mask):
    """The SAME arithmetic as seat_weights_probe.py: w0 = WL0/(WL0+WL2), the model seat."""
    w = WL[mask]
    den = w[:, 0] + w[:, 2]
    ok = den > 1e-12
    w0 = np.where(ok, w[:, 0] / np.where(ok, den, 1), 0.5)
    return w0, w, int((~ok).sum())


base = ready & np.isfinite(WL).all(1)
ym = np.array([time.strftime('%Y-%m', time.gmtime(int(t))) for t in a])

rows = []
for m in sorted(set(ym[(ym >= '2026-01') & base])):
    sel = base & (ym == m)
    w0, w, degen = masked(sel)
    rows.append({'month': m, 'n': int(sel.sum()), 'masked_w0_model_mean': float(w0.mean()),
                 'masked_w0_model_median': float(np.median(w0)),
                 'masked_w0_p10': float(np.percentile(w0, 10)),
                 'masked_w0_p90': float(np.percentile(w0, 90)),
                 'raw_WL_mean': [float(x) for x in w.mean(0)],
                 'degenerate_den_anchors': degen,
                 'first_anchor_utc': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(int(a[sel][0]))),
                 'last_anchor_utc': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(int(a[sel][-1])))})

ext = base & (a >= calendar.timegm(time.strptime('2026-01-01T00:00:00Z', '%Y-%m-%dT%H:%M:%SZ')))
frz = ext & (a <= FROZEN_2026_HI)
w0e, _, _ = masked(ext)
w0f, _, _ = masked(frz)

rec = {
    'device': 'seat_monthly_probe.py', 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'source': W + '/work/legs.npz',
    'axis_last_anchor_utc': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(int(a[base][-1]))),
    'monthly': rows,
    '2026_extended_to_axis_end': {'n': int(ext.sum()), 'masked_w0_model_mean': float(w0e.mean()),
                                  'masked_w0_model_median': float(np.median(w0e))},
    '2026_frozen_truncated_at_2026-08-31': {'n': int(frz.sum()),
                                            'masked_w0_model_mean': float(w0f.mean()),
                                            'masked_w0_model_median': float(np.median(w0f))},
    'anchors_the_frozen_bound_drops': int(ext.sum() - frz.sum()),
}
print(json.dumps(rec, indent=1))
if OUT:
    with open(OUT, 'w') as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print('receipt=' + OUT)
