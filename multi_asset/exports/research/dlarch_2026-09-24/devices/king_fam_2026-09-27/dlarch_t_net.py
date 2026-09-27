#!/usr/bin/env python3
"""dlarch_t_net.py -- the evaluation target T_net of DECISION_RULE_king_improvement_family_2026-09-27.md §1 (lead,
4158f1521), and the label source for the KN arm. Written and committed BEFORE any T_net reading or KN training.

  T_net[A, i] = y4s[A, i] - F[A, i]
  y4s = dlw_targets.npz y4s (ca479fcc): "(E, E+48] raw compounded; all closes observed" -- the v4 RAW accounting caliber and
        EXACTLY the price series the in-service King label ranks (news2_train_king L44-L47). The price half is a BITWISE copy
        and that is ASSERTED, so KN differs from A0 by the funding term only (one change at a time).
        Named reading of the rule's "价格部分逐位复现 legs 的 y4 口径": the y4 King is trained on (dlw_targets y4s). The
        nc_legs y4v (a float32 48-row sum of the rr channel) feeds only the seat LR, is a different caliber, and is NOT used.
  F   = funding a LONG pays over (A, A+4h]: sum of the settled rates of name i whose settlement time t satisfies A < t <= A+4h
        (a settlement exactly at A+4h belongs to the position held since A; one exactly at A does not), decimal units.
        Source = PRODUCER caliber, old P2 ledger_full.npz (bea6f575, second key) == ledger_full_ms folded to seconds
        (b355c1a55, bitwise) -- the rule's truth source. A name with no settlement in the window has F = 0.
  Coverage: the ledger ends 2026-09-01T02Z, so T_net is NaN for every anchor with A + 4h > ledger end (named); y4s NaN stays
  NaN. Nothing is ranked here: the rule ranks T_net within each anchor's members at use time (trainer / IC device).
CONTROLS (all must pass, else the device refuses to write the output):
  C1 price identity: where F == 0, T_net == y4s BITWISE; everywhere, T_net + F == y4s within float64 rounding (1e-15 rel).
  C2 synthetic known answer: one name, settlements at A+4h (in), A+5s (in), A (out) with rates 1e-4, 2e-4, 5e-4 => F = 3e-4.
  C3 red control: shifting every settlement time by +4h must change F on > 0 anchors (and the count is recorded).
  C4 coverage census: count of anchors with any settlement, share of cells with F != 0, and the anchor cut at ledger end.

usage: dlarch_t_net.py <env-whitelist> <out.npz> <receipt.json>
"""
import hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT, REC = sys.argv[2], sys.argv[3]
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
LED = '/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz'
PIN = {LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       LED: 'bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad'}
H4 = 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


for p, w in PIN.items():
    assert sha(p) == w, f'input moved: {p}'
T = np.load(LAB, allow_pickle=True); E = T['E_ts'].astype(np.int64); syms = [str(s) for s in T['symbols']]
y4s = T['y4s']                                              # float32, as the King label reads it
Z = np.load(LED, allow_pickle=True); assert [str(s) for s in Z['symbols']] == syms, 'ledger symbol order differs'
o = Z['off'].astype(np.int64); ft_all = Z['ft'].astype(np.int64); rt_all = Z['rate'].astype(np.float64)
LEDGER_END = int(ft_all.max())


def funding_matrix(shift=0):
    F = np.zeros((len(E), len(syms)))
    for j in range(len(syms)):
        ft, rt = ft_all[o[j]:o[j + 1]] + shift, rt_all[o[j]:o[j + 1]]
        if not len(ft):
            continue
        assert np.all(np.diff(ft) >= 0), 'ledger not time-sorted'
        lo, hi = np.searchsorted(ft, E, 'right'), np.searchsorted(ft, E + H4, 'right')      # (A, A+4h]
        cs = np.concatenate([[0.0], np.cumsum(rt)])
        F[:, j] = cs[hi] - cs[lo]
    return F


F = funding_matrix()
covered = E + H4 <= LEDGER_END
y = y4s.astype(np.float64)
Tn = y - F
Tn[~covered] = np.nan
# C1 price identity
z0 = covered[:, None] & (F == 0) & np.isfinite(y)
c1_bitwise = bool(np.array_equal(Tn[z0], y[z0]))
fin = covered[:, None] & np.isfinite(y)
c1_add = float(np.max(np.abs((Tn[fin] + F[fin]) - y[fin]))) if fin.any() else 0.0
C1 = {'bitwise_where_F_is_0': c1_bitwise, 'cells_F0': int(z0.sum()), 'max_abs(T_net + F - y4s)': c1_add,
      'PASS': c1_bitwise and c1_add <= 1e-15 * max(1.0, float(np.nanmax(np.abs(y[fin]))))}
# C2 synthetic known answer (same window rule, same cumsum code path)
A0_ = 1_000_000
ft_s = np.array([A0_, A0_ + 5, A0_ + H4]); rt_s = np.array([5e-4, 2e-4, 1e-4])
cs_s = np.concatenate([[0.0], np.cumsum(rt_s)])
f_s = cs_s[np.searchsorted(ft_s, A0_ + H4, 'right')] - cs_s[np.searchsorted(ft_s, A0_, 'right')]
C2 = {'F_synthetic': float(f_s), 'expected': 3e-4, 'PASS': abs(f_s - 3e-4) < 1e-18}
# C3 red control
F_red = funding_matrix(shift=H4)
changed = int(np.sum(np.any(np.abs(F_red - F)[covered] > 0, axis=1)))
C3 = {'anchors_changed_by_4h_shift': changed, 'PASS': changed > 0}
# C4 census
C4 = {'anchors_total': int(len(E)), 'anchors_covered': int(covered.sum()),
      'last_covered_anchor_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(E[covered].max()))),
      'ledger_end_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(LEDGER_END)),
      'anchors_with_any_settlement': int(np.sum(np.any(F[covered] != 0, axis=1))),
      'share_cells_F_nonzero_among_finite_y': float(np.mean(F[fin] != 0)) if fin.any() else None}
ok = C1['PASS'] and C2['PASS'] and C3['PASS']
rec = {'device': 'dlarch_t_net.py', 'self_sha256': sha(os.path.abspath(__file__)), 'inputs': PIN,
       'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'criterion': 'DECISION_RULE_king_improvement_family_2026-09-27.md §1 (4158f1521)',
       'definition': 'T_net = y4s - F, F = sum of settled rates in (A, A+4h], producer caliber (old P2, second key); decimal units',
       'C1_price_identity': C1, 'C2_known_answer': C2, 'C3_red_shift': C3, 'C4_census': C4, 'ALL_CONTROLS_PASS': ok}
if ok:
    np.savez(OUT, E_ts=E, symbols=np.array(syms), T_net=Tn, F=F, covered=covered)
    rec['output'] = {'path': OUT, 'sha256': sha(OUT)}
    chk = np.load(OUT, allow_pickle=True)                   # read back through the same reader before reporting
    assert np.array_equal(chk['T_net'], Tn, equal_nan=True) and np.array_equal(chk['E_ts'], E)
with open(REC, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=float)
with open(REC) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('T_NET %s out=%s receipt=%s sha256=%s' % ('DONE' if ok else 'REFUSED_CONTROLS', OUT if ok else '-', REC, sha(REC)), flush=True)
sys.exit(0 if ok else 1)
