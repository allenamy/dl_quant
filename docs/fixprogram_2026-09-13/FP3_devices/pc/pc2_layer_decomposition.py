#!/usr/bin/env python3
"""FP3 P-C2: layer decomposition of one UTC day from the executor's own records (no replay needed). Per anchor A:
 L0 producer target   = target_live weights / gross_norm × sizing.gross (phase_A)            — the strategy's intent
 L1 executor target   = orders target_w × anchors.target_gross                               — after withhold / stop / reshape / venue cap / dust
 L2 request intent    = L1 restricted to names with a placed request (skips removed)
 L3 actual book       = post-anchor readback notional (venue)                                 — after fills / rejects / partial expiry / protective flatten
Marks: readback |notional|/|qty| per symbol per anchor ⇒ 4h return r(A→A+4h) for every held or targeted name that has marks at both ends (else excluded, counted).
P&L of layer L over the anchor = Σ L_s × r_s (USDT, at the layer's own notional), so differences between layers are the P&L attributable to that layer.
Protective flattens (readback source ladder_flatten@post_flatten) are listed with time; after a flatten L3 = 0 for the rest of the anchor (the actual book), while L0..L2
keep earning/losing ⇒ the gap is the flatten's P&L footprint. usage: pc2_layer_decomposition.py <YYYYMMDD> <out.json>"""
import sys, os, json, time, collections
DAY, OUT = sys.argv[1], sys.argv[2]; REPO = os.path.expanduser("~/dl_quant_live"); WS = os.path.expanduser("~/wide_shadow"); P = f"{REPO}/state/live/pilot_log"
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t))); d0 = int(time.mktime(time.strptime(DAY, "%Y%m%d")) - time.timezone); anchors = [d0 + 14400 * k for k in range(6)]
def rows(day, name):
    f = f"{P}/{day}/{name}.jsonl"; return [json.loads(l) for l in open(f) if l.strip()] if os.path.exists(f) else []
nxt = time.strftime("%Y%m%d", time.gmtime(d0 + 86400)); prv = time.strftime("%Y%m%d", time.gmtime(d0 - 86400))
rb = rows(prv, "position_readback") + rows(DAY, "position_readback") + rows(nxt, "position_readback"); od = rows(DAY, "orders") + rows(nxt, "orders"); an = rows(DAY, "anchors") + rows(nxt, "anchors")
pa = {}
for l in open(f"{REPO}/state/anchor_runs.log"):
    if " phase_A: " in l:
        try: d = json.loads(l.split(" phase_A: ", 1)[1]); a = (d.get("external_wait") or {}).get("nominal_anchor_ts") or d.get("anchor_ts"); pa[int(a)] = d
        except Exception: pass
def marks_at(A):                                         # post-anchor snapshot of anchor A (bucket [A, A+4h)), marks and notionals
    snap = [r for r in rb if A <= float(r["anchor_ts"]) < A + 14400 and str(r.get("source", "")).endswith("@post_anchor")]
    m = {}; n = {}
    for r in snap:
        q = float(r["venue_position_qty"]); v = float(r["venue_position_notional"])
        if q: m[r["symbol"]] = abs(v) / abs(q)
        n[r["symbol"]] = v
    return m, n
