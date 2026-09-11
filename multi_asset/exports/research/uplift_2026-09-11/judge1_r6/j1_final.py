"""R6 JUDGE-1 FINAL — replay vs realized. PREREG_r6 §4 (sha 7dff6b0b...). Windows corrected to the frozen ends.
Caliber layer: HOLDINGS BOOK.  bps of gross per 4h anchor.
"""
import json, os, time, math, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(f'{HERE}/j1_recon_rows.json')); rows = D['rows']
S2 = np.load(f'{HERE}/j1_symret.npz', allow_pickle=True)
SL = np.load(f'{HERE}/j1_slice.npz', allow_pickle=True)
ts = SL['ts'].astype(np.int64); tpos = {int(t): i for i, t in enumerate(ts)}
y4s = SL['y4s'].astype(np.float64)
N1 = S2['N1'].astype(np.float64); RRl = S2['RR'].astype(np.float64); shave = S2['have']
NB = 2000; SEEDBASE = 20260911
ZK = 2.4977          # Bonferroni K_recon = 4 (PREREG §5 F2)
W = dict(
  W5=(1787716800, 1788998400),   # 2026-08-26 04Z .. 2026-09-10 00Z   (LIVE_COMBO)
  W4=(1785542400, 1788998400),   # 2026-08-01 00Z .. 2026-09-10 00Z   (LIVE_ALL)
  SEP=(1788220800, 1788998400),  # 2026-09-01 00Z .. 2026-09-10 00Z   (never replayed before)
  D1W=(1787716800, 1788120000),  # 2026-08-26 04Z .. 2026-08-30 20Z   (replay book == live book, DL leg alive)
  PRECOMBO=(1785542400, 1787702400),
)
def dayblk(A): return time.strftime('%Y%m%d', time.gmtime(A))
def boot(x, days, k):
    rng = np.random.default_rng([SEEDBASE, k]); da = np.array(days)
    ud = sorted(set(days)); idx = {d: np.where(da == d)[0] for d in ud}
    o = np.empty(NB)
    for b in range(NB):
        p = rng.integers(0, len(ud), len(ud))
        o[b] = x[np.concatenate([idx[ud[q]] for q in p])].mean()
    return float(x.mean()), float(o.std(ddof=1)), [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]
def pair(name, a, b, days, k):
    m = np.isfinite(a) & np.isfinite(b); a = a[m]; b = b[m]; dd = [days[i] for i in np.where(m)[0]]
    n = len(a)
    if n < 5: return dict(name=name, n=n, note='too few')
    rho = float(np.corrcoef(a, b)[0, 1]); z = 0.5*math.log((1+rho)/(1-rho)); se = 1/math.sqrt(n-3)
    lo, hi = math.tanh(z-ZK*se), math.tanh(z+ZK*se)
    sl, ic = np.polyfit(a, b, 1); res = b-(sl*a+ic); s2 = res.var(ddof=2)
    ses = math.sqrt(s2/((a-a.mean())**2).sum()); slo, shi = sl-1.96*ses, sl+1.96*ses
    dm, sd, ci = boot(a-b, dd, k)
    V1 = bool(rho >= 0.60 and lo > 0); V2 = bool(0.7 <= sl <= 1.3 and slo <= 1.0 <= shi); V3 = bool(abs(dm) <= 2*sd)
    if V1 and V2 and V3: v = 'VALIDATED'
    elif rho <= 0.20: v = 'FALSIFIED(rho<=0.20)'
    elif abs(dm) > 3*sd and np.sign(a.mean()) != np.sign(b.mean()): v = 'FALSIFIED(sign+3SE)'
    else: v = 'PARTIAL'
    return dict(name=name, n=n, mean_replay=float(a.mean()), mean_realized=float(b.mean()), rho=rho,
                rho_ci_K4=[lo, hi], slope=float(sl), slope_ci95=[float(slo), float(shi)], intercept=float(ic),
                mean_diff=dm, boot_se=sd, diff_ci95=ci, d_over_se=(dm/sd if sd else float('nan')),
                V1=V1, V2=V2, V3=V3, verdict=v)
