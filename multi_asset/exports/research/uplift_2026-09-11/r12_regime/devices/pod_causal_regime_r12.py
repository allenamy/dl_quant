#!/usr/bin/env python3
"""r12 CAUSAL regime primitives. READ-ONLY on pod2. CPU only, no GPU.

Builds, on the v4 meta anchor grid, ONLY quantities that are measurable at or before the anchor
timestamp, plus the raw per-window primitives A_k/B_k/D_k which the CONSUMER may use only at
indices k <= i-1. Nothing here partitions anything; the partition rules live in
PREREG_r12_regime_partition_2026-09-12.md, frozen before this ran.

Inputs (identical files the book itself reads; see w10_sleeve.py L110-L118, L155-158, L211-214):
  dev_v4/pod_backup_2026-08-21/wide_fea_hist_meta.npz -> meta_newprod_v4.npz   (E_ts, members, y4)
  dev_v4/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz                       (ts, f_fund_now, f_fund_iv)
  health_check/masks/umask_UPIT_CRYPTO.npz                                     (m1 CRYPTO mask)
  + uploaded A0_W_for_spay.npz (ts, W, gross_total) from the PINNED artifact
     r10_screen/CMUM_CARRY/pin/A0_PWR230k_s42.npz sha256 352ac36f...

NO expm1 anywhere: the pod 5m lineage y4 = sum of 5-minute simple returns (E-0904-F).
"""
import numpy as np, json, hashlib, os, sys, time

WHITELIST = {'PATH','HOME','PWD','SHLVL','_','LC_CTYPE','__CF_USER_TEXT_ENCODING','LANG','LC_ALL','TERM','LOGNAME','USER','SHELL','MAIL','XDG_SESSION_ID','XDG_RUNTIME_DIR','SSH_CLIENT','SSH_CONNECTION','SSH_TTY','OLDPWD','LS_COLORS','HOSTNAME','DEBIAN_FRONTEND','CUDA_VERSION','NV_.*'}
extra = sorted(k for k in os.environ if k not in WHITELIST and not k.startswith(('NV_','NVIDIA','LD_LIBRARY','PYTHONNOUSER')))
CALFLAGS = sorted(k for k in os.environ if k.startswith(('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP')))
assert CALFLAGS == [], ('caliber env flags present', CALFLAGS)

D = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
WNPZ = "/workspace/uplift_2026-09-11/r12_regime/A0_W_for_spay.npz"
OUT  = "/workspace/uplift_2026-09-11/r12_regime"
os.makedirs(OUT, exist_ok=True)

def sha(p, n=16):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]

MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
RN8 = np.nan_to_num(FN, nan=0.0) * (8.0 / IVf)          # 8h-equivalent settled rate, device L92
FINF = np.isfinite(FN)
UZ = np.load(MASK, allow_pickle=True)
assert [str(x) for x in UZ["symbols"]] == [str(x) for x in PW["symbols"]], "umask symbols mismatch"
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}
UM = np.asarray(UZ["mask"])
UMASK_ROW = {j: UM[umap[int(t)]] for j, t in enumerate(pts) if int(t) in umap}

Z = np.load(WNPZ); wts = Z["ts"].astype(np.int64); W = Z["W"]; WGT = Z["gross_total"]
wrow = {int(t): k for k, t in enumerate(wts)}

nA = len(E_ts); rows = []
for i in range(nA):
    t = int(E_ts[i]); j = pw_row.get(t)
    m = np.asarray(members[i], dtype=np.int64)
    if j is not None:
        mk = UMASK_ROW.get(j)
        if mk is not None: m = m[mk[m]]            # m1 semantics, device L155-158
    yv = y4[i, m]; ok = np.isfinite(yv); mm = m[ok]; yv = yv[ok]
    A = B = Dd = np.nan
    if mm.size >= 30:
        A = float(yv.mean()); B = float((yv > 0).mean()); Dd = float(yv.std()) * 1e4
    SIGF = FMED = np.nan; nf = 0
    if j is not None and m.size:
        f = RN8[j, m][FINF[j, m]]
        if f.size >= 30:
            SIGF = float(f.std()) * 1e4; FMED = float(np.median(f)) * 1e4; nf = int(f.size)
    SPAY = SRECV = LPAY = NETCAR = SHSHARE = np.nan
    k = wrow.get(t)
    if k is not None and j is not None:
        w = W[k].astype(np.float64); g = float(WGT[k])
        if g > 1e-12:
            c = w * RN8[j] * 0.5 * 1e4                # 4h slice of the 8h-equivalent, device: fnow*(4/iv)
            neg = w < 0; pos = w > 0
            SPAY = float(c[neg].sum() / g)            # >0 => short half PAYS
            LPAY = float(c[pos].sum() / g)            # >0 => long half PAYS
            NETCAR = SPAY + LPAY
            SHSHARE = float(np.abs(w[neg]).sum() / g)
    rows.append((t, int(mm.size), A, B, Dd, SIGF, FMED, nf, SPAY, LPAY, NETCAR, SHSHARE))
    if i % 2500 == 0: print("i", i, "/", nA, flush=True)

COLS = ["ts","n_mem","A_ew","B_breadth","D_disp_bps","SIGF","FMED","n_fund","SPAY","LPAY","NETCAR","SHORT_SHARE"]
R = np.array([[r[0]] + [float(x) for x in r[1:]] for r in rows], dtype=np.float64)
np.savez(f"{OUT}/causal_primitives_r12.npz", cols=np.array(COLS), rec=R)
rcp = dict(device=os.path.basename(__file__), device_sha256=sha(__file__, 64),
           inputs={p: dict(realpath=os.path.realpath(p), sha16=sha(p)) for p in
                   [f"{D}/wide_fea_hist_meta.npz", f"{D}/wide_panel_4h_hist_v2.npz", MASK, WNPZ]},
           n_anchors=int(nA), n_with_A=int(np.isfinite(R[:, 2]).sum()),
           n_with_SIGF=int(np.isfinite(R[:, 5]).sum()), n_with_SPAY=int(np.isfinite(R[:, 8]).sum()),
           env_whitelist_extra=extra, caliber_env_flags=CALFLAGS,
           python=sys.version.split()[0], numpy=np.__version__,
           note="A_ew/B_breadth/D_disp_bps are FORWARD-window primitives; consumer may use them only at k<=i-1",
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(rcp, open(f"{OUT}/RECEIPT_causal_primitives_r12.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rcp.items() if k != 'inputs'}, indent=1))
print("OUT", f"{OUT}/causal_primitives_r12.npz")
