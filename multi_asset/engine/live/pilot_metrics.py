"""pilot_metrics.py — the ONLY thing the pilot gates read (§9.5 item ②, F9).

The gates in §3 read this script's JSON output and nothing else. It is signed with the protocol and
its hash recorded: **editing this script after signing = editing the protocol.**

★ DEFINITIONS ARE PINNED (protocol §10) -- they are not re-litigated here, only implemented:

  M1 numerator    fees + slippage measured against `mid_at_anchor` (NOT arrival). funding EXCLUDED
                  (that is M6). Top-up taker fees ARE included.
                  >> Why the anchor benchmark: top-up orders submit up to 900s after the anchor, so
                     benchmarking against arrival silently drops the DELAY cost -- and delay cost is
                     not symmetric noise, it is systematically adverse. We buy what we predict will
                     rise; filling 900s later means filling after part of the predicted move has
                     already happened. That is alpha decay leaking into execution -- the same
                     "4h signal decays fast" fact seen from the execution side. The two readings
                     differed by 3.2bps on 0C's synthetic day while PASS(4.5)->FAIL(7.0) is only
                     2.5bps apart: the benchmark choice alone can turn a red book green.
  M1 denominator  sum of filled notional, ONE-SIDED, quote currency (USD)
  M2              MAKER fills only, per CHILD fill, weighted by fill notional
  M3 denominator  intended_notional of attempt_idx == 1 only (never sum intended across attempts --
                  attempt 2's intended is a RESIDUAL)
  M4 gate         TARGET-weight turnover vs the backtest 1466; realized turnover reported alongside
  M5              reconciled against `position_readback` (the VENUE), never against our own fills;
                  shortfall is split by `terminal_reason` so "did not fill" and "deliberately
                  abandoned under F16" are not conflated

★ team-lead ruling: `c` (M1) MUST be reported stratified by regime, and if the window contains zero
  stress days the script PRINTS a blind-spot warning rather than quietly reporting an overall mean.
  Rationale (0C's own correction): for a regime-dependent quantity, sample COUNT is not regime
  COVERAGE -- the two cannot substitute for each other.

Usage:
    python engine/live/pilot_metrics.py --root <log_root> [--days N] [--out <json>]
    python engine/live/pilot_metrics.py --self-hash
"""
from __future__ import annotations
import os
import argparse, hashlib, json, os, sys
from collections import defaultdict

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilot_log as PL

BPS = 1e4
BACKTEST_TURNOVER_ANN = 1466.0        # §3d reference


def self_hash() -> str:
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def _wmean(pairs):
    num = sum(v * w for v, w in pairs)
    den = sum(w for _, w in pairs)
    return (num / den) if den else None


# ------------------------------------------------------------------ metrics
# ★★ [h] THE COMPONENTS `measurement_complete` ACTUALLY CONSUMES, pinned so §2.5.7 cannot be
# loosened silently. §2.5.7 uses `m1.measurement_complete` as a day's eligibility test, but the
# flag means "the two KNOWN components were measured" — add a third unmeasurable component later
# and the criterion widens with nobody deciding to widen it.
# ★ AND THE SET IS TAKEN FROM THE EXPRESSION, NOT FROM A FIELD-NAME GLOB. `m1` returns THREE
#   `n_unmeasured_*` keys; `n_unmeasured_fills` is a back-compat ALIAS of the slippage counter,
#   not a component. An assertion written as "every field matching n_unmeasured_* is in the pin"
#   goes red on day one, and the cheapest way to silence it is to widen the pin — which is
#   precisely the loosening the assertion exists to prevent. Wrong candidate set, false alarm,
#   and the standard remedy for the false alarm is the real hole.
M1_COMPLETENESS_COMPONENTS = ("n_unmeasured_slippage", "n_unmeasured_fee")


