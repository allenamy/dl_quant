#!/usr/bin/env python3
"""FP3 P-A step 1 (2026-09-18): is the producer's own 5-minute panel (a rolling.npz snapshot taken by com.hsy.combosnap) the SAME data as the research
5-minute cache on their overlap? Per channel: NaN patterns, bitwise equality of cells finite in both, max |Δ|. Read-only. usage: pa_panel_identity.py <rolling_snapshot.npz> <research_cache.npz> <out.json> [xfer_syms.npz] [live_symbols.json|txt]  (v2: symbol axis asserted in order; NaN support split live/non-live)"""
import json, sys, time, hashlib, numpy as np
RP, CP, OUT = sys.argv[1:4]; sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
R = np.load(RP, allow_pickle=True); rts = R["ts"].astype(np.int64); RD = R["data"]; C = np.load(CP, allow_pickle=True); cts = C["ts"].astype(np.int64); CD = C["data"]; ch = [str(x) for x in C["ch"]]
# v2 (R7 §3.4): the symbol axis is asserted in ORDER against the producer's own axis file (fea171/xfer_syms.npz) and the cache's symbol list, not just by count
XS = sys.argv[4] if len(sys.argv) > 4 else None
if XS:
    _X = np.load(XS, allow_pickle=True); xs = [str(x) for x in _X[_X.files[0]]]; cs = [str(x) for x in C["syms"]] if "syms" in C.files else ([str(x) for x in C["symbols"]] if "symbols" in C.files else None)
    assert cs is not None and xs == cs and len(xs) == RD.shape[1] == CD.shape[1], ("symbol axis mismatch", len(xs), len(cs) if cs else None, RD.shape, CD.shape)
assert RD.shape[1] == CD.shape[1] and RD.shape[2] == CD.shape[2], (RD.shape, CD.shape)
LIVE = sys.argv[5] if len(sys.argv) > 5 else None; live_mask = None
if LIVE:
    lv = set(json.load(open(LIVE)) if LIVE.endswith(".json") else [l.strip() for l in open(LIVE) if l.strip()]); live_mask = np.array([x in lv for x in xs]) if XS else None
lo, hi = max(rts[0], cts[0]), min(rts[-1], cts[-1]); ri = np.where((rts >= lo) & (rts <= hi))[0]; ci = np.where((cts >= lo) & (cts <= hi))[0]
out = {"device": "pa_panel_identity.py", "self_sha256": sha(__file__), "utc": time.strftime("%FT%TZ", time.gmtime()), "inputs": {RP: sha(RP), CP: sha(CP)}, "overlap": [time.strftime("%FT%TZ", time.gmtime(int(lo))), time.strftime("%FT%TZ", time.gmtime(int(hi)))], "rows": int(len(ri)), "symbols": int(RD.shape[1]), "channels": ch, "ts_grid_equal": bool(np.array_equal(rts[ri], cts[ci])), "per_channel": {}}
A = RD[ri].astype(np.float32); B = CD[ci].astype(np.float32)
for k, name in enumerate(ch):
    a, b = A[:, :, k], B[:, :, k]; na, nb = np.isnan(a), np.isnan(b); both = ~na & ~nb; d = np.abs(a - b)[both]
    supp = {}
    if live_mask is not None:
        pn = (na & ~nb); supp = {"producer_nan_cache_finite_in_nonlive_symbols": int(pn[:, ~live_mask].sum()), "producer_nan_cache_finite_in_live_symbols": int(pn[:, live_mask].sum()), "n_live_symbols": int(live_mask.sum())}
    out["per_channel"][name] = {"support_breakdown": supp, "nan_frac_producer": float(na.mean()), "nan_frac_cache": float(nb.mean()), "producer_nan_cache_finite": int((na & ~nb).sum()), "producer_finite_cache_nan": int((~na & nb).sum()), "finite_both": int(both.sum()), "bitwise_equal_frac": float((a[both] == b[both]).mean()) if both.any() else None, "max_abs_diff": float(d.max()) if d.size else 0.0}
out["symbol_axis_asserted_in_order"] = bool(XS); out["aux_inputs"] = {k: sha(v) for k, v in (("xfer_syms", XS), ("live_symbols", LIVE)) if v}; out["VERDICT"] = ("DIFFERS (time axis unequal)" if not out["ts_grid_equal"] else "IDENTICAL_ON_FINITE_CELLS") if all(v["bitwise_equal_frac"] == 1.0 and v["producer_finite_cache_nan"] == 0 for v in out["per_channel"].values()) else "DIFFERS"
out["reads"] = "the producer fills bars only for its live universe (NaN elsewhere), so the producer panel is a subset of the cache; IDENTICAL means the channel formulas and bar data agree bit for bit wherever both are finite"
json.dump(out, open(OUT, "w"), indent=1); print(out["VERDICT"], out["overlap"], {k: (v["bitwise_equal_frac"], v["producer_finite_cache_nan"]) for k, v in out["per_channel"].items()})
