"""Canonical live-book P&L reconciliation, 2026-08-26 04Z (first combo anchor) -> latest closed anchor.
READ-ONLY on ~/wide_shadow and ~/dl_quant_live; writes only next to itself.

Definitions (all per nominal anchor N, bps of realized_gross_N unless stated):
  paper_comp      = sum_w w*(prod(1+r5)-1) / sum|w|, r5 = rolling.npz ch0 rows with ts in (N, N+4h]   (target_live weights)
  paper_sum       = same with sum(r5)
  paper_comp_s25  = paper_comp on rows ts in (N+25m, N+4h+25m]   (5m grid closest to the executor pricing moment N+24:02 / median first fill N+24:04)
  paper_comp_s20  = ... (N+20m, N+4h+20m]  (I2's choice, for decomposition only)
  twin_usd        = sum_s qty_s(N) * (mid_s(end) - mid_s(N)); qty from position_readback source fapi/v3/account@post_anchor at anchor N
                    (read ~N+41m), mid from anchors.jsonl mid_at_anchor_vector at the actual anchor_ts (N+24m) and at the END anchor's actual ts
  twin_notl_usd   = sum_s notional_s(N) * (mid_s(end)/mid_s(N) - 1)   (regime_dash / I3 convention; notional = qty*mark at read time)
  funding_usd     = sum funding_paid with settlement_ts in (N, end]
  IS_usd          = sum over this anchor's fills of sgn*(mid_s(N) - fill_px)*qty, sgn=+1 buy/-1 sell  (execution vs anchor mid; >0 = beat mid)
  end             = N+4h when that anchor row exists; else N+8h (extended window, flagged) when that exists.
"""
import os, json, glob, time, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
WS = "/Users/haosiyu/wide_shadow"; PL = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"; RD = "/Users/haosiyu/regime_dash"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def fmt(t): return time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))
def fN(t): return time.strftime("%m-%d %HZ", time.gmtime(float(t)))
H4 = 14400
REP = {"self_sha256": sha(os.path.abspath(__file__)), "rolling_sha256": sha(f"{WS}/state/rolling.npz"), "config_sha256": sha(f"{WS}/shadow_bundle/config.json"),
       "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
z = np.load(f"{WS}/state/rolling.npz"); cts = z["ts"].astype(np.int64); r5 = z["data"][:, :, 0].astype(np.float64); row_of = {int(t): i for i, t in enumerate(cts)}
REP["rolling"] = {"ts0": fmt(cts[0]), "ts1": fmt(cts[-1]), "shape": list(z["data"].shape)}

def win(t0, t1):
    """per-symbol (comp, sum) over rows ts in (t0, t1]; nan if >2 bars missing; None if window not in cache"""
    lo = row_of.get(t0 + 300); hi = row_of.get(t1)
    if lo is None or hi is None: return None
    seg = r5[lo:hi + 1]; n = seg.shape[0]; fin = np.isfinite(seg); zz = np.where(fin, seg, 0.0)
    comp = np.expm1(np.log1p(zz).sum(0)); s = zz.sum(0); bad = fin.sum(0) < n - 2
    comp[bad] = np.nan; s[bad] = np.nan
    return comp, s, n
def paper(w, v):
    g = np.abs(w).sum(); ok = np.isfinite(v)
    return float((w[ok] * v[ok]).sum() / g * 1e4), float(np.abs(w[ok]).sum() / g)

# ---------------- executor logs ----------------
days = sorted(d for d in os.listdir(PL) if d.isdigit() and d >= "20260825")
def jl(d, name):
    p = f"{PL}/{d}/{name}"
    if not os.path.exists(p): return []
    out = []
    for ln in open(p):
        ln = ln.strip()
        if ln:
            try: out.append(json.loads(ln))
            except Exception: pass
    return out
A = {}; RB = {}; RB_other = []; FUND = []; NAV = []; FILLS = {}
for d in days:
    for r in jl(d, "anchors.jsonl"):
        at = float(r["anchor_ts"]); N = int(at // H4 * H4)
        mv = r["mid_at_anchor_vector"]; mv = json.loads(mv) if isinstance(mv, str) else mv
        eb = r.get("external_book") or {}
        A[N] = {"actual_ts": at, "mids": {k: float(v) for k, v in mv.items()}, "realized_gross": float(r.get("realized_gross") or 0.0),
                "halted": bool(r.get("opening_halted")), "day": d, "producer": eb.get("producer"), "gross_mult": (r.get("weights") or {}).get("gross_mult")}
    for r in jl(d, "position_readback.jsonl"):
        at = float(r["anchor_ts"]); src = r.get("source")
        if src == "fapi/v3/account@post_anchor":
            RB.setdefault(at, {})[r["symbol"]] = (float(r["venue_position_qty"]), float(r["venue_position_notional"]))
        else:
            RB_other.append((at, src, float(r.get("read_ts") or at)))
    FUND += [(float(r["settlement_ts"]), r["symbol"], float(r["funding_paid"])) for r in jl(d, "funding.jsonl")]
    NAV += jl(d, "daily_nav.jsonl")
    for r in jl(d, "fills.jsonl"):
        FILLS.setdefault(float(r["anchor_ts"]), []).append((float(r["fill_ts"]), r["symbol"], r["side"], r.get("order_type"), float(r["fill_px"]), float(r.get("fill_notional") or 0.0)))
FUND.sort(); NAV.sort(key=lambda n: float(n["nav_ts"]))
flat_events = sorted(set((at, src) for at, src, rt in RB_other))
REP["non_post_anchor_readbacks"] = [(fmt(at), src) for at, src in flat_events]

# ---------------- per-slot table ----------------
N_FIRST_COMBO = 1787716800            # 2026-08-26 04Z: first anchors.jsonl row with producer=combo_stage_v1 (VERIFIED from external_book.producer)
N_I2_START = 1787702400               # 2026-08-26 00Z (I2's start; producer=shadow_loop_v3, pre-combo)
N_I1_CUTOFF = 1788494400              # 2026-09-04 04Z: last anchor I1 could close at its 12:29Z run (09-04 12Z row did not exist yet)
N_last = max(N for N in A if N + H4 in A)
rows = []
def bridge(N):
    """USD move of the post-anchor position of anchor N from the pricing moment (N+24m; nearest 5m close N+25m) to the NAV snapshot (~N+42m; nearest 5m close N+45m),
    using rolling.npz ch0 bars closing at N+30..N+45m. Explains the residual between twin (priced at N+24m) and daily_nav (priced at ~N+42m)."""
    a = A.get(N)
    if not a: return np.nan, np.nan
    lo = row_of.get(N + 1800); hi = row_of.get(N + 2700)
    if lo is None or hi is None or hi < lo: return np.nan, np.nan
    tot = 0.0; cov = 0.0; miss = 0.0
    for s, (q, nt) in RB.get(a["actual_ts"], {}).items():
        if q == 0: continue
        m0 = a["mids"].get(s); j = sidx.get(s)
        if not m0 or j is None: miss += abs(nt); continue
        seg = r5[lo:hi + 1, j]; seg = np.where(np.isfinite(seg), seg, 0.0); ret = np.expm1(np.log1p(seg).sum())
        tot += q * m0 * ret; cov += abs(nt)
    return tot, cov / (cov + miss) if (cov + miss) > 0 else np.nan
for N in range(1787688000, N_last + 1, H4):          # slots from 2026-08-25 20Z so the 08-26 nav-day has all six windows; canon/I1/I2 membership gated below
    rec = {"N": N, "when": fN(N), "precombo": N < N_FIRST_COMBO}
    tl = f"{WS}/state/target_live/{N}.json"; rec["has_target"] = os.path.exists(tl)
    rec["has_anchor"] = N in A; rec["has_next"] = (N + H4) in A
    a0 = A.get(N); rec["actual_ts"] = a0["actual_ts"] if a0 else None; rec["realized_gross"] = a0["realized_gross"] if a0 else None
    rec["halted"] = a0["halted"] if a0 else None; rec["producer"] = a0["producer"] if a0 else None
    end_N = N + H4 if rec["has_next"] else (N + 2 * H4 if (N + 2 * H4) in A else None)
    rec["end_N"] = end_N; rec["window_h"] = (end_N - N) // 3600 if end_N else None
    reasons = []
    if not rec["has_target"]: reasons.append("no target_live file (producer down: E-0829-B restart)")
    if not rec["has_anchor"]: reasons.append("no anchors.jsonl row (executor did not trade this slot)")
    if a0 and a0["realized_gross"] < 1000: reasons.append("flat book at anchor (opening_halted=%s, realized_gross=%.0f)" % (a0["halted"], a0["realized_gross"]))
    if a0 and end_N:
        for at, src in flat_events:
            if a0["actual_ts"] < at < A[end_N]["actual_ts"]: reasons.append(f"book flattened intra-window ({src} @ {fmt(at)}; E-0826 §4-5e)")
    if rec["has_anchor"] and not rec["has_next"]: reasons.append("next anchor row missing -> no 4h end mid; 8h extended window used" if end_N else "no end anchor at all")
    rec["precombo"] and reasons.append("pre-combo anchor (producer=shadow_loop_v3)")
    rec["reasons"] = reasons
    # paper on nominal grid, 4h
    w = np.zeros(len(syms)); gnorm = None
    if rec["has_target"]:
        doc = json.load(open(tl)); gnorm = doc.get("gross_norm")
        for s, v in doc["weights"].items():
            if s in sidx: w[sidx[s]] = float(v)
    rec["gross_norm"] = gnorm; g = float(np.abs(w).sum()); rec["sum_abs_w"] = g
    for key, off in (("", 0), ("_s25", 1500), ("_s20", 1200)):
        wr = win(N + off, N + H4 + off) if g > 0 else None
        if wr is None or wr[2] != 48: rec["paper_comp" + key] = np.nan; rec["paper_sum" + key] = np.nan; rec["paper_cov" + key] = np.nan
        else:
            rec["paper_comp" + key], rec["paper_cov" + key] = paper(w, wr[0]); rec["paper_sum" + key], _ = paper(w, wr[1])
    if end_N and rec["window_h"] == 8 and g > 0:
        wr = win(N, end_N); rec["paper_comp_ext"] = paper(w, wr[0])[0] if wr and wr[2] == 96 else np.nan
        wr = win(N + 1500, end_N + 1500); rec["paper_comp_s25_ext"] = paper(w, wr[0])[0] if wr and wr[2] == 96 else np.nan
    # twin
    rec.update({"twin_usd": np.nan, "twin_bps": np.nan, "twin_notl_usd": np.nan, "twin_cov": np.nan, "twin_miss_notl": np.nan, "n_pos": 0, "funding_usd": np.nan, "funding_bps": np.nan, "end_ts": None})
    if a0 and end_N:
        a1 = A[end_N]; rec["end_ts"] = a1["actual_ts"]; pos = RB.get(a0["actual_ts"], {})
        tw = 0.0; twn = 0.0; cov = 0.0; miss = 0.0; npos = 0
        for s, (q, nt) in pos.items():
            if q == 0: continue
            npos += 1; m0 = a0["mids"].get(s); m1 = a1["mids"].get(s)
            if m0 and m1: tw += q * (m1 - m0); twn += nt * (m1 / m0 - 1); cov += abs(nt)
            else: miss += abs(nt)
        rg = a0["realized_gross"]
        rec.update({"twin_usd": tw, "twin_notl_usd": twn, "n_pos": npos, "twin_cov": cov / rg if rg else np.nan, "twin_miss_notl": miss, "twin_bps": tw / rg * 1e4 if rg >= 1000 else np.nan})
        f = sum(p for t, s, p in FUND if N < t <= end_N); rec["funding_usd"] = f; rec["funding_bps"] = f / rg * 1e4 if rg >= 1000 else np.nan
        # implementation shortfall vs anchor mid for this anchor's fills
        isd = 0.0; nfl = 0; isn = 0.0
        for ft, s, side, otype, px, notl in FILLS.get(a0["actual_ts"], []):
            m0 = a0["mids"].get(s)
            if not m0 or px <= 0: continue
            q = notl / px; sgn = 1.0 if side == "buy" else -1.0; isd += sgn * (m0 - px) * q; nfl += 1; isn += notl
        rec["IS_usd"] = isd; rec["IS_n_fills"] = nfl; rec["IS_notional"] = isn
    rec["canon"] = (not rec["precombo"]) and rec["has_anchor"] and rec["has_next"] and (a0["realized_gross"] >= 1000) and not any("flattened" in r for r in reasons)
    rec["in_I1"] = (N >= N_FIRST_COMBO) and rec["has_anchor"] and rec["has_target"] and rec["has_next"] and g > 0 and N <= N_I1_CUTOFF   # I1 iterates anchors.jsonl rows (line 36: for A in sorted(anch))
    rec["in_I2"] = (N >= N_I2_START) and rec["has_target"] and rec["has_next"] and bool(a0) and a0["realized_gross"] >= 1000
    rows.append(rec)

def arr(rs, k): return np.array([r.get(k, np.nan) if r.get(k) is not None else np.nan for r in rs], float)
def st(x):
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean": float(x.mean()) if len(x) else np.nan, "sd": float(x.std(ddof=1)) if len(x) > 1 else np.nan, "sum": float(x.sum()) if len(x) else np.nan,
            "se": float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan}
MEAS = ["paper_comp", "paper_sum", "paper_comp_s25", "paper_sum_s25", "paper_comp_s20", "twin_bps", "funding_bps"]
def summarize(rs, label):
    out = {"label": label, "n_rows": len(rs), "anchors": [r["when"] for r in rs]}
    for k in MEAS: out[k] = st(arr(rs, k))
    out["twin_plus_funding"] = st(arr(rs, "twin_bps") + arr(rs, "funding_bps"))
    out["paper_s25_minus_twin"] = st(arr(rs, "paper_comp_s25") - arr(rs, "twin_bps"))
    pc, tw = arr(rs, "paper_comp_s25"), arr(rs, "twin_bps"); ok = np.isfinite(pc) & np.isfinite(tw)
    out["corr_paper_s25_twin"] = float(np.corrcoef(pc[ok], tw[ok])[0, 1]) if ok.sum() > 2 else np.nan
    pc0 = arr(rs, "paper_comp"); ok0 = np.isfinite(pc0) & np.isfinite(tw)
    out["corr_paper_comp_twin"] = float(np.corrcoef(pc0[ok0], tw[ok0])[0, 1]) if ok0.sum() > 2 else np.nan
    return out
canon = [r for r in rows if r["canon"]]
D0903 = {N for N in range(1788379200, 1788451200 + 1, H4)}   # windows ending in nav-day 09-03: N in {09-02 20Z .. 09-03 16Z}
SETS = {"canon": canon, "canon_ex_0903": [r for r in canon if r["N"] not in D0903], "canon_ex_0903_and_0904": [r for r in canon if r["N"] < 1788379200],
        "I1_set": [r for r in rows if r["in_I1"]], "I2_set": [r for r in rows if r["in_I2"]], "canon_plus_flatten_anchor": [r for r in rows if r["canon"] or r["N"] == 1787745600]}
REP["summary"] = {k: summarize(v, k) for k, v in SETS.items()}
REP["excluded"] = [{"when": r["when"], "reasons": r["reasons"], "in_I1": r["in_I1"], "in_I2": r["in_I2"], "paper_comp": r["paper_comp"], "twin_bps": r["twin_bps"], "funding_bps": r["funding_bps"], "window_h": r["window_h"]} for r in rows if not r["canon"]]

# ---------------- decomposition I1 vs I2 ----------------
byN = {r["N"]: r for r in rows}
I1N = {r["N"] for r in rows if r["in_I1"]}; I2N = {r["N"] for r in rows if r["in_I2"]}
dec = {"I1_only": sorted(I1N - I2N), "I2_only": sorted(I2N - I1N), "common": len(I1N & I2N)}
dec["twin"] = {"I1_reported_sum": 86.20524569114517, "I2_reported_sum": 1.4945301827639295,
               "I2_only_anchor_twin": {fN(N): byN[N]["twin_bps"] for N in dec["I2_only"]},
               "I1_only_anchor_twin": {fN(N): byN[N]["twin_bps"] for N in dec["I1_only"]},
               "flatten_anchor_0826_12Z": {"I1_value": 0.0, "I2_value": byN[1787745600]["twin_bps"], "why": "I1 keys position_readback by NOMINAL anchor -> the 12:49:28Z ladder_flatten@post_flatten readback (all qty 0) overwrote the 12:23Z post_anchor readback; I2 keys by actual anchor_ts -> pre-flatten positions held only 26 min"}}
dec["paper_comp"] = {"I1_reported_sum": 149.55, "I2_reported_sum": 101.78489958791373, "I2_only": {fN(N): byN[N]["paper_comp"] for N in dec["I2_only"]}, "I1_only": {fN(N): byN[N]["paper_comp"] for N in dec["I1_only"]}}
com = [byN[N] for N in sorted(I1N & I2N)]
dec["shift_on_common"] = {"s25_mean": float(np.nanmean(arr(com, "paper_comp_s25"))), "s20_mean": float(np.nanmean(arr(com, "paper_comp_s20"))), "n": len(com),
                          "mean_abs_diff_s25_s20": float(np.nanmean(np.abs(arr(com, "paper_comp_s25") - arr(com, "paper_comp_s20"))))}
REP["decomposition"] = dec

# ---------------- daily vs daily_nav ----------------
last_by_day = {}
for n in NAV: last_by_day[n["day"]] = n
dl = sorted(last_by_day); daily = []
for i in range(1, len(dl)):
    D, Dp = dl[i], dl[i - 1]
    if D < "20260826": continue
    n1, n0 = last_by_day[D], last_by_day[Dp]; t0, t1 = float(n0["nav_ts"]), float(n1["nav_ts"])
    ext = float(n1.get("external_flow_usdt") or 0.0); eq = float(n1["nav"]) - float(n0["nav"]) - ext
    wins = [r for r in rows if r["end_ts"] is not None and t0 < r["end_ts"] <= t1 and np.isfinite(r["twin_usd"])]
    tw = sum(r["twin_usd"] for r in wins); fw = sum(r["funding_usd"] for r in wins); pp = sum((r["paper_comp"] if np.isfinite(r["paper_comp"]) else 0.0) / 1e4 * (r["realized_gross"] or 0) for r in wins)
    pps = sum((r["paper_comp_s25"] if np.isfinite(r["paper_comp_s25"]) else 0.0) / 1e4 * (r["realized_gross"] or 0) for r in wins)
    fspan = sum(p for t, s, p in FUND if t0 < t <= t1)
    isum = sum(r.get("IS_usd", 0.0) for r in rows if r["actual_ts"] is not None and t0 < r["actual_ts"] <= t1)
    day0 = time.mktime(time.strptime(D + "Z", "%Y%m%d%Z")) if False else None
    d00 = int(time.strftime("%s", time.gmtime(t1)) if False else 0)
    # 00:00Z of day D (UTC)
    import calendar; d00 = calendar.timegm(time.strptime(D, "%Y%m%d"))
    f_since00 = sum(p for t, s, p in FUND if d00 < t <= t1); f_since00_incl = sum(p for t, s, p in FUND if d00 <= t <= t1)
    venue_ff = ((n1.get("realised_by_type") or {}).get("FUNDING_FEE"))
    notes = [r["when"] + ":" + ";".join(r["reasons"]) for r in wins if r["reasons"]]
    Nend, Nstart = int(t1 // H4 * H4), int(t0 // H4 * H4)
    b_end, b_end_cov = bridge(Nend); b_start, b_start_cov = bridge(Nstart)
    resid = eq - (tw + fspan); resid_adj = resid - (b_end if np.isfinite(b_end) else 0.0) + (b_start if np.isfinite(b_start) else 0.0) - isum
    daily.append({"day": D, "span": f"({fmt(t0)}, {fmt(t1)}]", "nav_prev": float(n0["nav"]), "nav": float(n1["nav"]), "ext_flow": ext, "equity_delta_net": eq,
                  "bridge_end": b_end, "bridge_end_anchor": fN(Nend), "bridge_start": b_start, "bridge_start_anchor": fN(Nstart), "residual_after_bridge_and_IS": resid_adj, "funding_jsonl_since_00Z_incl": f_since00_incl,
                  "n_windows": len(wins), "windows": [r["when"] + ("(8h)" if r["window_h"] == 8 else "") for r in wins], "twin_usd": tw, "funding_in_windows": fw, "funding_in_span": fspan,
                  "twin_plus_funding": tw + fspan, "residual": eq - (tw + fspan), "IS_usd_in_span": isum, "residual_after_IS": eq - (tw + fspan) - isum,
                  "paper_usd": pp, "paper_s25_usd": pps, "paper_plus_funding": pp + fspan, "paper_s25_plus_funding": pps + fspan,
                  "funding_jsonl_since_00Z": f_since00, "venue_FUNDING_FEE_since_00Z": venue_ff, "venue_realised_since_00Z": n1.get("realised_pnl"), "venue_COMMISSION_since_00Z": ((n1.get("realised_by_type") or {}).get("COMMISSION")),
                  "notes": notes, "partial_day": (D == dl[-1])})
REP["daily"] = daily
# 08-26 flatten-adjusted variant: replace the 12Z window (twin invalid) by the executor's own equity delta between the 12:45Z and 16:38Z nav rows net of funding in that span
nav26 = [n for n in NAV if n["day"] == "20260826"]; r12 = byN[1787745600]
n1245 = next(n for n in nav26 if abs(float(n["nav_ts"]) - r12["actual_ts"]) < 3600); n1638 = next(n for n in nav26 if 1787760000 < float(n["nav_ts"]) < 1787774400)
fl_span = (float(n1245["nav_ts"]), float(n1638["nav_ts"])); f_fl = sum(p for t, s, p in FUND if fl_span[0] < t <= fl_span[1])
eq_fl = float(n1638["nav"]) - float(n1245["nav"])
d26 = next(d for d in daily if d["day"] == "20260826")
d26_adj = {"twin_12Z_window_as_computed": r12["twin_usd"], "executor_equity_12:45Z->16:38Z": eq_fl, "funding_in_that_span": f_fl, "flatten_realised_price_pnl_est": eq_fl - f_fl,
           "twin_plus_funding_adjusted": d26["twin_plus_funding"] - r12["twin_usd"] + (eq_fl - f_fl), "residual_adjusted": d26["equity_delta_net"] - (d26["twin_plus_funding"] - r12["twin_usd"] + (eq_fl - f_fl))}
REP["daily_0826_flatten_adjusted"] = d26_adj
# merged 08-29 + 08-30 block (the 08-29 16Z window runs 8h across the 20:29Z nav snapshot)
d29 = next(d for d in daily if d["day"] == "20260829"); d30 = next(d for d in daily if d["day"] == "20260830")
REP["daily_merged_0829_0830"] = {"equity_delta_net": d29["equity_delta_net"] + d30["equity_delta_net"], "twin_plus_funding": d29["twin_plus_funding"] + d30["twin_plus_funding"],
                                 "residual": d29["residual"] + d30["residual"], "IS": d29["IS_usd_in_span"] + d30["IS_usd_in_span"], "n_windows": d29["n_windows"] + d30["n_windows"]}
full = [d for d in daily if not d["partial_day"]]
def dsum(ds, k): return float(sum(d[k] for d in ds))
REP["daily_summary"] = {"days": [d["day"] for d in daily], "sum_equity_delta_net_all": dsum(daily, "equity_delta_net"), "sum_twin_plus_funding_all": dsum(daily, "twin_plus_funding"),
                        "sum_residual_all": dsum(daily, "residual"), "sum_IS_all": dsum(daily, "IS_usd_in_span"),
                        "sum_equity_delta_net_0827_0903": dsum([d for d in daily if "20260827" <= d["day"] <= "20260903"], "equity_delta_net"),
                        "sum_twin_plus_funding_0827_0903": dsum([d for d in daily if "20260827" <= d["day"] <= "20260903"], "twin_plus_funding"),
                        "sum_residual_0827_0903": dsum([d for d in daily if "20260827" <= d["day"] <= "20260903"], "residual"),
                        "sum_IS_0827_0903": dsum([d for d in daily if "20260827" <= d["day"] <= "20260903"], "IS_usd_in_span"),
                        "sum_equity_delta_net_0827_0902": dsum([d for d in daily if "20260827" <= d["day"] <= "20260902"], "equity_delta_net"),
                        "sum_twin_plus_funding_0827_0902": dsum([d for d in daily if "20260827" <= d["day"] <= "20260902"], "twin_plus_funding"),
                        "sum_residual_0827_0902": dsum([d for d in daily if "20260827" <= d["day"] <= "20260902"], "residual")}
# ---------------- I3 comparison on its own anchors ----------------
BA = [json.loads(l) for l in open(f"{RD}/beta_alpha.jsonl")]
i3 = []
for b in BA:
    N = int(b["anchor_ts"]); r = byN.get(N)
    if r is None or b.get("sleeve_total_usdt") is None: continue
    i3.append({"when": fN(N), "I3_sleeve_total": b["sleeve_total_usdt"], "canon_twin_notl_plus_funding": (r["twin_notl_usd"] + r["funding_usd"]) if np.isfinite(r["twin_notl_usd"]) else None,
               "canon_twin_qty_plus_funding": (r["twin_usd"] + r["funding_usd"]) if np.isfinite(r["twin_usd"]) else None, "I3_beta_pnl": b["beta_pnl_usdt"], "I3_btc_ret_4h(unshifted cache)": b["btc_ret_4h"],
               "venue_btc_ratio": (A[N + H4]["mids"]["BTCUSDT"] / A[N]["mids"]["BTCUSDT"] - 1) if (N + H4) in A else None, "I3_gross": b["gross_usdt"], "canon_rg": r["realized_gross"]})
REP["I3_rows"] = i3
REP["rows"] = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()} for r in rows]
json.dump(REP, open(f"{HERE}/canon_report.json", "w"), indent=1, default=str)

