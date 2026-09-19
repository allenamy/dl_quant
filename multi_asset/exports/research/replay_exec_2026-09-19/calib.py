#!/usr/bin/env python3
"""replay_exec 2026-09-19 · CALIBRATION of the executor fill / fee / slippage model from the live ledger (anchors 2026-08-26 00Z
→ 2026-09-18 20Z), frozen into CALIBRATION_FROZEN_2026-09-19.json BEFORE any V1 number exists.

Population = the executor's own rows (mirror of pilot_log, read through the canonical collapsed fills reader). A "plan" is one
(rebalance_id, symbol) of a scheduled rebalance (rid "A<ts>"), whose FIRST maker leg is the attempt-1 maker row that is not the
requote leg (pre-09-05 the requote leg is the second attempt-1 row after a venue_reject; post-09-05 it carries requote_arm="requote").

Estimands (each reported with its sample size):
  1  maker first leg outcome: P(−5022 reject); among rested legs P(full ≥ 0.99) / P(zero) / P(partial) and the partial mean fill
     fraction (notional-weighted) — pooled (the sim parameter) and by placement arm (join / behind / exempt = reduce-only).
  2  requote leg outcome (same categories) and the requote-arm share among rejected first legs, before / after the requote
     experiment (first anchor whose rows carry requote_p, data-derived: 09-05 12Z).
  3  top-up (taker) legs: fill rate among ELIGIBLE legs (sent or abandoned; min-notional skips excluded — those are re-derived
     in the sim from the floors) by source (from_partial chase / chase_forced, from_reject) and the filled/intended ratio.
  4  fee rate per notional (USDT-equivalent; BNB at the BNBUSD 1m index nearest the fill) by fee era × maker flag, and by
     commission asset. The era switch is DATA-DERIVED (first 4h bucket from which every later bucket is USDT-majority; the
     brief's "09-07 08:25Z" is not what the fills show — the account's BNB ran out inside the 09-06 08:46Z flatten).
  5  fill price vs mid slippage (signed, adverse > 0, notional-weighted) by leg type, against mid_at_anchor (the sim's decision
     price) and against mid_at_submit (for the maker first leg and the top-up these two are the same number by construction:
     binance_executor 409ea16 L1096 sets mid_at_submit = mid_at_anchor and the top-up does not refresh it; the requote leg has a
     fresh mid).
  6  per-anchor executed turnover vs producer-target turnover (paired): exec = Σ|fill notional| of the rebalance legs of that
     anchor; producer-book turnover = sizing.gross × Σ|w_A/gn_A − w_{A−4h}/gn_{A−4h}|; executor-plan turnover = Σ|target − prev|
     over the executor's own first-leg rows (after withhold / reshape / clamp). A first draft compared exec with
     |producer target − executor position|, which mixes in the executor's persistent re-demeaning of the producer's net
     (≈6% per long name on 09-14) — not a turnover; replaced before any V1 number.
  7  min-notional skip rate: first legs skipped_min_notional among all planned first legs (count and |intended| share), and
     from_partial top-ups skipped for min-notional.
  8  timing (informational): first maker fill and top-up submit relative to the nominal anchor.
usage: calib.py <out.json> [mirror]
"""
import collections, hashlib, json, math, os, statistics, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L

# the requote experiment's first anchor is DATA-DERIVED: the first nominal anchor whose order rows carry requote_p (09-05 12Z;
# 12aa2a1 deployed 11:48:11Z — a first draft hard-coded 1789040880 = 09-10 12:28Z by an arithmetic slip, caught by the
# calibration-consistency check, fixed before any V1 number)
REBAL_OT = ("maker", "topup_taker")


def wmean(pairs):
    num = sum(v * w for v, w in pairs); den = sum(w for _, w in pairs)
    return (num / den if den else None), den


