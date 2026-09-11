#!/usr/bin/env python3
"""r12 stage 3 · the market-direction mechanism, in the DEPLOYED (_ex) caliber.

Answers: in a broad rally, WHAT loses — gross imbalance (a beta the book carries) or name selection?
Exact identity, per anchor, per unit gross:
    pnl_ex/gt = (gL*rL) - (gS*rS)     with  gL+gS = 1 (shares of gross),
                                            rL = EW-by-weight return of the long half,
                                            rS = same for the short half.
    = ((gL-gS)/2)*(rL+rS)  +  ((rL-rS)/2)*(gL+gS)      <-- exposure term + selection term
The first term is a DIRECTIONAL bet the book is not supposed to have; the second is the alpha.
"""
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
H = np.load(f"{R}/receipts/halves_ex_r12.npz"); HC = [str(c) for c in H['cols']]; HR = H['rec']
h = lambda k: HR[:, HC.index(k)].astype(float)
assert np.array_equal(h('ts').astype(np.int64), ts)
PLx, PSx = h('pnl_long_ex')/gt, h('pnl_short_ex')/gt
CLx, CSx = h('car_long_ex')/gt, h('car_short_ex')/gt
gL, gS = h('gshare_long_ex'), h('gshare_short_ex')
d = float(np.abs(PLx + PSx - pnl).max()); assert d < 1e-4, d
rL = np.where(gL > 1e-9, PLx/gL, np.nan)          # bps, weighted mean return of the long half
rS = np.where(gS > 1e-9, -PSx/gS, np.nan)         # bps, weighted mean return of the short half (sign flipped: the names' own return)
EXPO = ((gL - gS)/2.0)*(rL + rS)                   # directional term
SELE = ((rL - rS)/2.0)*(gL + gS)                   # selection term
assert float(np.nanmax(np.abs(EXPO + SELE - pnl))) < 1e-4, float(np.nanmax(np.abs(EXPO+SELE-pnl)))   # float32 W
P = np.load(f"{R}/receipts/causal_primitives_r12_v2.npz"); PC = [str(c) for c in P['cols']]; PR = P['rec']
mrow = {int(t): i for i, t in enumerate(PR[:, 0].astype(np.int64))}; take = np.array([mrow[int(t)] for t in ts])
Anow = PR[:, PC.index('A_ew')][take]; Bnow = PR[:, PC.index('B_breadth')][take]
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); WT = ts <= UB; WA = WT.copy(); WA[:900] = False
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
BUCK = [("A <= -150bp", Anow <= -0.015), ("-150..-50bp", (Anow > -0.015) & (Anow <= -0.005)),
        ("-50..0bp", (Anow > -0.005) & (Anow <= 0)), ("0..+50bp", (Anow > 0) & (Anow < 0.005)),
        ("+50..+150bp", (Anow >= 0.005) & (Anow < 0.015)), ("A >= +150bp", Anow >= 0.015)]
OUT = []
for nm, mk in BUCK:
    a = mk & WA
    OUT.append(dict(bucket=nm, n=int(a.sum()), A_mean_bps=float(np.nanmean(Anow[a])*1e4),
        g=float(g[a].mean()), pnl=float(pnl[a].mean()), expo=float(np.nanmean(EXPO[a])), sele=float(np.nanmean(SELE[a])),
        carry_paid=float(car[a].mean()), cost=float(cst[a].mean()),
        gL=float(gL[a].mean()), gS=float(gS[a].mean()), net_gross_tilt=float((gL[a]-gS[a]).mean()),
        rL=float(np.nanmean(rL[a])), rS=float(np.nanmean(rS[a])),
        sharpe=float(g[a].mean()/g[a].std(ddof=1)*np.sqrt(2190)), sharpe_se=float(np.sqrt(2190/a.sum()))))