# ---------------- print ----------------
print("RUN", REP["run_utc"], "self", REP["self_sha256"][:16], "rolling", REP["rolling_sha256"][:16], REP["rolling"])
print("non-post_anchor readbacks:", REP["non_post_anchor_readbacks"])
print("\n=== PER-SLOT TABLE (bps of realized_gross; paper on target_live weights) ===")
print("N | canon | I1 I2 | wh | rg | paper_comp paper_sum | s25_comp s25_sum | s20_comp | twin | fund | twin+fund | IS$ | reasons")
for r in rows:
    f = lambda k: ("   nan" if not np.isfinite(r.get(k, np.nan)) else f"{r[k]:+7.2f}")
    tf = r["twin_bps"] + r["funding_bps"] if np.isfinite(r["twin_bps"]) and np.isfinite(r["funding_bps"]) else np.nan
    print(f"{r['when']} | {'Y' if r['canon'] else '-'} | {'1' if r['in_I1'] else '.'}{'2' if r['in_I2'] else '.'} | {r['window_h'] or '-'} | {(r['realized_gross'] or 0):7.0f} | {f('paper_comp')} {f('paper_sum')} | {f('paper_comp_s25')} {f('paper_sum_s25')} | {f('paper_comp_s20')} | {f('twin_bps')} | {f('funding_bps')} | {('   nan' if not np.isfinite(tf) else f'{tf:+7.2f}')} | {r.get('IS_usd', float('nan')):+7.1f} | {'; '.join(r['reasons'])}")
