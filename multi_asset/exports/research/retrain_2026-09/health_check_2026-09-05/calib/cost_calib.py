"""cost_calib.py — live execution cost & fill calibration from the executor pilot logs.
READ-ONLY on ~/dl_quant_live and ~/wide_shadow. Writes cost_calib.json + calib_run.log next to itself.
Method frozen in docs/PREREG_live_form_health_check_2026-09-05.md §1 (items a-f); every number below is printed.

Row semantics (VERIFIED from live/binance_executor.py _requote_benign_rejects and the per-(rebalance,symbol) row
patterns): one "leg" = one (rebalance_id, symbol). Attempt-1 maker post-only order -> terminal row (filled /
partial_expired / venue_reject[-5022] / skipped_min_notional / blocked_by_halt). A -5022 first refusal is re-quoted ONCE
as maker: if it rests, its terminal row is written as a SECOND attempt-1 maker row for the same leg (the executor passes
attempt=1 positionally on the normal collect path); if refused again, an attempt-2 maker venue_reject row is written and
the residual goes to the taker top-up tagged topup_source=from_reject. Partial maker fills top up via topup_source=
from_partial (chase experiment randomises whether the residual is sent).

Units: notional in USDT (one-sided), fees in USDT (fee_paid = commission_BNB x bookTicker BNB mid at collect, exact on
all 6908 fee rows), bps = 1e-4 of the notional in the denominator named at each table.
"""
import os, json, time, hashlib, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PL = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
WS = os.path.expanduser("~/wide_shadow")
H4 = 14400
DAY0, DAY1 = "20260826", "20260905"
N_FIRST_COMBO = 1787716800          # 2026-08-26 04Z, first anchors.jsonl row with external_book.producer = combo_stage_v1 (VERIFIED)

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def fN(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
def jl(d, name):
    p = f"{PL}/{d}/{name}.jsonl"
    if not os.path.exists(p): return []
    out = []
    for ln in open(p):
        ln = ln.strip()
        if ln: out.append(json.loads(ln))
    return out

REP = {"run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "self_sha256": sha(os.path.abspath(__file__)),
       "inputs": {"pilot_log_root": PL, "days": [], "rolling_npz_sha256": sha(f"{WS}/state/rolling.npz"),
                  "config_json_sha256": sha(f"{WS}/shadow_bundle/config.json")}}
days = [d for d in sorted(os.listdir(PL)) if d.isdigit() and DAY0 <= d <= DAY1]
REP["inputs"]["days"] = days
O, F, A, NAV, FUND = [], [], [], [], []
for d in days:
    O += jl(d, "orders"); F += jl(d, "fills"); A += jl(d, "anchors"); NAV += jl(d, "daily_nav"); FUND += jl(d, "funding")
print(f"RUN {REP['run_utc']} self {REP['self_sha256'][:16]} days {days[0]}..{days[-1]} orders {len(O)} fills {len(F)} anchors {len(A)}")

# ---------------- anchors ----------------
ANC = {}
for r in A:
    at = float(r["anchor_ts"]); N = int(at // H4 * H4)
    eb = r.get("external_book") or {}
    ANC[N] = {"N": N, "when": fN(N), "actual_ts": at, "rebalance_id": r["rebalance_id"], "realized_gross": float(r.get("realized_gross") or 0.0),
              "venue_gross": float(r.get("venue_gross_usdt") or 0.0), "target_gross": float(r.get("target_gross") or 0.0),
              "halted": bool(r.get("opening_halted")), "producer": (eb.get("producer") or "")[:14], "gross_mult": (r.get("weights") or {}).get("gross_mult"),
              "regime": r.get("regime_at_anchor"), "day": days[0]}
rid2N = {v["rebalance_id"]: N for N, v in ANC.items()}
Ns = sorted(ANC)
# step-up / rebuild anchors: realized gross moved > 15% vs the previous traded anchor, or previous anchor was flat (rule stated in REPORT)
prev = None
for N in Ns:
    a = ANC[N]; a["stepup"] = False
    if prev is not None and prev["realized_gross"] > 0 and a["realized_gross"] > 0:
        a["stepup"] = abs(a["realized_gross"] / prev["realized_gross"] - 1) > 0.15
    elif prev is not None and prev["realized_gross"] == 0 and a["realized_gross"] > 0:
        a["stepup"] = True
    if a["realized_gross"] > 0: prev = a
    a["precombo"] = N < N_FIRST_COMBO
    a["in_calib"] = (not a["precombo"]) and (not a["halted"]) and a["venue_gross"] >= 1000
    a["steady"] = a["in_calib"] and not a["stepup"]
print("\n=== ANCHOR SET ===")
print("N | rebalance | realized_gross | venue_gross | mult | producer | halted | precombo | stepup | in_calib | steady")
for N in Ns:
    a = ANC[N]; print(f"{a['when']} | {a['rebalance_id']} | {a['realized_gross']:8.0f} | {a['venue_gross']:8.0f} | {a['gross_mult']} | {a['producer']} | {a['halted']} | {a['precombo']} | {a['stepup']} | {a['in_calib']} | {a['steady']}")
calibN = [N for N in Ns if ANC[N]["in_calib"]]; steadyN = [N for N in Ns if ANC[N]["steady"]]
REP["anchors"] = {"n_rows": len(Ns), "first": ANC[Ns[0]]["when"], "last": ANC[Ns[-1]]["when"], "n_in_calib": len(calibN), "calib_first": ANC[calibN[0]]["when"], "calib_last": ANC[calibN[-1]]["when"],
                  "n_steady": len(steadyN), "excluded": [{"when": ANC[N]["when"], "why": ("pre-combo (producer shadow_loop_v3)" if ANC[N]["precombo"] else "halted / flat book" if not ANC[N]["in_calib"] else "step-up anchor (|Δgross|>15% or rebuild from flat)")} for N in Ns if not ANC[N]["steady"]],
                  "stepup_rule": "excluded from the STEADY subset only: realized_gross moved >15% vs previous traded anchor, or rebuilt from a flat book"}
print("in_calib:", len(calibN), ANC[calibN[0]]["when"], "->", ANC[calibN[-1]]["when"], "| steady:", len(steadyN))
print("excluded from steady:", [(e["when"], e["why"]) for e in REP["anchors"]["excluded"]])

# ---------------- liquidity tiers: producer formula on the producer's own cache ----------------
z = np.load(f"{WS}/state/rolling.npz"); cts = z["ts"].astype(np.int64); row_of = {int(t): i for i, t in enumerate(cts)}
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
LQV = z["data"][:, :, 3].astype(np.float64)           # ch3 = log1p(5m quote volume) (shadow_loop_v3.py bars_to_channels: CH_NAMES[3] == 'log_qv')
def qv4h_at(N):
    ai = row_of[N]; seg = LQV[max(ai + 1 - 2016, 0):ai + 1]; fin = np.isfinite(seg)
    qvm = np.where(fin, seg, 0.0).sum(0) / np.maximum(fin.sum(0), 1)
    return np.expm1(np.clip(qvm, 0, 30)) * 48.0, fin.sum(0)
def tier_of(q):   # identical to shadow_loop_v3.py L520 and w10_universe_recheck.py tier_of
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
QV = {}; TIER = {}
for N in Ns:
    q, nfin = qv4h_at(N); QV[N] = q; TIER[N] = tier_of(q)
REP["tier_rule"] = {"source": "shadow_loop_v3.py L373/L473/L520 (producer) == w10_universe_recheck.py tier_of (replay device)",
                    "qv4h": "expm1(clip(mean over trailing 2016 5m bars of log1p(5m quote volume), 0, 30)) * 48, computed at the nominal anchor row of ~/wide_shadow/state/rolling.npz ch3",
                    "tiers": {"0": "qv4h >= 5e6 USDT", "1": "1e6 <= qv4h < 5e6", "2": "qv4h < 1e6"},
                    "note": "every traded symbol is tiered by its own qv4h, including names the producer force-exits outside its member set (which it costs at tier-2-worst 4.7 bps)"}
# tier of the first combo anchor's traded symbols, for the record
def tier_for(N, s):
    j = sidx.get(s)
    if j is None: return None, None
    return int(TIER[N][j]), float(QV[N][j])

# ---------------- fills: dedup by trade_id, keep the backfilled (superseding) row ----------------
byid = {}
for r in F:
    t = r["trade_id"]
    if t not in byid or r.get("supersedes_trade_id") is not None: byid[t] = r
FD = list(byid.values())
n_backfilled = sum(1 for r in FD if r.get("mid_at_fill_plus_60s") is not None)
print(f"\nfills rows {len(F)} -> unique trade_id {len(FD)}; backfilled (+60s mark present) {n_backfilled}")
REP["fills"] = {"rows": len(F), "unique_trade_id": len(FD), "backfilled": n_backfilled}
# BNB px per order row (bookTicker mid @collect) for fee attribution at fill level
PX = {}
for r in O:
    fc = r.get("fee_conversion")
    if fc and "BNB" in fc: PX[(r["rebalance_id"], r["symbol"], r["order_type"], int(r["attempt_idx"]))] = float(fc["BNB"]["px"])
for r in FD:
    k = (r["rebalance_id"], r["symbol"], r["order_type"], int(r["attempt_idx"]))
    r["_px_bnb"] = PX.get(k); r["_fee_usdt"] = float(r["commission"]) * PX[k] if k in PX else np.nan
    r["_N"] = rid2N.get(r["rebalance_id"]); r["_tier"], r["_qv4h"] = tier_for(r["_N"], r["symbol"]) if r["_N"] is not None else (None, None)
    px = float(r["fill_px"]); m60 = r.get("mid_at_fill_plus_60s"); sgn = 1.0 if r["side"] == "buy" else -1.0
    r["_markout_bps"] = sgn * (float(m60) - px) / px * 1e4 if m60 is not None else np.nan       # >0 = price moved our way after the fill (favourable)
    r["_notl"] = float(r["fill_notional"])
nofee = [r for r in FD if not np.isfinite(r["_fee_usdt"])]
print("fills without an order-row BNB px (fee unattributable):", len(nofee))

# ---------------- legs: one per (rebalance, symbol) from order rows ----------------
LEG = {}
for r in O:
    if r["order_type"] == "protective_flatten": continue
    k = (r["rebalance_id"], r["symbol"]); L = LEG.setdefault(k, {"rid": r["rebalance_id"], "symbol": r["symbol"], "rows": []})
    L["rows"].append(r)
for k, L in LEG.items():
    rows = L["rows"]; mk = [r for r in rows if r["order_type"] == "maker"]; tp = [r for r in rows if r["order_type"] == "topup_taker"]
    mk1 = [r for r in mk if int(r["attempt_idx"]) == 1]
    intents = sorted(set(round(abs(float(r["intended_notional"])), 6) for r in mk1))
    L["intended_full"] = max(intents) if intents else 0.0; L["intent_conflict"] = len(intents) > 1
    L["side"] = next((r["side"] for r in mk1 if r["side"]), None)
    if L["side"] is None:
        v = next((float(r["intended_notional"]) for r in mk1), 0.0); L["side"] = "buy" if v > 0 else "sell" if v < 0 else None
    L["sent"] = any(r["terminal_reason"] in ("filled", "partial_expired", "venue_reject") for r in mk1)
    L["not_sent_reason"] = None if L["sent"] else (mk1[0]["terminal_reason"] if mk1 else "no maker row")
    L["rej_first"] = any(r["terminal_reason"] == "venue_reject" and int(r["attempt_idx"]) == 1 for r in mk)
    L["rej_second"] = any(r["terminal_reason"] == "venue_reject" and int(r["attempt_idx"]) == 2 for r in mk)
    L["rej_note_5022"] = any("-5022" in (r.get("note") or "") for r in mk if r["terminal_reason"] == "venue_reject")
    L["requote_rested"] = L["rej_first"] and not L["rej_second"]
    L["maker_filled"] = sum(abs(float(r.get("filled_notional") or 0.0)) for r in mk)
    L["maker_fee"] = sum(float(r.get("fee_paid") or 0.0) for r in mk)
    L["topup_filled"] = sum(abs(float(r.get("filled_notional") or 0.0)) for r in tp)
    L["topup_fee"] = sum(float(r.get("fee_paid") or 0.0) for r in tp)
    L["topup_source"] = tp[0].get("topup_source") if tp else None
    L["topup_terminal"] = tp[0]["terminal_reason"] if tp else None
    L["N"] = rid2N.get(L["rid"]); L["tier"], L["qv4h"] = tier_for(L["N"], L["symbol"]) if L["N"] is not None else (None, None)
    L["mid_at_anchor"] = next((float(r["mid_at_anchor"]) for r in rows if r.get("mid_at_anchor")), None)
legs = [L for L in LEG.values() if L["N"] is not None]
print(f"legs (rebalance,symbol): {len(LEG)}; with anchor row: {len(legs)}; intent conflicts (two attempt-1 maker rows with different |intended|): {sum(1 for L in legs if L['intent_conflict'])}")
print("legs with -5022 first refusal:", sum(1 for L in legs if L["rej_first"]), "| requote rested:", sum(1 for L in legs if L["requote_rested"]), "| refused twice -> taker:", sum(1 for L in legs if L["rej_second"]),
      "| all reject notes are -5022:", all(L["rej_note_5022"] for L in legs if L["rej_first"]))
# unknown-fill rows (executor M3 rule: never value unknown as 0)
n_unknown = sum(1 for r in O if r["order_type"] != "protective_flatten" and r.get("filled_notional") is None)
print("order rows with filled_notional unknown (None):", n_unknown)

# ---------------- aggregation helpers ----------------
def agg_fees(fills, legs_, label, N_set):
    fl = [r for r in fills if r["_N"] in N_set]; lg = [L for L in legs_ if L["N"] in N_set and L["sent"]]
    out = {"label": label, "n_anchors": len(N_set)}
    for tier in (0, 1, 2, "all"):
        f = [r for r in fl if tier == "all" or r["_tier"] == tier]; l = [L for L in lg if tier == "all" or L["tier"] == tier]
        mk = [r for r in f if r["order_type"] == "maker"]; tk = [r for r in f if r["order_type"] == "topup_taker"]
        mk_n = sum(r["_notl"] for r in mk); tk_n = sum(r["_notl"] for r in tk); tot = mk_n + tk_n
        mk_fee = sum(r["_fee_usdt"] for r in mk if np.isfinite(r["_fee_usdt"])); tk_fee = sum(r["_fee_usdt"] for r in tk if np.isfinite(r["_fee_usdt"]))
        d = {"n_fills_maker": len(mk), "n_fills_taker": len(tk), "maker_notional": mk_n, "taker_notional": tk_n, "filled_notional": tot,
             "maker_fee_usdt": mk_fee, "taker_fee_usdt": tk_fee,
             "maker_fee_bps": mk_fee / mk_n * 1e4 if mk_n else np.nan, "taker_fee_bps": tk_fee / tk_n * 1e4 if tk_n else np.nan,
             "blended_fee_bps": (mk_fee + tk_fee) / tot * 1e4 if tot else np.nan, "maker_share": mk_n / tot if tot else np.nan}
        # markout (+60s), notional-weighted, only backfilled fills
        for typ, grp in (("maker", mk), ("taker", tk), ("all", f)):
            b = [r for r in grp if np.isfinite(r["_markout_bps"])]; w = np.array([r["_notl"] for r in b]); m = np.array([r["_markout_bps"] for r in b])
            gn = sum(r["_notl"] for r in grp)
            d[f"markout60_{typ}_bps"] = float((w * m).sum() / w.sum()) if w.sum() > 0 else np.nan
            d[f"markout60_{typ}_median_bps"] = float(np.median(m)) if len(m) else np.nan
            d[f"markout60_{typ}_n"] = int(len(b)); d[f"markout60_{typ}_coverage_notional"] = float(w.sum() / gn) if gn > 0 else np.nan
            d[f"markout60_{typ}_coverage_count"] = float(len(b) / len(grp)) if grp else np.nan
            # se of the weighted mean via weighted bootstrap-free approximation: sd of markout / sqrt(n)
            d[f"markout60_{typ}_se_bps"] = float(m.std(ddof=1) / np.sqrt(len(m))) if len(m) > 1 else np.nan
        # slippage vs anchor mid (100% coverage; supplementary, NOT one of the frozen a-f items)
        for typ, grp in (("maker", mk), ("taker", tk), ("all", f)):
            w = np.array([r["_notl"] for r in grp]); s = []
            for r in grp:
                m0 = MID.get((r["rebalance_id"], r["symbol"])); px = float(r["fill_px"]); sgn = 1.0 if r["side"] == "buy" else -1.0
                s.append(sgn * (m0 - px) / m0 * 1e4 if m0 else np.nan)
            s = np.array(s); ok = np.isfinite(s)
            d[f"vs_anchor_mid_{typ}_bps"] = float((w[ok] * s[ok]).sum() / w[ok].sum()) if ok.sum() and w[ok].sum() > 0 else np.nan   # >0 = filled better than anchor mid
        # fill ratios (legs)
        for side in ("buy", "sell", "all"):
            ls = [L for L in l if side == "all" or L["side"] == side]
            den = sum(L["intended_full"] for L in ls); mkf = sum(L["maker_filled"] for L in ls); tpf = sum(L["topup_filled"] for L in ls)
            d[f"fill_ratio_maker_{side}"] = mkf / den if den else np.nan; d[f"fill_ratio_after_topup_{side}"] = (mkf + tpf) / den if den else np.nan
            d[f"intended_sent_{side}"] = den; d[f"n_legs_sent_{side}"] = len(ls)
        # -5022
        nl = len(l); d["n_legs_sent"] = nl
        d["reject5022_first_rate_count"] = sum(1 for L in l if L["rej_first"]) / nl if nl else np.nan
        d["reject5022_first_rate_notional"] = sum(L["intended_full"] for L in l if L["rej_first"]) / sum(L["intended_full"] for L in l) if nl else np.nan
        d["reject5022_second_rate_count"] = sum(1 for L in l if L["rej_second"]) / nl if nl else np.nan
        d["requote_rested_share_of_first"] = (sum(1 for L in l if L["requote_rested"]) / sum(1 for L in l if L["rej_first"])) if any(L["rej_first"] for L in l) else np.nan
        d["taker_from_reject_notional"] = sum(L["topup_filled"] for L in l if L["topup_source"] == "from_reject")
        d["taker_from_partial_notional"] = sum(L["topup_filled"] for L in l if L["topup_source"] == "from_partial")
        # all-in cost per unit of filled notional (frozen definition: fees + (-markout)); markout applied only where measured
        ms = d["maker_share"]
        fee_blend = ms * d["maker_fee_bps"] + (1 - ms) * d["taker_fee_bps"] if np.isfinite(ms) else np.nan
        mo_blend = ms * d["markout60_maker_bps"] + (1 - ms) * d["markout60_taker_bps"] if np.isfinite(ms) else np.nan
        d["allin_fee_only_bps"] = fee_blend; d["allin_fee_minus_markout_bps"] = fee_blend - mo_blend if np.isfinite(mo_blend) else np.nan
        d["cost_vector_fee_only"] = [d["maker_fee_bps"], d["taker_fee_bps"], ms]
        d["cost_vector_fee_minus_markout"] = [d["maker_fee_bps"] - d["markout60_maker_bps"], d["taker_fee_bps"] - d["markout60_taker_bps"], ms]
        out[str(tier)] = d
    return out
MID = {}
for L in LEG.values(): MID[(L["rid"], L["symbol"])] = L["mid_at_anchor"]

SETS = {"all_calib": set(calibN), "steady": set(steadyN), "post_deposit": set(N for N in steadyN if N >= 1788465600), "pre_deposit": set(N for N in steadyN if N < 1788451200)}
REP["by_set"] = {}
for lab, S in SETS.items():
    REP["by_set"][lab] = agg_fees(FD, legs, lab, S)
    R = REP["by_set"][lab]
    print(f"\n=== FEES / SHARE / FILL / REJECT / MARKOUT — set {lab} (n_anchors={len(S)}) ===")
    print("tier | n_fills mk/tk | maker_notl | taker_notl | maker_share | maker_fee_bps | taker_fee_bps | blended_fee_bps | fill_mk buy/sell/all | fill_after_topup buy/sell/all | rej5022 first count/notl | second | rested/first | mo60 mk bps(n,cov%) | mo60 tk bps(n,cov%) | vs_anchor_mid mk/tk | allin fee | allin fee-mo")
    for tier in ("0", "1", "2", "all"):
        d = R[tier]
        print(f"{tier} | {d['n_fills_maker']}/{d['n_fills_taker']} | {d['maker_notional']:9.0f} | {d['taker_notional']:8.0f} | {d['maker_share']:.4f} | {d['maker_fee_bps']:.3f} | {d['taker_fee_bps']:.3f} | {d['blended_fee_bps']:.3f} | "
              f"{d['fill_ratio_maker_buy']:.3f}/{d['fill_ratio_maker_sell']:.3f}/{d['fill_ratio_maker_all']:.3f} | {d['fill_ratio_after_topup_buy']:.3f}/{d['fill_ratio_after_topup_sell']:.3f}/{d['fill_ratio_after_topup_all']:.3f} | "
              f"{d['reject5022_first_rate_count']:.3f}/{d['reject5022_first_rate_notional']:.3f} | {d['reject5022_second_rate_count']:.3f} | {d['requote_rested_share_of_first']:.3f} | "
              f"{d['markout60_maker_bps']:+.2f}({d['markout60_maker_n']},{100*d['markout60_maker_coverage_notional']:.1f}%) | {d['markout60_taker_bps']:+.2f}({d['markout60_taker_n']},{100*d['markout60_taker_coverage_notional']:.1f}%) | "
              f"{d['vs_anchor_mid_maker_bps']:+.2f}/{d['vs_anchor_mid_taker_bps']:+.2f} | {d['allin_fee_only_bps']:.3f} | {d['allin_fee_minus_markout_bps']:.3f}")

# ---------------- per-anchor series ----------------
PA = []
for N in Ns:
    a = ANC[N]; l = [L for L in legs if L["N"] == N]; ls = [L for L in l if L["sent"]]; f = [r for r in FD if r["_N"] == N]
    mk_n = sum(r["_notl"] for r in f if r["order_type"] == "maker"); tk_n = sum(r["_notl"] for r in f if r["order_type"] == "topup_taker"); tot = mk_n + tk_n
    fee = sum(r["_fee_usdt"] for r in f if np.isfinite(r["_fee_usdt"]))
    intended = sum(L["intended_full"] for L in ls); filled = sum(L["maker_filled"] + L["topup_filled"] for L in ls)
    vg = a["venue_gross"]
    row = {"N": N, "when": a["when"], "rebalance_id": a["rebalance_id"], "venue_gross": vg, "realized_gross": a["realized_gross"], "gross_mult": a["gross_mult"], "in_calib": a["in_calib"], "steady": a["steady"],
           "n_legs": len(l), "n_legs_sent": len(ls), "n_5022_first": sum(1 for L in ls if L["rej_first"]), "n_5022_second": sum(1 for L in ls if L["rej_second"]),
           "reject5022_first_rate_count": (sum(1 for L in ls if L["rej_first"]) / len(ls)) if ls else np.nan,
           "reject5022_first_rate_notional": (sum(L["intended_full"] for L in ls if L["rej_first"]) / intended) if intended else np.nan,
           "reject5022_second_rate_count": (sum(1 for L in ls if L["rej_second"]) / len(ls)) if ls else np.nan,
           "maker_filled": mk_n, "taker_filled": tk_n, "filled_notional": tot, "intended_sent": intended, "leg_filled": filled,
           "turnover_filled": tot / vg if vg else np.nan, "turnover_intended": intended / vg if vg else np.nan, "unfilled_frac_of_intended": (1 - filled / intended) if intended else np.nan,
           "maker_share": mk_n / tot if tot else np.nan, "fee_usdt": fee, "fee_bps_of_filled": fee / tot * 1e4 if tot else np.nan, "fee_bps_of_gross": fee / vg * 1e4 if vg else np.nan,
           "n_fills": len(f), "n_backfilled": sum(1 for r in f if np.isfinite(r["_markout_bps"]))}
    PA.append(row)
REP["per_anchor"] = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()} for r in PA]
print("\n=== PER-ANCHOR SERIES ===")
print("N | calib/steady | venue_gross | legs sent | -5022 first n (rate count / notl) | second n | maker_filled | taker_filled | turnover filled | turnover intended | unfilled% | maker_share | fee_usdt | fee bps/filled | fee bps/gross | fills(backfilled)")
for r in PA:
    g = lambda k, f="{:.3f}": ("  nan" if not np.isfinite(r[k]) else f.format(r[k]))
    print(f"{r['when']} | {'C' if r['in_calib'] else '-'}{'S' if r['steady'] else '-'} | {r['venue_gross']:8.0f} | {r['n_legs_sent']:3d} | {r['n_5022_first']:3d} ({g('reject5022_first_rate_count')}/{g('reject5022_first_rate_notional')}) | {r['n_5022_second']:3d} | {r['maker_filled']:8.0f} | {r['taker_filled']:7.0f} | {g('turnover_filled','{:.4f}')} | {g('turnover_intended','{:.4f}')} | {g('unfilled_frac_of_intended','{:.3f}')} | {g('maker_share')} | {r['fee_usdt']:6.2f} | {g('fee_bps_of_filled')} | {g('fee_bps_of_gross','{:.4f}')} | {r['n_fills']}({r['n_backfilled']})")