BR = (Anow > 0.005) & (Bnow > 0.65); SE_ = (Anow < -0.005) & (Bnow < 0.35)
EXTRA = {}
for nm, mk in [("BROAD RALLY now", BR), ("BROAD SELLOFF now", SE_)]:
    a = mk & WA
    EXTRA[nm] = dict(n=int(a.sum()), g=float(g[a].mean()), pnl=float(pnl[a].mean()),
                     expo=float(np.nanmean(EXPO[a])), sele=float(np.nanmean(SELE[a])),
                     carry_paid=float(car[a].mean()), cost=float(cst[a].mean()),
                     expo_share_of_pnl=float(np.nanmean(EXPO[a])/pnl[a].mean()) if pnl[a].mean() else np.nan,
                     per_year={int(y): dict(n=int((a & (year == y)).sum()), g=float(g[a & (year == y)].mean()),
                                            expo=float(np.nanmean(EXPO[a & (year == y)])),
                                            sele=float(np.nanmean(SELE[a & (year == y)])))
                               for y in sorted(set(year[WA].tolist())) if (a & (year == y)).sum() >= 20})
# regression of g on the contemporaneous market return: the book's realised market beta
ok = np.isfinite(Anow) & WA
X = np.column_stack([np.ones(ok.sum()), Anow[ok]*1e4]); Y = g[ok]
b, *_ = np.linalg.lstsq(X, Y, rcond=None); res = Y - X@b
s2 = res@res/(len(Y)-2); sb = np.sqrt(np.diag(s2*np.linalg.pinv(X.T@X)))
BETA = dict(alpha_bps=float(b[0]), beta=float(b[1]), se_alpha=float(sb[0]), se_beta=float(sb[1]),
            t_beta=float(b[1]/sb[1]), n=int(ok.sum()),
            note="g (bps/anchor/unit gross) on contemporaneous EW cross-section return (bps). "
                 "beta<0 => the book is net SHORT the market. OLS SEs are iid, so treat |t| as indicative.")
Xe = np.column_stack([np.ones(ok.sum()), Anow[ok]*1e4]); be, *_ = np.linalg.lstsq(Xe, np.nan_to_num(EXPO[ok]), rcond=None)
bs, *_ = np.linalg.lstsq(Xe, np.nan_to_num(SELE[ok]), rcond=None)
BETA['beta_from_exposure_term'] = float(be[1]); BETA['beta_from_selection_term'] = float(bs[1])
res = dict(buckets=OUT, extra=EXTRA, beta=BETA,
           mean_gross_tilt_alpha=float((gL[WA]-gS[WA]).mean()),
           mean_gross_tilt_alpha_file_caliber=float(col('netlong')[WA].mean()),
           identity_maxabs=float(np.nanmax(np.abs(EXPO+SELE-pnl))), env=ENV,
           built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(res, open(f"{R}/receipts/RECEIPT_r12_stage3_beta.json",'w'), indent=1, default=float)
print("%-14s %5s %10s %9s %9s %9s %9s %9s %9s %8s %8s"%("bucket","n","A bps","g","pnl_ex","EXPOSURE","SELECTION","carryPd","cost","Sharpe","SE"))
for o in OUT:
    print("%-14s %5d %+10.1f %+9.3f %+9.3f %+9.3f %+9.3f %+9.4f %8.4f %+8.3f %8.3f"%(
      o['bucket'],o['n'],o['A_mean_bps'],o['g'],o['pnl'],o['expo'],o['sele'],o['carry_paid'],o['cost'],o['sharpe'],o['sharpe_se']))
print("\ngross tilt (gL-gS) mean, _ex caliber: %+.5f   (file caliber netlong mean %+.5f)"%(res['mean_gross_tilt_alpha'], res['mean_gross_tilt_alpha_file_caliber']))
print("BETA: g = %+.4f %+.5f * A_bps   (se_beta %.5f, t %.2f, n %d)"%(BETA['alpha_bps'],BETA['beta'],BETA['se_beta'],BETA['t_beta'],BETA['n']))
print("      of which exposure term %+.5f, selection term %+.5f"%(BETA['beta_from_exposure_term'],BETA['beta_from_selection_term']))
for k,v in EXTRA.items():
    print("\n%s: n=%d g=%+.3f pnl=%+.3f EXPOSURE=%+.3f SELECTION=%+.3f carryPd=%+.4f cost=%.4f"%(k,v['n'],v['g'],v['pnl'],v['expo'],v['sele'],v['carry_paid'],v['cost']))
    for y,d_ in v['per_year'].items(): print("    %d n=%4d g=%+7.3f expo=%+7.3f sele=%+7.3f"%(y,d_['n'],d_['g'],d_['expo'],d_['sele']))
print("\nidentity maxabs %.3e"%res['identity_maxabs']); print("DONE_stage3")
