"""build_a1_spot.py — Track A family A1 (Binance SPOT vs USDT-perp) anchor features, PREREG_allweather_programme_2026-09-05 §2 row A1 / §3 Track A.
Source = the compact layout written by stream_a1.py (QUOTA MODE): features/a1_syms.json (477 mapped perp symbols, row order),
a1_spot_close (float32, × price_mult), a1_spot_lqv (float16 log1p quote volume), a1_spot_tbf (float16 taker-buy share), a1_perp_close (float32);
perp quote volume and taker-buy share come from the ext cache channels log_qv / tbf (/workspace/data/dlnative_5m_wide829_f16_ext.npz, same
source zips, same float16 encoding as the spot side). Row ts = bar CLOSE time (open_time + 5 min).
Right edge row R = idx(E) - 1 + SHIFT (SHIFT=0: last bar used CLOSES at E - 5 min, PREREG "+1 bar 时移"; asserted no row beyond E + (SHIFT-1)*5min).
Closes forward-filled up to 12 bars for the basis only. Windows are rows (R-w, R]. Features (raw; the gate device rank-transforms within members):
    qvr_4h      log(sum spot qv, 48) - log(sum perp qv, 48)          (both counts >= 80% of the window, both sums > 0)
    qvr_24h     same with 288
    basis       spot_close_ff/perp_close_ff - 1 at R
    basis_d4h   basis(R) - basis(R-48);  basis_d24h  basis(R) - basis(R-288)
    basis_z7d   (basis(R) - mean basis over (R-2016, R]) / std(same)    (count >= 60% of 2016, std > 0)
    tbs_diff_24h  sum spot tbqv / sum spot qv - sum perp tbqv / sum perp qv over 288   (counts >= 80%, sums > 0)
    svol_mom    log(sum spot qv, 288) - log(sum spot qv, 2016 / 7)      (counts >= 80%)
Output npz: F (nA, 829, 8) float32 (NaN for the 352 perps without a spot pair and wherever data is missing), names, E_ts,
avail (nA,829) bool = raw spot close AND raw perp close finite at R, shift.
env: ROOT CACHE_IN META_IN SHIFT OUT
"""
import os, sys, json, time, hashlib
import numpy as np
import pandas as pd
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA")
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
CACHE_IN = os.environ.get("CACHE_IN", "/workspace/data/dlnative_5m_wide829_f16_ext.npz")
Z = zload(CACHE_IN, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); SYMS = [str(s) for s in Z["symbols"]]; NS = len(SYMS); T = len(CTS)
assert NS == 829 and np.all(np.diff(CTS) == 300), (NS, T)
chs = [str(c) for c in Z["ch"]]; iQV, iTBF = chs.index("log_qv"), chs.index("tbf")
C_LQV = np.ascontiguousarray(Z["data"][:, :, iQV].T); C_TBF = np.ascontiguousarray(Z["data"][:, :, iTBF].T)   # (NS, T) float16
T0 = int(CTS[0]); del Z
A1S = json.load(open(f"{ROOT}/features/a1_syms.json")); MSYMS = A1S["syms"]; MAP = A1S["map"]
MM = {a: np.load(f"{ROOT}/features/a1_{a}.npy", mmap_mode="r") for a in ("spot_close", "spot_lqv", "spot_tbf", "perp_close")}
assert all(m.shape == (len(MSYMS), T) for m in MM.values()), {a: m.shape for a, m in MM.items()}
META_IN = os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz")
SHIFT = int(os.environ.get("SHIFT", "0")); OUT = os.environ["OUT"]
MT = np.load(META_IN, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64); nA = len(E_ts)
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
R = Ei - 1 + SHIFT
assert np.all(CTS[R] <= E_ts + (SHIFT - 1) * 300), "right edge beyond convention"
if SHIFT <= 1: assert np.all(CTS[R] <= E_ts), "future row used"
NAMES = ["qvr_4h", "qvr_24h", "basis", "basis_d4h", "basis_d24h", "basis_z7d", "tbs_diff_24h", "svol_mom"]
print(f"CONFIG {json.dumps({'self_sha256': SELF, 'META_IN': META_IN, 'SHIFT': SHIFT, 'OUT': OUT, 'nA': nA, 'n_mapped': len(MSYMS), 'right_edge_minus_E_seconds': int((CTS[R] - E_ts).max())})}", flush=True)
F = np.full((nA, NS, len(NAMES)), np.nan, np.float32); AV = np.zeros((nA, NS), bool)
def cums(x):
    fin = np.isfinite(x); return np.concatenate([[0.0], np.cumsum(np.where(fin, x, 0.0))]), np.concatenate([[0], np.cumsum(fin)])