def st(x):
    x = np.array([v for v in x if v is not None and np.isfinite(v)], float)
    return {"n": int(len(x)), "mean": float(x.mean()) if len(x) else np.nan, "median": float(np.median(x)) if len(x) else np.nan, "sd": float(x.std(ddof=1)) if len(x) > 1 else np.nan,
            "p10": float(np.percentile(x, 10)) if len(x) else np.nan, "p90": float(np.percentile(x, 90)) if len(x) else np.nan, "min": float(x.min()) if len(x) else np.nan, "max": float(x.max()) if len(x) else np.nan}
REP["per_anchor_summary"] = {}
for lab, S in SETS.items():
    rs = [r for r in PA if r["N"] in S]
    s = {k: st([r[k] for r in rs]) for k in ("turnover_filled", "turnover_intended", "unfilled_frac_of_intended", "maker_share", "reject5022_first_rate_count", "reject5022_first_rate_notional", "reject5022_second_rate_count", "fee_bps_of_filled", "fee_bps_of_gross")}
    s["turnover_filled_notional_weighted"] = float(sum(r["filled_notional"] for r in rs) / sum(r["venue_gross"] for r in rs)) if rs else np.nan
    s["fee_usdt_total"] = float(sum(r["fee_usdt"] for r in rs)); s["filled_notional_total"] = float(sum(r["filled_notional"] for r in rs)); s["venue_gross_sum"] = float(sum(r["venue_gross"] for r in rs))
    s["fee_bps_of_gross_per_anchor_weighted"] = s["fee_usdt_total"] / s["venue_gross_sum"] * 1e4 if rs else np.nan
    REP["per_anchor_summary"][lab] = s
    print(f"\n=== PER-ANCHOR SUMMARY — {lab} (n={len(rs)}) ===")
    for k, v in s.items():
        if isinstance(v, dict): print(f"  {k:32s} n={v['n']:2d} mean={v['mean']:.4f} median={v['median']:.4f} sd={v['sd']:.4f} p10={v['p10']:.4f} p90={v['p90']:.4f} min={v['min']:.4f} max={v['max']:.4f}")
        else: print(f"  {k:32s} {v:.4f}")

