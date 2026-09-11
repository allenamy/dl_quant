#!/usr/bin/env python3
"""r12 stage 2 · (i) long/short-half decomposition per cell, (ii) YEAR-CONFOUND control on the event
cells, (iii) day-block bootstrap of the event-minus-complement DIFFERENCE, (iv) the contemporaneous
(NON-CAUSAL, descriptive only) rally/selloff diagnostic the user's complaint is literally about.

Reuses the frozen partition rules; adds no new cell definitions beyond the year-stratified versions
of the already-frozen event cells and one explicitly-labelled non-causal diagnostic.
"""
import sys, os, json, time, calendar, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); U = os.path.abspath(os.path.join(R, '..'))
Z = np.load(f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz", allow_pickle=True)
C = [str(c) for c in Z['cols']]; RC = Z['rec']; col = lambda k: RC[:, C.index(k)].astype(float)
ts = col('ts').astype(np.int64); gt = col('gross_total'); g = col('net_ex')/gt
pnl, car, cst = col('pnl_ex')/gt, col('carry_ex')/gt, col('cost_ex')/gt
lk, lf, w3f, nlong = col('leg_king'), col('leg_fund'), col('w3_fund'), col('netlong')
P = np.load(f"{R}/receipts/causal_primitives_r12_v2.npz"); PC = [str(c) for c in P['cols']]; PR = P['rec']
p = lambda k: PR[:, PC.index(k)].astype(float)
mts = PR[:, 0].astype(np.int64); mrow = {int(t): i for i, t in enumerate(mts)}
take = np.array([mrow[int(t)] for t in ts])
A, Bb, Dd = p('A_ew'), p('B_breadth'), p('D_disp_bps')
def tmean(x, k):
    o = np.full(len(x), np.nan); cs = np.concatenate([[0.], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.], np.cumsum(np.isfinite(x)*1.)])
    for i in range(k, len(x)):
        n = cn[i]-cn[i-k]
        if n >= k*.8: o[i] = (cs[i]-cs[i-k])/n
    return o
def tsum(x, k):
    o = np.full(len(x), np.nan); cs = np.concatenate([[0.], np.cumsum(np.nan_to_num(x))]); cn = np.concatenate([[0.], np.cumsum(np.isfinite(x)*1.)])
    for i in range(k, len(x)):
        if cn[i]-cn[i-k] >= k*.8: o[i] = cs[i]-cs[i-k]
    return o
BRD6, R24, R72 = tmean(Bb, 6)[take], tsum(A, 6)[take], tsum(A, 18)[take]
SIGF, FMED, SPAY = p('SIGF')[take], p('FMED')[take], p('SPAY')[take]
PLg, PSg = p('pnl_long')[take]/gt, p('pnl_short')[take]/gt
CLg, CSg = p('car_long')[take]/gt, p('car_short')[take]/gt
GSL, GSS = p('gshare_long')[take], p('gshare_short')[take]
Anow, Bnow = A[take], Bb[take]                       # CONTEMPORANEOUS - non-causal, descriptive only
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
WT = ts <= UB; WA = WT.copy(); WA[:900] = False
assert WA.sum() == 9138
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
day = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
NB = 2000
def boot_diff(ma, mb):
    """day-block bootstrap of mean(g|ma) - mean(g|mb); the same resampled days feed both arms."""
    ia, ib = ma & WA, mb & WA
    dd = {}
    for k in np.nonzero(ia | ib)[0]: dd.setdefault(day[k], [[], []])[0 if ia[k] else 1].append(k)
    keys = sorted(dd); nd = len(keys)
    sa = np.array([g[dd[k][0]].sum() if dd[k][0] else 0. for k in keys]); na = np.array([len(dd[k][0]) for k in keys], float)
    sb = np.array([g[dd[k][1]].sum() if dd[k][1] else 0. for k in keys]); nb = np.array([len(dd[k][1]) for k in keys], float)
    out = np.full(NB, np.nan)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        A_, B_ = na[r].sum(), nb[r].sum()
        if A_ > 0 and B_ > 0: out[k] = sa[r].sum()/A_ - sb[r].sum()/B_
    o = out[np.isfinite(out)]
    return float(g[ia].mean()-g[ib].mean()), float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5)), float((o <= 0).mean())
