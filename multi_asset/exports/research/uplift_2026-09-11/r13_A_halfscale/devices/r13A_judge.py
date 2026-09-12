#!/usr/bin/env python3
"""r13-A judge · FORM A (half-scaling), MEASUREMENT ONLY.

Frozen by ../PREREG_r13A_halfscale_2026-09-12.md sha256 ecc929ff... (asserted before any number).
Regime cells are r12's 34-cell partition, rebuilt from r12's own device logic and gauges so the
table is comparable line for line (PREREG_r12_regime_partition_2026-09-12.md sha e239f8df..).

W_ALPHA (9138): every mean / dg / CI / Sharpe / turnover / cost / regime alpha number.
W_TAIL (10038): every maxDD / worst-UTC-day / HALT-ALERT number.
NOT DEPLOYABLE AS-IS: the live executor annihilates FORM A's dollar tilt exactly (r13_deploy §3).
Read-only. No live path touched.
"""
import os, sys, json, time, calendar, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))    # r13_A_halfscale
U = os.path.abspath(os.path.join(R, '..'))                            # uplift_2026-09-11
def sha(p, n=64):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]

PRE  = f"{R}/PREREG_r13A_halfscale_2026-09-12.md"
ARMS = f"{R}/receipts/r13A_arms.npz"
BOOK = f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz"
DEVW = f"{U}/trackA/w10_sleeve.py"
PRIM = f"{U}/r12_regime/receipts/causal_primitives_r12_v2.npz"
PR12 = f"{U}/r12_regime/PREREG_r12_regime_partition_2026-09-12.md"
XIB  = f"{R}/receipts/XIB_LAG50_s42__REAL.npz"
BLD  = f"{R}/receipts/RECEIPT_r13A_build.json"
SHAS = {os.path.relpath(p, U): sha(p) for p in (PRE, ARMS, BOOK, DEVW, PRIM, PR12, XIB, BLD)}
assert SHAS['r13_A_halfscale/PREREG_r13A_halfscale_2026-09-12.md'] == \
       'ecc929fff68f43e3c9d435a12cfb2186f22a48faea6fc698d5f7158e4607b12a', SHAS
assert SHAS['trackA/w10_sleeve.py'] == 'b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650'
assert SHAS['r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz'] == \
       '352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339'
assert SHAS['r12_regime/PREREG_r12_regime_partition_2026-09-12.md'] == \
       'e239f8dfd5645bf867a50950377d6d6e4b4e4fd276395e35aa2e3481a699ce3c'
BUILD = json.load(open(BLD))
assert BUILD['prereg_sha256'] == SHAS['r13_A_halfscale/PREREG_r13A_halfscale_2026-09-12.md']

# ------------------------------------------------------------------ series
Z = np.load(ARMS, allow_pickle=True)
ts = Z['ts'].astype(np.int64); gt = Z['gross_total']
NAMES = [str(x) for x in Z['arm_names']]
assert len(NAMES) == 18, NAMES
base_net = Z['base_net']; base_cost = Z['base_cost']; base_turn = Z['base_turn']
g0 = base_net / gt
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
W_TAIL = ts <= UB; W_ALPHA = W_TAIL.copy(); W_ALPHA[:900] = False
assert int(W_ALPHA.sum()) == 9138 and int(W_TAIL.sum()) == 10038
xa = g0[W_ALPHA]
assert abs(xa.mean() - 0.6341957) < 1e-5 and abs(xa.mean() / xa.std(ddof=1) * np.sqrt(2190) - 1.2912234) < 1e-5
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
day  = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
A_bps = Z['A_ew'] * 1e4

# ------------------------------------------------------------------ r12 cells (verbatim logic)
P = np.load(PRIM); PC = [str(c) for c in P['cols']]; PR = P['rec']
pcol = lambda k: PR[:, PC.index(k)].astype(float)
mts = PR[:, 0].astype(np.int64)
Aq, Bq, Dq = pcol('A_ew'), pcol('B_breadth'), pcol('D_disp_bps')
SIGF, FMED, SPAY = pcol('SIGF'), pcol('FMED'), pcol('SPAY')
def trail_mean(x, k):
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        n = cn[i] - cn[i - k]
        if n >= k * 0.8: out[i] = (cs[i] - cs[i - k]) / n
    return out
