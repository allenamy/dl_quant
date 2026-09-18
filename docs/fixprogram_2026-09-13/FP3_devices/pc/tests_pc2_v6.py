#!/usr/bin/env python3
"""Behavioural tests for P-C2 v6 (pnl_path.py + pc2_layer_decomposition.py + page/live_page.py) — the reviewer's round-11 counterexamples [A]-[G] and
round-12 set [H]-[M] (all kept green) plus the round-13 set [N]-[O]. Every case builds a complete miniature ledger tree (executor + producer roots) in
the scratchpad and runs the REAL device as a subprocess with FP3_LIVE_REPO / FP3_WS pointing at it; nothing is mocked inside the device.

ROUND 13 (independent review 7ba79b75 §5 / §6), each red on v4:
  N1 two partial flattens in ONE bar        v4 multiplied both ratios (0.8 x 0.5) and cut the reference to 4; the actual path leaves 5
  N2 a fill exactly AT the decision time    v4's gap took (A, t_d] and the window [t_d, t_end], so its 100 USDT price correction was booked twice
  N3 window/gap price reference reset       v4 re-derived a reference per window while the gap chained off the previous end: the join difference was
                                            booked nowhere (reviewer: previous end 120, next start 132, holding 10 = 120 USDT unexplained)
  N4 a name whose first event is in a gap   v4 walked only the previous window's priced layer, so the name was counted in n_fills and then vanished
  N5 `day_actual_full_day.complete`         v4 asked only for 6 windows + 6 gaps, ignoring censored names, residuals and price-chain joins
  O1 the page's two sub-period numbers      they are SCENARIOS, not bounds: the true TWR can fall outside them (reviewer: 46.67% vs 10% / 20%)
  O2 net-zero flow                          v4 called +100 then -100 in one segment "exact" while the capital timing really changed

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
Run: python3 tests_pc2_v6.py   (exit 0 iff ALL PASS)"""
import os, sys, json, time, subprocess, shutil, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# PC2_DEV / PC2_PAGE let the same suite run against an ARCHIVED predecessor, so every round-14 case can be shown red on v5 (the round-11..13
# cases were shown red the same way). The engine a device imports travels with it: the archived pair sits in archive/ with its own pnl_path.
DEV = os.environ.get("PC2_DEV") or f"{HERE}/pc2_layer_decomposition.py"
if not os.path.isabs(DEV): DEV = os.path.join(HERE, DEV)
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
check("J4 the priced-period ACTUAL figure = windows + gaps, and is NOT closed when not all six of each are priced (R13-P2 (5): `complete` renamed)",
      abs(j["day_actual_full_day"]["priced_period_pnl_usdt"] - (j["day_actual_full_day"]["windows_pnl_usdt"] + j["day_actual_full_day"]["gaps_pnl_usdt"])) < 1e-9
      and j["day_actual_full_day"]["closed"] is False and "full_day_pnl_usdt" not in j["day_actual_full_day"], j["day_actual_full_day"])
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
_pg = os.environ.get("PC2_PAGE") or os.path.join(HERE, "..", "page", "live_page.py")
_pg = _pg if os.path.isabs(_pg) else os.path.join(HERE, _pg); _src = open(_pg).read(); _tree = _ast.parse(_src)
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
check("M2 the lower SCENARIO is the flow-at-start answer 10% (R13-M1: it is a scenario, NOT a bound — see O1)", abs(_lo_r - 0.10) < 1e-9, (_lo_r, _hi_r))
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


# ───────────────────────── [N] round 13 R13-P2 — the price chain, the fill partition, the gap population, the closure claim ─────────────────────────
print("[N] round 13 R13-P2 — one price chain, a half-open fill partition, the gap's own population, and what 'the whole day' may claim")
import importlib.util as _ilu
# the engine travels with the device: when PC2_DEV points at an archived predecessor, PC2_ENGINE points at ITS engine, so a red control really
# exercises the old code path (otherwise the gap/qty cases would silently run against the current engine and look green)
_eng = os.environ.get("PC2_ENGINE") or "pnl_path.py"
_eng = _eng if os.path.isabs(_eng) else os.path.join(HERE, _eng)
_spec = _ilu.spec_from_file_location("pnl_path_under_test", _eng); PP = _ilu.module_from_spec(_spec); _spec.loader.exec_module(PP)

# N1 — two partial flatten observations in ONE 5-minute bar (reviewer's exact event list).
_ev = [(A + 1800, "fill", -2, A + 1600), (A + 1800, "set", 8, A + 1610), (A + 1800, "fill", -3, A + 1700), (A + 1800, "set", 5, A + 1710)]
_p = PP.qty_path(10, _ev, A + 1500, A + 1500, A + 14400); _cut = PP.cut_path(10, _p[-1], A + 1500, A + 14400)
check("N1 two sets in one bar (10 -> 8 -> 5): the actual path leaves 5 and the reference position is cut to 5, not 0.8 x 0.5 x 10 = 4 (v4's value)",
      abs(_p[2][A + 1800] - 5.0) < 1e-9 and abs(_cut[1][A + 1800] - 5.0) < 1e-9, (_p[2][A + 1800], _cut[1][A + 1800]))
