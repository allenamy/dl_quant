"""Round-2 causal 4h LOB feature panel (PREREG_r2_LOB_2026-09-11). Window W(i)=[E-14400,E), halves at E-7200.
Only lnot is used (ldep = lnot - log(price), redundant). Bands are CUMULATIVE (verified)."""
import numpy as np, glob, os, time, json
from multiprocessing import Pool
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
TS = PW["ts"].astype(np.int64); SYM = [str(s) for s in PW["symbols"]]
CI = {s: i for i, s in enumerate(SYM)}
OUT = "/workspace/uplift_2026-09-11/r2/lob2"; os.makedirs(OUT, exist_ok=True)
IB5, IB4, IB2, IB1 = 0, 1, 3, 4
IA1, IA2, IA4, IA5 = 7, 8, 10, 11
NF = 7   # r1mean, r1std, imbstd, slmean, cxmean, rbmean, rameam  (+dtrend computed from halves)
NOUT = 8
MINW, MINH = 120, 40

def cum(x):
    ok = np.isfinite(x)
    C = np.zeros(len(x) + 1); K = np.zeros(len(x) + 1)
    C[1:] = np.cumsum(np.where(ok, x, 0.0)); K[1:] = np.cumsum(ok)
    return C, K

def one(f):
    sym = os.path.basename(f)[:-4]
    ci = CI.get(sym)
    if ci is None: return None
    try:
        d = np.load(f); t = d["ts"].astype(np.int64); L = d["lnot"].astype(np.float64)
    except Exception: return None
    if len(t) < 200: return None
    N = np.expm1(np.clip(L, 0, 60))
    Nb1, Na1 = N[:, IB1], N[:, IA1]
    S1 = Nb1 + Na1; S2 = N[:, IB2] + N[:, IA2]; S4 = N[:, IB4] + N[:, IA4]
    good = (S1 > 0) & (S2 > 0) & (S4 > 0) & (Nb1 > 0) & (Na1 > 0)
    r1 = np.where(good, np.log(np.maximum(S1, 1e-12)), np.nan)
    imb = np.where(good, (Nb1 - Na1) / np.maximum(S1, 1e-12), np.nan)
    sl = np.where(good, (L[:, IB5] - L[:, IB1]) - (L[:, IA5] - L[:, IA1]), np.nan)
    cx = np.where(good, np.log(np.maximum(S4, 1e-12)) - 2 * np.log(np.maximum(S2, 1e-12)) + np.log(np.maximum(S1, 1e-12)), np.nan)
    rb = np.where(good, np.log(np.maximum(Nb1, 1e-12)), np.nan)
    ra = np.where(good, np.log(np.maximum(Na1, 1e-12)), np.nan)
    Cr, Kr = cum(r1); Cr2, _ = cum(r1 * r1)
    Ci, Ki = cum(imb); Ci2, _ = cum(imb * imb)
    Cs, Ks = cum(sl); Cc, Kc = cum(cx); Cb, Kb = cum(rb); Ca, Ka = cum(ra)
    i0 = np.searchsorted(t, TS - 14400, "left"); im = np.searchsorted(t, TS - 7200, "left")
    i1 = np.searchsorted(t, TS, "left")
    n = len(TS); res = np.full((n, NOUT), np.nan)
    nW = Kr[i1] - Kr[i0]; nH1 = Kr[im] - Kr[i0]; nH2 = Kr[i1] - Kr[im]
    okW = (nW >= MINW) & (nH1 >= MINH) & (nH2 >= MINH)
    with np.errstate(invalid="ignore", divide="ignore"):
        mr = (Cr[i1] - Cr[i0]) / np.maximum(nW, 1)
        vr = (Cr2[i1] - Cr2[i0]) / np.maximum(nW, 1) - mr * mr
        ni = Ki[i1] - Ki[i0]
        mi = (Ci[i1] - Ci[i0]) / np.maximum(ni, 1)
        vi = (Ci2[i1] - Ci2[i0]) / np.maximum(ni, 1) - mi * mi
        h1 = (Cr[im] - Cr[i0]) / np.maximum(nH1, 1); h2 = (Cr[i1] - Cr[im]) / np.maximum(nH2, 1)
        ms = (Cs[i1] - Cs[i0]) / np.maximum(Ks[i1] - Ks[i0], 1)
        mc = (Cc[i1] - Cc[i0]) / np.maximum(Kc[i1] - Kc[i0], 1)
        mb = (Cb[i1] - Cb[i0]) / np.maximum(Kb[i1] - Kb[i0], 1)
        ma = (Ca[i1] - Ca[i0]) / np.maximum(Ka[i1] - Ka[i0], 1)
    res[:, 0] = np.where(okW, np.sqrt(np.maximum(vr, 0)), np.nan)       # LDVOL
    res[:, 1] = np.where(okW & (ni >= MINW), np.sqrt(np.maximum(vi, 0)), np.nan)  # LIVOL
    res[:, 2] = np.where(okW, ms, np.nan)                               # LSLASY
    res[:, 3] = np.where(okW, h2 - h1, np.nan)                          # LDTREND
    res[:, 4] = np.where(okW, mc, np.nan)                               # LCONVX
    res[:, 5] = np.where(okW, mr, np.nan)                               # r1mean (for LDINNOV)
    res[:, 6] = np.where(okW, mb, np.nan)                               # rb mean (for LIMBINN)
    res[:, 7] = np.where(okW, ma, np.nan)                               # ra mean
    return ci, res.astype(np.float32)