def m1_effective_cost(orders, regime_by_anchor):
    """bps/side. numerator = fees + |avg_fill_px - mid_at_anchor| slippage; denominator = filled
    notional, one-sided. Returned overall AND stratified by regime."""
    per_regime = defaultdict(lambda: {"fee": 0.0, "slip": 0.0, "den": 0.0, "n": 0})
    tot = {"fee": 0.0, "slip": 0.0, "den": 0.0, "n": 0}
    n_unmeasured_slippage = 0
    n_unmeasured_fee = 0
    n_unknown_fill = 0
    n_unpriced_anchor = 0
    # ★★ M1's UNIVERSE IS THE REBALANCE LEGS (lead's ruling 2026-07-26, pre-window, structural).
    # `c` measures REBALANCE EXECUTION QUALITY — that is what §4-1's 9bps limit was calibrated
    # against. A `protective_flatten` is an event-driven crisis cost: it has no decision anchor to
    # be priced against, it happens at whatever the book costs to exit, and mixing it into `c`
    # would make one gate measure two quantities of different natures.
    # ⇒ It is NOT discarded — it is a real cost and is reported on its own line below
    #   (`protective_flatten_cost`). Excluded from the ratio, present in the record.
    # ⇒ This also dissolves, structurally, the side effect I reported: flatten rows carry no
    #   `mid_at_anchor`, so with them in the universe every day containing a flatten had
    #   `measurement_complete: False`. The fix is a caliber definition, not a scheduling trick.
    _flat = [o for o in orders if o.get("order_type") == "protective_flatten"]
    orders = [o for o in orders if o.get("order_type") in ("maker", "topup_taker")]
    for o in orders:
        # ★ `or 0.0` REMOVED: `filled_notional` is now None when we could not read it, and `or 0.0`
        # turned that into "this row filled nothing", which drops it from the cost measurement
        # ENTIRELY and silently — the denominator shrinks and nothing says why. It is the same
        # fold, in the same file, that the fee half already had.
        _f = o.get("filled_notional")
        if _f is None:
            n_unknown_fill += 1
            continue
        # ★ SCALE, not net: the effective-cost denominator is "how much notional did we trade",
        # one-sided. `if f <= 0: continue` discarded every SELL — measured on the trip day, the
        # denominator kept only the buy side (8757 of 13354, 65.6%), so `c` was a cost per unit
        # of BUY notional wearing the name of a cost per unit traded. One more reason the 20.16
        # reading is void, on top of the three already recorded.
        f = abs(float(_f))
        if f <= 0:
            continue
        # ★ and the same for the baseline. `mid_at_anchor` may now legitimately be None (a
        # `skipped_no_mid` row), and `float(None)` here is the exact crash that took all seven
        # stop-loss conditions down two hours ago via `avg_fill_px`. A row with fills but no
        # anchor mid is unmeasurable, not free.
        if o.get("mid_at_anchor") in (None, 0, 0.0):
            n_unpriced_anchor += 1
            continue
        mid = float(o["mid_at_anchor"])
        # ★ A FILLED ROW WITH NO FILL PRICE IS UNMEASURABLE, NOT ZERO-SLIPPAGE, AND NOT A CRASH.
        # `avg_fill_px` has no producer anywhere in the repo, so the first real fill used to reach
        # `float(None)` here and raise TypeError — which propagated out of watchdog.evaluate() and
        # took ALL SEVEN stop-loss conditions down with it, once per anchor. The rule we adopted
        # everywhere else applies here too: absence produces UNKNOWN. Substituting 0.0 would be
        # worse than the crash — |0 - mid|/mid = 1.0 is 10000bps of fabricated slippage.
        if o.get("avg_fill_px") is None:
            n_unmeasured_slippage += 1
            continue
        slip = abs(float(o["avg_fill_px"]) - mid) / mid * f
        # ★ THE TWIN OF THE LINE ABOVE, AND I MISSED IT ON THE FIRST PASS.
        # `fee_paid` has no producer either (commission is only in userTrades), so `or 0.0` was
        # still fabricating — one line below a check that refuses to fabricate. A row would enter
        # the numerator with a permanently-zero fee component, understating `c` by 2.6-3.5bps
        # against a 9bps limit (29-39%), in the "harder to trigger" direction — while
        # `measurement_complete` reported True, because it only counted the slippage half.
        _fee = o.get("fee_paid")
        if _fee is None:
            n_unmeasured_fee += 1
            fee = 0.0                 # contributes nothing; the row is flagged as fee-unmeasured
        else:
            fee = float(_fee)
        r = regime_by_anchor.get(o["anchor_ts"], "unknown")
        for acc in (per_regime[r], tot):
            acc["fee"] += fee; acc["slip"] += slip; acc["den"] += f; acc["n"] += 1
    def _c(a):
        return round((a["fee"] + a["slip"]) / a["den"] * BPS, 4) if a["den"] > 0 else None
    return {
        # a cost computed from only the measurable rows must say how many it could not see —
        # and BOTH components must be measurable before the measurement is complete
        "n_unmeasured_slippage": n_unmeasured_slippage,
        "n_unmeasured_fee": n_unmeasured_fee,
        "n_unmeasured_fills": n_unmeasured_slippage,        # kept for existing readers
        # rows excluded before the measurement even begins, each for a stated reason — without
        # these two the exclusions are invisible and the cost looks measured over everything
        "n_excluded_unknown_fill": n_unknown_fill,
        "n_excluded_no_anchor_mid": n_unpriced_anchor,
        # ★ the crisis leg, reported beside `c` and never inside it. `n` is the count of flatten
        # rows and `filled_notional` their total — a real cost kept visible without being averaged
        # into a metric whose threshold was set for a different quantity.
        "protective_flatten_cost": {
            "n_rows": len(_flat),
            "filled_notional": round(sum(abs(float(o["filled_notional"]))
                                         for o in _flat
                                         if o.get("filled_notional") is not None), 2),
            "n_unknown_fill": sum(1 for o in _flat if o.get("filled_notional") is None),
            "fee_paid": round(sum(float(o["fee_paid"]) for o in _flat
                                  if o.get("fee_paid") is not None), 6),
            "caliber": ("event-driven exit cost, EXCLUDED from c (which measures rebalance "
                        "execution quality, the quantity §4-1's limit was set for). Reported, "
                        "not discarded."),
        },
        # ★ THREE STATES. With ZERO fills, `n_unmeasured_* == 0` is true and the old two-state
        # flag said `measurement_complete: True` beside `c_bps_overall: None` — "the measurement
        # is complete" about a measurement that does not exist. Measured on the first TESTNET
        # day: 110 rows, all blocked_by_halt, 0 fills, and the pair read True/None.
        # None = "nothing to measure", which is not the same claim as "measured everything".
        "measurement_complete": (None if tot["n"] == 0 else
                                 (n_unmeasured_slippage == 0 and n_unmeasured_fee == 0
                                  and n_unknown_fill == 0 and n_unpriced_anchor == 0)),
        # ★ THE NUMBER CARRIES ITS CALIBER TO THE POINT OF COMPARISON.
        # A single fill's effective cost and this figure are different quantities, and one of them
        # was quoted against the 9.0 bps limit in a report (7.15 "against 9.0, margin under 2") —
        # a comparison whose two sides were not the same thing. Reporting a range instead of a
        # point fixes INCOMPLETENESS; it does nothing for a caliber mismatch, which needs the
        # prior question: is this number the same quantity as that threshold?
        # So the caliber travels WITH the value, and §4-1's limit declares the caliber it is
        # written in (watchdog.C_LIMIT_CALIBER); the two strings must match.
        "caliber": "per-DAY aggregate: (sum fee + sum |slippage|) / sum filled_notional, in bps, "
                   "over every filled order of the day; NOT a per-fill figure",
        "c_bps_overall": _c(tot),
        "filled_notional_total": round(tot["den"], 2),
        "n_filled_orders": tot["n"],
        "by_regime": {r: {"c_bps": _c(a), "filled_notional": round(a["den"], 2),
                          "n_filled_orders": a["n"]}
                      for r, a in sorted(per_regime.items())},
    }


