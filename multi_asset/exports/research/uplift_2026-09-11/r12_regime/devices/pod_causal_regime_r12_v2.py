#!/usr/bin/env python3
"""r12 pass 1+2 (v2, CORRECTED) · causal regime primitives + long/short halves for the PINNED A0 book.

v1 DEFECT (found by this device's own parity assertion, not by inspection): v1 took the member set
from the meta's `members[i]`. The pinned run has MEMBERS_TOPN=829, and w10_sleeve.py L31-37 then
REBUILDS members each anchor from the qvk ranking:
    q = nan_to_num(qvk[i], -1); o = argsort(-q); o = o[q[o] > -0.5]; members[i] = sort(o[:829])
so the book holds names that are NOT in meta members[i]. On 2025-10-10 20Z that accounted for
-35.3675 bps of a -104.2688 bps anchor. v1's gauges are VOID; this file replaces them.
(E-0825-H: semantics come from the code, not the field name.)

Then, exactly as the device (L155-158 / L211-214), UMASK_SCOPE='m1' shrinks that set by the
CRYPTO universe mask row.

Reconstructs and ASSERTS PARITY against the artifact's own columns:
    pnl_raw = (sm[m]*nan_to_num(y4[i,m]))*1e4        (CAL='log' => NO expm1, E-0904-F)
    car     = (sm[m]*nan_to_num(fnow)*(4/iv))*1e4
Read-only. CPU only. No GPU.
"""
import numpy as np, json, hashlib, os, sys, time
CALFLAGS = sorted(k for k in os.environ if k.startswith(('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')))
assert CALFLAGS == [], CALFLAGS
D = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
OUT = "/workspace/uplift_2026-09-11/r12_regime"
def sha(p, n=16):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]

B = np.load(f"{OUT}/A0_book_for_halves.npz", allow_pickle=True)
bts = B["ts"].astype(np.int64); W = B["W"]; PNL = B["pnl"]; CAR = B["carry"]; GT = B["gross_total"]
MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / IVf); FINF = np.isfinite(FN)
UZ = np.load(MASK, allow_pickle=True)
assert [str(x) for x in UZ["symbols"]] == [str(x) for x in PW["symbols"]]
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
brow = {int(t): k for k, t in enumerate(bts)}

MEMBERS_TOPN = 829            # read from the artifact's own config_json, asserted by the consumer
rows = []; mxp = mxc = 0.0; nchk = 0
for i in range(len(E_ts)):
    t = int(E_ts[i]); j = pw_row.get(t)
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:MEMBERS_TOPN]).astype(np.int64)          # device L31-37
    if j is not None and t in umap: m = m[UM[umap[t]][m]]   # device L211-214, UMASK_SCOPE='m1'
    yv = y4[i, m]; ok = np.isfinite(yv); yy = yv[ok]
    A = float(yy.mean()) if yy.size >= 30 else np.nan
    Bd = float((yy > 0).mean()) if yy.size >= 30 else np.nan
    Dd = float(yy.std()) * 1e4 if yy.size >= 30 else np.nan
    SIGF = FMED = np.nan
    if j is not None and m.size:
        f = RN8[j, m][FINF[j, m]]
        if f.size >= 30: SIGF = float(f.std()) * 1e4; FMED = float(np.median(f)) * 1e4
    pl = ps = cl = cs = gl = gs = SPAY = np.nan
    k = brow.get(t)
    if k is not None and j is not None:
        w = W[k].astype(np.float64)
        p = w[m] * np.nan_to_num(yv, nan=0.0) * 1e4
        c = w[m] * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / IVf[j, m]) * 1e4
        mxp = max(mxp, abs(p.sum() - PNL[k])); mxc = max(mxc, abs(c.sum() - CAR[k])); nchk += 1
        wl = w[m] > 0; ws = w[m] < 0; G = float(GT[k])
        pl, ps, cl, cs = p[wl].sum(), p[ws].sum(), c[wl].sum(), c[ws].sum()
        gl, gs = np.abs(w[m][wl]).sum() / G, np.abs(w[m][ws]).sum() / G
        SPAY = float(cs / G)
    rows.append((t, int(yy.size), A, Bd, Dd, SIGF, FMED, pl, ps, cl, cs, gl, gs, SPAY))
    if i % 2500 == 0: print("i", i, flush=True)
assert nchk == len(bts), (nchk, len(bts))
assert mxp < 1e-3 and mxc < 1e-4, ("PARITY FAILED", mxp, mxc)
COLS = ["ts","n_mem","A_ew","B_breadth","D_disp_bps","SIGF","FMED","pnl_long","pnl_short","car_long","car_short","gshare_long","gshare_short","SPAY"]
R = np.array([[r[0]] + [float(x) for x in r[1:]] for r in rows], dtype=np.float64)
np.savez(f"{OUT}/causal_primitives_r12_v2.npz", cols=np.array(COLS), rec=R)
rcp = dict(device=os.path.basename(__file__), device_sha256=hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
           members_rule="MEMBERS_TOPN=829 qvk rebuild (w10_sleeve.py L31-37) then UMASK m1 (L211-214)",
           parity_maxabs_pnl_bps=mxp, parity_maxabs_carry_bps=mxc, n_parity_checked=nchk,
           inputs={p: dict(realpath=os.path.realpath(p), sha16=sha(p)) for p in
                   [f"{D}/wide_fea_hist_meta.npz", f"{D}/wide_panel_4h_hist_v2.npz", MASK, f"{OUT}/A0_book_for_halves.npz"]},
           n_anchors=len(E_ts), caliber_env_flags=CALFLAGS,
           python=sys.version.split()[0], numpy=np.__version__,
           note="A_ew/B_breadth/D_disp_bps are FORWARD-window primitives; consumer may use them only at k<=i-1. SIGF/FMED/SPAY/halves are AT the anchor.",
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(rcp, open(f"{OUT}/RECEIPT_causal_primitives_r12_v2.json","w"), indent=1)
print(json.dumps({k:v for k,v in rcp.items() if k!='inputs'}, indent=1))