print("\n=== SUMMARY BY SET (mean / sd / n / sum, bps per anchor) ===")
for k, s in REP["summary"].items():
    print(f"[{k}] n_rows={s['n_rows']}")
    for m in MEAS + ["twin_plus_funding", "paper_s25_minus_twin"]:
        v = s[m]; print(f"   {m:22s} n={v['n']:2d} mean={v['mean']:+7.3f} sd={v['sd']:6.2f} se={v['se']:5.2f} sum={v['sum']:+8.2f}")
    print(f"   corr(paper_comp,twin)={s['corr_paper_comp_twin']:.3f} corr(paper_s25,twin)={s['corr_paper_s25_twin']:.3f}")
print("\n=== DECOMPOSITION ===", json.dumps(dec, indent=1, default=str))
print("\n=== DAILY vs daily_nav (USDT) ===")
print("day | span | nav_prev->nav | ext | eqΔnet | nwin | twin$ | fund$(span) | twin+fund | resid | IS$ | bridge_end(anchor) | bridge_start(anchor) | resid−bridgeΔ−IS | paper$ | paper_s25$ | fund.jsonl since00Z (excl/incl 00Z) vs venue FUNDING_FEE | notes")
for d in daily:
    be = "nan" if not np.isfinite(d['bridge_end']) else f"{d['bridge_end']:+7.1f}"; bs = "nan" if not np.isfinite(d['bridge_start']) else f"{d['bridge_start']:+7.1f}"
    print(f"{d['day']} | {d['span']} | {d['nav_prev']:.0f}->{d['nav']:.0f} | {d['ext_flow']:.0f} | {d['equity_delta_net']:+8.1f} | {d['n_windows']} | {d['twin_usd']:+8.1f} | {d['funding_in_span']:+7.1f} | {d['twin_plus_funding']:+8.1f} | {d['residual']:+7.1f} | {d['IS_usd_in_span']:+6.1f} | {be}({d['bridge_end_anchor']}) | {bs}({d['bridge_start_anchor']}) | {d['residual_after_bridge_and_IS']:+7.1f} | {d['paper_usd']:+8.1f} | {d['paper_s25_usd']:+8.1f} | {d['funding_jsonl_since_00Z']:+.2f}/{d['funding_jsonl_since_00Z_incl']:+.2f} vs {d['venue_FUNDING_FEE_since_00Z']:+.2f} | {'PARTIAL ' if d['partial_day'] else ''}{d['windows']} {d['notes']}")
print("08-26 flatten-adjusted:", json.dumps(d26_adj, indent=1))
print("merged 08-29+08-30:", REP["daily_merged_0829_0830"])
print("daily summary:", json.dumps(REP["daily_summary"], indent=1))
print("\n=== I3 (beta_alpha) sleeve vs canon twin(notional)+funding, USDT ===")
for x in i3: print(x)
print("CANON_DONE")