def cats(frs):
    """frs = [(fill_frac, intended_notional)] of rested legs -> category shares + partial mean fraction"""
    n = len(frs)
    full = [x for x in frs if x[0] >= 0.99]; zero = [x for x in frs if x[0] < 1e-9]; part = [x for x in frs if 1e-9 <= x[0] < 0.99]
    fbar, _ = wmean(part) if part else (None, 0)
    fnw, den = wmean(frs) if frs else (None, 0)
    return {"n": n, "p_full": len(full) / n if n else None, "p_zero": len(zero) / n if n else None,
            "p_part": len(part) / n if n else None, "fbar_part_notional_weighted": fbar,
            "nw_full": (sum(w for _, w in full) / den if den else None), "nw_zero": (sum(w for _, w in zero) / den if den else None),
            "nw_part": (sum(w for _, w in part) / den if den else None),
            "fill_frac_notional_weighted": fnw, "intended_notional_usdt": den,
            "notional_share_full": (sum(w for _, w in full) / den if den else None),
            "notional_share_zero": (sum(w for _, w in zero) / den if den else None)}


def main():
    out_p = sys.argv[1]
    M = L.Mirror(sys.argv[2] if len(sys.argv) > 2 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    assert not bad, f"mirror differs from INPUT_MANIFEST: {bad[:5]}"
    onom = M.orders_by_nominal()
    anchors = M.anchor_rows()
    RQ_FIRST_ANCHOR = min(k for k, v in onom.items() if not isinstance(k, tuple) and any(r.get("requote_p") is not None for r in v))
    A_set = [A for A in range(L.A_V1_FIRST, L.A_V1_LAST + 1, 14400)]

    # ── plans ──
    first_rows, rq_rows, rej_dir, topups, plan_rows = [], [], [], [], []
    per_anchor = {}
    n_min_first = n_first_planned = 0; notional_min_first = notional_first_planned = 0.0
    for A in A_set:
        od = onom.get(A, [])
        by = collections.defaultdict(list)
        for r in od:
            by[r["symbol"]].append(r)
        for s, v in by.items():
            m1 = [r for r in v if r["order_type"] == "maker" and int(r.get("attempt_idx") or 0) == 1]
            if not m1:
                continue
            if len(m1) == 1:
                first, rq = m1[0], None
            else:
                rej = [r for r in m1 if r["terminal_reason"] == "venue_reject" and r.get("requote_arm") in (None,)]
                first = rej[0] if rej else m1[0]
                others = [r for r in m1 if r is not first]
                rq = others[0] if others else None
            tr = first["terminal_reason"]
            if tr == "blocked_by_halt":
                continue
            inten = abs(float(first.get("intended_full") or first.get("intended_notional") or 0.0))
            n_first_planned += 1; notional_first_planned += inten
            if tr == "skipped_min_notional":
                n_min_first += 1; notional_min_first += inten
                continue
            if tr.startswith("skipped") or inten <= 0:
                continue
            m2 = [r for r in v if r["order_type"] == "maker" and int(r.get("attempt_idx") or 0) == 2]
            tps = [r for r in v if r["order_type"] == "topup_taker"]
            first_rows.append((A, s, first, rq, m2, tps, inten))
    # 1. first leg
    by_arm = collections.defaultdict(list); rej_n = collections.Counter(); rest_all = []; rej_w = 0.0; all_w = 0.0
    for A, s, f, rq, m2, tps, inten in first_rows:
        arm = f.get("placement_arm") or "none"
        all_w += inten
        if f["terminal_reason"] == "venue_reject":
            rej_n[arm] += 1; rej_n["ALL"] += 1; rej_w += inten
            continue
        fn = f.get("filled_notional")
        if fn is None:
            continue                                    # filled_amount_unknown: not a measurement (named in the receipt)
        fr = abs(float(fn)) / inten
        by_arm[arm].append((fr, inten)); rest_all.append((fr, inten))
    n_first = len(first_rows)
    first_leg = {"n_sent_first_legs": n_first, "n_rejected_5022": rej_n["ALL"], "p_rej": rej_n["ALL"] / n_first,
                 "p_rej_notional_weighted": rej_w / all_w, "intended_notional_usdt": all_w,
                 "rested": cats(rest_all),
                 "by_placement_arm": {a: {"n_rejected": rej_n[a], "p_rej": rej_n[a] / (rej_n[a] + len(by_arm[a])) if (rej_n[a] + len(by_arm[a])) else None,
                                          "rested": cats(by_arm[a])} for a in sorted(set(by_arm) | set(k for k in rej_n if k != "ALL"))},
                 "n_filled_amount_unknown_excluded": sum(1 for x in first_rows if x[2]["terminal_reason"] != "venue_reject" and x[2].get("filled_notional") is None)}
    # 2. requote leg
    pre, post = collections.Counter(), collections.Counter(); rq_rest = []; rq_rej = 0; rq_n = 0; rq_rej_w = 0.0; rq_all_w = 0.0
    for A, s, f, rq, m2, tps, inten in first_rows:
        if f["terminal_reason"] != "venue_reject":
            continue
        requoted = (rq is not None) or bool(m2)
        c = post if A >= RQ_FIRST_ANCHOR else pre
        c["rejected_first"] += 1; c["requoted"] += int(requoted)
        if not requoted:
            continue
        rq_n += 1; rq_all_w += inten
        if rq is None and m2:
            rq_rej += 1; rq_rej_w += inten; continue
        fn = rq.get("filled_notional")
        if fn is None:
            continue
        rq_rest.append((abs(float(fn)) / inten, inten))
    requote = {"n_requoted": rq_n, "n_rejected_again": rq_rej, "p_rej": rq_rej / rq_n if rq_n else None,
               "p_rej_notional_weighted": rq_rej_w / rq_all_w if rq_all_w else None, "rested": cats(rq_rest),
               "requote_share_before_experiment": {"n_rejected_first": pre["rejected_first"], "n_requoted": pre["requoted"],
                                                   "share": pre["requoted"] / pre["rejected_first"] if pre["rejected_first"] else None},
               "requote_share_under_experiment": {"n_rejected_first": post["rejected_first"], "n_requoted": post["requoted"],
                                                  "share": post["requoted"] / post["rejected_first"] if post["rejected_first"] else None,
                                                  "config_p_requote": 0.5}}
    # 3. top-ups
    tp = collections.defaultdict(lambda: collections.Counter()); tpn = collections.defaultdict(lambda: [0.0, 0.0])
    tpe = collections.defaultdict(lambda: [0.0, 0.0])            # [intended of filled legs, intended of eligible legs]
    for A, s, f, rq, m2, tps, inten in first_rows:
        for t in tps:
            src = t.get("topup_source"); arm = t.get("chase_arm") or "none"
            key = "from_reject" if src == "from_reject" else f"from_partial:{arm}"
            tr = t["terminal_reason"]
            tp[key][tr] += 1
            iw = abs(float(t.get("intended_residual") or t.get("intended_notional") or 0.0))
            if tr == "filled" or tr.startswith("abandoned"):
                tpe[key][1] += iw
                if tr == "filled":
                    tpe[key][0] += iw
            if tr == "filled" and t.get("filled_notional") is not None:
                tpn[key][0] += abs(float(t["filled_notional"])); tpn[key][1] += abs(float(t.get("intended_residual") or t.get("intended_notional") or 0.0))
    topup = {}
    for k, c in sorted(tp.items()):
        elig = c["filled"] + sum(v for kk, v in c.items() if kk.startswith("abandoned"))
        topup[k] = {"terminal_counts": dict(c), "n_eligible_sent_or_abandoned": elig,
                    "fill_rate_among_eligible": (c["filled"] / elig if elig else None),
                    "fill_rate_among_eligible_notional_weighted": (tpe[k][0] / tpe[k][1] if tpe[k][1] else None),
                    "eligible_intended_notional_usdt": tpe[k][1],
                    "filled_over_intended_notional": (tpn[k][0] / tpn[k][1] if tpn[k][1] else None)}
    chase_elig = sum(tpe[k][1] for k in ("from_partial:chase", "from_partial:chase_forced"))
    chase_fill = sum(tpe[k][0] for k in ("from_partial:chase", "from_partial:chase_forced"))
    rej_elig = tpe["from_reject"][1]
    rej_fill = tpe["from_reject"][0]
    # 7b. from_partial top-ups skipped for min notional
    n_fp = sum(sum(c.values()) for k, c in tp.items() if k.startswith("from_partial"))
    n_fp_min = sum(c.get("skipped_min_notional", 0) for k, c in tp.items() if k.startswith("from_partial"))

    # ── 4. fees + 5. slippage from fills / rows ──
    W, _ = L.live_windows()
    t_lo, t_hi = W[0]["t0"], W[141]["t1"]
    trades = L.all_trades(M, t_lo, t_hi)
    bnb = L.BnbIndex()
    # fee-asset era, DATA-DERIVED (not the date in the brief): per 4h bucket the share of fills paying commission in USDT; the
    # switch = the first bucket from which EVERY later bucket is USDT-majority (the account's BNB ran out during the 09-06 flatten).
    bk = collections.defaultdict(collections.Counter)
    for x in trades:
        if x["fee_asset"] in ("BNB", "USDT"):
            bk[int(x["ts"]) // 14400 * 14400][x["fee_asset"]] += 1
    keys = sorted(bk); switch = None
    for i, k in enumerate(keys):
        if all(bk[j]["USDT"] > bk[j]["BNB"] for j in keys[i:]):
            switch = k; break
    first_usdt_in_switch = min((x["ts"] for x in trades if x["fee_asset"] == "USDT" and x["ts"] >= (switch or 0)), default=None)
    last_bnb = first_usdt_in_switch
    first_usdt_after = first_usdt_in_switch
    fee = collections.defaultdict(lambda: [0.0, 0.0, 0]); fee_asset = collections.defaultdict(lambda: [0.0, 0.0, 0]); bnb_lag = []
    for x in trades:
        if x["fee"] is None or x["maker"] is None:
            continue
        f = float(x["fee"])
        if x["fee_asset"] == "BNB":
            p, lag = bnb.at(x["ts"]); f *= p; bnb_lag.append(lag)
        elif x["fee_asset"] != "USDT":
            continue
        era = "BNB_era" if (switch is not None and x["ts"] < first_usdt_in_switch) else "USDT_era"
        k = (era, "maker" if x["maker"] else "taker")
        fee[k][0] += f; fee[k][1] += abs(x["sn"]); fee[k][2] += 1
        ka = (x["fee_asset"], "maker" if x["maker"] else "taker")
        fee_asset[ka][0] += f; fee_asset[ka][1] += abs(x["sn"]); fee_asset[ka][2] += 1
    fees = {f"{e}|{m}": {"rate": v[0] / v[1], "rate_bps": v[0] / v[1] * 1e4, "n_fills": v[2], "notional_usdt": v[1], "fee_usdt_eq": v[0]}
            for (e, m), v in sorted(fee.items())}
    fees_by_asset = {f"{a}|{m}": {"rate_bps": v[0] / v[1] * 1e4, "n_fills": v[2], "notional_usdt": v[1]} for (a, m), v in sorted(fee_asset.items())}
    slip = collections.defaultdict(lambda: {"anchor": [], "submit": []})
    for A, s, f, rq, m2, tps, inten in first_rows:
        legs = [("maker_first", f)] + ([("maker_requote", rq)] if rq is not None else []) + \
               [("taker_from_reject" if t.get("topup_source") == "from_reject" else "taker_from_partial", t) for t in tps]
        for kind, r in legs:
            fn, px = r.get("filled_notional"), r.get("avg_fill_px")
            if not fn or not px or abs(float(fn)) <= 0:
                continue
            sg = 1.0 if str(r.get("side")).lower() == "buy" else (-1.0 if str(r.get("side")).lower() == "sell" else (1.0 if float(fn) > 0 else -1.0))
            w = abs(float(fn))
            if r.get("mid_at_anchor"):
                slip[kind]["anchor"].append((sg * (float(px) / float(r["mid_at_anchor"]) - 1.0), w))
            if r.get("mid_at_submit"):
                slip[kind]["submit"].append((sg * (float(px) / float(r["mid_at_submit"]) - 1.0), w))
    for rid_key, od in onom.items():
        if not (isinstance(rid_key, tuple) and rid_key[0] == "FLATTEN"):
            continue
        for r in od:
            if r["order_type"] != "protective_flatten" or not r.get("filled_notional") or not r.get("avg_fill_px") or not r.get("mid_at_submit"):
                continue
            if not (t_lo <= float(r.get("submit_ts") or 0) <= t_hi):
                continue
            sg = 1.0 if str(r.get("side")).lower() == "buy" else -1.0
            slip["protective_flatten"]["submit"].append((sg * (float(r["avg_fill_px"]) / float(r["mid_at_submit"]) - 1.0), abs(float(r["filled_notional"]))))
    slippage = {}
    for k, d in sorted(slip.items()):
        slippage[k] = {}
        for ref in ("anchor", "submit"):
            if d[ref]:
                m, den = wmean(d[ref])
                slippage[k][f"vs_mid_at_{ref}"] = {"bps_notional_weighted": m * 1e4, "n_legs": len(d[ref]), "notional_usdt": den,
                                                   "bps_median": statistics.median(v for v, _ in d[ref]) * 1e4}

    # ── 6. paired per-anchor turnover ──
    exec_by_rid = collections.defaultdict(float); mk_by_rid = collections.defaultdict(float)
    for x in trades:
        if x["order_type"] in REBAL_OT and x.get("rid") and str(x["rid"]).startswith("A"):
            exec_by_rid[str(x["rid"])] += abs(x["sn"])
            if x["order_type"] == "maker":
                mk_by_rid[str(x["rid"])] += abs(x["sn"])
    paired = []
    prev_book = None
    for A in A_set:
        pa = M.phase_a_trade(A); an = anchors.get(A); od = onom.get(A, [])
        tgt = json.load(open(M.target_path(A))) if os.path.exists(M.target_path(A)) else None
        book = ({s: float(w) / float(tgt["gross_norm"]) for s, w in tgt["weights"].items()} if tgt else None)
        pb, prev_book = prev_book, book
        if not pa or not an or not od or book is None:
            continue
        rid = pa.get("rebalance_id")
        if any(r["terminal_reason"] == "blocked_by_halt" for r in od):
            continue
        G = float((pa.get("sizing") or {}).get("gross") or 0.0)
        Tg = float(an.get("target_gross") or 0.0)
        first = {}
        for r in sorted(od, key=lambda r: (r["symbol"], r["terminal_reason"] != "venue_reject")):
            if r["order_type"] == "maker" and int(r.get("attempt_idx") or 0) == 1:
                first.setdefault(r["symbol"], r)
        plan_turn = sum(abs(float(r.get("intended_full") or r.get("intended_notional") or 0.0)) for r in first.values()
                        if not str(r["terminal_reason"]).startswith("skipped") and r["terminal_reason"] != "blocked_by_halt")
        prod_turn = (G * sum(abs(book.get(s, 0.0) - pb.get(s, 0.0)) for s in set(book) | set(pb)) if pb is not None else None)
        ex = exec_by_rid.get(rid, 0.0)
        paired.append({"anchor": A, "utc": L.UA(A), "rid": rid, "sizing_gross": G,
                       "producer_book_turnover_usdt": prod_turn, "executor_plan_turnover_usdt": plan_turn, "exec_turnover_usdt": ex,
                       "exec_over_producer": (ex / prod_turn if prod_turn else None), "exec_over_plan": (ex / plan_turn if plan_turn > 0 else None),
                       "taker_share": ((ex - mk_by_rid.get(rid, 0.0)) / ex if ex > 0 else None)})
    def _dist(key):
        v = sorted(p[key] for p in paired if p[key] is not None)
        return {"n": len(v), "median": statistics.median(v), "p10": v[len(v) // 10], "p90": v[(9 * len(v)) // 10]}
    pp = [p for p in paired if p["producer_book_turnover_usdt"] is not None]
    turnover = {"definitions": {"producer_book_turnover": "sizing.gross × Σ_s |w_A/gn_A − w_{A−4h}/gn_{A−4h}| (the producer's own book change, executor-state free; paired only when both books exist)",
                                "executor_plan_turnover": "Σ |intended_full| over SENT first maker legs (after withhold / reshape / clamp / min-notional / lot rounding) — the same population as the sim's plan_turnover",
                                "exec_turnover": "Σ |fill notional| of this rid's maker + top-up fills (collapsed ledger)"},
                "n_anchors_paired": len(paired), "n_anchors_with_producer_pair": len(pp),
                "sum_exec_over_sum_producer": sum(p["exec_turnover_usdt"] for p in pp) / sum(p["producer_book_turnover_usdt"] for p in pp),
                "sum_exec_over_sum_plan": sum(p["exec_turnover_usdt"] for p in paired) / sum(p["executor_plan_turnover_usdt"] for p in paired),
                "exec_over_producer_per_anchor": _dist("exec_over_producer"), "exec_over_plan_per_anchor": _dist("exec_over_plan"),
                "taker_share_of_exec_notional": sum(p["exec_turnover_usdt"] * (p["taker_share"] or 0) for p in paired) / sum(p["exec_turnover_usdt"] for p in paired),
                "taker_share_per_anchor": _dist("taker_share"),
                "per_anchor": paired}
    # ── 8. timing ──
    mk_dt, tk_dt = [], []
    for A, s, f, rq, m2, tps, inten in first_rows:
        if f.get("first_fill_ts"):
            mk_dt.append(float(f["first_fill_ts"]) - A)
        for t in tps:
            if t["terminal_reason"] == "filled" and t.get("submit_ts"):
                tk_dt.append(float(t["submit_ts"]) - A)
    timing = {"maker_first_fill_s_after_nominal": {"median": statistics.median(mk_dt), "n": len(mk_dt)},
              "taker_submit_s_after_nominal": {"median": statistics.median(tk_dt), "n": len(tk_dt)}}

    # ── frozen simulator parameters ──
    fl = first_leg["rested"]; rqr = requote["rested"]
    params = {
        "maker_first": {"p_rej": first_leg["p_rej_notional_weighted"], "p_full": fl["nw_full"], "p_zero": fl["nw_zero"], "p_part": fl["nw_part"],
                        "fbar_part": fl["fbar_part_notional_weighted"]},
        "maker_requote": {"p_rej": requote["p_rej_notional_weighted"], "p_full": rqr["nw_full"], "p_zero": rqr["nw_zero"], "p_part": rqr["nw_part"],
                          "fbar_part": rqr["fbar_part_notional_weighted"]},
        "share_weighting": ("NOTIONAL-weighted (v2). v1 used COUNT shares; the in-sample consistency check (sim executed / planned "
                            "0.917 vs live 0.863) showed larger orders zero-fill and get rejected more often (notional share zero 0.142 "
                            "vs count 0.110), so count shares over-execute an aggregate. Changed before any V1 number."),
        "requote_p_timeline": [{"from_anchor": 0, "p": requote["requote_share_before_experiment"]["share"], "mode": "expected_mix",
                                "why": "before the experiment: the MEASURED share of -5022 first legs that were requoted (n in 2_requote_leg), applied as an expected-value mix"},
                               {"from_anchor": RQ_FIRST_ANCHOR, "p": 0.5, "mode": "executor_hash",
                                "why": "config requote_experiment.p_requote = 0.5 (12aa2a1, deployed 09-05 11:48:11Z); first anchor with requote_p on its rows = %s; arm = requote_experiment.assign(rid, sym, p)" % L.UA(RQ_FIRST_ANCHOR)}],
        "taker_fill_rate": {"from_partial_chase": topup["from_partial:chase"]["fill_rate_among_eligible_notional_weighted"],
                            "from_partial_chase_forced": topup["from_partial:chase_forced"]["fill_rate_among_eligible_notional_weighted"],
                            "from_reject": rej_fill / rej_elig if rej_elig else None,
                            "weighting": "notional-weighted among eligible legs (sent or abandoned); chase_forced (C's size-selected fill set) is abandoned far more often than the randomised chase arm, so the two are separate parameters"},
        "fee_rate": {"switch_ts": first_usdt_in_switch, "switch_utc": L.U(first_usdt_in_switch) if first_usdt_in_switch else None,
                     "BNB_era": {"maker": fees.get("BNB_era|maker", {}).get("rate"), "taker": fees.get("BNB_era|taker", {}).get("rate")},
                     "USDT_era": {"maker": fees.get("USDT_era|maker", {}).get("rate"), "taker": fees.get("USDT_era|taker", {}).get("rate")}},
        "slippage_vs_mid_at_anchor": {k: slippage[k]["vs_mid_at_anchor"]["bps_notional_weighted"] / 1e4
                                      for k in ("maker_first", "maker_requote", "taker_from_partial", "taker_from_reject") if k in slippage},
        "slippage_flatten_vs_mid_at_submit": slippage.get("protective_flatten", {}).get("vs_mid_at_submit", {}).get("bps_notional_weighted", 0.0) / 1e4,
        "decision_boundary_offset_s": 1500, "decision_offset_why": "executor reads target_live at N+24:00 and captures mid_at_anchor then; the 5-minute panel boundary containing that instant is N+25:00",
        "stop_eval_offset_s": 2400, "stop_eval_why": "phase C / daily_nav / position readback at ~N+40",
        "rule_flatten_offset_s": 2760, "rule_flatten_why": "§4-2 trip is judged on the N+40 NAV row; the live 09-06 trip flattened at 08:46:08Z (N+46)",
        "hash_free": "expected-value fill model: no random draws; the only deterministic hashes are the executor's own (chase_policy.assign_arms, requote_experiment.assign)",
    }
    doc = {"device": "calib.py", "device_sha256": L.sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": f"/usr/bin/python3 {os.path.relpath(os.path.abspath(__file__), L.REPO)} {os.path.relpath(os.path.abspath(out_p), L.REPO)} {M.root}",
           "window": {"anchors": f"{L.UA(L.A_V1_FIRST)} .. {L.UA(L.A_V1_LAST)}", "trades": f"{L.U(t_lo)} .. {L.U(t_hi)}"},
           "inputs_sha256": L.input_shas(M), "mirror_manifest_verified": True, "frozen_before_v1": True,
           "calibration": {"1_maker_first_leg": first_leg, "2_requote_leg": requote, "3_topup": topup,
                           "4_fee_rate": {"by_era_and_maker_flag": fees, "by_commission_asset": fees_by_asset,
                                          "bnb_price": "BNBUSD 1m index close nearest the fill (INDEX_KLINES_1m_OHLC_cache); lag median s = %.0f, max s = %.0f" % (statistics.median(bnb_lag) if bnb_lag else -1, max(bnb_lag) if bnb_lag else -1),
                                          "era_switch": {"rule": "first 4h bucket from which every later bucket has more USDT- than BNB-commission fills; switch instant = first USDT fill in it",
                                                         "switch_utc": L.U(first_usdt_in_switch) if first_usdt_in_switch else None,
                                                         "per_bucket_counts": {L.UA(k): dict(bk[k]) for k in keys}}},
                           "5_slippage": slippage, "6_turnover_paired": turnover,
                           "7_min_notional": {"first_legs_planned": n_first_planned, "first_legs_skipped_min_notional": n_min_first,
                                              "skip_rate_count": n_min_first / n_first_planned, "skip_rate_intended_notional": notional_min_first / notional_first_planned,
                                              "from_partial_topups": n_fp, "from_partial_topups_skipped_min_notional": n_fp_min,
                                              "from_partial_skip_rate_count": n_fp_min / n_fp if n_fp else None},
                           "8_timing": timing},
           "params": params}
    with open(out_p + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)
    print(json.dumps(params, indent=1, default=str))
    print(json.dumps({"first_leg": {k: v for k, v in first_leg.items() if k != "by_placement_arm"}, "turnover": {k: v for k, v in turnover.items() if k != "per_anchor"},
                      "fees": fees, "slippage": slippage, "min_notional": doc["calibration"]["7_min_notional"], "timing": timing}, indent=1, default=str))


if __name__ == "__main__":
    main()
