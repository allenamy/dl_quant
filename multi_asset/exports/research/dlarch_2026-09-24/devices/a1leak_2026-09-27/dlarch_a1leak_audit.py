#!/usr/bin/env python3
"""dlarch_a1leak_audit.py -- A1 (monthly King retrain) leakage audit + model-age decomposition. lead 2026-09-27 05:1xZ.
DESCRIPTIVE ONLY: the A1 IC verdict (d585e1792, FAIL on the 2026 point) is not reopened by anything here. Committed before any
reading it produces exists (the shuffle arms are not even trained when this is committed).

Inputs are the delivered A1 / A0 members of fresh2's MANIFEST_IC.json (e606a778; A1 m0..m7, A0 m0..m7, A0 m0 == in service).

MODE static <out.json>
  L1 FOLD BOUNDARIES, three independent routes, per member (A1 and A0, 8 each), per fold:
     (a) receipt: max_train_label_end + 60 anchors (864000 s) <= score_start; the slack is REPORTED (0 = exactly the embargo);
     (b) recomputed: king_folds.fold_rows on the feature axis with kf_train_king.arm_specs (the trainer's own fold spec, imported,
         sha pinned) -- last train anchor + 4h <= start - 864000, and receipt max_train_label_end <= that recomputed bound;
     (c) ELEMENTWISE per scored anchor: the anchor's model_sha256 names exactly one fold of that member's receipt; the anchor lies
         inside that fold's score window and anchor - max_train_label_end >= 864000. Counted violations, not a boolean.
     The label window is (E, E+48 five-minute bars] = (E, E+4h] (label file meta_json target_window, read and recorded).
  L2 FEATURES / MEMBERS as-of: NOT testable by this device -- A1 and A0 read the SAME X78 and member rows (asserted: the trainer
     code path is shared, and the device checks both arms' receipts name the same feature file sha). Consequence recorded: a
     feature leak cannot create an A1-minus-A0 difference by itself; absolute feature causality rests on upstream receipts
     (label meta feature_window, NC parity gate), cited in the RESULT, not re-proved here.
  L3 OFFSET SPECTRUM, per member, per segment: IC(k) = mean over anchors of Spearman(P at anchor t, y4s at anchor t+k), k in
     [-K, K], labels placed BY TIMESTAMP on the feature axis and restricted to the anchor's members; frozen ic_series (MIN 20).
     Convention (C1.9): k > 0 = prediction leads the label = look-ahead direction.
     - absolute alignment asserted elementwise at k = 0 (label timestamp == prediction timestamp);
     - positive control on A1 m0 pooled: labels planted -2 anchors must move the measured peak by exactly +2 (relative control);
     - A1 and A0 spectra side by side (8-member mean) and the member-PAIRED difference D(k) = IC_A1_mk(k) - IC_A0_mk(k):
       mean and sd over the 8 pairs. Reading rule, fixed here: the A1-specific leak sign is a k > 0 point with mean D(k) > mean
       D(0) (A1's edge larger on a label it should not see than on its own target), listed; peak location of mean D reported.
  L5 MODEL AGE vs YEAR: daily paired dIC (A1 m_k - A0 m_k, mean over pairs defined that day; the verdict's pairing), for the
     verdict target T_net and for y4s. Per day: A0 model age and A1 model age = anchor - fold max_train_label_end (days, mean over
     the day's scored anchors), train-pair ratio A1/A0. Cells year (2023, 2024, 2025, 2026) x A0-age bucket [0,90) [90,180)
     [180,270) [270,400) days: n_days, mean, 95% moving-block bootstrap (block 5 days, B 2000, seed 20260927; < 20 days ->
     mean only), mean ages, mean train ratio; marginals by year and by bucket; a descriptive OLS of daily dIC on year + bucket
     dummies. Reading rule, fixed here: an AGE effect shows as dIC rising across buckets WITHIN a year; a YEAR effect as
     different dIC in the SAME bucket across years. The A0 and A1 IC levels per cell are reported beside it.
MODE shuffle <out.json> <future_dir> <pastlast_dir> <all_dir>   (dirs written by dlarch_a1leak_train.py, rs 0, arm A1, y4s)
  L4a future: its P must be BITWISE equal to A1 m0's P, per fold (differing cells counted per fold) and as whole arrays.
  L4b pastlast (negative control): on every fold it trained, the test cells must DIFFER from A1 m0 (count > 0), else L4a has no
      power and is not read.
  L4c all: the noise-trained model's pooled IC vs the TRUE y4s (and T_net) per segment, and its own permutation null: B = 200
      pooled means of ic_series with the pairing destroyed (ic_series' rng argument, seeds 20260927 + b). Within null iff the
      observed value lies in the null's [2.5, 97.5] percentiles. Power check: A1 m0 read the same way (B = 50) must lie outside.
usage: dlarch_a1leak_audit.py <env-whitelist> static <out.json>
       dlarch_a1leak_audit.py <env-whitelist> shuffle <out.json> <future_dir> <pastlast_dir> <all_dir>
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
MODE, OUT = sys.argv[2], sys.argv[3]
NS2 = '/dev/shm/news2_2026-09-23'; KF = '/workspace/kingfam_2026-09-27'; DL = '/workspace/dlarch_2026-09-24'
FEAT = f'{NS2}/work/NEWS_FEATURES.npz'; MAN = f'{KF}/MANIFEST_IC.json'
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
TNET, TREC = f'{DL}/king_fam_2026-09-27/T_NET.npz', f'{DL}/receipts/T_NET_2026-09-27.json'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       MAN: 'e606a778102f1266b9529ce1603e842c57dfeead83fa7e8c9d6f9383b35d2cde',
       LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       TNET: '929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c',
       f'{NS2}/devices/news2_diag1_score_ic.py': '291d800709650dddac72ba347cd151e71a8b0d22c730b535f3298e85bf6c79fc',
       f'{NS2}/devices/king_folds.py': '4886c278c12b0f5126bb1e8ad6b4789db95e604180a77d0cd02f1e7c612df640',
       f'{KF}/devices/kf_train_king.py': 'bf4594fff16d9d8375f1ebf623ceff27c49fa99c246dcc2e0dc07d6e429d6e95'}
H4, DAY, EMB = 14400, 86400, 60 * 14400
K = 6; PLANT = -2; B_BOOT, SEED = 2000, 20260927; B_NULL, B_NULL_POWER = 200, 50
AGE_EDGES = [0, 90, 180, 270, 400]; YEARS = (2023, 2024, 2025, 2026)
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
TR = json.load(open(TREC))
assert TR['device'] == 'dlarch_t_net.py' and TR['ALL_CONTROLS_PASS'] is True and TR['output']['sha256'] == PIN[TNET]
sys.path.insert(0, f'{NS2}/devices'); sys.path.insert(0, f'{KF}/devices')
from news2_diag1_score_ic import ic_series        # noqa: E402
from king_folds import fold_rows                   # noqa: E402
import kf_train_king as KFT                        # noqa: E402  (defs only at import; its main() is not run)

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
NA, NW = len(a), len(F['symbols'])
assert np.all(np.diff(a) == H4), 'feature axis must be the contiguous 4h grid (a shift by k anchors = k x 4h)'


def on_axis(E_ts, arr, name):
    """label array placed on the feature axis BY TIMESTAMP, restricted to each anchor's members; alignment asserted"""
    E = E_ts.astype(np.int64); ix = np.searchsorted(E, a); ok = (ix < len(E)) & (E[np.minimum(ix, len(E) - 1)] == a)
    assert np.array_equal(E[ix[ok]], a[ok]), f'{name}: label timestamp != anchor timestamp'
    Y = np.full((NA, NW), np.nan)
    for i in np.flatnonzero(ok):
        mem = m_all[off[i]:off[i + 1]]; Y[i, mem] = arr[ix[i], mem]
    return Y, {'anchors_with_label': int(ok.sum()), 'timestamp_mismatches_at_k0': 0}