def trail_sum(x, k):
    out = np.full(len(x), np.nan)
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.0], np.cumsum(np.isfinite(x).astype(float))])
    for i in range(k, len(x)):
        if cn[i] - cn[i - k] >= k * 0.8: out[i] = cs[i] - cs[i - k]
    return out
def trail_sd(x, k):
    out = np.full(len(x), np.nan)
    for i in range(k, len(x)):
        w = x[i - k:i]; w = w[np.isfinite(w)]
        if len(w) >= k * 0.8: out[i] = w.std()
    return out
BRD6 = trail_mean(Bq, 6); XSV30 = trail_mean(Dq, 30); MV30 = trail_sd(Aq, 30) * 1e4
R24 = trail_sum(Aq, 6); R72 = trail_sum(Aq, 18)
mrow = {int(t): i for i, t in enumerate(mts)}; take = np.array([mrow[int(t)] for t in ts])
BRD6, XSV30, MV30, R24, R72 = (v[take] for v in (BRD6, XSV30, MV30, R24, R72))
SIGFb, FMEDb, SPAYb = (v[take] for v in (SIGF, FMED, SPAY))
# parity: r12's own A_ew column vs the build device's per-anchor A_ew
assert float(np.abs(Aq[take] - Z['A_ew']).max()) == 0.0, "A_ew parity broken between devices"
def terc(v):
    return np.nanpercentile(v[W_ALPHA], [100 / 3, 200 / 3])
def band(v, q):
    lab = np.full(len(v), -1)
    f = np.isfinite(v)
    lab[f & (v <= q[0])] = 0; lab[f & (v > q[0]) & (v <= q[1])] = 1; lab[f & (v > q[1])] = 2
    return lab
QB, QX, QM, QS = terc(BRD6), terc(XSV30), terc(MV30), terc(SIGFb)
LB, LX, LM, LS = band(BRD6, QB), band(XSV30, QX), band(MV30, QM), band(SIGFb, QS)
Q_FMED_D1 = np.nanpercentile(FMEDb[W_ALPHA], 10); Q_SPAY_D9 = np.nanpercentile(SPAYb[W_ALPHA], 90)
CELLS = []
for y in sorted(set(year[W_TAIL].tolist())): CELLS.append(('a_YEAR', str(y), year == y))
for t_, nm in [(0, 'T1 narrowest'), (1, 'T2'), (2, 'T3 broadest')]: CELLS.append(('b_BREADTH(trail24h)', nm, LB == t_))
for t_, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]: CELLS.append(('c_XSVOL(trail5d disp)', nm, LX == t_))
for t_, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]: CELLS.append(('c2_MKTVOL(trail5d EW sd)', nm, LM == t_))
for t_, nm in [(0, 'T1 lowest'), (1, 'T2'), (2, 'T3 highest')]: CELLS.append(('d_SIGF(fund disp)', nm, LS == t_))
E = {}
E['POSTCRASH R24<=-2%'] = np.isfinite(R24) & (R24 <= -0.02)
E['~POSTCRASH'] = np.isfinite(R24) & (R24 > -0.02)
E['BROADRALLY R24>=+2%&B>=.60'] = np.isfinite(R24) & np.isfinite(BRD6) & (R24 >= 0.02) & (BRD6 >= 0.60)
E['~BROADRALLY'] = np.isfinite(R24) & np.isfinite(BRD6) & ~E['BROADRALLY R24>=+2%&B>=.60']
E['ALTSURGE R72>=+8%'] = np.isfinite(R72) & (R72 >= 0.08)
E['~ALTSURGE'] = np.isfinite(R72) & (R72 < 0.08)
E['ALTSURGE_BROAD'] = E['ALTSURGE R72>=+8%'] & np.isfinite(BRD6) & (BRD6 >= 0.60)
E['DEEPNEG_MKT (FMED d1)'] = np.isfinite(FMEDb) & (FMEDb <= Q_FMED_D1)
E['~DEEPNEG_MKT'] = np.isfinite(FMEDb) & (FMEDb > Q_FMED_D1)
E['DEEPNEG_SHORT (SPAY d10)'] = np.isfinite(SPAYb) & (SPAYb >= Q_SPAY_D9)
E['~DEEPNEG_SHORT'] = np.isfinite(SPAYb) & (SPAYb < Q_SPAY_D9)
for k, v in E.items(): CELLS.append(('e_EVENT', k, v))
for lo, hi, nm in [(-9, -0.04, 'R72 < -4%'), (-0.04, 0.0, 'R72 -4%..0'), (0.0, 0.04, 'R72 0..+4%'),
                   (0.04, 0.08, 'R72 +4..+8%'), (0.08, 0.15, 'R72 +8..+15%'), (0.15, 9, 'R72 >= +15%')]:
    CELLS.append(('e2_R72 ladder', nm, np.isfinite(R72) & (R72 >= lo) & (R72 < hi)))

