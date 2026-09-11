"""INSTRUMENT-2 / GATE A step 2: the ECHO decomposition of forward IC, with block-bootstrap CIs.

MECHANISM.  The traded 4h return has a NEGATIVE cross-sectional rank-autocorrelation at lag 1
(measured here from the oracle arm: a_m = ic_oracle(-m)).  Therefore ANY score that is loaded on
the previous bar inherits a forward IC of the OPPOSITE sign, with no alpha of its own.  That is why
sign-discordance at k=-1 is the DEFAULT for a return-loaded feature and carries no information about
look-ahead.  The quantity that does carry information is the EXCESS of ic(0) over that passive echo.

Two estimators, both reported:
  (1) FIRST-ORDER echo  e1 = sum_{m=1..M} ic(-m) * a_m ;  xic1 = ic(0) - e1.
  (2) EXACT per-anchor residualisation: regress rank(y4[i]) cross-sectionally on
      rank(y4[i-1..i-M]) over the SAME member set, take the residual ytil, and define
      xic2 = mean_i corr( rank(S[i]) , ytil_i ).  xic2 is the arm's forward IC against the part of
      the traded return that NO function of the last M bars could have produced.
M = 5 anchors (20h), declared before measurement.

STATISTIC: UTC-day block bootstrap, 2000 resamples, rng = numpy.default_rng([20260905, k]).
"""
import numpy as np, json, time, calendar
from scipy.stats import rankdata
HC = "/workspace/review_scratch/health_check"; B = HC + "/dev_v4/pod_backup_2026-08-21"
OUT = "/workspace/uplift_2026-09-11/r3_gates"
M_LAG = 5
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = np.asarray(MT["y4"], float); nA = len(E_ts)
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pts = PW["ts"].astype(np.int64); pw_row = {int(t): j for j, t in enumerate(pts)}
WSYM = [str(s) for s in PW["symbols"]]; NW = len(WSYM)
UM = np.load(HC + "/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
umap = {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}; UMM = np.asarray(UM["mask"])
UMASK_ROW = {j: UMM[umap[int(t)]] for j, t in enumerate(pts) if int(t) in umap}
FE = np.asarray(PW["f_fund_ema_v1"], float); BASE = np.isfinite(FE)
AMI = np.asarray(PW["f_amihud_24h"], float); TBF = np.asarray(PW["f_tbf_24h"], float)
R24 = np.asarray(PW["f_rev_24h"], float); R4 = np.asarray(PW["f_rev_4h"], float); M7 = np.asarray(PW["f_mom_7d"], float)
def rz(Mx):
    out = np.full(Mx.shape, np.nan)
    for i in range(Mx.shape[0]):
        v = Mx[i]; ok = np.isfinite(v); n = int(ok.sum())
        if n >= 10: out[i, ok] = (rankdata(v[ok]) - 1.0) / max(n - 1, 1) - 0.5
    return out
def lag1(Z):
    L = np.full_like(Z, np.nan); L[1:] = Z[:-1]; return np.where(BASE, L, np.nan)
def ema(Mx, hl):
    a = 1.0 - 0.5 ** (1.0 / hl); O = np.full(Mx.shape, np.nan); s = np.full(Mx.shape[1], np.nan)
    for i in range(Mx.shape[0]):
        v = Mx[i]; ok = np.isfinite(v)
        s = np.where(np.isfinite(s) & ok, s + a * (v - s), np.where(ok, v, s)); O[i] = s
    return O
ZF = rz(np.where(BASE, FE, np.nan)); ZA = rz(np.where(BASE, AMI, np.nan))
ZA_LAG = lag1(ZA); ZA_FWD = np.full_like(ZA, np.nan); ZA_FWD[:-1] = ZA[1:]; ZA_FWD = np.where(BASE, ZA_FWD, np.nan)
def orth(Z):
    R = np.full(Z.shape, np.nan)
    for i in range(Z.shape[0]):
        ok = np.isfinite(Z[i]) & np.isfinite(ZF[i])
        if ok.sum() < 10: continue
        x = ZF[i][ok]; y = Z[i][ok]; vx = float((x * x).sum())
        b = float((x * y).sum() / vx) if vx > 1e-12 else 0.0
        R[i][ok] = y - b * x
    return R
SLOW = np.load("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy")
def dl_align(path):
    pd = np.load(path); TG = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)
    dts = TG["E_ts"].astype(np.int64); dsy = [str(x) for x in TG["symbols"]]
    rmap = {int(t): k for k, t in enumerate(dts)}; cmap = {s: k for k, s in enumerate(dsy)}
    cols = np.array([cmap.get(s, -1) for s in WSYM], np.int64); okc = cols >= 0
    Mm = np.full((nA, NW), np.nan); 
    for i in range(nA):
        k = rmap.get(int(E_ts[i]))
        if k is not None: Mm[i, okc] = pd[k, cols[okc]]
    return Mm