L = np.load(LAB, allow_pickle=True); assert [str(s) for s in L['symbols']] == [str(s) for s in F['symbols']]
LMETA = json.loads(str(L['meta_json']))
Y4, AL4 = on_axis(L['E_ts'], L['y4s'], 'y4s')
Tz = np.load(TNET, allow_pickle=True); assert [str(s) for s in Tz['symbols']] == [str(s) for s in F['symbols']]
YT, ALT = on_axis(Tz['E_ts'], Tz['T_net'], 'T_net')
last_cov = int(a[np.flatnonzero(np.isfinite(YT).any(1))].max())
SEG = {'pre2026': (T_(2023, 1), T_(2026, 1)), '2026': (T_(2026, 1), last_cov + 1)}   # the verdict's segments

man = json.load(open(MAN))
MEM = {arm: [m['path'] for m in man['arms'][arm]] for arm in ('A1', 'A0')}
assert all(len(v) == 8 for v in MEM.values())
for arm in MEM:
    for k, p in enumerate(MEM[arm]):
        assert sha(p) == man['arms'][arm][k]['sha256'], f'{p} moved since the manifest'


def load(p):
    z = np.load(p, allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a)
    return z['P'].astype(np.float64), z['model_sha256']


def receipt(p):
    return json.load(open(os.path.join(os.path.dirname(p), 'TRAIN_RECEIPT.json')))


