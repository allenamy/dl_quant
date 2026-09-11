#!/usr/bin/env python3
"""r12 pass 2 · long-half / short-half price & carry decomposition of the PINNED A0 book.

Reconstructs, from the artifact's own weight matrix W (= `sm`, w10_sleeve.py L372 WS.append(sm))
and the same panel rows the device reads, the quantities the device sums at L328-L330:
    pnl_raw = (sm[m] * yv).sum()*1e4      yv = nan_to_num(y4[i,m])      <- NO expm1 (CAL='log', E-0904-F)
    car     = (sm[m] * fnow * 4/iv).sum()*1e4
and splits each by the sign of sm. PARITY ASSERTED against the artifact's own `pnl` / `carry`
columns anchor by anchor; the run aborts if the reconstruction is not the same arithmetic.
Read-only, CPU only, no GPU.
"""
import numpy as np, json, hashlib, os, sys, time
CALFLAGS = sorted(k for k in os.environ if k.startswith(('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')))
assert CALFLAGS == [], CALFLAGS
D = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
OUT = "/workspace/uplift_2026-09-11/r12_regime"
B = np.load(f"{OUT}/A0_book_for_halves.npz", allow_pickle=True)
ts = B["ts"].astype(np.int64); W = B["W"]; PNL = B["pnl"]; CAR = B["carry"]; GT = B["gross_total"]
MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
UZ = np.load(MASK, allow_pickle=True)
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
UMR = {j: UM[umap[int(t)]] for j, t in enumerate(pts) if int(t) in umap}
mrow = {int(t): i for i, t in enumerate(E_ts)}
rows = []; mx_p = mx_c = 0.0
for k, t in enumerate(ts):
    i = mrow[int(t)]; j = pw_row[int(t)]
    m = np.asarray(members[i], dtype=np.int64)
    mk = UMR.get(j)
    if mk is not None: m = m[mk[m]]
    w = W[k].astype(np.float64)[m]
    yv = np.nan_to_num(y4[i, m], nan=0.0)
    fn = np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / IVf[j, m])
    p = w * yv * 1e4; c = w * fn * 1e4
    mx_p = max(mx_p, abs(p.sum() - PNL[k])); mx_c = max(mx_c, abs(c.sum() - CAR[k]))
    L = w > 0; S = w < 0
    rows.append((int(t), p[L].sum(), p[S].sum(), c[L].sum(), c[S].sum(),
                 np.abs(w[L]).sum(), np.abs(w[S]).sum(), float(GT[k])))
assert mx_p < 1e-6 and mx_c < 1e-6, ("PARITY FAILED", mx_p, mx_c)
R = np.array(rows, dtype=np.float64)
COLS = ["ts", "pnl_long", "pnl_short", "car_long", "car_short", "g_long", "g_short", "gross_total"]
np.savez(f"{OUT}/halves_r12.npz", cols=np.array(COLS), rec=R)
rcp = dict(device=os.path.basename(__file__),
           device_sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
           parity_maxabs_pnl=mx_p, parity_maxabs_carry=mx_c, n=len(R),
           caliber_env_flags=CALFLAGS, python=sys.version.split()[0], numpy=np.__version__,
           note="split is on the FILE caliber (sm); the _ex caliber uses the reshaped smr and differs by the reshape",
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(rcp, open(f"{OUT}/RECEIPT_halves_r12.json", "w"), indent=1)
print(json.dumps(rcp, indent=1))
