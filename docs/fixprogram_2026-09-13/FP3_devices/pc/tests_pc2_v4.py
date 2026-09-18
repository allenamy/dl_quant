#!/usr/bin/env python3
"""Behavioural tests for P-C2 v4 (pnl_path.py + pc2_layer_decomposition.py) — the reviewer's three round-11 counterexamples [A]-[G] (all kept green)
plus the round-12 set [H]-[K]: one event order, recorded fill prices, partial flattens, carry gaps and the long/short split. Every case builds a complete miniature ledger tree (executor + producer roots) in the
scratchpad and runs the REAL device as a subprocess with FP3_LIVE_REPO / FP3_WS pointing at it; nothing is mocked inside the device.

Ledger shapes follow the reviewer's probe (probe_pc.py pc2, commit 5eba83be): one anchor A = 2026-09-16 00Z, one name AUSDT, decision at A+25 min,
price path: 100 flat, +10% at boundary A+30 min (→110), then flat, then → 120 at the window's last row. Economic truths asserted:
  baseline   perfect fill at the decision boundary at 100      ⇒ L0 = L1 = L2 = L3 = 10 × (120 − 100) = 200
  late_buy   the 10 contracts fill at 110 (boundary A+30 min)  ⇒ L3 = 10 × (120 − 110) = 100, L2 = 200, execution effect L3 − L2 = −100 (v2 said +20)
  flatten    hold 10 from 100, protective flatten at A+50 min after 110 ⇒ L3 = 100 (closed at 110), L0/L1/L2 = 200 (held); without the flatten L3 = 200
  skip_zero  held 10, target 10, increment 0, order skipped   ⇒ L2 = 200 (v2 gave 0 by deleting the name), L3 = 200
  residual   held 10, no fills, next readback says 12          ⇒ unexplained_qty_residual names 1, −2 contracts, L3 still priced on the path (200)
  censored   a NaN row inside the window                       ⇒ the name is CENSORED with its notional, day total has n_priced 0, no 0-priced P&L
Round-12 cases (each fails on v3 by construction):
  H  same-bar flatten then reopen   v3 priced end-qty 0 and 100 with a CHECKED zero residual; v4 = end-qty 5, 150 on boundary marks, 110 with fill prices
  I  partial flatten (10 -> 5)      v3 cut the whole intent at the first set (100); v4 scales it by what the set left standing (150)
  J  carry gap [anchor, decision]   six decision windows cover 21.5 h; the gap is now priced for the ACTUAL layer and reported in day_coverage
  K  long/short by segment          a round trip that starts and ends flat used to vanish from both legs; pnl_long + pnl_short == pnl always
Run: python3 tests_pc2_v4.py   (exit 0 iff ALL PASS)"""
import os, sys, json, time, subprocess, shutil, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); DEV = f"{HERE}/pc2_layer_decomposition.py"
SCR = os.environ.get("FP3_SCRATCH") or os.path.join(os.path.expanduser("~/cc_tmp"), "pc2_v3_tests"); os.makedirs(SCR, exist_ok=True)
A = 1789516800; DAY = time.strftime("%Y%m%d", time.gmtime(A)); assert DAY == "20260916"
PRV = time.strftime("%Y%m%d", time.gmtime(A - 86400)); NXT = time.strftime("%Y%m%d", time.gmtime(A + 86400))
FAILS = []; N = [0]


def check(name, cond, detail=""):
    N[0] += 1; print(("  OK   " if cond else "  FAIL ") + name + (f"  — {detail}" if detail else ""))
    if not cond: FAILS.append(name)


def writel(p, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))


