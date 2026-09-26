#!/usr/bin/env python3
"""dlarch_d2_pregates.py -- D2 (double-orthogonal residual) pre-gates, frozen order of
DECISION_RULE_D2_D4_pregates_2026-09-26.md (lead, 8bf66bdc5): PG-D2-3 -> PG-D2-0 -> PG-D2-1; PG-D2-2 is
descriptive only and is NOT computed by this device (named; a separate descriptive device, if lead wants it).
Zero GPU. Written and committed BEFORE any D2 reading exists.

LABEL (prereg §1): per anchor i, over names that are members AND have finite y4s, KZ and ZFD (>= MIN_GOOD):
  y4s = c + bK * KZ + bF * ZFD + e   (float64 lstsq)  ->  t2res = e, in RETURN UNITS (lead's T2 ruling (a)).
  KZ / ZFD are legs.npz at anchor i (causal legs, production caliber).
PG-D2-0: max over anchors of |Pearson(e, KZ)| and |Pearson(e, ZFD)| on the regression names, in float64,
  must be <= 1e-10; RED control: regress on [1, KZ] only => max |Pearson(e, ZFD)| must be > 1e-6.
PG-D2-3 (first), a KNOWN-ANSWER target: t* = kappa * s + n, where s is a synthetic N(0,1) column appended as
  feature 172 (seed 20260926) and n is t2res PERMUTED WITHIN EACH ANCHOR (seed 20260927) -- the real
  residual's marginal with its predictability destroyed -- so the ONLY learnable signal is s. kappa is
  bisected so that the mean per-anchor Spearman IC(s, t*) = 0.010 (the lead's number). The same ridge / LGBM
  walk-forward as PG-D2-1 is then run on (X + s, t*). PASS iff, for at least one model, the day-block 95%
  lower bound of IC(pred, t*) is > 0 in BOTH segments.
PG-D2-1: ridge and LGBM (dlarch_pregates.py constants, imported, sha-pinned) walk-forward on the 171 F10
  columns, year folds 2023 / 2024 / 2025 / 2026 via king_folds.fold_rows (embargo 60, train label end asserted
  <= test start - embargo); IC of predictions vs t2res through the frozen news2_diag1_score_ic.ic_series,
  CALLED ONE UTC DAY AT A TIME (dlarch_t2_pregate_2026.py's alignment rule), interval = frozen judge
  news_stats.boot with its BLOCK_MAIN (30), BLOCK_SENS (5) reported beside it. Segments: pre-2026 = test
  years 2023-2025; 2026 = test year 2026. sigma_yhat / sigma_y = std(pred) / std(t2res) on the segment's
  test pairs. Gate (transcribed): at least one model with 95% lower bound > 0 in BOTH segments AND
  sigma_yhat / sigma_y >= 0.02 in both.
Caliber: y4s, SCORE layer (NOT the v4 RAW accounting caliber); never quote an IC as a return.

usage: dlarch_d2_pregates.py <env-whitelist> <out.json>
"""
import calendar, gc, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]
W = '/dev/shm/news2_2026-09-23'
BASE = '/workspace/dlarch_2026-09-24'
FEAT, LEGS = f'{W}/work/NEWS_FEATURES.npz', f'{W}/work/legs.npz'
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       LEGS: '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',
       LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       f'{BASE}/dlarch_pregates.py': 'b1187d2fe6c0103f00d9bfe14b56dc05a6c342f384a9636afa8a02e107acd661',
       f'{W}/devices/king_folds.py': '4886c278c12b0f5126bb1e8ad6b4789db95e604180a77d0cd02f1e7c612df640',
       f'{W}/devices/news2_diag1_score_ic.py': '291d800709650dddac72ba347cd151e71a8b0d22c730b535f3298e85bf6c79fc'}
