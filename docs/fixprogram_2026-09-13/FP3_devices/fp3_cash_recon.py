#!/usr/bin/env python3
"""FP3 item D — independent cash reconciliation over the LIVE ledgers (read-only). v3 (2026-09-18, after independent review FP3-R01…R04):
 (1) fills deduped by trade_id (latest backfilled row wins); populations split by order_type: REGULAR = maker/topup_taker, PROTECTIVE = protective_flatten/exit_only/reconstructed.
 (2) positions rebuilt from fills and compared with every post-anchor venue readback; on a mismatch the QUANTITY is re-seated to the venue AND the cost basis is
     marked UNKNOWN for that name (R01) until the recorded fills bring it flat again; realised P&L (average cost) is produced only while the basis is known,
     the rest is reported as realised_unknown (count + notional), never as a number.
 (3) mark-to-market NAV IDENTITY per NAV snapshot window (prev nav_ts → nav_ts]: ΔNAV − flow = Σ_s [qty_s(t1)·mark_s(t1) − qty_s(t0)·mark_s(t0) − Σ_fills sgn·q·px]
     + funding(window) − fees(window) + residual; marks are the venue readback notional/qty at the window ends (no cost basis needed); a name whose venue
     quantity at t1 differs from qty(t0)+recorded fills is a POSITION GAP and its term is the venue side (the gap is what the residual carries).
     VERDICT = RECONCILED if every window |residual| ≤ max(2 USDT, 0.5 bp·NAV) and no gap; PARTIAL (windows named) otherwise; UNAVAILABLE if a window has no marks.
 (4) daily comparisons with the NAV row's venue figures use ONE cutoff = the row's nav_ts for realised / commission (USDT-equivalent AND native) / funding (R03).
 (5) slippage vs mid-at-anchor on the MATCHED order population only (numerator and denominator from the same orders), coverage reported (R02); fee tables per population and with/without protective buckets.
 (6) every mismatch anchor is classified: flatten bucket / single-name / OTHER (named; R04: 2026-08-02 08Z).
usage: fp3_cash_recon.py <out.json> [from_day] [to_day]"""
import glob, hashlib, json, os, sys, time, collections
VERSION = "v3-2026-09-18"
LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); OUT = sys.argv[1]
BNB_P = os.path.join(os.path.dirname(os.path.abspath(OUT)), "BNBUSDT_daily_20260801_20260918.json")
BNB = {d: v["close"] for d, v in json.load(open(BNB_P))["days"].items()} if os.path.isfile(BNB_P) else {}
D0 = sys.argv[2] if len(sys.argv) > 2 else "20260801"; D1 = sys.argv[3] if len(sys.argv) > 3 else "20991231"
days = sorted(d.split("/")[-1] for d in glob.glob(f"{LED}/2026*") if D0 <= d.split("/")[-1] <= D1)
day_of = lambda ts: time.strftime("%Y%m%d", time.gmtime(float(ts))); U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))
REGULAR = {"maker", "topup_taker"}; PROTECTIVE = {"protective_flatten", "exit_only", "reconstructed"}
def rows(day, name):
    p = f"{LED}/{day}/{name}.jsonl"
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.isfile(p) else []
def fee_usdt(r):
    a = r.get("commission_asset"); c = float(r.get("commission") or 0.0)
    if a == "USDT": return c
    if a == "BNB":
        px = BNB.get(day_of(r["fill_ts"]))
        if px is None: raise KeyError(f"no BNBUSDT close for {day_of(r['fill_ts'])}")
        return c * px
    raise ValueError(f"commission asset {a}")
inputs = {f"{d}/{n}": hashlib.sha256(open(f"{LED}/{d}/{n}.jsonl", "rb").read()).hexdigest()[:16] for d in days for n in ("fills", "orders", "funding", "position_readback", "daily_nav", "anchors") if os.path.isfile(f"{LED}/{d}/{n}.jsonl")}
# ── (1) fills ──
by_tid = {}; n_raw = 0
for d in days:
    for r in rows(d, "fills"):
        n_raw += 1; t = r.get("trade_id"); k = (r.get("backfilled_utc") or "", d)
        if t not in by_tid or k >= by_tid[t][0]: by_tid[t] = (k, r)
