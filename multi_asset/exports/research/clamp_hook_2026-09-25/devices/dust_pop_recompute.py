#!/usr/bin/env python3
"""Pure recompute from the ledger (no engine, no executor code run): what the executor's net would have been if a HELD untradable name whose
position is DUST (|held notional| < the venue's min notional for that name) were treated as FLAT — popped before the reshape (so the reshape
re-neutralises the rest) instead of clamped after it (lead 2026-09-25 ~15:5xZ, fix design item 3). READ-ONLY, pooled, no venue.
Today (scheduler/anchor_loop.py L331, withhold_pop): `if float(held.get(s, 0.0) or 0.0) == 0.0: pop` — only an EXACT zero is popped; a
0.12 USDT residual (PRLUSDT −1 contract) is "held" and goes to the clamp (clamp_held_untradable L464), and the planner can never close it
(live/binance_executor.py L825-L827: any |delta| < min_notional ⇒ skipped_min_notional, exits included).
Per anchor (anchors rows with a reshape record in the window):
  actual   L1 (reconstructed, identity-checked in layered_book.py) and L2 = order target_w × target_gross; net L2 = clamped_after_reshape
  dust-pop D = clamped names with |held| < floor (held = previous venue readback qty × mid_at_anchor; floor = exchange_info_cache min_notional);
           L1' = producer names minus removed minus D, demeaned + rescaled to G (signal/legs.py L194-199); L2' = L1' with the remaining
           clamped names at their actual L2 value (they are held above the floor: the clamp still applies); net L2' = sum L2'.
  reported: net L2 vs net L2' (USDT and / NAV), the D names with their held notional, and every clamped name kept.
usage: ~/wide_shadow/venv/bin/python dust_pop_recompute.py <out dir> [--from 2026-09-16T12] [--to 2026-09-25T12]"""
import calendar, collections, glob, json, math, os, sys, time
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; DQ = f"{HOME}/dl_quant_live"; L = f"{DQ}/state/live/pilot_log"
bad = lambda k: "chase" in str(k).lower() or "arm" in str(k).lower()
fmt = lambda t: time.strftime("%m-%dT%HZ", time.gmtime(t))


def num(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if math.isfinite(x) else None


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); a = sys.argv[2:]
    t_from = calendar.timegm(time.strptime(a[a.index("--from") + 1] if "--from" in a else "2026-09-16T12", "%Y-%m-%dT%H"))
    t_to = calendar.timegm(time.strptime(a[a.index("--to") + 1] if "--to" in a else "2026-09-25T12", "%Y-%m-%dT%H"))
    floor = {s: num(v.get("min_notional")) for s, v in json.load(open(f"{DQ}/state/exchange_info_cache.json")).items() if isinstance(v, dict)}
    days = sorted(os.path.basename(p) for p in glob.glob(f"{L}/2026*") if os.path.basename(p) >= time.strftime("%Y%m%d", time.gmtime(t_from - 86400)))
    rd = lambda n: [{k: v for k, v in json.loads(l).items() if not bad(k)} for d in days if os.path.exists(f"{L}/{d}/{n}.jsonl") for l in open(f"{L}/{d}/{n}.jsonl") if l.strip()]
    AN = sorted(rd("anchors"), key=lambda r: float(r["anchor_ts"])); OR = rd("orders"); RB = rd("position_readback")
    rb = collections.defaultdict(dict)
    for p in RB: rb[float(p["anchor_ts"])][p["symbol"]] = num(p.get("venue_position_qty"))
    rbt = sorted(rb); orr = collections.defaultdict(dict)
    for o in OR: orr[o.get("rebalance_id")].setdefault(o.get("symbol"), o)
    rows = []; dust_names = collections.Counter(); kept_names = collections.Counter()
    for an in AN:
        at = float(an["anchor_ts"]); A = int(at // 14400 * 14400)
        if not (t_from <= A <= t_to): continue
        rs = an.get("reshape") or {}; ca = rs.get("clamped_after_reshape") or {}; tl = f"{WS}/state/target_live/{A}.json"
        if not rs or not os.path.exists(tl): continue
        G = float(rs["sizing_gross"]); W = json.load(open(tl))["weights"]; sw = sum(abs(v) for v in W.values()); L0 = {s: v / sw * G for s, v in W.items()}
        removed = set(rs["removed_names"]) if "removed_names" in rs else set(rs.get("popped_names") or []) | set(rs.get("forced_flat_names") or [])
        mids = an.get("mid_at_anchor_vector"); mids = json.loads(mids) if isinstance(mids, str) else (mids or {})
        prev = [t for t in rbt if t < at]; held = rb[prev[-1]] if prev else {}
        tg = num(an.get("target_gross")); rid = an.get("rebalance_id")
        L2 = {s: float(num(o.get("target_w")) or 0.0) * tg for s, o in orr[rid].items()} if tg else {}
        D, kept = {}, {}
        for n in ca.get("names") or []:
            q, m = held.get(n), num(mids.get(n)); h = q * m if (q is not None and m is not None) else None
            if h is not None and floor.get(n) and abs(h) < floor[n]: D[n] = h
            else: kept[n] = h
        keep = [s for s in L0 if s not in removed and s not in D]
        v = np.array([L0[s] / G for s in keep]); v = v - v.mean(); v = v / np.abs(v).sum(); L1p = dict(zip(keep, (v * G).tolist()))
        L2p = dict(L1p)
        for n in kept: L2p[n] = L2.get(n, 0.0)
        nav = G / 2.0; net_act = float(ca.get("book_net_usdt") or 0.0); net_new = float(sum(L2p.values()))
        rows.append({"A": fmt(A), "net_actual_usdt": net_act, "net_dustpop_usdt": net_new, "net_actual_pct_nav": net_act / nav * 100, "net_dustpop_pct_nav": net_new / nav * 100,
                     "dust_popped": {k: round(x, 3) for k, x in D.items()}, "clamped_kept": {k: (round(x, 1) if x is not None else None) for k, x in kept.items()}})
        for n in D: dust_names[n] += 1
        for n in kept: kept_names[n] += 1
    rec = {"window": [fmt(t_from), fmt(t_to)], "anchors": rows,
           "summary": {"n_anchors": len(rows), "mean_net_actual_pct_nav": float(np.mean([r["net_actual_pct_nav"] for r in rows])) if rows else None,
                       "mean_net_dustpop_pct_nav": float(np.mean([r["net_dustpop_pct_nav"] for r in rows])) if rows else None,
                       "max_abs_net_dustpop_pct_nav": float(max(abs(r["net_dustpop_pct_nav"]) for r in rows)) if rows else None,
                       "dust_popped_name_anchors": dict(dust_names.most_common()), "clamped_kept_name_anchors": dict(kept_names.most_common())}}
    json.dump(rec, open(f"{out}/DUST_POP_RECOMPUTE.json", "w"), indent=1)
    for r in rows:
        print(f"{r['A']} net actual {r['net_actual_usdt']:+9.1f} ({r['net_actual_pct_nav']:+.3f}% NAV) -> dust-pop {r['net_dustpop_usdt']:+9.1f} ({r['net_dustpop_pct_nav']:+.3f}%) "
              f"| popped {list(r['dust_popped'])[:6]} kept {list(r['clamped_kept'])[:4]}")
    print("SUMMARY", json.dumps(rec["summary"])[:900])


if __name__ == "__main__":
    main()
