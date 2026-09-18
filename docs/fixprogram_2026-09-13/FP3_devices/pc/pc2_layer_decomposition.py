#!/usr/bin/env python3
"""FP3 P-C2 v4 (2026-09-18, after independent review round 12 R12-P2/P3; v3 after round 11 R11-PC2): layer decomposition of one UTC day by EVENT-PATH
pricing (engine: pnl_path.py).

ROUND 12 (each a reviewer counterexample v3 passed): (i) ONE event order — the pricing path sorted by 5-minute boundary while the residual check
walked real time, so a same-bar flatten erased a later reopen with a zero residual; (ii) the recorded FILL PRICES are applied as their own column
(`*_with_fill_prices`) instead of valuing every fill at its boundary mark; (iii) a PARTIAL flatten now cuts the intent layer by what the set actually
left standing, not to zero; (iv) the six decision windows cover 21.5 h — the six [anchor, decision] GAPS (150 min/day) are now priced for the ACTUAL
layer via `pnl_path.gap_pnl`, so a full-day actual figure exists and is labelled apart from the decision-window figure. THIS IS STILL NOT A CERTIFIED
EXECUTION-CONTRIBUTION NUMBER: unrecorded fills, endpoint marks, funding and the flatten-readback-as-event approximation remain open.
v1/v2 priced post-anchor positions with the return from the anchor start, did not cut the actual path at protective flattens, and deleted skipped names
from L2 — the reviewer's three counterexamples (late fill sign reversal; intra-period flatten; zero-increment skip) all pass v2 and fail here by design.

Per run labelled A (nominal 4h anchor), window [t_d, A+4h], t_d = earliest submit_ts of the rebalance (fallback A+24 min), boundaries ceil'd to 5 min:
 L0 producer intent    = target_live weights / gross_norm × sizing.gross, in contracts at the executor's mid_at_anchor, held from t_d to A+4h
 L1 executor target    = orders target_w × anchors.target_gross, in contracts at mid_at_anchor, held from t_d                 (names without an orders row: hold q0)
 L2 request intent     = previous readback quantity q0 + intended_notional / mid_at_anchor for PLACED requests; skipped ⇒ q0   (a skip is not a flat)
 L3 actual path        = q0, then every fill (signed, (symbol, trade_id)-deduplicated) and every flatten readback (→ 0) at the 5-minute boundary
                         containing its event time; the next post_anchor readback is a CONSISTENCY CHECK (unexplained_qty_residual), never adopted
All four layers are priced on the SAME price path (producer 5m panel ret5 anchored to the previous readback mark, else the first fill price, else
mid_at_anchor) with the cash identity Σ q(segment start) × Δpx. A name whose panel rows are missing/non-finite anywhere between the reference and the
window end is CENSORED (counted with its notional), never priced as 0. Fees = fills commission inside the window by asset (separate column); funding
is NOT included. Approximations are recorded per anchor: fills valued at their boundary price (intra_row_approx, fill_px_vs_path), intent contracts
converted at mid_at_anchor (mid_vs_path_price). A day total is only ever the sum over anchors with status OK, and says how many of six that is.
usage: pc2_layer_decomposition.py <YYYYMMDD> <out.json>     (env FP3_LIVE_REPO / FP3_WS override the ledger roots for tests)"""
import sys, os, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pnl_path as PP

DAY, OUT = sys.argv[1], sys.argv[2]
d0 = int(time.mktime(time.strptime(DAY, "%Y%m%d")) - time.timezone); anchors = [d0 + 14400 * k for k in range(6)]
panel = PP.Panel(); L = PP.LedgerDay(DAY)
out = {"device": "pc2_layer_decomposition.py", "version": "v5 one day price chain + fill partition + gap population + closure conditions (pnl_path.py)", "utc": time.strftime("%FT%TZ", time.gmtime()), "day": DAY,
       "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "engine_sha256": hashlib.sha256(open(PP.__file__, "rb").read()).hexdigest(),
       "panel": {"path": panel.path, "sha256": panel.sha, "t_first": panel.t_first, "t_last": panel.t_last, "n_symbols": len(panel.syms)},
       "ledger_roots": {"repo": PP.REPO, "ws": PP.WS}, "anchors": []}