_ev1 = [(A + 1800, "fill", -5, A + 1600), (A + 1800, "set", 5, A + 1610)]
_c1 = PP.cut_path(10, PP.qty_path(10, _ev1, A + 1500, A + 1500, A + 14400)[-1], A + 1500, A + 14400)
check("N1b CONTROL: a single 10 -> 5 set in one bar is still a half cut", abs(_c1[1][A + 1800] - 5.0) < 1e-9, _c1[1])

# N2 — a fill exactly AT the decision time of the second anchor: corrected once, and the day's partition says so.
n2 = build("fill_at_decision", q0=10.0, orders=[], second_anchor=True, next_q=15.0, fills=[{"t": A + 14400 + 1500, "px": 100.0, "qty": 5.0, "side": "buy"}])
_w2 = [x for x in n2["anchors"] if x.get("status") == "OK" and x["anchor"] == A + 14400]
_g2 = [x for x in n2["gaps"] if x["gap_for_anchor"] == A + 14400 and x.get("status") == "GAP_OK"]
_tot2 = (_w2[0]["fill_price_correction_usdt"] if _w2 else 0.0) + (_g2[0]["fill_price_correction_usdt"] if _g2 else 0.0)
check("N2 the decision-time fill's price correction is counted ONCE across gap+window (v4 booked it on both sides)",
      abs(_tot2 - 100.0) < 1e-6, {"window": (_w2[0]["fill_price_correction_usdt"] if _w2 else None), "gap": (_g2[0]["fill_price_correction_usdt"] if _g2 else None), "sum": _tot2})
check("N2b the day receipt publishes the partition and it is disjoint with no repeats",
      n2["day_fill_partition"]["disjoint"] and n2["day_fill_partition"]["no_repeat_within_side"] and n2["day_fill_partition"]["n_double_counted"] == 0, n2["day_fill_partition"])

# N3 — the reviewer's price-reference reset: an extra post-anchor mark incompatible with the panel close.
n3root = os.path.join(SCR, "window_reference_reset")
build("window_reference_reset", q0=10.0, orders=[], second_anchor=True, next_q=10.0)
_rbp = f"{n3root}/dl_quant_live/state/live/pilot_log/{DAY}/position_readback.jsonl"
_rs = [json.loads(x) for x in open(_rbp).read().splitlines()]
_rs.append({"symbol": "AUSDT", "anchor_ts": A + 1441, "read_ts": A + 2700, "source": "fapi/v3/account@post_anchor", "venue_position_qty": 10, "venue_position_notional": 1210})
open(_rbp, "w").write("".join(json.dumps(x) + "\n" for x in _rs))
_out3 = f"{n3root}/out_r13.json"
_r3 = subprocess.run([sys.executable, DEV, DAY, _out3], capture_output=True, text=True,
                     env={**os.environ, "FP3_LIVE_REPO": f"{n3root}/dl_quant_live", "FP3_WS": f"{n3root}/wide_shadow"})
assert _r3.returncode == 0, _r3.stderr[-800:]
n3 = json.load(open(_out3))
_w3 = [x for x in n3["anchors"] if x.get("status") == "OK" and x["anchor"] == A + 14400]
_g3 = [x for x in n3["gaps"] if x["gap_for_anchor"] == A + 14400 and x.get("status") == "GAP_OK"]
_w0 = [x for x in n3["anchors"] if x.get("status") == "OK" and x["anchor"] == A]
_j3 = (_w3[0]["price_chain_joins"] if _w3 else {})
_t3 = (_j3.get("top") or [{}])[0]
check("N3 the reviewer's reset is now a NAMED reconciliation item: chain 120 vs this window's own 132 on 10 contracts = 120 USDT, reported not lost",
      bool(_w3) and bool(_g3) and abs(_t3.get("px_chain_at_b0", 0) - 120.0) < 1e-6 and abs(_t3.get("px_own_at_b0", 0) - 132.0) < 1e-6
      and abs(_t3.get("value_diff_usdt", 0) - 120.0) < 1e-6 and _j3.get("n_value_over_1cent") == 1, _t3)
check("N3b the second window PRICES on the chain (not on its own fresh mark) and the difference carries a cause, never entering P&L",
      _t3.get("cause") == "mark_vs_close" and "never added to P&L" in _j3.get("rule", ""), (_t3.get("cause"), _j3.get("causes")))

# N4 — a name whose only event is a fill inside a gap, with no previous priced layer for it.
class _MiniPanel:
    t_last = A + 14400
    def index(self, s, ref, lo, hi):
        return {b: 1 + (b - lo) / 1500 * .1 for b in range(lo, hi + 1, 300)}
class _MiniLedger:
    fills = [{"fill_ts": A + 300, "symbol": "NEW", "side": "buy", "fill_px": 100., "fill_notional": 1000., "trade_id": 7}]
    def flattens(self, *a): return []