def trail42(A, W=42, MINF=10):
    """causal trailing mean over rows [i-W, i) exclusive of i; NaN if <MINF finite."""
    ok = np.isfinite(A)
    C = np.zeros((A.shape[0] + 1, A.shape[1])); K = np.zeros_like(C)
    C[1:] = np.cumsum(np.where(ok, A, 0.0), 0); K[1:] = np.cumsum(ok, 0)
    out = np.full(A.shape, np.nan)
    lo = np.maximum(0, np.arange(A.shape[0]) - W)
    cnt = K[np.arange(A.shape[0])] - K[lo]; s = C[np.arange(A.shape[0])] - C[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(cnt >= MINF, s / np.maximum(cnt, 1), np.nan)
    return out

if __name__ == "__main__":
    fs = sorted(glob.glob("/workspace/lob_npz/*.npz"))
    M = np.full((len(TS), len(SYM), NOUT), np.nan, np.float32)
    t0 = time.time(); done = 0; hit = 0
    with Pool(10) as p:
        for r in p.imap_unordered(one, fs, chunksize=2):
            done += 1
            if r is not None:
                ci, res = r; M[:, ci, :] = res; hit += 1
            if done % 100 == 0: print("%d/%d hit=%d %.0fs" % (done, len(fs), hit, time.time() - t0), flush=True)
    R1 = M[:, :, 5].astype(np.float64); RB = M[:, :, 6].astype(np.float64); RA = M[:, :, 7].astype(np.float64)
    DV = M[:, :, 0].astype(np.float64)
    F = {}
    F["LDVOL"] = M[:, :, 0]; F["LIVOL"] = M[:, :, 1]; F["LSLASY"] = M[:, :, 2]
    F["LDTREND"] = M[:, :, 3]; F["LCONVX"] = M[:, :, 4]
    F["LDINNOV"] = (R1 - trail42(R1)).astype(np.float32)
    F["LIMBINN"] = ((RB - trail42(RB)) - (RA - trail42(RA))).astype(np.float32)
    F["LDVOLR"] = (DV - trail42(DV)).astype(np.float32)
    F["_R1MEAN"] = M[:, :, 5]   # diagnostic only: the depth LEVEL (round-1 LOBDEPTH analogue)
    for nm, A in F.items():
        np.savez_compressed("%s/%s.npz" % (OUT, nm), symbols=PW["symbols"], ts=TS, mat=A)
    cov = {nm: float(np.isfinite(A).mean()) for nm, A in F.items()}
    yr = np.array([time.gmtime(int(t)).tm_year for t in TS])
    byyear = {str(y): {nm: float(np.isfinite(A[yr == y]).sum(1).mean()) for nm in ["LDVOL", "LDINNOV", "LIMBINN"] for A in [F[nm]]} for y in [2022, 2023, 2024, 2025, 2026]}
    json.dump({"coverage": cov, "names_by_year": byyear, "files_hit": hit, "nfiles": len(fs)},
              open("%s/COVERAGE.json" % OUT, "w"), indent=1)
    print("DONE", json.dumps(byyear), time.time() - t0, flush=True)
