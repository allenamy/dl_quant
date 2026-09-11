#!/usr/bin/env python3
"""r12 · per-regime measurement of the INCUMBENT book (A0, dynamic seat).

Partition rules are frozen in ../PREREG_r12_regime_partition_2026-09-12.md
(sha256 e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c), written before this ran.

Book series  : ../r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz  (sha256 352ac36f…)
Device of it : ../trackA/w10_sleeve.py  (sha256 b88e35a46b93d712… = CALIBER PIN)
Causal gauges: receipts/causal_primitives_r12.npz (pod_causal_regime_r12.py 7eb31945…)

g = net_ex/gross_total, bps per 4h anchor per unit gross.
W_ALPHA = drop first 900 (E-0911-A) AND ts<=2026-08-30 20Z (E-0911-D) -> n=9138   [alpha only]
W_TAIL  = ts<=2026-08-30 20Z, NO warm drop                            -> n=10038  [tail/halt only]
"""
import sys, os, json, time, calendar, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))      # r12_regime
U = os.path.abspath(os.path.join(R, '..'))                              # uplift_2026-09-11
def sha(p, n=64):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]

BOOK = f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
DEV  = f"{U}/trackA/w10_sleeve.py"
PRIM = f"{R}/receipts/causal_primitives_r12_v2.npz"
PRE  = f"{R}/PREREG_r12_regime_partition_2026-09-12.md"
SHAS = {os.path.relpath(p, U): sha(p) for p in (BOOK, DEV, PRIM, PRE)}
assert SHAS['trackA/w10_sleeve.py'] == 'b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650', SHAS
assert SHAS['r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz'] == '352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339', SHAS
assert SHAS['r12_regime/PREREG_r12_regime_partition_2026-09-12.md'] == 'e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c', SHAS

# ---------------------------------------------------------------- book
Z = np.load(BOOK, allow_pickle=True); C = [str(c) for c in Z['cols']]; RC = Z['rec']
cfg = json.loads(str(Z['config_json']))
assert cfg['CAL'] == 'log' and cfg['PHI'] == 0.45 and cfg['LEGS'] == '101' and cfg['WRULE'] == 'msharpe' \
   and cfg['W3FIX'] is None and cfg['UMASK_SCOPE'] == 'm1' and cfg['LOOK'] == 900, cfg
assert cfg['UPLIFT']['self_sha256'] == SHAS['trackA/w10_sleeve.py']
col = lambda k: RC[:, C.index(k)].astype(float)
ts   = col('ts').astype(np.int64)
gt   = col('gross_total')
g    = col('net_ex') / gt                      # THE statistic
pnl  = col('pnl_ex') / gt                      # price
car  = col('carry_ex') / gt                    # funding PAID (>0 = book pays)
cst  = col('cost_ex') / gt
turn_raw = col('turnover'); turn = turn_raw / gt
lk, lf, lr = col('leg_king'), col('leg_fund'), col('leg_rev24')
w3k, w3f   = col('w3_king'), col('w3_fund')
nlong      = col('netlong')
assert np.allclose(pnl - car - cst, g, atol=1e-9)

# ---------------------------------------------------------------- causal gauges (meta grid)
P = np.load(PRIM); PC = [str(c) for c in P['cols']]; PR = P['rec']
pcol = lambda k: PR[:, PC.index(k)].astype(float)
mts = PR[:, 0].astype(np.int64)
dts = np.diff(mts); assert set(np.unique(dts).tolist()) == {14400}, np.unique(dts)[:5]
A, B, D = pcol('A_ew'), pcol('B_breadth'), pcol('D_disp_bps')
SIGF, FMED, SPAY = pcol('SIGF'), pcol('FMED'), pcol('SPAY')
PL, PS, CL, CS = pcol('pnl_long'), pcol('pnl_short'), pcol('car_long'), pcol('car_short')
GSL, GSS = pcol('gshare_long'), pcol('gshare_short')

def trail_mean(x, k):
    """mean of x[i-k .. i-1] — strictly causal, NaN before k history."""
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        n = cn[i] - cn[i - k]
        if n >= k * 0.8: out[i] = (cs[i] - cs[i - k]) / n
    return out
