"""AX12 (axis_0919): attribution of f_fund_ema_v2 tail differences between this round's v2ext panel and the T5d ivfix panel (08-31T04Z..09-10T00Z).
Hypothesis H: the ONLY cause is the r6/pod_panel_splice algebra's span = max(2, round(24 / median(iv of ALL tail events in the build))) — a statistic
over the whole tail, so extending the tail (09-11 15:00 -> 09-18) changes the span of names whose interval mix changed in September.
Test: for every symbol whose v2 tail differs, recompute the v2 tail with THIS round's events and ledger intervals but the median taken over tail events
with settlement second <= AX_T5D_STREAM_END (the end of the stream T5d used, r6_fund_sep max) — every recomputed cell must equal the ivfix cell bitwise.
Also reports the two medians per symbol. Pure reads. env: AX_PANEL AX_IVFIX AX_BASE AX_LEDGER AX_T5D_STREAM_END AX_RECEIPT
"""
import os, json, time, hashlib
import numpy as np
E = {k: os.environ[k] for k in ("AX_PANEL", "AX_IVFIX", "AX_BASE", "AX_LEDGER", "AX_T5D_STREAM_END", "AX_RECEIPT")}
assert not os.path.exists(E["AX_RECEIPT"])
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
HL = 3 * 86400.0; SEND = int(E["AX_T5D_STREAM_END"])
A = np.load(E["AX_PANEL"], allow_pickle=True); B = np.load(E["AX_IVFIX"], allow_pickle=True); C = np.load(E["AX_BASE"], allow_pickle=True)
L = np.load(E["AX_LEDGER"], allow_pickle=True)
syms = [str(s) for s in A["symbols"]]; ta = A["ts"].astype(np.int64); tb = B["ts"].astype(np.int64); cut = int(C["ts"][-1]); nC = len(C["ts"])
tail_b = tb[nC:]; ia = np.searchsorted(ta, tail_b); assert np.array_equal(ta[ia], tail_b)
va, vb = A["f_fund_ema_v2"][ia], B["f_fund_ema_v2"][nC:]
d = ~((va == vb) | (np.isnan(va) & np.isnan(vb))); js = np.nonzero(d.any(0))[0]
res = {}; allok = True
for j in js:
    s = syms[j]; m = (L["sym"] == j)
    ft = L["ts"][m].astype(np.int64); fr = L["rate"][m].astype(np.float64); iv = L["iv"][m].astype(np.float64)
    sel = ft > cut; rate_nf = fr * (8.0 / iv)
    seed = float(C["f_fund_ema_v2"][-1, j]) if np.isfinite(C["f_fund_ema_v2"][-1, j]) else None
    med_all = float(np.median(iv[sel])) if sel.any() else 8.0
    sel2 = sel & (ft <= SEND); med_t5d = float(np.median(iv[sel2])) if sel2.any() else 8.0
    span = max(2, round(24 / med_t5d)); al2 = 2.0 / (span + 1.0)
    e2 = seed; ptr = np.nonzero(sel)[0]; k2 = 0; out = np.full(len(tail_b), np.nan, np.float32)
    for r, t_anchor in enumerate(tail_b):                                   # r6_panel_splice.py L118-127 algebra, v2 branch only
        while k2 < len(ptr) and ft[ptr[k2]] <= t_anchor:
            i_ = ptr[k2]; e2 = e2 + al2 * (rate_nf[i_] - e2) if e2 is not None else rate_nf[i_]; k2 += 1
        if e2 is not None: out[r] = np.float32(e2)
    ok = bool(np.array_equal(out.view(np.uint32)[~np.isnan(out)], vb[:, j].view(np.uint32)[~np.isnan(out)]) and np.array_equal(np.isnan(out), np.isnan(vb[:, j])))
    allok &= ok
    res[s] = {"cells_diff": int(d[:, j].sum()), "median_iv_tail_to_build_end": med_all, "median_iv_tail_to_t5d_stream_end": med_t5d,
              "span_this_build": max(2, round(24 / med_all)), "span_t5d": span, "recomputed_with_t5d_window_equals_ivfix_bitwise": ok}
rep = {"device": "ax12_v2span_attribution.py", "self_sha256": sha(os.path.abspath(__file__)), "env": E,
       "inputs_sha256": {k: sha(E[k]) for k in ("AX_PANEL", "AX_IVFIX", "AX_BASE", "AX_LEDGER")}, "t5d_stream_end": U(SEND),
       "n_symbols_v2_diff": len(js), "per_symbol": res, "H_confirmed_all_symbols": bool(allok and len(js) > 0) if len(js) else None}
json.dump(rep, open(E["AX_RECEIPT"], "w"), indent=1)
print("AX12_DONE", json.dumps(rep["per_symbol"]), "H_confirmed", rep["H_confirmed_all_symbols"], flush=True)
