#!/usr/bin/env python3
"""r12 stage 4 · (a) per-year market-direction loading of the replay book, (b) reconciliation with the
LIVE book's realised exposure.

(b) reads ONLY the already-archived artifact ../beta_exante_rows.json, whose producer
../beta_neutrality_2026-09-11.py was opened and read first (E-0825-H): it reconstructs live positions
from dl_quant_live/state/live/pilot_log/*/position_readback.jsonl and the wide_shadow rolling 5m
panel, caliber = SUM of 5m simple returns over the +30min-shifted 4h window (E-0904-F, no expm1).
This device does NOT touch the live tree itself.
"""
import sys, os, json, time, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); U = os.path.abspath(os.path.join(R, '..'))
Z = np.load(f"{U}/r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz", allow_pickle=True)
C = [str(c) for c in Z['cols']]; RC = Z['rec']; col = lambda k: RC[:, C.index(k)].astype(float)
ts = col('ts').astype(np.int64); gt = col('gross_total'); g = col('net_ex')/gt; pnl = col('pnl_ex')/gt
P = np.load(f"{R}/receipts/causal_primitives_r12_v2.npz"); PC = [str(c) for c in P['cols']]; PR = P['rec']
mrow = {int(t): i for i, t in enumerate(PR[:, 0].astype(np.int64))}; take = np.array([mrow[int(t)] for t in ts])
A = PR[:, PC.index('A_ew')][take] * 1e4
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); WA = (ts <= UB); WA[:900] = False
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
def ols(y, x):
    X = np.column_stack([np.ones(len(y)), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; s2 = r @ r / max(len(y) - 2, 1); se = np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))
    return b, se
PY = []
for y in sorted(set(year[WA].tolist())):
    a = WA & (year == y) & np.isfinite(A)
    b, se = ols(g[a], A[a])
    hy = {}
    for h_ in range(2):
        pass
    PY.append(dict(year=int(y), n=int(a.sum()), alpha_bps=float(b[0]), beta=float(b[1]),
                   se_beta=float(se[1]), t=float(b[1]/se[1]),
                   loss_at_plus250bps=float(b[0] + b[1]*250), gain_at_minus250bps=float(b[0] + b[1]*(-250))))
# rolling 500-anchor beta
RB = []
idx = np.nonzero(WA & np.isfinite(A))[0]
for s in range(0, len(idx)-500, 250):
    w = idx[s:s+500]; b, se = ols(g[w], A[w])
    RB.append(dict(start=time.strftime('%Y-%m-%d', time.gmtime(int(ts[w[0]]))), beta=float(b[1]), se=float(se[1])))
# ---- live reconciliation ----
rows = json.load(open(f"{U}/beta_exante_rows.json"))
ng = np.array([r['ng'] for r in rows]); db = np.array([r.get('dbeta_g', np.nan) for r in rows], float)
alt = np.array([r['alt'] for r in rows]) * 1e4; bps = np.array([r['bps'] for r in rows])
lb = np.array([r['lbps'] for r in rows]); sb = np.array([r['sbps'] for r in rows])
ok = np.isfinite(alt) & np.isfinite(bps)
b, se = ols(bps[ok], alt[ok])
LIVE = dict(n=int(len(rows)), n_used=int(ok.sum()),
            ng_mean=float(np.nanmean(ng)), ng_median=float(np.nanmedian(ng)), ng_p10=float(np.nanpercentile(ng,10)),
            dbeta_g_mean=float(np.nanmean(db)), dbeta_g_median=float(np.nanmedian(db)),
            live_alpha_bps=float(b[0]), live_beta=float(b[1]), live_se_beta=float(se[1]), live_t=float(b[1]/se[1]),
            live_loss_at_plus250=float(b[0]+b[1]*250), live_gain_at_minus250=float(b[0]+b[1]*(-250)),
            long_half_bps_mean=float(np.nanmean(lb)), short_half_bps_mean=float(np.nanmean(sb)),
            note="`ng` = net notional / gross from the live position readback; the replay's _ex caliber "
                 "re-demeans the book every anchor (gL-gS = -1.3e-4), so the replay carries NO dollar tilt "
                 "while the live book carries ng. The replay therefore UNDERSTATES the live book's "
                 "market-direction term by |ng| x market move.")
res = dict(replay_beta_by_year=PY, replay_beta_rolling500=RB, live=LIVE, env=ENV,
           built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(res, open(f"{R}/receipts/RECEIPT_r12_stage4.json",'w'), indent=1, default=float)
print("REPLAY market-direction loading, g = alpha + beta*A_bps, per year (W_ALPHA, _ex caliber):")
print("%6s %6s %10s %10s %9s %7s %14s %14s"%("year","n","alpha","beta","se","t","g@A=+250bp","g@A=-250bp"))
for o in PY: print("%6d %6d %+10.4f %+10.5f %9.5f %+7.2f %+14.3f %+14.3f"%(o['year'],o['n'],o['alpha_bps'],o['beta'],o['se_beta'],o['t'],o['loss_at_plus250bps'],o['gain_at_minus250bps']))
print("\nrolling 500-anchor beta:"); print("  " + "  ".join("%s:%+.4f"%(r['start'],r['beta']) for r in RB))
print("\nLIVE book reconciliation (beta_exante_rows.json, n=%d):"%LIVE['n'])
for k in ('ng_mean','ng_median','ng_p10','dbeta_g_mean','dbeta_g_median','live_alpha_bps','live_beta','live_se_beta','live_t','live_loss_at_plus250','live_gain_at_minus250','long_half_bps_mean','short_half_bps_mean'):
    print("   %-22s %+.5f"%(k, LIVE[k]))
print("DONE_stage4")