fills = sorted((r for _, r in by_tid.values()), key=lambda r: (float(r["fill_ts"]), str(r.get("trade_id"))))
for r in fills: r["_pop"] = "REGULAR" if r.get("order_type") in REGULAR else ("PROTECTIVE" if r.get("order_type") in PROTECTIVE else "OTHER")
qty_of = lambda r: float(r["fill_notional"]) / float(r["fill_px"]) if float(r["fill_px"]) else 0.0
sgn = lambda r: 1.0 if str(r.get("side", "")).upper() == "BUY" else -1.0
# ── readbacks / nav rows / funding ──
readbacks = sorted((r for d in days for r in rows(d, "position_readback")), key=lambda r: float(r["read_ts"]))
FLAT = sorted({(day_of(r["read_ts"]), int(round(float(r["read_ts"]) / 60) * 60)) for r in readbacks if "flatten" in str(r.get("source"))})
rb_by_anchor = collections.defaultdict(dict)
for r in readbacks: rb_by_anchor[int(float(r["anchor_ts"]) // 14400 * 14400)][r["symbol"]] = r
nav_rows = {}
for d in days:
    for r in rows(d, "daily_nav"):
        if r.get("mode") in (None, "LIVE"): nav_rows[d] = r
FUND = [x for d in days for x in rows(d, "funding")]
# ── (2) positions with cost-basis state ──
pos = collections.defaultdict(float); avg = collections.defaultdict(float); known = collections.defaultdict(lambda: True)
realised_by_fill = {}; realised_unknown = {"n_fills": 0, "notional": 0.0, "names": set()}; comm_native = collections.defaultdict(float)
def apply_fill(r):
    s, q, px = r["symbol"], qty_of(r) * sgn(r), float(r["fill_px"]); p0 = pos[s]; k = (day_of(r["fill_ts"]), float(r["fill_ts"]))
    if p0 == 0 or (p0 > 0) == (q > 0):
        if p0 == 0: known[s] = True; avg[s] = px
        elif known[s]: avg[s] = (abs(p0) * avg[s] + abs(q) * px) / (abs(p0) + abs(q))
        pos[s] = p0 + q
    else:
        closed = min(abs(p0), abs(q))
        if known[s]: realised_by_fill[k] = realised_by_fill.get(k, 0.0) + (px - avg[s]) * closed * (1 if p0 > 0 else -1)
        else: realised_unknown["n_fills"] += 1; realised_unknown["notional"] += closed * px; realised_unknown["names"].add(s)
        pos[s] = p0 + q
        if abs(pos[s]) < 1e-12: pos[s] = 0.0; avg[s] = 0.0; known[s] = True
        elif (pos[s] > 0) != (p0 > 0): avg[s] = px; known[s] = True
    comm_native[(day_of(r["fill_ts"]), r.get("commission_asset"))] += float(r.get("commission") or 0.0)
fi = 0; pos_checks = []; last_px = {}
for A in sorted(rb_by_anchor):
    rb = rb_by_anchor[A]; t_read = max(float(r["read_ts"]) for r in rb.values())
    while fi < len(fills) and float(fills[fi]["fill_ts"]) <= t_read: last_px[fills[fi]["symbol"]] = float(fills[fi]["fill_px"]); apply_fill(fills[fi]); fi += 1
    names = set(rb) | {s for s, q in pos.items() if abs(q) > 1e-12}; n_mis = 0; usd_mis = 0.0; worst = None; mis_names = []
    for s in names:
        vq = float(rb[s]["venue_position_qty"]) if s in rb else 0.0; rq = pos.get(s, 0.0); px = (abs(float(rb[s]["venue_position_notional"])) / abs(vq)) if s in rb and vq else last_px.get(s, 0.0)
        du = abs(vq - rq) * px
        if du > 1.0:
            n_mis += 1; usd_mis += du; mis_names.append(s)
            if worst is None or du > worst[1]: worst = (s, round(du, 2), round(vq, 6), round(rq, 6))
    fl = [U(t) for (dd, t) in FLAT if A <= t < A + 14400]
    cat = "flatten_bucket" if (n_mis and fl) else ("single_name" if n_mis == 1 else ("OTHER" if n_mis else "ok"))
    pos_checks.append({"anchor_ts": A, "anchor": U(A), "n_names_venue": len(rb), "n_mismatch_gt_1usd": n_mis, "usd_mismatch": round(usd_mis, 2), "worst": worst, "flatten_in_bucket": fl, "category": cat, "readback_sources": sorted({str(r.get("source")) for r in rb.values()})})
    for s in names:                                       # re-seat on the venue truth; the basis becomes UNKNOWN for a re-seated open position (R01)
        vq = float(rb[s]["venue_position_qty"]) if s in rb else 0.0
        if abs(vq - pos.get(s, 0.0)) > 1e-9:
            pos[s] = vq
            if abs(vq) < 1e-12: avg[s] = 0.0; known[s] = True
            else: known[s] = False
while fi < len(fills): apply_fill(fills[fi]); fi += 1
# ── (3) NAV identity per snapshot window ──
nav_seq = sorted(nav_rows.values(), key=lambda r: float(r["nav_ts"])); windows = []; fill_i = 0
fills_sorted = fills
def marks_at(ts):
    A = int(float(ts) // 14400 * 14400); rb = rb_by_anchor.get(A, {})
    return {s: (float(r["venue_position_qty"]), (abs(float(r["venue_position_notional"])) / abs(float(r["venue_position_qty"]))) if float(r["venue_position_qty"]) else 0.0) for s, r in rb.items()}, (max(float(r["read_ts"]) for r in rb.values()) if rb else None)
for i in range(1, len(nav_seq)):
    r0, r1 = nav_seq[i - 1], nav_seq[i]; t0, t1 = float(r0["nav_ts"]), float(r1["nav_ts"]); m0, rt0 = marks_at(t0); m1, rt1 = marks_at(t1)
    if not m0 or not m1 or rt0 is None or rt1 is None: windows.append({"from": U(t0), "to": U(t1), "status": "UNAVAILABLE (no readback marks)"}); continue
    fw = [f for f in fills_sorted if rt0 < float(f["fill_ts"]) <= rt1]; cash = collections.defaultdict(float); q_rec = collections.defaultdict(float)
    for f in fw: q = qty_of(f) * sgn(f); cash[f["symbol"]] += q * float(f["fill_px"]); q_rec[f["symbol"]] += q
    names = set(m0) | set(m1) | set(q_rec); term = 0.0; gaps = []
    for s in names:
        q0, mk0 = m0.get(s, (0.0, 0.0)); q1, mk1 = m1.get(s, (0.0, 0.0))
        term += q1 * mk1 - q0 * mk0 - cash[s]
        if abs((q0 + q_rec[s]) - q1) * (mk1 or mk0 or 1.0) > 1.0: gaps.append((s, round((q0 + q_rec[s]) - q1, 4)))
    fund = sum(float(x.get("funding_paid") or 0.0) for x in FUND if rt0 < float(x["settlement_ts"]) <= rt1); fees = sum(fee_usdt(f) for f in fw)
    dnav = float(r1["nav"]) - float(r1.get("external_flow_usdt") or 0.0) - float(r0["nav"]); explained = term + fund - fees; resid = dnav - explained
    # venue-side funding for a standard row→row window: the settlements in (t0, t1] are exactly those the t1 row counts "since 00:00Z" (no settlement
    # falls between a 20:4x row and midnight), so the venue FUNDING_FEE of row t1 replaces the local read-age approximation; also venue COMMISSION when present
    bt1 = r1.get("realised_by_type") or {}; std_window = 20.0 <= (t1 - t0) / 3600 <= 28.0 and time.gmtime(t0).tm_hour >= 20 and time.gmtime(t1).tm_hour >= 20
    fund_v = float(bt1["FUNDING_FEE"]) if (std_window and bt1.get("FUNDING_FEE") is not None) else None
    fees_v = -float(bt1["COMMISSION"]) if (std_window and bt1.get("COMMISSION") is not None and (r1.get("realised_by_type_asset") or {}).get("COMMISSION")) else None
    explained_v = (term + fund_v - (fees_v if fees_v is not None else fees)) if fund_v is not None else None; resid_v = (dnav - explained_v) if explained_v is not None else None
    tol = max(2.0, 0.5e-4 * float(r0["nav"]))
    windows.append({"from": U(t0), "to": U(t1), "hours": round((t1 - t0) / 3600, 2), "dnav_ex_flow": round(dnav, 2), "mtm_positions_and_fills": round(term, 2), "funding": round(fund, 2), "fees": round(fees, 2), "explained": round(explained, 2), "residual": round(resid, 2),
                    "funding_venue": None if fund_v is None else round(fund_v, 2), "fees_venue": None if fees_v is None else round(fees_v, 2), "residual_venue_funding": None if resid_v is None else round(resid_v, 2), "tol": round(tol, 2), "n_fills": len(fw), "position_gaps": gaps[:10], "n_gaps": len(gaps),
                    "ok": abs(resid) <= tol and not gaps, "ok_venue_funding": (resid_v is not None and abs(resid_v) <= tol and not gaps)})
n_ok = sum(1 for w in windows if w.get("ok") or w.get("ok_venue_funding")); n_un = sum(1 for w in windows if "status" in w); n_bad = len(windows) - n_ok - n_un
VERDICT = "UNAVAILABLE" if n_un == len(windows) else ("RECONCILED" if n_bad == 0 and n_un == 0 else "PARTIAL")
# ── (4) daily comparisons at the row's cutoff ──
fund_rows = collections.defaultdict(list)
for x in FUND: fund_rows[day_of(x["settlement_ts"])].append(x)
daily = []
for d in sorted(nav_rows):
    r = nav_rows[d]; bt = r.get("realised_by_type") or {}; ba = r.get("realised_by_type_asset") or {}; cut = float(r.get("nav_ts") or 0) or None
    inrow = lambda ts: day_of(ts) == d and (cut is None or float(ts) <= cut)
    l_comm_usdt = sum(fee_usdt(x) for x in fills if inrow(x["fill_ts"])); l_native = collections.defaultdict(float)
    for x in fills:
        if inrow(x["fill_ts"]): l_native[x.get("commission_asset")] += float(x.get("commission") or 0.0)
    l_real = sum(v for (dd, ts), v in realised_by_fill.items() if dd == d and (cut is None or ts <= cut)); l_fund = sum(float(x.get("funding_paid") or 0.0) for x in fund_rows.get(d, []) if cut is None or float(x["settlement_ts"]) <= cut)
    v_comm = {a: float(v) for a, v in (ba.get("COMMISSION") or {}).items()}
    rec = {"day": d, "nav_ts_utc": time.strftime("%H:%M:%SZ", time.gmtime(cut)) if cut else None, "venue_realized_pnl": bt.get("REALIZED_PNL"), "local_realized_known": round(l_real, 4), "venue_funding": bt.get("FUNDING_FEE"), "local_funding": round(l_fund, 4), "venue_commission_total": bt.get("COMMISSION"), "local_commission_usdt_equiv": round(-l_comm_usdt, 4), "local_commission_native": {a: round(-v, 6) for a, v in l_native.items()}, "venue_commission_by_asset": v_comm or None, "bnb_close": BNB.get(d), "flatten_events": [time.strftime("%H:%MZ", time.gmtime(t)) for (dd, t) in FLAT if dd == d]}
    rec["d_realized"] = None if bt.get("REALIZED_PNL") is None else round(l_real - float(bt["REALIZED_PNL"]), 4); rec["d_funding"] = None if bt.get("FUNDING_FEE") is None else round(l_fund - float(bt["FUNDING_FEE"]), 4)
    rec["d_commission_total"] = None if bt.get("COMMISSION") is None else round(-l_comm_usdt - float(bt["COMMISSION"]), 4)
    rec["d_commission_by_asset"] = ({a: round(-l_native.get(a, 0.0) - v_comm.get(a, 0.0), 6) for a in set(v_comm) | set(l_native)} if v_comm else "venue by-asset breakdown not recorded this day")
    daily.append(rec)
# ── (5) cost tables on matched populations ──
fills_notional = sum(abs(float(r["fill_notional"])) for r in fills)
fa = collections.defaultdict(lambda: {"traded": 0.0, "fee": 0.0, "maker_notional": 0.0, "n_fills": 0, "day": None, "protective_notional": 0.0})
for r in fills:
    A = int(float(r["anchor_ts"]) // 14400 * 14400); x = fa[A]; fn = abs(float(r["fill_notional"])); x["traded"] += fn; x["fee"] += fee_usdt(r); x["n_fills"] += 1; x["day"] = day_of(r["fill_ts"])
    if r.get("venue_maker_flag") is True: x["maker_notional"] += fn
    if r["_pop"] == "PROTECTIVE": x["protective_notional"] += fn
slip = collections.defaultdict(lambda: [0.0, 0.0, 0])
for d in days:
    for r in rows(d, "orders"):
        fn = abs(float(r.get("filled_notional") or 0.0)); px = r.get("avg_fill_px"); mid = r.get("mid_at_anchor")
        if fn and px and mid:
            A = int(float(r["anchor_ts"]) // 14400 * 14400); side = 1.0 if float(r.get("intended_notional") or 0.0) > 0 else -1.0
            slip[A][0] += (float(px) - float(mid)) / float(mid) * side * fn; slip[A][1] += fn; slip[A][2] += 1
cost = []
for A in sorted(fa):
    x = fa[A]; navd = nav_rows.get(x["day"], {}).get("nav"); sl = slip.get(A)
    cost.append({"anchor_ts": A, "day": x["day"], "traded_usdt": round(x["traded"], 2), "fee_usdt": round(x["fee"], 4), "fee_bps_of_traded": round(x["fee"] / x["traded"] * 1e4, 3) if x["traded"] else None, "maker_share_notional": round(x["maker_notional"] / x["traded"], 4) if x["traded"] else None,
                 "slip_matched_num": round(sl[0], 6) if sl else None, "slip_matched_den": round(sl[1], 2) if sl else None, "slip_matched_orders": sl[2] if sl else 0, "slip_coverage_of_fills": round(sl[1] / x["traded"], 3) if sl and x["traded"] else None,
                 "turnover_frac_2nav": round(x["traded"] / (2 * navd), 4) if navd else None, "n_fills": x["n_fills"], "protective_share": round(x["protective_notional"] / x["traded"], 3) if x["traded"] else None, "has_protective": x["protective_notional"] > 0})
def agg(sub):
    T = sum(c["traded_usdt"] for c in sub); F = sum(c["fee_usdt"] for c in sub); M = sum((c["maker_share_notional"] or 0) * c["traded_usdt"] for c in sub); sn = sum(c["slip_matched_num"] or 0 for c in sub); sd = sum(c["slip_matched_den"] or 0 for c in sub)
    return {"anchors": len(sub), "traded": round(T, 2), "fee_bps_of_traded": round(F / T * 1e4, 4) if T else None, "maker_share": round(M / T, 4) if T else None, "slippage_bps_matched": round(sn / sd * 1e4, 4) if sd else None, "slip_coverage": round(sd / T, 3) if T else None, "turnover_median": (lambda v: v[len(v) // 2] if v else None)(sorted(c["turnover_frac_2nav"] for c in sub if c["turnover_frac_2nav"] is not None))}
pop = {"REGULAR": collections.Counter(), "PROTECTIVE": collections.Counter(), "OTHER": collections.Counter()}
for r in fills: p = pop[r["_pop"]]; fn = abs(float(r["fill_notional"])); p["n"] += 1; p["traded"] += fn; p["fee"] += fee_usdt(r); p["maker"] += fn if r.get("venue_maker_flag") is True else 0
cost_sum = {"all_anchors": agg(cost), "since_0907_all": agg([c for c in cost if c["day"] >= "20260907"]), "since_0907_without_protective_buckets": agg([c for c in cost if c["day"] >= "20260907" and not c["has_protective"]]), "bnb_era_0805_0906": agg([c for c in cost if "20260805" <= c["day"] <= "20260906"]),
            "by_population": {k: {"n_fills": v["n"], "traded": round(v["traded"], 2), "fee_bps": round(v["fee"] / v["traded"] * 1e4, 4) if v["traded"] else None, "maker_share": round(v["maker"] / v["traded"], 4) if v["traded"] else None} for k, v in pop.items()},
            "note": "slippage = signed (avg_fill_px − mid_at_anchor) over the MATCHED order population only (coverage reported); it is not a post-fill markout"}
pos_sum = {"anchors_checked": len(pos_checks), "anchors_with_mismatch": sum(1 for p in pos_checks if p["n_mismatch_gt_1usd"]), "by_category": dict(collections.Counter(p["category"] for p in pos_checks if p["n_mismatch_gt_1usd"])), "usd_mismatch_total": round(sum(p["usd_mismatch"] for p in pos_checks), 2),
           "OTHER_anchors": [{k: p[k] for k in ("anchor", "n_mismatch_gt_1usd", "usd_mismatch", "worst")} for p in pos_checks if p["category"] == "OTHER"], "flatten_events": [U(t) for (dd, t) in FLAT],
           "realised_unknown": {"n_fills": realised_unknown["n_fills"], "notional": round(realised_unknown["notional"], 2), "n_names": len(realised_unknown["names"])}}
day_sum = {"days": len(daily), "d_realized_known_abs_sum": round(sum(abs(x["d_realized"]) for x in daily if x["d_realized"] is not None), 2), "d_funding_abs_sum": round(sum(abs(x["d_funding"]) for x in daily if x["d_funding"] is not None), 2), "d_commission_total_abs_sum": round(sum(abs(x["d_commission_total"]) for x in daily if x["d_commission_total"] is not None), 4),
           "days_commission_total_off_gt_1usd": [(x["day"], x["d_commission_total"]) for x in daily if x["d_commission_total"] is not None and abs(x["d_commission_total"]) > 1], "days_with_venue_by_asset": sum(1 for x in daily if x["venue_commission_by_asset"])}
out = {"device": "fp3_cash_recon.py", "version": VERSION, "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "days": [days[0], days[-1], len(days)], "inputs_sha16": inputs,
       "VERDICT": VERDICT, "nav_identity": {"windows": windows, "n_windows": len(windows), "n_ok": n_ok, "n_bad": n_bad, "n_unavailable": n_un, "tolerance": "max(2 USDT, 0.5 bp × NAV)", "residual_abs_sum": round(sum(abs(w["residual"]) for w in windows if "residual" in w), 2), "residual_venue_funding_abs_sum": round(sum(abs(w["residual_venue_funding"]) for w in windows if w.get("residual_venue_funding") is not None), 2), "n_ok_local_funding": sum(1 for w in windows if w.get("ok")), "n_ok_venue_funding": sum(1 for w in windows if w.get("ok_venue_funding")),
                        "windows_bad": [(w["from"], w["to"], w["residual"], w.get("residual_venue_funding"), w["n_gaps"]) for w in windows if "residual" in w and not (w["ok"] or w["ok_venue_funding"])], "reads": "a window reconciles if EITHER the local-funding or the venue-funding identity is within tolerance and no position gap exists; residual_venue_funding uses the venue FUNDING_FEE of the end row (and venue COMMISSION where the by-asset breakdown exists)"},
       "fills": {"raw_rows": n_raw, "distinct_trade_ids": len(by_tid), "notional_total": round(fills_notional, 2)}, "positions_vs_readback": pos_sum, "positions_per_anchor": pos_checks, "daily": daily, "daily_summary": day_sum, "cost_per_anchor": cost, "cost_summary": cost_sum}
json.dump(out, open(OUT, "w"), indent=1)
print("VERDICT", VERDICT, {k: out["nav_identity"][k] for k in ("n_windows", "n_ok", "n_bad", "n_unavailable", "residual_abs_sum")}); print("bad windows:", out["nav_identity"]["windows_bad"][:12]); print("positions:", {k: v for k, v in pos_sum.items() if k != "flatten_events"}); print("cost:", json.dumps(cost_sum)[:900]); print("daily:", day_sum)