TEST_YEARS = (2023, 2024, 2025, 2026)
Y2026 = calendar.timegm((2026, 1, 1, 0, 0, 0))
IC_PLANT = 0.010
rec = {'device': 'dlarch_d2_pregates.py', 'utc_start': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'criterion': 'DECISION_RULE_D2_D4_pregates_2026-09-26.md (8bf66bdc5), D2 section, transcribed',
       'PG_D2_2': 'NOT COMPUTED here (descriptive-only in the rule); named, not silently skipped'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def log(*a):
    print(time.strftime('%H:%M:%S', time.gmtime()), *a, flush=True)


def write(stop=None):
    rec['self_sha256'] = sha(os.path.abspath(__file__))
    rec['utc_end'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if stop:
        rec['STOPPED_AT'] = stop
    with open(OUT, 'w') as f:
        json.dump(rec, f, indent=1, sort_keys=True, default=float)
    with open(OUT) as f:
        assert json.load(f)['self_sha256'] == rec['self_sha256']
    print('D2_PREGATES %s out=%s sha256=%s' % (('STOPPED ' + stop) if stop else 'DONE', OUT, sha(OUT)), flush=True)


for p, want in PIN.items():
    assert sha(p) == want, f'input moved: {p}'
rec['inputs'] = PIN
sys.path.insert(0, BASE); sys.path.insert(0, f'{W}/devices'); sys.path.insert(0, f'{W}/engine')
import dlarch_pregates as PG                                          # noqa: E402  constants only; main() not run
from king_folds import fold_rows                                      # noqa: E402
from news2_diag1_score_ic import ic_series                            # noqa: E402
import news_stats as NS                                               # noqa: E402
import bt_tables as BT, bt_driver_lib as DL                            # noqa: E402
NS.BT, NS.DL = BT, DL
from scipy.stats import spearmanr                                     # noqa: E402
from sklearn.linear_model import Ridge                                # noqa: E402
import lightgbm as lgb                                                # noqa: E402
rec['constants'] = {'RIDGE_ALPHA': PG.RIDGE_ALPHA, 'LGB_PARAMS': PG.LGB_PARAMS, 'EMBARGO': PG.EMBARGO,
                    'MIN_GOOD': PG.MIN_GOOD, 'BLOCK_MAIN': NS.BLOCK_MAIN, 'BLOCK_SENS': NS.BLOCK_SENS}

F = np.load(FEAT); Lg = np.load(LEGS); lab = np.load(LAB, allow_pickle=True)
a = F['anchors'].astype(np.int64); NA, NW = len(a), len(F['symbols'])
assert np.array_equal(Lg['E_ts'].astype(np.int64), a) and np.array_equal(lab['symbols'], F['symbols'])
off = F['off'].astype(np.int64); ps = F['m'].astype(np.int64); pa = np.repeat(np.arange(NA), np.diff(off)); NP = len(pa)
ya = lab['E_ts'].astype(np.int64); Y = lab['y4s']
iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
ylong = np.full(NP, np.nan); g = lab_ok[pa]; ylong[g] = Y[iy[pa[g]], ps[g]]
KZl = Lg['KZ'][pa, ps].astype(np.float64); ZFl = Lg['ZFD'][pa, ps].astype(np.float64)


def residualise(use_fund=True):
    res = np.full(NP, np.nan); stats = {'r2': [], 'bK': [], 'bF': [], 'var_ratio': []}; maxc = [0.0, 0.0]
    for i in range(NA):
        sl = slice(off[i], off[i + 1]); t, k, f = ylong[sl], KZl[sl], ZFl[sl]
        ok = np.isfinite(t) & np.isfinite(k) & np.isfinite(f)
        if ok.sum() < PG.MIN_GOOD:
            continue
        A_ = np.column_stack([np.ones(int(ok.sum())), k[ok]] + ([f[ok]] if use_fund else []))
        sol = np.linalg.lstsq(A_, t[ok], rcond=None)[0]; e = t[ok] - A_ @ sol
        res[np.flatnonzero(ok) + off[i]] = e
        for j, v in enumerate((k[ok], f[ok])):
            if np.std(v) > 0 and np.std(e) > 0:
                maxc[j] = max(maxc[j], abs(float(np.corrcoef(e, v)[0, 1])))
        vt = float(np.var(t[ok]))
        if vt > 0:
            stats['r2'].append(1 - float(np.var(e)) / vt); stats['var_ratio'].append(float(np.var(e)) / vt)
        stats['bK'].append(float(sol[1])); stats['bF'].append(float(sol[2]) if use_fund else np.nan)
    return res, stats, maxc


t2res, st, maxc = residualise(True)
_, _, maxc_red = residualise(False)
summ = lambda v: {'n': len(v), 'mean': float(np.nanmean(v)), 'median': float(np.nanmedian(v)), 'p10': float(np.nanpercentile(v, 10)), 'p90': float(np.nanpercentile(v, 90))}
rec['label'] = {'finite_pairs': int(np.isfinite(t2res).sum()), 'R2_per_anchor': summ(st['r2']), 'bK': summ(st['bK']),
                'bF': summ(st['bF']), 'residual_to_label_variance_ratio': summ(st['var_ratio'])}
X = np.concatenate([F['X82'], F['X89']], 1).astype(np.float32); assert X.shape == (NP, 171) and np.isfinite(X).all()
del F; gc.collect()

# ── fold runner + IC readout (shared by PG-D2-3 and PG-D2-1) ────────────────────────────────────
def walk(XA, target):
    preds = {'ridge': np.full((NA, NW), np.nan, np.float32), 'lgbm': np.full((NA, NW), np.nan, np.float32)}; folds = {}
    for yr in TEST_YEARS:
        s0, s1 = calendar.timegm((yr, 1, 1, 0, 0, 0)), calendar.timegm((yr + 1, 1, 1, 0, 0, 0))
        tr_a, te_a = fold_rows(a, s0, s1, PG.EMBARGO)
        tr = np.isin(pa, tr_a) & np.isfinite(target); te = np.isin(pa, te_a)
        assert a[pa[tr]].max() + 14400 <= a[te_a[0]] - PG.EMBARGO * 14400, 'out-of-fold leak'
        Xtr, ytr, Xte = XA[tr], target[tr], XA[te]
        mu = Xtr.mean(0, dtype=np.float64); sd = Xtr.std(0, dtype=np.float64) + 1e-9
        R = Ridge(alpha=PG.RIDGE_ALPHA).fit(((Xtr - mu) / sd).astype(np.float32), ytr)
        preds['ridge'][pa[te], ps[te]] = R.predict(((Xte - mu) / sd).astype(np.float32))
        G = lgb.LGBMRegressor(**PG.LGB_PARAMS).fit(Xtr, ytr)
        preds['lgbm'][pa[te], ps[te]] = G.predict(Xte)
        folds[str(yr)] = {'train_pairs': int(tr.sum()), 'test_pairs': int(te.sum()),
                          'train_label_end': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(a[pa[tr]].max() + 14400)))}
        log('  fold', yr, folds[str(yr)])
        del Xtr, Xte, R, G; gc.collect()
    return preds, folds


