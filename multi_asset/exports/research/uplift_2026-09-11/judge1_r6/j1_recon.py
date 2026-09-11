"""R6 JUDGE-1 — replay vs realized, anchor by anchor.  PREREG §4 (sha 7dff6b0b...).
Caliber layer: HOLDINGS BOOK (g = pnl / gross, bps per 4h anchor, per unit gross).
D1 = replay's own book vs realized.   D2 = deployed weights scored through the replay return series vs realized.
Return series: y4s = prod(1+r)-1 (pod_dlw_targets lineage, E-0904-F; NO expm1).  Robustness: y4_meta (what the CAL=log device uses).
Bootstrap: UTC day blocks, 2000 draws, rng default_rng([20260911, k]).
"""
import json, os, time, hashlib
import numpy as np
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_WHITELIST = ['J1_NBOOT','J1_SEEDBASE']
ENV = {k: os.environ.get(k) for k in ENV_WHITELIST}
NB = int(os.environ.get('J1_NBOOT', '2000')); SEEDBASE = int(os.environ.get('J1_SEEDBASE', '20260911'))

Z = np.load(f'{HERE}/j1_slice.npz', allow_pickle=True)
ts = Z['ts'].astype(np.int64); SYM = [str(s) for s in Z['symbols']]
y4s = Z['y4s'].astype(np.float64); y4m = Z['y4_meta'].astype(np.float64)
fnow = Z['fnow'].astype(np.float64); fiv = Z['fiv'].astype(np.float64)
IVv = np.where(np.isfinite(fiv) & (fiv > 0), fiv, 8.0)
sidx = {s: i for i, s in enumerate(SYM)}
tidx = {int(t): i for i, t in enumerate(ts)}

RE = json.load(open(f'{HERE}/j1_realized.json'))
rows = {r['A']: r for r in RE['rows']}
WD = json.load(open(f'{HERE}/j1_w_deployed.json'))
WR = json.load(open(f'{HERE}/j1_w_realized.json'))

def vec(d):
    v = np.zeros(len(SYM)); miss = 0.0; tot = 0.0
    for s, w in d.items():
        tot += abs(float(w))
        j = sidx.get(s)
        if j is None: miss += abs(float(w)); continue
        v[j] += float(w)
    return v, (miss / tot if tot > 0 else 0.0)

def score(w, r):
    """per-unit-gross return in bps, using only names where r is finite; renormalise on that set."""
    ok = np.isfinite(r) & (np.abs(w) > 0)
    g = np.abs(w[ok]).sum()
    if g <= 0: return np.nan, 0.0, 0.0
    gall = np.abs(w).sum()
    return float((w[ok] * r[ok]).sum() / g * 1e4), float(g / gall), float(ok.sum())

W5_LO, W5_HI = 1787716800, 1789056000          # 2026-08-26 04Z .. 2026-09-10 00Z
W4_LO, W4_HI = 1785542400, 1789056000          # 2026-08-01 00Z .. 2026-09-10 00Z
D1_HI = 1788969600                              # 2026-08-30 20Z: last anchor with a finite DL leg (E-0911-B)

REC = {}
for nm in ('A0_PWR230k_s42', 'A0_PWR230k_s2027'):
    R = Z[f'{nm}_rec']; have = Z[f'{nm}_have']
    cols = [str(c) for c in Z['cols']]
    REC[nm] = dict(R=R, have=have, c={c: i for i, c in enumerate(cols)})

out_rows = []
for i, t in enumerate(ts):
    t = int(t)
    rr = rows.get(t)
    d = dict(A=t, utc=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(t)))
    d['realized'] = None if rr is None else dict(
        price_bps=rr['price_bps'], fund_bps=rr['fund_bps'], fee_bps=rr['fee_bps'],
        timing_bps=rr['timing_bps'], net_bps=rr['net_bps'], gross=rr['gross'],
        booster=rr['dep_booster'], producer=rr['dep_producer'], regime=rr['regime'])
    rY = y4s[i]; rM = y4m[i]
    # deployed weights scored through the replay return series  (D2)
    wd = WD.get(str(t))
    if wd is not None:
        v, miss = vec(wd)
        g, cov, nn = score(v, rY)
        gm, _, _ = score(v, rM)
        carry = -float((v * np.nan_to_num(fnow[i]) * (4.0 / IVv[i])).sum() / max(np.abs(v).sum(), 1e-12) * 1e4)
        d['D2'] = dict(price_y4s=g, price_y4meta=gm, fund_model=carry,
                       w_missing_frac=miss, ret_cov=cov, n_names=int(nn), gross_norm=float(np.abs(v).sum()))
    # actually-held weights scored through the replay return series
    wr = WR.get(str(t))
    if wr is not None:
        v2, miss2 = vec(wr)
        g2, cov2, nn2 = score(v2, rY)
        carry2 = -float((v2 * np.nan_to_num(fnow[i]) * (4.0 / IVv[i])).sum() / max(np.abs(v2).sum(), 1e-12) * 1e4)
        d['HELD'] = dict(price_y4s=g2, fund_model=carry2, w_missing_frac=miss2, ret_cov=cov2, n_names=int(nn2))
    # replay's own book (D1)
    for nm, R in REC.items():
        if not R['have'][i]: continue
        c = R['c']; r = R['R'][i]
        gt = r[c['gross_total']]
        d[nm] = dict(net_bps=r[c['net_ex']] / gt, price_bps=r[c['pnl_ex']] / gt,
                     fund_bps=-r[c['carry_ex']] / gt, cost_bps=-r[c['cost_ex']] / gt,
                     gross_total=gt, turnover=r[c['turnover']], nsel=r[c['nsel']],
                     w3=[r[c['w3_king']], r[c['w3_rev24']], r[c['w3_fund']]])
    out_rows.append(d)

json.dump(dict(meta=dict(read_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                         env_effective=ENV, nboot=NB, seedbase=SEEDBASE,
                         slice_sha256=hashlib.sha256(open(f'{HERE}/j1_slice.npz','rb').read()).hexdigest()[:16],
                         self_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest()),
               rows=out_rows), open(f'{HERE}/j1_recon_rows.json','w'), indent=1)
print('rows', len(out_rows), 'with realized', sum(1 for r in out_rows if r['realized']),
      'with D2', sum(1 for r in out_rows if 'D2' in r), 'with A0 replay', sum(1 for r in out_rows if 'A0_PWR230k_s42' in r))
