#!/usr/bin/env python3
"""dlarch_red_seats.py -- DESCRIPTIVE (King root cause, part 3b context): how the masked seats move when King is shuffled.
Reads fresh2's rebuilt legs_RED.npz (container sha asserted 7f40e476 by fresh2's device; here the file is pinned by its own
sha at run time and recorded) and the A0 legs; reports per month the masked King seat w0 = WL0/(WL0+WL2) in both, and their
difference. Written and committed before reading. usage: dlarch_red_seats.py <out.json>"""
import calendar, hashlib, json, sys, time
import numpy as np
A0L = '/dev/shm/mretrain_2026-09-26/arms/A0_m0/work/legs.npz'; REDL = '/workspace/mretrain_2026-09-26/redcause/legs_RED.npz'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
A, R = np.load(A0L), np.load(REDL); a = A['E_ts'].astype(np.int64); assert np.array_equal(a, R['E_ts'].astype(np.int64))
def w0(L):
    W = L['WL'].astype(np.float64); s = W[:, 0] + W[:, 2]
    return np.where(s > 1e-12, W[:, 0] / np.where(s > 1e-12, s, 1), np.nan)
wa, wr = w0(A), w0(R); ok = A['ready'] & R['ready'] & np.isfinite(wa) & np.isfinite(wr)
T = lambda y, m: calendar.timegm((y, m, 1, 0, 0, 0))
segs = [('pre2026', T(2023, 7), T(2026, 1))] + [(f'2026-{m:02d}', T(2026, m), T(2026, m + 1)) for m in range(1, 10)]
out = {'device': 'dlarch_red_seats.py', 'inputs': {A0L: sha(A0L), REDL: sha(REDL)}, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'months': {}}
for n, lo, hi in segs:
    s = ok & (a >= lo) & (a < hi)
    out['months'][n] = {'n': int(s.sum()), 'w0_A0': float(wa[s].mean()), 'w0_RED': float(wr[s].mean()), 'dw0_RED_minus_A0': float((wr[s] - wa[s]).mean())}
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('RED_SEATS DONE', json.dumps({k: (round(v['w0_A0'], 3), round(v['w0_RED'], 3)) for k, v in out['months'].items()}))