_g4 = PP.gap_pnl(_MiniLedger(), _MiniPanel(), A, A + 1500, {"status": "OK", "per_name_layers": {"L3_actual_path": {}}, "per_name": {}})
check("N4 a name that first appears inside the gap is priced or censored with a named reason — it no longer vanishes into a clean GAP_OK (v4: n_priced 0, censored 0)",
      _g4["n_fills_in_gap"] == 1 and (_g4["n_priced"] == 1 or _g4["censored"]["n"] == 1), {k: _g4.get(k) for k in ("status", "n_fills_in_gap", "n_priced", "censored", "n_names_carried")})

# N5 — the closure claim.
check("N5 `complete` is gone; `closed` requires censored names, readback residuals, price-chain joins, the fill partition and full coverage too",
      "complete" not in n2["day_actual_full_day"] and set(n2["day_actual_full_day"]["closure_conditions"]) >=
      {"six_windows_priced", "six_gaps_priced", "no_censored_names", "no_readback_residual_over_1usdt", "no_price_chain_join_over_1pct", "fills_partitioned", "coverage_full_day"},
      n2["day_actual_full_day"]["closure_conditions"])
check("N5b the figure is labelled a research price estimate over the PRICED periods and members, not a day cash account",
      "研究口径" in n2["day_actual_full_day"]["label"] and "不是当日现金账" in n2["day_actual_full_day"]["label"], n2["day_actual_full_day"]["label"])

# ───────────────────────── [O] round 13 R13-M1 — the page's return: scenarios, and gross flow ─────────────────────────
print("[O] round 13 R13-M1 — the two sub-period numbers are SCENARIOS (the true TWR can fall outside), and net-zero is not no-flow")
_src2 = open(_pg).read(); _tree2 = _ast.parse(_src2)
_lo2 = next(n.lineno for n in _tree2.body if isinstance(n, _ast.Assign) and "flows_t" in _ast.dump(n))
_hi2 = next(n.lineno for n in _tree2.body if isinstance(n, _ast.Assign) and getattr(n.targets[0], "id", "") == "dd_twr")
_blk2 = [n for n in _tree2.body if _lo2 <= n.lineno <= _hi2]
def _page_calc(flows, navrows):
    e = {"np": np, "time": time, "collections": __import__("collections"), "inc": flows, "nav": navrows,
         "dk": list(dict.fromkeys(time.strftime("%Y%m%d", time.gmtime(float(r["nav_ts"]))) for r in navrows))}   # one key per day, as the page builds it
    exec(compile(_ast.Module(body=_blk2, type_ignores=[]), _pg, "exec"), e); return e
# O1: reviewer's path — 100 grows to 200, deposit 100 => 300, falls to 220. True TWR 46.67%, outside the pair.
_o1 = _page_calc([{"type": "TRANSFER", "asset": "USDT", "income": 100.0, "time": (A + 1000) * 1000}],
                 [{"nav_ts": A, "nav": 100.0}, {"nav_ts": A + 2000, "nav": 220.0}])
_true1 = (200.0 / 100.0) * (220.0 / 300.0) - 1.0
check("O1 the FACT stands: the true time-weighted 46.67% lies OUTSIDE the two numbers, so they are not a bound",
      _true1 > _o1["cum_hi"] + 1e-9, (_o1["cum_lo"], _o1["cum_hi"], _true1))
check("O1b the page therefore calls them SCENARIOS and warns they need not contain the truth (v4 printed them as 区间/上下界)",
      "情景" in _src2 and "真实时间加权收益" in _src2 and "可以落在两者之外" in _src2 and "46.67%" in _src2,
      {"情景": "情景" in _src2, "warn": "可以落在两者之外" in _src2, "example": "46.67%" in _src2})
check("O1c and the variables are named for what they are (`scen_lo` / `scen_hi`), not `cum_lo`-as-a-bound",
      "scen_lo" in _src2 and "scen_hi" in _src2 and "SCENARIOS, not bounds" in _src2)
# O2: net-zero gross-positive flow.
_o2 = _page_calc([{"type": "TRANSFER", "asset": "USDT", "income": 100.0, "time": (A + 1000) * 1000},
                  {"type": "TRANSFER", "asset": "USDT", "income": -100.0, "time": (A + 1500) * 1000}],
                 [{"nav_ts": A, "nav": 100.0}, {"nav_ts": A + 2000, "nav": 120.0}])
check("O2 a segment whose flows net to zero but are GROSS 200 is no longer called exact (v4: n_approx 0 and an 'exact' 20%)",
      _o2["n_approx"] == 1 and _o2["segs"][0][4] is False and abs(_o2["segs"][0][5] - 200.0) < 1e-9,
      {"n_approx": _o2["n_approx"], "seg": _o2["segs"][0]})
check("O2b CONTROL: a segment with NO flow at all is still exact and equals the plain NAV ratio",
      (lambda e: e["n_approx"] == 0 and abs(e["segs"][0][1] - 0.2) < 1e-9)(_page_calc([], [{"nav_ts": A, "nav": 100.0}, {"nav_ts": A + 2000, "nav": 120.0}])))

