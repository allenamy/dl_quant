"""ONE definition of "what our own orders did to the book". Three guards read it; none re-derive it.

★ WHY THIS MODULE EXISTS — THE COPY WAS THE GENERATOR
The expression below existed in THREE places (`watchdog` §4-5b, `pilot_metrics.m5`,
`watchdog_inputs.derive_ops_stats`), and the same sign defect was present in all three:

    f = float(o["filled_notional"] or 0.0)
    if f > 0:                                          # <- drops every SELL
        fills[ats][sym] += (1 if o["side"] == "buy" else -1) * f   # <- re-applies a sign

`filled_notional` is ALREADY signed (`binance_broker`: `sign * cumQuote`). 0C's audit named four
sign sites; the third copy of THIS comparison was found only while reading §4-7 to classify it —
and the rule that would have found it ("when fixing a category error, SEARCH FOR ITS TWIN") was
written twenty lines above one of the copies and did not protect its own author.

⇒ The lasting fix is not the third repair, it is removing the thing that made three repairs
  necessary. One function, three callers, and a fourth copy has nowhere to come from.

★ WHAT IS SHARED AND WHAT IS NOT
Shared: the aggregation — signed fills, grouped by anchor and symbol. That is the piece that was
copied and the piece the defect lived in. NOT shared: what each guard concludes from it. §4-5b
asks "is the CURRENT position explained", M5 asks "how far is the book from target", §4-7 asks
"has drift gone un-recovered" — three questions, one input. Collapsing the questions too would be
the opposite error: a shared conclusion nobody can adjust per guard.

★ THE ONE THING A READER MUST NOT ASSUME
A flatten performed by the degradation ladder does NOT appear in the orders log, so a book that
went flat by ladder action is, from here, an unexplained change. That is a true statement about
our records and not a bug in this function — see docs/OPEN_ITEMS.md.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple


def signed_fills_by_anchor(orders: Iterable[Dict[str, Any]]) -> Dict[float, Dict[str, float]]:
    """{anchor_ts: {symbol: SIGNED filled notional}} — the exposure our orders actually created.

    ★ SIGNED, AND NOTHING IS RE-APPLIED. `filled_notional` carries its own sign; a buy is
    positive, a sell negative. Callers that want SCALE (a cost denominator, a fill rate) must take
    abs() at their own site — the column is one quantity and the consumer decides how to read it.

    ★ A None IS SKIPPED, NOT READ AS ZERO. Since the R19 pass, `filled_notional` is None when we
    could not read it (`skipped_unknown_fill`), and treating that as "filled nothing" is the exact
    reading that produced the 2x doubling. It contributes nothing here and the caller sees the
    symbol simply absent — which is what "we do not know" looks like in a sum.
    """
    out: Dict[float, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for o in orders:
        f = o.get("filled_notional")
        if f is None:
            continue
        f = float(f)
        if f:
            out[o["anchor_ts"]][o["symbol"]] += f
    return {k: dict(v) for k, v in out.items()}


def reconcile(days_data: List[Tuple[str, Dict[str, Any]]],
              tol: float = 0.10) -> Dict[str, Any]:
    """Walk the readbacks in time order and report positions our orders do not explain.

    `days_data` = [(day, {"orders": [...], "position_readback": [...]}), ...] in ascending order.

    Returns:
        anomalies            every (anchor, symbol) whose change exceeds `tol`, oldest first
        last_reconciled_ats  the newest anchor that HAD a predecessor to compare against
        latest               the anomalies at that anchor only  ← what a STATE gate reads
        n_reconciled_anchors how many comparisons were possible at all

    ★ `latest` vs `anomalies` IS THE STATE/HISTORY DISTINCTION, MADE ONCE HERE.
    A guard that asks about the CURRENT book reads `latest`; one that asks what happened over the
    window reads `anomalies`. Before this, each guard re-decided that question for itself and two
    of them chose "all of history", which gave them a property nobody wanted: once true, never
    false again. Deciding it in one place is what lets §4-5b and §4-7 give ONE answer.
    """
    # ★★ EXECUTIONS ARE CONSUMED BY INTERVAL, NOT BY ANCHOR BUCKET (lead's property 1).
    # The previous version looked up `fills[ats]` — the fills whose row carries THIS anchor's
    # anchor_ts. That silently assumes every execution belongs to some anchor's bucket, and the
    # one execution that does not is the one that matters most: the degradation ladder's
    # protective flatten, which happens between anchors under its own id. It would have been
    # missed, and the position change it caused would have been reported as unexplained — the
    # exact defect we are fixing, reintroduced one layer down.
    # ⇒ So each reconciliation consumes EVERY in-ledger execution in (t_prev, t_cur], whatever
    #   bucket it is labelled with. The ordering key is the execution's own time when it has one
    #   (`last_fill_ts`), falling back to its anchor_ts.
    _exec: List[Tuple[float, str, float]] = []
    for _day, one in days_data:
        for o in one.get("orders", []):
            f = o.get("filled_notional")
            if f is None or not float(f):
                continue
            t = o.get("last_fill_ts") or o.get("first_fill_ts") or o.get("anchor_ts")
            if t is None:
                continue
            _exec.append((float(t), o["symbol"], float(f)))
    _exec.sort()

    def _between(t_lo: Optional[float], t_hi: float) -> Dict[str, float]:
        agg: Dict[str, float] = defaultdict(float)
        for t, sym, f in _exec:
            if (t_lo is None or t > t_lo) and t <= t_hi:
                agg[sym] += f
        return agg

    anomalies: List[Dict[str, Any]] = []
    prev_rb: Optional[Dict[str, float]] = None
    prev_t: Optional[float] = None
    last_ats: Optional[float] = None
    n_reconciled = 0
    for _day, one in days_data:
        rb_by_anchor: Dict[float, Dict[str, float]] = defaultdict(dict)
        rb_time: Dict[float, float] = {}
        for r in one.get("position_readback", []):
            rb_by_anchor[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
            # the moment the venue was ASKED bounds the interval; anchor_ts is the fallback for
            # rows written before read_ts existed
            rb_time[r["anchor_ts"]] = float(r.get("read_ts") or r["anchor_ts"])
        for ats in sorted(rb_by_anchor):
            cur = rb_by_anchor[ats]
            t_cur = rb_time.get(ats, ats)
            if prev_rb is not None:
                n_reconciled += 1
                _win = _between(prev_t, t_cur)
                for sym, v in cur.items():
                    expected = prev_rb.get(sym, 0.0) + _win.get(sym, 0.0)
                    unexplained = abs(v - expected)
                    scale = max(abs(expected), abs(v), 1.0)
                    frac = unexplained / scale
                    if frac > tol:
                        anomalies.append({"anchor_ts": ats, "symbol": sym,
                                          "expected": round(expected, 2),
                                          "observed": round(v, 2),
                                          "unexplained_frac": round(frac, 4)})
                last_ats = ats
            prev_rb = cur
            prev_t = t_cur
    return {"anomalies": anomalies,
            "last_reconciled_ats": last_ats,
            "latest": [a for a in anomalies if a["anchor_ts"] == last_ats],
            "n_reconciled_anchors": n_reconciled,
            "tol": tol}
