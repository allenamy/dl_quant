#!/usr/bin/env python3
"""r12 pass 3 · halves in the DEPLOYED (_ex) caliber.

w10_sleeve.py L312-319 reshape (executor semantics, blueprint dl_quant_live/signal/legs.py:124):
    nz  = |sm| > 1e-12
    smr = sm.copy(); smr[nz] -= smr[nz].mean(); smr *= |sm|.sum() / |smr|.sum()
i.e. the executor RE-DEMEANS the book over its non-zero set and restores the original L1. All of
net_ex / pnl_ex / carry_ex / cost_ex are computed on smr; the `net/pnl/carry` columns are on sm.
This pass reconstructs smr from the stored sm, ASSERTS parity against pnl_ex / carry_ex, and splits
by the sign of smr, so the long/short attribution is in the same caliber as the statistic g.
Read-only. CPU only. No GPU.
"""
import numpy as np, json, hashlib, os, sys, time
CALFLAGS = sorted(k for k in os.environ if k.startswith(('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')))
assert CALFLAGS == [], CALFLAGS
D = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
OUT = "/workspace/uplift_2026-09-11/r12_regime"
B = np.load(f"{OUT}/A0_book_for_halves_ex.npz", allow_pickle=True)
bts = B["ts"].astype(np.int64); W = B["W"]; PEX = B["pnl_ex"]; CEX = B["carry_ex"]; GT = B["gross_total"]
MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw = {int(t): j for j, t in enumerate(pts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
UZ = np.load(MASK, allow_pickle=True); umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
mrow = {int(t): i for i, t in enumerate(E_ts)}
rows = []; mxp = mxc = 0.0
for k, t in enumerate(bts):
    t = int(t); i = mrow[t]; j = pw[t]
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:829]).astype(np.int64)
    if t in umap: m = m[UM[umap[t]][m]]
    sm = W[k].astype(np.float64)
    nz = np.abs(sm) > 1e-12
    smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9: smr *= g0 / g1
    yv = np.nan_to_num(y4[i, m], nan=0.0)
    fn = np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / IVf[j, m])
    p = smr[m] * yv * 1e4; c = smr[m] * fn * 1e4
    mxp = max(mxp, abs(p.sum() - PEX[k])); mxc = max(mxc, abs(c.sum() - CEX[k]))
    L = smr[m] > 0; S = smr[m] < 0; G = float(GT[k])
    rows.append((t, p[L].sum(), p[S].sum(), c[L].sum(), c[S].sum(),
                 np.abs(smr[m][L]).sum()/G, np.abs(smr[m][S]).sum()/G,
                 float(smr[m].sum()/np.abs(smr[m]).sum()) if np.abs(smr[m]).sum() > 0 else np.nan,
                 float(np.abs(smr).sum()/G)))
assert mxp < 1e-3 and mxc < 1e-4, ("PARITY FAILED _ex", mxp, mxc)
R = np.array(rows, dtype=np.float64)
COLS = ["ts","pnl_long_ex","pnl_short_ex","car_long_ex","car_short_ex","gshare_long_ex","gshare_short_ex","netlong_ex_inm","L1_ratio"]
np.savez(f"{OUT}/halves_ex_r12.npz", cols=np.array(COLS), rec=R)
rcp = dict(device=os.path.basename(__file__), device_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
           parity_maxabs_pnl_ex_bps=mxp, parity_maxabs_carry_ex_bps=mxc, n=len(R),
           caliber_env_flags=CALFLAGS, python=sys.version.split()[0], numpy=np.__version__,
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(rcp, open(f"{OUT}/RECEIPT_halves_ex_r12.json","w"), indent=1)
print(json.dumps(rcp, indent=1))
