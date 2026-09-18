#!/usr/bin/env python3
"""FP3 P-C2 v3 (2026-09-18, after independent review round 11 R11-PC2): layer decomposition of one UTC day by EVENT-PATH pricing (engine: pnl_path.py).
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
out = {"device": "pc2_layer_decomposition.py", "version": "v3 event-path pricing (pnl_path.py)", "utc": time.strftime("%FT%TZ", time.gmtime()), "day": DAY,
       "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "engine_sha256": hashlib.sha256(open(PP.__file__, "rb").read()).hexdigest(),
       "panel": {"path": panel.path, "sha256": panel.sha, "t_first": panel.t_first, "t_last": panel.t_last, "n_symbols": len(panel.syms)},
       "ledger_roots": {"repo": PP.REPO, "ws": PP.WS}, "anchors": []}
tot = {}; n_ok = 0; fees = {}; cens_tot = {}; by_class = {}
for A in anchors:
    rec = PP.window_pnl(L, panel, A)
    if rec.get("status") == "OK":
        n_ok += 1; rec["diffs"] = PP.layer_diffs(rec)
        bc = by_class.setdefault(rec["window_class"], {"n_windows": 0, "L3_minus_L2": 0.0, "L3_minus_L2cut_execution": 0.0, "L2cut_minus_L2_flatten_footprint": 0.0, "L1_minus_L0": 0.0})
        bc["n_windows"] += 1; bc["L3_minus_L2"] += rec["diffs"]["L3_minus_L2_timing_and_fills"]; bc["L3_minus_L2cut_execution"] += rec["diffs"]["L3_minus_L2cut_execution"]
        bc["L2cut_minus_L2_flatten_footprint"] += rec["diffs"]["L2cut_minus_L2_flatten_footprint"]; bc["L1_minus_L0"] += rec["diffs"]["L1_minus_L0_book_layer"]
        for k, v in rec["layers"].items():
            tot[k] = tot.get(k, 0.0) + v["pnl_usdt"]; cens_tot[k] = cens_tot.get(k, 0.0) + v["censored"]["notional"]
        for k, v in rec["fees_in_window"].items():
            fees[k] = fees.get(k, 0.0) + v
        slim = dict(rec); slim.pop("per_name_layers", None); slim["per_name"] = {s: v for s, v in rec["per_name"].items() if v.get("status") != "OK"}   # keep only censored names inline
        slim["n_names_ok"] = sum(1 for v in rec["per_name"].values() if v.get("status") == "OK")
        out["anchors"].append(slim)
    else:
        out["anchors"].append(rec)
out["day"] = DAY; out["n_anchors_ok"] = n_ok; out["n_anchors_total"] = 6
out["day_totals_over_ok_anchors_usdt"] = tot; out["day_censored_notional_by_layer"] = cens_tot; out["day_fees_in_windows"] = fees
out["day_diffs_by_window_class"] = by_class
out["day_diffs_over_ok_anchors"] = {"L3_minus_L2_timing_and_fills": tot.get("L3_actual_path", 0.0) - tot.get("L2_request_intent", 0.0),
                                    "L3_minus_L2cut_execution": tot.get("L3_actual_path", 0.0) - tot.get("L2_cut_at_flatten", 0.0),
                                    "L2cut_minus_L2_flatten_footprint": tot.get("L2_cut_at_flatten", 0.0) - tot.get("L2_request_intent", 0.0),
                                    "L2_minus_L1_skips": tot.get("L2_request_intent", 0.0) - tot.get("L1_executor_target", 0.0),
                                    "L1_minus_L0_book_layer": tot.get("L1_executor_target", 0.0) - tot.get("L0_producer", 0.0),
                                    "L3_minus_L0_total": tot.get("L3_actual_path", 0.0) - tot.get("L0_producer", 0.0)} if n_ok else None
out["boundary"] = ("price P&L only at 5-minute resolution; no funding; fees separate; fills valued at boundary price (intra_row_approx); intent contracts at mid_at_anchor; "
                   "a day total covers only the anchors with status OK (n_anchors_ok/6) and only names that are not CENSORED (day_censored_notional_by_layer)")
json.dump(out, open(OUT, "w"), indent=1, default=str)
print(DAY, f"anchors OK {n_ok}/6", "| day totals over OK anchors (USDT):", {k: round(v, 1) for k, v in tot.items()}, "| diffs:", {k: round(v, 1) for k, v in (out["day_diffs_over_ok_anchors"] or {}).items()},
      "| fees", {k: round(v, 4) for k, v in fees.items()}, "| censored notional", {k: round(v, 0) for k, v in cens_tot.items()})
for r in out["anchors"]:
    if r.get("status") != "OK":
        print("  ", r["utc"], r["status"]); continue
    Ls = r["layers"]
    print("  ", r["utc"], "t_d", time.strftime("%H:%M:%SZ", time.gmtime(r["t_decision"])), r["t_decision_source"], "rows", r["n_rows"],
          r["window_class"], {k[:2] + ("c" if "cut" in k else ""): (round(v["gross_b0"] / 1000, 1), round(v["pnl_usdt"], 0), f"{v['n_priced']}/{v['n']}") for k, v in Ls.items()},
          "fills", r["n_fills_in_window"], "flat", r["flattens_in_window"] or "", "resid>1$", r["unexplained_qty_residual"]["n_over_1usdt"], "cens", r["layers"]["L3_actual_path"]["censored"])