rec = {'device': 'dlarch_a1leak_audit.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': MODE, 'status': 'DESCRIPTIVE_NO_VERDICT',
       'utc': iso(time.time()), 'inputs': PIN, 'label_meta': {k: LMETA.get(k) for k in ('feature_window', 'target_window', 'membership')},
       'segments': {k: [iso(v[0]), iso(v[1] - 1)] for k, v in SEG.items()}, 'alignment_k0': {'y4s': AL4, 'T_net': ALT}}


def pooled_ic(P, Y, rows, shift=0, rng=None):
    rows = np.asarray(rows); j = rows + shift; keep = (j >= 0) & (j < NA)
    ics, _, _ = ic_series(P, Y, rows[keep], j[keep], rng)
    return float(ics.mean()) if ics.size else float('nan')


def seg_rows(P, lo, hi):
    r = np.flatnonzero((a >= lo) & (a < hi) & np.isfinite(P).any(1))
    return r[(r - K + PLANT >= 0) & (r + K - PLANT < NA)]      # the same rows for every k, planted or not


def spectrum(P, Y, rows, plant=0):
    return {k: pooled_ic(P, Y, rows, k + plant) for k in range(-K, K + 1)}


def peak(sp):
    v = {k: x for k, x in sp.items() if np.isfinite(x)}
    return max(v, key=v.get) if v else None


def mbb_ci(x, block):
    rng = np.random.default_rng(SEED); n = len(x); nb = int(np.ceil(n / block)); means = np.empty(B_BOOT)
    for b in range(B_BOOT):
        st = rng.integers(0, max(1, n - block + 1), nb)
        idx = np.concatenate([np.arange(s, min(s + block, n)) for s in st])[:n]; means[b] = x[idx].mean()
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def fold_of_anchor(P, msha, r):
    """per scored anchor -> fold dict of the member's receipt (by model sha); violations counted"""
    folds = {f['model_sha256']: f for f in r['folds']}
    assert len(folds) == len(r['folds']), 'model shas not unique across folds'
    scored = np.flatnonzero(np.isfinite(P).any(1)); out = {}; bad = {'unknown_sha': 0, 'outside_window': 0, 'lag_lt_embargo': 0, 'sha_without_scores': 0}
    bad['sha_without_scores'] = int(sum(1 for i in range(NA) if str(msha[i]) and not np.isfinite(P[i]).any()))
    for i in scored:
        f = folds.get(str(msha[i]))
        if f is None:
            bad['unknown_sha'] += 1; continue
        if not (f['score_start'] <= a[i] <= f['score_end']): bad['outside_window'] += 1
        if a[i] - f['max_train_label_end'] < EMB: bad['lag_lt_embargo'] += 1
        out[int(i)] = f
    return out, bad


