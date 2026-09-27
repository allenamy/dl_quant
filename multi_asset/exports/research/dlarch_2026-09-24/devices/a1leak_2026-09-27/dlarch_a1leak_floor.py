#!/usr/bin/env python3
"""dlarch_a1leak_floor.py -- lead 2026-09-27 06:0xZ, two DESCRIPTIVE questions on L4c (the A1 all-shuffle arm's IC +0.0028 lies
outside its own permutation null in both segments). Written and committed BEFORE the A0 noise models exist and before any
reading below is computed.

WHAT L4c SHUFFLED (read from dlarch_a1leak_train.py 235dc868, not from memory): permute() reorders, per anchor, the label values
among that anchor's MEMBER cells whose label is finite; one global rng (seed 20260927) walks every anchor once. So it keeps: the
anchor, the member set, the multiset of label values per anchor; it destroys: which asset carries which label (asset identity
within the anchor). Nothing is moved across anchors. Training target = within-anchor rank => the target is a random uniform
ranking per anchor, independent of the features.

WHY A PERMUTATION NULL CAN SIT BELOW A NOISE MODEL (the hypothesis this device measures, not asserts): the L4c null holds the
trained noise model FIXED and destroys the pairing on the test side, so its spread is only the test-label sampling noise of ONE
given score. A model fitted to noise is still a fixed, arbitrary function of the 78 features; its IC against the true label is
that function's projection onto the features' real relationship with returns -- zero on average over noise draws, but not zero
for a given draw, and persistent across time because the function is. The null for "is +0.0028 unusual for a model that learned
nothing" is therefore the spread over DRAWS of such functions, which the L4c null does not contain.

READINGS (fixed here):
 R1 synthetic, no training: 200 random directions w ~ N(0, I_78) (seed 20260927) applied to the within-anchor-ranked X78 of each
    anchor's member rows; score = X_rank . w; pooled IC vs y4s per segment (frozen ic_series, MIN 20), same anchors as L4c.
    Report the distribution (mean, sd, 2.5/97.5 pct, share with |IC| >= 0.0028) and the per-feature pooled IC vector's norm.
    Reading: +0.0028 is "ordinary for an arbitrary feature-built score" iff inside the random-direction [2.5, 97.5] in both
    segments.
 R2 noise-model draws: A0 m0 recipe (annual folds, rs 0) retrained on all-shuffled labels with seeds 20260927 (the SAME
    permuted labels as the A1 L4c arm, same axis and rng) .. 20260930; plus the existing A1 L4c arm (seed 20260927). For each:
    pooled IC vs y4s and T_net per segment; for the two seed-20260927 cells (A0 and A1) also the L4c permutation null, B = 200,
    the L4c code path (ic_series rng, seeds 20260927 + b).
    Reading for lead's question 2: "A0 has the same floor" iff the A0 seed-20260927 IC is outside its own null with the SAME sign
    as A1's in both segments. The noise-draw spread = sd over the 4 A0 seeds (reported; n = 4, a scale, not a sigma).
 R3 relevance to D0 (2026 A1 - A0 at k = 0, y4s spectrum +20.8e-4; T_net verdict +16.9e-4): printed side by side with the
    member-pair sd of D(0) from A1LEAK_STATIC (5.5e-4) and the R1 / R2 spreads. No threshold; a floor that is a per-draw random
    quantity enters D0 only through the member-to-member spread, which the 8 pairs already sample.
usage: dlarch_a1leak_floor.py <env-whitelist> <out.json> <A1_all_dir> <A0_seed_dir>...   (first A0 dir = seed 20260927)
"""
import calendar, hashlib, json, os, sys, time
import numpy as np
from scipy.stats import rankdata

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT, A1DIR, A0DIRS = sys.argv[2], sys.argv[3], sys.argv[4:]
NS2 = '/dev/shm/news2_2026-09-23'; DL = '/workspace/dlarch_2026-09-24'
FEAT = f'{NS2}/work/NEWS_FEATURES.npz'
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
TNET, TREC = f'{DL}/king_fam_2026-09-27/T_NET.npz', f'{DL}/receipts/T_NET_2026-09-27.json'
STATIC = f'{DL}/receipts/A1LEAK_STATIC_2026-09-27.json'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       TNET: '929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c',
       STATIC: '482047ae13b025814433c314f08090b2cd882eda1cbf8f2f8f13c625fff559db',
       f'{NS2}/devices/news2_diag1_score_ic.py': '291d800709650dddac72ba347cd151e71a8b0d22c730b535f3298e85bf6c79fc'}
