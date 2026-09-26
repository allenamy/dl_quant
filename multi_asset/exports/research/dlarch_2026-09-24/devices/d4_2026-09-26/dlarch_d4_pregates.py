#!/usr/bin/env python3
"""dlarch_d4_pregates.py -- D4 (funding-leg failure gate) pre-gates, in the frozen order of
DECISION_RULE_D2_D4_pregates_2026-09-26.md (lead, 8bf66bdc5): PG-D4-3 -> PG-D4-0 -> PG-D4-1 -> PG-D4-2.
Zero GPU. Written and committed BEFORE any T-b / feature / AUC reading exists.

TARGET T-b (prereg §1), per formation anchor A (legs.npz row k, LR[k] = return over (A, A+4h]):
  price(A) = the funding leg's own return, RECONSTRUCTED here from its weights so that the SAME weights can
             carry the funding: members pm = NEWS_FEATURES m at A; z = ZFD[k, pm] (nan -> 0); names whose
             4h return y4v is not finite get 0; de-mean over the finite ones; w = zz / sum|zz|;
             y4v = float32 sum of the 48 R_crypto rows (A, A+4h], NaN when < 46 finite  (nc_legs.py L44-L55)
  carry(A) = sum_j w_j * sum{rate of symbol j settled at ft in (A, A+4h]} * 1e4 bps   (a long pays +rate)
  T-b(A)   = price(A) - carry(A)
  IDENTITY CONTROL (named deviation from the draft's "bitwise"): ZFD is stored float32 while nc_legs used the
  float64 z, so price cannot be bit-identical to LR; the control is max|price - LR[:,2]| <= 1e-3 bps over
  every finite row, and the device refuses to continue otherwise. The funding half gets a known-answer
  synthetic case and a red control (shift every settlement by +4 h => T-b must change).
  Window convention (named): a settlement exactly at A+4h belongs to the position formed at A (the live
  executor rebalances 24 min after the anchor); one exactly at A does not.
  CALIBER: the GATE uses the PRODUCER caliber = old P2 ledger_full.npz (second key; bea6f575). The D10
  caliber = ledger_full_ms.npz (millisecond key, keeps the 18 same-second settlements; e179071d) is
  computed and reported beside it and never gates (lead 23:2xZ). Both ledgers end 2026-09-01T02Z, so T-b
  and everything built on it stops at 2026-08-31 (named; the 2026 segment here is the truncated one).
  Daily T-b = sum of the 6 anchors of a UTC day; a day with any missing anchor is excluded.
T-a (prereg §1, check only): daily (in-service - fundflip)/2 through the frozen judge, s42, from the in-service
  reference cell and alloc's R cell (32 PATH files each).
FEATURES (prereg §3, frozen): at each UTC day t (anchor t = 00:00Z):
  F1 IQR of member fe_v at t | F2 share of members with |fn_v| > p95 of pooled member |fn_v| over [t-90d, t)
  F3 BTC sum of 5m R over (t-7d, t] | F4 BTC std of those 5m R * sqrt(n) | F5 sum of daily T-b over [t-30d, t)
  (>= 25 finite days) | F6 share of members with iv_v != 8 | B0 = masked seat w2 = WL2 / (WL0 + WL2) at t.
LABEL: fail_t(H) = 1[ sum of daily T-b over days t .. t+H-1 < 0 ], H = 7 (gate) and 30 (described).
MODEL: logistic, C = 1.0, lbfgs; M = [B0, F1..F6], B0-model = [B0]; expanding window, refit on the 1st of
  every month from 2023-07 with train days s satisfying s + H days <= refit day (ASSERTED per refit), features
  standardised on the training rows only. OOS: pre-2026 = 2023-07-01..2025-12-31; 2026 = 2026-01-01.. last
  day whose label window ends by 2026-09-01.
STATISTICS: AUC; null = permute 7-day blocks of the fail labels within the segment (B = 2000, seeds
  20260926 + b); delta-AUC CI = 7-day block bootstrap (B = 2000, seeds 20270926 + b), 2.5/97.5 pct.
PG-D4-3 (first): planted T_H' = T_H + kappa * z(F1), kappa bisected so AUC(-z(F1), fail') = 0.75 on pre-2026
  OOS days; the whole walk-forward M is re-run on fail'; PASS iff pre-2026 z(AUC vs null) >= 3.
Gates are transcribed from the decision rule; this device computes them and records PASS/FAIL, it does not
set any threshold.

usage: dlarch_d4_pregates.py <env-whitelist> <out.json>
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]

NS2 = '/dev/shm/news2_2026-09-23'
FEAT, LEGS = f'{NS2}/work/NEWS_FEATURES.npz', f'{NS2}/work/legs.npz'
WK = '/dev/shm/nc_2026-09-23/work'
LED_PROD = '/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz'
LED_D10 = '/workspace/ledger_ms_2026-09-26/ledger_full_ms.npz'
REF_CELL = ('/workspace/dlarch_2026-09-24/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE',
            'DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE')
R_CELL = ('/workspace/alloc_2026-09-26/cells/inservice_fundflip_s42/runs/ALLOC_inservice_fundflip_s42X_scaled_rule_raw_UAFE',
          'ALLOC_inservice_fundflip_s42X_scaled_rule_raw_UAFE')
ENGINE = f'{NS2}/engine'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       LEGS: '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',
       f'{WK}/R_crypto.npy': '16458cab70cfa65a24360fe602951cfa04f8f33ed0e9a374c0ca598a1e56f185',
       LED_PROD: 'bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad',
       LED_D10: 'e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88'}
DAY, H4 = 86400, 14400
T = lambda *x: calendar.timegm(x + (0,) * (6 - len(x)))
OOS_PRE, OOS_26 = (T(2023, 7, 1), T(2026, 1, 1)), (T(2026, 1, 1), T(2026, 9, 1))
YEARS = {'2023H2': (T(2023, 6, 30), T(2024, 1, 1)), '2024': (T(2024, 1, 1), T(2025, 1, 1)),
         '2025': (T(2025, 1, 1), T(2026, 1, 1)), '2026': (T(2026, 1, 1), T(2026, 9, 1))}
B_NULL, B_BOOT, BLOCK = 2000, 2000, 7
PRICE_TOL_BPS = 1e-3
rec = {'device': 'dlarch_d4_pregates.py', 'utc_start': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'criterion': 'DECISION_RULE_D2_D4_pregates_2026-09-26.md (8bf66bdc5), D4 section, transcribed',
       'gate_caliber': 'PRODUCER (old P2 ledger_full, second key); D10 (ms key) reported, never gates'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def iso(t):
    return time.strftime('%Y-%m-%d', time.gmtime(int(t)))


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
    print('D4_PREGATES %s out=%s sha256=%s' % (('STOPPED ' + stop) if stop else 'DONE', OUT, sha(OUT)), flush=True)


for p, want in PIN.items():
    assert sha(p) == want, f'input moved: {p}'
rec['inputs'] = PIN

# ── load ───────────────────────────────────────────────────────────────────────────────────────
F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64)
syms = [str(s) for s in F['symbols']]; NW = len(syms)
Lg = np.load(LEGS); assert np.array_equal(Lg['E_ts'].astype(np.int64), a)
ZFD, WLs, LR, ready = Lg['ZFD'], Lg['WL'], Lg['LR'], Lg['ready']
m_all, fe_v, fn_v, iv_v = F['m'].astype(np.int64), F['fe_v'], F['fn_v'], F['iv_v']
ax = np.load(f'{WK}/axes.npz', allow_pickle=True); ts = ax['ts'].astype(np.int64); cols = ax['crypto_cols'].astype(np.int64)
assert [str(s) for s in ax['symbols']] == syms
R = np.load(f'{WK}/R_crypto.npy', mmap_mode='r')
cpos = np.full(NW, -1, np.int64); cpos[cols] = np.arange(len(cols))
ibtc = syms.index('BTCUSDT'); assert cpos[ibtc] >= 0


def ledger(path, key, scale):
    z = np.load(path, allow_pickle=True)
    assert [str(s) for s in z['symbols']] == syms, 'ledger symbol order differs'
    o = z['off'].astype(np.int64); ft = z[key].astype(np.int64); rate = z['rate'].astype(np.float64)
    return [(ft[o[j]:o[j + 1]] / scale, rate[o[j]:o[j + 1]]) for j in range(NW)]


LEDGERS = {'producer': ledger(LED_PROD, 'ft', 1.0), 'd10': ledger(LED_D10, 'ft_ms', 1000.0)}
LEDGER_END = min(max((float(f[-1]) for f, _ in L if len(f)), default=0) for L in LEDGERS.values())
rec['ledger_end_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(LEDGER_END))


def leg_weights(k):
    """nc_legs.py L44-L55 on the stored arrays: returns (pm, w, y4v_pm) for formation row k."""
    A = int(a[k]); pm = m_all[off[k]:off[k + 1]]
    ia = int(np.searchsorted(ts, A + H4)); assert ts[ia] == A + H4
    cp = cpos[pm]; seg = np.full((48, len(pm)), np.nan, np.float32)
    okc = cp >= 0; seg[:, okc] = R[ia - 47:ia + 1][:, cp[okc]]
    fin = np.isfinite(seg); y = np.where(fin, seg, 0).sum(0); y[fin.sum(0) < 46] = np.nan
    z = np.nan_to_num(ZFD[k, pm].astype(np.float64)); okl = np.isfinite(y)
    zz = np.where(okl, z, 0.0); zz -= zz[okl].mean() if okl.sum() else 0
    g = np.abs(zz).sum()
    return pm, (zz / g if g > 1e-9 else np.zeros_like(zz)), y


def carry(pm, w, A, L, shift=0.0):
    c = 0.0
    for j, wj in zip(pm, w):
        if wj == 0.0:
            continue
        ft, rt = L[j]
        lo, hi = np.searchsorted(ft, A + shift, 'right'), np.searchsorted(ft, A + H4 + shift, 'right')
        if hi > lo:
            c += wj * float(rt[lo:hi].sum())
    return c * 1e4


# ── T-b per anchor ────────────────────────────────────────────────────────────────────────────
rows = [k for k in range(len(a) - 1) if np.isfinite(LR[k, 2]) and a[k] + H4 <= LEDGER_END]
price = np.full(len(a), np.nan); tb = {c: np.full(len(a), np.nan) for c in LEDGERS}; tb_red = np.full(len(a), np.nan)
maxdiff = 0.0
for k in rows:
    assert a[k + 1] == a[k] + H4, 'LR row k must be followed by the next anchor'
    pm, w, y = leg_weights(k)
    price[k] = float((w * np.nan_to_num(y)).sum() * 1e4)
    maxdiff = max(maxdiff, abs(price[k] - LR[k, 2]))
    for c, L in LEDGERS.items():
        tb[c][k] = price[k] - carry(pm, w, int(a[k]), L)
    tb_red[k] = price[k] - carry(pm, w, int(a[k]), LEDGERS['producer'], shift=H4)
rec['price_identity'] = {'rows_compared': len(rows), 'max_abs_diff_bps': maxdiff, 'tol_bps': PRICE_TOL_BPS,
                         'PASS': maxdiff <= PRICE_TOL_BPS,
                         'why_not_bitwise': 'ZFD stored float32; nc_legs used the float64 z'}
# carry known answer + red
_syn = [(np.array([1000.0 + H4, 1000.0 + 5.0]), np.array([1e-4, 2e-4]))]      # one at A+4h (in), one inside
_c = carry(np.array([0]), np.array([1.0]), 1000, _syn)
_c0 = carry(np.array([0]), np.array([1.0]), 1000 + H4, [(np.array([1000.0 + H4]), np.array([1e-4]))])  # exactly at A: out
red_changed = int(np.sum(np.isfinite(tb_red) & (np.abs(tb_red - tb['producer']) > 1e-12)))
rec['carry_controls'] = {'known_answer_bps': _c, 'expected_bps': 3.0, 'at_A_excluded_bps': _c0,
                         'red_shift_4h_changed_anchors': red_changed,
                         'PASS': abs(_c - 3.0) < 1e-9 and _c0 == 0.0 and red_changed > 0}
log('price identity', rec['price_identity'], 'carry controls', rec['carry_controls'])
if not (rec['price_identity']['PASS'] and rec['carry_controls']['PASS']):
    write('TARGET_CONTROLS_FAILED'); sys.exit(1)

# daily T-b
days_all = np.unique((a // DAY) * DAY)


def daily(x):
    out = {}
    for d in days_all:
        ks = np.flatnonzero((a >= d) & (a < d + DAY))
        if len(ks) == 6 and np.all(np.isfinite(x[ks])):
            out[int(d)] = float(x[ks].sum())
    return out


TBD = {c: daily(tb[c]) for c in LEDGERS}
rec['daily_T_b_days'] = {c: len(v) for c, v in TBD.items()}
rec['carry_caliber_diff'] = {'anchors_where_producer_ne_d10': int(np.sum(np.isfinite(tb['producer']) & (np.abs(tb['producer'] - tb['d10']) > 1e-12)))}

# ── features and labels per UTC day ──────────────────────────────────────────────────────────
aidx = {int(t): i for i, t in enumerate(a)}
fn_abs = np.abs(fn_v.astype(np.float64))
pair_anchor = np.repeat(np.arange(len(a)), np.diff(off))


def features(t, TBd):
    k = aidx.get(t)
    if k is None or off[k + 1] - off[k] < 50:
        return None
    sl = slice(off[k], off[k + 1])
    f1 = float(np.subtract(*np.percentile(fe_v[sl].astype(np.float64), [75, 25])))
    lo_k, hi_k = np.searchsorted(a, t - 90 * DAY), np.searchsorted(a, t)          # anchors in [t-90d, t)
    pool = fn_abs[off[lo_k]:off[hi_k]]
    if pool.size < 1000:
        return None
    f2 = float(np.mean(fn_abs[sl] > np.percentile(pool, 95)))
    r0, r1 = np.searchsorted(ts, t - 7 * DAY, 'right'), np.searchsorted(ts, t, 'right')   # (t-7d, t]
    rb = np.asarray(R[r0:r1, cpos[ibtc]], np.float64); rb = rb[np.isfinite(rb)]
    if rb.size < 1500:
        return None
    f3, f4 = float(rb.sum()), float(rb.std() * np.sqrt(rb.size))
    past = [TBd.get(t - j * DAY) for j in range(1, 31)]
    past = [x for x in past if x is not None]
    if len(past) < 25:
        return None
    f5 = float(np.sum(past))
    f6 = float(np.mean(iv_v[sl] != 8))
    wl = WLs[k].astype(np.float64)
    if not np.all(np.isfinite(wl)) or wl[0] + wl[2] <= 0:
        return None
    b0 = float(wl[2] / (wl[0] + wl[2]))
    v = [b0, f1, f2, f3, f4, f5, f6]
    return v if np.all(np.isfinite(v)) else None


def label(t, H, TBd):
    xs = [TBd.get(t + j * DAY) for j in range(H)]
    if any(x is None for x in xs):
        return None
    return float(np.sum(xs))


def build(TBd, H):
    D, X, Y = [], [], []
    for t in sorted(TBd):
        if t + H * DAY > LEDGER_END:
            continue
        f = features(t, TBd); y = label(t, H, TBd)
        if f is None or y is None:
            continue
        D.append(t); X.append(f); Y.append(y)
    return np.array(D, np.int64), np.array(X), np.array(Y)


# ── walk-forward logistic + statistics ────────────────────────────────────────────────────────
from sklearn.linear_model import LogisticRegression          # noqa: E402
from sklearn.metrics import roc_auc_score                    # noqa: E402
from scipy.stats import spearmanr                            # noqa: E402


def month_starts(lo, hi):
    # T(y, m) WITHOUT a day is day 0 = the last day of the previous month (calendar.timegm accepts it). The
    # first run of this device (23:18Z) used exactly that, so every [ms, me) window was empty and the
    # walk-forward made 0 refits; PG-D4-3 then read "UNDEFINED" and STOPPED -- an instrument failure, not
    # a resolution reading. The day is now explicit everywhere and the test windows are asserted non-empty.
    y, m = time.gmtime(lo).tm_year, time.gmtime(lo).tm_mon; out = []
    while T(y, m, 1) < hi:
        out.append(T(y, m, 1)); y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def next_month(ms):
    g = time.gmtime(ms); assert g.tm_mday == 1 and g.tm_hour == 0
    return T(g.tm_year + (g.tm_mon == 12), g.tm_mon % 12 + 1, 1)


def walk(D, X, fail, H, cols_used):
    P = np.full(len(D), np.nan); refits = []
    for ms in month_starts(OOS_PRE[0], OOS_26[1]):
        me = next_month(ms)
        tr = D + H * DAY <= ms
        te = (D >= ms) & (D < me)
        if not te.any():
            continue
        assert (D[tr] + H * DAY <= ms).all() and (D[te] >= ms).all(), 'leakage: label window overlaps the refit'
        if tr.sum() < 180 or len(np.unique(fail[tr])) < 2:
            continue
        Xt = X[tr][:, cols_used]; mu, sd = Xt.mean(0), Xt.std(0) + 1e-12
        mdl = LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000).fit((Xt - mu) / sd, fail[tr])
        P[te] = mdl.predict_proba((X[te][:, cols_used] - mu) / sd)[:, 1]
        refits.append({'month': iso(ms), 'n_train': int(tr.sum()), 'max_train_label_end': iso(D[tr].max() + H * DAY)})
    n_months_with_days = sum(1 for ms in month_starts(OOS_PRE[0], OOS_26[1]) if ((D >= ms) & (D < next_month(ms))).any())
    assert len(refits) >= n_months_with_days - 1, f'walk-forward refit only {len(refits)} of {n_months_with_days} months'
    return P, refits


def blocks(D, lo):
    return ((D - lo) // (BLOCK * DAY)).astype(np.int64)


def seg_stats(D, P, P0, fail, y, seg):
    s = (D >= seg[0]) & (D < seg[1]) & np.isfinite(P) & np.isfinite(P0)
    if s.sum() < 20 or len(np.unique(fail[s])) < 2:
        return {'n_days': int(s.sum()), 'status': 'UNDEFINED (too few days or one class)'}
    d, p, p0, f, yy = D[s], P[s], P0[s], fail[s], y[s]
    auc, auc0 = roc_auc_score(f, p), roc_auc_score(f, p0)
    bl = blocks(d, seg[0]); ub = np.unique(bl); idx = [np.flatnonzero(bl == b) for b in ub]
    null = []
    for b in range(B_NULL):
        rng = np.random.default_rng(20260926 + b); perm = rng.permutation(len(ub))
        fp = np.concatenate([f[idx[j]] for j in perm])      # block order permuted; every block kept => same length
        assert len(fp) == len(f)
        if len(np.unique(fp)) == 2:
            null.append(roc_auc_score(fp, p))
    null = np.array(null)
    boot = []
    for b in range(B_BOOT):
        rng = np.random.default_rng(20270926 + b); pick = rng.integers(0, len(ub), len(ub))
        ii = np.concatenate([idx[j] for j in pick])
        if len(np.unique(f[ii])) == 2:
            boot.append(roc_auc_score(f[ii], p[ii]) - roc_auc_score(f[ii], p0[ii]))
    boot = np.array(boot)
    return {'n_days': int(s.sum()), 'n_fail': int(f.sum()), 'n_blocks': int(len(ub)),
            'AUC_M': float(auc), 'AUC_B0': float(auc0), 'dAUC': float(auc - auc0),
            'null_mean': float(null.mean()), 'null_sd': float(null.std(ddof=1)), 'null_p97_5': float(np.percentile(null, 97.5)),
            'null_B_used': int(len(null)), 'z_M_vs_null': float((auc - null.mean()) / null.std(ddof=1)),
            'dAUC_ci95': [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))], 'boot_B_used': int(len(boot)),
            'rankIC_pfail_vs_sum_Tb': float(spearmanr(p, yy).statistic)}


def run(TBd, H, planted_kappa=None):
    D, X, Y = build(TBd, H)
    if planted_kappa is not None:
        zf1 = (X[:, 1] - X[:, 1].mean()) / X[:, 1].std()
        Y = Y + planted_kappa * zf1
    fail = (Y < 0).astype(int)
    P, rf = walk(D, X, fail, H, [0, 1, 2, 3, 4, 5, 6])
    P0, _ = walk(D, X, fail, H, [0])
    return {'n_days_total': int(len(D)), 'refits': len(rf), 'first_refit': rf[0] if rf else None, 'last_refit': rf[-1] if rf else None,
            'pre2026': seg_stats(D, P, P0, fail, Y, OOS_PRE), '2026': seg_stats(D, P, P0, fail, Y, OOS_26)}, (D, X, Y)


# ── PG-D4-3 power (FIRST) ─────────────────────────────────────────────────────────────────────
D7, X7, Y7 = build(TBD['producer'], 7)
pre = (D7 >= OOS_PRE[0]) & (D7 < OOS_PRE[1])
zf1 = (X7[:, 1] - X7[:, 1].mean()) / X7[:, 1].std()


def true_auc(kappa):
    f = ((Y7 + kappa * zf1) < 0).astype(int)
    return roc_auc_score(f[pre], -zf1[pre])


lo_k, hi_k = 0.0, 1.0
while true_auc(hi_k) < 0.75:
    hi_k *= 2; assert hi_k < 1e9
for _ in range(60):
    mid = (lo_k + hi_k) / 2
    lo_k, hi_k = (mid, hi_k) if true_auc(mid) < 0.75 else (lo_k, mid)
kappa = hi_k
pw, _ = run(TBD['producer'], 7, planted_kappa=kappa)
z_pre = pw['pre2026'].get('z_M_vs_null')
rec['PG_D4_3_power'] = {'kappa_bps': kappa, 'true_AUC_planted_pre2026': float(true_auc(kappa)), 'target_true_AUC': 0.75,
                        'readout': pw, 'gate': 'pre-2026 z(AUC_M vs block-permutation null) >= 3; 2026 reported only',
                        'PASS': bool(z_pre is not None and z_pre >= 3.0)}
log('PG-D4-3', rec['PG_D4_3_power']['PASS'], 'z_pre', z_pre)
if not rec['PG_D4_3_power']['PASS']:
    write('PG_D4_3_NO_RESOLUTION'); sys.exit(0)

# ── PG-D4-0 target validity ───────────────────────────────────────────────────────────────────
sys.path.insert(0, '/workspace/dlarch_2026-09-24')
import dlarch_cell_retain as CR                               # noqa: E402
NS, _BT, _DL = CR.load_frozen(ENGINE)
ref, _ = NS.load_cell(*REF_CELL); rc, _ = NS.load_cell(*R_CELL)
A_ = ref[0]['A']; assert np.array_equal(A_, rc[0]['A'])
m_ = (A_ >= YEARS['2023H2'][0]) & (A_ < YEARS['2026'][1])
dd = NS.full_days(A_, m_)
_, Dm = NS.dbar(ref, rc, m_, dd)
TA = {int(d): float(v) * 1e4 / 2 for d, v in zip(dd, Dm.mean(0))}
cells = {}
for y, (lo, hi) in YEARS.items():
    common = [d for d in TA if lo <= d < hi and d in TBD['producer']]
    ta = float(np.mean([TA[d] for d in common])); tbm = float(np.mean([TBD['producer'][d] for d in common]))
    cells[y] = {'n_days': len(common), 'T_a_mean_bps_per_day': ta, 'T_b_mean_bps_per_day': tbm, 'same_sign': bool(np.sign(ta) == np.sign(tbm))}
n_same = sum(v['same_sign'] for v in cells.values())
rec['PG_D4_0_target_validity'] = {'cells': cells, 'n_same_sign': n_same, 'gate': '>= 3 of 4 same sign',
                                  'PASS': n_same >= 3, 'note': 'T-a is the (in-service - fundflip)/2 book difference, NOT the leg contribution (chain non-linear)'}
log('PG-D4-0', n_same, '/4')
if not rec['PG_D4_0_target_validity']['PASS']:
    write('PG_D4_0_TARGET_NOT_BOOK'); sys.exit(0)

# ── PG-D4-1 / PG-D4-2 (gate: producer, H=7; H=30 and D10 described) ─────────────────────────
res = {}
for c in ('producer', 'd10'):
    for H in (7, 30):
        res[f'{c}_H{H}'], _ = run(TBD[c], H)
        log('readout', c, H, 'done')
g = res['producer_H7']; gp, g6 = g['pre2026'], g['2026']
pg1 = bool(gp.get('AUC_M', 0) >= 0.60 and gp.get('AUC_M', 0) > gp.get('null_p97_5', 1) and g6.get('AUC_M', 0) >= 0.50)
pg2 = bool(gp.get('dAUC_ci95', [0])[0] > 0 and g6.get('dAUC', -1) > 0)
rec['readouts'] = res
rec['PG_D4_1_predictability'] = {'gate': 'pre-2026 AUC_M >= 0.60 and > null p97.5; 2026 AUC_M >= 0.50 (producer, H=7)', 'PASS': pg1}
rec['PG_D4_2_increment'] = {'gate': 'pre-2026 dAUC block-bootstrap 95% lower > 0; 2026 dAUC point > 0 (producer, H=7)', 'PASS': pg2}
rec['ALL_FOUR_PASS'] = bool(rec['PG_D4_3_power']['PASS'] and rec['PG_D4_0_target_validity']['PASS'] and pg1 and pg2)
write()