def dedupe_fills(fills):
    """Collapse superseding `fills` rows, last write wins, keyed on the venue's trade id.

    ★ WHY THE TABLE NEEDS THIS AT ALL. The log is APPEND-ONLY, and the +60s mark is a FUTURE
    observation about a fill that has already happened — so a row is written immediately with the
    mark pending, and a later backfill appends the same fill again with the mark filled in.
    Without collapsing, every backfilled fill would be counted twice by M2: once unmeasured, once
    measured, and the `n_unmeasured` counter would never fall.

    ★ ONLY ROWS WITH A trade_id ARE COLLAPSED. That id is the venue's own unique key, so equality
    means "the same execution". Rows without one (a fill we recorded from a source that had no id)
    are passed through untouched — inventing a synthetic key from (symbol, ts, notional) would
    silently merge two genuinely distinct executions that happened to agree, which is a worse
    failure than keeping a duplicate.

    ★ LAST WINS, BY POSITION, NOT BY A "newer" FLAG. The file is append-only, so position IS
    chronology; trusting a self-declared timestamp would let a mis-stamped row overwrite a correct
    one. The one thing the caller must not do is reorder the rows before calling this.
    """
    out, by_id = [], {}
    for f in fills:
        tid = f.get("trade_id")
        if tid is None:
            out.append(f)
            continue
        by_id[tid] = f          # later occurrence replaces the earlier one
    return out + list(by_id.values())