# ───────────────────────── [P] round 14 R14-M1/M2/M3 + the page title ─────────────────────────
print("[P] round 14 — an unmeasured readback is not a zero residual; an unknown carry is not zero; closure must cover the whole fill population")

# P1 (M1) — the real device: with NO next readback the residual is UNAVAILABLE, and closure must say so.
_p1 = build("m1_unmeasured", q0=10.0, orders=[])                      # no next_q ⇒ no readback after the window
_p1a = [x for x in _p1["anchors"] if x.get("status") == "OK"][0]
_c1 = _p1["day_actual_full_day"]["closure_conditions"]
check("P1 an UNAVAILABLE readback residual makes `readback_residual_measured` False (v5 read only n_over_1usdt, which is 0 when nothing was measured)",
      _p1a["unexplained_qty_residual"]["status"] == "UNAVAILABLE_no_readback_after_window"
      and _c1.get("readback_residual_measured") is False and _p1["day_actual_full_day"].get("n_windows_readback_unmeasured") == 1,
      {"status": _p1a["unexplained_qty_residual"]["status"], "cond": _c1.get("readback_residual_measured"),
       "n_unmeasured": _p1["day_actual_full_day"].get("n_windows_readback_unmeasured")})
_p1b = build("m1_measured", q0=10.0, orders=[], next_q=10.0)          # CONTROL: a readback exists ⇒ measured
_c1b = _p1b["day_actual_full_day"]["closure_conditions"]
check("P1b CONTROL: with a readback after the window the same condition is True and the state is CHECKED",
      _c1b.get("readback_residual_measured") is True and (_p1b["day_actual_full_day"].get("readback_residual_states") or {}).get("CHECKED") == 1,
      {"cond": _c1b.get("readback_residual_measured"), "states": _p1b["day_actual_full_day"].get("readback_residual_states")})

# P2 (M2) — the reviewer's gap case: the previous window CENSORED the name, so what it carried in is unknown.
class _MiniPanel2:
    t_last = A + 14400
    def index(self, s, ref, lo, hi):                                  # 100 -> 110 across the gap
        return {b: 1 + (b - lo) / max(hi - lo, 1) * .1 for b in range(lo, hi + 1, 300)}
class _MiniLedger2:
    fills = [{"fill_ts": A + 300, "symbol": "CEN", "side": "buy", "fill_px": 102., "fill_notional": 510., "trade_id": 9}]
    def flattens(self, *a): return []
_prev_cens = {"status": "OK", "per_name_layers": {"L3_actual_path": {"CEN": None}},
              "per_name": {"CEN": {"status": "CENSORED", "why": "panel_rows_missing_or_nonfinite", "px_b1": None}}}
_g5 = PP.gap_pnl(_MiniLedger2(), _MiniPanel2(), A, A + 1500, _prev_cens)
check("P2 a name the previous window CENSORED keeps an UNKNOWN carried quantity — it is censored `unknown_start_qty`, not priced from an implied zero "
      "(v5: GAP_OK, censored 0, profit from a 0 start; the same facts give a different answer if the carry was 10)",
      _g5["censored"]["n"] == 1 and (_g5["censored"].get("why") or {}).get("unknown_start_qty") == 1 and _g5["n_priced"] == 0
      and _g5.get("n_unknown_start_qty") == 1,
      {k: _g5.get(k) for k in ("status", "n_priced", "censored", "n_unknown_start_qty")})
class _MiniLedger2b(_MiniLedger2):
    fills = [{"fill_ts": A + 300, "symbol": "KNOWN", "side": "buy", "fill_px": 102., "fill_notional": 510., "trade_id": 9}]
_prev_known = {"status": "OK", "per_name_layers": {"L3_actual_path": {"KNOWN": {"qty_end": 0.0}}},
               "per_name": {"KNOWN": {"status": "OK", "px_b1": 100.0}}}
_g5b = PP.gap_pnl(_MiniLedger2b(), _MiniPanel2(), A, A + 1500, _prev_known)
check("P2b CONTROL: a name whose previous end quantity IS known is still priced normally (green on BOTH versions — it is the discriminator for P2)",
      _g5b["n_priced"] == 1 and _g5b["censored"]["n"] == 0 and _g5b.get("n_unknown_start_qty", 0) == 0,
      {k: _g5b.get(k) for k in ("status", "n_priced", "censored", "n_unknown_start_qty")})

# P3 (M3) — the closure expression itself, evaluated (not string-matched): a repeat on ONE side must break closure even when the two sides are disjoint.
_pc2_src = open(DEV).read(); _pc2_tree = _ast.parse(_pc2_src)
_conds_stmt = [n for n in _ast.walk(_pc2_tree) if isinstance(n, _ast.Assign) and getattr(n.targets[0], "id", "") == "_conds"]
assert len(_conds_stmt) == 1, "the closure condition assignment moved"
def _eval_conds(part, **kw):
    env = {"n_ok": 6, "gap_ok": [{}] * 6,   # the predecessor has no _resid_unmeasured; harmless there
            "_cens_names": 0, "_resid_over": 0, "_resid_unmeasured": 0, "_join_over": 0,
            "_no_nonfinite_published": True, "_resid_next_nonfinite": 0,   # R15-M1 (a v5 predecessor without these names ignores them)
           "win_cov": 77400, "gap_cov": 9000, "out": {"day_fill_partition": part}}
    env.update(kw)
    exec(compile(_ast.Module(body=[_conds_stmt[0]], type_ignores=[]), DEV, "exec"), env)
    return env["_conds"]