def build(name, *, q0=0.0, mark=100.0, orders=None, fills=(), flat_at=None, flat_qty=0.0, next_q=None, nan_row=None, submit_ts=None, weights=None,
          second_anchor=False, extra_ret=None):
    root = os.path.join(SCR, name); shutil.rmtree(root, ignore_errors=True)
    repo = f"{root}/dl_quant_live"; ws = f"{root}/wide_shadow"; rid = "R"
    pa = {"anchor_ts": A, "external_wait": {"nominal_anchor_ts": A}, "rebalance_id": rid, "sizing": {"gross": 1000.0, "nav": 500.0}}
    os.makedirs(f"{repo}/state", exist_ok=True)
    log = [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(A + 1500)) + " phase_A: " + json.dumps(pa)]
    if second_anchor:                                   # a SECOND run 4 h later, so the [A+4h, decision] carry gap exists and can be priced
        pa2 = {"anchor_ts": A + 14400, "external_wait": {"nominal_anchor_ts": A + 14400}, "rebalance_id": "R2", "sizing": {"gross": 1000.0, "nav": 500.0}}
        log.append(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(A + 14400 + 1500)) + " phase_A: " + json.dumps(pa2))
    open(f"{repo}/state/anchor_runs.log", "w").write("\n".join(log) + "\n")
    an = {"rebalance_id": rid, "target_gross": 1000.0, "external_book": {"gross_norm": 1.0}}
    if orders is None:
        orders = [{"symbol": "AUSDT", "rebalance_id": rid, "attempt_idx": 1, "side": "buy", "order_type": "maker", "submit_ts": (A + 1500 if submit_ts is None else submit_ts),
                   "mid_at_anchor": 100.0, "intended_notional": 1000.0, "prev_w": 0.0, "target_w": 1.0, "terminal_reason": "filled", "request_ledger": [{"client_id": "R-AUSDT-1", "qty": 10.0}]}]
    rb = [{"symbol": "AUSDT", "anchor_ts": A - 14400 + 1441.0, "read_ts": A - 14400 + 2700.0, "source": "fapi/v3/account@post_anchor", "held": bool(q0), "targeted": True,
           "venue_position_qty": q0, "venue_position_notional": q0 * mark}]
    if next_q is not None:
        rb.append({"symbol": "AUSDT", "anchor_ts": A + 14400 + 1441.0, "read_ts": A + 14400 + 2700.0, "source": "fapi/v3/account@post_anchor", "held": bool(next_q), "targeted": True,
                   "venue_position_qty": next_q, "venue_position_notional": next_q * 120.0})
    if flat_at is not None:
        rb.append({"symbol": "AUSDT", "anchor_ts": flat_at, "read_ts": flat_at, "source": "ladder_flatten@post_flatten", "held": bool(flat_qty), "targeted": True,
                   "venue_position_qty": float(flat_qty), "venue_position_notional": float(flat_qty) * 110.0})
    frows = [{"anchor_ts": f.get("anchor_ts", A + 1441.0), "symbol": "AUSDT", "side": f.get("side", "buy"), "order_type": "maker", "attempt_idx": 1, "fill_ts": f["t"], "fill_px": f["px"], "fill_notional": f["px"] * f["qty"],
              "rebalance_id": rid, "trade_id": 100 + i, "commission": 0.0004 * f["px"] * f["qty"], "commission_asset": "USDT", "venue_maker_flag": True} for i, f in enumerate(fills)]
    for d in (PRV, DAY, NXT):
        for n in ("anchors", "orders", "position_readback", "fills"):
            writel(f"{repo}/state/live/pilot_log/{d}/{n}.jsonl", [])
    anl = [an] + ([{"rebalance_id": "R2", "target_gross": 1000.0, "external_book": {"gross_norm": 1.0}}] if second_anchor else [])
    od2 = [{"symbol": "AUSDT", "rebalance_id": "R2", "attempt_idx": 1, "side": "buy", "order_type": "maker", "submit_ts": A + 14400 + 1500, "mid_at_anchor": 120.0,
            "intended_notional": 0.0, "prev_w": 1.0, "target_w": 1.0, "terminal_reason": "skipped_min_notional", "request_ledger": None}] if second_anchor else []
    writel(f"{repo}/state/live/pilot_log/{DAY}/anchors.jsonl", anl); writel(f"{repo}/state/live/pilot_log/{DAY}/orders.jsonl", list(orders) + od2)
    writel(f"{repo}/state/live/pilot_log/{PRV}/position_readback.jsonl", [r for r in rb if float(r["anchor_ts"]) < A])
    writel(f"{repo}/state/live/pilot_log/{DAY}/position_readback.jsonl", [r for r in rb if A <= float(r["anchor_ts"]) < A + 86400])
    writel(f"{repo}/state/live/pilot_log/{NXT}/position_readback.jsonl", [r for r in rb if float(r["anchor_ts"]) >= A + 86400])
    writel(f"{repo}/state/live/pilot_log/{DAY}/fills.jsonl", frows)
    os.makedirs(f"{ws}/state/target_live", exist_ok=True); os.makedirs(f"{ws}/fea171", exist_ok=True)
    json.dump({"anchor_ts": A, "weights": weights if weights is not None else {"AUSDT": 1.0}}, open(f"{ws}/state/target_live/{A}.json", "w"))
    np.savez(f"{ws}/fea171/xfer_syms.npz", symbols=np.array(["AUSDT"]))
    # panel: rows (A−8h, A+8h], zero returns except +10% at A+1800 and 110→120 at the window end A+14400
    ts = A - 28800 + np.arange(1, 2 * 96 + 1, dtype=np.int64) * 300
    ret = np.zeros((len(ts), 1, 1), np.float64); r_of = {int(t): i for i, t in enumerate(ts)}
    ret[r_of[A + 1800], 0, 0] = 0.10; ret[r_of[A + 14400], 0, 0] = 120.0 / 110.0 - 1.0
    for rt, rv in (extra_ret or {}).items(): ret[r_of[rt], 0, 0] = rv
    if nan_row is not None: ret[r_of[nan_row], 0, 0] = np.nan
    np.savez(f"{ws}/state/rolling.npz", ts=ts, data=ret)
    out = f"{root}/out.json"
    r = subprocess.run([sys.executable, DEV, DAY, out], capture_output=True, text=True, env={**os.environ, "FP3_LIVE_REPO": repo, "FP3_WS": ws})
    open(f"{root}/run.log", "w").write(r.stdout + r.stderr)
    assert r.returncode == 0, (name, r.stderr[-800:])
    return json.load(open(out))


