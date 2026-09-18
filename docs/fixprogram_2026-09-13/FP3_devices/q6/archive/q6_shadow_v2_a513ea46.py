#!/usr/bin/env python3
"""FP3 Q6 SHADOW (read-only; nothing wired into production): cross-window reconciliation carried from an EPISODE start instead of window by window.
Per symbol s, episodes are split at protective flattens (baseline reset = the venue's own flat). Inside an episode, at anchor t_k:
   identity   Q_s(t_k) − Q_s(t_0) = Σ known fills (t_0, t_k]  +  Σ_open σ_i x_i(t_k)
where known fills are the terminal requests with a final confirmed quantity (request_ledger) and x_i are the OPEN requests (non-final): their joint feasible
range is computed with an LP (continuous relaxation of the PREREG joint set: birth / monotone / post-terminal / evidence lower bounds are hard; observation
equations admitted chronologically, the first that empties the set is EXCLUDED and recorded). E_s(t_k) = distance from the admitted feasible range to the
observed reading (contracts, and × mark in USDT). A distance > 0 in the relaxation is a SOUND unexplained balance (the integer set is a subset); distance 0 does
not prove integer feasibility — the shadow errs towards not flagging. Compared per anchor with the executor's own window view (anchors.known_gaps).
usage: q6_shadow.py <from_day> <to_day> <out.json>"""
import sys, os, json, time, glob, collections
import numpy as np
from scipy.optimize import linprog
F, T, OUT = sys.argv[1], sys.argv[2], sys.argv[3]; REPO = os.path.expanduser("~/dl_quant_live"); P = f"{REPO}/state/live/pilot_log"
days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if F <= d.split("/")[-1] <= T)
rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t))); B = lambda t: int(float(t) // 14400 * 14400)
rb = [r for d in days for r in rows(d, "position_readback")]; od = [r for d in days for r in rows(d, "orders")]; an = [r for d in days for r in rows(d, "anchors")]
by_tid = {}
for d in days:
    for r in rows(d, "fills"):
        t = r.get("trade_id"); k = (r.get("backfilled_utc") or "", d)
        if t not in by_tid or k >= by_tid[t][0]: by_tid[t] = (k, r)
FILLS = collections.defaultdict(list)                                                    # symbol → [(fill_ts, signed contracts)]
for _, r in by_tid.values():
    px = float(r.get("fill_px") or 0.0)
    if px > 0: FILLS[r["symbol"]].append((float(r["fill_ts"]), float(r["fill_notional"]) / px * (1.0 if str(r.get("side", "")).upper() == "BUY" else -1.0)))
for s_ in FILLS: FILLS[s_].sort()
post = collections.defaultdict(dict); marks = collections.defaultdict(dict); last_in_bucket = collections.defaultdict(dict); last_ts = collections.defaultdict(dict)
for r in rb:
    q = float(r["venue_position_qty"]); a_ = B(r["anchor_ts"] if not "flatten" in str(r.get("source", "")) else r["read_ts"]); t_ = float(r["read_ts"])
    if str(r.get("source", "")).endswith("@post_anchor"):
        post[a_][r["symbol"]] = q
        if q: marks[a_][r["symbol"]] = abs(float(r["venue_position_notional"])) / abs(q)
    if t_ >= last_ts[a_].get(r["symbol"], -1): last_ts[a_][r["symbol"]] = t_; last_in_bucket[a_][r["symbol"]] = (q, t_)   # the LAST reading of the bucket (post-flatten when a flatten happened)
flat_anchors = sorted({B(r["read_ts"]) for r in rb if "flatten" in str(r.get("source", ""))})
anchors = sorted(post); kidx = {a: i for i, a in enumerate(anchors)}
gaps_rec = {}
for r in an:
    kg = r.get("known_gaps") or {}; gaps_rec[B(r["anchor_ts"])] = {"n_named": kg.get("n_named"), "gross_usdt": kg.get("gross_usdt"), "names": [x.get("symbol") for x in (kg.get("names") or [])]}
# ── requests per symbol from the request ledger ──
REQ = collections.defaultdict(list)
for o in od:
    a = B(o["anchor_ts"]); s = o["symbol"]; side = 1 if str(o.get("side", "")).lower() == "buy" else -1
    for e in (o.get("request_ledger") or []):
        cap = float(e.get("qty") or 0.0); cq = e.get("confirmed_qty"); fin = bool(e.get("confirmed_qty_final")) and bool(e.get("terminal"))
        REQ[s].append({"rid": e.get("client_id"), "side": side, "cap": cap, "birth": a, "terminal": a if e.get("terminal") else None, "lower": float(cq or 0.0), "exact": (float(cq) if fin and cq is not None else None)})
    if not o.get("request_ledger") and o.get("terminal_reason") == "venue_reject": REQ[s].append({"rid": f"{o.get('rebalance_id')}-{s}-rej", "side": side, "cap": 0.0, "birth": a, "terminal": a, "lower": 0.0, "exact": 0.0})
def episodes():
    cuts = [anchors[0]] + [a for a in flat_anchors if a in kidx]; cuts = sorted(set(cuts))
    for i, c in enumerate(cuts):
        end = cuts[i + 1] if i + 1 < len(cuts) else anchors[-1] + 1
        yield [a for a in anchors if c <= a < end]
def lp_range(open_reqs, admitted, k_now, obs_now):
    """feasible range of Σσx at k_now given admitted equalities on earlier anchors; returns (lo, hi, feasible)"""
    if not open_reqs: return 0.0, 0.0, True
    ks = sorted({k for _, k in admitted} | {k_now}); n = len(open_reqs); m = len(ks); idx = lambda i, j: i * m + j
    A_eq, b_eq, A_ub, b_ub, bounds = [], [], [], [], []
    for i, r in enumerate(open_reqs):
        for j, k in enumerate(ks):
            lo = 0.0 if k >= r["birth"] else 0.0; hi = r["cap"] if k >= r["birth"] else 0.0
            if r["terminal"] is not None and k >= r["terminal"]: lo = max(lo, r["lower"])
            bounds.append((lo, hi))
            if j > 0: row = np.zeros(n * m); row[idx(i, j - 1)] = 1; row[idx(i, j)] = -1; A_ub.append(row); b_ub.append(0.0)   # monotone
    for (obs, k) in admitted:
        row = np.zeros(n * m); j = ks.index(k)
        for i, r in enumerate(open_reqs): row[idx(i, j)] = r["side"]
        A_eq.append(row); b_eq.append(obs)
    c = np.zeros(n * m); j = ks.index(k_now)
    for i, r in enumerate(open_reqs): c[idx(i, j)] = r["side"]
    res_lo = linprog(c, A_ub=np.array(A_ub) if A_ub else None, b_ub=b_ub or None, A_eq=np.array(A_eq) if A_eq else None, b_eq=b_eq or None, bounds=bounds, method="highs")
    if res_lo.status != 0: return None, None, False
    res_hi = linprog(-c, A_ub=np.array(A_ub) if A_ub else None, b_ub=b_ub or None, A_eq=np.array(A_eq) if A_eq else None, b_eq=b_eq or None, bounds=bounds, method="highs")
    return float(res_lo.fun), float(-res_hi.fun), True
out_rows = []; per_anchor = collections.defaultdict(lambda: {"n_symbols_flagged": 0, "unexplained_usdt": 0.0, "n_excluded_obs": 0, "n_unmeasurable": 0})
symbols = sorted(set(s for a in anchors for s in post[a]) | set(REQ))
for s in symbols:
    reqs = sorted(REQ.get(s, []), key=lambda r: r["birth"])
    for ep in episodes():
        if len(ep) < 2: continue
        t0 = ep[0]; q0, t0_read = last_in_bucket[t0].get(s, (0.0, float(t0))); admitted = []; excluded = []   # episode baseline = last reading of the start bucket (post-flatten if any)
        for a in ep[1:]:
            if s not in post[a]: continue
            a_read = last_ts[a].get(s, float(a))
            known = sum(q for (ft, q) in FILLS.get(s, []) if t0_read < ft <= a_read)                                   # ALL recorded fills in (t0_read, a_read] — fills.jsonl, deduped
            open_reqs = [r for r in reqs if t0 < r["birth"] <= a and r["exact"] is None]                              # requests without a final confirmed quantity: their fills may be missing from the ledger
            obs = post[a][s] - q0 - known                                              # RHS for the open requests
            lo, hi, ok = lp_range(open_reqs, admitted, a, obs)
            if not ok: per_anchor[a]["n_unmeasurable"] += 1; continue
            dist = 0.0 if lo - 1e-9 <= obs <= hi + 1e-9 else (lo - obs if obs < lo else obs - hi)
            if dist > 1e-9:
                excluded.append(a); per_anchor[a]["n_excluded_obs"] += 1
            else:
                admitted.append((obs, a))
            mk = marks[a].get(s) or marks.get(a - 14400, {}).get(s) or 0.0; usd = abs(dist) * mk
            if usd > 1.0:
                per_anchor[a]["n_symbols_flagged"] += 1; per_anchor[a]["unexplained_usdt"] += usd
                out_rows.append({"symbol": s, "anchor": a, "utc": U(a), "episode_start": U(t0), "distance_contracts": dist, "unexplained_usdt": usd, "n_open_requests": len(open_reqs), "feasible_range": [lo, hi], "observed_rhs": obs, "in_executor_known_gaps": s in (gaps_rec.get(a, {}).get("names") or [])})
summary = []
for a in anchors:
    pa = per_anchor[a]; g = gaps_rec.get(a, {})
    summary.append({"anchor": a, "utc": U(a), "shadow_n_flagged": pa["n_symbols_flagged"], "shadow_unexplained_usdt": round(pa["unexplained_usdt"], 2), "shadow_excluded_obs": pa["n_excluded_obs"], "shadow_unmeasurable": pa["n_unmeasurable"], "executor_known_gaps_n": g.get("n_named"), "executor_known_gaps_usdt": g.get("gross_usdt")})
persist = collections.Counter()
for r in out_rows: persist[r["symbol"]] += 1
out = {"device": "q6_shadow.py", "utc": time.strftime("%FT%TZ", time.gmtime()), "window": [days[0], days[-1]], "n_anchors": len(anchors), "n_symbols": len(symbols), "episodes_split_at_flattens": [U(a) for a in flat_anchors if a in kidx], "n_flagged_rows": len(out_rows), "symbols_flagged_ge_6_anchors": {s: n for s, n in persist.items() if n >= 6}, "per_anchor": summary, "rows": out_rows[:2000], "known_fills_source": "fills.jsonl deduped by trade_id (signed contracts); request_ledger defines OPEN requests only", "contract_note": "LP relaxation of PREREG_reconcile_carry_forward_unexplained §1c: distance>0 sound, distance=0 not a proof of integer feasibility; episodes reset at protective flattens; non-request flows other than flattens not modelled (manual corrections ⇒ would appear as persistent unexplained)"}
json.dump(out, open(OUT, "w"), indent=1, default=str)
tot_sh = sum(r["shadow_unexplained_usdt"] for r in summary); print("window", out["window"], "anchors", len(anchors), "symbols", len(symbols), "| flagged rows", len(out_rows), "| symbols flagged ≥6 anchors:", len(out["symbols_flagged_ge_6_anchors"]))
print("per-anchor (last 8): shadow flagged / unexplained USDT vs executor known_gaps n / USDT")
for r in summary[-8:]: print("  ", r["utc"], r["shadow_n_flagged"], round(r["shadow_unexplained_usdt"]), "|", r["executor_known_gaps_n"], r["executor_known_gaps_usdt"])
print("anchors where shadow flags but executor known_gaps is 0/None:", sum(1 for r in summary if r["shadow_n_flagged"] > 0 and not r["executor_known_gaps_n"]), "| executor flags but shadow 0:", sum(1 for r in summary if r["shadow_n_flagged"] == 0 and (r["executor_known_gaps_n"] or 0) > 0))
print("most persistent:", sorted(out["symbols_flagged_ge_6_anchors"].items(), key=lambda kv: -kv[1])[:8])
