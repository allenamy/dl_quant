"""crash_forward_identity.py — identity receipt for the forward logger's data and detection code vs the pod event study (RESULT_crash_risk §Phase 2b/2c).
(1) DATA: producer cache (~/wide_shadow/state/rolling.npz, uploaded read-only as data/producer_rolling_2026-09-06T04Z.npz) vs the pod ext cache on the
    overlapping 5-min rows and the 829 symbols: symbol order equal; per-channel max |Δ| and share of unequal cells (both float16; NaN-aware).
(2) CODE: the forward logger's onset detection (first cumulative return ≤ −θ / ≥ +θ within rows E+1..E+48, cumulative log return with NaN bars skipped)
    applied to BOTH caches on the overlapping meta anchors with the SAME cohort mask (pod Phase 0 COH, book+fund cohort): event sets (anchor, symbol, k)
    must be identical and the delay-5m r(τ→next anchor) means equal; and the same applied with the pod's stored events_theta8.npz as the reference.
Output results/forward_identity.json. Read-only."""
import os, sys, json, time, hashlib
import numpy as np
ROOT = "/workspace/review_scratch/crash_risk"; SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
P = np.load(f"{ROOT}/data/producer_rolling_2026-09-06T04Z.npz", allow_pickle=True); pts = P["ts"].astype(np.int64); pd_ = P["data"]
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); cts = Z["ts"].astype(np.int64); cd = Z["data"]; syms = [str(s) for s in Z["symbols"]]; del Z
cfg_syms = json.load(open(f"{ROOT}/data/producer_symbols_panel.json"))
res = {"self_sha256": SELF, "producer_cache_sha256": hashlib.sha256(open(f"{ROOT}/data/producer_rolling_2026-09-06T04Z.npz", "rb").read()).hexdigest(), "symbols_equal": cfg_syms == syms, "producer_range": [time.strftime("%FT%TZ", time.gmtime(int(pts[0]))), time.strftime("%FT%TZ", time.gmtime(int(pts[-1])))]}
common, ip, ic = np.intersect1d(pts, cts, return_indices=True); res["overlap_rows"] = int(len(common)); res["overlap_range"] = [time.strftime("%FT%TZ", time.gmtime(int(common[0]))), time.strftime("%FT%TZ", time.gmtime(int(common[-1])))]
chan = {}
for c, nm in enumerate(["ret5", "rng", "cpos", "lqv", "lcnt", "lasz", "tbf"]):
    a = pd_[ip, :, c].astype(np.float32); b = cd[ic, :, c].astype(np.float32); fa = np.isfinite(a); fb = np.isfinite(b); both = fa & fb
    chan[nm] = {"cells": int(both.sum()), "max_abs_diff": float(np.abs(a[both] - b[both]).max()) if both.any() else None, "share_unequal": float((a[both] != b[both]).mean()) if both.any() else None, "nan_only_producer": int((~fa & fb).sum()), "nan_only_pod": int((fa & ~fb).sum())}
res["channels"] = chan; print("DATA", json.dumps(chan), flush=True)
# (2) code identity on overlapping meta anchors
P0 = np.load(f"{ROOT}/data/phase0.npz", allow_pickle=True); COH = P0["COH"]; E_ts = P0["E_ts"].astype(np.int64)
def lc(data, ts):
    r = data[:, :, 0].astype(np.float32); f = np.isfinite(r); return np.cumsum(np.where(f, np.log1p(np.clip(r, -0.99, None)), 0.0), 0, dtype=np.float64), {int(t): i for i, t in enumerate(ts)}
LP, rowP = lc(pd_, pts); LQ, rowQ = lc(cd, cts)
def detect(L, rowmap, theta):
    out = {}
    for i, A in enumerate(E_ts):
        e = rowmap.get(int(A))
        if e is None or e < 864 or e + 48 >= len(L): continue
        cj = np.where(COH[i])[0]
        if len(cj) == 0: continue
        cum = np.expm1(L[e + 1: e + 49][:, cj] - L[e, cj]); hit = cum <= -theta; any_ = hit.any(0); k = hit.argmax(0) + 1
        for c in np.where(any_)[0]:
            tau = e + int(k[c]); j = int(cj[c]); nxt = float(np.expm1(L[e + 48, j] - L[tau + 1, j])) if e + 48 > tau + 1 else None
            out[(int(A), j, int(k[c]))] = nxt
    return out
ev = np.load(f"{ROOT}/continuation/events_theta8.npz", allow_pickle=True); ref = {(int(a), int(j), int(k)): float(v) for a, j, k, v in zip(ev["E_ts"], ev["J"], ev["K"], ev["fwd_delay5m"][:, 2])}
cmp = {}
for th in (0.05, 0.08, 0.12):
    dp = detect(LP, rowP, th); dq = detect(LQ, rowQ, th); anchors_p = {k[0] for k in dp}; anchors_q = {k[0] for k in dq}; common_a = anchors_p & anchors_q
    dpc = {k: v for k, v in dp.items() if k[0] in common_a}; dqc = {k: v for k, v in dq.items() if k[0] in common_a}
    same = set(dpc) == set(dqc); vals = [(dpc[k], dqc[k]) for k in dpc if k in dqc and dpc[k] is not None and dqc[k] is not None]
    d = {"anchors_common": len(common_a), "events_producer": len(dpc), "events_pod": len(dqc), "event_sets_equal": bool(same), "n_only_producer": len(set(dpc) - set(dqc)), "n_only_pod": len(set(dqc) - set(dpc)),
         "max_abs_diff_rnext_delay5m": (float(max(abs(a - b) for a, b in vals)) if vals else None), "mean_rnext_bps_producer": round(float(np.mean([v for v in dpc.values() if v is not None])) * 1e4, 2) if dpc else None, "mean_rnext_bps_pod": round(float(np.mean([v for v in dqc.values() if v is not None])) * 1e4, 2) if dqc else None}
    if abs(th - 0.08) < 1e-9:
        refc = {k: v for k, v in ref.items() if k[0] in common_a}; d["events_pod_stored_theta8"] = len(refc); d["stored_vs_recomputed_pod_equal"] = bool(set(refc) == set(dqc)); d["stored_vs_recomputed_max_abs_diff"] = (float(max(abs(refc[k] - dqc[k]) for k in refc if k in dqc and dqc[k] is not None and np.isfinite(refc[k]))) if refc else None)
    cmp[f"theta{int(th*100)}"] = d; print("CODE", th, json.dumps(d), flush=True)
res["detection"] = cmp; json.dump(res, open(f"{ROOT}/results/forward_identity.json", "w"), indent=1); print("FORWARD_IDENTITY_DONE", flush=True)