def wsum(cs, cn, lo, hi, minfrac):
    lo = np.maximum(lo, -1); n = cn[hi + 1] - cn[lo + 1]; need = np.maximum(1, np.ceil(minfrac * (hi - lo)))
    return np.where(n >= need, cs[hi + 1] - cs[lo + 1], np.nan), n
def logpos(v):
    with np.errstate(invalid="ignore", divide="ignore"): return np.where(v > 0, np.log(v), np.nan)
t0 = time.time()
for r, s in enumerate(MSYMS):
    j = SYMS.index(s)
    sc = np.asarray(MM["spot_close"][r], np.float64); pc = np.asarray(MM["perp_close"][r], np.float64)
    if not (np.isfinite(sc).any() and np.isfinite(pc).any()): continue
    with np.errstate(invalid="ignore", over="ignore"):
        sq = np.expm1(np.asarray(MM["spot_lqv"][r], np.float64)); sb = np.asarray(MM["spot_tbf"][r], np.float64) * sq
        pq = np.expm1(np.asarray(C_LQV[j], np.float64)); pb = np.asarray(C_TBF[j], np.float64) * pq
    AV[:, j] = np.isfinite(sc[R]) & np.isfinite(pc[R])
    scf = pd.Series(sc).ffill(limit=12).to_numpy(); pcf = pd.Series(pc).ffill(limit=12).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"): b = scf / pcf - 1.0
    b[~(np.isfinite(scf) & np.isfinite(pcf))] = np.nan
    csq, cnq = cums(sq); csb, cnb = cums(sb); cpq, cpn = cums(pq); cpb, cpbn = cums(pb)
    cb, cbn = cums(b); cb2, _ = cums(b * b)
    s48, _ = wsum(csq, cnq, R - 48, R, 0.8); p48, _ = wsum(cpq, cpn, R - 48, R, 0.8)
    s288, _ = wsum(csq, cnq, R - 288, R, 0.8); p288, _ = wsum(cpq, cpn, R - 288, R, 0.8)
    F[:, j, 0] = logpos(s48) - logpos(p48)
    F[:, j, 1] = logpos(s288) - logpos(p288)
    F[:, j, 2] = b[R]
    F[:, j, 3] = b[R] - b[R - 48]
    F[:, j, 4] = b[R] - b[R - 288]
    with np.errstate(invalid="ignore", divide="ignore"):
        m7s, n7 = wsum(cb, cbn, R - 2016, R, 0.6); m7 = m7s / n7; q7, _ = wsum(cb2, cbn, R - 2016, R, 0.6)
        v7 = np.sqrt(np.maximum(q7 / n7 - m7 * m7, 0.0)); F[:, j, 5] = np.where(v7 > 0, (b[R] - m7) / v7, np.nan)
        sb288, _ = wsum(csb, cnb, R - 288, R, 0.8); pb288, _ = wsum(cpb, cpbn, R - 288, R, 0.8)
        F[:, j, 6] = np.where((s288 > 0) & (p288 > 0), sb288 / s288 - pb288 / p288, np.nan)
        s2016, _ = wsum(csq, cnq, R - 2016, R, 0.8)
        F[:, j, 7] = logpos(s288) - logpos(s2016 / 7.0)
    if (r + 1) % 100 == 0: print(f"fea {r+1}/{len(MSYMS)} ({time.time()-t0:.0f}s)", flush=True)
np.savez_compressed(OUT, F=F, names=np.array(NAMES), E_ts=E_ts, avail=AV, shift=SHIFT, self_sha256=SELF)
print(f"A1_FEATURES_DONE {F.shape} finite_by_col {[round(float(np.isfinite(F[:, :, k]).mean()), 4) for k in range(len(NAMES))]} avail {AV.mean():.4f} sha256 {hashlib.sha256(open(OUT,'rb').read()).hexdigest()[:16]}", flush=True)