# ---------------- fee cross-check vs the venue's own daily COMMISSION (daily_nav, /fapi/v1/income since 00:00Z) ----------------
import calendar
last_by_day = {}
for n in NAV: last_by_day[n["day"]] = n
XC = []
for D, n in sorted(last_by_day.items()):
    if D < DAY0: continue
    d00 = calendar.timegm(time.strptime(D, "%Y%m%d")); t1 = float(n["nav_ts"])
    # fills whose fill_ts in [00:00Z of D, nav_ts of the last row of D]
    fs = [r for r in FD if d00 <= float(r["fill_ts"]) <= t1]
    bnb = sum(float(r["commission"]) for r in fs); usdt = sum(r["_fee_usdt"] for r in fs if np.isfinite(r["_fee_usdt"]))
    venue = ((n.get("realised_by_type") or {}).get("COMMISSION"))
    XC.append({"day": D, "nav_ts": time.strftime("%H:%M:%SZ", time.gmtime(t1)), "n_fills": len(fs), "log_commission_BNB": bnb, "log_fee_usdt": usdt, "venue_COMMISSION_since_00Z": venue,
               "ratio_venue_over_log_bnb": (float(venue) / -bnb) if (venue is not None and bnb > 0) else None})
REP["fee_crosscheck_daily"] = XC
print("\n=== FEE CROSS-CHECK: pilot fills (dedup) vs venue daily COMMISSION (daily_nav last row of day; both since 00:00Z) ===")
print("day | nav_ts | n_fills | log Σcommission BNB | log Σfee USDT | venue COMMISSION (raw income units) | venue/(-log BNB)")
for x in XC: print(f"{x['day']} | {x['nav_ts']} | {x['n_fills']:4d} | {x['log_commission_BNB']:.6f} | {x['log_fee_usdt']:8.3f} | {x['venue_COMMISSION_since_00Z']} | {x['ratio_venue_over_log_bnb']}")

