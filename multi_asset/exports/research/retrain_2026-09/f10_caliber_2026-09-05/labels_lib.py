"""labels_lib.py — PREREG_f10_caliber_sensitivity_2026-09-05: the three labels built from the 5-minute cache, in-process (no intermediate file: the pod
volume is at quota). Construction copied verbatim from refute_C6_2/build_alt_meta.py (float16 → float32 → float64 cumsums; MIN_FIN = 46 finite bars else NaN).
For every meta anchor (wide_fea_v2ext_meta.npz E_ts; cache row E with ts == E_ts; cache ts = bar close, pod_merge_cache_ext.py L24: ts = open_time + 5min):
  (i)   oldsum  = Σ simple r5 over rows [E, E+47]      (= panel Y4 / meta y4)
  (ii)  newsum  = Σ simple r5 over rows [E+1, E+48]    (accounting window, no compounding)
  (iii) newprod = Π(1+r5)−1 over rows [E+1, E+48]      (= dlw y4s)
  conv = (Σr)² − Σr² over rows [E+1, E+48] (missing bars = 0; NaN if < 46 finite bars); rk[k] = r5[E+k], k = −3..+3 (NaN kept); rE48 = r5[E+48]
"""
import numpy as np, time
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"; META = "/workspace/data/wide_fea_v2ext_meta.npz"
LAGS = list(range(-3, 4))
def build_labels(log=print):
    t0 = time.time()
    Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); D = Z["data"]; syms5 = [str(s) for s in Z["symbols"]]; ch = [str(c) for c in Z["ch"]]
    assert ch[0] == "ret5", ch
    assert np.all(np.diff(CTS) == 300), "cache ts not 300s-equidistant"
    r5 = D[:, :, 0].astype(np.float32); fin = np.isfinite(r5); r5z = np.where(fin, r5, 0).astype(np.float64); NW = r5.shape[1]; del D
    log(f"[labels_lib {time.time()-t0:.0f}s] cache rows {len(CTS)} x {NW}; ts {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(CTS[0])))} .. {time.strftime('%Y-%m-%d %H:%M', time.gmtime(int(CTS[-1])))}")
    CS_r = np.concatenate([np.zeros((1, NW)), np.cumsum(r5z, 0)]); CS_L = np.concatenate([np.zeros((1, NW)), np.cumsum(np.log1p(r5z), 0)]); CS_f = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum(fin, 0, dtype=np.int32)])
    CS_r2 = np.concatenate([np.zeros((1, NW)), np.cumsum(r5z * r5z, 0)])
    MT = np.load(META, allow_pickle=True); E_ts = MT["E_ts"].astype(np.int64)
    row = {int(t): k for k, t in enumerate(CTS)}; r = np.array([row[int(t)] for t in E_ts]); assert (r + 49 <= len(CTS)).all() and (r - 3 >= 0).all()
    assert np.array_equal(CTS[r], E_ts) and np.all(E_ts % 14400 == 0)
    lo = r + 1; hi = r + 49; n = CS_f[hi] - CS_f[lo]
    newsum = (CS_r[hi] - CS_r[lo]).astype(np.float32); newsum[n < 46] = np.nan
    newprod = np.expm1(CS_L[hi] - CS_L[lo]).astype(np.float32); newprod[n < 46] = np.nan
    oldsum = (CS_r[r + 48] - CS_r[r]).astype(np.float32); oldsum[(CS_f[r + 48] - CS_f[r]) < 46] = np.nan
    sum64 = CS_r[hi] - CS_r[lo]; sumsq = CS_r2[hi] - CS_r2[lo]
    conv = (sum64 * sum64 - sumsq).astype(np.float32); conv[n < 46] = np.nan
    rk = np.stack([r5[r + k] for k in LAGS]).astype(np.float32); rE48 = r5[r + 48].astype(np.float32)
    del CS_r, CS_L, CS_f, CS_r2, r5, r5z, fin
    log(f"[labels_lib {time.time()-t0:.0f}s] labels built for {len(E_ts)} anchors")
    return {"E_ts": E_ts, "E_row": r, "oldsum": oldsum, "newsum": newsum, "newprod": newprod, "conv": conv, "nfin": n, "rk": rk, "rE48": rE48, "symbols": syms5,
            "meta": {"members": MT["members"], "y4": MT["y4"], "qvk": MT["qvk"], "names": MT["names"]}}