SEED, B_NULL, NDIR, FLOOR = 20260927, 200, 200, 0.0028
T_ = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))
iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(t)))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


for p, w in PIN.items():
    assert sha(p) == w, f'input moved: {p}'
TR = json.load(open(TREC)); assert TR['ALL_CONTROLS_PASS'] is True and TR['output']['sha256'] == PIN[TNET]
sys.path.insert(0, f'{NS2}/devices')
from news2_diag1_score_ic import ic_series        # noqa: E402

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
NA, NW = len(a), len(F['symbols']); X = F['X78'].astype(np.float64)


def on_axis(E_ts, arr):
    E = E_ts.astype(np.int64); ix = np.searchsorted(E, a); ok = (ix < len(E)) & (E[np.minimum(ix, len(E) - 1)] == a)
    assert np.array_equal(E[ix[ok]], a[ok])
    Y = np.full((NA, NW), np.nan)
    for i in np.flatnonzero(ok):
        mem = m_all[off[i]:off[i + 1]]; Y[i, mem] = arr[ix[i], mem]
    return Y


L = np.load(LAB, allow_pickle=True); Y4 = on_axis(L['E_ts'], L['y4s'])
Tz = np.load(TNET, allow_pickle=True); YT = on_axis(Tz['E_ts'], Tz['T_net'])
last_cov = int(a[np.flatnonzero(np.isfinite(YT).any(1))].max())
SEG = {'pre2026': (T_(2023, 1), T_(2026, 1)), '2026': (T_(2026, 1), last_cov + 1)}


def load(d, want_mode, want_arm):
    r = json.load(open(f'{d}/TRAIN_RECEIPT.json')); sh = r['A1LEAK_shuffle']
    assert sh['mode'] == want_mode and r['arm'] == want_arm and r['random_state'] == 0 and r['label_switch'] == 'y4s'
    z = np.load(f'{d}/KING_OOF.npz', allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a)
    return z['P'].astype(np.float64), {'dir': d, 'oof_sha256': sha(f'{d}/KING_OOF.npz'), 'shuffle_seed': sh['seed'], 'arm': r['arm'],
                                       'trainer_sha256': list(r['source_sha'].values())[0]}


def pooled(P, Y, rows, rng=None):
    ics, _, _ = ic_series(P, Y, rows, rows, rng)
    return float(ics.mean()) if ics.size else float('nan')


def rows_of(P, lo, hi):
    return np.flatnonzero((a >= lo) & (a < hi) & np.isfinite(P).any(1))


rec = {'device': 'dlarch_a1leak_floor.py', 'self_sha256': sha(os.path.abspath(__file__)), 'status': 'DESCRIPTIVE_NO_VERDICT', 'utc': iso(time.time()),
       'inputs': PIN, 'segments': {k: [iso(v[0]), iso(v[1] - 1)] for k, v in SEG.items()}}
P1, i1 = load(A1DIR, 'all', 'A1')
A0 = [load(d, 'all', 'A0') for d in A0DIRS]
assert i1['shuffle_seed'] == SEED and A0[0][1]['shuffle_seed'] == SEED, 'first cells must be the seed-20260927 draws'
ROWS = {s: rows_of(P1, lo, hi) for s, (lo, hi) in SEG.items()}   # the L4c anchors (A1 arm scored rows)

# ---------------- R2 noise-model draws
R2 = {}
for tag, (P, info) in [('A1_seed%d' % i1['shuffle_seed'], (P1, i1))] + [('A0_seed%d' % x[1]['shuffle_seed'], x) for x in A0]:
    row = {'model': info}
    for s, rows in ROWS.items():
        assert np.isfinite(P[rows]).any(1).all(), f'{tag}: not scored on every L4c anchor of {s}'
        c = {'IC_y4s': pooled(P, Y4, rows), 'IC_T_net': pooled(P, YT, rows), 'n_anchors': int(len(rows))}
        if info['shuffle_seed'] == SEED:
            null = np.array([pooled(P, Y4, rows, np.random.default_rng(SEED + b)) for b in range(B_NULL)])
            lo_, hi_ = np.percentile(null, [2.5, 97.5])
            c['null_y4s'] = {'B': B_NULL, 'mean': float(null.mean()), 'sd': float(null.std(ddof=1)), 'p2.5': float(lo_), 'p97.5': float(hi_)}
            c['outside_own_null'] = bool(not (lo_ <= c['IC_y4s'] <= hi_))
        row[s] = c
    R2[tag] = row
