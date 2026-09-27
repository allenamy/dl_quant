#!/usr/bin/env python3
"""dlarch_king_rootcause.py -- DESCRIPTIVE ONLY (lead 2026-09-27, user question): why is King so bad INSIDE the book in
2026 when it does not look bad on its own? Parts (1), (2), (3a) of the lead's list; (3b) seat-vs-composition cells are
fresh2's (King owner), (4) CF3 reconciliation is prose in the result file. Written and committed BEFORE any reading.

(1) KING ON ITS OWN, three layers, pre-2026 (2023-06-30 .. 2025-12-31) and 2026 (2026-01-01 .. 2026-08-31):
    a. SCORE layer: cross-sectional Spearman IC of KING_OOF P vs y4s (frozen news2_diag1_score_ic.ic_series, called one UTC
       day at a time), day-block CI from the frozen judge's boot (BLOCK_MAIN); the same for the fund rank ZFD, for contrast.
    b. SINGLE-LEG BOOK, per formation anchor A, with the leg weights of nc_legs.py L44-L55 (z de-meaned over names with a
       finite 4h return, w = zz / sum|zz|): price = sum(w * y4v) (reconstructed; identity vs LR[:,leg] asserted <= 1e-3 bps
       per anchor, the D4 control), funding = sum(w * settled rate in (A, A+4h]) (producer ledger, second key; a long pays
       +rate), fee PROXY = 3.52 bps * sum|w_A - w_{A-4h}| (the trainer's cost coefficient; no EMA/band, so an UPPER-side
       proxy of what a smoothed book would pay -- named). net = price - funding - fee. Daily sums; mean bps/day per unit gross,
       day-block CI. Legs: King (KZ) and fund (ZFD). Ledger ends 2026-09-01 => 2026 stops at 08-31 (named).
(2) KING vs FUND LEG, per anchor: Pearson and Spearman corr(KZ, ZFD) over members; opposition share = fraction of members
    with sign(KZ) != sign(ZFD); top-tercile King names that are bottom-tercile fund, and vice versa; daily corr of the two
    legs' NET returns and the hedge beta cov(K, F) / var(F); monthly for 2026 and the pre-2026 mean. (Momentum loadings are
    in MOM_LOADING / MOM_SEAT_DECOMP, cited, not recomputed.)
(3a) CHANNELS of fresh2's red control: SER_RED_m0 vs SER_A0_m0 (both seeds; 32 paths each), daily sums of the engine
    channels g = pnl - car - cst - unk (bps per unit gross, bt_tables.series_from_path definitions), mean over paths,
    RED - A0 per channel and segment; closure g == pnl - car - cst - unk asserted per anchor; the r-based D-bar is recomputed
    and compared with fresh2's MR_READ_red (a reproduction control, 1e-6).
Shares are NOT additive anywhere: each number is one quantity, no decomposition of the book gap is claimed.

usage: dlarch_king_rootcause.py <env-whitelist> <out.json>
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
OUT = sys.argv[2]
NS2 = '/dev/shm/news2_2026-09-23'; WK = '/dev/shm/nc_2026-09-23/work'; MR = '/dev/shm/mretrain_2026-09-26'
FEAT, LEGS, KOOF = f'{NS2}/work/NEWS_FEATURES.npz', f'{NS2}/work/legs.npz', f'{NS2}/work/king/KING_OOF.npz'
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
LED = '/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       LEGS: '9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65',
       KOOF: 'a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a',
       LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       f'{WK}/R_crypto.npy': '16458cab70cfa65a24360fe602951cfa04f8f33ed0e9a374c0ca598a1e56f185',
       LED: 'bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad',
       f'{MR}/series/SER_RED_m0_s42.npz': 'f5d58088ebd3270d2ebbf7700ceb5b862c2876e42b2902ef9482aa3fddd57fe7',
       f'{MR}/series/SER_A0_m0_s42.npz': '074e8fb25238e5a2b036bf98e105b33d7a7c6bd82a98a009320749e09b330564',
       f'{MR}/series/SER_RED_m0_s2027.npz': '1483918fb73ecf0a049d1d6f21a4e04f2305ab55b32d9950f586024fd07cc1de',
       f'{MR}/series/SER_A0_m0_s2027.npz': '421ff513a07befd812ca285102de8693038bdf7da09790fcc762a84dbf13c039'}
MR_READ_DBAR = {'pre2026': {'42': -5.7562329421296115, '2027': -5.765570369233967},
                '2026': {'42': 3.836574383815537, '2027': 4.736863034429291}}      # MR_READ_red.json (33abbad32), transcribed
DAY, H4, FEE = 86400, 14400, 3.52
T = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))
SEG = {'pre2026': (T(2023, 6, 30), T(2026, 1, 1)), '2026': (T(2026, 1, 1), T(2026, 9, 1))}


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
sys.path.insert(0, '/workspace/dlarch_2026-09-24'); sys.path.insert(0, f'{NS2}/devices')
import dlarch_cell_retain as CR                                   # noqa: E402
NS, BT, _DL = CR.load_frozen(f'{NS2}/engine')
from news2_diag1_score_ic import ic_series                        # noqa: E402
from scipy.stats import spearmanr                                 # noqa: E402
rec = {'device': 'dlarch_king_rootcause.py', 'inputs': PIN, 'descriptive_only': True, 'segments': {k: [time.strftime('%Y-%m-%d', time.gmtime(v[0])), time.strftime('%Y-%m-%d', time.gmtime(v[1]))] for k, v in SEG.items()}}

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
syms = [str(s) for s in F['symbols']]; NW = len(syms)
Lg = np.load(LEGS); assert np.array_equal(Lg['E_ts'].astype(np.int64), a)
KZ, ZFD, LR = Lg['KZ'], Lg['ZFD'], Lg['LR']
K = np.load(KOOF); assert np.array_equal(K['E_ts'].astype(np.int64), a)
lab = np.load(LAB, allow_pickle=True); ya = lab['E_ts'].astype(np.int64)
ax = np.load(f'{WK}/axes.npz', allow_pickle=True); ts = ax['ts'].astype(np.int64); cols = ax['crypto_cols'].astype(np.int64)
R = np.load(f'{WK}/R_crypto.npy', mmap_mode='r'); cpos = np.full(NW, -1, np.int64); cpos[cols] = np.arange(len(cols))
z = np.load(LED, allow_pickle=True); assert [str(s) for s in z['symbols']] == syms
_o = z['off'].astype(np.int64); LEDG = [(z['ft'][_o[j]:_o[j + 1]].astype(np.float64), z['rate'][_o[j]:_o[j + 1]].astype(np.float64)) for j in range(NW)]
LEDGER_END = max(float(f[-1]) for f, _ in LEDG if len(f))

# ── (1a) score-layer IC ─────────────────────────────────────────────────────────────────────────
iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
Ymat = np.full((len(a), NW), np.nan, np.float32); Ymat[lab_ok] = lab['y4s'][iy[lab_ok]]


def ic_seg(P, lo, hi):
    rows = np.flatnonzero(lab_ok & (a >= lo) & (a < hi) & np.isfinite(P).any(1))
    days = np.unique((a[rows] // DAY) * DAY); per = []
    for u in days:
        r = rows[(a[rows] // DAY) * DAY == u]
        icd, _, _ = ic_series(P, Ymat, r, r)
        if len(icd):
            per.append(float(np.mean(icd)))
    per = np.asarray(per); b = NS.boot(per, NS.BLOCK_MAIN)
    return {'ic_mean_of_days': float(per.mean()), 'n_days': len(per), 'ci95': [b['ci95_bps'][0] / 1e4, b['ci95_bps'][1] / 1e4]}


rec['score_layer_IC'] = {nm: {s: ic_seg(P, *SEG[s]) for s in SEG} for nm, P in
                         (('King_OOF', K['P'].astype(np.float32)), ('fund_rank_ZFD', ZFD.astype(np.float32)))}
log('IC done', json.dumps({k: {s: round(v[s]['ic_mean_of_days'], 4) for s in v} for k, v in rec['score_layer_IC'].items()}))

# ── (1b) single-leg books ─────────────────────────────────────────────────────────────────────
def leg_weights(k, Z):
    A = int(a[k]); pm = m_all[off[k]:off[k + 1]]
    ia = int(np.searchsorted(ts, A + H4)); assert ts[ia] == A + H4
    cp = cpos[pm]; seg = np.full((48, len(pm)), np.nan, np.float32); okc = cp >= 0
    seg[:, okc] = R[ia - 47:ia + 1][:, cp[okc]]
    fin = np.isfinite(seg); y = np.where(fin, seg, 0).sum(0); y[fin.sum(0) < 46] = np.nan
    zz0 = np.nan_to_num(Z[k, pm].astype(np.float64)); okl = np.isfinite(y)
    zz = np.where(okl, zz0, 0.0); zz -= zz[okl].mean() if okl.sum() else 0
    g = np.abs(zz).sum()
    return pm, (zz / g if g > 1e-9 else np.zeros_like(zz)), y


def carry(pm, w, A):
    c = 0.0
    for j, wj in zip(pm, w):
        if wj == 0.0:
            continue
        ft, rt = LEDG[j]; lo, hi = np.searchsorted(ft, A, 'right'), np.searchsorted(ft, A + H4, 'right')
        if hi > lo:
            c += wj * float(rt[lo:hi].sum())
    return c * 1e4


legs = {'King': (KZ, 0), 'fund': (ZFD, 2)}
per_anchor = {}
for name, (Z, col) in legs.items():
    price = np.full(len(a), np.nan); fund = np.full(len(a), np.nan); fee = np.full(len(a), np.nan)
    prev_w, prev_k = None, None; maxdiff = 0.0
    for k in range(len(a) - 1):
        if not np.isfinite(LR[k, col]) or a[k] + H4 > LEDGER_END or a[k] < SEG['pre2026'][0] - 30 * DAY:
            prev_w = None; continue
        pm, w, y = leg_weights(k, Z)
        price[k] = float((w * np.nan_to_num(y)).sum() * 1e4); maxdiff = max(maxdiff, abs(price[k] - LR[k, col]))
        fund[k] = carry(pm, w, int(a[k]))
        full = np.zeros(NW); full[pm] = w
        if prev_w is not None and prev_k == k - 1:
            fee[k] = FEE * float(np.abs(full - prev_w).sum())
        prev_w, prev_k = full, k
    assert maxdiff <= 1e-3, f'{name}: price reconstruction off by {maxdiff} bps'
    per_anchor[name] = {'price': price, 'funding': fund, 'fee': fee, 'net': price - fund - fee, 'max_price_diff_bps': maxdiff}
    log('leg', name, 'maxdiff', maxdiff)


def daily(x):
    out = {}
    for d in np.unique((a // DAY) * DAY):
        s = (a >= d) & (a < d + DAY)
        if s.sum() == 6 and np.all(np.isfinite(x[s])):
            out[int(d)] = float(x[s].sum())
    return out


DLY = {n: {c: daily(v[c]) for c in ('price', 'funding', 'fee', 'net')} for n, v in per_anchor.items()}
lb = {}
for n in DLY:
    lb[n] = {'price_reconstruction_max_abs_diff_bps': per_anchor[n]['max_price_diff_bps']}
    for s, (lo, hi) in SEG.items():
        lb[n][s] = {}
        for c in ('price', 'funding', 'fee', 'net'):
            v = np.array([x for d, x in DLY[n][c].items() if lo <= d < hi])
            b = NS.boot(v / 1e4, NS.BLOCK_MAIN)
            lb[n][s][c] = {'mean_bps_per_day': float(v.mean()), 'n_days': int(len(v)), 'ci95': b['ci95_bps']}
rec['single_leg_books'] = lb
rec['single_leg_units'] = 'bps per day per unit gross of a standalone leg book (sum of 6 anchors); fee = 3.52 bps x raw leg turnover (proxy)'

# ── (2) King vs fund leg ─────────────────────────────────────────────────────────────────────
rows2 = []
for k in range(len(a)):
    if not bool(Lg['ready'][k]) or a[k] < SEG['pre2026'][0]:
        continue
    pm = m_all[off[k]:off[k + 1]]; kz, fz = KZ[k, pm].astype(np.float64), ZFD[k, pm].astype(np.float64)
    ok = np.isfinite(kz) & np.isfinite(fz)
    if ok.sum() < 30:
        continue
    kz, fz = kz[ok], fz[ok]; n = len(kz)
    tk, bk = kz >= np.quantile(kz, 2 / 3), kz <= np.quantile(kz, 1 / 3)
    tf, bf = fz >= np.quantile(fz, 2 / 3), fz <= np.quantile(fz, 1 / 3)
    rows2.append({'A': int(a[k]), 'pearson': float(np.corrcoef(kz, fz)[0, 1]), 'spearman': float(spearmanr(kz, fz).statistic),
                  'opposition_share': float(np.mean(np.sign(kz) != np.sign(fz))),
                  'kingTop_in_fundBottom': float(np.mean(bf[tk])), 'kingBottom_in_fundTop': float(np.mean(tf[bk])),
                  'kingTop_in_fundTop': float(np.mean(tf[tk]))})
A2 = np.array([r['A'] for r in rows2])


def months26():
    return [(f'2026-{m:02d}', T(2026, m), T(2026, m + 1)) for m in range(1, 9)] + [('2026-09', T(2026, 9), T(2026, 10))]


cs = {}
for name, lo, hi in [('pre2026',) + SEG['pre2026']] + months26():
    s = (A2 >= lo) & (A2 < hi); cs[name] = {'n_anchors': int(s.sum())}
    for q in ('pearson', 'spearman', 'opposition_share', 'kingTop_in_fundBottom', 'kingBottom_in_fundTop', 'kingTop_in_fundTop'):
        cs[name][q] = float(np.mean([r[q] for r, keep in zip(rows2, s) if keep])) if s.any() else None
    dk, df = DLY['King']['net'], DLY['fund']['net']
    dd = [d for d in dk if lo <= d < hi and d in df]
    if len(dd) >= 10:
        x, y = np.array([dk[d] for d in dd]), np.array([df[d] for d in dd])
        cs[name]['daily_net_corr_King_fund'] = float(np.corrcoef(x, y)[0, 1])
        cs[name]['hedge_beta_King_on_fund'] = float(np.cov(x, y, ddof=1)[0, 1] / np.var(y, ddof=1))
        cs[name]['King_net_sum'], cs[name]['fund_net_sum'] = float(x.sum()), float(y.sum())
        cs[name]['n_days'] = len(dd)
rec['king_vs_fund'] = cs
rec['random_expectation'] = {'pearson': 0.0, 'opposition_share': 0.5, 'tercile_cross_overlap': 1 / 3}

# ── (3a) red-control channels ────────────────────────────────────────────────────────────────
ch = {}


def dsum(A_, x, days):
    """plain per-day SUM for the bps channels (BT.daily COMPOUNDS, which is right for r and wrong for bps channels)"""
    d = (A_ // DAY) * DAY; pos = np.searchsorted(days, d); pos = np.minimum(pos, len(days) - 1)
    ok = days[pos] == d
    return np.bincount(pos[ok], weights=np.asarray(x, float)[ok], minlength=len(days))


for seed in ('42', '2027'):
    Sr, Sa = np.load(f'{MR}/series/SER_RED_m0_s{seed}.npz'), np.load(f'{MR}/series/SER_A0_m0_s{seed}.npz')
    A_ = Sr['anchors'].astype(np.int64); assert np.array_equal(A_, Sa['anchors'].astype(np.int64))
    for S_ in (Sr, Sa):
        err = np.max(np.abs(S_['g_per_path'] - (S_['pnl_per_path'] - S_['car_per_path'] - S_['cst_per_path'] - S_['unk_per_path'])))
        assert err <= 1e-9, ('channel closure', seed, err)
    ch[seed] = {}
    segx = {'pre2026': (T(2023, 6, 30, ), T(2026, 1, 1)), '2026_X': (T(2026, 1, 1), T(2026, 9, 19))}
    for s, (lo, hi) in segx.items():
        m = (A_ >= lo) & (A_ < hi)
        days = NS.full_days(A_, m); ch[seed][s] = {}
        for c in ('r', 'g', 'pnl', 'car', 'cst', 'unk'):
            Dp = []
            for p in range(Sr[f'{c}_per_path'].shape[0]):
                if c == 'r':
                    dr = NS.daily_on(A_[m], Sr[f'{c}_per_path'][p][m], days); da = NS.daily_on(A_[m], Sa[f'{c}_per_path'][p][m], days)
                else:
                    dr = dsum(A_[m], Sr[f'{c}_per_path'][p][m], days); da = dsum(A_[m], Sa[f'{c}_per_path'][p][m], days)
                Dp.append(dr - da)
            D = np.mean(Dp, 0)
            ch[seed][s][c] = float(D.mean() * (1e4 if c == 'r' else 1.0))
        ch[seed][s]['n_days'] = int(len(days))
    ch[seed]['reproduction'] = {s: {'mine_r_dbar': ch[seed][s2]['r'], 'mr_read': MR_READ_DBAR[s][seed],
                                    'match_1e-6': abs(ch[seed][s2]['r'] - MR_READ_DBAR[s][seed]) <= 1e-6}
                                for s, s2 in (('pre2026', 'pre2026'), ('2026', '2026_X'))}
rec['red_minus_A0_channels'] = ch
rec['channel_units'] = 'r: bps/day of NAV (the D-bar of MR_READ); g/pnl/car/cst/unk: bps/day per unit gross, g = pnl - car - cst - unk; car = funding PAID (positive = paid)'
rec['self_sha256'] = sha(os.path.abspath(__file__))
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=float)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('KING_RC DONE out=%s sha256=%s' % (OUT, sha(OUT)), flush=True)