tot = {}; n_ok = 0; fees = {}; cens_tot = {}; by_class = {}; gaps = []; full = {}
# ★ R13-P2 (1): ONE price reference per symbol per day, carried CHRONOLOGICALLY: previous-day window → gap(A0) → window(A0) → gap(A1) → …
#   v4 priced window(A) BEFORE gap(A) although the gap precedes it in time, and each window re-derived its own reference, so the two sides of a join
#   could disagree with the difference booked nowhere. `decision_time` gives the gap its boundary without pricing the window first.
px_chain = {}
prev_rec = PP.window_pnl(L, panel, d0 - 14400, px_chain=px_chain)     # only as the carry state for the day's FIRST gap (its own P&L belongs to the previous day)
fill_corr_windows = 0.0; ls_tot = {"pnl_long_usdt": 0.0, "pnl_short_usdt": 0.0}
for A in anchors:
    t_d, t_d_src = PP.decision_time(L, A)
    g = PP.gap_pnl(L, panel, A, t_d, prev_rec, px_chain=px_chain)     # the gap comes FIRST in time
    rec = PP.window_pnl(L, panel, A, px_chain=px_chain)
    gaps.append(g); prev_rec = rec
    if rec.get("status") == "OK":
        n_ok += 1; rec["diffs"] = PP.layer_diffs(rec)
        bc = by_class.setdefault(rec["window_class"], {"n_windows": 0, "L3_minus_L2": 0.0, "L3_minus_L2cut_execution": 0.0, "L2cut_minus_L2_flatten_footprint": 0.0, "L1_minus_L0": 0.0})
        bc["n_windows"] += 1; bc["L3_minus_L2"] += rec["diffs"]["L3_minus_L2_timing_and_fills"]; bc["L3_minus_L2cut_execution"] += rec["diffs"]["L3_minus_L2cut_execution"]
        bc["L2cut_minus_L2_flatten_footprint"] += rec["diffs"]["L2cut_minus_L2_flatten_footprint"]; bc["L1_minus_L0"] += rec["diffs"]["L1_minus_L0_book_layer"]
        for k, v in rec["layers"].items():
            tot[k] = tot.get(k, 0.0) + v["pnl_usdt"]; cens_tot[k] = cens_tot.get(k, 0.0) + v["censored"]["notional"]
        fill_corr_windows += rec["fill_price_correction_usdt"]
        ls_tot["pnl_long_usdt"] += rec["layers"]["L3_actual_path"]["pnl_long_usdt"]; ls_tot["pnl_short_usdt"] += rec["layers"]["L3_actual_path"]["pnl_short_usdt"]
        bc["L3_minus_L2cut_execution_with_fill_prices"] = bc.get("L3_minus_L2cut_execution_with_fill_prices", 0.0) + rec["diffs"]["L3_minus_L2cut_execution_with_fill_prices"]
        bc["fill_price_correction"] = bc.get("fill_price_correction", 0.0) + rec["diffs"]["fill_price_correction"]
        for k, v in rec["fees_in_window"].items():
            fees[k] = fees.get(k, 0.0) + v
        slim = dict(rec); slim.pop("per_name_layers", None); slim["per_name"] = {s: v for s, v in rec["per_name"].items() if v.get("status") != "OK"}   # keep only censored names inline
        slim["n_names_ok"] = sum(1 for v in rec["per_name"].values() if v.get("status") == "OK")
        out["anchors"].append(slim)
    else:
        out["anchors"].append(rec)
# ── carry gaps: the 6 x ~25 min between each anchor instant and its decision boundary (R12-P3: six windows are 21.5 h, not 24 h) ──
gap_ok = [g for g in gaps if g.get("status") == "GAP_OK"]
gap_pnl_sum = float(sum(g["pnl_usdt"] for g in gap_ok)); gap_corr = float(sum(g["fill_price_correction_usdt"] for g in gap_ok))
win_cov = sum(r.get("coverage_s", 0) for r in out["anchors"] if r.get("status") == "OK"); gap_cov = sum(g.get("coverage_s", 0) for g in gap_ok)
out["gaps"] = gaps
out["day_gap_totals"] = {"n_gaps_priced": len(gap_ok), "n_gaps": len(gaps), "pnl_usdt": gap_pnl_sum, "fill_price_correction_usdt": gap_corr,
                         "pnl_usdt_with_fill_prices": gap_pnl_sum + gap_corr,
                         "pnl_long_usdt": float(sum(g["pnl_long_usdt"] for g in gap_ok)), "pnl_short_usdt": float(sum(g["pnl_short_usdt"] for g in gap_ok)),
                         "statuses": [(g["utc"], g.get("status")) for g in gaps],
                         "note": "ACTUAL layer only — the intent layers are defined from their own decision time and are not carried across the gap"}