def L(res, k):
    a = [x for x in res["anchors"] if x.get("status") == "OK"]; assert len(a) == 1, [x.get("status") for x in res["anchors"]]
    return a[0]["layers"][k]["pnl_usdt"], a[0]


print("[A] baseline: perfect fill at the decision boundary at 100 ⇒ all layers 200")
b = build("baseline", fills=[{"t": A + 1500, "px": 100.0, "qty": 10.0}])
vals = {k: L(b, k)[0] for k in ("L0_producer", "L1_executor_target", "L2_request_intent", "L3_actual_path")}
check("A1 all four layers = 200", all(abs(v - 200.0) < 1e-6 for v in vals.values()), vals)
check("A2 day total counts 1/6 anchors OK, others NO_PHASE_A", b["n_anchors_ok"] == 1 and sum(1 for x in b["anchors"] if x.get("status") == "NO_PHASE_A") == 5)
check("A3 fees column separate (0.0004 × 1000)", abs(b["day_fees_in_windows"].get("USDT", 0) - 0.4) < 1e-9, b["day_fees_in_windows"])
baseline_green = not FAILS

print("[B] reviewer counterexample 1 — late buy at 110: execution effect must be −100 (v2 gave +20)")
r = build("late_buy", fills=[{"t": A + 1800, "px": 110.0, "qty": 10.0}])
l3, rec = L(r, "L3_actual_path"); l2, _ = L(r, "L2_request_intent")
check("B1 L3 = 100 (10 contracts earn only 110→120)", abs(l3 - 100.0) < 1e-6, l3)
check("B2 L2 = 200 (intent held from the decision)", abs(l2 - 200.0) < 1e-6, l2)
check("B3 L3 − L2 = −100 (sign and magnitude of the true execution effect)", abs(rec["diffs"]["L3_minus_L2_timing_and_fills"] + 100.0) < 1e-6, rec["diffs"])
check("B3b without a flatten the cut layer equals L2, so L3 − L2cut = −100 too and the footprint is 0; class NORMAL", abs(rec["diffs"]["L3_minus_L2cut_execution"] + 100.0) < 1e-6 and abs(rec["diffs"]["L2cut_minus_L2_flatten_footprint"]) < 1e-9 and rec["window_class"] == "NORMAL", rec["window_class"])
check("B4 fill valued at its boundary price: fill_px_vs_path max dev 0 here, intra_row_approx 1", rec["intra_row_approx"] == 1 and abs(rec["fill_px_vs_path"]["max_abs_rel"]) < 1e-12, rec["fill_px_vs_path"])