RES = {}; k = 0
for wn, (lo, hi) in W.items():
    S = [r for r in rows if lo <= r['A'] <= hi and r.get('realized') and 'D2' in r]
    if len(S) < 5: RES[f'n_{wn}'] = len(S); continue
    days = [dayblk(r['A']) for r in S]
    a = np.array([r['D2']['price_y4s'] for r in S]); b = np.array([r['realized']['price_bps'] for r in S])
    k += 1; RES[f'D2price_{wn}'] = pair(f'D2-price {wn}', a, b, days, k)
    af = np.array([r['D2']['fund_model'] for r in S]); bf = np.array([r['realized']['fund_bps'] for r in S])
    k += 1; RES[f'D2fund_{wn}'] = pair(f'D2-funding {wn}', af, bf, days, k)
    an = a + af; bn = b + bf + np.array([r['realized']['fee_bps'] for r in S])
    k += 1; RES[f'D2net_{wn}'] = pair(f'D2-net {wn} (model price+fund vs realized price+fund+fee)', an, bn, days, k)
    RES[f'n_{wn}'] = len(S)
# D1: replay's own book, ONLY where the replay book is the live book and the DL leg is alive
for arm in ('A0_PWR230k_s42', 'A0_PWR230k_s2027'):
    for wn in ('D1W', 'W4', 'PRECOMBO'):
        lo, hi = W[wn]
        S = [r for r in rows if lo <= r['A'] <= hi and r.get('realized') and arm in r]
        if len(S) < 5: continue
        days = [dayblk(r['A']) for r in S]
        k += 1; RES[f'D1price_{wn}_{arm}'] = pair(f'D1-price {wn} {arm}',
            np.array([r[arm]['price_bps'] for r in S]), np.array([r['realized']['price_bps'] for r in S]), days, k)
        k += 1; RES[f'D1fund_{wn}_{arm}'] = pair(f'D1-funding {wn} {arm}',
            np.array([r[arm]['fund_bps'] for r in S]), np.array([r['realized']['fund_bps'] for r in S]), days, k)
        k += 1; RES[f'D1net_{wn}_{arm}'] = pair(f'D1-net {wn} {arm}',
            np.array([r[arm]['net_bps'] for r in S]),
            np.array([r['realized']['net_bps'] for r in S]), days, k)
        RES[f'n_D1_{wn}_{arm}'] = len(S)
# RETMODEL isolated on the common name set (same weights, same names, two return sources)
RM = {}
for wn, (lo, hi) in W.items():
    sel = [i for i, t in enumerate(ts) if lo <= int(t) <= hi and shave[i]]
    if len(sel) < 5: continue
    x = []
    for i in sel:
        w = N1[i]; rr = RRl[i]; ry = y4s[i]
        m = (np.abs(w) > 0) & np.isfinite(rr) & np.isfinite(ry)
        g = np.abs(w[m]).sum()
        if g <= 0: continue
        x.append(float((w[m]*(rr[m]-ry[m])).sum()/g*1e4))
    x = np.array(x); dd = [dayblk(int(ts[i])) for i in sel][:len(x)]
    k += 1; m_, s_, c_ = boot(x, dd, k)
    RM[wn] = dict(n=len(x), mean=m_, boot_se=s_, ci95=c_)
RES['RETMODEL_same_names'] = RM
json.dump(RES, open(f'{HERE}/j1_final.json', 'w'), indent=1, default=float)
for kk, v in RES.items():
    if not isinstance(v, dict) or 'rho' not in v:
        print(kk, json.dumps(v, default=float) if isinstance(v, dict) else v); continue
    print(f"{kk:34s} n={v['n']:4d} rho={v['rho']:+.4f}[{v['rho_ci_K4'][0]:+.3f},{v['rho_ci_K4'][1]:+.3f}] "
          f"sl={v['slope']:+.3f}[{v['slope_ci95'][0]:+.3f},{v['slope_ci95'][1]:+.3f}] ic={v['intercept']:+.3f} "
          f"mR={v['mean_replay']:+8.4f} mL={v['mean_realized']:+8.4f} d={v['mean_diff']:+7.4f} se={v['boot_se']:6.4f} "
          f"d/se={v['d_over_se']:+6.2f} {int(v['V1'])}{int(v['V2'])}{int(v['V3'])} {v['verdict']}")