def ystrat(ma, mb):
    """year-stratified difference: within each calendar year, mean(ma)-mean(mb); combined with
       weights = n of the smaller arm in that year (so a year with no event anchors cannot vote)."""
    num = den = 0.0; per = {}
    for y in sorted(set(year[WA].tolist())):
        a = ma & WA & (year == y); b = mb & WA & (year == y)
        if a.sum() < 20 or b.sum() < 20: per[y] = None; continue
        d = float(g[a].mean()-g[b].mean()); w = float(min(a.sum(), b.sum()))
        per[y] = dict(diff=d, n_event=int(a.sum()), n_comp=int(b.sum()))
        num += w*d; den += w
    return (num/den if den else np.nan), per
EV = {}
EV['POSTCRASH R24<=-2%']        = (np.isfinite(R24) & (R24 <= -0.02), np.isfinite(R24) & (R24 > -0.02))
EV['BROADRALLY R24>=+2%&B>=.6'] = (np.isfinite(R24) & np.isfinite(BRD6) & (R24 >= 0.02) & (BRD6 >= 0.60),
                                   np.isfinite(R24) & np.isfinite(BRD6) & ~((R24 >= 0.02) & (BRD6 >= 0.60)))
EV['ALTSURGE R72>=+8%']         = (np.isfinite(R72) & (R72 >= 0.08), np.isfinite(R72) & (R72 < 0.08))
EV['ALTSURGE_BROAD']            = (np.isfinite(R72) & (R72 >= 0.08) & np.isfinite(BRD6) & (BRD6 >= 0.60),
                                   np.isfinite(R72) & np.isfinite(BRD6) & ~((R72 >= 0.08) & (BRD6 >= 0.60)))
q10 = np.nanpercentile(FMED[WA], 10); q90 = np.nanpercentile(SPAY[WA], 90)
EV['DEEPNEG_MKT FMED d1']       = (np.isfinite(FMED) & (FMED <= q10), np.isfinite(FMED) & (FMED > q10))
EV['DEEPNEG_SHORT SPAY d10']    = (np.isfinite(SPAY) & (SPAY >= q90), np.isfinite(SPAY) & (SPAY < q90))
qb = np.nanpercentile(BRD6[WA], [100/3, 200/3])
EV['BREADTH T1 (narrow)']       = (np.isfinite(BRD6) & (BRD6 <= qb[0]), np.isfinite(BRD6) & (BRD6 > qb[0]))
qx = np.nanpercentile(tmean(Dd, 30)[take][WA], [100/3, 200/3]); XSV = tmean(Dd, 30)[take]
EV['XSVOL T1 (low disp)']       = (np.isfinite(XSV) & (XSV <= qx[0]), np.isfinite(XSV) & (XSV > qx[0]))
OUT = []
for nm, (ma, mb) in EV.items():
    d, lo, hi, pneg = boot_diff(ma, mb); ys, per = ystrat(ma, mb)
    a = ma & WA
    OUT.append(dict(event=nm, n=int(a.sum()), diff=d, diff_ci=[lo, hi], P_diff_le_0=pneg,
                    diff_year_stratified=ys, per_year=per,
                    pnl_long=float(PLg[a].mean()), pnl_short=float(PSg[a].mean()),
                    car_long=float(CLg[a].mean()), car_short=float(CSg[a].mean()),
                    gshare_short=float(GSS[a].mean()), leg_king=float(lk[a].mean()), leg_fund=float(lf[a].mean()),
                    w3_fund=float(w3f[a].mean()),
                    base_pnl_long=float(PLg[WA].mean()), base_pnl_short=float(PSg[WA].mean()),
                    base_car_long=float(CLg[WA].mean()), base_car_short=float(CSg[WA].mean())))
# halves by year and by the frozen tercile families
HAL = []
def halves(nm, mk):
    a = mk & WA
    if a.sum() < 30: return
    HAL.append(dict(cell=nm, n=int(a.sum()), g=float(g[a].mean()),
                    pnl_long=float(PLg[a].mean()), pnl_short=float(PSg[a].mean()),
                    car_long=float(CLg[a].mean()), car_short=float(CSg[a].mean()),
                    cost=float(cst[a].mean()), gshare_short=float(GSS[a].mean()),
                    leg_king=float(lk[a].mean()), leg_fund=float(lf[a].mean()), w3_fund=float(w3f[a].mean())))