# ------------------------------------------------------------------ statistics
NB = 2000; KBONF = 18
BPCT = 100 * 0.05 / (2 * KBONF)
def boot(x, mask):
    """UTC-day block bootstrap of mean(x) on mask & W_ALPHA. Same construction as r12 boot_ci."""
    idx = np.nonzero(mask & W_ALPHA)[0]
    if len(idx) < 10: return dict(n=int(len(idx)))
    dd = {}
    for k in idx: dd.setdefault(day[k], []).append(k)
    keys = sorted(dd); byday = [np.array(dd[k]) for k in keys]; nd = len(keys)
    tot = np.array([x[b].sum() for b in byday]); cnt = np.array([len(b) for b in byday], float)
    ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        ms[k] = tot[r].sum() / cnt[r].sum()
    return dict(n=int(len(idx)), mean=float(x[idx].mean()),
                ci_lo=float(np.percentile(ms, 2.5)), ci_hi=float(np.percentile(ms, 97.5)),
                bonf_lo=float(np.percentile(ms, BPCT)), bonf_hi=float(np.percentile(ms, 100 - BPCT)),
                boot_se=float(ms.std(ddof=1)))
def dayret(mask, gser, L=2.0):
    allday = {}
    for k in np.nonzero(W_TAIL)[0]: allday.setdefault(day[k], []).append(k)
    out = []
    for dd_, ks in sorted(allday.items()):
        if mask is None or all(mask[k] for k in ks):
            out.append((dd_, float(np.prod(1.0 + L * gser[np.array(ks)] * 1e-4) - 1.0)))
    return out
def maxdd(gser, mask, L=2.0):
    idx = np.nonzero(mask)[0]
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L * gser[idx] * 1e-4)])
    return float((1 - eq / np.maximum.accumulate(eq)).max())
def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + list(X))
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ c; s2 = (r @ r) / max(len(y) - X.shape[1], 1)
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    return c, se