def trail_sum(x, k):
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        if cn[i] - cn[i - k] >= k * 0.8: out[i] = cs[i] - cs[i - k]
    return out
def trail_sd(x, k):
    out = np.full(len(x), np.nan)
    for i in range(k, len(x)):
        w = x[i - k:i]; w = w[np.isfinite(w)]
        if len(w) >= k * 0.8: out[i] = w.std()
    return out

BRD6  = trail_mean(B, 6)            # trailing-24h breadth
XSV30 = trail_mean(D, 30)           # trailing-5d cross-sectional dispersion, bps
MV30  = trail_sd(A, 30) * 1e4       # trailing-5d realised vol of the EW market factor, bps
R24   = trail_sum(A, 6)
R72   = trail_sum(A, 18)
mrow = {int(t): i for i, t in enumerate(mts)}
take = np.array([mrow[int(t)] for t in ts])
BRD6, XSV30, MV30, R24, R72 = (v[take] for v in (BRD6, XSV30, MV30, R24, R72))
SIGF, FMED, SPAY = (v[take] for v in (SIGF, FMED, SPAY))
PL, PS, CL, CS, GSL, GSS = (v[take] for v in (PL, PS, CL, CS, GSL, GSS))
PL, PS, CL, CS = PL/gt, PS/gt, CL/gt, CS/gt          # per unit gross, file caliber
_dp=float(np.abs((PL+PS)-col('pnl')/gt).max()); _dc=float(np.abs((CL+CS)-col('carry')/gt).max())
assert _dp < 1e-4 and _dc < 1e-5, ('halves parity', _dp, _dc)
HALVES_PARITY=(_dp,_dc)

# ---------------------------------------------------------------- windows
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
W_TAIL  = ts <= UB
W_ALPHA = W_TAIL.copy(); W_ALPHA[:900] = False
assert W_ALPHA.sum() == 9138 and W_TAIL.sum() == 10038, (W_ALPHA.sum(), W_TAIL.sum())
xa = g[W_ALPHA]
assert abs(xa.mean() - 0.6341957) < 5e-7 and abs(xa.mean() / xa.std(ddof=1) * np.sqrt(2190) - 1.2912234) < 5e-7
assert abs(turn_raw[W_ALPHA].mean() - 0.03032) < 5e-6 and abs(turn[W_ALPHA].mean() - 0.0540270) < 5e-7
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
day  = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])

# ---------------------------------------------------------------- cells (cuts on W_ALPHA, applied to both)
def terc(v, w=W_ALPHA):
    q = np.nanpercentile(v[w], [100/3, 200/3]); return q
def band(v, q):
    lab = np.full(len(v), -1)
    lab[np.isfinite(v) & (v <= q[0])] = 0
    lab[np.isfinite(v) & (v > q[0]) & (v <= q[1])] = 1
    lab[np.isfinite(v) & (v > q[1])] = 2
    return lab
QB, QX, QM, QS = terc(BRD6), terc(XSV30), terc(MV30), terc(SIGF)
Q_FMED_D1 = np.nanpercentile(FMED[W_ALPHA], 10)
Q_SPAY_D9 = np.nanpercentile(SPAY[W_ALPHA], 90)
LB, LX, LM, LS = band(BRD6, QB), band(XSV30, QX), band(MV30, QM), band(SIGF, QS)

CELLS = []   # (family, label, boolean mask)
for y in sorted(set(year[W_TAIL].tolist())):
    CELLS.append(('a_YEAR', str(y), year == y))
for t, nm in [(0, 'T1 narrowest'), (1, 'T2'), (2, 'T3 broadest')]:
    CELLS.append(('b_BREADTH(trail24h)', nm, LB == t))
for t, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]:
    CELLS.append(('c_XSVOL(trail5d disp)', nm, LX == t))
for t, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]:
    CELLS.append(('c2_MKTVOL(trail5d EW sd)', nm, LM == t))
for t, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]:
    CELLS.append(('d_SIGF(fund disp)', nm, LS == t))
