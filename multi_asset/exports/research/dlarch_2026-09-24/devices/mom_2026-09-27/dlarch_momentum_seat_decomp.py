#!/usr/bin/env python3
"""dlarch_momentum_seat_decomp.py -- DESCRIPTIVE ONLY (lead 2026-09-27): after August the book's momentum loading
turned negative. Was it the funding leg losing its positive loading, or the seats moving?

Written and committed BEFORE any reading. Reuses the committed dlarch_momentum_loading.py loaders and 5m prefix
sums verbatim (copied text, same pins). Research replay axis only (ends 2026-09-18T20Z); the live window is
requested from integ separately (this line may not read live files).

THE IDENTITY IT RELIES ON (combo_target.step L28-L32, vendored): before the chain,
  combo_z = 0.55*zkc + 0.45*zfc = w0*(0.55*KZ + 0.45*zf) + w2*ZFD,   w = masked seats (WL0, 0, WL2)/sum,
  zf = uniform rank of the F10 score in [-0.5, 0.5]; KZ, ZFD = the legs the producer passes.
With a COVARIANCE loading L(x) = mean over members of (x - mean x) * z(p_k), this is exactly additive:
  L(combo_z) = T_K + T_F10 + T_FUND,  T_K = w0*0.55*L(KZ), T_F10 = w0*0.45*L(zf), T_FUND = w2*L(ZFD)
and the device ASSERTS the identity per anchor (|L(combo_z) - sum| <= 1e-12). Additivity holds only at this
pre-chain layer; the rn8 clamp and the chain (EMA / band / cap / renorm) are NOT linear, so the post-chain
book loading is reported beside it and never decomposed.
The August turn is then split, per k, with segment means (base = 2026-01..07, post = 2026-08 and 2026-09):
  loadings-only  = S(base seats, post leg loadings) - S(base)
  seats-only     = S(post seats, base leg loadings) - S(base)
  interaction    = total - loadings-only - seats-only      (reported; the two one-at-a-time terms do NOT add)
  fund-only      = S(base seats, base L_K, base L_F10, post L_FUND) - S(base)

usage: dlarch_momentum_seat_decomp.py <env-whitelist> <out.json>
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



F10P = f'{NS2}/work/f10_s42/F10_OOF.npz'
f10 = np.load(F10P); assert np.array_equal(f10['E_ts'].astype(np.int64), a)
P10 = f10['P']; WLs = Lg['WL']
cpos_ok = cpos >= 0
rows = []
for j, A in enumerate(CE):
    i = aidx.get(int(A))
    if i is None or not bool(Lg['ready'][i]):
        continue
    mem = m_all[off[i]:off[i + 1]]
    wl = WLs[i].astype(np.float64); s = wl[0] + wl[2]
    if not np.isfinite(s) or s <= 1e-12:
        continue
    w0, w2 = wl[0] / s, wl[2] / s
    kz = np.nan_to_num(KZ[i, mem].astype(np.float64)); fz = np.nan_to_num(ZFD[i, mem].astype(np.float64))
    sc = P10[i, mem].astype(np.float64); okf = np.isfinite(sc); zf = np.full(len(mem), np.nan)
    zf[okf] = rankdata(sc[okf]) / max(okf.sum() - 1, 1) - .5; zf = np.nan_to_num(zf)
    combo = w0 * (0.55 * kz + 0.45 * zf) + w2 * fz
    r = {'A': int(A), 'w0': w0, 'w2': w2}
    for k in KS:
        p = past_ret(int(A), k, mem); ok = np.isfinite(p)
        if ok.sum() < 20:
            for q in ('LK', 'LF10', 'LFUND', 'TK', 'TF10', 'TFUND', 'S'):
                r[f'{q}_k{k}'] = np.nan
            continue
        zp = (p[ok] - p[ok].mean()) / (p[ok].std() + 1e-12)
        L = lambda x: float(np.mean((x[ok] - x[ok].mean()) * zp))
        LK, LF10, LFUND = L(kz), L(zf), L(fz)
        TK, TF10, TFUND = w0 * 0.55 * LK, w0 * 0.45 * LF10, w2 * LFUND
        S = L(combo)
        assert abs(S - (TK + TF10 + TFUND)) <= 1e-12, ('additivity identity broken', int(A), S, TK + TF10 + TFUND)
        r.update({f'LK_k{k}': LK, f'LF10_k{k}': LF10, f'LFUND_k{k}': LFUND, f'TK_k{k}': TK, f'TF10_k{k}': TF10,
                  f'TFUND_k{k}': TFUND, f'S_k{k}': S})
    rows.append(r)
    if j % 2000 == 0:
        log('anchor', j, '/', len(CE))
keys = [k for k in rows[0] if k != 'A']
Aarr = np.array([r['A'] for r in rows]); M = {k: np.array([r[k] for r in rows], float) for k in keys}
SEGS = [('pre2026', T(2023, 7), T(2026, 1))] + [(f'2026-{mo:02d}', T(2026, mo), T(2026, mo + 1)) for mo in range(1, 10)] + \
       [('base_2026-01..07', T(2026, 1), T(2026, 8)), ('post_2026-08', T(2026, 8), T(2026, 9)), ('post_2026-09', T(2026, 9), T(2026, 10))]
seg = {}
for name, lo, hi in SEGS:
    s = (Aarr >= lo) & (Aarr < hi)
    seg[name] = {'n_anchors': int(s.sum())}
    for q in keys:
        seg[name][q] = float(np.nanmean(M[q][s])) if s.any() else None
rec = {'device': 'dlarch_momentum_seat_decomp.py', 'inputs': dict(PIN, combo=sha(COMBO), f10=sha(F10P)), 'descriptive_only': True,
       'identity_asserted_per_anchor': 'L(combo_z) == T_K + T_F10 + T_FUND within 1e-12 (pre-chain, pre-clamp)',
       'segments': seg}


def Sfun(w0, w2, LK, LF10, LFUND):
    return w0 * (0.55 * LK + 0.45 * LF10) + w2 * LFUND


split = {}
b = seg['base_2026-01..07']
for post in ('post_2026-08', 'post_2026-09'):
    q = seg[post]; split[post] = {}
    for k in KS:
        g = lambda d, n: d[f'{n}_k{k}']
        base = Sfun(b['w0'], b['w2'], g(b, 'LK'), g(b, 'LF10'), g(b, 'LFUND'))
        tot = Sfun(q['w0'], q['w2'], g(q, 'LK'), g(q, 'LF10'), g(q, 'LFUND')) - base
        lo_ = Sfun(b['w0'], b['w2'], g(q, 'LK'), g(q, 'LF10'), g(q, 'LFUND')) - base
        se_ = Sfun(q['w0'], q['w2'], g(b, 'LK'), g(b, 'LF10'), g(b, 'LFUND')) - base
        fo_ = Sfun(b['w0'], b['w2'], g(b, 'LK'), g(b, 'LF10'), g(q, 'LFUND')) - base
        split[post][f'k{k}'] = {'S_base': base, 'S_post': base + tot, 'total_change': tot, 'loadings_only': lo_,
                                'seats_only': se_, 'interaction': tot - lo_ - se_, 'fund_loading_only': fo_}
rec['august_turn_split'] = split
rec['note'] = 'one-at-a-time substitutions do NOT add up; the interaction term is printed so the reader sees the gap'
rec['self_sha256'] = sha(os.path.abspath(__file__))
with open(OUT, 'w') as f:
    json.dump(rec, f, indent=1, sort_keys=True, default=float)
with open(OUT) as f:
    assert json.load(f)['self_sha256'] == rec['self_sha256']
print('MOM_SEAT_DECOMP DONE out=%s sha256=%s' % (OUT, sha(OUT)), flush=True)