if MODE == 'static':
    # ---------------- L1
    L1 = {}
    for arm in ('A1', 'A0'):
        specs = KFT.arm_specs(arm, a)
        for k, p in enumerate(MEM[arm]):
            r = receipt(p); P, msha = load(p)
            assert r['arm'] == arm and r['random_state'] == k and r['label_switch'] == 'y4s'
            spec = {t: (s, e) for t, s, e in specs}; rows = []
            for f in r['folds']:
                s, e = spec[f['fold']]; tr, te = fold_rows(a, s, e, 60)
                bound = int(a[tr].max() + H4) if len(tr) else None
                rows.append({'fold': f['fold'], 'a_receipt_slack_s': int(f['score_start'] - EMB - f['max_train_label_end']),
                             'a_pass': f['max_train_label_end'] + EMB <= f['score_start'],
                             'b_recomputed_bound_ok': bound is not None and bound <= s - EMB and f['max_train_label_end'] <= bound and f['score_start'] == int(a[te[0]]),
                             'lag_days': (f['score_start'] - f['max_train_label_end']) / DAY, 'train_pairs': f['train_pairs']})
            _, bad = fold_of_anchor(P, msha, r)
            L1[f'{arm}_m{k}'] = {'n_folds': len(rows), 'all_a': all(x['a_pass'] for x in rows), 'all_b': all(x['b_recomputed_bound_ok'] for x in rows),
                                 'min_slack_s': min(x['a_receipt_slack_s'] for x in rows), 'max_slack_s': max(x['a_receipt_slack_s'] for x in rows),
                                 'c_elementwise_violations': bad, 'features_sha_in_receipt': [v for kk, v in r['inputs'].items() if kk.endswith('NEWS_FEATURES.npz')],
                                 'folds': rows if k == 0 else 'same checks; per-fold rows kept for m0 only'}
    fsh = {v['features_sha_in_receipt'][0] for v in L1.values()}
    rec['L1_fold_boundaries'] = L1
    rec['L1_ALL_PASS'] = all(v['all_a'] and v['all_b'] and not any(v['c_elementwise_violations'].values()) for v in L1.values())
    rec['L2_shared_features'] = {'feature_shas_across_16_members': sorted(fsh), 'one_file': len(fsh) == 1 and PIN[FEAT] in fsh,
                                 'limit': 'shared features cannot create an A1-minus-A0 difference by themselves; absolute feature causality is not re-proved here'}
    # ---------------- L3
    Ps = {arm: [load(p)[0] for p in MEM[arm]] for arm in MEM}
    L3 = {}
    for s, (lo, hi) in SEG.items():
        rows = seg_rows(Ps['A1'][0], lo, hi)
        spA1 = [spectrum(P, Y4, rows) for P in Ps['A1']]; spA0 = [spectrum(P, Y4, rows) for P in Ps['A0']]
        ks = list(range(-K, K + 1))
        D = np.array([[spA1[m][k] - spA0[m][k] for k in ks] for m in range(8)])
        mA1 = {k: float(np.mean([x[k] for x in spA1])) for k in ks}; mA0 = {k: float(np.mean([x[k] for x in spA0])) for k in ks}
        mD = {k: float(D[:, i].mean()) for i, k in enumerate(ks)}; sdD = {k: float(D[:, i].std(ddof=1)) for i, k in enumerate(ks)}
        L3[s] = {'n_anchors': int(len(rows)), 'A1_mean': mA1, 'A0_mean': mA0, 'A1_peak_k': peak(mA1), 'A0_peak_k': peak(mA0),
                 'D_mean': mD, 'D_sd_over_8_pairs': sdD, 'D_peak_k': peak(mD),
                 'kpos_with_D_above_D0': [k for k in ks if k > 0 and mD[k] > mD[0]],
                 'per_member_A1': spA1, 'per_member_A0': spA0}
        base = spectrum(Ps['A1'][0], Y4, rows); planted = spectrum(Ps['A1'][0], Y4, rows, PLANT)
        L3[s]['positive_control_A1m0'] = {'base_peak_k': peak(base), 'planted_peak_k': peak(planted), 'plant_labels_by': PLANT,
                                          'expected_move': -PLANT, 'PASS': (peak(planted) - peak(base)) == -PLANT if None not in (peak(base), peak(planted)) else None}
    rec['L3_offset_spectrum_y4s'] = L3
    # ---------------- L5
    def daily(P, Y):
        rows = np.flatnonzero(np.isfinite(Y).any(1) & np.isfinite(P).any(1)); dd = (a[rows] // DAY) * DAY; out = {}
        for u in np.unique(dd):
            ics, _, _ = ic_series(P, Y, rows[dd == u], rows[dd == u])
            if ics.size: out[int(u)] = float(ics.mean())
        return out
    fa = {arm: fold_of_anchor(*load(MEM[arm][0]), receipt(MEM[arm][0]))[0] for arm in MEM}   # folds identical across members (asserted below)
    for arm in MEM:
        for p in MEM[arm][1:]:
            assert [(f['fold'], f['score_start'], f['max_train_label_end']) for f in receipt(p)['folds']] == \
                   [(f['fold'], f['score_start'], f['max_train_label_end']) for f in receipt(MEM[arm][0])['folds']]
    dayinfo = {}
    for i, f0 in fa['A0'].items():
        f1 = fa['A1'].get(i)
        if f1 is None: continue
        u = int((a[i] // DAY) * DAY); d = dayinfo.setdefault(u, [])
        d.append(((a[i] - f0['max_train_label_end']) / DAY, (a[i] - f1['max_train_label_end']) / DAY, f1['train_pairs'] / f0['train_pairs']))
    dayinfo = {u: tuple(np.mean(v, axis=0)) for u, v in dayinfo.items()}
    L5 = {}
    for lbl, Y in (('T_net', YT), ('y4s', Y4)):
        ic = {arm: [daily(P, Y) for P in Ps[arm]] for arm in Ps}
        days = sorted(set().union(*[set(d) for d in ic['A1']]) & set(dayinfo))
        dIC, lvl1, lvl0 = {}, {}, {}
        for u in days:
            pr = [ic['A1'][m][u] - ic['A0'][m][u] for m in range(8) if u in ic['A1'][m] and u in ic['A0'][m]]
            if pr:
                dIC[u] = float(np.mean(pr)); lvl1[u] = float(np.mean([ic['A1'][m][u] for m in range(8) if u in ic['A1'][m]]))
                lvl0[u] = float(np.mean([ic['A0'][m][u] for m in range(8) if u in ic['A0'][m]]))
        yr = lambda u: time.gmtime(u).tm_year
        bk = lambda u: int(np.searchsorted(AGE_EDGES, dayinfo[u][0], side='right') - 1)
        use = [u for u in dIC if yr(u) in YEARS and 0 <= bk(u) < len(AGE_EDGES) - 1 and u < SEG['2026'][1]]

        def cell(us):
            x = np.array([dIC[u] for u in us])
            c = {'n_days': len(us)}
            if len(us) == 0: return c
            c.update({'dIC_mean': float(x.mean()), 'A1_IC_mean': float(np.mean([lvl1[u] for u in us])), 'A0_IC_mean': float(np.mean([lvl0[u] for u in us])),
                      'A0_age_days_mean': float(np.mean([dayinfo[u][0] for u in us])), 'A1_age_days_mean': float(np.mean([dayinfo[u][1] for u in us])),
                      'train_pairs_ratio_A1_over_A0_mean': float(np.mean([dayinfo[u][2] for u in us]))})
            c['dIC_ci95_block5'] = mbb_ci(x, 5) if len(us) >= 20 else 'UNDEFINED(<20 days)'
            return c
        names = [f'[{AGE_EDGES[b]},{AGE_EDGES[b + 1]})' for b in range(len(AGE_EDGES) - 1)]
        grid = {str(y): {names[b]: cell(sorted(u for u in use if yr(u) == y and bk(u) == b)) for b in range(len(names))} for y in YEARS}
        by_year = {str(y): cell(sorted(u for u in use if yr(u) == y)) for y in YEARS}
        by_bucket = {sg: {names[b]: cell(sorted(u for u in use if bk(u) == b and (yr(u) < 2026) == (sg == 'pre2026'))) for b in range(len(names))}
                     for sg in ('pre2026', '2026')}
        cols = [f'y{y}' for y in YEARS[1:]] + [f'b{names[b]}' for b in range(1, len(names))]
        X = np.array([[1.0] + [float(yr(u) == y) for y in YEARS[1:]] + [float(bk(u) == b) for b in range(1, len(names))] for u in use])
        yv = np.array([dIC[u] for u in use]); coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
        L5[lbl] = {'grid_year_x_A0age': grid, 'by_year': by_year, 'by_A0age_bucket': by_bucket,
                   'ols_descriptive': {'baseline': f'year {YEARS[0]}, bucket {names[0]}', 'intercept': float(coef[0]), **{c: float(v) for c, v in zip(cols, coef[1:])},
                                       'n_days': len(use), 'note': 'descriptive additive fit; no SE (days are autocorrelated); read the grid'}}
    rec['L5_model_age'] = L5

elif MODE == 'shuffle':
    FUT, PAS, ALL = sys.argv[4:7]
    P0, _ = load(MEM['A1'][0]); r0 = receipt(MEM['A1'][0]); win = {f['fold']: (f['score_start'], f['score_end']) for f in r0['folds']}
    sub = {}
    for tag, d, mode in (('L4a_future', FUT, 'future'), ('L4b_pastlast', PAS, 'pastlast')):
        z = np.load(f'{d}/KING_OOF.npz', allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a)
        P = z['P'].astype(np.float64); r = json.load(open(f'{d}/TRAIN_RECEIPT.json')); sh = r['A1LEAK_shuffle']
        assert sh['mode'] == mode and r['arm'] == 'A1' and r['random_state'] == 0 and r['label_switch'] == 'y4s'
        per = {}
        for f in r['folds']:
            lo, hi = win[f['fold']]; rows = np.flatnonzero((a >= lo) & (a <= hi))
            A_, B_ = P[rows], P0[rows]
            per[f['fold']] = {'differing_cells': int((~((A_ == B_) | (np.isnan(A_) & np.isnan(B_)))).sum()), 'anchors_permuted': sh['per_fold'][f['fold']]['anchors_permuted'],
                              'bitwise_equal': A_.tobytes() == B_.tobytes()}
        sub[tag] = {'dir': d, 'oof_sha256': sha(f'{d}/KING_OOF.npz'), 'trainer_sha256': list(r['source_sha'].values())[0], 'n_folds': len(per), 'per_fold': per}
    sub['L4a_future']['whole_P_bitwise_equal_to_A1_m0'] = np.load(f'{FUT}/KING_OOF.npz')['P'].tobytes() == np.load(MEM['A1'][0])['P'].tobytes()
    sub['L4a_future']['ALL_FOLDS_BITWISE'] = all(v['bitwise_equal'] for v in sub['L4a_future']['per_fold'].values())
    sub['L4a_future']['ALL_FOLDS_PERMUTED_SOMETHING'] = all(v['anchors_permuted'] > 0 for v in sub['L4a_future']['per_fold'].values())
    sub['L4b_pastlast']['ALL_FOLDS_DIFFER'] = all(v['differing_cells'] > 0 for v in sub['L4b_pastlast']['per_fold'].values())
    sub['L4a_readable'] = sub['L4b_pastlast']['ALL_FOLDS_DIFFER']
    z = np.load(f'{ALL}/KING_OOF.npz', allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a)
    Pn = z['P'].astype(np.float64); rn = json.load(open(f'{ALL}/TRAIN_RECEIPT.json')); assert rn['A1LEAK_shuffle']['mode'] == 'all'
    L4c = {'dir': ALL, 'oof_sha256': sha(f'{ALL}/KING_OOF.npz')}
    for s, (lo, hi) in SEG.items():
        rows = np.flatnonzero((a >= lo) & (a < hi) & np.isfinite(Pn).any(1))
        row = {'n_anchors': int(len(rows))}
        for lbl, Y in (('y4s', Y4), ('T_net', YT)):
            obs = pooled_ic(Pn, Y, rows); row[f'shuffled_IC_{lbl}'] = obs
        null = np.array([pooled_ic(Pn, Y4, rows, 0, np.random.default_rng(SEED + b)) for b in range(B_NULL)])
        lo_, hi_ = np.percentile(null, [2.5, 97.5])
        row['null_y4s'] = {'B': B_NULL, 'mean': float(null.mean()), 'p2.5': float(lo_), 'p97.5': float(hi_)}
        row['shuffled_within_own_null'] = bool(lo_ <= row['shuffled_IC_y4s'] <= hi_)
        obs1 = pooled_ic(P0, Y4, rows); n1 = np.array([pooled_ic(P0, Y4, rows, 0, np.random.default_rng(SEED + b)) for b in range(B_NULL_POWER)])
        row['power_A1m0'] = {'IC_y4s': obs1, 'null_p2.5': float(np.percentile(n1, 2.5)), 'null_p97.5': float(np.percentile(n1, 97.5)),
                             'outside_null': bool(not (np.percentile(n1, 2.5) <= obs1 <= np.percentile(n1, 97.5)))}
        L4c[s] = row
    sub['L4c_all'] = L4c
    rec['L4_shuffle'] = sub
else:
    raise SystemExit(f'unknown mode {MODE}')

def clean(o):   # NaN -> None (named in the receipt as null; allow_nan=False then guards everything else)
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o


rec = clean(rec)
tmp = OUT + '.tmp'
with open(tmp, 'w') as f:
    json.dump(rec, f, indent=1, allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
os.replace(tmp, OUT)
back = json.load(open(OUT)); assert back['self_sha256'] == rec['self_sha256'] and back['mode'] == MODE
print('A1LEAK %s out=%s sha256=%s' % (MODE.upper(), OUT, sha(OUT)), flush=True)
