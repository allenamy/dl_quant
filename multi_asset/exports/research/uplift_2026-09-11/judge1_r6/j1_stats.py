"""R6 JUDGE-1 statistics: V1/V2/V3, paired tests, decomposition. PREREG §4.2 thresholds frozen before any reading."""
import json, os, time, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(f'{HERE}/j1_recon_rows.json'))
rows = D['rows']
NB = 2000; SEEDBASE = 20260911
W5 = (1787716800, 1789056000); W4 = (1785542400, 1789056000); D1_HI = 1788969600

def dayblk(A): return time.strftime('%Y%m%d', time.gmtime(A))

def boot_mean(x, days, k):
    """UTC day-block bootstrap of the mean. rng = default_rng([SEEDBASE, k])."""
    rng = np.random.default_rng([SEEDBASE, k])
    ud = sorted(set(days)); idx = {d: np.where(np.array(days) == d)[0] for d in ud}
    out = np.empty(NB)
    for b in range(NB):
        pick = rng.integers(0, len(ud), len(ud))
        sel = np.concatenate([idx[ud[p]] for p in pick])
        out[b] = x[sel].mean()
    return out

def rep(name, a, b, days, k):
    """a = replay/model, b = realized. Returns V1/V2/V3 readings."""
    m = np.isfinite(a) & np.isfinite(b)
    a = a[m]; b = b[m]; dd = [days[i] for i in np.where(m)[0]]
    n = len(a)
    if n < 5: return dict(name=name, n=n, note='too few')
    rho = float(np.corrcoef(a, b)[0, 1])
    z = 0.5 * math.log((1 + rho) / (1 - rho)); sez = 1 / math.sqrt(n - 3)
    zK = 2.4977   # Bonferroni K_recon = 4, two-sided (PREREG §5 F2)
    lo_r = math.tanh(z - zK * sez); hi_r = math.tanh(z + zK * sez)
    sl, ic = np.polyfit(a, b, 1)
    resid = b - (sl * a + ic); s2 = resid.var(ddof=2)
    se_sl = math.sqrt(s2 / ((a - a.mean()) ** 2).sum())
    sl_lo, sl_hi = sl - 1.96 * se_sl, sl + 1.96 * se_sl
    dmean = float(a.mean() - b.mean())
    bm = boot_mean(a - b, dd, k)
    se_d = float(bm.std(ddof=1))
    return dict(name=name, n=n, mean_replay=float(a.mean()), mean_realized=float(b.mean()),
                rho=rho, rho_lo_K4=lo_r, rho_hi_K4=hi_r,
                slope=float(sl), slope_ci=[float(sl_lo), float(sl_hi)], intercept=float(ic),
                mean_diff=dmean, boot_se=se_d, diff_over_se=(dmean / se_d if se_d else float('nan')),
                diff_ci95=[float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))],
                V1=bool(rho >= 0.60 and lo_r > 0), V2=bool(0.7 <= sl <= 1.3 and sl_lo <= 1.0 <= sl_hi),
                V3=bool(abs(dmean) <= 2 * se_d))

def verdict(r):
    if r.get('note'): return 'N/A'
    if r['V1'] and r['V2'] and r['V3']: return 'VALIDATED'
    if r['rho'] <= 0.20: return 'FALSIFIED(rho)'
    if abs(r['mean_diff']) > 3 * r['boot_se'] and np.sign(r['mean_replay']) != np.sign(r['mean_realized']): return 'FALSIFIED(sign+mag)'
    if r['rho'] >= 0.60: return 'PARTIAL'
    if 0.20 < r['rho'] < 0.60: return 'PARTIAL'
    return 'PARTIAL'

def sub(lo, hi, need):
    return [r for r in rows if lo <= r['A'] <= hi and all(k in r and r[k] is not None for k in need)]

