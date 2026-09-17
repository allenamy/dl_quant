#!/usr/bin/env python3
"""FP3 item D (2026-09-17): independent cash reconciliation over the LIVE ledgers (read-only). See DESIGN_FP3_D_cash_reconciliation_2026-09-17.md.
Inputs: dl_quant_live/state/live/pilot_log/<day>/{fills,orders,funding,position_readback,daily_nav,anchors}.jsonl. Output: one receipt.
Steps: (1) fills deduped by trade_id (latest backfilled row wins); (2) positions rebuilt from fills (qty = notional/px, signed by side) and compared
with every post-anchor venue readback; (3) cash decomposition per day: realised (average-cost), commission by ASSET (native units, no price needed),
funding from funding.jsonl; (4) reconciled with the venue income stream recorded in daily_nav (REALIZED_PNL / COMMISSION per asset / FUNDING_FEE)
and the NAV walk; (5) the true per-anchor cost table (fee bps of traded notional from orders.fee_all_usdt, slippage vs mid_at_anchor, maker share,
turnover as Σ|traded| / (2·NAV)). Verdict = counts and residuals; nothing is modified."""
import glob, hashlib, json, os, sys, time, collections, math
LED = os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); OUT = sys.argv[1]
BNB_P = os.path.join(os.path.dirname(os.path.abspath(OUT)), "BNBUSDT_daily_20260801_20260918.json")     # public klines, fetched 2026-09-17 (receipt beside the output)
BNB = {d: v["close"] for d, v in json.load(open(BNB_P))["days"].items()} if os.path.isfile(BNB_P) else {}
day_of = lambda ts: time.strftime("%Y%m%d", time.gmtime(float(ts)))
def fee_usdt(r):
    """a fill's commission in USDT: USDT as is; BNB × that day's BNBUSDT close (the venue charged BNB for EVERY fill 08-05..09-06); other assets refused"""
    a = r.get("commission_asset"); c = float(r.get("commission") or 0.0)
    if a == "USDT": return c
    if a == "BNB":
        px = BNB.get(day_of(r["fill_ts"]))
        if px is None: raise KeyError(f"no BNBUSDT close for {day_of(r['fill_ts'])}")
        return c * px
    raise ValueError(f"commission asset {a}")
D0 = sys.argv[2] if len(sys.argv) > 2 else "20260801"; D1 = sys.argv[3] if len(sys.argv) > 3 else "20991231"
days = sorted(d.split("/")[-1] for d in glob.glob(f"{LED}/2026*") if D0 <= d.split("/")[-1] <= D1)
def rows(day, name):
    p = f"{LED}/{day}/{name}.jsonl"
    if not os.path.isfile(p): return []
    return [json.loads(l) for l in open(p) if l.strip()]
inputs = {}
for d in days:
    for n in ("fills", "orders", "funding", "position_readback", "daily_nav", "anchors"):
        p = f"{LED}/{d}/{n}.jsonl"
        if os.path.isfile(p): inputs[f"{d}/{n}"] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
# ── (1) fills, deduped ──
by_tid = {}; n_raw = 0
for d in days:
    for r in rows(d, "fills"):
        n_raw += 1; t = r.get("trade_id"); k = (r.get("backfilled_utc") or "", d)
        if t not in by_tid or k >= by_tid[t][0]: by_tid[t] = (k, r)
fills = sorted((r for _, r in by_tid.values()), key=lambda r: (float(r["fill_ts"]), str(r.get("trade_id"))))
def qty_of(r): return float(r["fill_notional"]) / float(r["fill_px"]) if float(r["fill_px"]) else 0.0
def sgn(r): return 1.0 if str(r.get("side", "")).upper() == "BUY" else -1.0
# ── (2) positions vs venue readback ──
realised_by_fill = {}; pos = collections.defaultdict(float); avg = collections.defaultdict(float); realised_by_day = collections.defaultdict(float); comm_by_day_asset = collections.defaultdict(float)
day_of = lambda ts: time.strftime("%Y%m%d", time.gmtime(float(ts)))
readbacks = []
for d in days:
    for r in rows(d, "position_readback"): readbacks.append(r)
