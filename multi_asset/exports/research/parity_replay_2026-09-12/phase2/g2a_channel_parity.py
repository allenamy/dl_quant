#!/usr/bin/env python3
"""G2-A channel parity (PREREG Phase 2 §3): producer rolling.npz (snapshot 1789200000) vs pod holefix2 5m cache on the overlap window.
Read-only on both inputs; writes one JSON receipt. Env whitelist asserted."""
import os, sys, json, hashlib, time
import numpy as np
allowed = {"PATH", "HOME", "LC_CTYPE", "PWD", "SHLVL", "_", "OLDPWD"}
extra = sorted(k for k in os.environ if k not in allowed)
assert not extra, f"env not whitelisted: {extra}"
D = "/workspace/uplift_2026-09-11/parity_phase2"; CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
R = np.load(f"{D}/rolling.npz", allow_pickle=True); rts = R["ts"].astype(np.int64); RD = R["data"]           # (T,829,7) f16
Z = np.load(CACHE, allow_pickle=True); keys = list(Z.files); print("pod cache keys", keys, flush=True)
syms_pod = [str(s) for s in Z["symbols"]] if "symbols" in keys else None
ch_pod = [str(c) for c in Z["ch"]] if "ch" in keys else None
tkey = "ts" if "ts" in keys else ("cts" if "cts" in keys else None)
dkey = "data" if "data" in keys else ("cd" if "cd" in keys else None)
cts = Z[tkey].astype(np.int64); CD = Z[dkey]
syms_prod = json.load(open(f"{D}/producer_symbols.json"))["symbols_panel"]
CH = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
print("pod ch order", ch_pod, "| pod shape", CD.shape, "dtype", CD.dtype, "| producer shape", RD.shape, flush=True)
same_syms = syms_pod == syms_prod if syms_pod else None
if syms_pod and not same_syms:
    pos = {s: i for i, s in enumerate(syms_pod)}; idx = [pos.get(s, -1) for s in syms_prod]; print("symbol order differs; missing in pod:", sum(1 for i in idx if i < 0))
else:
    idx = list(range(len(syms_prod)))
# overlap timestamps
lo, hi = max(int(rts[0]), int(cts[0])), min(int(rts[-1]), int(cts[-1]))
mr = (rts >= lo) & (rts <= hi); mp = (cts >= lo) & (cts <= hi)
rt = rts[mr]; pt = cts[mp]
common = np.intersect1d(rt, pt); print("overlap", time.strftime("%Y-%m-%d %H:%M", time.gmtime(lo)), "→", time.strftime("%Y-%m-%d %H:%M", time.gmtime(hi)), "| producer rows", mr.sum(), "pod rows", mp.sum(), "common ts", len(common), flush=True)
ri = np.searchsorted(rts, common); pi = np.searchsorted(cts, common)
out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rolling_sha256": sha(f"{D}/rolling.npz"), "cache_sha256": sha(CACHE), "cache_path": CACHE,
       "pod_ch_order": ch_pod, "producer_ch_order": CH, "symbols_identical_order": same_syms, "overlap": [lo, hi], "n_common_ts": int(len(common)), "channels": {}}
chmap = {c: (ch_pod.index(c) if ch_pod and c in ch_pod else k) for k, c in enumerate(CH)}
for k, c in enumerate(CH):
    a = RD[ri][:, :, k].astype(np.float32)                        # producer
    b = CD[pi][:, idx, chmap[c]].astype(np.float32)                # pod, aligned to producer symbol order
    fa, fb = np.isfinite(a), np.isfinite(b)
    both = fa & fb; only_a = fa & ~fb; only_b = ~fa & fb
    d = np.abs(a[both] - b[both]); ulp = np.maximum(np.abs(b[both]) * 2 ** -10, 2 ** -24)   # f16 relative half-ulp scale
    viol = d > ulp
    q = np.quantile(d, [0.5, 0.9, 0.99, 0.999, 1.0]) if d.size else [None] * 5
    rec = {"n_cells": int(a.size), "both_finite": int(both.sum()), "only_producer_finite": int(only_a.sum()), "only_pod_finite": int(only_b.sum()),
           "abs_diff_quantiles_50_90_99_999_max": [None if x is None else float(x) for x in q], "n_diff_gt_f16_ulp": int(viol.sum()), "frac_diff_gt_f16_ulp": float(viol.mean()) if d.size else None,
           "producer_clip_bounds_hit": int((np.abs(a[fa]) >= 0.3 - 1e-6).sum()) if c == "ret5" else None}
    # where are the violations? top symbols
    if viol.any():
        rows, cols = np.where(both); vr, vc = rows[viol], cols[viol]
        sym_counts = np.bincount(vc, minlength=len(syms_prod)); top = np.argsort(-sym_counts)[:8]
        rec["top_symbols_by_violations"] = [(syms_prod[j], int(sym_counts[j])) for j in top if sym_counts[j] > 0]
        tcount = np.bincount(vr, minlength=len(common)); tt = np.argsort(-tcount)[:5]
        rec["top_times_by_violations"] = [(time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(common[t]))), int(tcount[t])) for t in tt if tcount[t] > 0]
        # is the violation a constant offset / scale (e.g. log base) ? report median ratio and median diff on violating cells
        av, bv = a[both][viol], b[both][viol]; ok = np.abs(bv) > 1e-6
        rec["violation_median_ratio_prod_over_pod"] = float(np.median(av[ok] / bv[ok])) if ok.any() else None
        rec["violation_median_diff"] = float(np.median(av - bv))
    out["channels"][c] = rec
    print(c, {kk: rec[kk] for kk in ("both_finite", "only_producer_finite", "only_pod_finite", "n_diff_gt_f16_ulp", "frac_diff_gt_f16_ulp")}, "q99.9/max", rec["abs_diff_quantiles_50_90_99_999_max"][3:], flush=True)
json.dump(out, open(f"{D}/G2A_channel_parity.json", "w"), indent=1); print("G2A_DONE", flush=True)
