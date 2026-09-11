#!/usr/bin/env python3
"""r12 stage 5 · the three states the user named, at leg level, plus halt-day attribution."""
import sys, os, json, time, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); U = os.path.abspath(os.path.join(R, '..'))
Z = np.load(f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz", allow_pickle=True)
C = [str(c) for c in Z['cols']]; RC = Z['rec']; col = lambda k: RC[:, C.index(k)].astype(float)
ts = col('ts').astype(np.int64); gt = col('gross_total'); g = col('net_ex')/gt
pnl, car, cst = col('pnl_ex')/gt, col('carry_ex')/gt, col('cost_ex')/gt
lk, lf, w3f = col('leg_king'), col('leg_fund'), col('w3_fund')
H = np.load(f"{R}/receipts/halves_ex_r12.npz"); HC = [str(c) for c in H['cols']]; HR = H['rec']
h = lambda k: HR[:, HC.index(k)].astype(float)
PLx, PSx = h('pnl_long_ex')/gt, h('pnl_short_ex')/gt
CLx, CSx = h('car_long_ex')/gt, h('car_short_ex')/gt
gL, gS = h('gshare_long_ex'), h('gshare_short_ex')
rL = np.where(gL > 1e-9, PLx/gL, np.nan); rS = np.where(gS > 1e-9, -PSx/gS, np.nan)
P = np.load(f"{R}/receipts/causal_primitives_r12_v2.npz"); PC = [str(c) for c in P['cols']]; PR = P['rec']
mrow = {int(t): i for i, t in enumerate(PR[:, 0].astype(np.int64))}; take = np.array([mrow[int(t)] for t in ts])
pc = lambda k: PR[:, PC.index(k)]
A = pc('A_ew'); Bb = pc('B_breadth'); SIGFa = pc('SIGF'); FMEDa = pc('FMED'); SPAYa = pc('SPAY')
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
Anow = A[take]*1e4; Bnow = Bb[take]; SIGF, FMED, SPAY = SIGFa[take], FMEDa[take], SPAYa[take]
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); WT = ts <= UB; WA = WT.copy(); WA[:900] = False
year = np.array([time.gmtime(int(t)).tm_year for t in ts]); day = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
def ols(y, x):
    X = np.column_stack([np.ones(len(y)), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X@b; s2 = r@r/max(len(y)-2, 1); se = np.sqrt(np.diag(s2*np.linalg.pinv(X.T@X)))
    return b, se
q10 = np.nanpercentile(FMED[WA], 10); q90 = np.nanpercentile(SPAY[WA], 90); qb = np.nanpercentile(BRD6[WA], [100/3, 200/3])
STATES = {
 'ALTSURGE R72>=+8%':      np.isfinite(R72) & (R72 >= 0.08),
 'ALTSURGE_BROAD':         np.isfinite(R72) & (R72 >= 0.08) & np.isfinite(BRD6) & (BRD6 >= 0.60),
 'POSTCRASH R24<=-2%':     np.isfinite(R24) & (R24 <= -0.02),
 'BROADRALLY(trailing)':   np.isfinite(R24) & np.isfinite(BRD6) & (R24 >= 0.02) & (BRD6 >= 0.60),
 'DEEPNEG_SHORT d10':      np.isfinite(SPAY) & (SPAY >= q90),
 'DEEPNEG_MKT d1':         np.isfinite(FMED) & (FMED <= q10),
 'BREADTH T1':             np.isfinite(BRD6) & (BRD6 <= qb[0]),
 'ALL':                    np.ones(len(ts), bool),
}
OUT = []
for nm, mk in STATES.items():
    a = mk & WA & np.isfinite(Anow)
    if a.sum() < 40: continue
    b, se = ols(g[a], Anow[a])
    a26 = a & (year == 2026)
    b26 = ols(g[a26], Anow[a26])[0] if a26.sum() >= 40 else (np.nan, np.nan)
    OUT.append(dict(state=nm, n=int(a.sum()), g=float(g[a].mean()), pnl=float(pnl[a].mean()),
        carry_paid=float(car[a].mean()), cost=float(cst[a].mean()),
        car_long=float(CLx[a].mean()), car_short=float(CSx[a].mean()),
        leg_king=float(lk[a].mean()), leg_fund=float(lf[a].mean()), w3_fund=float(w3f[a].mean()),
        rL=float(np.nanmean(rL[a])), rS=float(np.nanmean(rS[a])),
        alpha=float(b[0]), beta=float(b[1]), se_beta=float(se[1]), t=float(b[1]/se[1]),
        beta_2026=float(b26[1]) if a26.sum() >= 40 else None, n_2026=int(a26.sum()),
        A_mean_bps=float(np.nanmean(Anow[a])), SIGF=float(np.nanmean(SIGF[a]))))
# halt-day attribution
allday = {}
for k in np.nonzero(WT)[0]: allday.setdefault(day[k], []).append(k)
DAYS = sorted(((d, float(np.prod(1.0+2.0*g[np.array(ks)]*1e-4)-1.0), ks) for d, ks in allday.items()), key=lambda z: z[1])
HALT = []
for d, r, ks in DAYS:
    if r > -0.0268: break
    k = np.array(ks); Ad = float(np.nansum(Anow[k]))
    HALT.append(dict(day=d, ret2x=r, n=len(k), day_alt_move_bps=Ad,
        g_sum=float(g[k].sum()), price=float(pnl[k].sum()), carry_paid=float(car[k].sum()), cost=float(cst[k].sum()),
        carry_paid_short=float(CSx[k].sum()), carry_paid_long=float(CLx[k].sum()),
        leg_king=float(lk[k].sum()), leg_fund=float(lf[k].sum()),
        rL=float(np.nansum(rL[k])), rS=float(np.nansum(rS[k])),
        R24_at_open=float(R24[k[0]]), R72_at_open=float(R72[k[0]]), BRD6_at_open=float(BRD6[k[0]]),
        SPAY=float(np.nanmean(SPAY[k])), FMED=float(np.nanmean(FMED[k])), SIGF=float(np.nanmean(SIGF[k])),
        postwarm=bool(WA[k].all()), year=int(year[k[0]]),
        beta_explained_2026=float(-0.09131*Ad) if year[k[0]] == 2026 else None))
res = dict(states=OUT, halt_and_alert_days=HALT, env=ENV, cuts=dict(FMED_d1=float(q10), SPAY_d9=float(q90)),
           built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(res, open(f"{R}/receipts/RECEIPT_r12_stage5.json",'w'), indent=1, default=float)
print("%-22s %5s %8s %8s %8s %8s %8s %8s %9s %9s %9s %8s %8s"%("state","n","g","price","carryPd","carPdSh","legKing","legFund","alpha","beta","se","t","beta26"))
for o in OUT:
    print("%-22s %5d %+8.3f %+8.3f %+8.4f %+8.4f %+8.3f %+8.3f %+9.3f %+9.5f %9.5f %+8.2f %s"%(
     o['state'],o['n'],o['g'],o['pnl'],o['carry_paid'],o['car_short'],o['leg_king'],o['leg_fund'],
     o['alpha'],o['beta'],o['se_beta'],o['t'], ("%+.5f"%o['beta_2026']) if o['beta_2026'] is not None else "  -"))
print("\nALL UTC days at or below the ALERT line (-2.68%%), 2.0x, W_TAIL:")
print("%-9s %8s %10s %9s %9s %9s %9s %9s %8s %8s %8s %6s"%("day","ret2x","altmove","gsum","price","carryPd","carPdShort","legFund","R24open","R72open","SPAY","pwarm"))
for x in HALT:
    print("%-9s %7.3f%% %+10.1f %+9.2f %+9.2f %+9.3f %+10.3f %+9.2f %+8.4f %+8.4f %+8.3f %6s"%(
     x['day'],100*x['ret2x'],x['day_alt_move_bps'],x['g_sum'],x['price'],x['carry_paid'],x['carry_paid_short'],
     x['leg_fund'],x['R24_at_open'],x['R72_at_open'],x['SPAY'],x['postwarm']))
print("DONE_stage5")