E = {}
E['POSTCRASH R24<=-2%']        = np.isfinite(R24) & (R24 <= -0.02)
E['~POSTCRASH']                = np.isfinite(R24) & (R24 > -0.02)
E['BROADRALLY R24>=+2%&B>=.60']= np.isfinite(R24) & np.isfinite(BRD6) & (R24 >= 0.02) & (BRD6 >= 0.60)
E['~BROADRALLY']               = np.isfinite(R24) & np.isfinite(BRD6) & ~E['BROADRALLY R24>=+2%&B>=.60']
E['ALTSURGE R72>=+8%']         = np.isfinite(R72) & (R72 >= 0.08)
E['~ALTSURGE']                 = np.isfinite(R72) & (R72 < 0.08)
E['ALTSURGE_BROAD']            = E['ALTSURGE R72>=+8%'] & np.isfinite(BRD6) & (BRD6 >= 0.60)
E['DEEPNEG_MKT (FMED d1)']     = np.isfinite(FMED) & (FMED <= Q_FMED_D1)
E['~DEEPNEG_MKT']              = np.isfinite(FMED) & (FMED > Q_FMED_D1)
E['DEEPNEG_SHORT (SPAY d10)']  = np.isfinite(SPAY) & (SPAY >= Q_SPAY_D9)
E['~DEEPNEG_SHORT']            = np.isfinite(SPAY) & (SPAY < Q_SPAY_D9)
for k, v in E.items(): CELLS.append(('e_EVENT', k, v))
for lo, hi, nm in [(-9, -0.04, 'R72 < -4%'), (-0.04, 0.0, 'R72 -4%..0'), (0.0, 0.04, 'R72 0..+4%'),
                   (0.04, 0.08, 'R72 +4..+8%'), (0.08, 0.15, 'R72 +8..+15%'), (0.15, 9, 'R72 >= +15%')]:
    CELLS.append(('e2_R72 ladder', nm, np.isfinite(R72) & (R72 >= lo) & (R72 < hi)))

# ---------------------------------------------------------------- statistics
NB = 2000
def boot_ci(mask):
    idx = np.nonzero(mask & W_ALPHA)[0]
    if len(idx) < 10: return (np.nan, np.nan, np.nan)
    dd = {}
    for k in idx: dd.setdefault(day[k], []).append(k)
    keys = sorted(dd); byday = [np.array(dd[k]) for k in keys]; nd = len(keys)
    tot = np.array([g[b].sum() for b in byday]); cnt = np.array([len(b) for b in byday], float)
    ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        ms[k] = tot[r].sum() / cnt[r].sum()
    return float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5)), float(ms.std(ddof=1))

def dayret(mask, L=2.0):
    """full-day book return for UTC days whose anchors are >=4/6 inside `mask` (within W_TAIL)."""
    allday = {}
    for k in np.nonzero(W_TAIL)[0]: allday.setdefault(day[k], []).append(k)
    pure, mix = [], 0
    for dd, ks in sorted(allday.items()):
        inc = sum(1 for k in ks if mask[k])
        if inc >= 4 and inc >= len(ks) * 0.6:
            pure.append((dd, float(np.prod(1.0 + L * g[np.array(ks)] * 1e-4) - 1.0)))
        elif inc > 0: mix += 1
    return pure, mix

def cellDD(mask, L=2.0):
    """maxDD of the regime-conditional equity curve: cell anchors in time order, compounded at L.
       NOT a tradable drawdown (the book is not flat outside the cell)."""
    idx = np.nonzero(mask & W_TAIL)[0]
    if len(idx) < 5: return np.nan
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * g[idx] * 1e-4)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())