def m2_markout(fills):
    """maker-only, per CHILD fill, notional-weighted, D=60s. Positive = adverse (mid moved against).

    ★ Rows are de-duplicated first: a backfilled mark arrives as a NEW row for a fill already
    written, and counting both would inflate `n_fills` and freeze `n_unmeasured`.
    """
    fills = dedupe_fills(fills)
    # ★ `float(f["fill_notional"])` was unguarded and the column is no longer not_null (R19: it is
    # the venue's account of the fill, and an absent one must read as absent). A fill row missing
    # its notional, side or price cannot be marked out at all — it is UNUSABLE, which is a third
    # state next to "marked" and "mark pending", and folding it into either would misreport.
    _unusable = [f for f in fills
                 if f["order_type"] == "maker"
                 and (f.get("fill_notional") is None or f.get("fill_px") is None
                      or f.get("side") is None)]
    mk = [f for f in fills if f["order_type"] == "maker"
          and f.get("fill_notional") is not None and f.get("fill_px") is not None
          and f.get("side") is not None and float(f["fill_notional"]) > 0]
    if not mk:
        return {"markout_bps": None, "n_fills": 0, "n_unmeasured": 0,
                "n_unusable": len(_unusable),
                "note": ("no maker fills" if not _unusable else
                         f"no USABLE maker fills; {len(_unusable)} row(s) lack side/price/notional")}
    # ★ A PENDING MARK IS NOT A ZERO MARKOUT. `mid_at_fill_plus_60s` is legitimately None while a
    # fill's +60s moment has not passed (top-up fills land ~16 min into a ~17-min anchor), and
    # this line used to call float() on it unguarded — the third instance tonight of "relax a
    # carrier's not_null and an unguarded consumer crashes" (fee_paid, realised_pnl, now this).
    # Excluding it from the mean is right; counting it is what keeps the exclusion visible.
    pairs, n_unmeasured = [], 0
    for f in mk:
        mark = f.get("mid_at_fill_plus_60s")
        if mark is None:
            n_unmeasured += 1
            continue
        sgn = 1.0 if f["side"] == "buy" else -1.0
        px = float(f["fill_px"])
        adverse = -sgn * (float(mark) - px) / px * BPS
        pairs.append((adverse, float(f["fill_notional"])))
    return {"markout_bps": (round(_wmean(pairs), 4) if pairs else None),
            "n_fills": len(pairs), "n_unmeasured": n_unmeasured,
            "n_unusable": len(_unusable),
            "measurement_complete": ((n_unmeasured == 0 and not _unusable and bool(pairs))
                                     if mk else None),
            "maker_notional": round(sum(w for _, w in pairs), 2),
            "sign_convention": "positive = adverse (mid moved against us 60s after the fill)",
            "caliber": "maker-only, per CHILD fill, notional-weighted, D=60s; fills whose +60s "
                       "mark is not yet observable are EXCLUDED and counted, never valued at 0"}


def m3_fill_rate(orders):
    """maker filled / maker intended on attempt_idx == 1 only."""
    # ★ UNKNOWN ROWS LEAVE BOTH SIDES, AND ARE COUNTED. `or 0.0` on the numerator reads "this
    # maker filled nothing" and on the denominator reads "we intended nothing" — the second is
    # the worse of the two, because it shrinks the denominator and RAISES the fill rate. A
    # readback outage would therefore improve M3, which is the wrong direction for a metric whose
    # job is to notice that the book is not reaching its target.
    _mk = [o for o in orders if o["order_type"] == "maker"]
    n_unknown = sum(1 for o in _mk if o.get("filled_notional") is None
                    or (int(o["attempt_idx"]) == 1 and o.get("intended_notional") is None))
    # ★ SCALE: a fill RATE compares magnitudes. Summing the signed values let buys and sells
    # cancel, so a perfectly balanced book could report a fill rate near zero while every order
    # filled completely — the metric would have been most wrong exactly when the book was most
    # neutral, which is the state we aim for.
    num = sum(abs(float(o["filled_notional"])) for o in _mk
              if o.get("filled_notional") is not None)
    den = sum(abs(float(o["intended_notional"])) for o in _mk
              if int(o["attempt_idx"]) == 1 and o.get("intended_notional") is not None)
    n_multi = 0
    seen = defaultdict(int)
    for o in orders:
        if o["order_type"] == "maker":
            seen[(o["anchor_ts"], o["symbol"])] += 1
    n_multi = sum(1 for v in seen.values() if v > 1)
    return {"fill_rate": round(num / den, 5) if den > 0 else None,
            "maker_filled_notional": round(num, 2),
            "maker_intended_attempt1_notional": round(den, 2),
            "n_maker_rows_unknown": n_unknown,
            "multi_maker_attempt_cases": n_multi,
            "definition": "denominator = intended_notional of attempt_idx==1 only (never summed "
                          "across attempts; attempt 2's intended is a residual)"}