_rep = _eval_conds({"disjoint": True, "no_repeat_within_side": False, "covers_population": True})
check("P3 the SAME fill key twice on one side breaks `fills_partitioned` even though the two sides are disjoint (v5 asked only for `disjoint`)",
      _rep.get("fills_partitioned") is False, _rep)
_uncov = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": False})
check("P3b a corrected-fill union that does not cover the full priced population breaks `fill_population_covered` (v5 compared only the consumed subset)",
      _uncov.get("fill_population_covered") is False, _uncov)
_green = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True})
check("P3c CONTROL: with a real partition and full coverage every condition above is True", 
      _green.get("fills_partitioned") is True and _green.get("fill_population_covered") is True and _green.get("readback_residual_measured") is True, _green)
check("P3d the device publishes the population comparison it now judges on",
      set(_p1["day_fill_partition"]) >= {"n_population_in_priced_intervals", "n_population_not_corrected", "covers_population",
                                          "n_day_fills_outside_every_priced_interval"}, sorted(_p1["day_fill_partition"]))

# P4 — the page heading no longer claims a whole-day actual, and prints the evidence the figure depends on.
_src4 = open(_pg).read()
check("P4 the page no longer titles the figure 「全日实际价格损益」; it is a price estimate over the covered periods and members, stated as not closed",
      "全日实际价格损益" not in _src4 and "已覆盖时段与成员的价格估计" in _src4 and "不是当日现金账, 也未闭合" in _src4,
      {"old_title": "全日实际价格损益" in _src4, "new_title": "已覆盖时段与成员的价格估计" in _src4})
check("P4b the page prints the readback states, the price-chain joins and the unknown-carry count beside it — and still calls the returns SCENARIOS",
      "回读残差状态" in _src4 and "只有 CHECKED 才算测过" in _src4 and "只对账, 不加进损益" in _src4 and "持仓未知" in _src4 and "情景" in _src4,
      {"rb": "回读残差状态" in _src4, "join": "只对账, 不加进损益" in _src4, "unknown": "持仓未知" in _src4})

# ───────────────────────── [Q] round 15 R15-M1 (finiteness) + R15-M2 (day-boundary contract) ─────────────────────────
print("[Q] round 15 — a non-finite value is UNAVAILABLE not a clean zero; every fill is bound to ONE day-boundary contract, not left a closure footnote")
import math as _math


def _writel_q(p, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))