# ------------------------------------------------------------------ per-arm
COST_REPRICE = 3.2167
RES = {}
for nm in NAMES:
    net = Z[f'{nm}__net']; cost = Z[f'{nm}__cost']; turn = Z[f'{nm}__turn']; d = Z[f'{nm}__d']
    ga = net / gt
    dgs = ga - g0                                   # paired per-anchor dg series
    dcost_g = (cost - base_cost) / gt
    dturn = (turn - base_turn) / gt
    b = boot(dgs, np.ones(len(ts), bool))
    dg = b['mean']
    dgr = dg - (COST_REPRICE - 1.0) * float(dcost_g[W_ALPHA].mean())
    # sign of dg under repricing, with CI shifted by the same deterministic amount
    row = dict(arm=nm, kind=BUILD['arms'][nm]['kind'],
               dg=dg, ci95=[b['ci_lo'], b['ci_hi']], bonf18=[b['bonf_lo'], b['bonf_hi']],
               boot_se=b['boot_se'],
               dg_reprice_3p2167=dgr, ci95_reprice=[b['ci_lo'] - (COST_REPRICE - 1) * float(dcost_g[W_ALPHA].mean()),
                                                   b['ci_hi'] - (COST_REPRICE - 1) * float(dcost_g[W_ALPHA].mean())],
               dcost_g_fitted=float(dcost_g[W_ALPHA].mean()),
               dturn_matched=float(dturn[W_ALPHA].mean()),
               dturn_pct_of_A0=float(dturn[W_ALPHA].mean() / 0.0540270 * 100),
               mean_abs_d=float(np.abs(d[W_ALPHA]).mean()), fire_frac=float((np.abs(d) > 0)[W_ALPHA].mean()),
               sharpe_arm=float(ga[W_ALPHA].mean() / ga[W_ALPHA].std(ddof=1) * np.sqrt(2190)),
               sharpe_A0=float(xa.mean() / xa.std(ddof=1) * np.sqrt(2190)),
               rho_dg_to_A0=float(np.corrcoef(dgs[W_ALPHA], g0[W_ALPHA])[0, 1]),
               beta_book_pre=float(np.abs(Z['beta_book'][W_ALPHA]).mean()),
               beta_book_post=float(np.abs(Z[f'{nm}__beta_book'][W_ALPHA]).mean()),
               gap_pre=float((Z['beta_L'] - Z['beta_S'])[W_ALPHA].mean()),
               gap_post=float(np.nanmean((Z[f'{nm}__beta_L'] - Z[f'{nm}__beta_S'])[W_ALPHA])))
    # tail, W_TAIL
    dr_a = dict(dayret(None, ga)); dr_0 = dict(dayret(None, g0))
    da = np.array([dr_a[k] for k in sorted(dr_a)]); d0 = np.array([dr_0[k] for k in sorted(dr_0)])
    wk = sorted(dr_a)[int(np.argmin(da))]
    row.update(tail=dict(n_days=len(da),
        halt4_arm=int((da <= -0.04).sum()), halt4_A0=int((d0 <= -0.04).sum()),
        alert268_arm=int((da <= -0.0268).sum()), alert268_A0=int((d0 <= -0.0268).sum()),
        worst_day_arm=[wk, float(da.min())],
        worst_day_A0=[sorted(dr_0)[int(np.argmin(d0))], float(d0.min())],
        worst_day_same_date_arm=float(dr_a[sorted(dr_0)[int(np.argmin(d0))]]),
        maxDD_arm=maxdd(ga, W_TAIL), maxDD_A0=maxdd(g0, W_TAIL),
        maxDD_arm_Walpha=maxdd(ga, W_ALPHA), maxDD_A0_Walpha=maxdd(g0, W_ALPHA)))
    # per-year: dg, beta_book, g-on-A slope pre/post
    yr = {}
    for y in sorted(set(year[W_ALPHA].tolist())):
        mk = (year == y) & W_ALPHA
        by = boot(dgs, year == y)
        c0, s0 = ols(g0[mk], [A_bps[mk]]); c1, s1 = ols(ga[mk], [A_bps[mk]])
        yr[str(y)] = dict(n=int(mk.sum()), dg=by.get('mean'), ci95=[by.get('ci_lo'), by.get('ci_hi')],
                          beta_on_A_A0=float(c0[1]), beta_on_A_A0_se=float(s0[1]),
                          beta_on_A_arm=float(c1[1]), beta_on_A_arm_se=float(s1[1]),
                          beta_book_pre=float(np.abs(Z['beta_book'][mk]).mean()),
                          beta_book_post=float(np.abs(Z[f'{nm}__beta_book'][mk]).mean()),
                          g_A0=float(g0[mk].mean()), g_arm=float(ga[mk].mean()))
    row['per_year'] = yr
    # regimes
    cells = []
    for fam, lab, mk in CELLS:
        a = mk & W_ALPHA
        if int(a.sum()) < 30: continue
        bb = boot(dgs, mk)
        cells.append(dict(family=fam, cell=lab, n=int(a.sum()), g_A0=float(g0[a].mean()), g_arm=float(ga[a].mean()),
                          dg=bb['mean'], ci95=[bb['ci_lo'], bb['ci_hi']],
                          dcost_g=float(dcost_g[a].mean()),
                          dg_reprice=float(bb['mean'] - (COST_REPRICE - 1) * dcost_g[a].mean()),
                          sharpe_A0=float(g0[a].mean() / g0[a].std(ddof=1) * np.sqrt(2190)),
                          sharpe_arm=float(ga[a].mean() / ga[a].std(ddof=1) * np.sqrt(2190)),
                          beta_book_pre=float(np.abs(Z['beta_book'][a]).mean()),
                          beta_book_post=float(np.abs(Z[f'{nm}__beta_book'][a]).mean())))
    row['cells'] = cells
    RES[nm] = row
    print("JUDGED", nm, round(dg, 5), [round(v, 4) for v in row['ci95']], flush=True)