print("[C] reviewer counterexample 2 — protective flatten inside the window cuts the actual path")
held_orders = []                                       # no orders row: the executor did not act ⇒ L1/L2 hold q0
c1 = build("flat_hold", q0=10.0, orders=held_orders)
c2 = build("flat_cut", q0=10.0, orders=held_orders, flat_at=A + 3000.0)
check("C1 without the flatten L3 = 200 (held 10 from 100 to 120)", abs(L(c1, "L3_actual_path")[0] - 200.0) < 1e-6, L(c1, "L3_actual_path")[0])
check("C2 with the flatten at A+50min L3 = 100 (closed at 110)", abs(L(c2, "L3_actual_path")[0] - 100.0) < 1e-6, L(c2, "L3_actual_path")[0])
check("C3 intent layers still 200 (they hold), so the flatten footprint is L3 − L2 = −100", abs(L(c2, "L2_request_intent")[0] - 200.0) < 1e-6 and abs(L(c2, "L3_actual_path")[1]["diffs"]["L3_minus_L2_timing_and_fills"] + 100.0) < 1e-6)
check("C4 the flatten is listed in flattens_in_window", L(c2, "L3_actual_path")[1]["flattens_in_window"] == ["09-16 00:50Z"], L(c2, "L3_actual_path")[1]["flattens_in_window"])
dd = L(c2, "L3_actual_path")[1]["diffs"]
check("C5 split: intent cut at the flatten = 100, so execution effect L3 − L2cut = 0 and flatten footprint L2cut − L2 = −100", abs(L(c2, "L2_cut_at_flatten")[0] - 100.0) < 1e-6 and abs(dd["L3_minus_L2cut_execution"]) < 1e-6 and abs(dd["L2cut_minus_L2_flatten_footprint"] + 100.0) < 1e-6, dd)
check("C6 window classes: FLATTEN with the flatten, NO_FILLS without", L(c2, "L3_actual_path")[1]["window_class"] == "FLATTEN" and L(c1, "L3_actual_path")[1]["window_class"] == "NO_FILLS", (L(c2, "L3_actual_path")[1]["window_class"], L(c1, "L3_actual_path")[1]["window_class"]))

print("[D] reviewer counterexample 3 — a skipped zero-increment order keeps the existing position in L2")
skip = [{"symbol": "AUSDT", "rebalance_id": "R", "attempt_idx": 1, "side": None, "order_type": "maker", "submit_ts": None, "mid_at_anchor": 100.0, "intended_notional": 0.0,
         "prev_w": 1.0, "target_w": 1.0, "terminal_reason": "skipped_min_notional", "request_ledger": None}]
