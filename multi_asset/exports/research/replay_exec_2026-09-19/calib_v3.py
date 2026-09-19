#!/usr/bin/env python3
"""replay_exec 2026-09-19 · v3 POOLED calibration of the executor fill / timing / slippage / fee model — anchors 08-26 00Z .. 09-10 20Z
ONLY (v1b_gate.CALIB_ANCHORS), frozen into CALIBRATION_v3_POOLED_20260826_20260910.json BEFORE any hold-out number exists.

BLIND PROTOCOL (CFG-04 chase arms, CFG-06 placement / requote arms, binding): every outcome parameter here is POOLED across all
experiment arms. The order rows are SANITISED on read — every key naming an arm or experiment (`*arm*`, `*chase*`, `*requote*`,
`*placement*`) is deleted before any row is used — so no quantity in this file can be grouped by arm, and the output is asserted
to carry no such key. Nothing per arm is computed, printed or written.

Population: a PLAN = one (rebalance_id, symbol) of a scheduled rebalance whose rid anchor lies in the calibration anchors and
whose first maker leg was sent (not blocked_by_halt, not skipped). FIRST LEG = the earliest-submitted attempt-1 maker row. Fill
amounts come from the collapsed fills ledger (fills_reader): if the first leg was not refused (−5022), every maker fill of the
plan is a first-leg fill (a requote leg only exists after a refusal; attempt-2 maker rows carry no fills); if it was refused,
its maker fills are the later (requote) leg. Top-up (taker) fills are later legs.

Estimands (all notional-weighted, each with its sample size):
  first_leg     P(refused) ; among rested legs the shares full (fill ≥ 0.99) / zero / partial and the partial mean fraction
  completion    residual after the first leg = intended − first-leg fill; ELIGIBLE iff residual ≥ the symbol's venue floor (the
                executor's own rule; the sim applies it on the rounded residual). π = Σ later-leg fills / Σ eligible residual over
                ALL eligible plans (refused and rested residuals together, every arm together); μ = maker share of those fills.
  timing        fill instant − decision instant (the rid timestamp = when the executor read the target: N+23:00 before 08-27
                08Z, N+24:00 after): notional-weighted quantiles 0.1/0.3/0.5/0.7/0.9 of first-leg fills and of later-leg fills;
                protective flatten fills relative to their event's first fill.
  slippage      side × (avg fill px / the executor's OWN recorded mid − 1), adverse > 0, weighted by |filled notional|, over
                order rows: rebalance legs against mid_at_anchor (the true venue mid at the decision instant) — first legs, and
                later legs pooled (maker requote + taker top-up, every arm together); protective flatten rows against
                mid_at_submit. The simulator applies them to ITS proxy of that mid (the panel chain at the last complete bar at or
                before the decision / the flatten start), so a level error of the chain cancels inside the sim.
                ★ A first draft (same session, before any simulator number) referenced the panel chain at the fill's own bar.
                The chain carries LEVEL errors — rolling.npz itself holds 15 bars clipped at exactly ±0.30 (BULLAUSDT 09-05 03:00
                leaves the chain 17% low for the rest of the window; chain / executor-mid deviation over 37,287 anchor mids: p50
                0.15%, p99 6.2%, max 60%) — and a handful of such names (BULLA, TAC, VELVET) dominated the pooled means (flatten
                −18.0 bps mean vs +1.7 bps median). Replaced by the executor-mid reference.
  fees          |commission| (BNB at the BNBUSD 1m index) / |notional| by fee era × maker flag; era switch data-derived (the
                first 4h bucket from which every later bucket is USDT-commission majority) — same rule as calib.py.
Trades used for fees / flatten: fill time in [08-26 00:00Z, 09-11 00:00Z) (the 09-11 00Z decision is at 00:24Z, so no hold-out
anchor's fill is inside). usage: calib_v3.py <out.json> [mirror]
"""
import collections, json, math, os, statistics, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1b_gate as G

QS = (0.1, 0.3, 0.5, 0.7, 0.9)
BLIND_KEY_PARTS = ("arm", "chase", "requote", "placement")


def sanitise(r):
    """drop every experiment / arm key before the row is used (blind protocol)"""
    return {k: v for k, v in r.items() if not any(p in k.lower() for p in BLIND_KEY_PARTS)}