flats = sorted({(r["symbol"], int(float(r["read_ts"]) // 60 * 60)) for r in rb if "flatten" in str(r.get("source", ""))}); flat_times = sorted({t for _, t in flats if d0 <= t < d0 + 86400})
# v2: 4h returns from the PRODUCER's own 5-minute panel (rolling.npz ret5 = 5m simple returns, 829 symbols, 40 days) so that names without a venue position (after a
# flatten, or never held) are still priced; readback marks are the fallback. r(A→A+4h) = Π(1 + ret5) over the 48 bars in (A, A+4h] − 1.
import numpy as np
_R = np.load(f"{WS}/state/rolling.npz", allow_pickle=True); _rts = _R["ts"].astype(np.int64); _ret5 = np.asarray(_R["data"][:, :, 0], np.float64); _syms = [str(x) for x in np.load(f"{WS}/fea171/xfer_syms.npz", allow_pickle=True)["symbols"]]; _sidx = {s: i for i, s in enumerate(_syms)}
def panel_ret(A):
    lo, hi = A, A + 14400; m = (_rts > lo) & (_rts <= hi)
    if m.sum() != 48: return {}
    seg = _ret5[m]; ok = np.isfinite(seg).all(0); r = np.prod(1.0 + np.where(np.isfinite(seg), seg, 0.0), axis=0) - 1.0
    return {s: float(r[_sidx[s]]) for s in _syms if ok[_sidx[s]]}
out = {"device": "pc2_layer_decomposition.py", "utc": time.strftime("%FT%TZ", time.gmtime()), "day": DAY, "version": "v2 producer-panel returns", "protective_flattens_utc": [U(t) for t in flat_times], "anchors": []}
tot = collections.defaultdict(float)
for A in anchors:
    d = pa.get(A); rec = {"anchor": A, "utc": U(A)}
    if not d or not (d.get("sizing") or {}).get("gross"): rec["status"] = "NO_PHASE_A"; out["anchors"].append(rec); continue
    G = float(d["sizing"]["gross"]); anr = [r for r in an if r.get("rebalance_id") == d["rebalance_id"]]
    if not anr: rec["status"] = "NO_ANCHORS_ROW"; out["anchors"].append(rec); continue
    anr = anr[-1]; gn = float(anr["external_book"]["gross_norm"]); Gt = float(anr["target_gross"])
    tf = f"{WS}/state/target_live/{A}.json"
    L0 = {s: float(w) / gn * G for s, w in json.load(open(tf))["weights"].items()} if os.path.exists(tf) else None
    oa = [r for r in od if r.get("rebalance_id") == d["rebalance_id"]]; first = {}
    for r in sorted(oa, key=lambda r: (r["symbol"], int(r.get("attempt_idx") or 0))): first.setdefault(r["symbol"], r)
    L1 = {s: float(r["target_w"]) * Gt for s, r in first.items()}; L2 = {s: v for s, v in L1.items() if not str(first[s].get("terminal_reason", "")).startswith("skipped")}
    m0, n_prev = marks_at(A - 14400); m1, n_post = marks_at(A); L3 = n_post
    m_next, _ = marks_at(A + 14400)
    ret_marks = {s: (m_next[s] / m1[s] - 1.0) for s in m1 if s in m_next and m1[s] > 0}
    ret = panel_ret(A); ret_src = "producer_panel_ret5"
    if not ret: ret = ret_marks; ret_src = "readback_marks_fallback"
    rec["return_source"] = ret_src; rec["n_priced_panel"] = len(ret); rec["panel_vs_marks_max_abs_diff"] = (max((abs(ret[s] - ret_marks[s]) for s in ret_marks if s in ret), default=None) if ret_src == "producer_panel_ret5" else None)
    def pnl(L): 
        cov = [s for s in L if s in ret]; return float(sum(L[s] * ret[s] for s in cov)), len(cov), len(L)
    layers = {"L0_producer": L0, "L1_executor_target": L1, "L2_request_intent": L2, "L3_actual_post_anchor": L3}
    for k, L in layers.items():
        if L is None: rec[k] = None; continue
        p, cov, n = pnl(L); rec[k] = {"gross": float(sum(abs(v) for v in L.values())), "net": float(sum(L.values())), "n": n, "pnl_next4h_usdt": p, "n_priced": cov}
        tot[k] += p
    rec["flatten_in_anchor"] = [U(t) for t in flat_times if A <= t < A + 14400]
    if L0 and L1:
        popped = [s for s in L0 if s not in L1]; rec["L0_to_L1"] = {"n_popped_or_absent": len(popped), "mass_popped": float(sum(abs(L0[s]) for s in popped)), "n_L1_not_in_L0": len([s for s in L1 if s not in L0]), "gross_L0": rec["L0_producer"]["gross"], "gross_L1": rec["L1_executor_target"]["gross"]}
    out["anchors"].append(rec)
out["day_totals_pnl_next4h_usdt"] = dict(tot); json.dump(out, open(OUT, "w"), indent=1, default=str)
print(DAY, "flattens:", out["protective_flattens_utc"]); print("day totals (next-4h P&L by layer, USDT):", {k: round(v, 0) for k, v in tot.items()})
for r in out["anchors"]:
    if r.get("status"): print("  ", r["utc"], r["status"]); continue
    print("  ", r["utc"], {k[:2]: (round(r[k]["gross"] / 1000, 1), round(r[k]["pnl_next4h_usdt"], 0), f"{r[k]['n_priced']}/{r[k]['n']}") for k in ("L0_producer", "L1_executor_target", "L2_request_intent", "L3_actual_post_anchor") if r.get(k)}, "FLAT" if r["flatten_in_anchor"] else "", r.get("return_source", "")[:6], "|panel−marks| max", (round(r["panel_vs_marks_max_abs_diff"], 4) if r.get("panel_vs_marks_max_abs_diff") is not None else None))
