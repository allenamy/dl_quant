#!/usr/bin/env python3
"""r13-A diagnostic · WHY the per-year dg signs come out the way they do, and the rho table.
Frozen by ../PREREG_r13A_halfscale_2026-09-12.md sha256 ecc929ff... (asserted). No new arm, no new
threshold: this device only decomposes numbers the judge already produced. W_ALPHA for every mean."""
import os, sys, json, time, calendar, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); U = os.path.abspath(os.path.join(R, '..'))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
assert sha(f"{R}/PREREG_r13A_halfscale_2026-09-12.md") == 'ecc929fff68f43e3c9d435a12cfb2186f22a48faea6fc698d5f7158e4607b12a'
Z = np.load(f"{R}/receipts/r13A_arms.npz", allow_pickle=True)
ts = Z['ts'].astype(np.int64); gt = Z['gross_total']; g0 = Z['base_net'] / gt
A = Z['A_ew'] * 1e4; bb = Z['beta_book']
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
WT = ts <= UB; WA = WT.copy(); WA[:900] = False
assert int(WA.sum()) == 9138 and int(WT.sum()) == 10038
year = np.array([time.gmtime(int(t)).tm_year for t in ts])
day = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
OUT = {}
# --- why the years came out as they did: the exposure P&L the overlay removes
EX = {}
for y in sorted(set(year[WA].tolist())) + ['ALL']:
    mk = WA if y == 'ALL' else (WA & (year == y))
    EX[str(y)] = dict(n=int(mk.sum()), A_mean_bps=float(A[mk].mean()), A_sd_bps=float(A[mk].std()),
                      beta_ante_mean=float(bb[mk].mean()), beta_ante_sd=float(bb[mk].std()),
                      exposure_pnl_bps=float((bb[mk] * A[mk]).mean()),
                      term_meanbeta_x_meanA=float(bb[mk].mean() * A[mk].mean()),
                      term_cov=float(np.cov(bb[mk], A[mk])[0, 1] * (mk.sum() - 1) / mk.sum()),
                      corr_beta_A=float(np.corrcoef(bb[mk], A[mk])[0, 1]),
                      predicted_dg_if_grip_1=float(-(bb[mk] * A[mk]).mean()),
                      actual_dg_AM_f100=float(((Z['AM_f100__net'] / gt) - g0)[mk].mean()))
OUT['exposure_pnl_decomposition'] = EX
# --- rho table
NAMES = [str(x) for x in Z['arm_names']]
XZ = np.load(f"{R}/receipts/XIB_LAG50_s42__REAL.npz", allow_pickle=True)
XC = [str(c) for c in XZ['cols']]; XR = XZ['rec']
assert np.array_equal(XR[:, XC.index('ts')].astype(np.int64), ts)
dx = XR[:, XC.index('net_ex')] / XR[:, XC.index('gross_total')] - g0
RHO = {'_XIB_LAG50_marginal_itself': dict(dg=float(dx[WA].mean()),
                                          rho_to_A0_g=float(np.corrcoef(dx[WA], g0[WA])[0, 1]))}
for nm in NAMES:
    d = Z[f'{nm}__net'] / gt - g0
    RHO[nm] = dict(rho_marginal_to_A0_g=float(np.corrcoef(d[WA], g0[WA])[0, 1]),
                   rho_marginal_to_XIB_LAG50_marginal=float(np.corrcoef(d[WA], dx[WA])[0, 1]),
                   rho_armg_to_A0g=float(np.corrcoef((Z[f'{nm}__net'] / gt)[WA], g0[WA])[0, 1]),
                   sd_marginal_bps=float(d[WA].std()))
OUT['rho'] = RHO
# --- HALT / ALERT day detail on W_TAIL
def days(gser, L=2.0):
    dd = {}
    for k in np.nonzero(WT)[0]: dd.setdefault(day[k], []).append(k)
    return {k: float(np.prod(1.0 + L * gser[np.array(v)] * 1e-4) - 1.0) for k, v in dd.items()}
D0 = days(g0); TL = {}
for nm in ('AM_f100', 'AM_cond', 'AM_f100c10', 'AS_f100'):
    DA = days(Z[f'{nm}__net'] / gt)
    h0 = sorted([k for k, v in D0.items() if v <= -0.04]); ha = sorted([k for k, v in DA.items() if v <= -0.04])
    TL[nm] = dict(halt_days_A0=[[k, D0[k]] for k in h0], halt_days_arm=[[k, DA[k]] for k in ha],
                  halt_days_added=[k for k in ha if k not in h0], halt_days_removed=[k for k in h0 if k not in ha],
                  worst5_A0=[[k, D0[k], DA[k]] for k in sorted(D0, key=D0.get)[:5]],
                  n_days=len(D0),
                  warm_note="the first 250 book anchors carry d=0 (beta warm-up); W_TAIL tail numbers "
                            "are therefore conservative about the overlay's tail effect")
OUT['tail_detail'] = TL
# --- identity: the exposure term the overlay switches on
ID = {}
for nm in ('AM_f100', 'AS_f100'):
    nog = Z[f'{nm}__nog']
    ID[nm] = dict(net_over_gross_mean=float(np.nanmean(nog[WA])), net_over_gross_sd=float(np.nanstd(nog[WA])),
                  net_over_gross_absmax=float(np.nanmax(np.abs(nog[WA]))),
                  A0_net_over_gross_after_reshape="0 by construction (redemean); r12 replay residual -1.3e-4")
OUT['dollar_tilt'] = ID
OUT['meta'] = dict(device=os.path.basename(__file__),
                   device_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(),
                   prereg_sha256='ecc929fff68f43e3c9d435a12cfb2186f22a48faea6fc698d5f7158e4607b12a',
                   env=ENV, built_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
json.dump(OUT, open(f"{R}/receipts/RECEIPT_r13A_diag.json", 'w'), indent=1, default=float)
for y, v in EX.items():
    print(f"{y:5s} n={v['n']:5d} Amean={v['A_mean_bps']:+8.2f}bp Asd={v['A_sd_bps']:7.1f} "
          f"bante={v['beta_ante_mean']:+7.4f} expPnL={v['exposure_pnl_bps']:+8.4f} "
          f"(meanxmean {v['term_meanbeta_x_meanA']:+7.4f} + cov {v['term_cov']:+7.4f}) "
          f"pred_dg={v['predicted_dg_if_grip_1']:+8.4f} actual={v['actual_dg_AM_f100']:+8.4f}")
print("\nrho AM_f100:", json.dumps(RHO['AM_f100']))
print("rho AS_f100:", json.dumps(RHO['AS_f100']))
print("rho AM_cond:", json.dumps(RHO['AM_cond']))
print("XIB itself:", json.dumps(RHO['_XIB_LAG50_marginal_itself']))
print("\nHALT AM_f100:", json.dumps(TL['AM_f100']['halt_days_removed']), "added", json.dumps(TL['AM_f100']['halt_days_added']))
print("HALT AS_f100 added:", json.dumps(TL['AS_f100']['halt_days_added']), "removed", json.dumps(TL['AS_f100']['halt_days_removed']))
print("worst5 A0 -> AM_f100:", json.dumps(TL['AM_f100']['worst5_A0']))
print("dollar tilt:", json.dumps(ID))
print("DONE")