def m4_turnover(orders, anchors):
    """TARGET-weight turnover is the gate (§3d vs 1466); realized reported alongside.

    ★★ [h] ROW-TYPE GUARD. Turnover is a statement about REBALANCING: `target_w`/`prev_w` only
    have meaning on a rebalance leg. A `protective_flatten` row is an exit, carries `prev_w:
    None`, and its `anchor_ts` is the TRIP time — so before this guard the function
      (a) raised TypeError on `float(None)`, taking PM.compute (the whole M1-M6 report) down with
          it on any tree containing a ladder row, i.e. every tree since 2026-07-26 12:17:31Z, and
      (b) would, once the None was made "safe", have opened one extra anchor bucket per trip.
          `n_anchors` is the annualisation DENOMINATOR of the §3d gate, so ladder rows adding 0 to
          the numerator and +1 each to the denominator make the gate read better than reality —
          and [b] writes one row per ladder order per attempt, multiplying it.
    ⇒ Excluding by TYPE fixes both at once, and is the only version that survives [b]. Making the
      None safe fixes only the crash and arms the dilution: the shallow error was hiding the deep
      one here exactly as -1111 hid the units error in the ladder.

    ★★ TWO DISTINCT REDS — DO NOT QUOTE ONE FOR THE OTHER (0C's correction, measured 2026-07-27):
      RED-1  CRASH, this guard removed and the code otherwise as it was:
             `TypeError: float() argument must be ... not 'NoneType'` — the comparison is never
             reached, so no gate value exists to be wrong. THIS is what the fixtures demonstrate.
      RED-2  DILUTION, only reachable under the COUNTERFACTUAL repair `float(prev_w or 0)`:
             clean ann=328.5 n_anchors=2  ->  with ghosts ann=219.0 n_anchors=3.
             No test exercises this, because the counterfactual is not the code — it is the
             reason the counterfactual is FORBIDDEN.
      Conflating them would let a later reader believe the dilution case is covered. It is not.

    ★ SIBLING GUARD, PRE-EXISTING AND LOAD-BEARING: `m1_effective_cost` carries the same
      `order_type in ("maker","topup_taker")` filter. Measured by removing it: a single ghost row
      flips `measurement_complete` True -> False (it has no `mid_at_anchor`, so it counts as an
      unmeasurable fill). Two guards, one property, and both must stay.
    """
    orders = [o for o in orders if o.get("order_type") in ("maker", "topup_taker")]
    tgt = 0.0
    by_anchor = defaultdict(dict)
    for o in orders:
        by_anchor[o["anchor_ts"]][o["symbol"]] = o          # one row per (anchor,symbol) suffices
    for ats, rows in by_anchor.items():
        tgt += sum(abs(float(r["target_w"]) - float(r["prev_w"])) for r in rows.values())
    gross_by_anchor = {a["anchor_ts"]: float(a["target_gross"]) for a in anchors}
    real = 0.0
    for o in orders:
        g = gross_by_anchor.get(o["anchor_ts"])
        if g:
            real += abs(float(o["filled_notional"] or 0.0)) / g
    n_anch = max(len(by_anchor), 1)
    per_year = 365 * 6
    return {"target_weight_turnover_total": round(tgt, 5),
            "realized_turnover_total": round(real, 5),
            "target_weight_turnover_annualised": round(tgt / n_anch * per_year, 1),
            "realized_turnover_annualised": round(real / n_anch * per_year, 1),
            "backtest_reference_annualised": BACKTEST_TURNOVER_ANN,
            "n_anchors": n_anch,
            "gate_uses": "target_weight (validates the signal pipeline); realized reported alongside"}