OUT = []
for fam, lab, mk in CELLS:
    a = mk & W_ALPHA; t = mk & W_TAIL
    n = int(a.sum())
    if n < 30:
        OUT.append(dict(family=fam, cell=lab, n=n, note='too few')); continue
    x = g[a]; m = float(x.mean()); sd = float(x.std(ddof=1))
    sh = m / sd * np.sqrt(2190); se = float(np.sqrt(2190 / n))
    lo, hi, bse = boot_ci(mk)
    pure, mix = dayret(mk)
    dr = np.array([p[1] for p in pure]) if pure else np.array([])
    wd = min(pure, key=lambda p: p[1]) if pure else ('-', np.nan)
    OUT.append(dict(family=fam, cell=lab, n=n, n_tail=int(t.sum()),
        mean_g=m, ci_lo=lo, ci_hi=hi, boot_se=bse,
        sharpe=float(sh), sharpe_se=se, sharpe_lo=float(sh - 1.96 * se), sharpe_hi=float(sh + 1.96 * se),
        pnl=float(pnl[a].mean()), carry_paid=float(car[a].mean()), cost=float(cst[a].mean()),
        turn_matched=float(turn[a].mean()), turn_raw=float(turn_raw[a].mean()),
        leg_king=float(lk[a].mean()), leg_fund=float(lf[a].mean()),
        w3_fund=float(w3f[a].mean()), netlong=float(nlong[a].mean()), gross=float(gt[a].mean()),
        SIGF=float(np.nanmean(SIGF[a])), FMED=float(np.nanmean(FMED[a])),
        SPAY=float(np.nanmean(SPAY[a])), BRD6=float(np.nanmean(BRD6[a])), R24=float(np.nanmean(R24[a])),
        maxDD_cond=cellDD(mk), n_days_pure=len(pure), n_days_mixed=mix,
        worst_day=wd[0], worst_day_ret=float(wd[1]) if pure else np.nan,
        halt4=int((dr <= -0.04).sum()) if len(dr) else 0,
        halt4_per_yr=float((dr <= -0.04).sum() / (len(dr) / 365)) if len(dr) else np.nan,
        alert268=int((dr <= -0.0268).sum()) if len(dr) else 0,
        alert268_per_yr=float((dr <= -0.0268).sum() / (len(dr) / 365)) if len(dr) else np.nan))

# expanding-window causal tercile assignment for BREADTH (robustness)
LBc = np.full(len(ts), -1)
for i in range(900, len(ts)):
    h = BRD6[:i][np.isfinite(BRD6[:i])]
    if len(h) < 900 or not np.isfinite(BRD6[i]): continue
    q1, q2 = np.percentile(h, [100/3, 200/3])
    LBc[i] = 0 if BRD6[i] <= q1 else (1 if BRD6[i] <= q2 else 2)
EXP = []
for t_, nm in [(0, 'T1 narrowest'), (1, 'T2'), (2, 'T3 broadest')]:
    a = (LBc == t_) & W_ALPHA; n = int(a.sum())
    if n < 30: continue
    x = g[a]; sh = x.mean() / x.std(ddof=1) * np.sqrt(2190); se = np.sqrt(2190 / n)
    lo, hi, _ = boot_ci(LBc == t_)
    EXP.append(dict(cell=nm, n=n, mean_g=float(x.mean()), ci_lo=lo, ci_hi=hi,
                    sharpe=float(sh), sharpe_se=float(se), sharpe_lo=float(sh - 1.96 * se)))

# worst anchors / worst days with their regime state
ordA = np.argsort(g + np.where(W_TAIL, 0, 1e9))[:20]
WORST_A = [dict(ts=int(ts[i]), utc=time.strftime('%Y-%m-%d %HZ', time.gmtime(int(ts[i]))), g=float(g[i]),
                pnl=float(pnl[i]), carry_paid=float(car[i]), cost=float(cst[i]),
                leg_king=float(lk[i]), leg_fund=float(lf[i]), w3_fund=float(w3f[i]), netlong=float(nlong[i]),
                BRD6=float(BRD6[i]), R24=float(R24[i]), R72=float(R72[i]), SIGF=float(SIGF[i]),
                FMED=float(FMED[i]), SPAY=float(SPAY[i]), XSV30=float(XSV30[i]),
                postwarm=bool(W_ALPHA[i])) for i in ordA]
allday = {}
for k in np.nonzero(W_TAIL)[0]: allday.setdefault(day[k], []).append(k)
DR = sorted(((dd, float(np.prod(1.0 + 2.0 * g[np.array(ks)] * 1e-4) - 1.0), ks) for dd, ks in allday.items()),
            key=lambda z: z[1])[:20]