out["day_coverage"] = {"windows_s": int(win_cov), "gaps_s": int(gap_cov), "total_s": int(win_cov + gap_cov), "day_s": 86400,
                       "covered_frac": round((win_cov + gap_cov) / 86400.0, 6),
                       "note": "the decision windows alone cover 21.5 h of 24 h (6 x ~25 min missing); the gaps close that for the ACTUAL layer only"}
# ── R13-P2 (2): the fill partition over the day — the gap owns (A, t_d), the window owns [t_d, t_end]; every corrected fill belongs to exactly one ──
_wk = [tuple(k) for r in out["anchors"] if r.get("status") == "OK" for k in (r.get("fill_partition") or {}).get("keys", []) if k]
_gk = [tuple(k) for g in gap_ok for k in (g.get("fill_partition") or {}).get("keys", []) if k]
_dup = sorted(set(_wk) & set(_gk)); _all = _wk + _gk
out["day_fill_partition"] = {"n_corrected_in_windows": len(_wk), "n_corrected_in_gaps": len(_gk), "n_total": len(_all), "n_distinct": len(set(_all)),
                             "n_double_counted": len(_dup), "double_counted": [list(k) for k in _dup[:10]],
                             "disjoint": not _dup, "no_repeat_within_side": len(_all) == len(set(_all)),
                             "rule": "gap (A, t_d) ∪ window [t_d, t_end] is a partition of the corrected fills — R13-P2 (2): v4 used A < t <= t_d and t_d <= t <= t_end, so a fill exactly at t_d was corrected twice"}
# ── R13-P2 (5): what "the whole day" is allowed to claim. v4's `complete` only asked for 6 windows + 6 gaps and ignored censored names, missing
#    start prices, the readback residual and the price-chain joins. The claim is renamed and every sub-condition is published beside it. ──
_ok_recs = [r for r in out["anchors"] if r.get("status") == "OK"]
_cens_names = sum(r["layers"]["L3_actual_path"]["censored"]["n"] for r in _ok_recs) + sum(g.get("censored", {}).get("n", 0) for g in gap_ok)
_resid_over = sum(r["unexplained_qty_residual"]["n_over_1usdt"] for r in _ok_recs)
_join_over = sum((r.get("price_chain_joins") or {}).get("n_over_1pct", 0) for r in _ok_recs)
_conds = {"six_windows_priced": n_ok == 6, "six_gaps_priced": len(gap_ok) == 6, "no_censored_names": _cens_names == 0,
          "no_readback_residual_over_1usdt": _resid_over == 0, "no_price_chain_join_over_1pct": _join_over == 0,
          "fills_partitioned": bool(out["day_fill_partition"]["disjoint"]), "coverage_full_day": int(win_cov + gap_cov) == 86400}
out["day_actual_full_day"] = {"windows_pnl_usdt": tot.get("L3_actual_path", 0.0), "gaps_pnl_usdt": gap_pnl_sum,
                              "priced_period_pnl_usdt": tot.get("L3_actual_path", 0.0) + gap_pnl_sum,
                              "priced_period_pnl_usdt_with_fill_prices": tot.get("L3_actual_path", 0.0) + gap_pnl_sum + fill_corr_windows + gap_corr,
                              "fill_price_correction_usdt": fill_corr_windows + gap_corr,
                              "n_censored_names": int(_cens_names), "n_readback_residual_over_1usdt": int(_resid_over), "n_price_chain_joins_over_1pct": int(_join_over),
                              "closure_conditions": _conds, "closed": all(_conds.values()),
                              "label": "研究口径的价格估计, 覆盖【已定价的时段与成员】; 不是当日现金账 —— closure_conditions 逐条说明缺什么",
                              "note": "R13-P2 (5): v4 called this `complete` on 6 windows + 6 gaps alone. It is now `closed` only when every condition above holds; "
                                      "the figure itself is a research price estimate over the priced periods and members, never a certified day P&L"} if n_ok else None