def m5_weight_fidelity(orders, anchors, readback):
    """Reconcile against the VENUE's reported positions, and split shortfall by terminal_reason."""
    rb = defaultdict(dict)
    for r in readback:
        rb[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
    gross_by_anchor = {a["anchor_ts"]: float(a["target_gross"]) for a in anchors}
    errs, drift = [], []
    # ★ THE THIRD CALLER OF ONE SHARED AGGREGATION. This was a hand-rolled copy of the same
    # signed-fills walk as §4-5b and §4-7, and the same sign defect lived in all three. The copy
    # was the generator; `reconcile.signed_fills_by_anchor` is its removal. What M5 does with the
    # result is still M5's own question (how far is the book from target) — only the input is
    # shared, because only the input was duplicated.
    import reconcile as _RC
    inferred = defaultdict(float)
    _by_anchor = _RC.signed_fills_by_anchor(sorted(orders, key=lambda x: x["anchor_ts"]))
    for _ats in sorted(_by_anchor):
        for _sym, _v in _by_anchor[_ats].items():
            inferred[_sym] += _v
        # after each anchor's rows are consumed we compare below
    for ats in sorted(rb):
        g = gross_by_anchor.get(ats)
        if not g:
            continue
        tgt = {o["symbol"]: float(o["target_w"]) for o in orders if o["anchor_ts"] == ats}
        for s, w in tgt.items():
            actual_w = rb[ats].get(s, 0.0) / g
            errs.append(abs(actual_w - w))
    # venue-vs-our-own-fills drift: the whole point of the readback
    last = max(rb) if rb else None
    if last is not None:
        for s, v in rb[last].items():
            drift.append(abs(inferred.get(s, 0.0) - v))
    reasons = defaultdict(float)
    n_short_unknown = 0
    for o in orders:
        # a shortfall is intended MINUS filled; if either side is unknown the shortfall is
        # unknown, and `or 0.0` would report a full-size shortfall (intended, minus a fabricated
        # zero fill) attributed to a terminal_reason that never claimed the trade did not happen
        if o.get("intended_notional") is None or o.get("filled_notional") is None:
            n_short_unknown += 1
            continue
        # ★ SCALE on both sides: a shortfall is "how much less did we trade than we meant to".
        # Mixing a magnitude with a signed value made every SELL report a shortfall of
        # |intended| + |filled| — larger than the order itself — attributed to whatever
        # terminal_reason that row happened to carry.
        short = abs(float(o["intended_notional"])) - abs(float(o["filled_notional"]))
        if short > 1e-9:
            reasons[o["terminal_reason"]] += short
    return {"mean_abs_weight_error": round(sum(errs) / len(errs), 6) if errs else None,
            "max_abs_weight_error": round(max(errs), 6) if errs else None,
            "n_comparisons": len(errs),
            "venue_vs_inferred_drift_usd_max": round(max(drift), 6) if drift else None,
            "shortfall_notional_by_terminal_reason": {k: round(v, 2)
                                                      for k, v in sorted(reasons.items())},
            "n_rows_shortfall_unknown": n_short_unknown,
            "reconciled_against": "position_readback (venue), NOT our own fills"}


def m6_funding(funding):
    tot = sum(float(f["funding_paid"]) for f in funding)
    per_sym = defaultdict(float)
    for f in funding:
        per_sym[f["symbol"]] += float(f["funding_paid"])
    return {"funding_paid_total_usd": round(tot, 4), "n_settlements": len(funding),
            "sign_convention": "positive = we RECEIVED funding",
            "top_contributors": dict(sorted(per_sym.items(), key=lambda kv: -abs(kv[1]))[:5])}


def m6_sign_consistency(funding):
    """§3f (0C re-ruling): per-settlement SIGN agreement between the cash actually paid/received
    and the sign implied by position x rate. >5% disagreement = a WIRING ERROR.

    ★ This is a bug detector, not an alpha test, and the two need different tools. The original
      wording ("cumulative significantly negative") had no threshold and leaned on human judgement,
      and it could not fire until enough days had accumulated. A wiring error is a large, persistent,
      deterministic effect -- asking whether it is "statistically significant" is the wrong question.
      Mechanical, no statistics, live from day one.
    """
    n_bad = 0
    n = 0
    n_no_rate = 0
    bad_examples = []
    for f in funding:
        # ★ `funding_rate` is no longer not_null: the public rate is matched to the settlement
        # within a 5-minute tolerance and legitimately misses. `float(None)` here would be the
        # fourth "relax a carrier and an unguarded consumer crashes" of the night, and this one
        # sits inside the §3f WIRING detector — the check whose failure mode is the loudest.
        # A settlement with no matched rate is UNVERIFIABLE, which is neither agreement nor
        # disagreement, so it leaves both the numerator and the denominator and is counted.
        if f.get("funding_rate") is None:
            n_no_rate += 1
            continue
        pos = float(f["position_notional_at_settlement"])
        rate = float(f["funding_rate"])
        paid = float(f["funding_paid"])
        implied = -pos * rate                       # long a negative-funding name RECEIVES
        if abs(implied) < 1e-12 or abs(paid) < 1e-12:
            continue                                # no sign to compare
        n += 1
        if (implied > 0) != (paid > 0):
            n_bad += 1
            if len(bad_examples) < 5:
                bad_examples.append({"symbol": f["symbol"], "settlement_ts": f["settlement_ts"],
                                     "position": pos, "rate": rate, "paid": paid,
                                     "implied": round(implied, 8)})
    frac = (n_bad / n) if n else 0.0
    return {"n_compared": n, "n_sign_mismatch": n_bad, "mismatch_frac": round(frac, 5),
            "n_unverifiable_no_rate": n_no_rate,
            "limit": 0.05, "wiring_error": bool(frac > 0.05), "examples": bad_examples,
            "note": ("bug detector, not an alpha test — a wiring error is a large deterministic "
                     "effect, so no statistical test is appropriate; active from day 1")}


def stoploss_inputs(navs):
    if not navs:
        return {"available": False, "note": "no daily_nav rows -- stop-losses NOT auditable"}
    navs = sorted(navs, key=lambda r: r["day"])
    # ★★ TWO FABRICATIONS ON ONE LINE, AND BOTH FED THE STOP-LOSSES.
    # It was: float(r["realised_pnl"]) + float(r.get("unrealised_pnl") or 0.0)
    #   - realised_pnl was not_null, so every row carried a defaulted 0.0 and this "P&L" was
    #     the unrealised half wearing a full name;
    #   - `or 0.0` then turned a missing unrealised into zero — and a zero LOSS makes the
    #     drawdown gate easier to pass, i.e. absence bending the gate toward "fine", which is
    #     the one direction that must never happen.
    # Removing the not_null (2026-07-26) turned the silent wrong answer into a TypeError on the
    # first TESTNET anchor. A day we cannot price is now DROPPED and COUNTED, never valued at 0.
    usable, skipped = [], []
    for r in navs:
        real, unreal = r.get("realised_pnl"), r.get("unrealised_pnl")
        g = r.get("target_gross")
        if real is None or unreal is None or not g:
            # ★ `is None` for the P&L terms, falsy for the denominator. A first draft used
            # `v is None or v == 0` for all three and reported a perfectly good
            # `unrealised_pnl: 0.0` as missing — the mirror image of the bug being fixed here:
            # one direction turns absence into zero, the other turns zero into absence.
            miss = [k for k, v in (("realised_pnl", real), ("unrealised_pnl", unreal))
                    if v is None]
            if not g:
                miss.append("target_gross")
            skipped.append({"day": r.get("day"), "missing": miss})
            continue
        usable.append((r["day"], (float(real) + float(unreal)) / float(g)))
    if not usable:
        return {"available": False, "n_days": len(navs), "n_priced_days": 0,
                "unpriced_days": skipped,
                "note": ("daily_nav rows exist but NONE can be priced (realised and/or unrealised "
                         "P&L absent) — the drawdown stop-losses have no input. This is reported "
                         "as unavailable rather than as a drawdown of 0.")}
    daily_ret = [x for _, x in usable]
    cum, peak, maxdd = 0.0, 0.0, 0.0
    for r in daily_ret:
        cum += r
        peak = max(peak, cum)
        maxdd = min(maxdd, cum - peak)
    return {"available": True, "n_days": len(navs), "n_priced_days": len(usable),
            "unpriced_days": skipped,
            # ★ the caller must be able to see that the verdict covers only part of the window
            "coverage_complete": not skipped,
            "worst_day_pct_of_target_gross": round(min(daily_ret) * 100, 4),
            "cumulative_pct_of_target_gross": round(cum * 100, 4),
            "max_drawdown_pct_of_target_gross": round(maxdd * 100, 4),
            "note": "denominated in TARGET gross per §9-F12; unpriced days are EXCLUDED, not "
                    "counted as flat"}


# ------------------------------------------------------------------ driver
def compute(root, days=None, verbose=True):
    avail = PL.available_days(root)
    if days:
        avail = avail[-days:]
    data = PL.read_range(root, avail)
    regime_by_anchor = {a["anchor_ts"]: a["regime_at_anchor"] for a in data["anchors"]}
    out = {
        "schema_version": PL.SCHEMA_VERSION,
        "pilot_metrics_sha256": self_hash(),
        "days": avail,
        "n_days": len(avail),
        "M1_effective_cost": m1_effective_cost(data["orders"], regime_by_anchor),
        "M2_markout": m2_markout(data["fills"]),
        "M3_fill_rate": m3_fill_rate(data["orders"]),
        "M4_turnover": m4_turnover(data["orders"], data["anchors"]),
        "M5_weight_fidelity": m5_weight_fidelity(data["orders"], data["anchors"],
                                                 data["position_readback"]),
        "M6_funding": m6_funding(data["funding"]),
        "M6_sign_consistency": m6_sign_consistency(data["funding"]),
        "STOPLOSS_inputs": stoploss_inputs(data["daily_nav"]),
    }
    # ★ regime-coverage blind spot (team-lead ruling)
    seen = set(out["M1_effective_cost"]["by_regime"])
    n_unknown = out["M1_effective_cost"]["by_regime"].get("unknown", {}).get("n_filled_orders", 0)
    missing = sorted({"calm", "normal", "stress"} - seen)
    out["regime_coverage"] = {
        "regimes_present": sorted(seen), "regimes_missing": missing,
        "stress_present": "stress" in seen,
        "n_orders_with_unknown_regime": n_unknown,
        "unknown_regime_warning": (None if not n_unknown else
                                   f"{n_unknown} filled orders carry regime='unknown' — the "
                                   "classifier did not label their anchor. They are included in "
                                   "the overall c but cannot be stratified."),
        "blind_spot_warning": (None if "stress" in seen else
                               "STRESS SAMPLE MISSING — the c reading above has a known blind "
                               "spot. Adverse selection is regime-dependent, so sample COUNT is "
                               "not regime COVERAGE: more days in one regime cannot substitute "
                               "for a stress observation. Do NOT read the overall c as if it "
                               "covered stress conditions."),
    }
    if verbose:
        m1 = out["M1_effective_cost"]
        print(f"[pilot_metrics] sha256={out['pilot_metrics_sha256'][:16]}… days={len(avail)}",
              flush=True)
        print(f"  M1 c = {m1['c_bps_overall']} bps/side  (n={m1['n_filled_orders']} filled orders)",
              flush=True)
        for r, v in m1["by_regime"].items():
            print(f"       regime {r:7s}: c = {v['c_bps']} bps  (n={v['n_filled_orders']})",
                  flush=True)
        if out["regime_coverage"]["blind_spot_warning"]:
            print(f"  ⚠ {out['regime_coverage']['blind_spot_warning']}", flush=True)
        print(f"  M2 markout = {out['M2_markout']['markout_bps']} bps "
              f"({out['M2_markout']['n_fills']} maker child fills)", flush=True)
        print(f"  M3 fill rate = {out['M3_fill_rate']['fill_rate']}", flush=True)
        print(f"  M4 turnover (target) = {out['M4_turnover']['target_weight_turnover_annualised']} "
              f"vs backtest {BACKTEST_TURNOVER_ANN}", flush=True)
        print(f"  M5 mean |w err| = {out['M5_weight_fidelity']['mean_abs_weight_error']}", flush=True)
        print(f"  M6 funding = {out['M6_funding']['funding_paid_total_usd']} USD", flush=True)
        sc = out["M6_sign_consistency"]
        print(f"  M6 sign-consistency: {sc['n_sign_mismatch']}/{sc['n_compared']} mismatched "
              f"({sc['mismatch_frac']:.1%}) — wiring_error={sc['wiring_error']}", flush=True)
        print(f"  STOPLOSS inputs available = {out['STOPLOSS_inputs']['available']}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(MA, "exports", "live", "pilot_log"))
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--self-hash", action="store_true")
    a = ap.parse_args()
    if a.self_hash:
        print(self_hash())
        raise SystemExit(0)
    res = compute(a.root, a.days)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"-> {a.out}", flush=True)