F10_42 = dl_align(f"{HC}/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy")
RS42 = dl_align("/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s42.npy")
RS27 = dl_align("/workspace/uplift_2026-09-11/r2_learned/preds/RESID_SHARPE_s2027.npy")
PANEL = {
 "LIVE_FUND_f_fund_ema_v1": ZF, "XIB_LAG50": 0.5 * ZF + 0.5 * ZA_LAG, "AMI_SLEEVE_ORTHLAG": orth(ZA_LAG),
 "TBF_raw_SLarm": np.where(BASE, TBF, np.nan), "TBF_ema08_r2form": orth(lag1(rz(ema(np.where(BASE, TBF, np.nan), 8)))),
 "LEG_REV24": np.where(BASE, -R24, np.nan), "CTRL_MOM7": np.where(BASE, M7, np.nan),
 "CTRL_REV4": np.where(BASE, -R4, np.nan), "CTRL_AMI_RAW": ZA,
 "CTRL_LEAK_XIB_FWD50": 0.5 * ZF + 0.5 * ZA_FWD, "CTRL_NULL_perm": None,
}
rngp = np.random.default_rng(20260911); ZP = np.full_like(ZF, np.nan)
for i in range(ZF.shape[0]):
    ok = np.isfinite(ZF[i]); n = int(ok.sum())
    if n >= 10:
        v = ZF[i, ok].copy(); rngp.shuffle(v); ZP[i, ok] = v
PANEL["CTRL_NULL_perm"] = ZP
ANCH = {"LIVE_KING": SLOW, "LIVE_DL_F10_s42": F10_42, "RESID_SHARPE_s42": RS42, "RESID_SHARPE_s2027": RS27,
        "CTRL_ORACLE_y4": y4}
rows = []
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    m = members[i]; mk = UMASK_ROW.get(j)
    if mk is not None: m = m[mk[m]]
    if len(m) < 50: continue
    rows.append((i, j, int(E_ts[i]), m))
nR = len(rows); ts_all = np.array([r[2] for r in rows], np.int64)
# ---- per-anchor residualised target ytil, and the past-rank design ----
YTIL = [None] * nR; YMASK = [None] * nR; R2PAST = np.full(nR, np.nan)
for p, (i, j, t, m) in enumerate(rows):
    if i - M_LAG < 0: continue
    y0 = y4[i, m]; ok = np.isfinite(y0)
    X = []
    for mm in range(1, M_LAG + 1):
        v = y4[i - mm, m]; ok = ok & np.isfinite(v); X.append(v)
    if ok.sum() < 50: continue
    r0 = rankdata(y0[ok]); r0 = (r0 - r0.mean()) / max(r0.std(), 1e-12)
    D = np.column_stack([(lambda r: (r - r.mean()) / max(r.std(), 1e-12))(rankdata(v[ok])) for v in X] + [np.ones(int(ok.sum()))])
    beta, *_ = np.linalg.lstsq(D, r0, rcond=None)
    res = r0 - D @ beta
    YTIL[p] = res; YMASK[p] = ok; R2PAST[p] = 1.0 - float((res * res).sum() / max((r0 * r0).sum(), 1e-12))
KS = list(range(-M_LAG, 1))
def ic_series(MAT, on_panel):
    IC = np.full((nR, len(KS)), np.nan); XIC = np.full(nR, np.nan)
    for p, (i, j, t, m) in enumerate(rows):
        s = MAT[j, m] if on_panel else MAT[i, m]
        fs = np.isfinite(s)
        if fs.sum() < 50: continue
        for q, k in enumerate(KS):
            ii = i + k
            if ii < 0: continue
            y = y4[ii, m]; ok = fs & np.isfinite(y)
            if ok.sum() < 50: continue
            a = rankdata(s[ok]); b = rankdata(y[ok]); a = a - a.mean(); b = b - b.mean()
            d = np.sqrt((a * a).sum() * (b * b).sum())
            if d > 0: IC[p, q] = (a * b).sum() / d
        if YTIL[p] is not None:
            ok = YMASK[p] & fs[YMASK[p]] if False else None
            okf = YMASK[p].copy(); okf[okf] = fs[okf]
            if okf.sum() >= 50:
                a = rankdata(s[okf]); a = a - a.mean()
                sel = fs[YMASK[p]]
                b = YTIL[p][sel]; b = b - b.mean()
                d = np.sqrt((a * a).sum() * (b * b).sum())
                if d > 0: XIC[p] = (a * b).sum() / d
    return IC, XIC