out["day_long_short_windows"] = ls_tot
out["day"] = DAY; out["n_anchors_ok"] = n_ok; out["n_anchors_total"] = 6
out["day_totals_over_ok_anchors_usdt"] = tot; out["day_censored_notional_by_layer"] = cens_tot; out["day_fees_in_windows"] = fees
out["day_diffs_by_window_class"] = by_class
out["day_fill_price_correction_in_windows_usdt"] = fill_corr_windows
out["day_totals_with_fill_prices_usdt"] = {"L3_actual_path": tot.get("L3_actual_path", 0.0) + fill_corr_windows} if n_ok else None
out["day_diffs_over_ok_anchors"] = {"L3_minus_L2_timing_and_fills": tot.get("L3_actual_path", 0.0) - tot.get("L2_request_intent", 0.0),
                                    "L3_minus_L2cut_execution": tot.get("L3_actual_path", 0.0) - tot.get("L2_cut_at_flatten", 0.0),
                                    "L2cut_minus_L2_flatten_footprint": tot.get("L2_cut_at_flatten", 0.0) - tot.get("L2_request_intent", 0.0),
                                    "L2_minus_L1_skips": tot.get("L2_request_intent", 0.0) - tot.get("L1_executor_target", 0.0),
                                    "L1_minus_L0_book_layer": tot.get("L1_executor_target", 0.0) - tot.get("L0_producer", 0.0),
                                    "L3_minus_L0_total": tot.get("L3_actual_path", 0.0) - tot.get("L0_producer", 0.0),
                                    "L3_minus_L2cut_execution_with_fill_prices": tot.get("L3_actual_path", 0.0) + fill_corr_windows - tot.get("L2_cut_at_flatten", 0.0)} if n_ok else None
out["boundary"] = ("price P&L only at 5-minute resolution; no funding; fees separate; the boundary figure values fills at their boundary mark and the "
                   "*_with_fill_prices figure applies the RECORDED fill prices (both are printed, neither replaces the other); intent contracts at "
                   "mid_at_anchor; a day total covers only the anchors with status OK (n_anchors_ok/6) and only names that are not CENSORED; the intent "
                   "layers cover the DECISION WINDOWS only (21.5 h) while the actual layer additionally carries the six [anchor, decision] gaps — "
                   "day_coverage says exactly how much of the 86,400 s is priced. THIS IS NOT A CERTIFIED EXECUTION-CONTRIBUTION FIGURE: unrecorded "
                   "fills, endpoint marks, funding and treating a flatten READBACK as the event time all remain open")
json.dump(out, open(OUT, "w"), indent=1, default=str)
print(DAY, f"anchors OK {n_ok}/6", f"gaps priced {len(gap_ok)}/6", "| day totals over OK anchors (USDT):", {k: round(v, 1) for k, v in tot.items()},
      "| fill-price correction", round(fill_corr_windows + gap_corr, 1), "| gaps", round(gap_pnl_sum, 1),
      "| coverage", f"{out['day_coverage']['total_s']}/86400 s ({out['day_coverage']['covered_frac']:.1%})",
      "| diffs:", {k: round(v, 1) for k, v in (out["day_diffs_over_ok_anchors"] or {}).items()},
      "| fees", {k: round(v, 4) for k, v in fees.items()}, "| censored notional", {k: round(v, 0) for k, v in cens_tot.items()})
for r in out["anchors"]:
    if r.get("status") != "OK":
        print("  ", r["utc"], r["status"]); continue
    Ls = r["layers"]
    print("  ", r["utc"], "t_d", time.strftime("%H:%M:%SZ", time.gmtime(r["t_decision"])), r["t_decision_source"], "rows", r["n_rows"],
          r["window_class"], {k[:2] + ("c" if "cut" in k else ""): (round(v["gross_b0"] / 1000, 1), round(v["pnl_usdt"], 0), f"{v['n_priced']}/{v['n']}") for k, v in Ls.items()},
          "fills", r["n_fills_in_window"], "flat", r["flattens_in_window"] or "", "resid>1$", r["unexplained_qty_residual"]["n_over_1usdt"], "cens", r["layers"]["L3_actual_path"]["censored"])