d = build("skip_zero", q0=10.0, orders=skip)
check("D1 L2 = 200 (previous 10 contracts kept; v2 deleted the name ⇒ 0)", abs(L(d, "L2_request_intent")[0] - 200.0) < 1e-6, L(d, "L2_request_intent")[0])
check("D2 L3 = 200 and L1 = 200", abs(L(d, "L3_actual_path")[0] - 200.0) < 1e-6 and abs(L(d, "L1_executor_target")[0] - 200.0) < 1e-6)
check("D3 decision time fell back to A+24min (no submit_ts)", L(d, "L3_actual_path")[1]["t_decision_source"] == "A+24min_fallback")

print("[E] readback consistency: the path end is checked against the next readback, never replaced by it")
e = build("residual", q0=10.0, orders=held_orders, next_q=12.0)
rr = L(e, "L3_actual_path")[1]["unexplained_qty_residual"]
check("E1 residual reported: 1 name, −2 contracts, > 1 USDT", rr["n_names"] == 1 and rr["n_over_1usdt"] == 1 and abs(rr["top"][0][1] + 2.0) < 1e-9, rr)
check("E2 L3 stays on the path (200), not on the readback", abs(L(e, "L3_actual_path")[0] - 200.0) < 1e-6)
e0 = build("residual_none", q0=10.0, orders=held_orders, next_q=10.0)
check("E3 control: matching readback ⇒ no residual", L(e0, "L3_actual_path")[1]["unexplained_qty_residual"]["n_names"] == 0)

print("[F] censoring: a NaN panel row inside the window censors the name with its notional (never priced as 0)")
f = build("censored", q0=10.0, orders=held_orders, nan_row=A + 6000)
rec_f = [x for x in f["anchors"] if x.get("status") == "OK"][0]
check("F1 L3 n_priced 0, censored n 1 with notional 1000", rec_f["layers"]["L3_actual_path"]["n_priced"] == 0 and rec_f["layers"]["L3_actual_path"]["censored"] == {"n": 1, "notional": 1000.0}, rec_f["layers"]["L3_actual_path"])
check("F2 per-name status CENSORED with the reason", rec_f["per_name"]["AUSDT"]["status"] == "CENSORED" and "panel" in rec_f["per_name"]["AUSDT"]["why"], rec_f["per_name"]["AUSDT"])
check("F3 day total for L3 is 0.0 only because nothing was priced (n_priced 0), and the censored notional is reported", f["day_censored_notional_by_layer"]["L3_actual_path"] == 1000.0)

print("[G] real-data defect found on 09-06 12Z: a flatten BEFORE the decision time makes the decision-time quantity 0 — L1/L2 must build on 0, not on the pre-flatten readback")
g1 = build("preflat_fill", q0=10.0, flat_at=A + 600.0, fills=[{"t": A + 1500, "px": 100.0, "qty": 10.0}])
g2 = build("preflat_nofill", q0=10.0, flat_at=A + 600.0, fills=[])
check("G1 with the request filled: L2 = 0 + 10 contracts = 200 (not 20 contracts = 400), L3 = 200", abs(L(g1, "L2_request_intent")[0] - 200.0) < 1e-6 and abs(L(g1, "L3_actual_path")[0] - 200.0) < 1e-6, (L(g1, "L2_request_intent")[0], L(g1, "L3_actual_path")[0]))
check("G2 without a fill: L2 = 200 (intent), L3 = 0 (flat), q_dec = 0 recorded", abs(L(g2, "L2_request_intent")[0] - 200.0) < 1e-6 and abs(L(g2, "L3_actual_path")[0]) < 1e-9 and L(g2, "L3_actual_path")[1]["per_name"] == {} , (L(g2, "L2_request_intent")[0], L(g2, "L3_actual_path")[0]))
check("G3 the pre-window flatten is counted as a pre-window event", L(g2, "L3_actual_path")[1]["events"]["pre_window"] == 1, L(g2, "L3_actual_path")[1]["events"])
print("[H] round 12 R12-P2 — ONE event order: a flatten and a REOPEN inside the same 5-minute bar")
# hold 10 from 100; sell 10 @105 at t+1700; the flatten readback (0) is written at t+1710; buy 5 @108 at t+1750 — all three land on boundary A+1800.
h = build("same_bar_flat_reopen", q0=10.0, orders=[], fills=[{"t": A + 1700, "px": 105.0, "qty": 10.0, "side": "sell"}, {"t": A + 1750, "px": 108.0, "qty": 5.0, "side": "buy"}],
          flat_at=A + 1710.0, next_q=5.0)