# ---------------- protective flatten (08-26 12:49Z, E-0826-F): out of the calibration, recorded ----------------
PF = [r for r in O if r["order_type"] == "protective_flatten"]
REP["protective_flatten_event"] = {"n_rows": len(PF), "filled_notional": sum(abs(float(r.get("filled_notional") or 0)) for r in PF), "fee_paid_sum": sum(float(r.get("fee_paid") or 0) for r in PF),
                                   "note": "taker liquidation of the whole book by the degradation ladder; no fills.jsonl rows and no fee_conversion -> its fees are only in the venue's 08-26 COMMISSION, not in this calibration"}
print("\nprotective_flatten:", REP["protective_flatten_event"])

# ---------------- twin gap (paper target vs real), reused from canon_reconcile.py (copied verbatim, run next to this file) ----------------
cp = f"{HERE}/canon_report.json"
if os.path.exists(cp):
    CR = json.load(open(cp)); S = CR["summary"]["canon"]
    rows = [r for r in CR["rows"] if r["canon"]]
    tw = np.array([r["twin_bps"] for r in rows], float); fu = np.array([r["funding_bps"] for r in rows], float); pc = np.array([r["paper_comp"] for r in rows], float); ps = np.array([r["paper_comp_s25"] if r["paper_comp_s25"] is not None else np.nan for r in rows], float)
    rng = np.random.default_rng(20260905)
    def boot(x, B=20000):
        x = x[np.isfinite(x)]; idx = rng.integers(0, len(x), (B, len(x))); m = x[idx].mean(1)
        return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), int(len(x))
    tg = {"canon_reconcile_sha256": sha(f"{HERE}/canon_reconcile.py"), "canon_report_sha256": sha(cp), "run_utc": CR["run_utc"], "n_canon": len(rows), "first": rows[0]["when"], "last": rows[-1]["when"],
          "twin_plus_funding_bps_per_anchor": {"mean": S["twin_plus_funding"]["mean"], "sd": S["twin_plus_funding"]["sd"], "se": S["twin_plus_funding"]["se"], "n": S["twin_plus_funding"]["n"],
                                               "ci95_normal": [S["twin_plus_funding"]["mean"] - 1.96 * S["twin_plus_funding"]["se"], S["twin_plus_funding"]["mean"] + 1.96 * S["twin_plus_funding"]["se"]],
                                               "ci95_bootstrap": boot(tw + fu)[1:3]},
          "paper_comp_bps": {"mean": S["paper_comp"]["mean"], "se": S["paper_comp"]["se"], "n": S["paper_comp"]["n"], "ci95_bootstrap": boot(pc)[1:3]},
          "paper_comp_s25_bps": {"mean": S["paper_comp_s25"]["mean"], "se": S["paper_comp_s25"]["se"], "n": S["paper_comp_s25"]["n"], "ci95_bootstrap": boot(ps)[1:3]},
          "twin_bps": {"mean": S["twin_bps"]["mean"], "se": S["twin_bps"]["se"], "n": S["twin_bps"]["n"], "ci95_bootstrap": boot(tw)[1:3]},
          "funding_bps": {"mean": S["funding_bps"]["mean"], "se": S["funding_bps"]["se"], "n": S["funding_bps"]["n"]},
          "paper_s25_minus_twin_bps": {"mean": S["paper_s25_minus_twin"]["mean"], "se": S["paper_s25_minus_twin"]["se"], "n": S["paper_s25_minus_twin"]["n"], "ci95_bootstrap": boot(ps - tw)[1:3],
                                        "meaning": "paper target book (shifted to the venue pricing moment) minus the real position twin: the execution discount band, price leg only"},
          "paper_minus_twin_minus_funding_bps": {"mean": float(np.nanmean(pc - tw - fu)), "ci95_bootstrap": boot(pc - tw - fu)[1:3], "n": int(np.isfinite(pc - tw - fu).sum()),
                                                  "meaning": "paper Π on the nominal 4h grid minus real (twin + funding): everything the paper book does not pay (execution, timing, carry)"},
          "corr_paper_s25_twin": S["corr_paper_s25_twin"], "daily_summary": CR.get("daily_summary"),
          "sets": {k: {"n": v["twin_plus_funding"]["n"], "twin_plus_funding_mean": v["twin_plus_funding"]["mean"], "se": v["twin_plus_funding"]["se"], "paper_comp_mean": v["paper_comp"]["mean"], "paper_s25_mean": v["paper_comp_s25"]["mean"], "twin_mean": v["twin_bps"]["mean"], "funding_mean": v["funding_bps"]["mean"]} for k, v in CR["summary"].items()}}
    REP["twin_gap"] = tg
    print("\n=== TWIN GAP (canon_reconcile.py reused verbatim; bps of realized gross per anchor; canonical clean 4h windows) ===")
    print(json.dumps({k: v for k, v in tg.items() if k not in ("daily_summary", "sets")}, indent=1))
    print("sets:", json.dumps(tg["sets"], indent=1)); print("daily_summary:", json.dumps(tg["daily_summary"], indent=1))
