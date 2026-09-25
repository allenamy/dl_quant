#!/usr/bin/env python3
"""R25-03 + the "+2.3% NAV long tilt" breakdown, one device (independent review 7cbe907ba; lead ruling 2026-09-25). READ-ONLY, pooled, no venue.
Replaces paper_vs_live.py's comparison, whose "paper" was the PRODUCER'S RAW book (target_live, pre-reshape) labelled "what the executor
sizes" (wrong: the executor re-demeans, pops, clamps — scheduler/anchor_loop.py apply_withhold_and_reshape L336) and whose missing prices
counted as 0. Here every layer is valued at the SAME decision-time price and over the SAME holding interval, per name:
  L0 producer raw   w_raw(target_live/A.json) / sum|w_raw| x G,  G = reshape.sizing_gross (the executor's own number; E6 identity
                    net_producer_usdt == sum L0 is asserted)
  L1 reshaped       L0 minus reshape.removed_names, demeaned over the remaining names, rescaled to sum| | = G (signal/legs.py L194-199);
                    asserted: sum L1 == reshape.net_after, sum|L1| == reshape.gross_after (the reconstruction must reproduce the report)
  L2 clamped target the order rows' target_w x anchors.target_gross (asserted: sum == clamped_after_reshape.book_net_usdt); names with a
                    target but no order row are listed
  L3 tried          the clamped target for a name with >= 1 submitted row, else the previous position (rev 1: the per-attempt\n                    intended_notional sum double counted re-intended residuals)
  L4 filled         prev position + signed filled_notional (every row)
  L5 readback       this anchor's venue readback quantity x the same mid
  positions (prev, L5) are QUANTITIES from position_readback valued at mid_at_anchor (anchors row) — never the readback's own notional,
  which moves with the mark between reads. Contract closure per name: post_qty == prev_qty + sum filled_qty (filled_qty missing ⇒ derived
  from filled_notional / avg_fill_px; not derivable ⇒ UNKNOWN), residuals listed.
P&L of every layer = sum_i layer_i x r_i with r_i the rr return (nc_contract.rr_from_ch0, latest snapshot) from this anchor's readback time to
the next one's; a name without a price goes to UNPRICED (its |notional| per layer is reported; it is never counted as 0 P&L). Differences
between consecutive layers name the step: reshape (L1-L0), clamp (L2-L1), lot/min-notional/not-sent (L3-L2), fill shortfall (L4-L3),
readback vs fills (L5-L4).
Net tilt per layer (sum, USDT) for every anchor with a reshape record; the L2 -> L5 net gap per name classified by the name's order outcome:
  skipped_min_notional / partial_expired / venue_reject / blocked_by_halt / filled / designed abstention (arm-named label, pooled) /
  no_order_row / other.
usage: ~/wide_shadow/venv/bin/python layered_book.py <out dir> [--from 2026-09-24T08] [--to 2026-09-25T08]"""
import calendar, collections, glob, hashlib, json, math, os, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
bad = lambda k: "chase" in str(k).lower() or "arm" in str(k).lower()
LAYERS = ["L0_raw", "L1_reshaped", "L2_clamped", "L3_intended", "L4_filled", "L5_readback"]


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def jl(name, days):
    out = []
    for d in days:
        p = f"{L}/{d}/{name}.jsonl"
        if os.path.exists(p): out += [{k: v for k, v in json.loads(l).items() if not bad(k)} for l in open(p) if l.strip()]
    return out


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); a = sys.argv[2:]
    t_from = calendar.timegm(time.strptime(a[a.index("--from") + 1] if "--from" in a else "2026-09-24T08", "%Y-%m-%dT%H"))
    t_to = calendar.timegm(time.strptime(a[a.index("--to") + 1] if "--to" in a else "2026-09-25T08", "%Y-%m-%dT%H"))
    days = sorted(os.path.basename(d) for d in glob.glob(f"{L}/2026*") if os.path.basename(d) >= time.strftime("%Y%m%d", time.gmtime(t_from - 86400)))
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit()); last = snaps[-1]
    Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); B = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)]); FIN = np.isfinite(RR)
    def ret(s, tA, tB):
        j = col.get(s)
        if j is None or tB > ts[-1] + 300: return None
        i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
        if i0 < 0 or i1 <= i0 or FIN[i0 + 1:i1 + 1, j].sum() < 0.9 * (i1 - i0): return None
        return float(np.expm1(LP[i1 + 1, j] - LP[i0 + 1, j]))
    AN = sorted(jl("anchors", days), key=lambda r: float(r["anchor_ts"])); OR = jl("orders", days); RB = jl("position_readback", days)
    rb = collections.defaultdict(dict); rbt = {}
    for p in RB:
        t = float(p["anchor_ts"]); rb[t][p["symbol"]] = p.get("venue_position_qty"); rbt[t] = max(rbt.get(t, 0.0), float(p.get("read_ts") or t))
    rb_ts = sorted(rb)
    orows = collections.defaultdict(lambda: collections.defaultdict(list))
    for o in OR: orows[o.get("rebalance_id")][o.get("symbol")].append(o)
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "price_snapshot": last, "rolling_sha256": sha(f"{WS}/state/snap/{last}/rolling.npz"),
           "window": [fmt(t_from), fmt(t_to)], "anchors": []}
    T = collections.defaultdict(float)
    for an in AN:
        at = float(an["anchor_ts"]); A = int(at // 14400 * 14400)
        if not (t_from <= A <= t_to): continue
        rs = {k: v for k, v in (an.get("reshape") or {}).items() if not bad(k)}; rid = an.get("rebalance_id")
        row = {"A": fmt(A), "rebalance_id": rid, "checks": {}}
        tl = f"{WS}/state/target_live/{A}.json"
        if not rs or not os.path.exists(tl):
            row["skip"] = "no reshape record or no target_live"; rec["anchors"].append(row); continue
        G = float(rs["sizing_gross"]); W = json.load(open(tl))["weights"]; sw = sum(abs(v) for v in W.values())
        mids = an.get("mid_at_anchor_vector"); mids = json.loads(mids) if isinstance(mids, str) else (mids or {})
        L0 = {s: v / sw * G for s, v in W.items()}
        row["checks"]["E6 sum L0 == net_producer_usdt"] = abs(sum(L0.values()) - rs["net_producer_usdt"]) < 1e-6 * G
        keep = [s for s in L0 if s not in set(rs.get("removed_names") or [])]
        v = np.array([L0[s] / G for s in keep]); v = v - v.mean(); v = v / np.abs(v).sum()
        L1 = {s: float(x * G) for s, x in zip(keep, v)}
        for s in rs.get("forced_flat_names") or []: L1[s] = 0.0
        row["checks"]["L1 reproduces net_after / gross_after"] = abs(sum(L1.values()) - rs["net_after"]) < 1e-6 * G and abs(sum(abs(x) for x in L1.values()) - rs["gross_after"]) < 1e-6 * G
        orr = orows.get(rid, {}); tg = num(an.get("target_gross"))
        L2 = {s: float(num(rows[0].get("target_w")) or 0.0) * tg for s, rows in orr.items()} if tg else {}
        ca = rs.get("clamped_after_reshape") or {}
        row["checks"]["sum L2 == clamped_after_reshape.book_net_usdt"] = bool(tg) and abs(sum(L2.values()) - float(ca.get("book_net_usdt", 0))) < 1e-3 * G
        row["L1_names_without_order_row"] = sorted(s for s in L1 if s not in orr and abs(L1[s]) > 1e-9)
        prev_t = [t for t in rb_ts if t < at]; prev = rb[prev_t[-1]] if prev_t else {}; post = rb.get(at, {})
        names = sorted(set(L0) | set(L1) | set(L2) | set(prev) | set(post))
        per = {}; unknown_mid = []
        for s in names:
            m = num(mids.get(s))
            rows = orr.get(s, [])
            pq, qq = num(prev.get(s)) if s in prev else 0.0, num(post.get(s)) if s in post else 0.0
            fq, fq_known = 0.0, True; intended = 0.0; filled_usdt = 0.0
            for o in rows:
                sd = 1.0 if str(o.get("side")).lower() == "buy" else (-1.0 if str(o.get("side")).lower() == "sell" else 0.0)
                pass   # rev 1: intended_notional is per ATTEMPT (a residual re-intended by later attempts / top-ups) — summing it double counts
                fn = num(o.get("filled_notional")); filled_usdt += fn or 0.0
                q = num(o.get("filled_qty"))
                if q is None:
                    px = num(o.get("avg_fill_px"))
                    if fn == 0.0 or (fn is None and o.get("submit_ts") is None): q = 0.0
                    elif fn is not None and px: q = fn / px
                    else: fq_known = False; q = 0.0
                fq += q
            e = {"L0_raw": L0.get(s, 0.0), "L1_reshaped": L1.get(s, 0.0), "L2_clamped": L2.get(s, 0.0) if s in L2 else L1.get(s, 0.0)}
            if m is None or pq is None or qq is None:
                unknown_mid.append(s); e.update({"L3_intended": None, "L4_filled": None, "L5_readback": None})
            else:
                # rev 1 (run 1 showed L3 net +9.7k..+20.7k: the per-attempt sum double counts): L3 = what the executor TRIED to reach —
                # the clamped target for a name with >= 1 submitted row, the previous position for a name whose rows were all not sent
                sent = any(o.get("submit_ts") is not None for o in rows)
                e["L3_intended"] = e["L2_clamped"] if sent else pq * m
                e["L4_filled"] = pq * m + filled_usdt; e["L5_readback"] = qq * m
            e["closure_qty_residual"] = (qq - pq - fq) if (fq_known and pq is not None and qq is not None) else None
            reasons = {("<designed abstention, pooled>" if bad(o.get("terminal_reason")) else str(o.get("terminal_reason"))) for o in rows}
            e["class"] = ("no_order_row" if not rows else next((c for c in ("venue_reject", "partial_expired", "blocked_by_halt", "skipped_min_notional",
                          "<designed abstention, pooled>", "filled") if c in reasons), "other"))
            e["clamped"] = s in set(ca.get("names") or [])
            per[s] = e
        _nc = [abs(e["L2_clamped"] - e["L1_reshaped"]) for s_, e in per.items() if not e["clamped"] and s_ in L1 and s_ in L2]
        row["checks"]["per name L2 == L1 for every NON-clamped name (the reshape population is the producer's names, no zero-target names)"] = \
            bool(_nc) and max(_nc) < 1e-6 * G
        row["max_abs_L2_minus_L1_nonclamped_usdt"] = max(_nc) if _nc else None
        row["net_by_layer"] = {Lk: sum(e[Lk] for e in per.values() if e[Lk] is not None) for Lk in LAYERS}
        row["unknown_price_names"] = unknown_mid
        cls = collections.defaultdict(float)
        for s, e in per.items():
            if e["L5_readback"] is None: continue
            cls["clamp (L2-L1): " + ("clamped names" if e["clamped"] else "others")] += e["L2_clamped"] - e["L1_reshaped"]
            cls["L2->L5: " + e["class"]] += e["L5_readback"] - e["L2_clamped"]
        row["net_gap_by_class"] = dict(cls)
        row["closure"] = {"n_names_unknown_fill_qty": sum(1 for e in per.values() if e["closure_qty_residual"] is None),
                          "n_names_residual_gt_1e-9": sum(1 for e in per.values() if e["closure_qty_residual"] is not None and abs(e["closure_qty_residual"]) > 1e-9),
                          "worst": sorted(((s, e["closure_qty_residual"]) for s, e in per.items() if e["closure_qty_residual"] is not None), key=lambda x: -abs(x[1]))[:5]}
        # P&L by layer over (this readback, next readback)
        nxt = [t for t in rb_ts if t > at]
        if nxt:
            tA, tB = rbt.get(at, at), rbt.get(nxt[0], nxt[0])
            pnl = collections.defaultdict(float); unpriced = collections.defaultdict(float); n_unp = 0
            for s, e in per.items():
                r = ret(s, tA, tB)
                for Lk in LAYERS:
                    x = e[Lk]
                    if x is None: continue
                    if r is None: unpriced[Lk] += abs(x)
                    else: pnl[Lk] += x * r
                n_unp += r is None and any(abs(e[Lk] or 0) > 0 for Lk in LAYERS)
            row["pnl_by_layer"] = dict(pnl); row["unpriced_abs_notional_by_layer"] = dict(unpriced); row["n_unpriced_names"] = n_unp
            row["priced"] = tB <= ts[-1] + 300
            if row["priced"]:
                for Lk in LAYERS: T["pnl_" + Lk] += pnl[Lk]
                T["n_priced_anchors"] += 1
        for Lk in LAYERS: T["net_" + Lk] += row["net_by_layer"][Lk]
        T["n_anchors"] += 1
        rec["anchors"].append(row)
    rec["totals"] = dict(T)
    json.dump(rec, open(f"{out}/LAYERED_BOOK.json", "w"), indent=1, default=str)
    for r in rec["anchors"]:
        if "skip" in r: print(r["A"], r["skip"]); continue
        print(f"{r['A']} checks {r['checks']}")
        print("   net by layer:", {k: round(v, 1) for k, v in r["net_by_layer"].items()})
        print("   L1->L5 net gap by class:", {k: round(v, 1) for k, v in sorted(r["net_gap_by_class"].items())})
        print("   closure:", r["closure"], "| unknown price names", len(r["unknown_price_names"]), "| L1 names w/o order row", r["L1_names_without_order_row"][:8])
        if "pnl_by_layer" in r: print("   P&L by layer" + ("" if r["priced"] else " (NOT fully priced: next readback after the price cache)") + ":",
                                     {k: round(v, 1) for k, v in r["pnl_by_layer"].items()}, "| unpriced |notional|", {k: round(v) for k, v in r["unpriced_abs_notional_by_layer"].items() if v})
    print("TOTALS", {k: round(v, 1) for k, v in T.items()})


if __name__ == "__main__":
    main()