def build_full_day(name, *, nan_readback_k=None, mid_fill=None, extra_fills=(), run_days=(DAY,), nan_weight=False):
    """A synthetic full 24h day: 6 windows, 6 gaps, flat prices, a held AUSDT position at every anchor — it CLOSES. Mutations expose the round-15
    defects. Runs the REAL device as a subprocess for each day in run_days (nothing mocked) and returns {day: parsed json}."""
    root = os.path.join(SCR, name); shutil.rmtree(root, ignore_errors=True)
    repo = f"{root}/dl_quant_live"; ws = f"{root}/wide_shadow"; nan = float("nan"); os.makedirs(f"{repo}/state", exist_ok=True)
    log = []; anchors_by_day = {}
    for k in range(-1, 6):                                # phase_A + anchors for the prev-day-last run (gap-0 carry) and the six day runs
        Ak = A + 14400 * k; rid = f"R{k}"
        pa = {"anchor_ts": Ak, "external_wait": {"nominal_anchor_ts": Ak}, "rebalance_id": rid, "sizing": {"gross": 1000.0, "nav": 500.0}}
        log.append(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(Ak + 1500)) + " phase_A: " + json.dumps(pa))
        anchors_by_day.setdefault(time.strftime("%Y%m%d", time.gmtime(Ak)), []).append({"rebalance_id": rid, "target_gross": 1000.0, "external_book": {"gross_norm": 1.0}})
    open(f"{repo}/state/anchor_runs.log", "w").write("\n".join(log) + "\n")
    rb_by_day = {}
    for k in range(-2, 7):                                # AUSDT held 10 (mark 100) at every anchor ⇒ each window has a reference AND a next readback
        Ak = A + 14400 * k; q = nan if k == nan_readback_k else 10.0; n = nan if k == nan_readback_k else 1000.0
        rb_by_day.setdefault(time.strftime("%Y%m%d", time.gmtime(Ak)), []).append(
            {"symbol": "AUSDT", "anchor_ts": Ak + 1441.0, "read_ts": Ak + 2700.0, "source": "fapi/v3/account@post_anchor", "held": True, "targeted": True,
             "venue_position_qty": q, "venue_position_notional": n})
    fills_by_day = {}; syms = ["AUSDT"]
    if mid_fill is not None:                              # a name bought at mid_fill['t'] and held: readbacks 0 before, qty after ⇒ reconciles cleanly
        msym = mid_fill["symbol"]; mt = mid_fill["t"]; syms.append(msym)
        for k in range(-2, 7):
            Ak = A + 14400 * k; held = mid_fill["qty"] if Ak >= mt else 0.0
            rb_by_day.setdefault(time.strftime("%Y%m%d", time.gmtime(Ak)), []).append(
                {"symbol": msym, "anchor_ts": Ak + 1441.0, "read_ts": Ak + 2700.0, "source": "fapi/v3/account@post_anchor", "held": bool(held), "targeted": True,
                 "venue_position_qty": float(held), "venue_position_notional": float(held) * mid_fill["px"]})
        fills_by_day.setdefault(time.strftime("%Y%m%d", time.gmtime(mt)), []).append(
            {"anchor_ts": mt, "symbol": msym, "side": "buy", "order_type": "maker", "attempt_idx": 1, "fill_ts": mt, "fill_px": mid_fill["px"],
             "fill_notional": mid_fill["px"] * mid_fill["qty"], "rebalance_id": "RX", "trade_id": mid_fill.get("trade_id", 777), "commission": 0.0, "commission_asset": "USDT"})
    for f in extra_fills:                                 # fills used only for the day-boundary/conservation tests (classification is by timestamp)
        if f["symbol"] not in syms: syms.append(f["symbol"])
        fills_by_day.setdefault(time.strftime("%Y%m%d", time.gmtime(f["t"])), []).append(
            {"anchor_ts": f["t"], "symbol": f["symbol"], "side": f.get("side", "buy"), "order_type": "maker", "attempt_idx": 1, "fill_ts": f["t"], "fill_px": f["px"],
             "fill_notional": f["px"] * f["qty"], "rebalance_id": "RX", "trade_id": f["trade_id"], "commission": 0.0, "commission_asset": "USDT"})
    for d in set(time.strftime("%Y%m%d", time.gmtime(A + 14400 * k)) for k in range(-8, 13)):
        _writel_q(f"{repo}/state/live/pilot_log/{d}/anchors.jsonl", anchors_by_day.get(d, []))
        _writel_q(f"{repo}/state/live/pilot_log/{d}/orders.jsonl", [])
        _writel_q(f"{repo}/state/live/pilot_log/{d}/position_readback.jsonl", rb_by_day.get(d, []))
        _writel_q(f"{repo}/state/live/pilot_log/{d}/fills.jsonl", fills_by_day.get(d, []))
    os.makedirs(f"{ws}/state/target_live", exist_ok=True); os.makedirs(f"{ws}/fea171", exist_ok=True)
    for k in range(0, 6):   # nan_weight: a PRODUCER weight (never routed through the per-name ledger gate) goes non-finite — an "unpatched" injection
        json.dump({"anchor_ts": A + 14400 * k, "weights": {"AUSDT": (float("nan") if nan_weight else 1.0)}}, open(f"{ws}/state/target_live/{A + 14400 * k}.json", "w"))
    np.savez(f"{ws}/fea171/xfer_syms.npz", symbols=np.array(syms))
    ts = np.arange(A - 8 * 3600 - 28800, A + 86400 + 7200 + 300, 300, dtype=np.int64)
    np.savez(f"{ws}/state/rolling.npz", ts=ts, data=np.zeros((len(ts), len(syms), 1), np.float64))
    res = {}
    for d in run_days:
        out = f"{root}/out_{d}.json"
        r = subprocess.run([sys.executable, DEV, d, out], capture_output=True, text=True, env={**os.environ, "FP3_LIVE_REPO": repo, "FP3_WS": ws})
        open(f"{root}/run_{d}.log", "w").write(r.stdout + r.stderr); assert r.returncode == 0, (name, d, r.stderr[-800:])
        res[d] = json.load(open(out))
    return res


# Q0 — positive control: the full day closes with closed=True and a FINITE priced-period P&L (the base every round-15 red control mutates ONE thing from)
_q0 = build_full_day("q_fullday_baseline")[DAY]; _fa0 = _q0["day_actual_full_day"]
check("Q0 positive control: a full 24h day (6 windows, 6 gaps, flat prices, a held position) closes with closed=True and finite P&L, incl. the round-15 conditions",
      _fa0["closed"] is True and _fa0["priced_period_pnl_usdt"] == 0.0 and set(_fa0["closure_conditions"]) >=
      {"no_nonfinite_in_published_figures", "readback_next_finite", "no_current_day_fill_outside_priced_intervals"}, _fa0["closure_conditions"])