else:
    print("\n(no canon_report.json next to this script — twin gap not refreshed)")

# ---------------- uncertainty: anchor-level bootstrap for per-anchor rates, fill-level weighted bootstrap for markout ----------------
rng2 = np.random.default_rng(7)
def boot_mean(x, B=20000):
    x = np.array([v for v in x if v is not None and np.isfinite(v)], float)
    if len(x) < 2: return [np.nan, np.nan]
    idx = rng2.integers(0, len(x), (B, len(x))); m = x[idx].mean(1); return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]
def boot_wmean(v, w, B=20000):
    v = np.array(v, float); w = np.array(w, float); ok = np.isfinite(v) & np.isfinite(w); v, w = v[ok], w[ok]
    if len(v) < 2: return [np.nan, np.nan]
    idx = rng2.integers(0, len(v), (B, len(v))); m = (v[idx] * w[idx]).sum(1) / w[idx].sum(1); return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]
REP["uncertainty"] = {}
for lab in ("steady", "all_calib"):
    S = SETS[lab]; rs = [r for r in PA if r["N"] in S]; fl = [r for r in FD if r["_N"] in S]
    u = {"n_anchors": len(rs)}
    for k in ("turnover_filled", "maker_share", "reject5022_first_rate_count", "reject5022_second_rate_count", "unfilled_frac_of_intended", "fee_bps_of_filled"):
        u[k + "_ci95_anchor_boot"] = boot_mean([r[k] for r in rs])
    for typ in ("maker", "topup_taker"):
        for tier in (0, 1, 2, "all"):
            b = [r for r in fl if r["order_type"] == typ and (tier == "all" or r["_tier"] == tier) and np.isfinite(r["_markout_bps"])]
            u[f"markout60_{typ}_tier{tier}_ci95_fill_boot"] = boot_wmean([r["_markout_bps"] for r in b], [r["_notl"] for r in b]); u[f"markout60_{typ}_tier{tier}_n"] = len(b)
            vam = []; wv = []
            for r in fl:
                if r["order_type"] != typ or not (tier == "all" or r["_tier"] == tier): continue
                m0 = MID.get((r["rebalance_id"], r["symbol"])); px = float(r["fill_px"]); sgn = 1.0 if r["side"] == "buy" else -1.0
                if m0: vam.append(sgn * (m0 - px) / m0 * 1e4); wv.append(r["_notl"])
            u[f"vs_anchor_mid_{typ}_tier{tier}_ci95_fill_boot"] = boot_wmean(vam, wv); u[f"vs_anchor_mid_{typ}_tier{tier}_median"] = float(np.median(vam)) if vam else np.nan
    # markout selection diagnostics (why the 4% subset is not random)
    bfl = [r for r in fl if np.isfinite(r["_markout_bps"])]
    u["markout_subset_distinct_symbols"] = len(set(r["symbol"] for r in bfl)); u["population_distinct_symbols"] = len(set(r["symbol"] for r in fl))
    REP["uncertainty"][lab] = u