def blind_violations(obj, path=""):
    """keys anywhere in a JSON-like object that name an arm / experiment (must be empty for a v3 pooled calibration)"""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(p in str(k).lower() for p in BLIND_KEY_PARTS):
                out.append(path + "/" + str(k))
            out += blind_violations(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += blind_violations(v, f"{path}[{i}]")
    return out


def wquant(vals, wts, qs=QS):
    o = np.argsort(vals); v = np.asarray(vals, float)[o]; w = np.asarray(wts, float)[o]
    c = np.cumsum(w) / w.sum()
    return [float(v[min(len(v) - 1, int(np.searchsorted(c, q)))]) for q in qs]


def wmean(pairs):
    num = sum(v * w for v, w in pairs); den = sum(w for _, w in pairs)
    return (num / den if den else None), den


def main():
    out_p = sys.argv[1]
    M = L.Mirror(sys.argv[2] if len(sys.argv) > 2 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    bad = M.verify_manifest()
    assert not bad, f"mirror differs from INPUT_MANIFEST: {bad[:5]}"
    A_LO, A_HI = G.CALIB_ANCHORS
    T_LO, T_HI = float(A_LO), float(A_HI + 14400)          # [08-26 00:00Z, 09-11 00:00Z)
    filt = M.exchange_filters()
    floor = lambda s: float((filt.get(s) or {}).get("min_notional", 5.0) or 5.0)

    # ── plans from the executor's own order rows (sanitised) ──
    rows = collections.defaultdict(list)
    for r in M.range_rows("orders"):
        rid = str(r.get("rebalance_id") or "")
        if rid.startswith("A") and A_LO <= L.nominal(float(rid[1:])) <= A_HI:
            rows[(rid, r["symbol"])].append(sanitise(r))
    fills = collections.defaultdict(list)
    for f in M.fills():
        rid = str(f.get("rebalance_id") or "")
        if rid.startswith("A") and A_LO <= L.nominal(float(rid[1:])) <= A_HI:
            fills[(rid, f["symbol"])].append(sanitise(f))
    n_sk = collections.Counter(); plans = []
    for (rid, s), v in rows.items():
        m1 = sorted([r for r in v if r["order_type"] == "maker" and int(r.get("attempt_idx") or 0) == 1], key=lambda r: float(r.get("submit_ts") or 0.0))
        if not m1:
            continue
        first = m1[0]; tr = first["terminal_reason"]
        if tr == "blocked_by_halt":
            n_sk["blocked_by_halt"] += 1; continue
        if str(tr).startswith("skipped"):
            n_sk[tr] += 1; continue
        inten = abs(float(first.get("intended_full") or first.get("intended_notional") or 0.0))
        if inten <= 0:
            n_sk["no_intended"] += 1; continue
        refused = tr == "venue_reject"
        fl = fills.get((rid, s), [])
        mk = [f for f in fl if f.get("order_type") == "maker"]
        tk = [f for f in fl if f.get("order_type") == "topup_taker"]
        mk_n = sum(abs(float(f["fill_notional"])) for f in mk); tk_n = sum(abs(float(f["fill_notional"])) for f in tk)
        first_fill = 0.0 if refused else mk_n
        row_fill = first.get("filled_notional")
        plans.append({"rid": rid, "t_dec": float(rid[1:]), "sym": s, "inten": inten, "refused": refused, "first_fill": first_fill,
                      "first_row_fill": (abs(float(row_fill)) if row_fill is not None else None),
                      "later_maker": (mk_n if refused else 0.0), "later_taker": tk_n,
                      "first_fills": ([] if refused else mk), "later_fills": ((mk if refused else []) + tk)})
    # consistency of the fills-ledger first-leg amount with the executor's own row (rested legs with a known row amount)
    cons = [abs(p["first_fill"] - p["first_row_fill"]) / p["inten"] for p in plans if not p["refused"] and p["first_row_fill"] is not None]

    # ── first leg (pooled) ──
    all_w = sum(p["inten"] for p in plans); rej_w = sum(p["inten"] for p in plans if p["refused"])
    rest = [(min(1.0, p["first_fill"] / p["inten"]), p["inten"]) for p in plans if not p["refused"]]
    den = sum(w for _, w in rest)
    full = [x for x in rest if x[0] >= 0.99]; zero = [x for x in rest if x[0] < 1e-9]; part = [x for x in rest if 1e-9 <= x[0] < 0.99]
    fbar, _ = wmean(part)
    first_leg = {"n_plans": len(plans), "n_refused": sum(p["refused"] for p in plans), "intended_notional_usdt": all_w,
                 "p_rej": rej_w / all_w, "n_rested": len(rest), "p_full": sum(w for _, w in full) / den, "p_zero": sum(w for _, w in zero) / den,
                 "p_part": sum(w for _, w in part) / den, "fbar_part": fbar, "n_partial": len(part),
                 "fills_ledger_vs_row_rel_diff": {"n": len(cons), "median": statistics.median(cons) if cons else None,
                                                  "p99": float(np.percentile(cons, 99)) if cons else None}}
    # ── completion (pooled over refused + rested residuals and over every arm) ──
    el_res = el_fill = el_mk = 0.0; n_el = 0; inel_fill = 0.0; n_inel_fill = 0
    for p in plans:
        res = max(0.0, p["inten"] - p["first_fill"])
        later = p["later_maker"] + p["later_taker"]
        if res >= floor(p["sym"]):
            n_el += 1; el_res += res; el_fill += later; el_mk += p["later_maker"]
        elif later > 0:
            n_inel_fill += 1; inel_fill += later
    completion = {"n_eligible_plans": n_el, "eligible_residual_usdt": el_res, "later_fill_usdt": el_fill,
                  "pi_fill": el_fill / el_res, "maker_share": el_mk / el_fill if el_fill else 0.0,
                  "n_ineligible_with_later_fill": n_inel_fill, "ineligible_later_fill_usdt": inel_fill}

    # ── timing (fills ledger, relative to the decision instant) ──
    tim = {"first": ([], []), "later": ([], [])}
    for p in plans:
        for k in ("first", "later"):
            for f in p[k + "_fills"]:
                tim[k][0].append(float(f["fill_ts"]) - p["t_dec"]); tim[k][1].append(abs(float(f["fill_notional"])))
    trades = L.all_trades(M, T_LO, T_HI - 1e-6)
    fl_tr = [x for x in trades if x["order_type"] == "protective_flatten"]
    starts = []
    for x in fl_tr:
        if not starts or x["ts"] - starts[-1] > 3600:
            starts.append(x["ts"])
    fl_off, fl_w = [], []
    for x in fl_tr:
        st = max(t for t in starts if t <= x["ts"])
        fl_off.append(x["ts"] - st); fl_w.append(abs(x["sn"]))
    timing = {"quantiles": list(QS),
              "first_leg_fill_offset_s": wquant(*tim["first"]), "later_leg_fill_offset_s": wquant(*tim["later"]),
              "flatten_fill_offset_s": wquant(fl_off, fl_w),
              "n_fills": {"first": len(tim["first"][0]), "later": len(tim["later"][0]), "flatten": len(fl_off)},
              "flatten_events": [L.U(t) for t in starts],
              "min_first_leg_offset_s": float(min(tim["first"][0]))}
    # ── slippage vs the executor's own recorded mid (order rows) ──
    def row_slip(r, ref_key):
        fn, px, mid = r.get("filled_notional"), r.get("avg_fill_px"), r.get(ref_key)
        if not fn or not px or not mid or abs(float(fn)) <= 0 or float(mid) <= 0:
            return None
        sd = str(r.get("side")).lower()
        sg = 1.0 if sd == "buy" else (-1.0 if sd == "sell" else (1.0 if float(fn) > 0 else -1.0))
        return (sg * (float(px) / float(mid) - 1.0), abs(float(fn)))
    sl = {"first": [], "later": [], "flatten": []}; n_miss = collections.Counter()
    for (rid, s), v in rows.items():
        m1 = sorted([r for r in v if r["order_type"] == "maker" and int(r.get("attempt_idx") or 0) == 1], key=lambda r: float(r.get("submit_ts") or 0.0))
        if not m1 or m1[0]["terminal_reason"] == "blocked_by_halt" or str(m1[0]["terminal_reason"]).startswith("skipped"):
            continue
        for r in v:
            if r["order_type"] not in ("maker", "topup_taker") or not r.get("filled_notional"):
                continue
            k = "first" if r is m1[0] else "later"
            x = row_slip(r, "mid_at_anchor")
            if x is None:
                n_miss[k] += 1
            else:
                sl[k].append(x)
    fl_events = set()
    for key, v in M.orders_by_nominal().items():
        if not (isinstance(key, tuple) and key[0] == "FLATTEN"):
            continue
        for r in v:
            r = sanitise(r)
            if r["order_type"] != "protective_flatten" or not (T_LO <= float(r.get("submit_ts") or 0.0) < T_HI):
                continue
            x = row_slip(r, "mid_at_submit")
            if x is None:
                n_miss["flatten"] += 1
            else:
                sl["flatten"].append(x); fl_events.add(key[1])
    slippage = {}
    for k, name in (("first", "first_leg"), ("later", "later_leg"), ("flatten", "flatten")):
        m, den2 = wmean(sl[k])
        slippage[name] = {"frac_notional_weighted": m, "bps_notional_weighted": m * 1e4, "n_rows": len(sl[k]), "notional_usdt": den2,
                          "bps_median": statistics.median(x for x, _ in sl[k]) * 1e4,
                          "reference": ("mid_at_submit" if k == "flatten" else "mid_at_anchor")}
    slippage["flatten"]["events_with_priced_rows"] = sorted(fl_events)
    slippage["n_filled_rows_without_reference"] = dict(n_miss)

    # ── fees by era × maker flag (same rule as calib.py) ──
    bnb = L.BnbIndex()
    bk = collections.defaultdict(collections.Counter)
    for x in trades:
        if x["fee_asset"] in ("BNB", "USDT"):
            bk[int(x["ts"]) // 14400 * 14400][x["fee_asset"]] += 1
    keys = sorted(bk); switch = None
    for i, k in enumerate(keys):
        if all(bk[j]["USDT"] > bk[j]["BNB"] for j in keys[i:]):
            switch = k; break
    sw_ts = min(x["ts"] for x in trades if x["fee_asset"] == "USDT" and x["ts"] >= switch)
    fee = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for x in trades:
        if x["fee"] is None or x["maker"] is None or x["fee_asset"] not in ("BNB", "USDT"):
            continue
        f = abs(float(x["fee"])) * (bnb.at(x["ts"])[0] if x["fee_asset"] == "BNB" else 1.0)
        era = "BNB_era" if x["ts"] < sw_ts else "USDT_era"
        k = (era, "maker" if x["maker"] else "taker")
        fee[k][0] += f; fee[k][1] += abs(x["sn"]); fee[k][2] += 1
    fees = {f"{e}|{m}": {"rate": v[0] / v[1], "rate_bps": v[0] / v[1] * 1e4, "n_fills": v[2], "notional_usdt": v[1]} for (e, m), v in sorted(fee.items())}

    params = {
        "first_leg": {k: first_leg[k] for k in ("p_rej", "p_full", "p_zero", "p_part", "fbar_part")},
        "completion": {"pi_fill": completion["pi_fill"], "maker_share": completion["maker_share"]},
        "timing_offsets_after_decision_s": {"first_leg": timing["first_leg_fill_offset_s"], "later_leg": timing["later_leg_fill_offset_s"],
                                            "weights": [0.2] * len(QS)},
        "timing_offsets_after_flatten_start_s": {"flatten": timing["flatten_fill_offset_s"], "weights": [0.2] * len(QS)},
        "slippage_vs_executor_mid": {"first_leg": slippage["first_leg"]["frac_notional_weighted"],
                                      "later_leg": slippage["later_leg"]["frac_notional_weighted"],
                                      "flatten": slippage["flatten"]["frac_notional_weighted"]},
        "fee_rate": {"switch_ts": sw_ts, "switch_utc": L.U(sw_ts),
                     "BNB_era": {"maker": fees["BNB_era|maker"]["rate"], "taker": fees["BNB_era|taker"]["rate"]},
                     "USDT_era": {"maker": fees["USDT_era|maker"]["rate"], "taker": fees["USDT_era|taker"]["rate"]}},
        "decision_offset_default_s": 1440, "decision_offset_why": "config/book.json external_book.anchor_offset_min = 24 (N+23 before 08-27 08Z); the sim uses the executor's recorded rid timestamp where one exists",
        "eval_offset_without_frame_s": 2700, "eval_why": "per-name stop / §4-2 are judged on the post-run readback; with the live frame that is the window's t0 readback, without it N+45 (after the pooled later-leg timing)",
        "rule_flatten_offset_s": 2760, "rule_flatten_why": "the live 09-06 §4-2 trip flattened at 08:46:08Z (N+46)",
    }
    doc = {"device": "calib_v3.py", "device_sha256": L.sha_file(os.path.abspath(__file__)), "kind": "v3_pooled",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": f"/usr/bin/python3 {os.path.relpath(os.path.abspath(__file__), L.REPO)} {os.path.relpath(os.path.abspath(out_p), L.REPO)} {M.root}",
           "calibration_anchors": list(G.CALIB_ANCHORS), "calibration_anchors_utc": [L.UA(a) for a in G.CALIB_ANCHORS],
           "trade_time_range_utc": [L.U(T_LO), L.U(T_HI)], "frozen_before_holdout": True,
           "blind_protocol": "outcome parameters pooled across every CFG-04 / CFG-06 arm; order and fill rows sanitised (keys naming arm / chase / requote / placement deleted on read); no per-arm quantity computed or written",
           "inputs_sha256": L.input_shas(M), "mirror_manifest_verified": True,
           "estimands": {"first_leg": first_leg, "completion": completion, "timing": timing, "slippage": slippage, "fees": fees,
                         "plans_skipped": dict(n_sk)},
           "params": params}
    viol = blind_violations(doc)
    assert not viol, f"blind protocol: arm / experiment keys in the calibration output: {viol[:5]}"
    with open(out_p + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)
    print(json.dumps(params, indent=1, default=str))
    print(json.dumps({"n_plans": len(plans), "completion": completion, "timing_n": timing["n_fills"], "fee_switch": L.U(sw_ts),
                      "flatten_events": timing["flatten_events"], "first_leg_consistency": first_leg["fills_ledger_vs_row_rel_diff"],
                      "plans_skipped": dict(n_sk), "slippage": slippage}, indent=1, default=str))


if __name__ == "__main__":
    main()