# Q1 (R15-M1) — a NaN readback quantity used as a window's q0: v6 kept closed=True with a NaN day P&L; now the name is CENSORED and the day refuses, finitely.
_q1 = build_full_day("q_nan_readback", nan_readback_k=2)[DAY]; _fa1 = _q1["day_actual_full_day"]
check("Q1 a NaN carried quantity is CENSORED (nonfinite_start_qty), never a clean 0: closed=False AND the priced-period P&L is FINITE (v6: it was NaN with closed=True)",
      _fa1["closed"] is False and _math.isfinite(_fa1["priced_period_pnl_usdt"]) and _fa1["closure_conditions"]["no_censored_names"] is False,
      {"closed": _fa1["closed"], "pnl": _fa1["priced_period_pnl_usdt"], "n_censored": _fa1["n_censored_names"]})

# Q2 (R15-M1) — a NaN readback used ONLY as a next-readback (the last one, never any window's q0): no name is censored and totals stay finite, yet closure must refuse.
_q2 = build_full_day("q_nan_next", nan_readback_k=6)[DAY]; _fa2 = _q2["day_actual_full_day"]
check("Q2 a NaN NEXT readback is not a clean zero residual: readback_next_finite is False and the day refuses even though no name is censored and every total is finite",
      _fa2["closed"] is False and _fa2["closure_conditions"]["readback_next_finite"] is False
      and _fa2["closure_conditions"]["no_censored_names"] is True and _fa2["closure_conditions"]["no_nonfinite_in_published_figures"] is True, _fa2["closure_conditions"])

# Q3 (R15-M1) — the gap carry the reviewer flagged (pnl_path.py lines 513-516), exercised directly: a NaN carried qty_end is DISTINCT from unknown_start_qty.
class _MiniPanelN:
    t_last = A + 14400
    def index(self, s, ref, lo, hi): return {b: 1.0 for b in range(lo, hi + 1, 300)}
class _MiniLedgerN:
    fills = []
    def flattens(self, *a): return []
_prev_nan = {"status": "OK", "per_name_layers": {"L3_actual_path": {"NANC": {"qty_end": float("nan")}}}, "per_name": {"NANC": {"status": "OK", "px_b1": 100.0}}}
_gN = PP.gap_pnl(_MiniLedgerN(), _MiniPanelN(), A, A + 1500, _prev_nan)
check("Q3 a non-finite carried qty_end is censored `nonfinite_carried_qty` (its own reason, distinct from unknown_start_qty) and priced nothing (v6: the NaN entered the path with q_known True)",
      _gN["censored"]["n"] == 1 and (_gN["censored"].get("why") or {}).get("nonfinite_carried_qty") == 1 and _gN["n_priced"] == 0
      and _gN.get("n_unknown_start_qty", 0) == 0 and _gN.get("n_nonfinite_carried", 0) == 1, {k: _gN.get(k) for k in ("status", "n_priced", "censored", "n_nonfinite_carried")})

# Q4 (R15-M1) — the closure expression itself (evaluated, not string-matched): a non-finite total or a non-finite next readback breaks closure; controls are green.
_nan_tot = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True}, _no_nonfinite_published=False)
check("Q4 a non-finite in ANY published figure breaks `no_nonfinite_in_published_figures` — the single source-agnostic checkpoint, not a per-source isfinite", _nan_tot.get("no_nonfinite_in_published_figures") is False, _nan_tot)
_nan_next = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True}, _resid_next_nonfinite=1)
check("Q4b a non-finite next readback (dropped before any sum) breaks `readback_next_finite`", _nan_next.get("readback_next_finite") is False, _nan_next)
_fin_green = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True})
check("Q4c CONTROL: finite figures and finite next readbacks ⇒ both finiteness conditions True", _fin_green.get("no_nonfinite_in_published_figures") is True and _fin_green.get("readback_next_finite") is True, _fin_green)

# Q5 (R15-M2) — a fill exactly at midnight t==d0 is bound to the PREVIOUS day under the stated (00,24] contract, not left as a closure footnote.
_q5 = build_full_day("q_midnight", mid_fill={"symbol": "MIDUSDT", "t": A, "px": 100.0, "qty": 5.0})[DAY]; _dfp5 = _q5["day_fill_partition"]
check("Q5 a midnight fill (t==d0) is attributed to the PREVIOUS day: n_adjacent_prev_day 1, NOT owned by this day, n_day_fills_outside 0 (v6: it was a this-day out-of-interval footnote with closed untouched)",
      _dfp5["n_adjacent_prev_day"] == 1 and _dfp5["n_owned_current_day"] == 0 and _dfp5["n_day_fills_outside_every_priced_interval"] == 0
      and "d0, d0+86400" in _dfp5["day_owns"] and _q5["day_actual_full_day"]["closed"] is True, _dfp5)

# Q6 (R15-M2) — a this-day fill outside every priced interval must BLOCK closure (v6: `_pop_out` fed no condition at all).
_out_blocks = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True, "n_day_fills_outside_every_priced_interval": 1})
check("Q6 a this-day fill outside every priced interval breaks `no_current_day_fill_outside_priced_intervals` — a known out-of-interval fill is no longer a footnote",
      _out_blocks.get("no_current_day_fill_outside_priced_intervals") is False, _out_blocks)