RES = {}
k = 0
for wn, (lo, hi) in (('W5', W5), ('W4', W4)):
    # ---- D2-price ----
    S = [r for r in rows if lo <= r['A'] <= hi and r.get('realized') and 'D2' in r]
    a = np.array([r['D2']['price_y4s'] for r in S]); b = np.array([r['realized']['price_bps'] for r in S])
    days = [dayblk(r['A']) for r in S]
    k += 1; RES[f'D2price_{wn}'] = rep(f'D2-price {wn}', a, b, days, k); RES[f'D2price_{wn}']['verdict'] = verdict(RES[f'D2price_{wn}'])
    # robustness on the device's own y4 (CAL=log)
    a2 = np.array([r['D2']['price_y4meta'] for r in S])
    k += 1; RES[f'D2price_y4meta_{wn}'] = rep(f'D2-price(y4_meta) {wn}', a2, b, days, k); RES[f'D2price_y4meta_{wn}']['verdict'] = verdict(RES[f'D2price_y4meta_{wn}'])
    # ---- D2-funding ----
    af = np.array([r['D2']['fund_model'] for r in S]); bf = np.array([r['realized']['fund_bps'] for r in S])
    k += 1; RES[f'D2fund_{wn}'] = rep(f'D2-funding {wn}', af, bf, days, k); RES[f'D2fund_{wn}']['verdict'] = verdict(RES[f'D2fund_{wn}'])
    RES[f'_n_{wn}'] = len(S)

# ---- D1: replay's own book vs realized (descriptive, PREREG §4.1) ----
for nm in ('A0_PWR230k_s42', 'A0_PWR230k_s2027'):
    S = [r for r in rows if W4[0] <= r['A'] <= D1_HI and r.get('realized') and nm in r]
    days = [dayblk(r['A']) for r in S]
    a = np.array([r[nm]['price_bps'] for r in S]); b = np.array([r['realized']['price_bps'] for r in S])
    k += 1; RES[f'D1price_{nm}'] = rep(f'D1-price {nm} (2026-08-01..08-30 20Z)', a, b, days, k)
    an = np.array([r[nm]['net_bps'] for r in S]); bn = np.array([r['realized']['net_bps'] for r in S])
    k += 1; RES[f'D1net_{nm}'] = rep(f'D1-net {nm}', an, bn, days, k)
    af = np.array([r[nm]['fund_bps'] for r in S]); bf = np.array([r['realized']['fund_bps'] for r in S])
    k += 1; RES[f'D1fund_{nm}'] = rep(f'D1-funding {nm}', af, bf, days, k)
    RES[f'_D1n_{nm}'] = len(S)
    # combo-era-only slice
    Sc = [r for r in S if r['A'] >= W5[0]]
    if len(Sc) >= 5:
        dc = [dayblk(r['A']) for r in Sc]
        k += 1; RES[f'D1price_combo_{nm}'] = rep(f'D1-price {nm} combo-era only', np.array([r[nm]['price_bps'] for r in Sc]),
                                                 np.array([r['realized']['price_bps'] for r in Sc]), dc, k)
        RES[f'_D1n_combo_{nm}'] = len(Sc)

json.dump(RES, open(f'{HERE}/j1_stats.json', 'w'), indent=1, default=float)
for kk, v in RES.items():
    if kk.startswith('_'): print(kk, v); continue
    if v.get('note'): print(kk, v); continue
    print(f"{kk:26s} n={v['n']:4d} rho={v['rho']:+.4f} [{v['rho_lo_K4']:+.3f},{v['rho_hi_K4']:+.3f}] "
          f"slope={v['slope']:+.3f} [{v['slope_ci'][0]:+.3f},{v['slope_ci'][1]:+.3f}] icpt={v['intercept']:+.3f} "
          f"mR={v['mean_replay']:+.4f} mL={v['mean_realized']:+.4f} d={v['mean_diff']:+.4f} se={v['boot_se']:.4f} "
          f"d/se={v['diff_over_se']:+.2f} V1={int(v['V1'])} V2={int(v['V2'])} V3={int(v['V3'])} {v.get('verdict','')}")