for y in sorted(set(year[WA].tolist())): halves(f"YEAR {y}", year == y)
for nm, (ma, _) in EV.items(): halves(nm, ma)
halves("ALL W_ALPHA", np.ones(len(ts), bool))
# NON-CAUSAL contemporaneous diagnostic (labelled; describes the state the book is IN, not a rule)
NC = []
for nm, mk in [("NOW broad rally  A>+50bp & B>65%", (Anow > 0.005) & (Bnow > 0.65)),
               ("NOW narrow rally A>+50bp & B<=65%", (Anow > 0.005) & (Bnow <= 0.65)),
               ("NOW broad selloff A<-50bp & B<35%", (Anow < -0.005) & (Bnow < 0.35)),
               ("NOW quiet |A|<=50bp", np.abs(Anow) <= 0.005),
               ("NOW big up A>+150bp", Anow > 0.015),
               ("NOW big down A<-150bp", Anow < -0.015)]:
    a = mk & WA
    if a.sum() < 30: continue
    x = g[a]; sh = x.mean()/x.std(ddof=1)*np.sqrt(2190)
    NC.append(dict(state=nm, n=int(a.sum()), mean_g=float(x.mean()), sharpe=float(sh),
                   sharpe_se=float(np.sqrt(2190/a.sum())),
                   pnl_long=float(PLg[a].mean()), pnl_short=float(PSg[a].mean()),
                   car_long=float(CLg[a].mean()), car_short=float(CSg[a].mean()),
                   leg_king=float(lk[a].mean()), leg_fund=float(lf[a].mean())))
# year composition of each frozen cell
COMP = {}
for nm, (ma, _) in EV.items():
    a = ma & WA
    COMP[nm] = {int(y): int(((year == y) & a).sum()) for y in sorted(set(year[WA].tolist()))}
res = dict(events=OUT, halves=HAL, noncausal_contemporaneous=NC, year_composition=COMP,
           cuts=dict(FMED_d1=float(q10), SPAY_d9=float(q90), BRD6_terciles=qb.tolist(), XSV_terciles=qx.tolist()),
           env=ENV, built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(res, open(f"{R}/receipts/RECEIPT_r12_stage2.json", 'w'), indent=1, default=float)
print("%-30s %5s %9s %9s %9s %7s %10s"%("event vs complement","n","diff","ci_lo","ci_hi","P(d<=0)","yr-strat"))
for o in OUT:
    print("%-30s %5d %+9.4f %+9.4f %+9.4f %7.3f %+10.4f"%(o['event'],o['n'],o['diff'],o['diff_ci'][0],o['diff_ci'][1],o['P_diff_le_0'],o['diff_year_stratified']))
print("\nPER-YEAR difference (event - complement), bps/anchor/unit gross:")
print("%-30s %10s %10s %10s %10s %10s"%("event","2022","2023","2024","2025","2026"))
for o in OUT:
    print("%-30s"%o['event'] + "".join(("%10s"%("%+.3f"%o['per_year'][y]['diff'] if o['per_year'].get(y) else "-")) for y in (2022,2023,2024,2025,2026)))
print("\n%-30s %5s %8s %9s %9s %9s %9s %8s %8s %8s %8s"%("cell","n","g","pnlLong","pnlShort","carLong","carShort","cost","gshS","legKing","legFund"))
for h in HAL:
    print("%-30s %5d %+8.3f %+9.3f %+9.3f %+9.4f %+9.4f %8.4f %8.4f %+8.3f %+8.3f"%(h['cell'],h['n'],h['g'],h['pnl_long'],h['pnl_short'],h['car_long'],h['car_short'],h['cost'],h['gshare_short'],h['leg_king'],h['leg_fund']))
print("\nNON-CAUSAL contemporaneous states (descriptive; NOT a partition you can trade):")
print("%-36s %5s %9s %8s %7s %9s %9s %9s %9s"%("state","n","mean_g","Sharpe","SE","pnlLong","pnlShort","carLong","carShort"))
for o in NC:
    print("%-36s %5d %+9.3f %8.3f %7.3f %+9.3f %+9.3f %+9.4f %+9.4f"%(o['state'],o['n'],o['mean_g'],o['sharpe'],o['sharpe_se'],o['pnl_long'],o['pnl_short'],o['car_long'],o['car_short']))
print("\nYEAR COMPOSITION of event cells:"); print(json.dumps(COMP, indent=0))
print("DONE_stage2")