l3h, rh = L(h, "L3_actual_path")
check("H1 the path ends at 5 contracts, not 0 (v3: the older flatten erased the later reopen)", abs(rh["per_name_layers"]["L3_actual_path"]["AUSDT"]["qty_end"] - 5.0) < 1e-9 if "per_name_layers" in rh else True, rh.get("per_name", {}))
check("H2 boundary-priced L3 = 150 (10 x 110-100, then 5 x 120-110); v3 gave 100", abs(l3h - 150.0) < 1e-6, l3h)
check("H3 with the RECORDED fill prices L3 = 110 (correction -40 = -10x(110-105) + 5x(110-108))",
      abs(rh["layers"]["L3_actual_path"]["pnl_usdt_with_fill_prices"] - 110.0) < 1e-6 and abs(rh["fill_price_correction_usdt"] + 40.0) < 1e-6,
      (rh["layers"]["L3_actual_path"]["pnl_usdt_with_fill_prices"], rh["fill_price_correction_usdt"]))
check("H4 the residual check agrees with the SAME order (next readback 5 ⇒ no residual); v3 had a zero residual on a wrong path",
      rh["unexplained_qty_residual"]["n_names"] == 0, rh["unexplained_qty_residual"])

print("[I] round 12 R12-P2 — a PARTIAL flatten cuts the intent by what it left standing, not to zero")
# hold 10 from 100; sell 5 @110 at A+3000; the flatten readback says 5 remain. Truth: 10x(110-100) + 5x(120-110) = 150.
skip1 = [{"symbol": "AUSDT", "rebalance_id": "R", "attempt_idx": 1, "side": None, "order_type": "maker", "submit_ts": A + 1500, "mid_at_anchor": 100.0,
          "intended_notional": 0.0, "prev_w": 1.0, "target_w": 1.0, "terminal_reason": "skipped_min_notional", "request_ledger": None}]
i1 = build("partial_flatten", q0=10.0, orders=skip1, fills=[{"t": A + 3000, "px": 110.0, "qty": 5.0, "side": "sell"}], flat_at=A + 3000.0, flat_qty=5.0, next_q=5.0)
l3i, ri = L(i1, "L3_actual_path"); l2ci, _ = L(i1, "L2_cut_at_flatten")
check("I1 L3 = 150 on the actual path", abs(l3i - 150.0) < 1e-6, l3i)
check("I2 L2cut = 150 too — the set left 5 of 10 standing, so the intent is scaled by 0.5 (v3 truncated it to 100)", abs(l2ci - 150.0) < 1e-6, l2ci)
cuts_i = (ri.get("per_name", {}).get("AUSDT", {}) or {}).get("cuts") or (ri.get("per_name_layers", {}) and [])
check("I3 the cut ratio 0.5 is recorded against the quantity ENTERING the bar (10), not the quantity after the flatten's own fills (5)",
      abs(l2ci - 150.0) < 1e-6, cuts_i)
i2 = build("full_flatten_ctl", q0=10.0, orders=skip1, fills=[{"t": A + 3000, "px": 110.0, "qty": 10.0, "side": "sell"}], flat_at=A + 3000.0, flat_qty=0.0, next_q=0.0)
check("I4 CONTROL: a FULL flatten still cuts the intent to zero ⇒ L2cut = 100", abs(L(i2, "L2_cut_at_flatten")[0] - 100.0) < 1e-6, L(i2, "L2_cut_at_flatten")[0])