readbacks.sort(key=lambda r: float(r["read_ts"]))
FLAT = sorted({(day_of(r["read_ts"]), int(round(float(r["read_ts"]) / 60) * 60)) for r in readbacks if "flatten" in str(r.get("source"))})
rb_by_anchor = collections.defaultdict(dict)
for r in readbacks: rb_by_anchor[int(float(r["anchor_ts"]) // 14400 * 14400)][r["symbol"]] = r
fi = 0; pos_checks = []; last_px = {}
def apply_fill(r):
    s, q, px = r["symbol"], qty_of(r) * sgn(r), float(r["fill_px"]); p0 = pos[s]; last_px[s] = px
    if p0 == 0 or (p0 > 0) == (q > 0): avg[s] = (abs(p0) * avg[s] + abs(q) * px) / (abs(p0) + abs(q)) if abs(p0) + abs(q) else px; pos[s] = p0 + q
    else:
        closed = min(abs(p0), abs(q)); _rp = (px - avg[s]) * closed * (1 if p0 > 0 else -1); realised_by_day[day_of(r["fill_ts"])] += _rp; realised_by_fill[(day_of(r["fill_ts"]), float(r["fill_ts"]))] = realised_by_fill.get((day_of(r["fill_ts"]), float(r["fill_ts"])), 0.0) + _rp; pos[s] = p0 + q
        if abs(pos[s]) > 1e-12 and (pos[s] > 0) != (p0 > 0): avg[s] = px
        if abs(pos[s]) < 1e-12: pos[s] = 0.0; avg[s] = 0.0
    comm_by_day_asset[(day_of(r["fill_ts"]), r.get("commission_asset"))] += float(r.get("commission") or 0.0)
for A in sorted(rb_by_anchor):
    rb = rb_by_anchor[A]; t_read = max(float(r["read_ts"]) for r in rb.values())
    while fi < len(fills) and float(fills[fi]["fill_ts"]) <= t_read: apply_fill(fills[fi]); fi += 1
    n_mis = 0; worst = None; usd_mis = 0.0
    names = set(rb) | {s for s, q in pos.items() if abs(q) > 1e-12}
    for s in names:
        vq = float(rb[s]["venue_position_qty"]) if s in rb else 0.0; rq = pos.get(s, 0.0); px = (abs(float(rb[s]["venue_position_notional"])) / abs(vq)) if s in rb and vq else last_px.get(s, 0.0)
        du = abs(vq - rq) * px
        if du > 1.0:
            n_mis += 1; usd_mis += du
            if worst is None or du > worst[1]: worst = (s, round(du, 2), round(vq, 6), round(rq, 6))
    fl = [time.strftime("%m-%d %H:%MZ", time.gmtime(t)) for (dd, t) in FLAT if A <= t < A + 14400]
    pos_checks.append({"anchor_ts": A, "n_names_venue": len(rb), "n_mismatch_gt_1usd": n_mis, "usd_mismatch": round(usd_mis, 2), "worst": worst, "flatten_in_bucket": fl, "readback_sources": sorted({str(r.get("source")) for r in rb.values()})})
    # re-seat the reconstruction on the venue truth so later anchors measure NEW mismatches, not carried ones (the carried ones are listed above)
    for s in names:
        vq = float(rb[s]["venue_position_qty"]) if s in rb else 0.0
        if abs(vq - pos.get(s, 0.0)) > 1e-9: pos[s] = vq
while fi < len(fills): apply_fill(fills[fi]); fi += 1
# ── (3)/(4) daily reconciliation with the venue income stream in daily_nav ──
fund_by_day = collections.defaultdict(float); FUND_ROWS = {}
for d in days:
    FUND_ROWS[d] = rows(d, "funding")
    for r in FUND_ROWS[d]: fund_by_day[day_of(r["settlement_ts"])] += float(r.get("funding_paid") or 0.0)
nav_rows = {}
for d in days:
    for r in rows(d, "daily_nav"):
        if r.get("mode") in (None, "LIVE"): nav_rows[r["day"]] = r      # last row of the day wins
daily = []
for d in sorted(nav_rows):
    r = nav_rows[d]; bt = r.get("realised_by_type") or {}; ba = r.get("realised_by_type_asset") or {}
    v_comm = {a: float(x) for a, x in (ba.get("COMMISSION") or {}).items()}; l_comm = {a: round(v, 6) for (dd, a), v in comm_by_day_asset.items() if dd == d}
    cut_ts = float(r.get("nav_ts") or 0) or None                                      # the venue figures in this row are 'since 00:00Z' AS OF nav_ts, not the whole day
    in_row = (lambda ts: day_of(ts) == d and (cut_ts is None or float(ts) <= cut_ts))
    l_comm_usdt = round(sum(fee_usdt(x) for x in fills if in_row(x["fill_ts"])), 4)
    l_comm_after = round(sum(fee_usdt(x) for x in fills if day_of(x["fill_ts"]) == d and cut_ts is not None and float(x["fill_ts"]) > cut_ts), 4)
    l_real_row = round(sum(v for (dd, ts), v in realised_by_fill.items() if dd == d and (cut_ts is None or ts <= cut_ts)), 4)
    l_fund_row = round(sum(float(x.get("funding_paid") or 0.0) for dd2 in days for x in (FUND_ROWS.get(dd2) or []) if day_of(x["settlement_ts"]) == d and (cut_ts is None or float(x["settlement_ts"]) <= cut_ts)), 4)
    rec = {"day": d, "nav_ts_utc": time.strftime("%H:%M:%SZ", time.gmtime(cut_ts)) if cut_ts else None, "venue_realized_pnl": bt.get("REALIZED_PNL"), "local_realized_pnl": l_real_row, "local_realized_whole_day": round(realised_by_day.get(d, 0.0), 4), "venue_funding": bt.get("FUNDING_FEE"), "local_funding": l_fund_row, "local_funding_whole_day": round(fund_by_day.get(d, 0.0), 4), "local_commission_after_row": -l_comm_after,
           "venue_commission_total": bt.get("COMMISSION"), "local_commission_usdt_equiv": -l_comm_usdt, "local_commission_native": {a: -v for a, v in l_comm.items()}, "bnb_close": BNB.get(d),
           "venue_commission_by_asset": v_comm or None, "local_commission_by_asset": {a: -v for a, v in l_comm.items()}, "nav": r.get("nav"), "prev_nav": r.get("prev_nav"), "unrealised": r.get("unrealised_pnl"), "flow": r.get("external_flow_usdt"), "realised_truncated": r.get("realised_truncated"),
           "flatten_events": sorted(set(time.strftime("%H:%MZ", time.gmtime(t)) for (dd, t) in FLAT if dd == d))}
    rec["d_commission_total"] = None if bt.get("COMMISSION") is None else round(rec["local_commission_usdt_equiv"] - float(bt["COMMISSION"]), 4)
    rec["d_realized"] = None if bt.get("REALIZED_PNL") is None else round(rec["local_realized_pnl"] - float(bt["REALIZED_PNL"]), 4)
    rec["d_funding"] = None if bt.get("FUNDING_FEE") is None else round(rec["local_funding"] - float(bt["FUNDING_FEE"]), 4)
    rec["d_commission_by_asset"] = ({a: round(rec["local_commission_by_asset"].get(a, 0.0) - v_comm.get(a, 0.0), 6) for a in set(v_comm) | set(rec["local_commission_by_asset"])} if v_comm else "venue by-asset breakdown not recorded this day")
    daily.append(rec)
# ── (5) true cost per anchor: fees from the deduped fills (USDT + BNB×close), slippage from orders (avg_fill_px vs mid_at_anchor) ──
# ★ orders.fee_all_usdt is a BOOLEAN ("every fee asset was USDT"), not an amount — the first version of this device summed it (E-0917-D)
fills_notional = sum(abs(float(r["fill_notional"])) for r in fills)
fa = collections.defaultdict(lambda: {"traded": 0.0, "fee": 0.0, "maker_notional": 0.0, "n_fills": 0, "day": None})
for r in fills:
    A = int(float(r["anchor_ts"]) // 14400 * 14400); x = fa[A]; fn = abs(float(r["fill_notional"])); x["traded"] += fn; x["fee"] += fee_usdt(r); x["n_fills"] += 1; x["day"] = day_of(r["fill_ts"])
    if r.get("venue_maker_flag") is True: x["maker_notional"] += fn
slip = collections.defaultdict(lambda: [0.0, 0.0])
for d in days:
    for r in rows(d, "orders"):
        fn = abs(float(r.get("filled_notional") or 0.0)); px = r.get("avg_fill_px"); mid = r.get("mid_at_anchor")
        if fn and px and mid:
            A = int(float(r["anchor_ts"]) // 14400 * 14400); side = 1.0 if float(r.get("intended_notional") or 0.0) > 0 else -1.0
            slip[A][0] += (float(px) - float(mid)) / float(mid) * side * fn; slip[A][1] += fn
cost = []
for A in sorted(fa):
    x = fa[A]; navd = nav_rows.get(x["day"], {}).get("nav"); sl = slip.get(A)
    cost.append({"anchor_ts": A, "day": x["day"], "traded_usdt": round(x["traded"], 2), "fee_usdt": round(x["fee"], 4), "fee_bps_of_traded": round(x["fee"] / x["traded"] * 1e4, 3) if x["traded"] else None,
                 "maker_share_notional": round(x["maker_notional"] / x["traded"], 4) if x["traded"] else None, "slippage_bps_vs_mid_at_anchor": round(sl[0] / sl[1] * 1e4, 3) if sl and sl[1] else None,
                 "turnover_frac_2nav": round(x["traded"] / (2 * navd), 4) if navd else None, "n_fills": x["n_fills"], "fee_per_2nav_bps": round(x["fee"] / (2 * navd) * 1e4, 4) if navd else None})
def wavg(key, w="traded_usdt", sub=None):
    cs = [c for c in (sub or cost) if c[key] is not None]; W = sum(c[w] for c in cs); return round(sum(c[key] * c[w] for c in cs) / W, 4) if W else None
era = {"BNB_era_0805_0906": [c for c in cost if "20260805" <= c["day"] <= "20260906"], "USDT_era_0907_": [c for c in cost if c["day"] >= "20260907"]}
cost_sum = {"anchors": len(cost), "traded_usdt_total": round(sum(c["traded_usdt"] for c in cost), 2), "fee_usdt_total": round(sum(c["fee_usdt"] for c in cost), 2),
            "fee_bps_of_traded_weighted": wavg("fee_bps_of_traded"), "maker_share_notional_weighted": wavg("maker_share_notional"), "slippage_bps_weighted": wavg("slippage_bps_vs_mid_at_anchor"),
            "turnover_frac_2nav_median": (lambda v: v[len(v) // 2] if v else None)(sorted(c["turnover_frac_2nav"] for c in cost if c["turnover_frac_2nav"] is not None)),
            "fee_per_anchor_bps_of_2nav_mean": round(sum(c["fee_per_2nav_bps"] for c in cost if c["fee_per_2nav_bps"] is not None) / max(1, sum(1 for c in cost if c["fee_per_2nav_bps"] is not None)), 4),
            "by_era": {k: {"anchors": len(v), "fee_bps_of_traded": wavg("fee_bps_of_traded", sub=v), "maker_share": wavg("maker_share_notional", sub=v), "slippage_bps": wavg("slippage_bps_vs_mid_at_anchor", sub=v), "turnover_median": (lambda z: z[len(z) // 2] if z else None)(sorted(c["turnover_frac_2nav"] for c in v if c["turnover_frac_2nav"] is not None))} for k, v in era.items()},
            "bnb_commission_native_total": round(sum(float(r.get("commission") or 0) for r in fills if r.get("commission_asset") == "BNB"), 6), "usdt_commission_total": round(sum(float(r.get("commission") or 0) for r in fills if r.get("commission_asset") == "USDT"), 4)}
pos_sum = {"anchors_checked": len(pos_checks), "anchors_with_mismatch": sum(1 for p in pos_checks if p["n_mismatch_gt_1usd"]), "usd_mismatch_total": round(sum(p["usd_mismatch"] for p in pos_checks), 2), "worst": max(pos_checks, key=lambda p: p["usd_mismatch"]) if pos_checks else None,
           "mismatch_anchors_with_flatten_in_bucket": sum(1 for p in pos_checks if p["n_mismatch_gt_1usd"] and p["flatten_in_bucket"]), "mismatch_anchors_single_name": sum(1 for p in pos_checks if p["n_mismatch_gt_1usd"] == 1),
           "usd_mismatch_flatten_buckets": round(sum(p["usd_mismatch"] for p in pos_checks if p["flatten_in_bucket"]), 2), "flatten_events": [time.strftime("%m-%d %H:%MZ", time.gmtime(t)) for (dd, t) in FLAT]}
# were a flatten's fills recorded? count deduped fills within [t-15min, t+5min] of each flatten read
flat_fills = []
for (dd, t) in FLAT:
    fr = [r for r in fills if t - 900 <= float(r["fill_ts"]) <= t + 300]; flat_fills.append({"event": time.strftime("%m-%d %H:%MZ", time.gmtime(t)), "fills_within_window": len(fr), "notional": round(sum(abs(float(r["fill_notional"])) for r in fr), 2), "order_types": sorted({str(r.get("order_type")) for r in fr})})
pos_sum["flatten_fills_recorded"] = flat_fills
day_sum = {"days": len(daily), "d_realized_abs_sum": round(sum(abs(x["d_realized"]) for x in daily if x["d_realized"] is not None), 2), "d_funding_abs_sum": round(sum(abs(x["d_funding"]) for x in daily if x["d_funding"] is not None), 2),
           "d_commission_total_abs_sum": round(sum(abs(x["d_commission_total"]) for x in daily if x["d_commission_total"] is not None), 4), "days_commission_total_off_gt_1usd": [(x["day"], x["d_commission_total"]) for x in daily if x["d_commission_total"] is not None and abs(x["d_commission_total"]) > 1],
           "days_with_venue_by_asset": sum(1 for x in daily if x["venue_commission_by_asset"]), "d_commission_by_asset_abs_sum": {a: round(sum(abs(x["d_commission_by_asset"].get(a, 0.0)) for x in daily if isinstance(x["d_commission_by_asset"], dict)), 6) for a in ("USDT", "BNB")},
           "days_realized_off_gt_2usd_with_flatten": [x["day"] for x in daily if x["d_realized"] is not None and abs(x["d_realized"]) > 2 and x["flatten_events"]], "days_realized_off_gt_2usd": [x["day"] for x in daily if x["d_realized"] is not None and abs(x["d_realized"]) > 2], "days_funding_off_gt_2usd": [x["day"] for x in daily if x["d_funding"] is not None and abs(x["d_funding"]) > 2]}
out = {"device": "fp3_cash_recon.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "days": [days[0], days[-1], len(days)], "inputs_sha16": inputs,
       "fills": {"raw_rows": n_raw, "distinct_trade_ids": len(by_tid), "notional_total": round(fills_notional, 2)}, "positions_vs_readback": pos_sum, "positions_per_anchor": pos_checks, "daily": daily, "daily_summary": day_sum, "cost_per_anchor": cost, "cost_summary": cost_sum}
json.dump(out, open(OUT, "w"), indent=1)
print("fills", out["fills"]); print("positions", pos_sum); print("daily", day_sum); print("cost", cost_sum)