print("\n=== UNCERTAINTY (95% bootstrap) ===")
print(json.dumps(REP["uncertainty"], indent=1, default=str))

# ---------------- compact calibration block (PREREG §1 product shape) + units chain ----------------
ANCH_PER_YEAR = 2190.0
def compact(lab):
    R = REP["by_set"][lab]; s = REP["per_anchor_summary"][lab]; N_set = SETS[lab]; rs = [r for r in PA if r["N"] in N_set]
    tot = sum(r["filled_notional"] for r in rs)
    out = {"anchors": {"n": len(N_set), "first": ANC[min(N_set)]["when"], "last": ANC[max(N_set)]["when"]}, "tiers": {}, "all": {}}
    for tier in ("0", "1", "2", "all"):
        d = R[tier]
        blk = {"maker_bps_fee": d["maker_fee_bps"], "taker_bps_fee": d["taker_fee_bps"], "maker_share": d["maker_share"],
               "fill_ratio_maker": d["fill_ratio_maker_all"], "fill_ratio_maker_buy": d["fill_ratio_maker_buy"], "fill_ratio_maker_sell": d["fill_ratio_maker_sell"],
               "fill_ratio_after_topup": d["fill_ratio_after_topup_all"], "fill_ratio_after_topup_buy": d["fill_ratio_after_topup_buy"], "fill_ratio_after_topup_sell": d["fill_ratio_after_topup_sell"],
               "reject5022_first_rate": d["reject5022_first_rate_count"], "reject5022_to_taker_rate": d["reject5022_second_rate_count"],
               "markout60_maker_bps": d["markout60_maker_bps"], "markout60_taker_bps": d["markout60_taker_bps"], "markout60_coverage_notional": d["markout60_all_coverage_notional"], "markout60_n": d["markout60_all_n"],
               "cost_per_unit_turnover_fee_only_bps": d["allin_fee_only_bps"], "cost_per_unit_turnover_fee_minus_markout_bps": d["allin_fee_minus_markout_bps"],
               "share_of_filled_notional": d["filled_notional"] / tot if tot else np.nan, "n_fills": d["n_fills_maker"] + d["n_fills_taker"], "n_legs_sent": d["n_legs_sent"],
               "COST_B_format_fee_only": d["cost_vector_fee_only"], "COST_B_format_fee_minus_markout": d["cost_vector_fee_minus_markout"]}
        (out["tiers"] if tier != "all" else out)[tier if tier != "all" else "all"] = blk
    out["turnover_per_anchor"] = {"mean": s["turnover_filled"]["mean"], "median": s["turnover_filled"]["median"], "notional_weighted": s["turnover_filled_notional_weighted"], "p10": s["turnover_filled"]["p10"], "p90": s["turnover_filled"]["p90"]}
    out["units_chain"] = {"fee_bps_of_gross_per_anchor": s["fee_bps_of_gross_per_anchor_weighted"], "anchors_per_year": ANCH_PER_YEAR,
                          "fee_pct_of_gross_per_year": s["fee_bps_of_gross_per_anchor_weighted"] * ANCH_PER_YEAR / 1e4 * 100,
                          "fee_pct_of_NAV_per_year_at_2x": s["fee_bps_of_gross_per_anchor_weighted"] * ANCH_PER_YEAR / 1e4 * 100 * 2.0,
                          "check_turnover_x_cost": out["turnover_per_anchor"]["notional_weighted"] * out["all"]["cost_per_unit_turnover_fee_only_bps"],
                          "device_COST_B_blended_bps_per_unit_turnover_by_tier": {"0": 0.85 * -0.25 + 0.15 * 5.0, "1": 0.75 * 0.5 + 0.25 * 6.0, "2": 0.55 * 2.0 + 0.45 * 8.0},
                          "device_COST_B_applied_to_live_tier_mix_bps": sum((0.85 * -0.25 + 0.15 * 5.0, 0.75 * 0.5 + 0.25 * 6.0, 0.55 * 2.0 + 0.45 * 8.0)[t] * out["tiers"][str(t)]["share_of_filled_notional"] for t in (0, 1, 2))}
    return out