# ------------------------------------------------------------------ nulls on the common firing set
NW = Z['null_win'].astype(bool)
NULLS = {}
prim = Z['AM_f100__net'] / gt - g0
NULLS['AM_f100 (primary, same set)'] = boot(prim, NW)
for nm in NAMES:
    if 'SHIFT' in nm or 'RELAB' in nm:
        NULLS[nm] = boot(Z[f'{nm}__net'] / gt - g0, NW)
        NULLS[nm]['dturn_matched'] = float(((Z[f'{nm}__turn'] - base_turn) / gt)[NW].mean())
NULLS['AM_f100 (primary, same set)']['dturn_matched'] = float(((Z['AM_f100__turn'] - base_turn) / gt)[NW].mean())

# ------------------------------------------------------------------ rho to XIB_LAG50
XZ = np.load(XIB, allow_pickle=True); XC = [str(c) for c in XZ['cols']]; XR = XZ['rec']
xts = XR[:, XC.index('ts')].astype(np.int64)
assert np.array_equal(xts, ts), "XIB ts grid differs from A0"
gx = XR[:, XC.index('net_ex')] / XR[:, XC.index('gross_total')]
dx = gx - g0
RHO = {}
for nm in NAMES:
    dgs = Z[f'{nm}__net'] / gt - g0
    RHO[nm] = dict(rho_marginal_to_XIB_LAG50=float(np.corrcoef(dgs[W_ALPHA], dx[W_ALPHA])[0, 1]),
                   rho_marginal_to_A0_g=float(np.corrcoef(dgs[W_ALPHA], g0[W_ALPHA])[0, 1]),
                   rho_arm_g_to_A0_g=float(np.corrcoef((Z[f'{nm}__net'] / gt)[W_ALPHA], g0[W_ALPHA])[0, 1]))
RHO['_XIB_LAG50_itself'] = dict(dg=float(dx[W_ALPHA].mean()),
                                rho_marginal_to_A0_g=float(np.corrcoef(dx[W_ALPHA], g0[W_ALPHA])[0, 1]))

OUTJ = dict(prereg_sha256=SHAS['r13_A_halfscale/PREREG_r13A_halfscale_2026-09-12.md'],
            device=os.path.basename(__file__),
            device_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(),
            input_sha256=SHAS, K=KBONF, bonferroni_pct=BPCT,
            gate_P=BUILD['gate_P'], beta=BUILD['beta'], null_match=BUILD['null_match'],
            cells_n=len(CELLS), cuts=dict(BRD6=QB.tolist(), XSV30=QX.tolist(), MV30=QM.tolist(),
                                          SIGF=QS.tolist(), FMED_d1=float(Q_FMED_D1), SPAY_d9=float(Q_SPAY_D9)),
            arms=RES, nulls=NULLS, rho=RHO,
            cost_repricing=COST_REPRICE,
            cost_statement="Whether realised cost is ~3.2167x the fitted model is CONTESTED and "
                           "UNRESOLVED between two of our own instruments; r12 showed it decides the "
                           "SIGN of every turnover-adding arm.",
            deployability="NOT DEPLOYABLE AS-IS (r13_deploy: the executor's redemean annihilates the "
                          "half dollar tilt exactly; measured survival ratio 0.000e+00 over 640 injections).",
            env=ENV, built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(OUTJ, open(f"{R}/receipts/RECEIPT_r13A_judge.json", 'w'), indent=1, default=float)
print("DONE")