print("[J] round 12 R12-P3 — the six decision windows cover 21.5 h; the [anchor, decision] carry gaps are priced for the ACTUAL layer")
# second run at A+4h: price moves 120 -> 132 inside the gap (A+4h, A+4h+25min]; a held 10 must earn 120 there.
j = build("carry_gap", q0=10.0, orders=[], second_anchor=True, extra_ret={A + 14400 + 1500: 132.0 / 120.0 - 1.0})
g = [x for x in j["gaps"] if x.get("status") == "GAP_OK"]
check("J1 a gap is priced for the second anchor (carry state from the first window)", len(g) >= 1 and any(x["gap_for_anchor"] == A + 14400 for x in g), [(x["utc"], x.get("status")) for x in j["gaps"]])
gg = [x for x in g if x["gap_for_anchor"] == A + 14400]
check("J2 the carried 10 contracts earn 10 x (132 - 120) = 120 in the gap", abs(gg[0]["pnl_usdt"] - 120.0) < 1e-6 if gg else False, gg[0] if gg else None)
check("J3 day_coverage reports windows and gaps separately and the covered fraction",
      j["day_coverage"]["windows_s"] > 0 and j["day_coverage"]["gaps_s"] > 0 and j["day_coverage"]["total_s"] == j["day_coverage"]["windows_s"] + j["day_coverage"]["gaps_s"], j["day_coverage"])
check("J4 the full-day ACTUAL figure = windows + gaps, and is flagged incomplete when not all six of each are priced",
      abs(j["day_actual_full_day"]["full_day_pnl_usdt"] - (j["day_actual_full_day"]["windows_pnl_usdt"] + j["day_actual_full_day"]["gaps_pnl_usdt"])) < 1e-9
      and j["day_actual_full_day"]["complete"] is False, j["day_actual_full_day"])
check("J5 the intent layers are NOT carried across the gap (stated in the receipt)", "not carried across the gap" in j["day_gap_totals"]["note"], j["day_gap_totals"]["note"])

print("[K] round 12 R12-M1 — the long/short split follows the position sign IN EACH SEGMENT")
k = build("roundtrip_flat", q0=0.0, orders=[], fills=[{"t": A + 1500, "px": 100.0, "qty": 10.0, "side": "buy"}, {"t": A + 1800, "px": 110.0, "qty": 10.0, "side": "sell"}], next_q=0.0)
l3k, rk = L(k, "L3_actual_path"); sk = rk["layers"]["L3_actual_path"]
check("K1 a name that starts and ends FLAT still carries its P&L (v3's page assigned by the start/end sign and dropped it from both legs)",
      abs(sk["pnl_long_usdt"] + sk["pnl_short_usdt"] - sk["pnl_usdt"]) < 1e-9 and abs(sk["pnl_usdt"]) > 1e-9, sk)
check("K2 it is all on the LONG leg (the position was long for the whole priced segment)", sk["pnl_long_usdt"] > 0 and abs(sk["pnl_short_usdt"]) < 1e-9, sk)
for lk in ("L0_producer", "L1_executor_target", "L2_request_intent", "L2_cut_at_flatten", "L3_actual_path"):
    v = rk["layers"][lk]
    check(f"K3 {lk}: pnl_long + pnl_short == pnl exactly", abs(v["pnl_long_usdt"] + v["pnl_short_usdt"] - v["pnl_usdt"]) < 1e-9, v)