a0 = [R2[t] for t in R2 if t.startswith('A0_')]
R2['A0_draws_summary'] = {s: {'n_draws': len(a0), 'IC_y4s': [x[s]['IC_y4s'] for x in a0], 'mean': float(np.mean([x[s]['IC_y4s'] for x in a0])),
                              'sd': float(np.std([x[s]['IC_y4s'] for x in a0], ddof=1)) if len(a0) > 1 else None} for s in SEG}
k1, k0 = 'A1_seed%d' % SEED, 'A0_seed%d' % SEED
R2['question2_A0_same_floor'] = {s: bool(R2[k0][s]['outside_own_null'] and np.sign(R2[k0][s]['IC_y4s']) == np.sign(R2[k1][s]['IC_y4s'])) for s in SEG}
rec['R2_noise_models'] = R2

# ---------------- R1 random directions over within-anchor-ranked features (member rows only; same anchors)
XR = np.full_like(X, np.nan)
for i in range(NA):
    lo, hi = off[i], off[i + 1]
    if hi - lo >= 2:
        XR[lo:hi] = (np.apply_along_axis(rankdata, 0, X[lo:hi]) - 1) / (hi - lo - 1) - .5
W = np.random.default_rng(SEED).standard_normal((NDIR, 78))
R1 = {}
for s, rows in ROWS.items():
    S = np.full((NA, NW), np.nan); ics = []
    featic = []
    for j in range(78):
        for i in rows: S[i, m_all[off[i]:off[i + 1]]] = XR[off[i]:off[i + 1], j]
        featic.append(pooled(S, Y4, rows))
    for w in W:
        for i in rows: S[i, m_all[off[i]:off[i + 1]]] = XR[off[i]:off[i + 1]] @ w
        ics.append(pooled(S, Y4, rows))
    ics = np.array(ics); fi = np.array(featic)
    R1[s] = {'n_dirs': NDIR, 'mean': float(ics.mean()), 'sd': float(ics.std(ddof=1)), 'p2.5': float(np.percentile(ics, 2.5)), 'p97.5': float(np.percentile(ics, 97.5)),
             'share_abs_ge_floor': float((np.abs(ics) >= FLOOR).mean()), 'A1_L4c_IC_y4s': R2[k1][s]['IC_y4s'],
             'A1_L4c_inside_randdir_95': bool(np.percentile(ics, 2.5) <= R2[k1][s]['IC_y4s'] <= np.percentile(ics, 97.5)),
             'per_feature_IC_norm': float(np.sqrt((fi ** 2).sum())), 'per_feature_IC_max_abs': float(np.abs(fi).max()),
             'per_feature_IC': [float(v) for v in fi]}
rec['R1_random_directions'] = R1

# ---------------- R3 side by side for D0
st = json.load(open(STATIC))
rec['R3_D0_context'] = {s: {'D0_y4s_spectrum': st['L3_offset_spectrum_y4s'][s]['D_mean']['0'], 'D0_member_pair_sd': st['L3_offset_spectrum_y4s'][s]['D_sd_over_8_pairs']['0'],
                            'L4c_perm_null_sd_A1': R2[k1][s]['null_y4s']['sd'], 'randdir_sd': R1[s]['sd'], 'A0_noise_draw_sd_n4': R2['A0_draws_summary'][s]['sd']} for s in SEG}

tmp = OUT + '.tmp'
with open(tmp, 'w') as f:
    json.dump(rec, f, indent=1, allow_nan=False)
os.replace(tmp, OUT)
assert json.load(open(OUT))['self_sha256'] == rec['self_sha256']
print('A1LEAK FLOOR out=%s sha256=%s' % (OUT, sha(OUT)), flush=True)