_out_ok = _eval_conds({"disjoint": True, "no_repeat_within_side": True, "covers_population": True, "n_day_fills_outside_every_priced_interval": 0})
check("Q6b CONTROL: zero this-day out-of-interval fills ⇒ the condition is True", _out_ok.get("no_current_day_fill_outside_priced_intervals") is True, _out_ok)

# Q7 (R15-M2) — CONSERVATION across two ADJACENT days: every fill in the union is attributed to EXACTLY ONE day.
_ef = [{"symbol": "AUSDT", "t": A - 43200, "px": 100.0, "qty": 1.0, "trade_id": 8001},   # prev-interior
       {"symbol": "AUSDT", "t": A,         "px": 100.0, "qty": 1.0, "trade_id": 8002},    # midnight boundary (prev day owns it)
       {"symbol": "AUSDT", "t": A + 43200, "px": 100.0, "qty": 1.0, "trade_id": 8003},    # this-interior
       {"symbol": "AUSDT", "t": A + 86400, "px": 100.0, "qty": 1.0, "trade_id": 8004}]    # next midnight (this day owns it, closed-high)
_cons = build_full_day("q_conservation", extra_fills=_ef, run_days=(PRV, DAY))
_own_D = {tuple(k) for k in _cons[DAY]["day_fill_partition"]["owned_fill_keys"]}
_own_P = {tuple(k) for k in _cons[PRV]["day_fill_partition"]["owned_fill_keys"]}
_keys = {("AUSDT", 8001), ("AUSDT", 8002), ("AUSDT", 8003), ("AUSDT", 8004)}
check("Q7 the two adjacent days own DISJOINT fill sets and together attribute every fill in the union EXACTLY ONCE",
      (_own_D & _own_P) == set() and all(((k in _own_D) + (k in _own_P)) == 1 for k in _keys), {"prev": sorted(_own_P & _keys), "day": sorted(_own_D & _keys)})
check("Q7b the midnight fill (t==d0) belongs to the PREVIOUS day, not this day ((00,24] convention)",
      ("AUSDT", 8002) in _own_P and ("AUSDT", 8002) not in _own_D, {"in_prev": ("AUSDT", 8002) in _own_P, "in_day": ("AUSDT", 8002) in _own_D})
check("Q7c next-midnight (t==d0+86400) and this-interior belong to THIS day; prev-interior to the PREVIOUS day",
      ("AUSDT", 8004) in _own_D and ("AUSDT", 8003) in _own_D and ("AUSDT", 8001) in _own_P, {"day": sorted(_own_D & _keys), "prev": sorted(_own_P & _keys)})

# Q8 — the device PUBLISHES the day-boundary contract and the adjacency populations it now binds attribution to (not just a bare footnote count).
check("Q8 the device publishes the day-boundary contract, the owned/adjacent populations and the round-15 finiteness evidence",
      set(_q5["day_fill_partition"]) >= {"day_owns", "n_owned_current_day", "n_adjacent_prev_day", "n_adjacent_next_day", "owned_fill_keys"}
      and set(_fa0) >= {"no_nonfinite_in_published_figures", "n_nonfinite_next_readback", "n_day_fills_outside_every_priced_interval", "n_adjacent_prev_day_fills"},
      {"dfp": sorted(_q5["day_fill_partition"]), "fa": sorted(_fa0)})

# Q9 (R15-M1 STRUCTURAL) — THE class-shaped proof the reviewer asked for: introduce a non-finite value on a path I did NOT explicitly patch, and show
# closure still refuses. A PRODUCER weight (target_live) goes NaN; it is never read through any per-name ledger gate, so NO name is censored and no
# per-source isfinite fires — the NaN flows into the L0 layer and the day totals, and the SINGLE source-agnostic checkpoint refuses closure. A fix that
# only "added isfinite where NaN currently leaks" would sail past this (it never patched the producer-weight path); the structural checkpoint catches it.
_q9 = build_full_day("q_nonfinite_unpatched", nan_weight=True)[DAY]; _fa9 = _q9["day_actual_full_day"]; _c9 = _fa9["closure_conditions"]
check("Q9 a NaN on an UNPATCHED path (a producer weight) refuses closure via no_nonfinite_in_published_figures ALONE — no name censored, no per-source check fired",
      _fa9["closed"] is False and _c9["no_nonfinite_in_published_figures"] is False and _c9["no_censored_names"] is True
      and _c9["readback_next_finite"] is True and _c9["no_unknown_start_qty_in_gaps"] is True,
      {"closed": _fa9["closed"], "no_nonfinite_in_published_figures": _c9["no_nonfinite_in_published_figures"], "no_censored_names": _c9["no_censored_names"]})
check("Q9b and the checkpoint is source-agnostic: the L0 producer day total is where this particular NaN surfaced (a different field would surface elsewhere and still refuse)",
      not _math.isfinite(_q9["day_totals_over_ok_anchors_usdt"]["L0_producer"]), _q9["day_totals_over_ok_anchors_usdt"])

check("Z baseline was green before the red cases were read", baseline_green)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}  ({N[0]} checks)")
sys.exit(0 if not FAILS else 1)
