#!/usr/bin/env python3
"""dlarch_momentum_loading.py -- DESCRIPTIVE ONLY, no gate (lead 2026-09-27, user question "no rally, losses
keep growing"): is the in-service book anti-momentum, and through which leg?

Written and committed BEFORE any reading. Everything here is on the RESEARCH REPLAY axis, which is bitwise the
production combo at s42 (parity, 9c1b3a179 family) and ends 2026-09-18T20Z (R_crypto ends 2026-09-19T00Z).
It therefore covers only 09-16..09-18 of the live drawdown; 09-19..09-26 need live inputs this device may not
read (team rule: dlarch never touches ~/wide_shadow or ~/dl_quant_live) -- named, not silently dropped.

(1) LOADINGS per anchor A (2023-01-01 .. 2026-09-18T20Z), k in {1, 3, 7} days, past return
    p_k = sum of log1p(5m R_crypto) over (A - k d, A], >= 80% finite rows, crypto members only:
      fund leg : Spearman(ZFD[A, members], p_k)          (the fund-rank z both books carry)
      King leg : Spearman(KZ[A, members], p_k)
      book     : Spearman(held weights over names with |w| > 0, p_k)   held = last PUBLISHED weights
                 (combo_s42/scaled_diagnostic 'weights' where trade_mask, carried forward), and the exposure
                 E_k = sum(w * z(p_k)) / sum|w| (z over the same names) as a second, non-rank reading
    reported: 2026 per calendar month (mean over anchors) and the pre-2026 mean (2023-07 .. 2025-12).
(2) MOMENTUM FACTOR per anchor: m = rank-z of p_k over crypto members, de-meaned, sum|m| = 1; its return over
    (A, A+4h] = sum(m * (prod(1 + R) - 1)) in bps; daily sum. BOOK daily return = the certified in-service
    reference cell (DLARCH_REF_NC_s42X, 32 paths, mean path) through the frozen judge; also the price-only
    held-book return from the same 5m data (an ESTIMATE, excludes funding and fees).
    reported: corr(book daily, MOM_k daily) per 2026 month and pre-2026; OLS beta of book on MOM_k in 2026;
    and for the covered drawdown days (>= 2026-09-16): MOM_k daily return, book daily return, and the
    beta * MOM product per day -- an ESTIMATE, and shares are NOT additive (one regressor, no decomposition).
(3) alloc R reconciliation: monthly corr(fund-leg LR daily, MOM_k daily) and the monthly sum of both, 2026 vs
    pre-2026 -- is the fund leg's large 2026 value (R flip -56 bps/day) an anti-momentum payoff?
Caliber: research replay / 5m return channel; engine returns are v4 RAW via the frozen judge; everything
built from the 5m channel is labelled ESTIMATE.

usage: dlarch_momentum_loading.py <env-whitelist> <out.json>
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]
NS2 = '/dev/shm/news2_2026-09-23'; WK = '/dev/shm/nc_2026-09-23/work'
FEAT, LEGS, COMBO = f'{NS2}/work/NEWS_FEATURES.npz', f'{NS2}/work/legs.npz', f'{NS2}/work/combo_s42/scaled_diagnostic.npz'
REF_CELL = ('/workspace/dlarch_2026-09-24/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE',
            'DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE')
ENGINE = f'{NS2}/engine'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       LEGS: '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',
       f'{WK}/R_crypto.npy': '16458cab70cfa65a24360fe602951cfa04f8f33ed0e9a374c0ca598a1e56f185'}
DAY, H4, KS = 86400, 14400, (1, 3, 7)
T = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))
PRE = (T(2023, 7), T(2026, 1)); Y26 = T(2026, 1); DD0 = T(2026, 9, 16)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def log(*a):
    print(time.strftime('%H:%M:%S', time.gmtime()), *a, flush=True)


for p, w in PIN.items():
    assert sha(p) == w, f'input moved: {p}'
from scipy.stats import spearmanr, rankdata                     # noqa: E402

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
syms = [str(s) for s in F['symbols']]; NW = len(syms)
Lg = np.load(LEGS); assert np.array_equal(Lg['E_ts'].astype(np.int64), a)
KZ, ZFD, LR = Lg['KZ'], Lg['ZFD'], Lg['LR']
C = np.load(COMBO); CE = C['E_ts'].astype(np.int64); Wpub, TM = C['weights'], C['trade_mask']
assert [str(s) for s in C['symbols']] == syms
ax = np.load(f'{WK}/axes.npz', allow_pickle=True); ts = ax['ts'].astype(np.int64); cols = ax['crypto_cols'].astype(np.int64)
assert [str(s) for s in ax['symbols']] == syms
R = np.load(f'{WK}/R_crypto.npy', mmap_mode='r')
cpos = np.full(NW, -1, np.int64); cpos[cols] = np.arange(len(cols))
aidx = {int(t): i for i, t in enumerate(a)}
rec = {'device': 'dlarch_momentum_loading.py', 'inputs': dict(PIN, combo=sha(COMBO)), 'descriptive_only': True,
       'axis': [time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(CE[0]))), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(CE[-1])))],
       'live_gap': '2026-09-19 .. 09-26 NOT covered: needs live target weights + 5m returns (dlarch may not read ~/wide_shadow or ~/dl_quant_live)'}


# prefix sums over the whole 5m axis (one pass; per-anchor window sums are then O(names)):
#   CS[t] = sum_{u < t} log1p(R_u) with NaN -> 0 ; CN[t] = count of finite R_u, u < t
log('building prefix sums')
CS = np.zeros((len(ts) + 1, len(cols)), np.float64); CN = np.zeros((len(ts) + 1, len(cols)), np.int32)
for c0 in range(0, len(ts), 50000):
    blk = np.asarray(R[c0:c0 + 50000], np.float64); fin = np.isfinite(blk)
    CS[c0 + 1:c0 + 1 + len(blk)] = CS[c0] + np.cumsum(np.log1p(np.where(fin, blk, 0.0)), 0)
    CN[c0 + 1:c0 + 1 + len(blk)] = CN[c0] + np.cumsum(fin, 0)
log('prefix sums done')


def win(lo_t, hi_t, names):
    """sum log1p(R) and finite count over 5m rows with ts in (lo_t, hi_t], for crypto names (NaN elsewhere)."""
    r0, r1 = np.searchsorted(ts, lo_t, 'right'), np.searchsorted(ts, hi_t, 'right')
    cp = cpos[names]; ok = cp >= 0
    s = np.full(len(names), np.nan); n = np.zeros(len(names), np.int64)
    s[ok] = CS[r1, cp[ok]] - CS[r0, cp[ok]]; n[ok] = CN[r1, cp[ok]] - CN[r0, cp[ok]]
    return s, n, r1 - r0


def past_ret(A, k, names):
    s, n, rows = win(A - k * DAY, A, names)
    s[n < 0.8 * rows] = np.nan
    return s


def fwd_ret(A, names):
    s, n, rows = win(A, A + H4, names)
    out = np.expm1(s); out[n < 46] = np.nan
    return out


def rho(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 20 or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
        return np.nan
    return float(spearmanr(x[ok], y[ok]).statistic)


# ── per-anchor loadings, factor returns, held-book price return ───────────────────────────────
held = np.zeros(NW); rows = []
for j, A in enumerate(CE):
    if TM[j]:
        held = Wpub[j].astype(np.float64)
    i = aidx.get(int(A))
    if i is None:
        continue
    mem = m_all[off[i]:off[i + 1]]
    fr = fwd_ret(int(A), np.arange(NW))
    bookn = np.flatnonzero(np.abs(held) > 1e-12)
    r = {'A': int(A), 'book_price_bps': float(np.nansum(held * np.nan_to_num(fr)) * 1e4)}
    for k in KS:
        pk_m = past_ret(int(A), k, mem)
        r[f'fund_k{k}'] = rho(ZFD[i, mem].astype(np.float64), pk_m)
        r[f'king_k{k}'] = rho(KZ[i, mem].astype(np.float64), pk_m)
        pk_b = past_ret(int(A), k, bookn)
        r[f'book_k{k}'] = rho(held[bookn], pk_b)
        okb = np.isfinite(pk_b)
        if okb.sum() >= 20:
            zb = (pk_b[okb] - pk_b[okb].mean()) / (pk_b[okb].std() + 1e-12)
            r[f'bookE_k{k}'] = float((held[bookn][okb] * zb).sum() / (np.abs(held[bookn][okb]).sum() + 1e-12))
        else:
            r[f'bookE_k{k}'] = np.nan
        okm = np.isfinite(pk_m) & np.isfinite(fr[mem])
        if okm.sum() >= 20:
            rk = rankdata(pk_m[okm]); z = rk - rk.mean(); z /= np.abs(z).sum()
            r[f'mom_k{k}_bps'] = float((z * fr[mem][okm]).sum() * 1e4)
        else:
            r[f'mom_k{k}_bps'] = np.nan
    r['fundLR_bps'] = float(LR[i, 2]) if np.isfinite(LR[i, 2]) else np.nan
    rows.append(r)
    if j % 1000 == 0:
        log('anchor', j, '/', len(CE))
keys = [k for k in rows[0] if k != 'A']
Aarr = np.array([r['A'] for r in rows]); M = {k: np.array([r[k] for r in rows], float) for k in keys}

# ── certified book daily returns (in-service reference cell) ─────────────────────────────────
sys.path.insert(0, '/workspace/dlarch_2026-09-24')
import dlarch_cell_retain as CR                                  # noqa: E402
NS, BT, _DL = CR.load_frozen(ENGINE)
paths, _ = NS.load_cell(*REF_CELL); PA = paths[0]['A']
mm = np.ones(len(PA), bool); days = NS.full_days(PA, mm)
book_day = {int(d): float(v) * 1e4 for d, v in zip(days, np.mean([NS.daily_on(p['A'][mm], p['r'][mm], days) for p in paths], 0))}

# daily aggregation of per-anchor quantities (6 anchors per day)
dayk = (Aarr // DAY) * DAY
def daily(x):
    out = {}
    for d in np.unique(dayk):
        s = dayk == d
        if s.sum() == 6 and np.all(np.isfinite(x[s])):
            out[int(d)] = float(x[s].sum())
    return out
MOMD = {k: daily(M[f'mom_k{k}_bps']) for k in KS}; FUNDD = daily(M['fundLR_bps']); BPD = daily(M['book_price_bps'])

def months():
    out = []
    for mo in range(1, 10):
        out.append((f'2026-{mo:02d}', T(2026, mo), T(2026, mo + 1) if mo < 12 else T(2027, 1)))
    return out
SEGS = [('pre2026', PRE[0], PRE[1])] + months()

load = {}
for name, lo, hi in SEGS:
    s = (Aarr >= lo) & (Aarr < hi)
    load[name] = {'n_anchors': int(s.sum())}
    for leg in ('fund', 'king', 'book', 'bookE'):
        for k in KS:
            load[name][f'{leg}_k{k}'] = float(np.nanmean(M[f'{leg}_k{k}'][s])) if s.any() else None
rec['loadings'] = load


def corr_days(A_, B_, lo, hi):
    d = [x for x in A_ if lo <= x < hi and x in B_]
    if len(d) < 5:
        return {'n_days': len(d), 'corr': None}
    x, y = np.array([A_[t] for t in d]), np.array([B_[t] for t in d])
    return {'n_days': len(d), 'corr': float(np.corrcoef(x, y)[0, 1]), 'sum_A': float(x.sum()), 'sum_B': float(y.sum())}


fac = {}
for name, lo, hi in SEGS:
    fac[name] = {f'MOM{k}': {'book_certified': corr_days(book_day, MOMD[k], lo, hi),
                             'book_price_ESTIMATE': corr_days(BPD, MOMD[k], lo, hi),
                             'fund_leg_LR': corr_days(FUNDD, MOMD[k], lo, hi)} for k in KS}
rec['factor_correlations'] = fac

# 2026 beta and the covered drawdown days
beta = {}
for k in KS:
    d = [t for t in book_day if Y26 <= t < T(2026, 9, 19) and t in MOMD[k]]
    x = np.array([MOMD[k][t] for t in d]); y = np.array([book_day[t] for t in d])
    b = float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)); beta[f'MOM{k}'] = {'n_days': len(d), 'beta_book_on_MOM': b}
    dd = [t for t in d if t >= DD0]
    beta[f'MOM{k}']['drawdown_days_covered'] = [{'day': time.strftime('%Y-%m-%d', time.gmtime(t)), 'MOM_bps': MOMD[k][t],
                                                  'book_bps': book_day[t], 'beta_x_MOM_bps_ESTIMATE': b * MOMD[k][t]} for t in dd]
rec['beta_2026'] = beta
rec['note_shares'] = 'beta x MOM is one regressor on one book series; it is NOT a share of the drawdown and does not add with anything'
rec['self_sha256'] = sha(os.path.abspath(__file__))
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=float)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('MOM_LOADING DONE out=%s sha256=%s' % (OUT, sha(OUT)), flush=True)