REP["calib"] = {"primary_steady": compact("steady"), "all_calib": compact("all_calib"), "pre_deposit": compact("pre_deposit"), "post_deposit": compact("post_deposit")}
print("\n=== COMPACT CALIB ===")
print(json.dumps(REP["calib"], indent=1, default=str))
# execution discount band per unit turnover (book level, from the twin gap; very wide by construction)
if "twin_gap" in REP:
    tg = REP["twin_gap"]; to = REP["calib"]["primary_steady"]["turnover_per_anchor"]["notional_weighted"]
    tg["per_unit_turnover_band_bps"] = {"paper_s25_minus_twin_over_turnover": tg["paper_s25_minus_twin_bps"]["mean"] / to, "ci95": [c / to for c in tg["paper_s25_minus_twin_bps"]["ci95_bootstrap"]],
                                        "turnover_used": to, "note": "book-level twin gap divided by steady turnover per anchor; the CI is ±50 bps per unit turnover wide at n=53 — reported as a band, not a calibration"}
    print("per-unit-turnover band:", tg["per_unit_turnover_band_bps"])

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o
json.dump(clean(REP), open(f"{HERE}/cost_calib.json", "w"), indent=1)
print("\nWROTE", f"{HERE}/cost_calib.json", sha(f"{HERE}/cost_calib.json")[:16])
print("CALIB_DONE")
