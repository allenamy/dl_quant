"""INSTRUMENT-2 / GATE A device: full k=-5..+5 cross-sectional offset spectrum on the PINNED v4 replay axis.

Definition (frozen here, matches r2_sleeve/devices/ic_spec.py and r2_learned/devices/diag_r2.py):
  ic(k) = mean_i  Spearman( S[i, m_i] , y4[i+k, m_i] )
  y4[i] = the forward 4h return TRADED from anchor i (meta['y4'], log caliber).
  k=0  -> forward predictive power (the alpha).
  k=-1 -> the bar that just CLOSED before the anchor (the most recent realised bar).
  k<=-2 -> older bars.  k>=+1 -> bars after the traded one.
RANK CALIBER: scipy.stats.rankdata (AVERAGE ranks), never argsort(argsort) — the device's own xz().
UNIVERSE: members[i] INTERSECT the CRYPTO m1 umask, identical to w10_sleeve.legs() with UMASK_SCOPE=m1.
Rank-IC is invariant to the log/simple monotone per-name transform, so CAL does not enter here.
Outputs the FULL per-anchor IC series per (arm,k) so windows and block bootstraps are computed downstream.
"""
import numpy as np, json, os, time
from scipy.stats import rankdata

HC = "/workspace/review_scratch/health_check"
B  = HC + "/dev_v4/pod_backup_2026-08-21"
OUT= "/workspace/uplift_2026-09-11/r3_gates"

MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = np.asarray(MT["y4"], float)
nA = len(E_ts)
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}
WSYM = [str(s) for s in PW["symbols"]]; NW = len(WSYM)
UM = np.load(HC + "/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
assert [str(x) for x in UM["symbols"]] == WSYM
umap = {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}; UMM = np.asarray(UM["mask"])
UMASK_ROW = {j: UMM[umap[int(t)]] for j, t in enumerate(pts) if int(t) in umap}

FE  = np.asarray(PW["f_fund_ema_v1"], float); BASE = np.isfinite(FE)
AMI = np.asarray(PW["f_amihud_24h"], float)
TBF = np.asarray(PW["f_tbf_24h"], float)
R24 = np.asarray(PW["f_rev_24h"], float)
R4  = np.asarray(PW["f_rev_4h"], float)
M7  = np.asarray(PW["f_mom_7d"], float)

def rz_avg(M):
    """per-row cross-sectional rank in [-0.5,0.5], AVERAGE ranks (the device's xz)."""
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = int(ok.sum())
        if n >= 10: out[i, ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
def rz_ord(M):
    """the ORDINAL form used by the archived XIB/sleeve signal builders (argsort of argsort)."""
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = int(ok.sum())
        if n >= 10: out[i, ok] = np.argsort(np.argsort(v[ok])) / max(n - 1, 1) - 0.5
    return out

ZF  = rz_avg(np.where(BASE, FE, np.nan))
ZA  = rz_avg(np.where(BASE, AMI, np.nan))
ZA_LAG = np.full_like(ZA, np.nan); ZA_LAG[1:] = ZA[:-1]; ZA_LAG = np.where(BASE, ZA_LAG, np.nan)
ZA_FWD = np.full_like(ZA, np.nan); ZA_FWD[:-1] = ZA[1:]; ZA_FWD = np.where(BASE, ZA_FWD, np.nan)
ZF_FWD = np.full_like(ZF, np.nan); ZF_FWD[:-1] = ZF[1:]; ZF_FWD = np.where(BASE, ZF_FWD, np.nan)
ZF_ORD = rz_ord(np.where(BASE, FE, np.nan))
ZA_LAG_ORD = np.full_like(ZA, np.nan)
_zao = rz_ord(np.where(BASE, AMI, np.nan)); ZA_LAG_ORD[1:] = _zao[:-1]
ZA_LAG_ORD = np.where(BASE, ZA_LAG_ORD, np.nan)

def orth_to_ZF(Z):
    R = np.full(Z.shape, np.nan)
    for i in range(Z.shape[0]):
        ok = np.isfinite(Z[i]) & np.isfinite(ZF[i])
        if ok.sum() < 10: continue
        x = ZF[i][ok]; y = Z[i][ok]; vx = float((x * x).sum())
        b = float((x * y).sum() / vx) if vx > 1e-12 else 0.0
        R[i][ok] = y - b * x
    return R
ORTHLAG = orth_to_ZF(ZA_LAG)

rng_perm = np.random.default_rng(20260911)
ZP = np.full_like(ZF, np.nan)
for i in range(ZF.shape[0]):
    ok = np.isfinite(ZF[i]); n = int(ok.sum())
    if n >= 10:
        v = ZF[i, ok].copy(); rng_perm.shuffle(v); ZP[i, ok] = v

# ---- anchor-axis matrices (king, DL, resid) ----
SLOW = np.load("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy")
assert SLOW.shape == (nA, NW), SLOW.shape
def dl_align(path):
    pd = np.load(path)
    TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
    dts = TG["E_ts"].astype(np.int64); dsy = [str(x) for x in TG["symbols"]]
    rmap = {int(t): k for k, t in enumerate(dts)}; cmap = {s: k for k, s in enumerate(dsy)}
    cols = np.array([cmap.get(s, -1) for s in WSYM], np.int64); okc = cols >= 0
    M = np.full((nA, NW), np.nan, np.float64); nr = 0
    for i in range(nA):
        k = rmap.get(int(E_ts[i]))
        if k is None: continue
        M[i, okc] = pd[k, cols[okc]]; nr += 1
    return M, nr
F10_42, n42 = dl_align(f"{B}/../f8_2026-08-22/preds/f10_A0_s42.npy")
F10_27, n27 = dl_align(f"{B}/../f8_2026-08-22/preds/f10_A0_s2027.npy")
RS_42, nr42 = dl_align("/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s42.npy")
RS_27, nr27 = dl_align("/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s2027.npy")
print("aligned rows: f10_42 %d f10_2027 %d resid42 %d resid2027 %d / nA %d" % (n42, n27, nr42, nr27, nA), flush=True)

# oracle leak control built on the anchor axis
ORACLE = y4.copy()

PANEL_ARMS = {   # keyed on PANEL row j
  "LIVE_FUND_f_fund_ema_v1": ZF,
  "XIB_LAG50_avgrank":       0.5 * ZF + 0.5 * ZA_LAG,
  "XIB_LAG50_ordinal_archived": 0.5 * ZF_ORD + 0.5 * ZA_LAG_ORD,
  "AMI_SLEEVE_ORTHLAG":      ORTHLAG,
  "TBF_raw_SLarm":           np.where(BASE, TBF, np.nan),
  "LEG_REV24_minus_f_rev_24h": np.where(BASE, -R24, np.nan),
  "CTRL_MOM7_legal_trailing": np.where(BASE, M7, np.nan),
  "CTRL_REV4_minus_f_rev_4h": np.where(BASE, -R4, np.nan),
  "CTRL_AMI_RAW_unlagged":   ZA,
  "CTRL_LEAK_XIB_FWD50":     0.5 * ZF + 0.5 * ZA_FWD,
  "CTRL_LEAK_FUND_FWD1":     ZF_FWD,
  "CTRL_NULL_permuted_fund": ZP,
}
ANCHOR_ARMS = {
  "LIVE_KING_SLOWv3":        SLOW,
  "LIVE_DL_F10_A0_s42":      F10_42,
  "LIVE_DL_F10_A0_s2027":    F10_27,
  "RESID_SHARPE_s42":        RS_42,
  "RESID_SHARPE_s2027":      RS_27,
  "CTRL_ORACLE_y4":          ORACLE,
}

KS = list(range(-5, 6))
MINN = 50
rows = []      # (i, j, ts, m)
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]
    mk = UMASK_ROW.get(j)
    if mk is not None: m = m[mk[m]]
    if len(m) < MINN: continue
    rows.append((i, j, int(E_ts[i]), m))
print("valid anchors", len(rows), time.strftime("%F %HZ", time.gmtime(rows[0][2])), "->", time.strftime("%F %HZ", time.gmtime(rows[-1][2])), flush=True)

def spearman(a, b):
    ra = rankdata(a); rb = rankdata(b)
    ra = ra - ra.mean(); rb = rb - rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else np.nan

res = {}
ts_all = np.array([r[2] for r in rows], np.int64)
for nm, MAT in list(PANEL_ARMS.items()) + list(ANCHOR_ARMS.items()):
    on_panel = nm in PANEL_ARMS
    t0 = time.time()
    S = np.full((len(rows), len(KS)), np.nan)
    for p, (i, j, t, m) in enumerate(rows):
        s = MAT[j, m] if on_panel else MAT[i, m]
        fs = np.isfinite(s)
        if fs.sum() < MINN: continue
        for q, k in enumerate(KS):
            ii = i + k
            if ii < 0 or ii >= nA: continue
            y = y4[ii, m]
            ok = fs & np.isfinite(y)
            if ok.sum() < MINN: continue
            S[p, q] = spearman(s[ok], y[ok])
    res[nm] = S
    mu = np.nanmean(S, 0); n = np.isfinite(S).sum(0)
    print("%-30s n0=%5d  " % (nm, n[KS.index(0)]) + " ".join("%+0.5f" % v for v in mu) + "  [%.0fs]" % (time.time() - t0), flush=True)

np.savez_compressed(OUT + "/offspec_series.npz", ts=ts_all, ks=np.array(KS),
                    **{("S_" + k): v.astype(np.float32) for k, v in res.items()})
json.dump({"ks": KS, "n_anchors": len(rows),
           "mean_ic": {k: [float(x) for x in np.nanmean(v, 0)] for k, v in res.items()},
           "n_used": {k: [int(x) for x in np.isfinite(v).sum(0)] for k, v in res.items()}},
          open(OUT + "/offspec_mean.json", "w"), indent=1)
print("wrote", OUT + "/offspec_series.npz")
