#!/usr/bin/env python3
"""fix-pkg-d first-anchor acceptance, the lead's three extra checks (2026-09-26 ~00:2xZ). Criteria FROZEN here before the 04Z anchor
(committed before 04:00Z). READ-ONLY on ~/dl_quant_live; blind: no arm-named field is printed.
  (a) FIELDS: the anchor's anchors row carries reshape.n_dust_popped (int) and reshape.dust_popped_names (list), with
      n_dust_popped == len(dust_popped_names) and dust_popped_names ⊆ reshape.popped_names.
  (b) NEUTRAL: post-clamp book net = reshape.clamped_after_reshape.book_net_usdt; NAV = m3_beta_overlay.nav_usdt.
      NEUTRAL iff |book_net| <= max(50 USDT, 0.1 % of NAV). Reference: the 08Z fixture (tests_dust_pop D6) gives -7.16 USDT under the
      fixed rule vs +2,464 recorded; the engine cell's post-clamp |net| p95 was 0.08 %. Not neutral ⇒ the clamped names that are still
      pinned (reshape.clamped_after_reshape.names, pinned_net_usdt) are listed so the residual is attributed, never silently passed.
      The pre-release anchors' book_net_usdt are printed beside it (the same field, same caliber).
  (c) NO QUANTITY for popped names: in orders rows of this rebalance_id, every row of a name in reshape.popped_names must have
      |intended_notional| == 0 (or absent) and filled_qty == 0 (or absent); any other row = RED, listed.
Unknown is not zero: a missing row / field is UNDECIDED (named), never PASS.
usage: /usr/bin/python3 accept_dustpop_first_anchor.py <anchor_ts> [--ref-anchors a,b,c]"""
import json, math, os, sys, time

LIVE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
bad = lambda k: "chase" in str(k).lower() or "arm" in str(k).lower()


def rows(day, table):
    p = f"{LIVE}/{day}/{table}.jsonl"
    if not os.path.exists(p): return None
    out = []
    for l in open(p):
        try: out.append(json.loads(l))
        except ValueError: pass
    return out


def anchor_row(A):
    day = time.strftime("%Y%m%d", time.gmtime(A))
    rs = rows(day, "anchors")
    if rs is None: return None, day
    m = [r for r in rs if A <= float(r.get("anchor_ts") or 0) < A + 14400]    # the row's anchor_ts is the REBALANCE time (N+24 min)
    return (m[-1] if m else None), day


def num(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if math.isfinite(x) else None


def main():
    A = int(sys.argv[1]); a = sys.argv[2:]
    refs = [int(x) for x in a[a.index("--ref-anchors") + 1].split(",")] if "--ref-anchors" in a else []
    verdict = {}
    r, day = anchor_row(A)
    print(f"ACCEPT_DUSTPOP A={A} ({time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(A))}) day={day}")
    if r is None:
        print("UNDECIDED: no anchors row for A"); print("ACCEPT_DUSTPOP VERDICT=UNDECIDED"); return 2
    rs = r.get("reshape") or {}
    # (a)
    n_dp, dpn, popped = rs.get("n_dust_popped"), rs.get("dust_popped_names"), rs.get("popped_names")
    print(f"(a) reshape.n_dust_popped={n_dp!r} dust_popped_names={dpn!r} n_popped={rs.get('n_popped')!r} popped_names={popped!r}")
    if not isinstance(n_dp, int) or not isinstance(dpn, list) or not isinstance(popped, list):
        verdict["a"] = "UNDECIDED (field missing or wrong type)"
    else:
        verdict["a"] = "PASS" if (n_dp == len(dpn) and set(dpn) <= set(popped)) else "RED (n != len or dust not a subset of popped)"
    # (b)
    car = rs.get("clamped_after_reshape") or {}
    bn = num(car.get("book_net_usdt")); nav = num((r.get("m3_beta_overlay") or {}).get("nav_usdt"))
    print(f"(b) post-clamp book_net_usdt={bn} NAV={nav} ratio={None if (bn is None or not nav) else round(bn / nav * 100, 4)}% "
          f"| still clamped: names={car.get('names')} pinned_net_usdt={car.get('pinned_net_usdt')} net_shift_usdt={car.get('net_shift_usdt')} "
          f"| venue_net_usdt={r.get('venue_net_usdt')} net_over_gross={r.get('net_over_gross')}")
    for R in refs:
        rr, _ = anchor_row(R)
        c = ((rr or {}).get("reshape") or {}).get("clamped_after_reshape") or {}
        nv = num(((rr or {}).get("m3_beta_overlay") or {}).get("nav_usdt"))
        b2 = num(c.get("book_net_usdt"))
        print(f"    ref {time.strftime('%m-%dT%HZ', time.gmtime(R))} (pre-release) book_net_usdt={b2} ratio={None if (b2 is None or not nv) else round(b2 / nv * 100, 4)}% clamped={c.get('names')}")
    if bn is None or not nav:
        verdict["b"] = "UNDECIDED (book_net or NAV missing)"
    else:
        tol = max(50.0, 0.001 * nav)
        verdict["b"] = f"NEUTRAL (|{bn:.2f}| <= {tol:.2f})" if abs(bn) <= tol else f"NOT NEUTRAL (|{bn:.2f}| > {tol:.2f}; residual attributed to the still-clamped names above)"
    # (c)
    od = rows(day, "orders")
    rid = r.get("rebalance_id")
    if od is None or rid is None or not isinstance(popped, list):
        verdict["c"] = "UNDECIDED (orders table / rebalance_id / popped_names missing)"
    else:
        pr = [o for o in od if o.get("rebalance_id") == rid and o.get("symbol") in set(popped)]
        viol = []
        for o in pr:
            inot = num(o.get("intended_notional")); fq = num(o.get("filled_qty"))
            if (o.get("intended_notional") is not None and (inot is None or abs(inot) > 0)) or (o.get("filled_qty") is not None and (fq is None or abs(fq) > 0)):
                viol.append({k: o.get(k) for k in ("symbol", "order_type", "intended_notional", "filled_qty", "terminal_reason") if not bad(k)})
        print(f"(c) orders rows of this rebalance ({rid}) for popped names: {len(pr)}; "
              f"terminal={sorted(set(str(o.get('terminal_reason')) for o in pr))}; with a quantity: {viol}")
        verdict["c"] = "PASS" if not viol else f"RED ({len(viol)} row(s) with a quantity)"
    for k in "abc": print(f"  ({k}) {verdict[k]}")
    overall = ("RED" if any(v.startswith("RED") for v in verdict.values()) else
               "UNDECIDED" if any(v.startswith("UNDECIDED") for v in verdict.values()) else
               "NOT_NEUTRAL" if verdict["b"].startswith("NOT") else "PASS")
    print(f"ACCEPT_DUSTPOP VERDICT={overall} a={verdict['a'].split()[0]} b={verdict['b'].split()[0]} c={verdict['c'].split()[0]}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