def boot(v, ts, key):
    ok = np.isfinite(v); v = v[ok]; ts = ts[ok]
    if len(v) < 10: return (np.nan, np.nan, np.nan)
    day = ts // 86400; ud, inv = np.unique(day, return_inverse=True)
    idx = [np.where(inv == u)[0] for u in range(len(ud))]
    rng = np.random.default_rng([20260905, key]); out = np.empty(2000)
    for b in range(2000):
        pick = rng.integers(0, len(idx), len(idx))
        out[b] = np.concatenate([idx[q] for q in pick]).size and v[np.concatenate([idx[q] for q in pick])].mean()
    return float(v.mean()), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
T = lambda y, mo, d, h=0: calendar.timegm((y, mo, d, h, 0, 0))
HI = T(2026, 8, 10, 20)
WIN = {"FULLCYCLE_postwarm": (int(ts_all[900]), HI), "F23": (T(2023, 1, 1), HI), "FROZEN": (T(2025, 3, 1), HI)}
ORAC_IC, _ = ic_series(y4, False)
A_LAG = np.nanmean(ORAC_IC, 0)   # a_m for k=-M..0 ; a[-1] is k=0 == 1.0
print("oracle a_m (k=-5..0):", " ".join("%+0.5f" % x for x in A_LAG), flush=True)
res = {"a_m_by_window": {}, "arms": {}, "M_LAG": M_LAG, "n_anchors": nR,
       "mean_R2_of_y0_on_past%d" % M_LAG: round(float(np.nanmean(R2PAST)), 5)}
for wn, (lo, hi) in WIN.items():
    mw = (ts_all >= lo) & (ts_all <= hi)
    res["a_m_by_window"][wn] = [round(float(np.nanmean(ORAC_IC[mw, q])), 6) for q in range(len(KS))]
key = 0
for nm, MAT in list(PANEL.items()) + list(ANCH.items()):
    on_panel = nm in PANEL
    IC, XIC = ic_series(MAT, on_panel)
    e = {}
    for wn, (lo, hi) in WIN.items():
        mw = (ts_all >= lo) & (ts_all <= hi)
        a = np.array(res["a_m_by_window"][wn])
        icm = np.nanmean(IC[mw], 0)
        e1 = float(sum(icm[q] * a[q] for q in range(len(KS) - 1)))   # exclude k=0
        key += 1; m0, l0, u0 = boot(IC[mw, len(KS) - 1], ts_all[mw], key)
        key += 1; mx, lx, ux = boot(XIC[mw], ts_all[mw], key)
        e[wn] = {"n": int(np.isfinite(IC[mw, len(KS) - 1]).sum()),
                 "ic_k": [round(float(x), 6) for x in icm],
                 "ic0": round(m0, 6), "ic0_CI95": [round(l0, 6), round(u0, 6)],
                 "echo_firstorder": round(e1, 6), "xic1_ic0_minus_echo": round(m0 - e1, 6),
                 "xic2_resid_target": round(mx, 6), "xic2_CI95": [round(lx, 6), round(ux, 6)],
                 "echo_share_of_ic0": (round(e1 / m0, 3) if abs(m0) > 1e-9 else None)}
    res["arms"][nm] = e
    f = e["FULLCYCLE_postwarm"]
    print("%-24s ic0 %+0.5f [%+0.5f,%+0.5f]  echo %+0.5f  xic1 %+0.5f  xic2 %+0.5f [%+0.5f,%+0.5f]" %
          (nm, f["ic0"], f["ic0_CI95"][0], f["ic0_CI95"][1], f["echo_firstorder"], f["xic1_ic0_minus_echo"],
           f["xic2_resid_target"], f["xic2_CI95"][0], f["xic2_CI95"][1]), flush=True)
json.dump(res, open(OUT + "/echo_decomposition.json", "w"), indent=1)
print("wrote", OUT + "/echo_decomposition.json")