def readout(preds, target):
    Tm = np.full((NA, NW), np.nan, np.float32); Tm[pa, ps] = target
    rows = np.flatnonzero(np.isfinite(Tm).any(1) & (a >= calendar.timegm((TEST_YEARS[0], 1, 1, 0, 0, 0))))
    segs = {'pre2026': rows[a[rows] < Y2026], '2026': rows[a[rows] >= Y2026]}
    out = {}
    for mdl, P in preds.items():
        out[mdl] = {}
        for s, rr in segs.items():
            days = np.unique((a[rr] // 86400) * 86400); per_day = []
            for u in days:
                r = rr[(a[rr] // 86400) * 86400 == u]
                icd, _, _ = ic_series(P, Tm, r, r)
                if len(icd):
                    per_day.append(float(np.mean(icd)))
            per_day = np.asarray(per_day)
            b, bs = NS.boot(per_day, NS.BLOCK_MAIN), NS.boot(per_day, NS.BLOCK_SENS)
            m = np.isfinite(P[rr]) & np.isfinite(Tm[rr])
            out[mdl][s] = {'ic_mean_of_days': float(per_day.mean()), 'n_days': int(len(per_day)),
                           'ci95_lower': b['ci95_bps'][0] / 1e4, 'ci95_upper': b['ci95_bps'][1] / 1e4,
                           'ci95_lower_sens_block': bs['ci95_bps'][0] / 1e4,
                           'sigma_yhat_over_sigma_y': float(np.std(P[rr][m]) / np.std(Tm[rr][m]))}
    return out


# ── PG-D2-3 power (FIRST): known-answer target, the only learnable signal is s ─────────────────
rng = np.random.default_rng(20260926); s_col = rng.standard_normal(NP).astype(np.float32)
noise = t2res.copy(); rng2 = np.random.default_rng(20260927)
for i in range(NA):
    sl = slice(off[i], off[i + 1]); v = noise[sl]; ok = np.isfinite(v)
    if ok.sum() > 1:
        idx = np.flatnonzero(ok); v[idx] = v[rng2.permutation(idx)]
ok_anchor = [i for i in range(NA) if np.isfinite(noise[off[i]:off[i + 1]]).sum() >= 20]


def mean_ic(kappa):
    ics = []
    for i in ok_anchor[::5]:                               # every 5th anchor: calibration only, named
        sl = slice(off[i], off[i + 1]); t = kappa * s_col[sl] + noise[sl]; ok = np.isfinite(t)
        ics.append(spearmanr(s_col[sl][ok], t[ok]).statistic)
    return float(np.mean(ics))


lo_k, hi_k = 0.0, float(np.nanstd(noise)) * 0.1
while mean_ic(hi_k) < IC_PLANT:
    hi_k *= 2
for _ in range(40):
    mid = (lo_k + hi_k) / 2
    lo_k, hi_k = (mid, hi_k) if mean_ic(mid) < IC_PLANT else (lo_k, mid)
kappa = hi_k; tstar = kappa * s_col + noise
log('PG-D2-3 kappa', kappa, 'calibrated IC', mean_ic(kappa))
pw_preds, pw_folds = walk(np.concatenate([X, s_col[:, None]], 1), tstar)
pw = readout(pw_preds, tstar)
det = {m: all(pw[m][s]['ci95_lower'] > 0 for s in ('pre2026', '2026')) for m in pw}
rec['PG_D2_3_power'] = {'kappa': kappa, 'calibrated_IC_every_5th_anchor': mean_ic(kappa), 'target_IC': IC_PLANT,
                        'folds': pw_folds, 'readout': pw, 'detected_both_segments': det,
                        'gate': 'at least one model: 95% lower bound > 0 in BOTH segments', 'PASS': any(det.values())}
del pw_preds; gc.collect()
if not rec['PG_D2_3_power']['PASS']:
    write('PG_D2_3_NO_RESOLUTION'); sys.exit(0)

# ── PG-D2-0 orthogonality ───────────────────────────────────────────────────────────────────────
rec['PG_D2_0_orthogonality'] = {'max_abs_corr_res_KZ': maxc[0], 'max_abs_corr_res_ZFD': maxc[1],
                                'red_max_abs_corr_res_ZFD_when_ZFD_not_regressed': maxc_red[1],
                                'gate': 'both max |corr| <= 1e-10; red > 1e-6',
                                'PASS': bool(maxc[0] <= 1e-10 and maxc[1] <= 1e-10 and maxc_red[1] > 1e-6)}
if not rec['PG_D2_0_orthogonality']['PASS']:
    write('PG_D2_0_ORTHOGONALITY_FAILED'); sys.exit(0)

# ── PG-D2-1 learnability ────────────────────────────────────────────────────────────────────────
preds, folds = walk(X, t2res)
ro = readout(preds, t2res)
ok_m = {m: all(ro[m][s]['ci95_lower'] > 0 and ro[m][s]['sigma_yhat_over_sigma_y'] >= 0.02 for s in ('pre2026', '2026')) for m in ro}
rec['PG_D2_1_learnability'] = {'folds': folds, 'readout': ro, 'per_model_pass': ok_m,
                               'gate': 'at least one model: 95% lower bound > 0 in BOTH segments and sigma ratio >= 0.02 in both',
                               'PASS': any(ok_m.values())}
rec['PREGATES_PASS'] = bool(rec['PG_D2_3_power']['PASS'] and rec['PG_D2_0_orthogonality']['PASS'] and rec['PG_D2_1_learnability']['PASS'])
rec['GPU_arm_release'] = 'NOT released by these pre-gates alone: additionally requires alloc A3 non-inferiority PASS or a lead ruling'
write()