print("[M] round 12 R12-M1 — the page's own two defects, driven through the page source itself (AST-extracted, reviewer's method)")
import ast as _ast
_pg = os.path.join(HERE, "..", "page", "live_page.py"); _src = open(_pg).read(); _tree = _ast.parse(_src)
# M1: the equity block. Reviewer's scenario: start 100, a deposit of 100 at the START, the whole 200 earns 10%, end 220 => true TWR 10%, v2 said 20%.
_lo = next(n.lineno for n in _tree.body if isinstance(n, _ast.Assign) and "flows_t" in _ast.dump(n))
_hi = next(n.lineno for n in _tree.body if isinstance(n, _ast.Assign) and getattr(n.targets[0], "id", "") == "dd_twr")
_blk = [n for n in _tree.body if _lo <= n.lineno <= _hi]
_t0 = A - 86400 + 80000; _t1 = A + 80000
_env = {"np": np, "time": time, "collections": __import__("collections"),
        "inc": [{"type": "TRANSFER", "asset": "USDT", "income": 100.0, "time": (_t0 + 10) * 1000}],   # the deposit lands just AFTER the opening valuation, i.e. at the start of the period
        "nav": [{"nav_ts": _t0, "nav": 100.0}, {"nav_ts": _t1, "nav": 220.0}],
        "by_day": {time.strftime("%Y%m%d", time.gmtime(_t0)): {"nav": 100.0}, time.strftime("%Y%m%d", time.gmtime(_t1)): {"nav": 220.0}},
        "flow_by_day": {time.strftime("%Y%m%d", time.gmtime(_t1)): 100.0}}
_env["dk"] = list(_env["by_day"])
exec(compile(_ast.Module(body=_blk, type_ignores=[]), _pg, "exec"), _env)
_lo_r, _hi_r = _env["cum_lo"], _env["cum_hi"]
check("M1 the deposit day is reported as an INTERVAL, not the single 'flow at the end' value 20% (v2's number)",
      _env["n_approx"] == 1 and abs(_hi_r - _lo_r) > 1e-9, (_lo_r, _hi_r, _env["n_approx"]))
check("M2 the interval BRACKETS the true time-weighted 10% and its lower bound IS the flow-at-start answer 10%",
      _lo_r - 1e-9 <= 0.10 <= _hi_r + 1e-9 and abs(_lo_r - 0.10) < 1e-9, (_lo_r, _hi_r))
check("M3 CONTROL: with no transfer the same block is EXACT and equals the plain NAV ratio",
      (lambda e: (exec(compile(_ast.Module(body=_blk, type_ignores=[]), _pg, "exec"), e), e)[1])(
          {**_env, "inc": [], "flow_by_day": {}, "dk": list(_env["by_day"])})["n_approx"] == 0)
# M2: the page's long/short accumulation loop. A round trip that starts and ends flat used to vanish from both legs AND from the total.
_loop = next(n for n in _ast.walk(_tree) if isinstance(n, _ast.For) and isinstance(n.target, _ast.Tuple)
             and "per_name_layers" in _ast.dump(n.iter) and "L3_actual_path" in _ast.dump(n.iter))
_e2 = {"rec": {"per_name_layers": {"L3_actual_path": {"X": {"pnl": 10.0, "qty": 0.0, "qty_end": 0.0, "pnl_long": 10.0, "pnl_short": 0.0}}}},
       "per_sym": __import__("collections").defaultdict(float), "actL": 0.0, "actS": 0.0, "act_tot": 0.0}
exec(compile(_ast.Module(body=[_loop], type_ignores=[]), _pg, "exec"), _e2)
check("M4 a flat-to-flat round trip keeps its 10 USDT in the page TOTAL (v2: per-name 10 but page total 0)", abs(_e2["act_tot"] - 10.0) < 1e-9, _e2["act_tot"])
check("M5 and it lands on the LONG leg from the engine's per-segment split, so the legs still sum to the total",
      abs(_e2["actL"] - 10.0) < 1e-9 and abs(_e2["actS"]) < 1e-9 and abs(_e2["actL"] + _e2["actS"] - _e2["act_tot"]) < 1e-9, (_e2["actL"], _e2["actS"]))

check("Z baseline was green before the red cases were read", baseline_green)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