WORST_D = [dict(day=dd, ret2x=r, n=len(ks),
                pnl=float(pnl[np.array(ks)].mean()), carry_paid=float(car[np.array(ks)].mean()),
                cost=float(cst[np.array(ks)].mean()), g=float(g[np.array(ks)].mean()),
                leg_king=float(lk[np.array(ks)].mean()), leg_fund=float(lf[np.array(ks)].mean()),
                BRD6=float(np.nanmean(BRD6[np.array(ks)])), R24=float(np.nanmean(R24[np.array(ks)])),
                R72=float(np.nanmean(R72[np.array(ks)])), SPAY=float(np.nanmean(SPAY[np.array(ks)])),
                FMED=float(np.nanmean(FMED[np.array(ks)])),
                postwarm=bool(W_ALPHA[np.array(ks)].all())) for dd, r, ks in DR]

CUTS = dict(BRD6=QB.tolist(), XSV30=QX.tolist(), MV30=QM.tolist(), SIGF=QS.tolist(),
            FMED_decile1=float(Q_FMED_D1), SPAY_decile10=float(Q_SPAY_D9))
res = dict(prereg_sha256=SHAS['r12_regime/PREREG_r12_regime_partition_2026-09-12.md'],
           shas=SHAS, book_config=cfg, env=ENV, cuts=CUTS,
           selfcheck=dict(n_alpha=int(W_ALPHA.sum()), n_tail=int(W_TAIL.sum()),
                          mean_g=float(xa.mean()), sharpe=float(xa.mean()/xa.std(ddof=1)*np.sqrt(2190)),
                          turn_raw=float(turn_raw[W_ALPHA].mean()), turn_matched=float(turn[W_ALPHA].mean()),
                          turn_ratio_raw_over_matched=float(turn_raw[W_ALPHA].mean()/turn[W_ALPHA].mean()),
                          cost_pug=float(cst[W_ALPHA].mean()),
                          cost_per_unit_matched_turnover=float(cst[W_ALPHA].mean()/turn[W_ALPHA].mean())),
           cells=OUT, breadth_expanding_cut=EXP, worst_anchors=WORST_A, worst_days=WORST_D,
           built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(res, open(f"{R}/receipts/RECEIPT_r12_regime_table.json", 'w'), indent=1, default=float)
print(json.dumps(res['selfcheck'], indent=1)); print("CUTS", json.dumps(CUTS))
print("\n%-26s %-30s %6s %9s %9s %9s %8s %7s %8s %8s %8s %8s %8s %7s %8s" % (
  "family", "cell", "n", "meang", "ci_lo", "ci_hi", "Sharpe", "SE", "Sh_lo", "price", "carryPd", "cost", "turnMch", "days", "worstDay"))
for r in OUT:
    if r.get('note'): print("%-26s %-30s %6d  (too few)" % (r['family'], r['cell'], r['n'])); continue
    print("%-26s %-30s %6d %+9.4f %+9.4f %+9.4f %8.3f %7.3f %+8.3f %+8.4f %+8.4f %8.4f %8.5f %7d %8.3f%%" % (
      r['family'], r['cell'], r['n'], r['mean_g'], r['ci_lo'], r['ci_hi'], r['sharpe'], r['sharpe_se'],
      r['sharpe_lo'], r['pnl'], r['carry_paid'], r['cost'], r['turn_matched'], r['n_days_pure'],
      100*r['worst_day_ret'] if r['worst_day_ret'] == r['worst_day_ret'] else float('nan')))
np3 = sum(1 for r in OUT if not r.get('note') and r['sharpe'] > 3.0)
nl3 = sum(1 for r in OUT if not r.get('note') and r['sharpe_lo'] > 3.0)
nt  = sum(1 for r in OUT if not r.get('note'))
print("\nANSWER: Sharpe point estimate > 3.0 in %d / %d cells ; CI95 lower bound > 3.0 in %d / %d cells" % (np3, nt, nl3, nt))
print("DONE_r12")
