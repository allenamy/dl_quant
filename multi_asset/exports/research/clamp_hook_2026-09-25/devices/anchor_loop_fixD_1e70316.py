"""The anchor loop: every 4h, data -> signal -> execute -> log. The assembled machine.

ORDER OF OPERATIONS AT ONE ANCHOR (each step can refuse; refusal is a defined state):
    0. guards        drift gate / day budget / factor version / data staleness   -> BLOCK if red
    1. anchor        capture mid_at_anchor for every symbol (before any order exists)
    2. signal        four legs -> unit-gross market-neutral target (split-path caliber)
    3. freshness     ★ stale-signal ladder (below)
    4. execute       passive maker k=900s -> mandatory IOC top-up
    5. log           orders / fills / anchors rows (schema v2), funding ledger pull
    6. watchdog      evaluate §4 conditions on what just happened
    7. report        daily report + mirror + (when configured) email

★ THE STALE-SIGNAL LADDER — the answer to "what if the server dies"
The DL preds come from a pipeline that can fail (today: server-computed; later: local inference —
either can break). Failure means NO NEW signal, not a WRONG signal, and the book is market-neutral
at ~3.3% margin, so holding is survivable — but not indefinitely: weights drift from optimal and
the funding leg stops tracking crowding. Pre-registered, mechanical, no judgement at 4am:

    fresh (age < 1 anchor)          TRADE normally
    1..5 anchors stale              HOLD    keep positions, no new orders, alarm once
    6..8  anchors stale (>=24h)     DERISK  to 50% of the PRE-STALE gross (reduce-only)
    9..11 anchors stale (>=36h)     DERISK  to 25% of the PRE-STALE gross (reduce-only)
    >=12 anchors stale  (>=48h)     FLATTEN exit entirely; a two-day-blind book is not a book

    ★ The ladder is a TARGET-FRACTION TABLE, not a repeated multiplier. Audit finding: a first
    draft halved the CURRENT positions at every stale anchor — which compounds to ~1.6% by
    anchor 11, i.e. an undocumented exponential liquidation paying 6 IOC round-trips for what
    one planned cut should cost. Targets are fractions of the gross SNAPSHOTTED when the stale
    episode began, so re-running an anchor at the same stage is a no-op (idempotent).

Why HOLD and not instant flatten: flattening costs a full round-trip of fees+slippage; alpha
decays over ~4h but the market-neutral shell holds. One missed anchor is noise; the ladder only
escalates when staleness stops looking like a hiccup and starts looking like an outage.
De-risking uses REDUCE-ONLY orders exclusively, so it composes with the watchdog's halt.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
import math
import time
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
for d in ("live", "signal"):
    sys.path.insert(0, os.path.join(_REPO, d))

import book_config as BC      # noqa: E402
import per_name_stop as PNS   # noqa: E402  逐名止损条款 cf40ea21(2026-08-20 用户裁定全面启用)
import external_book as EXT   # noqa: E402  外部书适配器(DESIGN_wide_live_deployment_2026-08-22 §1)
import reject_rate as RR      # noqa: E402  场所拒单率: 以场所应答的首次 maker 单为分母(E-0905-H)
import beta_overlay as BO     # noqa: E402  M3 BTC-beta 叠加腿(PREREG_m3_beta_overlay 24c3f803f; 执行书上算 β)  # M3-LINE
import durable_io as DIO      # noqa: E402  B-2: state writes land byte for byte or raise (DESIGN_executor_durable_state_2026-09-25)

# ★ THE BAND IS A POLICY NUMBER AND SAYS SO. 3% of gross is the lead's figure; no measurement
#   produced it and it must not be quoted as if one had. The two live anchors so far read +0.99%
#   and -6.92%, so it sits between them by construction rather than by calibration.
NEUTRALITY_ALARM_FRAC = 0.03


def neutrality_from_snapshot(snap):
    """Realised neutrality, read off the VENUE's own positions. Pure; returns row fields.

    ★★★ On 2026-08-01's second anchor the realised book came out at -6.92% of gross (-12% of
        equity) while INTENT was +40.76 — execution alone put ~-298 USDT of unchosen direction on
        the book — and **nothing said so**. It was found by hand in a post-mortem. A quantity
        nobody computes is a quantity nobody can be alarmed about.
    ★ FROM THE SNAPSHOT, NOT FROM TARGETS: computing it from intent would report the property we
      ASSUMED rather than the one we ACHIEVED.
    """
    pn = (snap or {}).get("positions_notional") or {}
    net = float(sum(pn.values()))
    grs = float(sum(abs(v) for v in pn.values()))
    eq = (snap or {}).get("equity")
    return {"venue_net_usdt": round(net, 6),
            "venue_gross_usdt": round(grs, 6),
            "net_over_gross": (round(net / grs, 6) if grs else None),
            "net_over_equity": (round(net / float(eq), 6) if eq else None),
            "neutrality_caliber": (
                "signed sum of the venue's own position notionals at the end-of-anchor read; a "
                "SNAPSHOT, not a P&L and not a forecast. net_over_gross is the "
                "leverage-independent reading — use it to compare across anchors.")}


def neutrality_alarm_text(row, order_rows, rebalance_id, band=None):
    """The page, or None inside the band. Names WHAT IS MISSING, not only how much.

    ★ "-6.9%" sends the reader back to the ledger; "short by 6.9%, the BUY side is deficient, and
      these are the biggest buys that never filled" is a diagnosis. Measured on that anchor the
      maker leg filled 73% buy-side against 97% sell-side — the deficient side and its unfilled
      names ARE the story.
    ★ Inside the band it returns None: the first anchor read +0.99%, and a warning that fires
      every anchor is furniture. Silence is about the PAGE; the measurement is recorded either way.
    """
    band = NEUTRALITY_ALARM_FRAC if band is None else band
    r = row.get("net_over_gross")
    if r is None or abs(float(r)) <= band:
        return None
    side = "buy" if float(r) < 0 else "sell"
    mine = [o for o in (order_rows or [])
            if o.get("rebalance_id") == rebalance_id
            and o.get("order_type") == "maker"
            and str(o.get("side", "")).lower() == side
            and not o.get("filled_notional")]
    mine.sort(key=lambda o: -abs(float(o.get("intended_notional") or 0.0)))
    names = [f"{o['symbol']}(${abs(float(o.get('intended_notional') or 0)):.0f})"
             for o in mine[:6]]
    return (f"★ 收锚不中性: net/gross {float(r):+.2%} (带 ±{band:.0%}), "
            f"net {row.get('venue_net_usdt')} USDT, net/equity {row.get('net_over_equity')}. "
            f"欠缺侧 = {side.upper()} ({len(mine)} 个 maker 单未成交). "
            f"该侧最大的未成交: {', '.join(names) if names else '(无)'}. "
            f"这是**执行**造成的方向, 与规划残差(INTENT)是两件事 —— 对照 anchors 行的 "
            f"weights 与 target_gross.")


def neutrality_price(row, order_rows, rebalance_id):
    """What it would COST to top the book up to neutral, at THIS anchor's own measured taker cost.

    ★★★ MEASUREMENT ONLY — NOTHING ACTS ON THIS (lead's ruling 2026-08-01). The auto neutrality
        top-up was downgraded from "do it" to "measure first, rule later" after the forensics
        overturned its premise: the venue's -6.92% was not abandoned orders ($0.33 in total) but
        maker fill asymmetry (buy 73% vs sell 97%), so topping up would pay the taker cost to
        correct a symptom of the same cause. The ruling needs 5-10 anchors of this number first.

    ★ THE ARITHMETIC IS THE EASY PART; THE CALIBER IS THE POINT.
      price = |venue net| x (this anchor's measured taker cost on the DEFICIENT side).
      Measured on the 16:01Z anchor: net -257.04 (short) => we would BUY 257.04, and this anchor's
      buy-side taker legs cost 54.87bps all-in (5.00 fee + 49.87 adverse) => ~1.41 USDT.

    ★★ AND IT IS A LOWER BOUND, WHICH MUST TRAVEL WITH THE NUMBER. The 49.87bps was paid pushing
       387 USDT of buys into a one-sided market; buying another 257 pushes the same way. The cost
       of the increment is not the cost of the average, and this reports the average.

    ★★★ IT REFUSES TO SUBSTITUTE THE OTHER SIDE. On 16:01Z the SELL-side taker cost rests on ONE
        fill of 25.85 USDT, and on 12:00Z there were no sell-side taker fills at all. A missing
        measurement is reported as missing — `n_fills_basis`/`notional_basis` are in the record so
        a reader can see whether the bps rests on ten fills or on one, and `price_usdt` is None
        rather than borrowing the side we did not trade. The cheapest way to invent a comforting
        number here would be to average the two sides; the sides are not exchangeable.
    """
    net = row.get("venue_net_usdt")
    if net is None:
        return None
    net = float(net)
    # short book (net < 0) => the deficient side is BUY: we must buy to come back to flat.
    side = "buy" if net < 0 else "sell"
    need = abs(net)
    legs = [o for o in (order_rows or [])
            if o.get("rebalance_id") == rebalance_id
            and o.get("order_type") == "topup_taker"
            and abs(float(o.get("filled_notional") or 0.0)) > 0
            and ((float(o["filled_notional"]) > 0) == (side == "buy"))]
    notional = sum(abs(float(o["filled_notional"])) for o in legs)
    # ★★ round 13 (review R12-COST-COVERAGE): a fill WITHOUT a price has an UNKNOWN adverse cost — it is not a
    #    zero-cost fill. The bps is measured over the PRICED fills only (their fee + their signed adverse); the
    #    unpriced fills are reported beside it (count, notional, their fee), and with no priced fill the bps
    #    is None, never 0.
    # ★★ round 14 (review R13-COST-COMPLETENESS): a fill is MEASURED only when its price is usable (finite, positive
    #    avg AND mid) AND its fee is known (fee_paid not None, finite). "priced" alone is not "measured": a row the
    #    fee writer left at fee_paid=None has an unknown cost, and `or 0.0` read it as a free fill. Buckets:
    #    unpriced (no usable price) / fee-unknown (priced, fee None) / measured; the bps rests on the measured set.
    def _pos(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if (v == v and v not in (float("inf"), float("-inf")) and v > 0) else None

    def _fee(o):
        f = o.get("fee_paid")
        if f is None:
            return None
        # ★ round 14b (verified in apply_commission_to_rows): when the commissions were not all in USDT and no
        #   conversion completed, the writer stores the RAW mixed-asset sum as a number with fee_all_usdt=False —
        #   that is not a known USDT fee; only an all-USDT fee or a completed conversion counts as measured
        if o.get("fee_all_usdt") is False and not o.get("fee_conversion"):
            return None
        try:
            v = float(f)
        except (TypeError, ValueError):
            return None
        return v if (v == v and v not in (float("inf"), float("-inf"))) else None
    priced = [o for o in legs if _pos(o.get("avg_fill_px")) and _pos(o.get("mid_at_anchor"))]
    measured = [o for o in priced if _fee(o) is not None]
    notional_priced = sum(abs(float(o["filled_notional"])) for o in priced)
    notional_measured = sum(abs(float(o["filled_notional"])) for o in measured)
    fee_measured = sum(_fee(o) for o in measured)
    adverse = 0.0
    for o in measured:
        px, mid = _pos(o.get("avg_fill_px")), _pos(o.get("mid_at_anchor"))
        sgn = 1.0 if float(o["filled_notional"]) > 0 else -1.0
        adverse += sgn * (px - mid) / mid * abs(float(o["filled_notional"]))
    n_priced, n_measured = len(priced), len(measured)
    bps = (1e4 * (fee_measured + adverse) / notional_measured) if notional_measured else None
    return {
        "deficient_side": side,
        "taker_notional_needed_usdt": round(need, 4),
        "measured_taker_bps_same_side": (round(bps, 4) if bps is not None else None),
        "measured_over": ("MEASURED fills only — fills with a usable price (finite positive avg_fill_px and mid) AND a "
                          "known fee (fee_paid not None); an unpriced or fee-unknown fill is NOT zero-cost. Round 13/14 "
                          "changed this key's denominator from every fill to the measured fills — see the "
                          "coverage fields; mixed anchors read differently from before."),
        "n_fills_basis": len(legs),
        "n_fills_priced": n_priced,
        "n_fills_unpriced": len(legs) - n_priced,
        "n_fills_fee_unknown": n_priced - n_measured,
        "n_fills_measured": n_measured,
        "notional_basis_usdt": round(notional, 4),
        "notional_priced_usdt": round(notional_priced, 4),
        "notional_measured_usdt": round(notional_measured, 4),
        "unpriced_notional_usdt": round(notional - notional_priced, 4),
        "fee_unknown_notional_usdt": round(notional_priced - notional_measured, 4),
        "coverage_priced": (round(notional_priced / notional, 4) if notional else None),          # NOTIONAL coverage of usable prices
        "coverage_measured_notional": (round(notional_measured / notional, 4) if notional else None),
        "coverage_measured_count": (round(n_measured / len(legs), 4) if legs else None),
        "price_usdt": (round(need * bps / 1e4, 4) if bps is not None else None),
        "price_is_lower_bound": True,
        "caliber": (
            "|venue net| x this anchor's OWN realised taker cost (fee + signed adverse) on the "
            "deficient side, over the MEASURED fills only (`notional_measured_usdt`; usable price and "
            "known fee — round 13/14). MEASUREMENT ONLY — no top-up is sent. A LOWER BOUND: the measured "
            "bps was paid moving `notional_measured_usdt` into that side, and topping up pushes the "
            "same way, so the marginal cost exceeds this average. `price_usdt` is None when this "
            "anchor traded no taker volume on that side — the opposite side is NOT substituted, "
            "because the two sides are not exchangeable (16:01Z: buy 54.87bps on 10 fills vs "
            "sell 20.08bps on a single 25.85 USDT fill)."),
    }
import fapi_source as FS      # noqa: E402
import legs as LG             # noqa: E402
import universe as UNI        # noqa: E402
import reduce_only_reject as RO   # noqa: E402

# ★ `ANCHOR_HOURS = (0,4,8,12,16,20)` used to live here as a literal, and identically in
# ops/dryrun_ledger.py and config/book.json. The schedule and the lateness tolerance are the two
# numbers the ledger and this gate must agree on; both now come from live/book_config.py.


def _anchor_seconds() -> int:
    """Spacing between anchors, DERIVED from the schedule instead of written down a second time.
    The staleness ladder counts age in whole anchors; if the schedule changed and a hardcoded
    14400 did not, every rung would fire at the wrong age while looking perfectly healthy."""
    hrs = sorted(BC.anchor_hours())
    gaps = {b - a for a, b in zip(hrs, hrs[1:])} | {24 - hrs[-1] + hrs[0]}
    if len(gaps) != 1:
        raise ValueError(f"anchors_utc is not evenly spaced ({hrs}); the staleness ladder counts "
                         f"age in whole anchors and has no meaning on an uneven schedule")
    return int(gaps.pop()) * 3600


ANCHOR_S = _anchor_seconds()
STALE_HOLD_ANCHORS = 1
STALE_DERISK_ANCHORS = 6                       # >=24h without a fresh signal
STALE_FLATTEN_ANCHORS = 12                     # >=48h
DERISK_TABLE = ((9, 0.25), (6, 0.50))          # (min_age_anchors, target frac of PRE-STALE gross)


def _dt_day_start_ms(day: str) -> int:
    """00:00:00Z of a YYYYMMDD day, in ms. The income window must start at the UTC day boundary,
    not 24h before now — otherwise a row labelled `day` sums a window that straddles two days."""
    import calendar
    return int(calendar.timegm(time.strptime(day, "%Y%m%d")) * 1000)


def derisk_target_frac(age_anchors: float) -> float:
    for min_age, frac in DERISK_TABLE:
        if age_anchors >= min_age:
            return frac
    return 1.0

STATE_PATH = os.environ.get("LIVE_LOOP_STATE",
                            os.path.join(_REPO, "state", "loop_state.json"))
PREDS_PATH = os.environ.get("LIVE_PREDS_PATH",
                            os.path.join(_REPO, "state", "preds_latest.json"))
# ★ Same env-override pattern as the other state paths — and for the same reason in reverse:
# without it, a genuinely engaged kill switch pollutes every test (production state leaking INTO
# tests), and a test cannot exercise the switch without touching the real one. The production
# entry point never sets this var, so the canonical path is what actually runs.
# share of an anchor's orders lost to throttling before it becomes a finding. Not zero: a single
# throttled name is noise. Not high: this is the one drift no stop-loss covers.
RATE_LIMIT_SKIP_FRAC = 0.05
# share of an anchor's orders the VENUE refused before it becomes a finding. Same reasoning as the
# line above and the same number, deliberately: both describe "the book did not reach its target
# and no stop-loss will say so". Measured 2026-08-02 04:00Z: 17/109 = 15.6% refused, silent, and
# §4-5e flattened the book 18 minutes later over a hole those refusals were 93% of.
# ★ A POLICY NUMBER. One refusal is noise; at 5% of an anchor the book is materially short.
# ★★ SINCE 2026-09-05 (E-0905-H) THIS APPLIES TO THE NON-RECOVERABLE REFUSALS ONLY (-1111/-4164/
#    -1102: our own malformed orders), on the denominator the venue answered. -5022 (post-only
#    would have crossed) is recovered by the requote + taker top-up and has its own meter below.
VENUE_REJECT_FRAC = 0.05
# Post-only refusal share (-5022, first attempt, per name) above which one anchor is a HIGH page.
# ★ A POLICY NUMBER carried over from E-0903-D's tracking rule (">40% 持续 ⇒ 升级"), now applied
#   to the TRUE rate: refused-at-attempt-1 / (refused-at-attempt-1 + rested-at-attempt-1).
#   Measured 2026-08-22..09-05 (85 anchors): mean 25-27% of names, max 42.4% (09-05 08Z). The
#   ratio the old alarm printed excluded rested makers and tracked the min-notional skip count.
POST_ONLY_REFUSAL_ESCALATE = 0.40

# ★★★ THE TWO RESHAPE SWITCHES (lead's ruling 2026-08-01, effective 20:00Z anchor).
# They restore the two properties a WITHHOLD destroys, and they are TWO switches because they
# carry TWO justifications that must be revertible one at a time:
#   REDEMEAN — neutrality is the foundation of the risk argument. Order-preserving (a uniform
#              shift preserves rank), so restoring it costs no alpha.
#   RESCALE  — leverage is a RISK DECISION and must not become a by-product of tradability.
# ★ Deliberately module constants, not config keys. `config/book.json["weights"]` spent weeks
#   with ZERO readers while every record cited it as the operating config; a constant with one
#   call site, exercised by `tests_book_reshape`, cannot develop that gap. Reverting is a
#   one-line edit, which is the property "independently revertible" actually asks for.
# ★ RESCALE-without-REDEMEAN is refused at runtime (`strict=True` below), because scaling a still
#   tilted book UP grows the net in proportion — strictly worse than leaving the defect alone.
RESHAPE_REDEMEAN = True
RESHAPE_RESCALE = True


def withhold_pop(target, held, untradable, floors=None, dust_out=None):
    """Pass 1 of the withhold: drop the untradable names we do NOT hold. Mutates `target`.

    ★ FIX PACKAGE D (dust pop, quant_research DESIGN_dust_pop_before_reshape_2026-09-25, lead-approved): a held residual BELOW the
      name's venue min notional (`floors[s]`) counts as NOT held. The planner can never close it (binance_executor.plan: |delta| <
      min_notional ⇒ skipped_min_notional, exits included), so economically it is flat; before this it went to the clamp AFTER the
      reshape and its reshape target was not re-absorbed (+2,464 USDT net long at 2026-09-25 08Z, the stop-cooldown trio held as
      ~1 USDT dust while the producer kept shorting them). Strictly below the floor; no floor for the name (or floors None) ⇒ the
      exact-zero rule as before. A popped name leaves the target, so the planner (which iterates the target only) gives it no row and
      no order: it cannot be opened (the cooldown's intent) and its dust stays where it is. `dust_out` (a list) collects the names
      popped BECAUSE of the floor, for the report.

    Returns the popped symbols. Nothing to close and we may not open, so the name simply leaves
    the book — which is precisely why the remainder must be reshaped afterwards.

    ★ A NAMED FUNCTION BECAUSE THE TEST CALLS IT. `tests_orphan_position` used to lift this rule
      out of the source by string offsets and `exec` it; splitting the loop in two made the
      injected anchor `if cur == 0.0:` match twice and the lift silently span the reshape block.
      A test that reaches into a file by byte offset breaks on edits that have nothing to do with
      it — and worse, can keep passing while spanning code it never meant to execute.
    """
    popped = []
    for s_ in untradable:                       # scored, but withheld by the venue
        h_ = float((held or {}).get(s_, 0.0) or 0.0)
        fl_ = (floors or {}).get(s_)
        dust_ = (h_ != 0.0 and fl_ is not None and float(fl_) > 0.0 and abs(h_) < float(fl_))   # NaN held ⇒ False ⇒ clamp (unknown is not dust)
        if h_ == 0.0 or dust_:
            target.pop(s_, None)
            popped.append(s_)
            if dust_ and dust_out is not None:
                dust_out.append(s_)
    return popped


def apply_withhold_and_reshape(target, held, untradable, sizing_gross,
                               floors_usdt=None, floors_source="not supplied",
                               redemean=None, rescale=None, force_flat=()):
    """POP -> RESHAPE -> CLAMP, in that order. Mutates `target`; returns (disposition, report).

    ★★★ W9 (2026-09-13, DESIGN_stopped_long_flatten_2026-09-13): `force_flat` = names whose target a CLAUSE requires to be
        EXACTLY 0 (the per-name stop, cf40ea21: "目标归零 ⇒ 既有 flatten_only 通道"). They used to be zeroed by the CALLER before
        this function — and step 2 then re-demeaned the WHOLE target, those zeros included, moving every name by the same
        shift a = −sizing·mean/L1. The clamp saw a, not 0: a stopped holding with the sign of a became `add_blocked` (pinned at
        its position) or `reduced` (cut to ≈ a). Measured on the live ledger 2026-08-20..09-12: 157 stopped-and-held
        instances, 144 longs pinned or merely reduced, and — before the external book, when a < 0 — shorts instead. So the
        order this function owns now includes them: POP (an unheld force_flat name is popped like any unheld untradable) →
        the HELD force_flat names leave the reshape population → RESHAPE the rest → those names go back at exactly 0.0 →
        CLAMP (target 0 ⇒ flatten_only, reduce-only, never past flat). A force_flat name is untradable by definition.
        Empty (the default) ⇒ bit-for-bit the previous behaviour. `net_before` is unchanged by construction (a zero adds
        nothing to Σw); only the mean's divisor and the L1 norm lose the stopped names, so the rest of the book is neutral and
        at the sizing gross over the names that still trade.

    ★★★ THE ORDER IS THE DESIGN, WHICH IS WHY THE THREE STEPS LIVE IN ONE NAMED FUNCTION RATHER
        THAN AS THREE STATEMENTS IN `run_anchor`. A caller can get the sequence wrong; a caller
        cannot get this wrong without editing it.
        A POP is a SHAPE change — a name leaves the book and the remainder is no longer the thing
        we decided. A CLAMP is a VENUE CONSTRAINT on a name that STAYS. So:
          · reshaping BEFORE the clamps means the clamp comparisons run on the FINAL numbers — a
            `reduced` name cannot be pushed back above its own position by the rescale and quietly
            become an ADD, which is precisely what the clamp exists to prevent.
          · reshaping AFTER them would normalise the venue's constraint away — taking a name the
            venue pinned at `cur` and scaling it to something else. That is the one thing we may
            not do, and it would look like success in every aggregate.

    ★★ THE LIMIT, STATED RATHER THAN PAPERED OVER: when a HELD untradable exists, the clamps
       re-break neutrality by exactly the pinned amount. That residue is VENUE-FORCED, it is
       reported as `clamped_after_reshape`, and it is NOT absorbed into the other names. Absorbing
       it would mean tilting ~100 alpha weights to offset one stuck coin — a hedging decision
       nobody has made. Today this is unexercised: all three live anchors popped only (ARKM /
       PORTAL, never held). Unexercised is not impossible, which is why it is written down.

    THE DEFECT IT REPAIRS (measured, 2026-08-01 12:00Z and 16:01Z): the pop triggers a
    RE-SUMMATION OF GROSS but never a RE-DEMEANING. `plan()` computes `target_w = tgt / Σ|tgt|`,
    so sum|w| self-heals to exactly 1.000000 while sum(w) keeps the popped name's weight.
    16:01Z: sum(w) = +0.0096 on a 4246.04 book = **+40.76 USDT of direction nobody chose**, and
    the book deployed 4246.04 against the 4278.81 sizing had decided. Of the two properties, the
    one that self-heals is the camouflage for the one that does not.
    """
    redemean = RESHAPE_REDEMEAN if redemean is None else redemean
    rescale = RESHAPE_RESCALE if rescale is None else rescale
    g = float(sizing_gross)
    clamp = {"reduced": [], "add_blocked": [], "flatten_only": [], "popped": []}
    _force = sorted(set(force_flat or ()))
    if _force and set(_force) - set(untradable):
        untradable = list(untradable) + sorted(set(_force) - set(untradable))   # a force_flat name is untradable

    # ★ E6 (EXE-03): the book's net AS COMPOSED, before anything leaves it — so the reshape report can say how much of the
    #   pre-reshape net is the producer's own and how much the removed names took away (the alarm used to blame the removed names
    #   for all of it; 09-13 12Z the producer's book was itself −8.46% of its gross and the 11 withheld names were +0.80%).
    _net_composed = float(sum(float(v or 0.0) for v in target.values()))
    # ── 1. the UNHELD untradables: pop. This is the shape change. ──────────────────────────
    _dust_popped = []
    clamp["popped"] = withhold_pop(target, held, untradable, floors=floors_usdt, dust_out=_dust_popped)   # fix package D: dust ⇒ pop
    # ── 1b. W9: the HELD force_flat names still in the target leave the reshape population ───────
    _flat_out = [s_ for s_ in _force if s_ in target]
    _flat_out_net = float(sum(float(target.get(s_) or 0.0) for s_ in _flat_out))
    for s_ in _flat_out:
        target.pop(s_)

    # ── 2. restore what the pop destroyed ──────────────────────────────────────────────────
    rs = None
    # ★ NOT `and (redemean or rescale)`. With both switches off the reshape is a no-op — but it
    #   must still RUN, because its report is how "we declined to correct 120 USDT" reaches the
    #   ledger. Gating the call on the switches makes a disabled correction indistinguishable from
    #   a book that never needed one, which is the exact shape this whole seam exists to kill.
    if target and g > 0:
        import numpy as _np
        syms = sorted(target)                  # deterministic: the report indexes into this
        vec = _np.array([target[s_] / g for s_ in syms], float)
        # floors let the reshape report a name that crosses its min-notional BECAUSE of the move.
        # A floors-less run reports "nothing crossed", which is indistinguishable from "nothing
        # was checked" unless the source is labelled — so it always is.
        fl = ({i: float((floors_usdt or {}).get(s_, 0.0) or 0.0) for i, s_ in enumerate(syms)}
              if floors_usdt is not None else None)
        rs = LG.reshape_after_withhold(vec, sizing_gross=g, redemean=redemean, rescale=rescale,
                                       floors_usdt=fl, strict=True)
        for i, s_ in enumerate(syms):
            target[s_] = float(rs["w"][i]) * g
        rs.pop("w", None)                      # the vector IS the book; the row keeps the report
        rs["names_crossed_floor"] = [syms[i] for i in rs["names_crossed_floor"]]
        rs["floors_source"] = floors_source if floors_usdt is not None else (
            "NOT SUPPLIED — floor crossings were not checked, not 'none found'")
        rs["n_popped"] = len(clamp["popped"])
        rs["popped_names"] = sorted(clamp["popped"])
        rs["n_dust_popped"] = len(_dust_popped)                   # fix package D: popped because |held| < min notional (a subset of popped)
        rs["dust_popped_names"] = sorted(_dust_popped)
        rs["sizing_gross"] = g
        # ★ E6 (EXE-03): net_before == net_producer_usdt − net_removed_usdt, both stated
        rs["net_producer_usdt"] = _net_composed
        rs["net_removed_usdt"] = _net_composed - float(rs["net_before"])
        rs["n_removed"] = len(clamp["popped"]) + len(_flat_out)
        rs["removed_names"] = sorted(set(clamp["popped"]) | set(_flat_out))
        rs["net_removed_flat_out_usdt"] = _flat_out_net
    # ── 2b. W9: the held force_flat names come back at EXACTLY 0.0 — after the reshape, so no shift reaches them ──
    for s_ in _flat_out:
        target[s_] = 0.0
    if rs is not None:
        rs["forced_flat_names"] = list(_flat_out)

    # ── 3. the HELD untradables: clamp, never pop. Venue constraint, applied LAST. ─────────
    pinned_before = {s_: float(target.get(s_, 0.0) or 0.0) for s_ in untradable}
    clamp.update(clamp_held_untradable(target, held, untradable))
    if rs is not None:
        pinned = clamp["add_blocked"] + clamp["flatten_only"]
        # ★★ THE NUMBER THAT EXPLAINS THE BOOK IS THE SHIFT, NOT THE PIN. Reporting the pinned
        #    notional alone ("P is 200") does not tell an operator why the book's net is not zero:
        #    the reshape had already placed P at some value, and the clamp MOVED it. The net you
        #    end up with is `0 - (what the clamp took away)`, so that difference is the reportable
        #    quantity. `book_net_usdt` is then stated outright rather than left to be re-derived —
        #    a reader who has to recompute it will eventually recompute it differently.
        rs["clamped_after_reshape"] = {
            "names": sorted(pinned),
            "pinned_net_usdt": float(sum(float(target.get(s_, 0.0) or 0.0) for s_ in pinned)),
            "net_shift_usdt": float(sum(float(target.get(s_, 0.0) or 0.0) - pinned_before.get(s_, 0.0)
                                        for s_ in pinned)),
            "book_net_usdt": float(sum(target.values())),
            "caliber": ("`net_shift_usdt` is how far the venue's clamps moved the book's net away "
                        "from the zero the reshape had just established; `book_net_usdt` is where "
                        "it ended up. The residue is deliberately NOT absorbed into the other "
                        "names — that would be an unmade hedging decision."),
        }
    return clamp, rs


def clamp_held_untradable(target, held, untradable):
    """Pass 2 of the withhold: the names we DO hold. Mutates `target`; returns the disposition.

    WITHHELD MEANS "CANNOT OPEN", NOT "CANNOT CLOSE" — and until 2026-08-01 the code meant the
    second [S1]. `target.pop()` erased the name, `plan()` iterates the target, so a
    WITHHELD-BUT-HELD name produced NOT ONE ROW: no reduction, no record, no alarm. The position
    was silently orphaned, while the comment beside the withholding rule had always read "a cap of
    0 blocks opening, not closing" — the comment said the opposite of what the code did, which is
    why reading either alone could not find it.
    """
    out = {"reduced": [], "add_blocked": [], "flatten_only": []}
    for s_ in untradable:
        cur = float((held or {}).get(s_, 0.0) or 0.0)
        if cur == 0.0:
            continue                                       # already popped in pass 1
        tgt = float(target.get(s_, 0.0) or 0.0)
        if tgt * cur > 0 and abs(tgt) <= abs(cur):
            out["reduced"].append(s_)                      # already a reduction: leave it
        elif tgt * cur > 0:
            target[s_] = cur                               # would ADD: no movement permitted
            out["add_blocked"].append(s_)
        else:
            target[s_] = 0.0                               # flatten, and never past flat
            out["flatten_only"].append(s_)
    return out
# |net_before| / sizing_gross above which the withhold itself is a finding, not just a correction.
# ★ A POLICY NUMBER, not a calibrated one — three anchors are not a distribution. 2% of gross is
#   roughly two popped names at typical tail weight; more than that means the universe gate is
#   removing a slice of the book big enough that "we corrected it" stops being the whole story.
RESHAPE_RESIDUAL_ALARM_FRAC = 0.02


def reshape_residual_alarm_text(rs, gross):
    """★ E6 (EXE-03, FX-EXEC 2026-09-13): the 撤名残差 page states the two quantities that make the pre-reshape net — the producer's
    book as composed, and what the removed names took away — instead of "由 N 个撤下的名字造成", which blamed the removed names for the
    producer's own net. Kept under the same head word, so alarm_policy files it where it always went (C, record only)."""
    g = max(float(gross or 0.0), 1e-9)
    nb, npr, nrm = float(rs["net_before"]), float(rs.get("net_producer_usdt", 0.0)), float(rs.get("net_removed_usdt", 0.0))
    return (f"撤名残差 {nb:+.2f} USDT = 目标 gross 的 {nb / g:+.2%} (>{RESHAPE_RESIDUAL_ALARM_FRAC:.0%}) = 生产者书自身净 {npr:+.2f} "
            f"({npr / g:+.2%}) − 撤下 {int(rs.get('n_removed', rs.get('n_popped', 0)))} 名的净 {nrm:+.2f} ({nrm / g:+.2%}): "
            f"{sorted(rs.get('removed_names') or rs.get('popped_names') or [])[:8]}。已重整回中性; 这一净额的大头若在生产者书里, "
            f"它不是撤名带来的。")


# ★ E6 (FX-EXEC 2026-09-13): WHY a held name is withheld, per name. Every source that joins `_untradable` in run_anchor, in display
#   order. The held-withheld page said "withheld by the venue (maxNotionalValue=0)" for all of them; on 09-13 16Z the seven held
#   names were five the producer no longer targets and two below 2x minNotional, and stopped / cooldown names ride the same channel.
WITHHELD_SOURCE_LABELS = (
    ("per_name_stop", "逐名止损已停(cf40ea21)"),
    ("per_name_stop_cooldown", "逐名止损冷却期"),
    ("venue_zero_cap", "场所 maxNotionalValue=0(不许开新仓)"),
    ("venue_not_trading", "场所状态非 TRADING"),
    ("external_held_exit", "外部书不再持有(持仓出场)"),
    ("external_dust", "外部书目标低于 2×minNotional"),
    ("external_meta", "外部书元数据排除"),
)


def held_withheld_alarm_text(clamp, sources):
    """The page for HELD untradable names, each listed under every source that put it there; a held name no source recorded is listed
    as such — never attributed to the venue by default. Keeps "reduce-only from here", so alarm_policy files it where it always went (B)."""
    held = sorted(set(clamp.get("reduced") or []) | set(clamp.get("add_blocked") or []) | set(clamp.get("flatten_only") or []))
    src = {k: set(v or ()) for k, v in (sources or {}).items()}
    parts, seen = [], set()
    for key, label in WITHHELD_SOURCE_LABELS:
        names = [n for n in held if n in src.get(key, set())]
        if names:
            seen |= set(names)
            parts.append(f"{label}: {names[:8]}{' +' + str(len(names) - 8) if len(names) > 8 else ''}")
    unknown = [n for n in held if n not in seen]
    if unknown:
        parts.append(f"来源未记录: {unknown[:8]}")
    return (f"{len(held)} held name(s) withheld, reduce-only from here — by source: " + "; ".join(parts) + ". "
            f"reducing={list(clamp.get('reduced') or [])[:4]} add_blocked={list(clamp.get('add_blocked') or [])[:4]} "
            f"flatten_only={list(clamp.get('flatten_only') or [])[:4]}")
# share of an EXTERNAL book's gross withheld by the 2x-min-notional eligibility filter above which
# the breadth loss is a finding. ★ A POLICY NUMBER, same reasoning as min_gross_usdt's '排除 ≤10%':
# measured on the 2026-08-22 00:00Z shadow weights at NAV 15.4k x 1.0 the filter withholds 6.2% of
# gross (195 tail names); at 2.0x 1.7%. Recorded every anchor either way; paged only above this.
EXT_DUST_ALARM_FRAC = 0.10

KILL_PATH = os.environ.get("LIVE_KILL_SWITCH",
                           os.path.join(_REPO, "state", "KILL_SWITCH.json"))


def prev_nonzero_symbols(root: str, before_anchor_ts: float) -> set:
    """Symbols carrying a NONZERO venue position at the most recent readback strictly before
    `before_anchor_ts`, searched backwards across day files.

    ★★ [i-face2] WHY THIS EXISTS. The readback universe was `set(venue) | targeted`, and
    `positions_notional()` returns only nonzero holdings because the venue encodes "flat" as
    ABSENCE. So a symbol that BOTH left the tradable universe AND went to zero is missing from
    both sets, gets no row, and §4-5b — which iterates over the current readback — never compares
    it. Measured 2026-07-26 16:00Z: ONTUSDT went -171.60 -> 0 while leaving the universe, and
    §4-5b reported 102 names with ONTUSDT not among them.

    The escaping class is "departed AND zeroed" — a departee that still HOLDS appears in `venue`
    and is reconciled normally. Departed-and-zeroed is precisely the liquidation case §4-5b is
    named for: a forced liquidation of a departed name would be seen by nothing.

    ★ THE FIX IS AT THE WRITE SIDE ON PURPOSE. Widening `reconcile` with a live venue read would
    have made a shared, replayable pure function depend on the network — the same log would score
    differently on two runs, and the ghost-row and turnover fixtures assert on it by replaying
    tree copies. A decision function with external input cannot be checked against a known answer.
    Recording the fact instead keeps every consumer pure and needs no exemption logic.

    ★ CROSS-DAY BY CONSTRUCTION (lead's boundary). The first anchor of a day has no earlier
    anchor in its own file; its predecessor is the last anchor of the previous day. Scanning only
    today would silently return the empty set at exactly one anchor per day — the "interval
    seam" family — so days are walked newest-first until a readback older than the cutoff appears.
    """
    import pilot_log as _PL          # local, as everywhere else in this module
    out: set = set()
    try:
        days = _PL.available_days(root)
    except Exception:
        return out
    for day in reversed(days):
        try:
            rows = _PL.read_day(root, day).get("position_readback", [])
        except Exception:
            continue
        prior = [r for r in rows if float(r.get("anchor_ts", 0)) < float(before_anchor_ts)]
        if not prior:
            continue                       # nothing in this day precedes the cutoff: keep walking
        last_ts = max(float(r["anchor_ts"]) for r in prior)
        for r in prior:
            if float(r["anchor_ts"]) == last_ts and abs(float(
                    r.get("venue_position_notional") or 0.0)) > 1e-9:
                out.add(r["symbol"])
        return out                          # the immediately preceding readback, and only it
    return out


def fill_collection_gap(phase_b: dict):
    """[B26a] Orders reached a terminal state and NO fills were collected. Returns a message or None.

    ★ THE SIGNATURE, from the run log over every anchor that actually traded:
        07-26 00:01Z  already_terminal=46  fill_rows_built=[FIELD ABSENT]   <- incident 1
        07-26 12:00Z  already_terminal=77  fill_rows_built=1382             ok
        07-27 00:01Z  already_terminal=87  fill_rows_built=0                <- incident 2
        07-27 08:01Z  already_terminal=81  fill_rows_built=1527             ok
        07-27 12:00Z  already_terminal=90  fill_rows_built=1052             ok
      87 orders finished at the venue and the ledger recorded zero fills. Nothing watched that
      combination, so the first thing to notice was §4-5b — three hours later, when the response
      had become a flatten. This fires at the anchor that caused it.

    ★★ ABSENT AND ZERO FIRE ALIKE, AND THAT IS THE LOAD-BEARING PART. At the first incident the
      field DID NOT EXIST (the collector was wired at 01:15-02:15Z that day), so `fill_rows_built
      == 0` is False there — the obvious spelling would skip one of the two known cases, and it
      would skip the earlier and worse one, where there was no collector at all. "We have no
      collector" and "the collector returned nothing" are the same fact about the ledger.

    ★★ AND THE COUNTER SITTING NEXT TO IT WAS TRUE AND MISLEADING: the same phase_B reported
      `n_trades_unattributed: 0`. Its denominator is trades COLLECTED, so with zero collected it
      is vacuously 0 — "the collector saw nothing" and "there was nothing to see" print the same.
      The message below says so, because that is the number a reader will reach for.

    ★ IT MUST STAY SILENT ON AN ANCHOR THAT DID NOT TRADE: `already_terminal > 0` is the
      discriminator. Every DRY_RUN run measured on 2026-07-27 reports 0/0, which is honest.

    ★ NOT A REPAIR. The trades are still in `userTrades` and can be backfilled; this only makes the
      loss visible while it is still cheap. The backfill path is its own item.
    """
    kc = (phase_b or {}).get("k_cancel") or {}
    try:
        terminal = int(kc.get("already_terminal") or 0)
    except (TypeError, ValueError):
        terminal = 0
    if terminal <= 0:
        return None
    has_field = "fill_rows_built" in (phase_b or {})
    built = (phase_b or {}).get("fill_rows_built")
    if has_field and built:
        return None
    where = ("the collector returned ZERO" if has_field else
             "there was NO COLLECTOR at all (the field is absent)")
    return (f"{terminal} order(s) reached a terminal state at the venue and NO fill rows were "
            f"recorded — {where}. Those executions are missing from our ledger, so §4-5b will "
            f"report the position change as unexplained (measured: it did, 3h later, and the "
            f"response was a flatten). Note `n_trades_unattributed` is vacuously 0 here: its "
            f"denominator is trades COLLECTED. The trades are still retrievable from userTrades "
            f"— backfill them rather than letting one outage cost the ledger permanently.")


def book_after_anchor(prev: dict, rows: list, rebalance_id: str) -> dict:
    """[B29] The cached book after an anchor = what we HELD, plus what actually FILLED.

    ★★ THE DEFECT THIS REPLACES: THE BOOK WAS WRITTEN FROM THE INTENT.
        state["positions"][sym] = cur + intended_notional   if the leg was a top-up
                                  target.get(sym, cur)      otherwise
    Both branches record a WISH as a FACT. The maker branch wrote the TARGET — a leg that filled
    5% of its delta was booked at 100% of it — and the top-up branch added what we MEANT to send,
    not what came back. Measured drift against the venue on consecutive anchors: 26 -> 88 -> 107
    names (107 of 109 by the third), monotonically, and it never self-heals because the error is
    re-committed every anchor.
    ★ AND `terminal_reason == "filled"` WAS THE WRONG GATE. On the real tree most executions carry
    `partial_expired` WITH a non-zero `filled_notional` (the maker filled some, the rest expired);
    those fills moved the book and were skipped entirely. What moved the book is the fill, so the
    fill is what is read — the terminal_reason is a description of the leg's ending, not of it.

    ★ WHAT IT DOES *NOT* CLAIM. `filled_notional is None` means the venue's answer was never read.
    That symbol is left at its previous value and NAMED in `unknown`: adding 0.0 would assert
    "nothing filled", which is the reading that produced the 2x doubling, and asserting the target
    is the defect above. The caller reports the names; the next anchor re-reads the venue anyway.

    ★ SEMANTICS SHARED WITH `reconcile.signed_fills_by_anchor` ON PURPOSE: signed column, summed,
    None skipped rather than zeroed. Grouped by rebalance_id here because a cached book is a
    property of the batch that just ran, not of an anchor bucket.
    """
    out = dict(prev or {})
    unknown: list = []
    for row in rows or []:
        if row.get("rebalance_id") != rebalance_id:
            continue
        sym = row["symbol"]
        f = row.get("filled_notional")
        if f is None:
            unknown.append(f"{sym}/{row.get('order_type')}")
            continue
        f = float(f)
        if f:
            out[sym] = float(out.get(sym, 0.0)) + f
    return {"positions": out, "unknown": sorted(set(unknown))}


def readback_universe(venue, targeted, prev_nonzero) -> set:
    """Which symbols get a position_readback row this anchor.

    Three sources, three different facts, and only the union distinguishes them:
      venue        — what we hold now (absence here means flat, not unknown)
      targeted     — what we aimed at (a target we did not reach is a fact about US)
      prev_nonzero — what we held at the previous readback, so a name that goes to zero is
                     RECORDED going to zero instead of vanishing from the comparison entirely
    """
    return set(venue or {}) | set(targeted or set()) | set(prev_nonzero or set())


# ════════════════════════════════════════════════════════════════════════════════════════════
# W6C-B13 — THE BOOK WE COULD NOT LOOK AT
#
# `finalize_anchor` writes zero position_readback rows for four different reasons, and in the log
# they are ONE observable: the end-of-anchor account read raised; DRY_RUN has no account at all;
# the readback universe was empty on a successful read; or a row the logger refused broke the write
# loop and the tail was never written. The watchdog cannot tell them apart from the rows, and on
# ef60f85 it did not try — §4-5b, §4-5e and §4-7 all fell back to the previous anchor and printed
# CLEAN about a book we had not seen (probe_unreadable_book cell U1; and on the real 2026-08-01
# rows, deleting one anchor's readback makes that day's genuine §4-5e BREAK disappear).
#
# So the producer says which it was, in one vocabulary, and the watchdog reads it.
def _book_observation(verdict: str, n_rows: int, anchor_ts, why: str) -> Dict[str, Any]:
    """The end-of-anchor verdict on whether we managed to LOOK at the book.

    OBSERVED / OBSERVED_EMPTY   the account was read (the second: nothing to write, which is a book
                                we saw and that was flat, not a book we missed)
    READ_FAILED                 the account read raised — we do not know what we hold
    NO_ACCOUNT                  DRY_RUN: there is no account, and there never was one
    WRITE_TRUNCATED             rows were written and then the write stopped; the tail is missing
    NO_LOGGER                   nothing was written because nothing could be
    """
    return {"verdict": verdict, "n_rows": int(n_rows), "anchor_ts": anchor_ts, "why": why}


def book_unobserved_halt(last_eval_path: str, mode: str) -> Dict[str, Any]:
    """Should this anchor refuse to OPEN because the newest evaluation could not see the book?

    Returns a dict; the caller halts iff `out["halt"]`. The answer is only ever about the OPENING
    direction — reduce-only paths keep running, no position is ever closed here and the account-wide
    switch is never touched. That is the user's rule of 2026-09-12 applied: an instrument's own
    doubt gets an instrument-shaped response. Worst case of a false positive is one anchor of
    skipped opening trades on a book that is still held.

    ★ IT CLEARS ITSELF, and that is why it writes no state of its own. The next anchor still writes
      its readback while opening is halted (`finalize_anchor` writes it whenever the account read
      succeeds, independent of every halt), so the following evaluation says OBSERVED and this
      returns halt=False. No timer, no counter, no state file for an operator to clear, and
      `ops/resume_from_trip.sh` is not involved at all.

    ★ FAIL-CLOSED EXACTLY AS GATE 0b DOES, and no further: a file that EXISTS and cannot be read,
      or that another mode wrote, resolves to halted. A file that does not exist is a fresh state
      tree's first anchor and is not.

    ★ AND AN EVALUATION FROM BEFORE THIS CODE IS A DEPLOY BOUNDARY, NOT A LOST BOOK. The key is
      simply absent there, and failing closed on it would halt the book on the first anchor after
      deployment. It returns halt=False with the state NAMED (`NOT_EVALUATED`) and does not page:
      every evaluation older than this build lacks the key, so a page would fire routinely, and a
      page that fires routinely is one nobody reads. The anchor records the state in its own
      phase_A output, which is where the first-anchor review looks.
    """
    out: Dict[str, Any] = {"halt": False, "state": None, "page": False, "why": "",
                           "path": last_eval_path, "evaluated_utc": None, "observability": None}
    if not os.path.exists(last_eval_path):
        out.update(state="NO_EVALUATION",
                   why="no evaluation on disk yet (a fresh state tree's first anchor)")
        return out
    try:
        import state_root as _SR
        data, note = _SR.read_stamped(last_eval_path, mode, strict=False)
        if note and "was written by mode" in note:
            out.update(halt=True, state="WRONG_MODE", page=True, why=note[:200])
            return out
        data = data or {}
    except Exception as e:
        out.update(halt=True, state="UNREADABLE", page=True,
                   why=f"{type(e).__name__}: {str(e)[:160]}")
        return out
    out["evaluated_utc"] = data.get("evaluated_utc")
    obs = data.get("book_observability")
    if not isinstance(obs, dict):
        # ★ RECORDED, NOT PAGED. Every evaluation written before this code lacks the key, so a
        #   page here fires on the first anchor after deployment and on every anchor of every tree
        #   whose watchdog is older — a page that fires routinely is a page nobody reads (the sleep
        #   guard's lesson, and the reason `reconcile_summary` is counted rather than alarmed).
        #   The fact travels in `book_observability_gate`, which phase_A prints, and the
        #   first-anchor review reads it once, where a human is already looking.
        out.update(state="NOT_EVALUATED", page=False,
                   why=("the newest evaluation carries no book_observability block — it was "
                        "written by a build from before this gate existed. Not a lost book; not "
                        "silent either: this is in the anchor's own phase_A record."))
        return out
    out["observability"] = obs
    out.update(halt=bool(obs.get("halt_opening")), state=obs.get("state"),
               page=bool(obs.get("halt_opening")),
               why=(f"newest evaluation ({data.get('evaluated_utc')}) reports "
                    f"{obs.get('state')} via {obs.get('reference')}; newest scheduled anchor "
                    f"{obs.get('newest_scheduled_anchor_ts')}"))
    return out


def _load(path: str, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def _save(path: str, obj):
    # ★ B-2 (DESIGN_executor_durable_state_2026-09-25; census 501d80737): the former body was
    #   `json.dump(obj, open(tmp, "w")); os.replace(tmp, path)` — the handle was closed by the garbage
    #   collector, where a full-disk error is NOT raised (measured), so an empty / truncated tmp silently
    #   REPLACED the good state. Now: bytes in memory -> private tmp inside `with` -> fsync -> read back
    #   and compared byte for byte -> os.replace -> dir fsync; any failure raises DurableWriteError and
    #   leaves the target untouched. Byte-identical output to the old path (json.dumps(obj, indent=1)).
    os.makedirs(os.path.dirname(path), exist_ok=True)
    DIO.write_json_durable(path, obj, indent=1)


def signal_age_anchors(preds: Optional[Dict], now: Optional[float] = None) -> float:
    """Age of the newest usable prediction, in units of anchors. inf when absent."""
    now = now or time.time()
    if not preds or "computed_ts" not in preds:
        return float("inf")
    return max(0.0, (now - float(preds["computed_ts"])) / ANCHOR_S)


def staleness_action(age_anchors: float) -> str:
    """Pre-registered ladder. Mechanical: the operator never decides this at 4am."""
    if age_anchors < STALE_HOLD_ANCHORS:
        return "TRADE"
    if age_anchors < STALE_DERISK_ANCHORS:
        return "HOLD"
    if age_anchors < STALE_FLATTEN_ANCHORS:
        return "DERISK"
    return "FLATTEN"


# ★ E-0909-E (2026-09-09): the venue's FINITE position cap. `symbolConfig.maxNotionalValue` is the
#   largest notional the venue lets this account hold in a name AT ITS CURRENT LEVERAGE; an order
#   that would take position + order past it is refused with -2027. The planner clamped only
#   cap == 0 (`clamp_held_untradable`), so PIEVERSEUSDT (20x, cap 2,000; held 1,890; target
#   ≈2,330) was refused six anchors running and re-sent the same delta each time. 715 of 897
#   names sit at 20x with caps of 2,000–5,000 USDT; at NAV×2 a 1% weight is ≈2,300 USDT, so this
#   is a standing constraint, not one name's accident.
# ★ ONLY SHRINKS. Sign is never changed, nothing is popped, names without a finite positive cap
#   are untouched (cap 0 = withheld, handled above). A name whose POSITION already exceeds the
#   limit (the venue lowered the cap) gets a target of cap×(1−margin) — a REDUCTION, which the
#   venue always accepts. The margin absorbs mark-vs-mid drift inside the anchor.
# ★ APPLIED AFTER pop→reshape→held-clamp, i.e. on the FINAL numbers, and like the held clamps
#   its residue is deliberately NOT absorbed into other names (that would be an unmade hedging
#   decision). Fail-closed at the call site: any exception ⇒ targets unchanged + HIGH page.
VENUE_CAP_MARGIN = 0.02


def clamp_venue_cap(target, held, cfgmap, margin=VENUE_CAP_MARGIN):
    """Cap |target[s]| at maxNotionalValue×(1−margin) for every name with a finite positive cap.

    ★ Round 3 (review 31fa3e4e cap P2): ATOMIC and FINITE. Every cap / target / held / margin is
      validated first; a non-finite or unparsable value is recorded in `invalid` and that name is
      left untouched; the new targets are computed into a temporary map and applied only after
      every name has been decided — so a failure part-way can no longer leave the first names
      changed while the caller's log says "targets unchanged". A name whose POSITION already
      exceeds the limit is reported in `reduce_only_syms` so the planner sends its reduction as
      reduce-only rather than relying on the label.
    Mutates `target` only on success; returns {"capped": [...], "n_checked": int, "margin": float,
    "invalid": [...], "reduce_only_syms": [...]}."""
    out = {"capped": [], "n_checked": 0, "margin": float(margin), "invalid": [],
           "reduce_only_syms": []}
    _m = float(margin)
    if not (_m == _m and 0.0 <= _m < 1.0):
        raise ValueError(f"clamp_venue_cap: margin {margin!r} is not a finite fraction in [0, 1)")
    _new: Dict[str, float] = {}

    def _finite(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if (v == v and v not in (float("inf"), float("-inf"))) else None

    # ★ Round 5 (review R7/Q5): target and held are validated for EVERY name first, independent of
    #   whether a cap exists or parses — a NaN/None target with no cap, or beside a bad cap, used to
    #   walk past this check into the planner. A raw None is invalid too (`or 0.0` validated a zero
    #   the planner never saw).
    _bad: set = set()
    for s_ in list(target.keys()):
        _tv = target.get(s_)
        if _tv is None or _finite(_tv) is None:
            out["invalid"].append({"symbol": s_, "field": "target", "value": str(_tv)[:32]}); _bad.add(s_)
        _hv = (held or {}).get(s_, 0.0)
        if _hv is not None and _finite(_hv) is None:
            out["invalid"].append({"symbol": s_, "field": "held", "value": str(_hv)[:32]}); _bad.add(s_)
    for s_ in list(target.keys()):
        c = (cfgmap or {}).get(s_)
        if not isinstance(c, dict):
            continue
        _raw = c.get("maxNotionalValue")
        if _raw in (None, "", 0, 0.0, "0"):
            continue                                     # withheld / unset: the untradable clamps own it
        cap = _finite(_raw)
        if cap is None:
            out["invalid"].append({"symbol": s_, "field": "maxNotionalValue", "value": str(_raw)[:32]})
            continue
        if cap <= 0.0 or s_ in _bad:
            continue
        t = float(target.get(s_, 0.0) or 0.0)
        cur = float((held or {}).get(s_, 0.0) or 0.0)
        out["n_checked"] += 1
        lim = cap * (1.0 - _m)
        if abs(t) <= lim:
            continue
        new = lim if t > 0 else -lim
        _kind = "reduce_to_cap" if (cur * t > 0 and abs(cur) > lim) else "add_capped"
        out["capped"].append({"symbol": s_, "target_before": round(t, 2),
                              "target_after": round(new, 2), "cap": cap, "held": round(cur, 2),
                              "kind": _kind})
        if _kind == "reduce_to_cap":
            out["reduce_only_syms"].append(s_)
        _new[s_] = new
    for s_, v in _new.items():                           # apply only after every name decided
        target[s_] = v
    return out


def submit_with_cleanup(executor, plans, anchor_ts, rid, alarm):
    """`executor.submit_maker`, and if ANYTHING escapes it: cancel what rested, write the rows,
    page, re-raise. (E-0909-D, 2026-09-09 12:00Z LIVE.)

    ★★★ WHAT HAPPENED. A TLS handshake timeout on the 5th maker POST propagated out of
        submit_maker → _trade → run_anchor → main. Four GTX orders (HUSDT/CLO/ANKR/CHZ, ≈320 USDT)
        were left resting with no ledger row, no cancel and no page; the process exited rc=1 and
        the only trace was a traceback in anchor_runs.log. 66 fills landed in the next ten minutes
        with nothing watching. The next anchor's sweep_stale_orders cancelled the four — the
        backstop working, four hours late.
    ★★ THE BROKER NOW RESENDS TRANSPORT FAILURES AND THE EXECUTOR RECORDS THEM (see
       binance_broker._request / binance_executor.submit_maker), so THAT exception no longer
       escapes. This wrapper is for the class: whatever escapes the submit loop next time — a
       KeyError in a new experiment branch, a bug in a row writer — must leave the venue with no
       unowned order, the ledger with a row per plan, and the operator with a page. It decides
       nothing; it makes sure the failure is neither silent nor exposed.
    ★ ORDER: cancel first (exposure), rows second (record), page third, re-raise always. Each
      step is wrapped so a failure inside the cleanup can neither mask the original exception
      nor stop the next step. The exception is re-raised UNCHANGED: an anchor that failed must
      still exit non-zero (launchd, the dead-man ping and run_anchor's page key on that), and
      phase B/C must NOT run on a half-submitted book.
    ★ ROWS. A plan that rested (in `_live_inflight`) or that was mid-send when the loop died
      (`submit_ts` set, no row, not in `live`) is cancelled by its deterministic client id and
      written `filled_amount_unknown` — it left (or may have), phase B will not read its fills,
      so the residual is a gap of UNKNOWN size, which is exactly what that label means. A plan
      the loop never reached is `never_submitted`. Rows submit_maker already wrote are not
      duplicated.
    """
    try:
        return executor.submit_maker(plans, anchor_ts, rid)
    except Exception as exc:                                    # noqa: BLE001 — deliberate
        rep = {"error": f"{type(exc).__name__}: {str(exc)[:200]}", "n_inflight": 0,
               "n_midsend": 0, "cancel": None, "cancel_error": None,
               "rows_written": 0, "rows_error": None, "rows_failed": []}
        inflight = list(getattr(executor, "_live_inflight", None) or [])
        try:
            _done = {(r.get("symbol"), int(r.get("attempt_idx") or 1))
                     for r in (getattr(executor, "rows_orders", None) or [])
                     if r.get("rebalance_id") == rid}
        except Exception:                                       # noqa: BLE001
            _done = set()
        _in = {id(p) for p in inflight}
        midsend = [p for p in plans
                   if id(p) not in _in and p.get("submit_ts") and not p.get("submitted")
                   and (p.get("symbol"), 1) not in _done]
        rep["n_inflight"], rep["n_midsend"] = len(inflight), len(midsend)
        to_cancel = inflight + midsend
        if to_cancel:
            try:
                rep["cancel"] = executor.cancel_resting(to_cancel, rid)
            except Exception as ce:                             # noqa: BLE001
                rep["cancel_error"] = f"{type(ce).__name__}: {str(ce)[:160]}"
        # ★ Review b0a573a1 P2: ONE row fault must not silence the other plans — each plan's
        #   row is its own try; failures are named in `rows_failed` and paged.
        _mid = {id(p) for p in midsend}
        for p in plans:
            try:
                if p.get("skip") is not None or "qty" not in p:
                    # submit_maker's own skip rule, verbatim — including the row it would have
                    # written for a truthy skip the loop never reached
                    if p.get("skip") and (p.get("symbol"), 1) not in _done:
                        executor._order_row(p, anchor_ts, rid, 1, "maker",
                                            terminal_reason=p["skip"], submitted=False)
                        rep["rows_written"] += 1
                    continue
                if (p.get("symbol"), 1) in _done:
                    continue                    # the loop already wrote this one
                if id(p) in _in or id(p) in _mid:
                    executor._order_row(p, anchor_ts, rid, 1, "maker",
                                        terminal_reason="filled_amount_unknown", submitted=True,
                                        unknown=("filled_notional",),
                                        note=(f"submit loop aborted ({rep['error'][:80]}); "
                                              + ("rested, cancelled in cleanup, fills unread"
                                                 if id(p) in _in else
                                                 "was mid-send — may or may not have left; "
                                                 "cancel attempted, fills unread")))
                else:
                    executor._order_row(p, anchor_ts, rid, 1, "maker",
                                        terminal_reason="never_submitted", submitted=False,
                                        note=f"submit loop aborted before this plan "
                                             f"({rep['error'][:80]})")
                rep["rows_written"] += 1
            except Exception as re_:                            # noqa: BLE001
                rep["rows_failed"].append({"symbol": p.get("symbol") if isinstance(p, dict) else None,
                                           "error": f"{type(re_).__name__}: {str(re_)[:120]}"})
        if rep["rows_failed"]:
            rep["rows_error"] = (f"{len(rep['rows_failed'])} row(s) failed: "
                                 + ", ".join(f"{r['symbol']} ({r['error'][:40]})"
                                             for r in rep["rows_failed"][:5]))
        _c = rep["cancel"] or {}
        try:
            alarm("CRITICAL",
                  f"下单阶段异常中断 ({rep['error']}); 在飞 {len(inflight)} 张挂单"
                  f"{' + ' + str(len(midsend)) + ' 张发送中' if midsend else ''}已尝试撤销 "
                  f"(撤 {_c.get('cancelled', '?')}/已终态 {_c.get('already_terminal', '?')}/"
                  f"未决 {len(_c.get('unresolved') or [])}"
                  f"{', 撤单本身失败: ' + rep['cancel_error'] if rep['cancel_error'] else ''}); "
                  f"补写账本行 {rep['rows_written']}"
                  f"{' (写行失败: ' + rep['rows_error'] + ')' if rep['rows_error'] else ''}。"
                  f"本锚点不进阶段 B, 进程按失败退出; 下一锚开场扫单兜底。")
        except Exception:                                       # noqa: BLE001
            pass
        try:
            executor.submit_abort_report = rep
        except Exception:                                       # noqa: BLE001
            pass
        raise


class AnchorLoop:
    def __init__(self, broker, executor, gross_usdt: float, log=None, alarm=None,
                 fills_provider=None):
        self.broker = broker
        self.executor = executor
        self.gross = gross_usdt
        self.log = log
        self.alarm = alarm or (lambda sev, msg: None)
        # fills_provider(rebalance_id, symbols) -> {symbol: filled_notional}. Injected because the
        # real implementation (order status / userTrades) only becomes testable with credentials;
        # DRY_RUN defaults to "nothing filled", which exercises the FULL top-up path — the
        # mandatory leg — rather than the flattering all-filled one.
        self.fills = fills_provider or (lambda rid, syms: {})
        self.src = FS.FapiSource()

    # ── one anchor, end to end ───────────────────────────────────────────────────────────────
    def run_anchor(self, now: Optional[float] = None) -> Dict[str, Any]:
        now = now or time.time()
        # NOTE: `last_alarm_stale` was removed 2026-07-26 — a DEAD FIELD (1 write, 0 reads
        # anywhere in the repo). Its job was taken over by `alarmed_stages` (one alarm per stage
        # per episode) and it was left behind, still being written. A field that is written and
        # never read is indistinguishable from a field that is read and wrong, until someone
        # checks — which is why the sweep is worth more than the deletion.
        state = _load(STATE_PATH, {"positions": {},
                                   "stale_ref_positions": None, "alarmed_stages": []})
        state.setdefault("stale_ref_positions", None)
        state.setdefault("alarmed_stages", [])
        out: Dict[str, Any] = {"anchor_wall_ts": now}
        # ── BOOK SOURCE (DESIGN_wide_live_deployment_2026-08-22 §1): internal (today) | external ─
        # ★ Resolved ONCE, here, before any state is read. INVALID (a typo, a malformed block, a
        #   gross_mult above the §4-4b leverage policy) BLOCKS the anchor outright: a book source
        #   that cannot be named must not pick a book — not the retired one, not the new one.
        # ★ `now_sched` keeps the ENTRY time for the off-schedule gate: in external mode this
        #   process deliberately idles until the producer's slot (N+anchor_offset_min) before it
        #   reads state or acts; it is still the scheduled run, and the ledger keys on process
        #   START for the same fact. Internal mode: now_sched == now, byte for byte.
        try:
            _book_cfg = BC.load()
        except Exception:                        # noqa: BLE001 — unreadable config = unknown source
            _book_cfg = None
        _ext_cfg = EXT.config(_book_cfg)
        out["book_source"] = _ext_cfg["source"]
        if _ext_cfg["source"] == "INVALID":
            out["action"] = "BLOCKED_CONFIG"
            out["note"] = f"book_source config invalid: {_ext_cfg['error']} — no orders of any kind"
            self.alarm("CRITICAL", f"book_source 配置无效: {_ext_cfg['error']} — 本锚不交易(既不读外部书, "
                                   f"也不回退在役引擎)。修 config/book.json 后下锚生效。")
            return out
        now_sched = now
        if _ext_cfg["source"] == "external":
            _pc = EXT.pns_profile_consistent(_book_cfg)
            if not _pc["ok"]:
                out["pns_profile_inconsistent"] = _pc["why"]
                self.alarm("HIGH", f"外部书与逐名止损 profile 不一致: {_pc['why']} — 条款仍按当前 profile 运行")
            if getattr(self.broker, "mode", "DRY_RUN") != "DRY_RUN":
                out["external_wait"] = EXT.wait_for_slot(_ext_cfg, now)
                if out["external_wait"].get("slept_s"):
                    now = time.time()
        # ── §2.5.9 rehearsal gate, evaluated ONCE and EARLY ──────────────────────────────────
        # Early, because two later blocks ask "is this a rehearsal?" (the off-schedule halt, and
        # the id mint) and a question answered twice is a question with two answers. It raises
        # rather than degrades: asking for rehearsal and silently getting a normal anchor is the
        # one outcome that would send an operator's off-schedule test into the schedule's count.
        import rebalance_id as _RID
        try:
            _cfg_clock = BC.load().get("dryrun_clock_start")
        except Exception:
            _cfg_clock = "UNREADABLE"        # fail-closed: unreadable config => clock is "started"
        out["_rehearsal"] = _RID.rehearsal_gate(getattr(self.broker, "mode", "DRY_RUN"), _cfg_clock)
        if out["_rehearsal"]["enabled"]:
            out["rehearsal"] = {k: v for k, v in out["_rehearsal"].items() if k != "checks"}
        # cleared per anchor: a stale context from the previous anchor would be written into THIS
        # anchor's row with last anchor's mids and target. (One process per anchor makes this
        # unreachable in production and perfectly reachable in a test that reuses the loop —
        # which is exactly the asymmetry that lets such a bug ship.)
        self._anchor_ctx = None

        # ── 0. KILL SWITCH — refuses EVERYTHING, including exits ────────────────────────
        # A stop button that only stops FUTURE wakeups is half a button: a process already
        # running (or one launched by hand) must also refuse. The flag is a local file, so this
        # check needs no network, no venue, no credentials — it cannot fail to fire. Clearing it
        # is deliberate and manual: resuming must cost more than stopping.
        if os.path.exists(KILL_PATH):
            killed = _load(KILL_PATH, {})
            out["action"] = "KILLED"
            out["halt_source"] = "KILL_SWITCH"
            out["killed_at_utc"] = killed.get("killed_at_utc")
            out["note"] = ("emergency stop is engaged; no orders of any kind. "
                           "Remove state/KILL_SWITCH.json to resume.")
            try:
                self.broker.halt_opening_orders("KILL_SWITCH engaged")
            except Exception:
                pass                     # the flag alone already blocks; this is belt-and-braces
            return out

        # ── 0b. WATCHDOG TRIP — persistent, and DIRECTIONAL (opening only) ──────────────
        # ★★ THE TWO HALTS HAVE OPPOSITE SEMANTICS AND MUST NOT BE MERGED.
        #   KILL_SWITCH : refuse EVERYTHING (above: immediate return, no exits either)
        #   watchdog    : refuse the OPENING DIRECTION ONLY — reduce-only must still pass,
        #                 because the flatten IS reduce-only. That exemption is the entire
        #                 reason `halt_opening_orders` runs FIRST in the degradation ladder.
        # Routing a trip into the kill-switch branch (which I did in 0e55d6b) blocks the ladder's
        # own exit: to stop it opening, it would also seal the way out. A protective action
        # inverted into a trap.
        #
        # ★ AND WHY IT MUST BE RE-APPLIED HERE AT ALL: `open_orders_halted` / `reduce_only` are
        # attributes on the broker OBJECT, and every anchor is a NEW PROCESS. The trip is
        # persisted to disk (watchdog.py writes it unconditionally) but nothing ever read it
        # back, so the protection lasted exactly as long as the process that raised it. The file
        # was sticky; the reader was missing.
        #
        # ★ FAIL-CLOSED: a state file we cannot read or parse is treated as TRIPPED. "We do not
        # know whether we are halted" must resolve to halted — the opposite default would make a
        # corrupted byte silently re-enable trading.
        wd_path = os.environ.get("LIVE_WATCHDOG_STATE",
                                 os.path.join(_REPO, "state", "watchdog", "state.json"))
        wd, wd_unreadable = {}, False
        if os.path.exists(wd_path):
            try:
                # ★ read through the MODE-STAMPED reader. I added `read_stamped` for exactly this
                # and then did not call it from anywhere — writing a guard and leaving it unwired,
                # one hour after diagnosing that same family. The scanner
                # (ops/scan_probe_only_callers.py) found it: its only caller was its own test.
                # ⇒ Here it matters most: this is the read that decides whether we are halted.
                # Another mode's state file parses, is self-consistent, and would answer that
                # question with a confident wrong value in either direction.
                import state_root as _SR
                _mode = os.environ.get("LIVE_MODE", "DRY_RUN")
                wd, _note = _SR.read_stamped(wd_path, _mode, strict=False)
                wd = wd or {}
                if _note and "was written by mode" in _note:
                    # a cross-mode file is NOT usable as a halt verdict -> fail closed
                    wd, wd_unreadable = {}, True
                    self.alarm("CRITICAL", f"watchdog state belongs to another mode: {_note[:160]}")
            except Exception:
                wd, wd_unreadable = {}, True
        if wd_unreadable or wd.get("tripped_at") or wd.get("reduce_only"):
            # ★★ THE ROUTE FOLLOWS THE HALT'S KIND (2026-08-01). This was a constant naming
            # `resume_from_trip.sh`, and a rehearsal-seeded halt is cleared by a different tool —
            # so on the one tree where it mattered the anchor's own record pointed at a route that
            # refuses. Reading the state's `resume_requires` instead was my first fix and was
            # WORSE in a way worth recording: that field is advice written when the halt was
            # created, and the LIVE halt's copy was already out of date, so the report faithfully
            # carried a stale pointer. The KIND is the durable fact (the marker, which any real
            # trigger's write drops); the mapping from kind to tool is design, and one function
            # owns it (state_root.resume_route) so three readers cannot answer differently.
            # ★ An unreadable state has no kind — `resume_route({})` returns the trip route, which
            #   is the conservative one: it refuses while anything holds.
            import state_root as _SR2
            _rt = _SR2.resume_route(wd)
            out["watchdog_halt"] = {
                "source": "unreadable_state_file" if wd_unreadable else "tripped",
                "tripped_at": wd.get("tripped_at"), "reason": wd.get("reason"),
                "resume": _rt["route"],
                "resume_kind": _rt["kind"],
                "resume_claimed_by_state": _rt["claimed"],
                "resume_claim_stale": _rt["mismatch"],
                # ★ EXE-01: WHAT KIND of halt, from the state's own fields — a proportional local response halts
                #   opening on a book that is still HELD; a trip halts a book the ladder flattened. The anchors row
                #   carries this forward (`halt_kind`) because §4-5e judges a no-submission anchor against intent
                #   ZERO only when the book was flattened.
                "state_kind": wd.get("kind"), "book_flattened": wd.get("book_flattened")}
            try:
                self.broker.halt_opening_orders(
                    f"watchdog trip persisted at {wd.get('tripped_at')}"
                    if not wd_unreadable else "watchdog state unreadable — fail-closed")
                self.broker.set_reduce_only(True, "watchdog trip persisted across anchors")
            except Exception as e:
                # if we cannot even engage the halt, that is worse than the trip itself
                self.alarm("CRITICAL", f"could not re-apply the persisted watchdog halt ({e}) — "
                                       f"this anchor may open positions after a stop-loss")
            # DELIBERATELY NOT `return`: the anchor continues so reduce-only paths (the staleness
            # ladder's DERISK/FLATTEN, universe exits) still run. Opening orders are refused by
            # the broker, per-order and by direction.

        # ── 0b-bis. THE BOOK WE COULD NOT LOOK AT — refuse to OPEN, page, close nothing ────
        # ★★ W6C-B13. The newest watchdog evaluation says whether it managed to see the book at the
        # newest anchor that happened. If it did not, adding risk we cannot see is the one thing we
        # must not do — and closing the book we cannot see is the OTHER thing we must not do (user,
        # 2026-09-12: an instrument's own doubt never gets a book-level response; the cost of that
        # lesson was a 235k USDT false-positive flatten). So: opening only, same direction and same
        # exemption as 0b, and no state of our own — this clears itself the moment an anchor writes
        # a readback again, because `finalize_anchor` writes one whatever halt is in force.
        # ★ THE PATH IS DERIVED FROM 0b's OWN, not read from a second env var. `state_root` does
        #   publish `LIVE_WATCHDOG_DIR`, and using it would be the "one place owns a path" rule —
        #   but the property that matters here is stronger: this gate and 0b must never be able to
        #   read DIFFERENT trees. `run_anchor` writes `last_eval.json` beside `state.json` in the
        #   same `watchdog_dir`, so taking the directory from `wd_path` binds the two gates to
        #   whichever tree 0b resolved, however the env redirected it.
        try:
            _obs_gate = book_unobserved_halt(
                os.path.join(os.path.dirname(wd_path), "last_eval.json"),
                os.environ.get("LIVE_MODE", "DRY_RUN"))
        except Exception as e:                   # a gate that cannot run must not take the anchor
            _obs_gate = {"halt": False, "state": "GATE_ERROR", "page": True,
                         "why": f"{type(e).__name__}: {str(e)[:160]}"}
        out["book_observability_gate"] = _obs_gate
        if _obs_gate.get("halt"):
            out["book_unobserved_halt"] = _obs_gate
            try:
                self.broker.halt_opening_orders(
                    f"book not observed at the newest anchor ({_obs_gate.get('state')}) — "
                    f"opening refused, positions untouched")
            except Exception as e:
                self.alarm("CRITICAL", f"book-unobserved gate fired and the opening halt FAILED "
                                       f"({e}) — this run may open into a book we cannot see")
            self.alarm("HIGH", f"本锚拒绝开仓: 最新看门狗评估未能读到最新已排程锚的持仓读回 "
                               f"({_obs_gate.get('state')})。{_obs_gate.get('why')} —— "
                               f"只停开仓, 未平任何仓位, 未触碰账户级 reduce-only 开关; "
                               f"下一个锚写出读回后自动解除。")
        elif _obs_gate.get("page"):
            self.alarm("HIGH", f"看门狗可观测性门: {_obs_gate.get('state')} —— "
                               f"{_obs_gate.get('why')} (未停开仓)")

        # ── 0c. OFF-SCHEDULE RUN — a run that is not the scheduled anchor must not OPEN ─────
        # ★ The §2.5 count and this gate must be the same decision. ops/dryrun_ledger excludes a
        # run that started more than `anchor_late_tolerance_min` from its slot ("manual /
        # kickstart, does not inflate the count"). Without this gate such a run still traded —
        # real orders placed by a run the certification does not count, which is the one
        # combination that makes the completion figure mean something other than it says.
        # Both sides now read live/book_config.py; nothing here holds a private copy.
        #
        # ★ DIRECTIONAL, LIKE 0b, AND FOR THE SAME REASON: refusing everything would also seal
        # the exits (universe delistings, the ladder's DERISK/FLATTEN). Being late is a reason
        # not to take on new risk; it is never a reason to be unable to shed it.
        #
        # ★ FAIL-CLOSED: if we cannot establish whether we are on schedule, we are not. "We do
        # not know what time it is" resolves to halted, same as the unreadable watchdog file.
        try:
            sched = BC.schedule_check(now_sched)
        except Exception as e:
            sched = {"on_schedule": False, "error": str(e),
                     "note": "schedule could not be established — treated as off-schedule"}
        out["schedule"] = sched
        # ── §2.5.9 REHEARSAL: the ONE exemption from the off-schedule opening halt ───────────
        # A rehearsal anchor exists to walk a never-executed path BEFORE the measurement window,
        # and every such path (funding settlement crossing, the preds ladder, DERISK, the kill
        # switch, maxQty chunking) needs a real anchor at a time nobody scheduled. The gate that
        # grants it lives in `rebalance_id.rehearsal_gate` and refuses under LIVE, after the clock
        # starts, or without a declared target — all three by machine.
        # ★ IT DOES NOT BUY A COMPLETION. The exemption is from the HALT, never from the COUNT:
        #   the rows carry an `R` prefix and every §2.5 counter drops them (and prints how many).
        #   An exemption that also removed the rows from the ledger would be the opposite — see
        #   §2.5.9 constraint 5, and §4-5b's history of calling our own protective action an
        #   unexplained position.
        _reh = out.get("_rehearsal") or {}
        if _reh.get("enabled") and not sched.get("on_schedule"):
            out["rehearsal_off_schedule_allowed"] = {
                "offset_min": sched.get("offset_min"), "target": _reh.get("declared_target"),
                "note": ("§2.5.9 rehearsal anchor: opening orders ALLOWED off-schedule. This run "
                         "is excluded from every §2.5/§2.5.8 count by its R prefix, and the "
                         "exclusion prints its own row count.")}
            self.alarm("HIGH", f"§2.5.9 排练锚点: off-schedule 开仓已放行 "
                               f"(偏离 {sched.get('offset_min')} 分钟), 目标路径 = "
                               f"{_reh.get('declared_target')}. 该锚点不计入 §2.5/§2.5.8 任何计数。")
            sched = dict(sched)
            sched["on_schedule"] = True
            sched["rehearsal_override"] = True
            out["schedule"] = sched
        if not sched.get("on_schedule"):
            # An explicit, call-site-visible opt-out for manual smoke tests — the same shape as
            # LIVE_FAST_K. The scheduled path never sets it, so the certification window cannot
            # acquire it by accident; and it is recorded in the run's output either way, so an
            # audit can see which runs traded off-schedule and on whose say-so.
            if os.environ.get("LIVE_ALLOW_OFF_SCHEDULE") == "1":
                out["off_schedule_override"] = True
                self.alarm("HIGH", f"本次运行偏离计划 {sched.get('offset_min')} 分钟, "
                                   f"但 LIVE_ALLOW_OFF_SCHEDULE=1 已放行 —— 该运行不计入 §2.5 "
                                   f"完成率, 却会真实下单。认证窗口内不得使用。")
            else:
                out["off_schedule_halt"] = {
                    "offset_min": sched.get("offset_min"), "nominal": sched.get("nominal_utc"),
                    "tolerance_min": sched.get("tolerance_min"), "error": sched.get("error"),
                    "note": ("not the scheduled anchor: opening orders refused, reduce-only "
                             "paths still run. This run is excluded from the §2.5 count too — "
                             "the ledger and this gate share one constant.")}
                try:
                    self.broker.halt_opening_orders(
                        f"off-schedule run: {sched.get('offset_min')} min from "
                        f"{sched.get('nominal_utc')} (tolerance {sched.get('tolerance_min')})")
                except Exception as e:
                    self.alarm("CRITICAL", f"off-schedule run and the opening halt FAILED ({e}) — "
                                           f"this run may open positions the ledger will not count")

        # ── reconcile with venue truth FIRST (audit 3c) ──────────────────────────────────
        # If the watchdog flattened between anchors, our cached book is a ghost: the next
        # rebalance would trade against positions that no longer exist. Venue readback wins.
        # (Skipped in DRY_RUN, where positions() is empty by construction, not by truth.)
        # ★ E-0912-A (b): the venue's CONTRACTS per name, from the SAME snapshot that fills `state["positions"]`
        #   below — used by `plan()` for one thing only: a full exit is sized as the position itself. Not a second
        #   cache (the rejection of a parallel contracts cache below stands): it lives for THIS anchor, on the loop
        #   object, and is empty in DRY_RUN or when the read failed — `plan()` then falls back and says so.
        self._held_qty = {}
        if self.broker.mode != "DRY_RUN":
            try:
                # ★ NOTIONAL, not contracts: state["positions"] is USDT notional throughout the
                # loop (plan deltas, DERISK snapshots, gross accounting). The venue speaks both
                # calibers; the bookkeeping dict must only ever hear one of them.
                # ★★ ONE READ, BOTH QUANTITIES. Sizing needs equity and reconciliation needs
                # positions, and `positions_notional()` already calls /fapi/v3/account — so two
                # calls would spend two requests AND let a fill land between them, making the
                # equity and the book describe different moments. That is the B30 lesson applied
                # before it can bite: one snapshot, both calibers.
                _snap0 = self.broker.account_snapshot()
                venue = (_snap0 or {}).get("positions_notional") or {}
                self._equity = (_snap0 or {}).get("equity")
                self._held_qty = dict((_snap0 or {}).get("positions_contracts") or {})   # E-0912-A (b)
                cached = state.get("positions", {})
                keys = set(venue) | set(cached)
                # ★★★ [R1] THE 1.0 USDT THRESHOLD MADE THIS A PRICE-MOVE DETECTOR.
                # Both sides are NOTIONAL, a position is ~230 USDT, so a 0.4% price move exceeded
                # 1.0 and the name was reported as "differing from the venue". Measured
                # 2026-07-29T00:00Z: 45 names reported, and the sampled differences had a median
                # of 3.07 USDT and a max of 5.07 (1.36% of the position) — every one of them
                # revaluation, paged at HIGH, every anchor. Same family as B30, where §4-5b was a
                # price-move detector wearing a position-mismatch label.
                #
                # ★★ AND WHY THIS IS NOT SIMPLY "COMPARE CONTRACTS". The cache holds NOTIONAL and
                # no mark. `cached_notional / mark_now` is not the cached contract count (the
                # cache was formed at earlier marks, and phase B adds fills at trade prices), so
                # revaluation and position change CANNOT be separated exactly from what is stored.
                # Storing a parallel contracts cache was rejected: `state["positions"]` is written
                # at six sites, and a second quantity that six writers must keep in step is the
                # caliber-split generator this repo keeps meeting.
                # ⇒ So the difference is graded RELATIVELY instead of pretended to be exact, and
                #   the note says which part of it is unknowable.
                #
                # ★ AND THIS IS A STALENESS NOTICE, NOT THE POSITION GUARD. Venue truth is adopted
                # either way — that behaviour is correct and is unchanged. Whether the book is
                # explained is §4-5b's question (full attribution walk) and whether it is where we
                # intended is §4-5e's; neither is weakened by anything here. What changes is only
                # which differences are worth waking someone for.
                _FLOOR, _BAND = 5.0, 0.05      # dust; and the revaluation band, relative
                _reval, _real = {}, {}
                for k in keys:
                    c, v = cached.get(k, 0.0), venue.get(k, 0.0)
                    d = abs(c - v)
                    scale = max(abs(c), abs(v), _FLOOR)
                    if d <= _FLOOR:
                        continue                       # below the venue's own minimum: not news
                    # a SIGN FLIP or a name on one side only is never revaluation, whatever its
                    # size — a price move cannot move a position across zero or create one
                    _structural = (c * v < 0) or (abs(c) <= _FLOOR) or (abs(v) <= _FLOOR)
                    (_real if (_structural or d / scale > _BAND) else _reval)[k] = (c, v)
                if _real:
                    self.alarm("HIGH", f"position reconcile: {len(_real)} name(s) differ from the "
                                       f"venue beyond revaluation (sign flip / one-sided / "
                                       f">{_BAND:.0%}) — adopting venue truth")
                # ★ the benign case is COUNTED AND RETURNED, never paged: a page that fires every
                # anchor is a page nobody reads, and this one fired on arithmetic that cannot be
                # avoided. `reconcile_summary` below travels in the phase_A dict that run_anchor
                # prints, so it is visible without inventing a second channel.
                # ★ NOT `self.log(...)`: `self.log` is the PilotLogger, not a logging function —
                # calling it would be a TypeError. That is the exact defect recorded 500 lines
                # down (a caller assuming `self.log` was a logger and reaching for a method it
                # does not have), and I nearly reproduced it here.
                out["reconciled"] = {k: {"cached": c, "venue": v}
                                     for k, (c, v) in list(_real.items())[:10]}
                out["reconcile_summary"] = {
                    "n_beyond_revaluation": len(_real), "n_within_revaluation": len(_reval),
                    "band": _BAND, "dust_floor_usdt": _FLOOR,
                    "caliber": ("both sides are NOTIONAL and the cache stores no mark, so the "
                                "revaluation part cannot be removed exactly; names are graded "
                                "relatively and sign flips / one-sided names are always REAL. "
                                "This is a cache-staleness notice — the position guards are "
                                "§4-5b (is the change explained) and §4-5e (is the book where we "
                                "intended).")}
                state["positions"] = venue
            except Exception as e:
                # cannot read venue: proceed on cache but SAY so — a silent fallback here
                # recreates the ghost-book problem one layer up
                self.alarm("HIGH", f"position readback failed ({e}); proceeding on cached book")
                out["reconcile_failed"] = str(e)

        # 0/3 — freshness decides the shape of this anchor before anything is priced
        preds = _load(PREDS_PATH, None)
        ext = None
        if _ext_cfg["source"] == "external":
            # ★ THE EXTERNAL FILE IS THE SIGNAL. The preds file is not consulted for freshness;
            #   the ladder's AGE comes from the newest USABLE external target — this file if it
            #   verified, else the last good one — so the pre-registered rungs apply unchanged
            #   (HOLD first, DERISK ≥24h, FLATTEN ≥48h; `on_unavailable: "hold"` pins HOLD).
            #   A failed read NEVER trades and NEVER falls back to the internal composer.
            ext = EXT.read_target(_ext_cfg, now=now,
                                  poll=(getattr(self.broker, "mode", "DRY_RUN") != "DRY_RUN"
                                        and os.environ.get("LIVE_EXTERNAL_WAIT", "1") != "0"))
            _agei = EXT.age_anchors(ext, _ext_cfg, state, now, ANCHOR_S)
            age = _agei["age_anchors"]
            out["external_book"] = EXT.record(ext, {"age_ref": _agei})
            if ext["ok"]:
                state["external_last_good_anchor_ts"] = int(ext["anchor_ts"])
                if ext.get("producer_prefix_fallback"):
                    # PREREG_deploy_exec_n6 §1.2: the sidecar did not rewrite the file within
                    # producer_grace_min — we trade the producer's own (king-form) file, as before
                    # the gate existed, but never silently.
                    self.alarm("HIGH", f"external book: 文件 producer={ext.get('producer')!r} 在宽限期内未被 "
                                       f"{ext.get('producer_prefix_expected')!r} 重写 — 本锚按生产者原文件(king 形态)交易"
                                       f"(与前缀门之前的回退语义相同); 检查 combo_live 守护。")
                if float(ext.get("gross_outside_frac") or 0.0) > EXT.OUTSIDE_UNIVERSE_ALARM_FRAC:
                    self.alarm("HIGH", f"external book: {ext.get('n_outside_universe')} 个名字 = 生产方 gross 的 "
                                       f"{float(ext.get('gross_outside_frac') or 0.0):.1%} 在其自己的宇宙之外(冻结尾巴) — "
                                       f"已从目标剔除并按宇宙内 Σ|w| 归一; 信息级(>{EXT.OUTSIDE_UNIVERSE_ALARM_FRAC:.0%} 才报), "
                                       f"生产方纸面书仍含尾巴。")
        else:
            age = signal_age_anchors(preds, now)
        action = staleness_action(age)
        if ext is not None and not ext["ok"]:
            # a failed read can never TRADE; `on_unavailable: hold` (config) or an UNKNOWN age (no
            # verified target ever seen — cold start / state reset) can never ESCALATE either: an
            # irreversible cut on missing information is the one thing worse than holding.
            if action == "TRADE" or _ext_cfg["on_unavailable"] == "hold" or age == float("inf"):
                action = "HOLD"
            self.alarm("HIGH", EXT.unavailable_text(ext, action))
        out["signal_age_anchors"] = round(age, 2) if age != float("inf") else "inf"
        out["action"] = action

        # ── one alarm per STAGE per episode (audit 3b): the file that says "a repeating
        # alarm trains the operator to ignore it" must not itself repeat alarms. Each stage
        # transition alerts exactly once; a fresh signal resets the episode entirely.
        def stage_alarm(stage: str, sev: str, msg: str):
            if stage not in state["alarmed_stages"]:
                self.alarm(sev, msg)
                state["alarmed_stages"].append(stage)

        if action == "TRADE":
            state["stale_ref_positions"] = None
            state["stale_ref_contracts"] = None
            state["alarmed_stages"] = []
            # ★ PASSED, not re-derived. `_trade` mints the batch id, and re-reading the gate there
            # would give the id's prefix a second chance to disagree with the halt exemption that
            # was granted from the same question 200 lines earlier.
            out.update(self._trade(preds, state, now,
                                   rehearsal=bool((out.get("_rehearsal") or {}).get("enabled")),
                                   external=ext))
        else:
            # snapshot the pre-stale book ONCE, at episode start — the ladder's reference
            if state.get("stale_ref_positions") is None:
                state["stale_ref_positions"] = dict(state.get("positions", {}))
            if action == "HOLD":
                stage_alarm("HOLD", "HIGH",
                            f"signal stale {age:.1f} anchors — HOLDING, no new orders")
                out["note"] = "held existing positions; no orders"
            elif action == "DERISK":
                frac = derisk_target_frac(age)
                stage_alarm(f"DERISK_{frac}", "CRITICAL",
                            f"signal stale {age:.1f} anchors — de-risking to {frac:.0%} of "
                            f"pre-stale gross, reduce-only")
                out.update(self._scale_to(state, frac))
            else:  # FLATTEN
                # ★ Severity follows CONSEQUENCE, not stage name. Flattening a book that holds
                # positions is CRITICAL. "Flattening" an EMPTY book (cold start, nothing ever
                # traded) is a no-op — a CRITICAL that wakes the operator at midnight for a
                # no-op trains alarm fatigue, which is the exact failure alarms exist to prevent.
                has_positions = any(abs(v) > 1e-9
                                    for v in state.get("positions", {}).values())
                if has_positions:
                    stage_alarm("FLATTEN", "CRITICAL",
                                f"signal stale {age:.1f} anchors (>=48h) — flattening book")
                    try:
                        setattr(self.broker, "flatten_client_prefix",
                                f"F{time.strftime('%Y%m%d%H%M%S', time.gmtime())}")
                    except Exception:                           # noqa: BLE001
                        pass
                    self.broker.flatten_all(state.get("positions", {}),
                                            "stale-signal ladder: FLATTEN")
                    state["positions"] = {}
                    out["note"] = "book flattened by staleness ladder"
                else:
                    stage_alarm("FLATTEN_COLD", "INFO",
                                "no signal yet and book is empty — idle (cold start, expected "
                                "until the preds producer is wired)")
                    out["note"] = "cold start: no signal, empty book, nothing to do"

        _save(STATE_PATH, state)
        return out

    # ── normal trading path ──────────────────────────────────────────────────────────────────
    # ── universe reality check: what the venue will actually let us trade ────────────────────
    def _size_book(self, target_leverage=None, leverage_source=None) -> Dict[str, Any]:
        """gross = nav x target_leverage, with a dead zone and a floor. Returns the decision.

        ★★ WHY CONSTANT LEVERAGE AT ALL (user's ruling 2026-07-29). Under a constant gross the
        risk budget grows on its own: equity falls, gross does not, effective leverage rises, and
        the same bad day costs a larger share of what is left. Measured on the historical series,
        the worst day was -17.0% of equity at 5.00x and -34.0% at 10.0x — the SAME day. Nobody
        ever decided to take more risk; arithmetic did it.

        ★★ THE THREE NUMBERS HERE ARE POLICY, and are kept apart from the arithmetic ones
        (liquidation ~ equity 296, structural death = gross/20) exactly as the operator card does:
        a policy number written in the same breath as an arithmetic one inherits its authority.

        ★ THE DEAD ZONE IS ABOUT COST, NOT ABOUT PRECISION. Re-sizing on every anchor turns the
        intraday noise of equity into real turnover: a 1% equity wobble would re-target ~1% of a
        9,200 USDT book, six times a day, for nothing. +/-10% is wide enough that only a genuine
        move re-sizes.

        ★ AND THE FLOOR HALTS RATHER THAN SHRINKS. Below it the min-notional cut removes names
        from the bottom up, so the surviving book is not a smaller version of the strategy but a
        concentrated residue of it. Measured breadth loss (N=109, testnet floors):
        gross 9,217 -> 7 names lost; 6,000 -> 8; 4,000 -> 10; 3,000 -> 13; 2,000 -> 21.
        ⇒ 4,000 is the lowest gross that keeps the loss at or under 10%.
        ⇒ It is NOT a competing gate with the -25% drawdown halt: that halt fires at 0.75x of
          starting equity, i.e. a gross of ~6,912 losing only 8 names. The floor is the backstop
          for a drawdown halt that failed, or for capital being withdrawn — not a routine limit.
        """
        cfg = _load(os.path.join(_REPO, "config", "book.json"), {}) or {}
        # ★ external book: the leverage IS `external_book.gross_mult` (design §1 target_gross =
        #   NAV x gross_mult). Same arithmetic, same dead zone, same floor — only the number's
        #   origin differs, and it is stamped so a row can say which policy sized it.
        tgt_lev = (float(cfg.get("target_leverage") or 2.0) if target_leverage is None
                   else float(target_leverage))
        lev_src = leverage_source or "config/book.json target_leverage"
        dead = float(cfg.get("leverage_deadzone_frac") or 0.10)
        floor = float(cfg.get("min_gross_usdt") or 0.0)
        nav = getattr(self, "_equity", None)
        prev = float(self.gross or 0.0)
        if nav is None or not float(nav) > 0:
            # ★ NO EQUITY IS NOT A REASON TO GUESS. Carrying the previous gross is the only
            # non-inventing option, and it is SAID rather than done quietly.
            # ★ THE SAME KEY SET AS THE NORMAL RETURN. A dict whose shape depends on which
            # branch produced it makes every consumer carry a `.get` or a KeyError — my own
            # first probe of this method hit exactly that. One shape, `blind` distinguishes it.
            return {"nav": None, "target_leverage": tgt_lev, "leverage_source": lev_src,
                    "actual_leverage": None,
                    "leverage_drift_frac": None, "deadzone_frac": dead, "resized": False,
                    "gross_previous": prev, "gross_wanted": None, "gross": prev,
                    "min_gross_usdt": floor, "halt": False, "blind": True, "halt_on": None,
                    "reason": ("equity unreadable this anchor — carrying the previous gross; "
                               "sizing is UNVERIFIED, which is not the same as unchanged"),
                    "caliber": "see the non-blind branch"}
        nav = float(nav)
        want = nav * tgt_lev
        actual = (prev / nav) if prev else None
        # the dead zone is judged on the leverage we are ACTUALLY running, not on the gross
        drift = None if actual is None else abs(actual / tgt_lev - 1.0)
        resize = (actual is None) or (drift is not None and drift > dead)
        gross = want if resize else prev
        out = {"nav": nav, "target_leverage": tgt_lev, "leverage_source": lev_src,
               "actual_leverage": actual,
               "leverage_drift_frac": None if drift is None else round(drift, 4),
               "deadzone_frac": dead, "resized": bool(resize),
               "gross_previous": prev, "gross_wanted": round(want, 2),
               "gross": round(gross, 2), "min_gross_usdt": floor, "halt": False, "blind": False, "halt_on": None,
               # ★ `reason` is present on EVERY return, empty when there is nothing to explain —
               # so a consumer never has to ask whether the key exists before reading it.
               "reason": "",
               "caliber": ("gross = nav x target_leverage, recomputed only when the ACTUAL "
                           "leverage has drifted more than the dead zone. target_leverage and "
                           "min_gross_usdt are POLICY numbers (config/book.json); the arithmetic "
                           "floors are elsewhere — liquidation from maintMarginRatio (arm A7) and "
                           "structural death at gross/bracket.")}
        # ★★★ THE FLOOR IS JUDGED ON `want`, NOT ON THE POSSIBLY-STALE `gross` — and the
        # interaction that forced this was measured, not imagined. With a dead zone the gross can
        # sit ABOVE the floor while the policy-implied size is below it:
        #     nav 1,950 -> want 3,900 (below the 4,000 floor); prev gross 4,200; drift 7.7%
        #     => inside the dead zone, no resize, gross stays 4,200, and the floor check PASSED.
        # A band of about nine percent right at the floor in which we would keep trading a book
        # the policy says is already too small to hold its own names. The floor is a statement
        # about the book we SHOULD hold, so it has to be judged on the size the policy asks for.
        # ⇒ THAT IS THE dead-zone x floor INTERACTION. The third member — the S1 per-name clamp —
        #   does NOT participate: it acts per symbol after the book size is fixed, so it can only
        #   shrink individual legs, never the gross. Recorded so the next reader does not have to
        #   re-derive which pairs actually interact.
        if want < floor or gross < floor:
            out["halt"] = True
            out["halt_on"] = ("policy-implied size (the dead zone was suppressing the resize)"
                              if want < floor <= gross else "current size")
            out["reason"] = (f"EXPOSURE FLOOR: nav {nav:.2f} x {tgt_lev} = {want:.0f} USDT is "
                             f"below the floor {floor:.0f}. Below it the min-notional cut takes "
                             f"names from the bottom up and what survives is a concentrated "
                             f"residue, not a smaller book — so this halts rather than shrinks. "
                             f"No orders this anchor.")
        return out

    def _universe_gate(self, pred_symbols, state, rebalance_id=None) -> Dict[str, Any]:
        """Run BEFORE planning. A coin can be delisted under us between anchors, and the normal
        order path cannot exit it (no book -> no mid -> no size). Exits here are price-free."""
        if self.broker.mode == "DRY_RUN":
            return {"skipped": "DRY_RUN"}
        st = UNI.venue_status(self.src)
        held_contracts = {}
        try:
            held_contracts = self.broker.positions()          # signed CONTRACTS, venue truth
        except Exception:
            pass
        cls = UNI.classify(pred_symbols, held_contracts, st)
        if cls.get("venue_status_unknown"):
            # unknown != nothing trades. Refusing to act on an unknown universe is the safe
            # default; the anchor proceeds on the predicted set and says so.
            self.alarm("HIGH", "exchangeInfo unreachable — universe status UNKNOWN this anchor; "
                               "proceeding on the predicted set without a delisting check")
            return {"venue_status_unknown": True}

        for o in UNI.exit_orders(cls["exit_only_held"], rebalance_id=rebalance_id):
            try:
                self.broker.submit(o, o["_reason"])           # reduce-only -> passes the halt
                # ★★★ RECORD IT. This exact action, unrecorded, cost the pilot two anchors and a
                # full liquidation on 2026-08-01: §4-5b explains a position change only from
                # `Σdq_fills`, so an exit with no row makes the change unexplained — identical, to
                # the guard, to a liquidation. The facts are BUFFERED here because `anchor_ts` is
                # minted later; `flush_exit_rows` materialises them. Buffering the ROW, never the
                # SUBMIT: the exit is protective and does not wait on bookkeeping.
                self.executor.note_exit_fill(o, self.broker)
            except Exception as e:
                self.alarm("CRITICAL", f"{o['symbol']} left TRADING and the exit FAILED ({e}) — "
                                       f"position may be settled by the venue. Check the app.")
                self.executor.note_exit_fill(o, None, error=str(e)[:160])
        if cls["exit_only_held"]:
            self.alarm("HIGH", f"exited {len(cls['exit_only_held'])} name(s) that left TRADING: "
                               f"{', '.join(list(cls['exit_only_held'])[:8])}")
        if cls["gone_from_venue_held"]:
            # No status, no book, no normal exit. The operator MUST hear this one.
            self.alarm("CRITICAL", "held position(s) VANISHED from exchangeInfo — no normal way "
                                   f"out: {', '.join(cls['gone_from_venue_held'])}. "
                                   f"Venue will settle these; verify in the app.")
        # ★ A THIRD ELIGIBILITY FACT, learned from the venue rather than from us: a symbol whose
        # `maxNotionalValue` is 0 is one the venue will not let us OPEN at all — every order in it
        # is a guaranteed -2027 ("Exceeded the maximum allowable position at current leverage").
        # It is neither a delisting (status is still TRADING) nor an account restriction, and it is
        # readable in advance from /fapi/v1/symbolConfig. Withholding these at planning time turns
        # a venue rejection into a non-event; the previous anchor spent one order discovering it.
        # Existing positions are NOT withheld — a cap of 0 blocks opening, not closing.
        blocked = set()
        _status_withheld = sorted(set(pred_symbols) - set(cls["tradable"]))          # E6: not TRADING (or gone), per name
        cfgmap = getattr(self.broker, "symbol_config", None) or {}
        if cfgmap:
            blocked = {sym for sym, c in cfgmap.items()
                       if float(c.get("maxNotionalValue") or 0) == 0}
            if blocked:
                shrunk = [s_ for s_ in cls["tradable"] if s_ not in blocked]
                if len(shrunk) != len(cls["tradable"]):
                    self.alarm("HIGH", f"{len(cls['tradable']) - len(shrunk)} name(s) withheld: "
                                       f"the venue reports maxNotionalValue=0 (no new position "
                                       f"permitted) — "
                                       f"{sorted(set(cls['tradable']) - set(shrunk))[:5]}")
                cls["tradable"] = shrunk
        return {"tradable": cls["tradable"], "n_exit_only": len(cls["exit_only_held"]),
                # ★ E6: the two venue reasons, per name, so the held-withheld page can say which one applies
                "withheld_status_names": _status_withheld,
                "withheld_zero_cap_names": sorted((set(pred_symbols) - set(_status_withheld)) & blocked),
                "n_zero_cap_withheld": len(blocked & set(cls["tradable"] + list(blocked))),
                "n_gone": len(cls["gone_from_venue_held"]),
                "n_new_listings_ignored": len(cls["new_listings"])}

    def _trade(self, preds: Dict[str, Any], state: Dict[str, Any], now: float,
               rehearsal: bool = False,
               external: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # ★★★ THE ID IS MINTED HERE, BEFORE THE UNIVERSE GATE (2026-08-01 incident).
        # It used to be minted after `capture_anchor`, ~100 lines below — but the universe gate
        # SENDS ORDERS (the exits for names that left TRADING), and at that moment there was no id
        # to stamp on them. Anonymous orders cannot be matched back by `venue_fills`, which keys on
        # the `{rebalance_id}-` prefix, so those executions could never enter our books at all.
        # ★ Moving it is SAFE BY THE FUNCTION'S OWN NATURE, and that is asserted rather than
        #   asserted-about: `mint(now, rehearsal)` is pure in both arguments and `now` does not
        #   change within this call, so the id is bit-identical to the one the old site produced.
        #   `tests_exit_ledger` pins that equality — "it is pure" is a claim about the code.
        import rebalance_id as _RID
        rid = _RID.mint(now, rehearsal)
        # ── M3-BEGIN  BTC-beta overlay leg (live/beta_overlay.py; PREREG_m3 24c3f803f). Resolved per anchor, reset per anchor.
        #    mode off (key absent) ⇒ nothing below changes the book, the orders or the loop state (tests_beta_overlay [Z]).
        self._m3 = {"mode": "off", "record": None}
        if getattr(self, "executor", None) is not None:        # a loop built without an executor (tests) stays constructible
            self.executor._m3_overlay_leg = None
            self.executor._m3_overlay_net_usdt = None
        try:
            _m3c = BO.config(BC.load())
        except Exception as _m3e:                              # noqa: BLE001 — unreadable ⇒ off, paged
            _m3c = {"mode": "off", "error": f"book config unreadable ({type(_m3e).__name__})", "present": True}
        _m3last = state.get("m3_overlay_last")
        if _m3c.get("error"):
            # a BROKEN config is not an explicit off: an active leg is FROZEN below (BO.config_fault), never unwound on a typo
            self.alarm("HIGH", f"M3 beta_overlay 配置无效: {_m3c['error']} — 本锚不加新对冲腿; "
                               + ("已持对冲腿冻结(不平掉)。" if BO.leg_active(_m3last) else "无在持对冲腿, 按 off 的书交易。"))
        if _m3c["mode"] != "off" and external is None:
            self.alarm("HIGH", f"M3 beta_overlay.mode={_m3c['mode']} 但本锚不是外部书 — 叠加腿只对外部书定义, 本锚按 off。")
            _m3c = dict(_m3c, mode="off", non_external=True)
        if (not _m3c.get("error")) and _m3c["mode"] in ("off", "shadow") and isinstance(_m3last, dict) and not _m3last.get("released_by"):
            # an EXPLICIT off / shadow (or a non-external anchor) RELEASES the leg: from here the held BTC is the book's again and
            # its rules unwind the hedge (one full unwind cost). Recorded so a later broken config cannot resurrect a stale leg.
            if BO.leg_active(_m3last):
                self.alarm("HIGH", f"M3 显式 {_m3c['mode']}{'(非外部书)' if _m3c.get('non_external') else ''}: 在持对冲腿自本锚起"
                                   f"交还书的规则撤下(一次对冲平仓成本)。")
            state["m3_overlay_last"] = dict(_m3last, released_by=("non_external" if _m3c.get("non_external") else _m3c["mode"]),
                                            released_rebalance_id=rid)
        self._m3 = {"mode": _m3c["mode"], "record": None, "error": _m3c.get("error"),
                    "max_combined_leverage": _m3c.get("max_combined_leverage")}
        # ── M3-END
        # ── EXTERNAL BOOK (DESIGN_wide_live_deployment_2026-08-22 §1) ──────────────────────
        # ★ The four DL-preds gates below (caliber stamp / frozen-input census / column set /
        #   universe OOD) judge the PREDS FILE, which does not decide an external anchor's book.
        #   They are SKIPPED — and the skip is written into the record rather than faked as a
        #   pass. Everything that is a VENUE fact (universe gate, per_name_stop, withhold ->
        #   reshape, clamp/flatten_only, executor) runs unchanged below.
        _is_ext = external is not None
        if _is_ext:
            preds = preds or {}
            # ★ symbols = the producer's IN-UNIVERSE non-zero names ∪ every name we HOLD. A held name the
            #   producer no longer targets (left its universe / member set, or weight 0) is EXITED through
            #   the existing clamp -> flatten_only channel (maker reduce-only, mandatory top-up after) —
            #   NOT market-exited by the universe gate, which stays reserved for names whose venue status
            #   is no longer TRADING. Out-of-universe names we do NOT hold are simply absent (popped at
            #   the reader: `external["w"]` is the in-universe book, normalised by its own sum|w|).
            self._ext_held_exit = EXT.held_not_in_target(state.get("positions"), external["symbols"])
            symbols = sorted(set(external["symbols"]) | set(self._ext_held_exit))
            # ── M3-BEGIN  mode on: BTC is always priced, venue-gated, stop-checked and meta-checked with the book's names. A BTC
            #    the file does not target and we do not hold enters with weight 0 and is dust-popped by the book stage exactly as an
            #    absent name (the book is unchanged); the leg then reaches it through the combined value (M3b).
            if self._m3["mode"] == "on":
                symbols = sorted(set(symbols) | {BO.BTC})
            # ── M3-END
            out_census = {"skipped": "external_book — the DL artifact census does not decide this book"}
            want = None
            _ood_report = {"state": "SKIPPED_EXTERNAL", "n_members": len(symbols), "n_ood": None,
                           "ood_symbols": [], "blind": True,
                           "does_not_establish": "anything — the frozen DL model is not scoring this book"}
        else:
            # ── caliber stamp assertion (audit ②): the split-path guarantee must be a MECHANISM,
            # not a convention. preds declare their calibers; we assert against config; mismatch
            # BLOCKS the anchor. Closes the chain config -> stamp -> consumption, the same shape
            # as the protocol's registry -> declaration -> observation chain.
            expected = _load(os.path.join(_REPO, "config", "book.json"), {}).get("factor_versions")
            stamped = preds.get("factor_versions")
            if expected and stamped != expected:
                self.alarm("CRITICAL", f"caliber stamp mismatch: preds={stamped} config={expected} "
                                       f"— anchor BLOCKED, no orders")
                return {"blocked": "caliber_stamp_mismatch", "preds_stamp": stamped,
                        "expected": expected}

            # ── [B27] THE FROZEN-INPUT CENSUS: is every artifact that decides a prediction the one
            # we signed? ────────────────────────────────────────────────────────────────────────
            # ★★ NOTHING COMPARED THESE. `checkpoints/MANIFEST.json` carries the signed fingerprints,
            # `signal/inference.load()` RE-COMPUTES them at every load and stamps them into
            # preds_latest.json under `models` — and no code anywhere reads one against the other.
            # Two independent recordings of the same quantity, compared never; a swapped checkpoint
            # would have travelled all the way to an order. (Fifth member of this repo's
            # writer-with-no-reader family, after pilot_log.fill, FundingLedger, the 5c error-code
            # fast path and `state_root.read_stamped`.)
            # ★ IT BLOCKS ON MISMATCH, matching the precedent one block up: when we cannot establish
            # WHICH model is speaking, the anchor does not trade. A missing pin or an unpinnable
            # artifact ALARMS but does not block — "we have not fingerprinted it yet" is a different
            # statement from "it is not what we signed", and collapsing them would make the strong
            # signal unreadable.
            try:
                import frozen_inputs as _FI
                _cen = _FI.census()
                _undecl = _FI.undeclared()
                out_census = {k: v for k, v in _cen.items() if k != "rows"}
                out_census["undeclared_artifacts"] = _undecl
                _bad = [r for r in _cen["rows"] if r["state"] in ("MISMATCH", "ABSENT")]
                if _bad:
                    self.alarm("CRITICAL",
                               f"frozen-input census FAILED for {[r['artifact'] for r in _bad]} — the "
                               f"model's inputs are not the ones we signed; anchor BLOCKED, no orders")
                    return {"blocked": "frozen_input_mismatch", "census": out_census,
                            "failed": [{k: r[k] for k in ("artifact", "state", "expected", "observed")}
                                       for r in _bad]}
                # ★ ONE FACT, ONE VOICE: an unpinnable artifact that already has its own guard
                # (`alarmed_by`) is recorded and not re-alarmed here — `training_member_union` is
                # named by universe_guard at this same anchor, and two HIGH alarms for one missing
                # file is how an alarm stream stops being read. One WITHOUT its own guard still
                # alarms, so quiet is never the default.
                _unvoiced = _cen.get("unvoiced_unpinnable") or []
                if _cen["n_missing_pin"] or _undecl or _unvoiced:
                    self.alarm("HIGH",
                               f"frozen-input census: {_cen['n_missing_pin']} artifact(s) not "
                               f"fingerprinted, {len(_unvoiced)} unpinnable with no guard of their "
                               f"own {_unvoiced}, {len(_undecl)} undeclared {_undecl} — a change in "
                               f"any of them changes every prediction and nothing would notice")
            except Exception as e:
                out_census = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
                self.alarm("HIGH", f"frozen-input census could not run ({type(e).__name__}) — "
                                   f"the model's inputs are unverified this anchor")

            # ── column-set assertion: the CROSS-SECTION is part of the model ──────────────────────
            # The panel encoder attends ACROSS columns, so a changed column set changes every
            # prediction, not just the new column's. The producer stamps the ordered column list; we
            # refuse preds we cannot recognise. Absent stamp also BLOCKS -- "the producer forgot" and
            # "the column set changed" are indistinguishable from here, and both are unsafe.
            try:
                import sys as _sys
                _sig = os.path.join(_REPO, "signal")
                if _sig not in _sys.path:
                    _sys.path.insert(0, _sig)
                import compute_preds as _CP
                import live_panel as _LP
                want = _CP.columns_fingerprint(_LP.panel_symbols())
            except Exception as e:                       # cannot establish the expected set
                want = None
                self.alarm("HIGH", f"could not compute the expected column fingerprint ({e}); "
                                   f"column-set assertion SKIPPED this anchor")
            if want is not None:
                got = {k: (preds.get("panel") or {}).get(k) for k in ("n_columns", "columns_sha256")}
                if got != want:
                    self.alarm("CRITICAL",
                               f"prediction column set does not match the frozen universe: "
                               f"preds={got} expected={want} — anchor BLOCKED, no orders")
                    return {"blocked": "column_set_mismatch", "preds_columns": got, "expected": want}
            symbols = preds["symbols"]
            # ★ [B27] IS THE FROZEN MODEL BEING ASKED ABOUT A COIN IT NEVER SAW?
            # Membership is reselected monthly while the model is frozen. The encoder has no per-coin
            # parameters, so an unseen coin is scored perfectly normally — the failure is silent BY
            # CONSTRUCTION, which is exactly why it needs a voice. Blind (no pinned training set) also
            # alarms: "we did not check" must not read like "we checked and it was fine".
            # ★ THE VERDICT IS RETURNED, NOT ASSIGNED INTO SOME OTHER SCOPE'S DICT. The first version
            # wrote `out[...]` — `run_anchor`'s name, not one that exists here — so every anchor raised
            # NameError, the except below relabelled it "check failed", and the guard's only observable
            # in production was its own error handler. `_trade`'s return is merged into `run_anchor`'s
            # record (`out.update(self._trade(...))`), so returning it is what makes it visible.
            _ood_report: Optional[Dict[str, Any]] = None
            try:
                import universe_guard as _UG
                _ood = _UG.check_members(symbols)
                # ★★ THE PROJECTION MUST CARRY THE VERDICT'S OWN LIMITS, NOT JUST ITS ANSWER.
                # This was a hand-picked five-key subset, so when `check_members` gained `guards` /
                # `does_not_establish` / `evidence_ceiling` (2026-07-29, when the training union was
                # pinned) the anchor's record kept reporting a bare `state: OK` — the wording existed
                # in the guard and reached no reader, which is the "produced a property nobody
                # consumes" shape this repo keeps paying for. The limits travel WITH the answer or the
                # answer is read as unqualified.
                # ⇒ `.get` because the three are absent on an OOD result by design (the
                #   subset-by-construction excuse is false there and must not be printed).
                _ood_report = {k: _ood.get(k) for k in
                               ("state", "n_members", "n_ood", "ood_symbols", "blind",
                                "guards", "does_not_establish", "evidence_ceiling")}
                _txt = _UG.ood_alarm_text(_ood)
                if _txt:
                    self.alarm("HIGH", _txt)
            except Exception as e:
                _ood_report = {"state": "CHECK_FAILED", "error": f"{type(e).__name__}: {str(e)[:120]}",
                               "n_members": len(symbols), "n_ood": None, "ood_symbols": [],
                               "blind": True}
                self.alarm("HIGH", f"universe OOD check failed ({type(e).__name__}: {str(e)[:70]}) — "
                                   f"a frozen model is scoring {len(symbols)} coins unverified")
        gate = self._universe_gate(symbols, state, rebalance_id=rid)
        if gate.get("tradable") is not None and not gate.get("venue_status_unknown"):
            # compose on the FULL predicted cross-section (ranks/z-scores are cross-sectional —
            # dropping names before scoring would silently change every other name's weight),
            # then withhold orders for the untradable ones at the planning stage.
            self._untradable = set(symbols) - set(gate["tradable"])
        else:
            self._untradable = set()
        # ★ E6: every source that adds to `_untradable` is recorded per name, for the held-withheld page
        self._untradable_sources = {"venue_not_trading": set(gate.get("withheld_status_names") or ()),
                                    "venue_zero_cap": set(gate.get("withheld_zero_cap_names") or ())}
        # ── 逐名止损条款(cf40ea21): stop 名与冷却名并入 untradable ⇒ 复用既有 pop/clamp/
        #    reduce-only 全通道。stop 名的目标恰为 0 由 withhold 接缝函数的 force_flat 参数保证(_pns_zero_targets, W9)。
        self._pns_sets = {"stop": set(), "cooldown": set()}
        if PNS.cfg_enabled():
            try:
                self._pns_sets = PNS.active_sets(PNS.load_state(), time.time())
                _pns_all = self._pns_sets["stop"] | self._pns_sets["cooldown"]
                if _pns_all:
                    # 不在此重复告警(冷却期 42 锚会刷屏 — BNB 告警疲劳教训#60): 触发/转冷却/期满
                    # 的一次性告警在终锚钩子; 每锚的持续状态由 clamp 通道的 withheld 告警与
                    # anchors 行的 per_name_stop 字段承载。
                    self._untradable = set(self._untradable) | _pns_all
                    self._untradable_sources["per_name_stop"] = set(self._pns_sets["stop"])
                    self._untradable_sources["per_name_stop_cooldown"] = set(self._pns_sets["cooldown"])
            except Exception as _e:
                self.alarm("HIGH", f"per_name_stop 状态读取失败({type(_e).__name__}) — 条款本锚未生效, "
                                   f"计数状态未损失(只读路径)")
        # ── external book: venue ELIGIBILITY beyond `status` (design §1 '450 候选 ∩ 交易所
        #    TRADING COIN perp', 非 ASCII/股票类名排除) — probe v2's rule, pure fn over exchangeInfo.
        #    Excluded names join `_untradable` ⇒ pop if unheld / clamp if held (reduce-only).
        #    DRY_RUN skips the fetch exactly as _universe_gate does.
        self._ext_meta = None
        if _is_ext and self.broker.mode != "DRY_RUN":
            try:
                _exi = self.src._get("/fapi/v1/exchangeInfo").get("symbols", [])
                self._ext_meta = EXT.venue_meta_exclusions(_exi, symbols)
                if self._ext_meta:
                    self._untradable = set(self._untradable) | set(self._ext_meta)
                    self._untradable_sources["external_meta"] = set(self._ext_meta)
            except Exception as _e:                  # noqa: BLE001
                self.alarm("HIGH", f"external book: exchangeInfo 元数据过滤不可用({type(_e).__name__}) — "
                                   f"本锚只按 status 门过滤(非 COIN/非 ASCII 名未排除)")

        if _is_ext and getattr(self, "_ext_held_exit", None):
            # held names the producer no longer targets ⇒ reduce-only exit via clamp/flatten_only
            self._untradable = set(self._untradable) | set(self._ext_held_exit)
            self._untradable_sources["external_held_exit"] = set(self._ext_held_exit)
        if _is_ext:
            # ★ THE PRODUCER'S WEIGHTS ARE THE TARGET (design §1): no compose_book, no risk budget,
            #   no harvest EMA, no neutral band. target_w = w / gross_norm (unit gross), so the
            #   book below is exactly w/gross_norm x NAV x gross_mult before venue withholds.
            book = {"target_w": EXT.target_vector(external, symbols)}
            _bw = {"book_source": "external", "gross_mult": external["gross_mult"]}
            self._last_harvest_ema = {"alpha": None, "applied": False, "n_carried": 0,
                                      "n_symbols": len(symbols), "reset_by_trip": False,
                                      "skipped": "external_book"}
        else:
            # signal: split-path caliber is enforced by construction — funding comes from the
            # corrected fapi series HERE; king/s2 arrive precomputed from the as-trained panel.
            import numpy as np
            fund = np.array([preds["funding_ema"].get(s, np.nan) for s in symbols], float)
            dvol = np.array([preds["dvol30"].get(s, np.nan) for s in symbols], float)
            king = np.array([preds["king"].get(s, np.nan) for s in symbols], float)
            s2 = np.array([preds["s2"].get(s, np.nan) for s in symbols], float)
            # ★★★ THE WEIGHTS COME FROM config/book.json, NOT FROM legs.py's LITERAL (2026-08-01).
            # This line read `LG.compose_book(king, s2, fund, dvol)` — no weights — so the function
            # fell back to its own module constant and `book.json["weights"]` had ZERO readers in the
            # whole repo. Switching the book by editing that file would have changed the config, every
            # record citing it, and nothing about the orders; no guard could have seen the gap,
            # because both halves were internally consistent.
            # ⇒ `tests_book_weights_effective` mutates the file and requires the ORDERING weights to
            #   move with it — the caliber is the book we send, never the file agreeing with itself.
            _bw = BC.weights()
            # risk budget: config-driven (single source config/book.json), rvol from the SAME preds
            # file as every other input. Old preds without `rvol24` -> all-NaN -> compose_book no-op.
            _rb = _load(os.path.join(_REPO, "config", "book.json"), {}).get("risk_budget")
            rv = np.array([(preds.get("rvol24") or {}).get(s, np.nan) for s in symbols], float)
            book = LG.compose_book(king, s2, fund, dvol, weights=_bw, rvol=rv, risk_budget=_rb)
            # ── 收割速度 EMA (PREREG_harvest_speed_acceptance, sha 53ab6f5a74bd8ef8) ──────────────
            # ★ 默认 alpha=1.0 ⇒ 逐位无操作。状态按【名字】存在 state/live/harvest_ema.json。
            # ★★ halt/flatten 之后必须重置: 平仓后我们持有的是零, 而 EMA 会把清仓前的权重拖过断点,
            #    让书以为自己还持有那些仓位。`reduce_only` 或 watchdog 已触发 ⇒ 丢弃状态。
            # ★★★ 2026-08-06 10:1xZ 修复一个【已经打在实盘上】的缺陷。上一版这里是:
            #       _wd_path = ...os.path.join(_REPO, "state", "watchdog", "state.json")
            #       _tripped = os.path.exists(_wd_path)
            #   两处都错: (a) 路径写死成 DRY_RUN 树 —— 与它上面那行自己写的"用与开仓门同一个路径来源,
            #   不另造一份"正好相反(注释给出了规则, 代码没有兑现它); (b) 谓词是【文件在不在】, 而三个
            #   mode 的 watchdog 状态文件长期都在、内容都是 tripped_at:null(未触发) ⇒ 恒判"已触发"
            #   ⇒ prev 恒为 None ⇒ **a=0.3 静默退化成逐位无操作**, 而 `applied:true` 照写。
            #   实盘回执: state/live/harvest_ema.json 写于 08:39:55Z(08:00Z 锚), n_carried=0。
            #   ★ 首锚 n_carried=0 本来就正常 ⇒ 该读数【不具判别力】, 判定来自对表达式的直接求值。
            import state_root as _SRh
            _mode_h = os.environ.get("LIVE_MODE", "DRY_RUN")
            _ph = _SRh.paths_for(_mode_h)
            # ★ env 可重定向, 与 LIVE_WATCHDOG_STATE 同族。实测缺它的代价: 09:51:54Z 验收电池里
            #   tests_signal_and_loop 进程内跑 _trade, 把 EMA 状态写进了【真实】DRY_RUN 树
            #   (state/harvest_ema.json) —— 测试写生产树, 与今天堵掉的 anchor_runs.log 污染同形。
            _hp = os.environ.get("LIVE_HARVEST_STATE",
                                 os.path.join(_ph["root"], "harvest_ema.json"))
            _ha = float((_load(os.path.join(_REPO, "config", "book.json"), {})
                         .get("harvest_ema") or {}).get("alpha", 1.0))
            _wd_path = os.environ.get("LIVE_WATCHDOG_STATE", _ph["watchdog_state"])
            # ★★★ read_stamped 是裸的 `json.load(open(path))` —— `strict` 只管【跨模式】那一支,
            #   文件缺失或 JSON 损坏一律抛。而"文件缺失"恰恰是我上一行推理过的那个场景
            #   (resume_from_trip.sh:263 会 remove 它)。第一版直接调用 ⇒ **一次正常恢复之后,
            #   这里会抛 FileNotFoundError 并杀掉整个锚点** —— 比它要修的"EMA 空转"严重得多。
            #   电池的 tests_signal_and_loop 当场逮住(它构造的临时树里没有 state.json)。
            #   ⇒ 又一次"守卫就差你停下的下一行": 我把语义推对了, 然后调用了一个处理不了该语义的函数。
            _present = os.path.exists(_wd_path)
            _wdh, _noteh = None, None
            if _present:
                try:
                    _wdh, _noteh = _SRh.read_stamped(_wd_path, _mode_h, strict=False)
                except Exception as _e:                       # noqa: BLE001 — 读不出 ⇒ fail-closed
                    _wdh, _noteh = None, f"unreadable: {type(_e).__name__}"
            _rst = LG.harvest_reset_required(_wdh, _noteh, _present)
            _tripped = bool(_rst["reset"])
            _prev = None if _tripped else (_load(_hp, {}) or {}).get("state")
            _hz = LG.apply_harvest_ema(book["target_w"], symbols, _prev, _ha)
            book["target_w"] = _hz["target_w"]
            try:
                _save(_hp, {"state": _hz["state"], "alpha": _hz["alpha"],
                                    # ★ anchor_ts 此处尚未赋值(它在 capture_anchor 之后才出现) ——
                                    # 用【已经存在】的 rebalance_id 与本次调用的 now, 不引用未来的名字。
                                    "rebalance_id": rid, "written_at": now, "applied": _hz["applied"],
                                    "n_carried": _hz["n_carried"],
                                    # ★ 记真实理由, 不记一个笼统的 "watchdog tripped" —— 上一版
                                    #   无论何种原因都写同一句, 于是"文件恒在"这个错因在记录里
                                    #   看起来与真正的触发一模一样。
                                    "reset_reason": _rst["reason"], "mode": _mode_h,
                                    "watchdog_state_path": _wd_path})
            except Exception as _e:
                # 同上: 本类里没有 `log`。写失败必须留痕, 否则下一锚从 raw 重来 = 静默退化成 alpha=1.0
                self._last_harvest_ema_error = f"{type(_e).__name__}: {str(_e)[:80]}"
                self.alarm("HIGH", f"harvest_ema 状态写入失败({type(_e).__name__}) — 下一个锚会从 raw "
                                   f"重新起步, 等于静默退化成 alpha=1.0(不平滑), 而没有任何读数会变红")
            # ★ 报告走【返回的 phase_A dict】, 不另造日志通道 —— `log` 是 run_anchor 的模块级名字,
            #   本类里不存在; `self.log` 是 PilotLogger 不是记录函数(调用它是 TypeError, 该缺陷已在
            #   本文件 855 行登记过)。我按邻行 `self._last_sizing` 的写法挂在实例上, 由 phase_A 取。
            self._last_harvest_ema = {"alpha": _hz["alpha"], "applied": _hz["applied"],
                                      "n_carried": _hz["n_carried"], "n_symbols": len(symbols),
                                      "reset_by_trip": bool(_tripped)}
        # ★★★ CONSTANT LEVERAGE REPLACES CONSTANT EXPOSURE (user's ruling 2026-07-29).
        # `gross` was a config constant, so as equity fell the effective leverage rose and nobody
        # decided that — the risk budget was being enlarged by arithmetic. It is now
        # `nav x target_leverage`, recomputed here, every anchor.
        # ★★ σ_fund gross ladder (PREREG_deploy_sigma_ladder_2026-09-04) — WITHDRAWN, AND NO LONGER READ (OPS-01b, FX-EXEC 2026-09-13).
        #   It multiplied target_leverage by g in {0.5, 1.0} taken from a dashboard-written state file. The ladder was withdrawn by
        #   ruling; its launchd producer was disabled and its plist retired at 2026-09-13T14:00:50Z (OPS-01). This reader stayed: any
        #   fresh, well-formed g=0.5 file — written by hand, restored from a backup, or produced by a job someone re-enables — halved
        #   target gross on the next anchor with nothing louder than an INFO line. (It also read ~/dl_quant_live/state by default, so a
        #   test process could be sized by the LIVE tree's file.)
        #   ⇒ No file sets exposure any more: sizing is NAV x gross_mult, the call that was already the default path. live/sigma_ladder.py
        #     stays (tests_sigma_ladder pins the evaluator) but nothing on the anchor path imports it; the record below says the rule was
        #     not applied, so an anchors row can never be read as "ladder at g=1.0 by choice". Re-instating a ladder is a new ruling and a
        #     new wiring, not a file.
        if _is_ext:
            _bw["gross_ladder"] = {"src": "sigma_ladder", "g": 1.0, "accepted": False,
                                   "reason": "retired_not_read (OPS-01b: ladder withdrawn; producer disabled 2026-09-13T14:00:50Z)"}
        _sz = self._size_book(target_leverage=(external["gross_mult"] if _is_ext else None),
                              leverage_source=("external_book.gross_mult" if _is_ext else None))
        out_sizing = _sz
        self._last_sizing = _sz
        if _sz.get("halt"):
            # ★ BELOW THE EXPOSURE FLOOR WE STOP, WE DO NOT SHRINK. A book too small to carry its
            # own names is not a smaller version of the strategy — the min-notional floor removes
            # names from the bottom up, so what survives is a concentrated residue with the
            # breadth the strategy depends on gone. Halting is the honest outcome.
            self.alarm("CRITICAL", _sz["reason"])
            try:
                self.broker.halt_opening_orders(_sz["reason"])
            except Exception as e:
                self.alarm("CRITICAL", f"exposure floor breached AND the opening halt FAILED "
                                       f"({e}) — this anchor may still open positions")
            return {"blocked": "exposure_floor", "sizing": _sz}
        self.gross = _sz["gross"]
        target = LG.to_notional(book["target_w"], symbols, self.gross)
        # ★★★ [S1] WITHHELD MEANS "CANNOT OPEN", NOT "CANNOT CLOSE" — AND THE CODE USED TO MEAN
        # THE SECOND. `target.pop()` erased the name from the target dict, `plan()` iterates the
        # target, so a WITHHELD-BUT-HELD name produced NOT ONE ROW: no reduction, no record, no
        # alarm. The position was silently orphaned. Meanwhile the comment beside the withholding
        # rule (see `_universe_gate`) has always read "Existing positions are NOT withheld — a cap
        # of 0 blocks opening, not closing" — **the comment said the opposite of what the code
        # did**, which is why reading either one alone could not find it.
        # ⇒ ARKMUSDT is in exactly this state today (maxNotionalValue = 0, still predicted). It has
        #   never been entered, so nothing has been orphaned YET; the reachable sequence is
        #   hold -> venue restricts -> orphan, and no step of it is exotic.
        # ⇒ So: CLAMP, do not pop. The four cases, which is the whole rule:
        #     not held            -> pop, as before (nothing to close, and we may not open)
        #     same sign, |t|<=|c| -> keep  (a REDUCTION; permitted)
        #     same sign, |t|> |c| -> clamp to c (an ADD; forbidden, so no order, and it is counted)
        #     opposite sign or 0  -> clamp to 0 (flattening is a pure reduction; going PAST zero
        #                            would open the other side, so it stops exactly at flat)
        #   The last case is the one that is easy to get wrong: a target of -300 against a +200
        #   position is a 500 order, of which only the first 200 is a close.
        # ⇒ The comment is now true of the code, so the comment does not change.
        _held_book = state.get("positions", {})
        try:
            _fl = {s_: float((self.executor.filters.f.get(s_) or {}).get("min_notional", 0.0)
                             or 0.0) for s_ in target}
            _fl_src = "executor.filters.f[*].min_notional"
        except Exception as _e:
            _fl, _fl_src = None, f"UNAVAILABLE ({type(_e).__name__}) — floor crossings NOT checked"
        # ── external book: 2x min-notional ELIGIBILITY (design §1 '最小名义额可达 NAV×gross/名 ≥
        #    2×minNotional'): a name that cannot clear twice its floor cannot be ADJUSTED later, so
        #    it is withheld here — unheld ⇒ popped (then the reshape re-demeans/rescales the rest),
        #    held ⇒ clamped reduce-only. Recorded every anchor; paged only above EXT_DUST_ALARM_FRAC.
        self._ext_dust = None
        if _is_ext:
            self._ext_dust = EXT.below_min_notional(target, _fl, external["min_notional_mult"])
            if self._ext_dust["names"]:
                self._untradable = set(getattr(self, "_untradable", ())) | set(self._ext_dust["names"])
                self._untradable_sources = dict(getattr(self, "_untradable_sources", None) or {}, external_dust=set(self._ext_dust["names"]))
            if (self._ext_dust.get("mass_frac") or 0.0) > EXT_DUST_ALARM_FRAC:
                self.alarm("HIGH", f"external book: {self._ext_dust['n']} 个名字的目标名义额低于 "
                                   f"{external['min_notional_mult']:g}×minNotional, 合计 gross 的 "
                                   f"{self._ext_dust['mass_frac']:.1%} (>{EXT_DUST_ALARM_FRAC:.0%}) 被撤下 — "
                                   f"NAV×gross_mult 对 450 名宇宙太小, 广度损失是个发现, 不是噪声。")
        # _pns_zero_targets: stop 名目标必须【恰为 0】并落 flatten_only(条款 cf40ea21 动作 = flatten, 非 reduce)。
        # ★ W9 更正(2026-09-13): 这里原先在调用前 `target[_s] = 0.0`, 注释写「置零后 clamp pass-2 的 tgt*cur>0 恒假 ⇒ 必落
        #   flatten_only」—— 与代码相反: 置零与 clamp 之间隔着 reshape 的 re-demean, 它把这些 0 平移成 a(撤名残差 net_before<0
        #   ⇒ a>0), 与 a 同号的已停持仓被判 add_blocked 钉住或 reduced 砍到 ≈ a(实盘 08-20..09-12 157 例中 144 例多头)。
        #   现在由拥有 POP → RESHAPE → CLAMP 顺序的函数负责: stop 集以 force_flat 传入, 移出重整人口, 重整后恰为 0, 再 clamp。
        # ── M3-BEGIN  BTC's untradability, classified BEFORE the book stage (which runs exactly as in mode off): name-level
        #    reasons (hard) suspend the leg; `external_dust` alone lets the COMBINED value decide (M3b, AMENDMENT_1 912788743).
        _m3_hard = BO.hard_block(getattr(self, "_untradable", ()), getattr(self, "_untradable_sources", None))
        _m3_dust_only = BO.dust_only(getattr(self, "_untradable", ()), getattr(self, "_untradable_sources", None))
        # ── M3-END
        _clamp, _rs = apply_withhold_and_reshape(
            target, _held_book, getattr(self, "_untradable", ()), self.gross,
            floors_usdt=_fl, floors_source=_fl_src,
            force_flat=getattr(self, "_pns_sets", {}).get("stop", ()))
        if _rs is not None and _rs["names_crossed_floor"]:
            # ★ A REAL NEW FACT, not bookkeeping: the correction moved a name across the venue's
            #   minimum, so it will now trade when it would not have (or the reverse). Reported,
            #   never iterated away — one pass, or we converge on a book nobody specified.
            self.alarm("HIGH",
                       f"重整后 {len(_rs['names_crossed_floor'])} 个名字跨过了 min_notional 门槛: "
                       f"{_rs['names_crossed_floor'][:8]} — 这些名字的可交易性由这次重整改变, "
                       f"不是由信号改变。仅报告, 不迭代。")
        if _rs is not None and abs(_rs["net_before"]) > RESHAPE_RESIDUAL_ALARM_FRAC * max(
                self.gross, 1e-9):
            # the CORRECTION is routine; a correction THIS LARGE means the universe gate took out
            # a slice of the book big enough that "we fixed it" is not the whole story.
            self.alarm("HIGH", reshape_residual_alarm_text(_rs, self.gross))       # E6 (EXE-03): producer net and removed net, separately
        if any(_clamp[k] for k in ("reduced", "add_blocked", "flatten_only")):
            # ★ HIGH, and it names the disposition per name. A held position the venue will not
            # let us re-open is a state an operator has to know about while it lasts — and until
            # this fix the only way to learn of it was to notice the position was not moving.
            self.alarm("HIGH", held_withheld_alarm_text(_clamp, getattr(self, "_untradable_sources", None) or {}))   # E6: per-name source
        out_clamp = _clamp
        # ── M3-BEGIN  the independent leg, AFTER POP -> RESHAPE -> CLAMP (prereg §2 step 4): beta on the EXECUTED book.
        #    shadow ⇒ validated + computed + recorded, target untouched; on ⇒ target[BTCUSDT] = book component + hedge.
        if self._m3["mode"] == "off" and self._m3.get("error") and _is_ext:
            # R10 §5 A.4-4/11: a broken config FREEZES an active leg (explicit off / shadow unwinds it); no active leg ⇒ None
            _m3f0 = BO.config_fault(target, _held_book, _m3_hard, state.get("m3_overlay_last"), self._m3["error"])
            if _m3f0 is not None:
                self._m3["record"] = _m3f0["record"]
                for _m3sev, _m3msg in _m3f0["alarms"]:
                    self.alarm(_m3sev, _m3msg)
                self.executor._m3_overlay_net_usdt = _m3f0["overlay_net_usdt"]
                _m3f0["record"]["prev"] = state.get("m3_overlay_last")
                state["m3_overlay_last"] = dict(state.get("m3_overlay_last") or {}, rebalance_id=rid,
                                                nominal_ts=external.get("anchor_ts"), status=_m3f0["record"]["status"],
                                                leg_active=(_m3f0["record"]["status"] == "frozen_config_invalid"))
        if self._m3["mode"] != "off":
            _m3o = BO.stage(self._m3["mode"], target, _held_book, external, self.gross, _m3_hard,
                            prev_status=(state.get("m3_overlay_last") or {}).get("status"),
                            btc_floor=(_fl or {}).get(BO.BTC), dust_mult=(external or {}).get("min_notional_mult"),
                            btc_dust_only=_m3_dust_only, max_combined_leverage=self._m3.get("max_combined_leverage"),
                            nav=(getattr(self, "_last_sizing", None) or {}).get("nav"),
                            prev_leg_active=BO.leg_active(state.get("m3_overlay_last")))
            self._m3["record"] = _m3o["record"]
            self._m3["betas"] = _m3o["betas"]
            if _m3o["release_btc"]:
                # the combined value overruled the book-component dust: BTC leaves the clamp's lists, so it is not sent reduce-only
                _m3o["record"]["released_from"] = sorted(k for k in ("reduced", "add_blocked", "flatten_only", "popped")
                                                         if BO.BTC in (_clamp.get(k) or []))
                for _m3k in ("reduced", "add_blocked", "flatten_only", "popped"):
                    _clamp[_m3k] = [s_ for s_ in (_clamp.get(_m3k) or []) if s_ != BO.BTC]
            for _m3sev, _m3msg in _m3o["alarms"]:
                self.alarm(_m3sev, _m3msg)
            if self._m3["mode"] == "on":
                self.executor._m3_overlay_leg = _m3o["leg"]
                self.executor._m3_overlay_net_usdt = _m3o["overlay_net_usdt"]
                _m3o["record"]["prev"] = state.get("m3_overlay_last")
                _m3st = _m3o["record"].get("status")
                state["m3_overlay_last"] = {"rebalance_id": rid, "nominal_ts": external.get("anchor_ts"),
                                            "status": _m3st,
                                            "hedge_target_usdt": _m3o["record"].get("hedge_target_usdt"),
                                            "btc_combined_target_usdt": _m3o["record"].get("btc_combined_target_usdt"),
                                            # a placed leg, or a refused anchor that FROZE a leg we already held
                                            "leg_active": bool(_m3st in BO.APPLIED or (_m3st == "refused" and _m3o["record"].get(
                                                "btc_frozen_at_usdt") is not None and BO.leg_active(_m3o["record"]["prev"])))}
        # ── M3-END

        if _is_ext:
            # ★ design §1: the external book is NOT passed through the neutral band (the producer's
            #   weights already carry its own turnover rule; W2b measured the mixed pipeline loses).
            _nb = {"applied": False, "skipped": "external_book", "n_in": len(target),
                   "n_held": 0, "n_traded": len(target), "n_exempt": 0}
            self._last_no_trade_band = _nb
        else:
            # ★ 中性保持型免交易带(PROPOSAL_neutral_band 8e499dac, 用户裁定 2026-08-10)。
            #   必须在 withhold+reshape 之后 —— reshape 的 re-demean 会移动所有名字, 放在其前带就白带了;
            #   场所约束名(reduced/add_blocked/flatten_only)豁免于摊派 —— 对它们加常数会把 clamp
            #   刚刚禁止的方向重新打开。带宽是【权重】口径(no_trade_band_w × gross = 名义), 与
            #   executor 里休眠的 band_bps(bps 口径, 恒 0)是两个机制 —— tests_neutral_band T7 钉死
            #   只有本条活着。缺 key ⇒ 0.0 ⇒ 恒等直通(失败向 = 带关闭 = 部署前行为, 非危险向)。
            _bw = float((_load(os.path.join(_REPO, "config", "book.json"), {}) or {})
                        .get("no_trade_band_w") or 0.0)
            _nb_exempt = (set(_clamp.get("reduced") or ()) | set(_clamp.get("add_blocked") or ())
                          | set(_clamp.get("flatten_only") or ()))
            target, _nb = LG.apply_no_trade_band(
                target, _held_book, band_notional=_bw * float(self.gross or 0.0),
                exempt=_nb_exempt)
            self._last_no_trade_band = _nb
            try:
                _save(os.path.join(os.path.dirname(_hp), "no_trade_band.json"),
                      {"rebalance_id": rid, "written_at": now, "band_w": _bw,
                       "gross": float(self.gross or 0.0), **_nb})
            except Exception as _e:
                # 带是无状态的(不像 EMA 有状态链), 写失败只损失观测 —— 记在返回件上, 不告警刷屏
                self._last_no_trade_band = {**_nb, "state_write_error": type(_e).__name__}

        # anchor capture -> plan -> maker -> (k window handled by caller/cron cadence) -> topup
        anchor_ts, mids = self.executor.capture_anchor(symbols)
        # ★ THE PREFIX IS MINTED BY THE WRITER — never applied to rows afterwards. A list of
        # rehearsal ids kept beside the data drifts away from the data; a prefix cannot
        # (§2.5.9 constraint 3). Still ONE mint site, now at the top of this method (see there for
        # why it moved); the two prefixes therefore still cannot disagree about a batch.
        # ★★★ AND HERE IS WHERE THE EXITS FINALLY GET THEIR LEDGER ROWS. They were SENT back at
        # the universe gate, before `anchor_ts` existed; their execution facts were buffered at
        # that moment and are materialised now, against the real anchor. The submit was NOT
        # delayed for this — an exit is a protective action and must not wait on bookkeeping.
        self.executor.flush_exit_rows(anchor_ts, rid)
        # ★★★ THE CLAMPED NAMES GO OUT AS reduce-only. `reduced` is sized at most to the position
        # and `flatten_only` stops exactly at flat, so both are reductions BY CONSTRUCTION — the
        # tag states to the venue what the clamp already guarantees. `add_blocked` is deliberately
        # absent: its target IS the current position, so its delta is zero and it produces no
        # order at all; tagging it would be a claim about a row that does not exist.
        # ★ E-0909-E: the venue's finite cap, on the final numbers, fail-closed (see clamp_venue_cap).
        _capd = {"capped": [], "n_checked": 0, "margin": VENUE_CAP_MARGIN, "error": None}
        try:
            _capd.update(clamp_venue_cap(target, _held_book,
                                         getattr(self.broker, "symbol_config", None) or {}))
        except Exception as _ce:                                    # noqa: BLE001 — fail closed
            _capd["error"] = f"{type(_ce).__name__}: {str(_ce)[:160]}"
            self.alarm("HIGH", f"场所上限截断失败 ({_capd['error']}) — 目标未改动, 超上限的名将照旧被 -2027 拒。")
        if _capd["capped"]:
            _cn = sum(abs(c["target_before"]) - abs(c["target_after"]) for c in _capd["capped"])
            self.alarm("HIGH" if (len(_capd["capped"]) > 3 or _cn > 0.01 * max(self.gross, 1e-9))
                       else "INFO",
                       f"场所上限截断 {len(_capd['capped'])} 名 (Σ|Δ| {_cn:,.0f}U = gross {_cn / max(self.gross, 1e-9):.2%}): "
                       + ", ".join(f"{c['symbol']} {c['target_before']:+,.0f}→{c['target_after']:+,.0f} (cap {c['cap']:,.0f}, {c['kind']})"
                                   for c in _capd["capped"][:6]) + (" …" if len(_capd["capped"]) > 6 else "")
                       + "; 该名目标超过当前杠杆下 maxNotionalValue×(1−2%), 截到上限而不是被 -2027 拒。")
        if _capd.get("invalid"):
            # ★ Round 4 (review R7): a name whose TARGET or HELD value is not a finite number must
            #   not reach the planner — `tgt - cur` on a None aborts the whole anchor, a NaN walks
            #   through the arithmetic. Fail closed on THAT name only: target := held (delta 0 ⇒ a
            #   `skip` plan row, nothing sent) when the held value is finite; popped when it is not.
            #   An unparsable CAP beside a finite target stays unclamped (the venue's -2027 is the
            #   backstop) and is paged, as in round 3.
            _inv_disp = {}
            for _iv in _capd["invalid"]:
                _s = _iv.get("symbol")
                if _iv.get("field") not in ("target", "held") or _s not in target:
                    continue
                try:
                    _hv = float((_held_book or {}).get(_s, 0.0) or 0.0)
                except (TypeError, ValueError):
                    _hv = float("nan")
                _held_ok = (_hv == _hv and _hv not in (float("inf"), float("-inf"))
                            and not any(_j.get("symbol") == _s and _j.get("field") == "held" for _j in _capd["invalid"]))
                if _iv.get("field") == "target" and _held_ok:
                    target[_s] = _hv; _inv_disp[_s] = "held, no trade this anchor"
                else:
                    target.pop(_s, None); _inv_disp[_s] = "popped (held value unreadable)"
            _capd["invalid_disposition"] = _inv_disp
            self.alarm("HIGH", f"场所上限截断: {len(_capd['invalid'])} 名的 cap/target/held 非有限值 "
                               f"{_capd['invalid'][:4]}; target/held 非有限的名本锚不交易: "
                               f"{_inv_disp or '(仅 cap 非有限: 未截断, 其余照常)'}")
        # ── M3-BEGIN  the venue cap applies to the COMBINED BTC target; a truncated hedge is paged and recorded
        if self._m3.get("record") is not None:
            for _m3sev, _m3msg in BO.after_cap(self._m3["record"], target, _capd, self._m3.get("betas")):
                self.alarm(_m3sev, _m3msg)
            if self._m3["record"].get("mode") in ("on", "config_invalid"):
                # R10-A02: the chase basis subtracts the overlay the FINAL target carries (after the budget and the cap)
                self.executor._m3_overlay_net_usdt = self._m3["record"].get("overlay_net_usdt")
        # ── M3-END
        plans = self.executor.plan(target, state.get("positions", {}), mids,
                                   reduce_only_syms=set(_clamp["reduced"])
                                   | set(_clamp["flatten_only"])
                                   | set(_capd.get("reduce_only_syms") or []),
                                   # E-0912-A (b): full exits are sized as the venue's position (contracts)
                                   held_qty=getattr(self, "_held_qty", None))
        self.executor._last_plans = plans          # phase B (complete_anchor) reads these back
        # ── M3-BEGIN  plan-level delivery of the hedge (lot rounding / min-notional), record only
        if self._m3.get("record") is not None:
            _m3f = (getattr(getattr(self.executor, "filters", None), "f", None) or {}).get(BO.BTC) or {}
            BO.after_plan(self._m3["record"], plans, lot_step=_m3f.get("step"), min_notional=_m3f.get("min_notional"))
        # ── M3-END
        # ★★ SWEEP BEFORE PLACING, NOT AFTER. An order left by an earlier anchor and a new order
        #    in the same name coexist as DOUBLE exposure — which is the very thing the k-cancel
        #    exists to prevent within a rebalance, and which nothing prevented BETWEEN rebalances.
        #    Twice now (07-29 trip, 07-30 -1003 ban) a cancel failed to land and the survivor
        #    filled hours later with no ledger row. Sweeping after would leave the same window.
        _sweep = self.executor.sweep_stale_orders(rid)
        if _sweep.get("cancelled") or _sweep.get("failed") or _sweep["state"].startswith("UNKNOWN"):
            self.alarm("HIGH",
                       f"开场扫单: {len(_sweep.get('cancelled') or [])} 张上锚遗留单已撤, "
                       f"{len(_sweep.get('failed') or [])} 张撤不掉 — {_sweep['state'][:200]}。"
                       f"遗留单会在我们背后成交, 而那是一次没有账本行的仓位变化。")
        live = submit_with_cleanup(self.executor, plans, anchor_ts, rid, self.alarm)
        # ★ RATE-LIMIT SKIPS MUST TRIGGER SOMETHING. A throttled rejection is written as
        # `skipped_rate_limit`, which no stop-loss reads: §4-5c counts `venue_reject`, and the
        # only guard that would notice the resulting drift is M5, which has no producer yet.
        # ⇒ without this the book sits short of target while all seven stop-losses stay silent.
        # It is deliberately at the ANCHOR level (share of this rebalance), not a daily average:
        # one badly throttled anchor is already a book that did not reach its target.
        _rows = [r for r in self.executor.rows_orders if r["rebalance_id"] == rid]
        _rl = [r for r in _rows if r["terminal_reason"] == "skipped_rate_limit"]
        if _rows and len(_rl) / len(_rows) > RATE_LIMIT_SKIP_FRAC:
            self.alarm("HIGH",
                       f"限流跳过 {len(_rl)}/{len(_rows)} 单 (>{RATE_LIMIT_SKIP_FRAC:.0%}) — "
                       f"本锚点的书未达目标, 而没有任何止损会因此触发。"
                       f"检查权重预算与下单节流。")
        # ★★★ THE SAME REASONING, FOR VENUE REFUSALS — AND IT WAS MISSING (2026-08-02 04:00Z).
        # 17 of 109 makers (15.6%) were refused at that anchor and NOTHING SAID SO. The first
        # signal anyone got was §4-5e flattening 83 positions eighteen minutes later, over a hole
        # those refusals were 93% of. The rate-limit alarm above exists because "the book sits
        # short of target while every stop-loss stays silent"; a refusal cluster is that same
        # sentence with a different cause, and the alarm simply did not exist for it.
        # ★ IT STILL MATTERS AFTER THE -5022 FIX, which is the point. -5022 is now topped up, but
        # -1111 / -4164 / -1102 are OUR malformed orders and must NOT be auto-retried — for those
        # the correct response is a human fixing the order, and the only thing standing between
        # that cluster and another §4-5e flatten is this line. The reject that CAN be recovered is
        # now recovered; this covers the ones that cannot.
        # ★★ E-0909-D: a venue that did not ANSWER is a third way for the book to sit short of
        #    target with every stop-loss silent — same shape as the two alarms around it.
        _te = [r for r in _rows if r["terminal_reason"] in ("transport_error",
                                                           "skipped_transport_outage")]
        _vl = getattr(self.executor, "venue_lock_report", None) or {}
        if _vl.get("first_refused"):
            _st = self.broker.api_trading_status() if hasattr(self.broker, "api_trading_status") else {}
            self.alarm("HIGH", f"场所账户级锁 [-4400](E-0910-A, {_vl.get('phase')} 相): 首拒 {_vl['first_refused']}, "
                               f"其后 {_vl.get('n_skipped', 0)} 张开仓单未发(skipped_venue_lock); 场所 apiTradingStatus: "
                               f"locked={_st.get('locked')} 指标={_st.get('indicators')} 预计解锁 {_st.get('planned_recover_utc')}"
                               f"{' (读取失败: ' + str(_st.get('error')) + ')' if _st.get('error') else ''}. "
                               f"减仓单不受影响; 下锚在解锁后照常。")
        _tr = getattr(self.executor, "transport_report", None) or {}
        if _te or _tr.get("n_ambiguous"):
            _sev = ("CRITICAL" if (_tr.get("aborted")
                                   or (_rows and len(_te) / len(_rows) > RATE_LIMIT_SKIP_FRAC))
                    else "HIGH")
            self.alarm(_sev,
                       f"场所无应答: {len(_te)} 单未送达 (transport_error "
                       f"{_tr.get('n_transport_error', 0)}, 熔断跳过 "
                       f"{_tr.get('n_skipped_outage', 0)}); {_tr.get('n_ambiguous', 0)} 单应答"
                       f"丢失, 按「可能在挂」处理(阶段 B 撤单+读成交)。"
                       f"{'熔断: 连续失败后本锚剩余订单未发。' if _tr.get('aborted') else ''}"
                       f"书未达目标, 无止损会因此触发; 下一锚重新对标。")
        # ★★ E-0909-E: a -2027 maker is a gap the VENUE sizes (its bracket cap at our leverage);
        #    the planner clamps only maxNotionalValue == 0, so the same name is refused every
        #    anchor and nothing said so for six anchors (PIEVERSEUSDT 09-08 12Z → 09-09 08Z,
        #    707→423 USDT). Paged here so it has an owner. The fix candidate — clamp the target to
        #    the finite cap from symbolConfig at planning time — changes what is sent and waits
        #    for the user's word; this line changes nothing but who knows.
        _cap = [r for r in _rows if r["terminal_reason"] == "venue_reject"
                and "-2027" in str(r.get("note") or "")]
        if _cap:
            self.alarm("HIGH",
                       "场所仓位上限拒单 (-2027 venue_position_limit): "
                       + ", ".join(f"{r['symbol']} {float(r.get('intended_notional') or 0):+.0f}U"
                                   for r in _cap[:6]) + (" …" if len(_cap) > 6 else "")
                       + "; 目标超过当前杠杆下场所 maxNotionalValue, 规划器只截断 cap=0 的名, "
                         "该缺口每锚重现直到目标回落。候选修复=规划期按 symbolConfig 有限上限截断"
                         "(需用户字)。")
        _vr = [r for r in _rows if r["terminal_reason"] == "venue_reject"]
        # ★★★ THE DENOMINATOR (2026-09-05, E-0905-H). This used to divide the refusal rows by the
        # rows written so far. At this line those rows are the SKIPPED plans and the REFUSED makers — a maker
        # that rested has no row until it turns terminal — so the printed "reject rate" excluded
        # every successful order and double-counted a name refused at attempt 1 and at its requote.
        # 09-05 08Z printed 46.5% (87/187) while the venue had answered 158 first-attempt makers and
        # refused 67 (42.4%); over 85 anchors the printed ratio tracked the min-notional skip count
        # (rank-corr -0.96), which the 09-03 deposit halved, so it "rose" while the true rate was
        # flat. The rate is now computed in `reject_rate.summarise` from the refusal rows and `live`
        # (rested plans, attempt_idx 2 = a requote that rested) and split by MECHANISM: -5022 is
        # recovered (requote, then taker top-up) and is a cost meter; the other codes are our own
        # malformed orders with no recovery path — the thing this alarm was written for.
        # ★ NAME COLLISION REPAIRED 2026-09-08: this used to bind to `_rs`, the SAME local the
        #   withhold/reshape report was bound to at the top of run_anchor. The rebind happened
        #   after the reshape alarms had already fired (so the pages stayed correct) but BEFORE
        #   `row["reshape"] = _rs` below — so from the anchor that first ran this summariser
        #   (2026-09-05 12:00Z, the E-0905 reject-rate denominator fix) the ledger's `reshape`
        #   field silently carried the REJECT-RATE report instead of net_before / net_after /
        #   n_popped / popped_names / names_crossed_floor / clamped_after_reshape. The comment
        #   beside that write says a silent correction and a correction that never ran produce
        #   the identical book — which is exactly the property the collision destroyed. Ledger
        #   evidence: every anchor 08-01→09-05 08Z carries net_before; 09-05 12Z onward, none.
        #   Zero book impact (no trading decision reads either report); the loss was the record.
        _rr = RR.summarise(_rows, live, getattr(self.executor, "requote_report", None))
        if _rr["n_reached"] and _rr["rate_bad"] is not None and _rr["rate_bad"] > VENUE_REJECT_FRAC:
            self.alarm("HIGH", RR.render_bad(_rr, VENUE_REJECT_FRAC))
        if _rr["n_reached"] and _rr["rate_5022"] is not None:
            _po_txt = RR.render_post_only(_rr, POST_ONLY_REFUSAL_ESCALATE)
            if _rr["rate_5022"] > POST_ONLY_REFUSAL_ESCALATE:
                self.alarm("HIGH", "★ post-only 拒单率超升级线 — " + _po_txt)
            else:
                # routine reading: into the anchor record (below) and the run log, not a page
                print(f"[{rid}] {_po_txt}", flush=True)
        # ★ everything the anchors row needs, captured HERE because this is the only place it all
        # exists at once. `finalize_anchor` runs after phase B, by which time `plans`, `mids` and
        # the preds payload are otherwise out of scope. The regime label is taken from the preds
        # file — it is stamped by the producer at signal time, i.e. BEFORE any markout is
        # knowable, which is the property that makes "classified before the outcome" auditable
        # from the log instead of from a file's mtime.
        _reg = (preds.get("regime") or {}) if isinstance(preds.get("regime"), dict) else {}
        self._anchor_ctx = {
            "anchor_ts": anchor_ts, "mids": mids, "target": target,
            "rebalance_id": rid,
            "n_skipped": len(getattr(self, "_untradable", ())) + sum(
                1 for r in _rows if str(r["terminal_reason"]).startswith("skipped_")),
            "regime": _reg.get("label", "unknown"),
            "regime_source": _reg.get("source", "absent from preds — recorded as unknown rather "
                                                "than guessed"),
            # ★ an EXPLICIT sentinel, matching `panel_hash` on the next line. `json.dumps(None)`
            # is the four-character string "null", which satisfies not_null while telling the
            # reader nothing — and reads, in a JSONL file, exactly like a JSON null that was meant.
            "factor_version": (EXT.factor_version_stamp(external) if _is_ext else
                               json.dumps(preds["factor_versions"], sort_keys=True)
                               if preds.get("factor_versions") is not None else
                               "UNKNOWN — the preds file carried no factor_versions"),
            "panel_hash": (external["universe_sha"] if _is_ext else
                           (preds.get("panel") or {}).get("columns_sha256", "UNKNOWN")),
            # ★ WHICH BOOK: 'internal' is today's composer; 'external' names the producer's file
            #   (booster/weights/universe shas travel in factor_version + panel_hash above) and
            #   the two KEPT per-name filters' verdicts — the ledger can then explain every name
            #   the wide book asked for that was not sent.
            "book_source": "external" if _is_ext else "internal",
            "external_book": (EXT.record(external, {
                "held_exit": list(getattr(self, "_ext_held_exit", None) or [])[:40],
                "n_held_exit": len(getattr(self, "_ext_held_exit", None) or []),
                "meta_excluded": (dict(sorted((getattr(self, "_ext_meta", None) or {}).items())[:40])
                                  if getattr(self, "_ext_meta", None) is not None else "NOT CHECKED (DRY_RUN or fetch failed)"),
                "n_meta_excluded": (len(getattr(self, "_ext_meta", None) or {})
                                    if getattr(self, "_ext_meta", None) is not None else None),
                "below_min_notional": ({k: (sorted(v)[:40] if isinstance(v, set) else v)
                                        for k, v in (getattr(self, "_ext_dust", None) or {}).items()}
                                       if getattr(self, "_ext_dust", None) else None)})
                              if _is_ext else None),
            # ★★★ WHICH BOOK THIS ANCHOR TRADED, IN THE LEDGER (2026-08-01). The shadow products
            # got a weights stamp when the mixture moved to challenger; the pilot's OWN ledger did
            # not, so "which weights produced this anchor?" was answerable only from the run log's
            # `deployed_w=` line — and a log is not a ledger. `factor_version` and `panel_hash`
            # beside it already record WHICH SIGNALS; the mixture is the third leg of the same
            # question and was the one missing.
            "weights": _bw,
            # ★ WHAT THE RESHAPE CORRECTED, IN THE LEDGER. `net_before` is THE DEFECT'S SIZE, so
            # the row answers "how much was wrong" and not only "it is neutral now" — a silent
            # correction and a correction that never ran produce the identical book.
            "reshape": _rs,
        }
        # ── M3-BEGIN  the overlay's record travels with the anchor (anchors row `m3_beta_overlay`)
        if self._m3.get("record") is not None:
            self._anchor_ctx["m3_beta_overlay"] = self._m3["record"]
        # ── M3-END
        return {"columns_verified": (want or {}).get("columns_sha256", "SKIPPED")[:12],
                "transport": getattr(self.executor, "transport_report", None),
                "venue_cap_clamp": _capd,
                "frozen_input_census": out_census,
                # ★ the sweep's verdict travels in the anchor record. Its most important reading
                #   is not "we cancelled N" but UNKNOWN — an anchor that could not see the venue's
                #   resting orders has no basis for believing nothing was left behind, and that
                #   has to be legible afterwards rather than inferred from a missing key.
                "stale_order_sweep": _sweep,
                "universe_ood": _ood_report,
                "n_rate_limited": len(_rl),
                # ★ the post-only refusal meter on the answered-makers denominator (E-0905-H);
                #   `legacy_ratio` inside it is the number the alarm printed before 2026-09-05.
                "post_only_refusals": _rr,
                "n_targets": len(target), "n_planned": len(plans), "n_live": len(live),
                # ★ off-schedule 守门的精确对象是【开仓】单: reduce-only(含 per_name_stop 的 flatten_only)
                #   路径按设计在停机时仍放行(见 off_schedule_halt.note)。把两类分开记账, 否则第一次
                #   止损触发就会让"off-schedule ⇒ 零开仓"的断言因 flatten 单而假红(2026-08-21 电池实例)。
                "n_live_opening": sum(1 for _p in live if not (_p or {}).get("reduce_only")),
                "live_reduce_only_syms": sorted(str((_p or {}).get("symbol")) for _p in live if (_p or {}).get("reduce_only"))[:20],
                "sizing": out_sizing,
                "universe": gate, "n_untradable_withheld": len(getattr(self, "_untradable", ())),
                # ★ the disposition travels in the anchor record: "withheld" is now three
                # different outcomes and they must not print as one number.
                # ★★ NAMES, NOT ONLY COUNTS (2026-08-01). `popped: 1` said a member had been
                # withheld and nothing said WHICH — so the +75.37 USDT of intent net it left
                # behind could not be attributed without re-deriving the whole book. A count is
                # enough to notice, never enough to explain, and this one is the sole cause of a
                # directional tilt nothing else measures.
                "untradable_disposition": {k: len(v) for k, v in out_clamp.items()},
                "untradable_names": {k: sorted(v)[:12] for k, v in out_clamp.items() if v},
                "untradable_reason": ("withheld by the universe gate — typically "
                                      "maxNotionalValue=0 on this account (see arm's "
                                      "zero_max_notional / n_zero_cap_withheld)"),
                "untradable_held": {k: v[:6] for k, v in out_clamp.items() if k != "popped"},
                "rebalance_id": rid, "anchor_ts": anchor_ts,
                "book_source": "external" if _is_ext else "internal",
                **({"external_filters": (self._anchor_ctx.get("external_book") or {})} if _is_ext else {}),
                # ★ `live` and `benign_rejected` are handed over SEPARATELY on purpose. `live`
                # means "may be resting" and drives the k-cancel and the venue fills query;
                # `benign_rejected` has nothing resting and no fills, and joins only the TOP-UP.
                # Merging them would make us cancel orders that never existed. (2026-08-02)
                "_pending": {"live": [p["symbol"] for p in live], "target": target,
                             "benign_rejected": [p["symbol"] for p in
                                                 getattr(self.executor, "benign_rejected", [])]}}

    # ── phase B: after the k-window — cancel, top up, emit rows ─────────────────────────────
    def complete_anchor(self, pending: Dict[str, Any], anchor_ts: float,
                        rebalance_id: str) -> Dict[str, Any]:
        """Runs k seconds after run_anchor. The top-up is MANDATORY (~+27pp/yr); the gap left by
        anything unfillable is measured via terminal_reason, never hidden. Also updates the
        cached book with what actually traded — the executor's rows are the source of truth."""
        live_syms = pending.get("live", [])
        target = pending.get("target", {})
        # ★ CANCEL FIRST, THEN READ FILLS. Reading first and cancelling after loses any fill that
        # lands in between; and leaving the maker resting while the IOC top-up fires can double
        # the position. Both orderings look identical in DRY_RUN, where no order is real.
        live_plans_all = [p_ for p_ in getattr(self.executor, "_last_plans", [])
                          if p_["symbol"] in live_syms]
        cancels = self.executor.cancel_resting(live_plans_all, rebalance_id)
        if cancels.get("errors"):
            self.alarm("HIGH", f"k-cancel failed for {len(cancels['errors'])} name(s): "
                               f"{cancels['errors'][:3]} — those orders may still fill on top of "
                               f"the top-up")
        # ★★★ AN ORDER LEFT RESTING GETS ITS OWN PAGE, AT ITS OWN SEVERITY (2026-08-01, second
        #     occurrence: 07-31 16:20Z ['LISTAUSDT','ONEUSDT'], 08-01 08:19Z ['DOGEUSDT','TIAUSDT']).
        #     `errors` and `unresolved` are DIFFERENT FACTS and the old code only had the first:
        #     under a -1003 ban the refusals are rate-limit refusals, so the operator saw "k-cancel
        #     failed" — a sentence about our request — and not "two maker orders are still on the
        #     live book", which is the one about our money. Every factual clause below is carried
        #     from the cancel report; none of it is spelled into the wording.
        if cancels.get("unresolved"):
            _b = cancels.get("ban") or {}
            _pin = cancels.get("pinned") or {}
            self.alarm("CRITICAL",
                       f"★ {len(cancels['unresolved'])} maker order(s) LEFT RESTING on the venue: "
                       f"{cancels['unresolved'][:6]} — a resting order can still fill, hours from "
                       f"now, at a price chosen for a book we no longer hold. "
                       f"why: {cancels.get('stopped_because') or 'cancel failed'}. "
                       f"ban_until={_b.get('until_utc')} remaining_s={_b.get('seconds_remaining')} "
                       f"waits={cancels.get('ban_waits')} retried={cancels.get('retried')}. "
                       f"pinned={_pin.get('added')} new / {_pin.get('total')} standing"
                       f"{' — ★ PIN WRITE FAILED, see errors' if _pin == {} else ''}")
        # ★★ THE TOP-UP MUST KNOW WHAT THE MAKER ALREADY FILLED. This line used to be
        #     filled = self.fills(rebalance_id, live_syms)
        # and `self.fills` defaults to `lambda rid, syms: {}` — a default chosen deliberately for
        # DRY_RUN (where it exercises the full top-up path) and never overridden for a mode with
        # real fills. run_anchor.py constructed AnchorLoop without a provider, so on the FIRST
        # real anchor every maker-filled name was bought again in full: 47 of 47 held names came
        # back at exactly 2.00x intended (ratio median 1.997), §4-5b tripped, and the book was
        # flattened. `venue_fills.fills_for()` existed for precisely this and had ZERO callers.
        # ⇒ The fills now come from the SAME allOrders call that already fetched the execution
        # facts three lines below — the data was in scope the whole time, read by one consumer
        # and not the other. An injected provider still wins if one is supplied (tests).
        filled, unknown = {}, set()
        try:
            import venue_fills as _VF
            _details = _VF.fill_details_for(self.broker, rebalance_id, live_syms)
            _reached = _VF.last_coverage()
            # ★ Round 4 (review E1): an ambiguous maker not seen in allOrders is settled by ITS OWN
            #   id — or stays UNKNOWN. A full page never proves absence.
            try:
                _settle = _VF.settle_ambiguous_legs(self.broker, rebalance_id, live_plans_all, _details,
                                                    _VF.last_matched_cids(), _VF.last_full_pages(),
                                                    reached=_reached, non_terminal=_VF.last_non_terminal(),
                                                    matched_rows=_VF.last_matched_rows())
            except Exception as _se:                                    # noqa: BLE001 — fail closed per name
                _settle = {"unknown": {p_["symbol"] for p_ in live_plans_all if p_.get("submit_ambiguous")},
                           "report": [{"verdict": "UNKNOWN", "why": f"settlement raised {type(_se).__name__}: {str(_se)[:80]}"}]}
            _details = dict(_details or {}); _details.update(_settle.get("updates") or {})
            _settled_unknown = set(_settle.get("unknown") or ())
            # ★ Round 5 (review E4-P1): an order the venue still shows OPEN, and a cancel that did
            #   not resolve, keep their symbol UNKNOWN — a top-up on top of a live order is the
            #   double the k-cancel exists to prevent. Only a settlement that saw the order
            #   terminal after cancel+re-query ("found") lifts it.
            _found = set(_settle.get("found") or [])
            # round 7 (review R6-P2): a request allOrders itself shows terminal is resolved like a
            # settled one — for the k-cancel's unresolved set and its pin
            _found_all = _found | set(_settle.get("terminal_matched") or [])
            _still_open = set(_VF.last_non_terminal()) - _found
            # ★ Round 6 (review R5-E1): a cancel that failed at k-cancel is SUPERSEDED by a later
            #   reliable terminal fact for the same request (cancel + re-query in settlement). The
            #   unresolved set is reconciled by request, and the pin is cleared with the evidence —
            #   an old "unresolved" must never re-create a Q − C authorisation on a finished order.
            _unres0 = set(cancels.get("unresolved") or [])
            _settled_unknown |= _still_open | (_unres0 - _found_all)
            for s_, d_ in (_settle.get("partial") or {}).items():
                if s_ not in (_settle.get("updates") or {}):
                    _details[s_] = dict(_details.get(s_) or {}, **d_)   # facts read, not a settlement (R5-E2)
            _resolved_pins = sorted(_found_all & _unres0)
            if _resolved_pins:
                try:
                    import stuck_orders as _SO
                    _keys = [(p_["symbol"], f"{rebalance_id}-{p_['symbol']}-{int(p_.get('attempt_idx') or 1)}"[:36])
                             for p_ in live_plans_all if p_["symbol"] in _resolved_pins]
                    _cl = _SO.clear(self.broker.mode, _keys,
                                    reason=f"phase B settled terminal by cancel+re-query (rid {rebalance_id})")
                    self.alarm("INFO", f"阶段 B 结算清除 {len(_keys)} 条撤单 pin(查单已确认终态): {_cl}")
                except Exception as _pe:                                    # noqa: BLE001
                    self.alarm("HIGH", f"阶段 B 结算后清 pin 失败: {type(_pe).__name__}: {str(_pe)[:80]}")
            if _settle.get("report"):
                # ★ E-0912-A (3) — 告警文案≠来源 family: this line said "满页或查询失败" for every UNKNOWN name, while the
                #   12Z rows' `inconsistent` was an identity/origQty mismatch. The text now carries EACH name's actual
                #   reason (the settlement report's `why`, else the fold's `inconsistent`, first 120 chars); a name with
                #   neither is labelled as such rather than given a guessed cause.
                _why_by = {}
                for _r_ in (_settle.get("report") or []):
                    if _r_.get("verdict") == "UNKNOWN" and _r_.get("symbol") in _settled_unknown and _r_.get("why"):
                        _why_by.setdefault(_r_["symbol"], str(_r_["why"])[:120])
                for _s_ in sorted(_settled_unknown):
                    _inc_ = (_details.get(_s_) or {}).get("inconsistent")
                    if _s_ not in _why_by and _inc_:
                        _why_by[_s_] = str(_inc_[0] if isinstance(_inc_, list) and _inc_ else _inc_)[:120]
                    _why_by.setdefault(_s_, "no reason recorded by the settlement (unreached / full page / query failed)")
                self.alarm("HIGH" if _settled_unknown else "INFO",
                           f"阶段 B 歧义 maker 结算: 查到 {len(_settle.get('found') or [])} / 确认未下达 "
                           f"{len(_settle.get('absent') or [])} / 仍 UNKNOWN {len(_settled_unknown)}"
                           f"{(' — 逐名原因: ' + '; '.join(f'{s_}: {w_}' for s_, w_ in sorted(_why_by.items())[:6])) if _settled_unknown else ''}; "
                           f"UNKNOWN 名不补单, 其 maker 行带请求量作授权带")
            if _details:
                self.executor.apply_fill_details(live_plans_all, _details)
            # ★★ [F5] `or 0.0` HERE WAS THE CONSUMER HALF OF THE SAME FOLD. `fill_details_for`
            # can now answer "it filled, and the venue gave no amount" (filled_notional None),
            # and this expression turned that third state into "it filled nothing" — the reading
            # that sizes a full top-up on top of a position we may already hold. A symbol whose
            # AMOUNT is unreadable is UNKNOWN for exactly the same reason as one we could not
            # reach: both are "we cannot state what the maker did", and only the cause differs.
            filled, _amount_unreadable = {}, set()
            for s_, d in _details.items():
                _fn = d.get("filled_notional")
                if d.get("inconsistent"):
                    # ★ round 8 (review R7-C): a contradiction in the fold is not a number to top up
                    #   from — the name is UNKNOWN, its maker row carries the contradiction, the
                    #   reader refuses to quantify it
                    _amount_unreadable.add(s_)
                    continue
                if _fn is None:
                    _amount_unreadable.add(s_)
                else:
                    filled[s_] = float(_fn)
            # a symbol we could not query is UNKNOWN, never "did not fill" — see topup()
            if self.broker.mode != "DRY_RUN":
                unknown = {s_ for s_ in live_syms if s_ not in _reached} | _amount_unreadable | _settled_unknown
                if _amount_unreadable:
                    self.alarm("HIGH",
                               f"{len(_amount_unreadable)} symbol(s) reported a filled QUANTITY "
                               f"with no readable amount ({sorted(_amount_unreadable)[:4]}); they "
                               f"are treated as UNKNOWN and not topped up. Reading them as 0.0 is "
                               f"the input that produced the 2.00x doubling.")
        except Exception as e:
            # ★ FAIL-CLOSED ON THE WHOLE CALL: if we cannot establish ANY fills, every live name
            # is unknown. Topping up from an empty dict here is exactly the defect above.
            unknown = set(live_syms) if self.broker.mode != "DRY_RUN" else set()
            self.alarm("CRITICAL", f"could not read fills ({e}); {len(unknown)} name(s) will NOT "
                                   f"be topped up — sizing a top-up from an assumed zero would "
                                   f"double any position the maker already filled")
        _injected = self.fills(rebalance_id, live_syms)
        if _injected:
            filled = _injected                 # explicit provider wins (tests, future sources)
        if unknown:
            # ★ [①] AND SAY WHAT FAILED THEM. This alarm used to report only the COUNT, so on
            # 2026-07-27 00:00Z "101 name(s) had unreadable fills" was the whole record and the
            # investigation could not tell 502 from timeout from empty. The reader now classifies
            # each failure; a count plus a class histogram is the difference between "reads
            # failed" and "this endpoint is returning 502".
            try:
                import collections as _c
                _f = _VF.last_read_failures()
                _hist = dict(_c.Counter(v.get("error_class") for v in _f.values()))
                _eps = sorted({v.get("endpoint") for v in _f.values()})
            except Exception:
                _hist, _eps = {}, []
            self.alarm("HIGH", f"{len(unknown)} name(s) had unreadable fills; their top-up is "
                               f"skipped and recorded as skipped_unknown_fill. "
                               f"failure classes={_hist or 'UNRECORDED'} endpoints={_eps}")
        spreads = {}
        if self.broker.mode != "DRY_RUN":
            try:
                spreads = {s_: v["spread_bps"] for s_, v in self.src.book_mids().items()}
            except Exception as e:
                self.alarm("HIGH", f"spread fetch failed at topup ({e}); "
                                   f"proceeding without spread guard")
        # ★★★ THE TOP-UP POPULATION IS `live` PLUS THE BENIGNLY-REFUSED (2026-08-02 04:18Z).
        # A -5022 maker never entered `live`, so its name left the anchor entirely: no fill, no
        # top-up, no further mention. 17 such names at 04:00Z were 1050.10 USDT — 93% of the 1131
        # break §4-5e then flattened the whole book over. Their residual is the FULL delta (they
        # filled nothing), which `topup` computes for free: `filled` has no entry for them, so
        # `residual = delta - 0`.
        # ★ ONLY here. `cancel_resting` and `fill_details_for` above still see `live` alone —
        # there is nothing resting to cancel and no fill to fetch for an order the venue refused.
        _rejected_syms = set(pending.get("benign_rejected") or [])
        _topup_plans = live_plans_all + [p_ for p_ in getattr(self.executor, "_last_plans", [])
                                         if p_["symbol"] in _rejected_syms]
        if _rejected_syms:
            self.alarm("HIGH",
                       f"{len(_rejected_syms)} 个 maker 被 -5022 拒(post-only 会立刻成交), "
                       f"其残差按全额进入 taker 补单: {sorted(_rejected_syms)[:8]}。"
                       f"这些名字此前会整个从本锚消失 —— 04:00Z 那次占了 §4-5e 缺口的 93%。")
        # ★ E4 (ruling R2′): the stop set the PLAN used — a stopped name's from_partial residual is never chased
        _stop_now = set((getattr(self, "_pns_sets", None) or {}).get("stop") or ())
        self.executor.topup(_topup_plans, filled, anchor_ts, rebalance_id,
                            spreads_bps=spreads, unknown_fills=unknown, stop_names=_stop_now)
        _sx = getattr(self.executor, "stop_exit_report", None) or {}
        if _sx.get("carried"):
            # ★ E4: a stop exit that did not close this anchor is paged EVERY anchor it lasts — the trigger page fires once;
            #   a maker exit that keeps not filling would otherwise be as silent as the pinned longs W9 found
            import binance_executor as _BEXs          # the spread gate the conversion is subject to — its own constant, not a copy
            self.alarm("HIGH",
                       f"逐名止损出场未完成 {len(_sx['carried'])} 名: 部分成交残差不追, 留待下一锚重新挂 maker(reduce-only; 这部分残差"
                       f"是 maker-only 的); 被场所拒绝的 maker 当锚已在补单环节转市价 reduce-only, 受 {_BEXs.MAX_CROSS_BPS:g} bps 点差门与最小名义额约束"
                       f"(条款 cf40ea21, 裁定 R2′): " + ", ".join(f"{c['symbol']} {c['terminal_reason']} "
                                              f"{float(c['residual_usdt']):+.2f}U" if c.get("residual_usdt") is not None
                                              else f"{c['symbol']} {c['terminal_reason']} residual=UNKNOWN"
                                              for c in _sx["carried"][:8]))

        # ── COMMISSION AND THE CHILD FILLS — one query, AFTER both legs have executed ────────
        # ★ WHY AFTER, AND WHY IT USED TO BE BEFORE. `userTrades` is the only endpoint carrying
        # commission, and the first wiring called it between the cancel and the top-up — i.e.
        # before the taker order existed. It therefore returned the maker leg only, and the
        # per-symbol total it produced was stamped on the shared plan dict, so BOTH rows got the
        # maker's fee: counted twice, taker's never. Moving the single call to here fixes both
        # halves at once and costs no extra request.
        # ★ AND IT IS THE ONLY INPUT THE `fills` TABLE CAN HAVE. M2 is a per-CHILD-FILL markout;
        # the aggregate cannot produce it. `pilot_log.fill()` had zero callers until this line —
        # found by ops/scan_probe_only_callers.py, not by a failing test, because a table nobody
        # writes has nothing to fail.
        fill_rows: List[Dict[str, Any]] = []
        n_unattributed = None
        try:
            # ★★★ THE COMMISSION QUERY NEEDS THE REFUSED NAMES TOO — AND `live_syms` EXCLUDES
            # THEM BY DESIGN. `live` means "may be resting", which is the right population for
            # the k-cancel and the maker fills query; a -5022 name has nothing resting and no
            # maker fill. But its TOP-UP executed, so it has userTrades and therefore a fee.
            # ⇒ Measured on the 08:00Z anchor: all 22 `from_reject` top-ups filled and EVERY ONE
            #   had an unknown fee, so the cost table read `from_reject 0.00bps` against
            #   `from_partial 5.00bps` — **one population priced with fees and the other without,
            #   i.e. exactly the comparison the split exists to make, made incomparable.** A
            #   missing number that looks like a favourable number is the worst kind.
            # ★ The LEGS side needed nothing: `submitted_order_legs` reads the broker's own submit
            #   records for this rebalance, so the refused names' top-ups were always there.
            #   Widening only the query is the whole fix — and widening only the legs would have
            #   fetched nothing while looking correct.
            _fee_syms = sorted(set(live_syms) | set(pending.get("benign_rejected") or []))
            # ★ price_fn 显式穿给【每腿】聚合 (2026-08-05): `user_trades_for` 会用 broker 自默认
            #   price_fn(每符号层的换算一直活着), 但 `attribute_trades` 是纯函数拿不到 broker ——
            #   它的每腿字典因此没有换算字段, stamp 找不到 `commission_usdt_converted` 就回落到
            #   纯 USDT 部分 = 测得的 0.0(16:00Z 实测 100/100)。两级聚合一级修了一级没修。
            _pfn = (lambda a: _VF._asset_usdt_mid(self.broker, a))
            _trades = _VF.user_trades_for(self.broker, _fee_syms,
                                          since_ms=int((anchor_ts - 300) * 1000),
                                          price_fn=_pfn)
            _reached_t = _VF.last_trade_coverage()
            _legs = _VF.submitted_order_legs(self.broker, rebalance_id)
            _sent = {(i["symbol"], i["leg"]) for i in _legs.values()}
            _att = _VF.attribute_trades(_trades, _legs, price_fn=_pfn)
            n_unattributed = _att["n_unattributed"]
            _fee = self.executor.apply_commission_to_rows(rebalance_id, _att["by_symbol"],
                                                          _reached_t, _sent)
            if _fee["unknown"]:
                # ★ THE ONE THAT NEEDS A VOICE. This failure is silent and in the SAFE direction
                # — no wrong fee, just a permanently incomplete M1 — which is exactly why nothing
                # else would ever surface it. Note it is per LEG: a symbol can have a measured
                # top-up fee and an unknown maker fee, and both statements are kept.
                self.alarm("HIGH", f"{_fee['unknown']} order row(s) have an UNKNOWN fee: either "
                                   f"userTrades was unreadable for the symbol, or we hold no "
                                   f"submit response to attribute that leg's fills to. M1 must "
                                   f"report those rows as fee-unmeasured, never as zero-fee.")
            fill_rows = _VF.fill_rows_from_trades(_att["attributed_trades"], anchor_ts,
                                                  rebalance_id)
            # ★ 重分级 (2026-08-06, 用户裁定"按建议来"): 旧版在这里对【每个】含非 USDT 手续费的锚
            #   无条件 HIGH —— 而 BNB 缴费是有意配置(08-05 划转购 BNB 换折扣), 6h 内 6 条同因 HIGH
            #   占掉近半决策面; 且旧文案 "fee_paid is the USDT portion only" 自 c05f1f5(逐腿换算)
            #   起已为假。判定提成 venue_fills.fee_asset_change_verdict(纯函数, 可测) —— 报告【变化】
            #   不报告状态; 换算不完整仍逐锚 HIGH(那是测量洞不是配置)。基线按 mode 根存放。
            import state_root as _SRf
            _mode_f = os.environ.get("LIVE_MODE", "DRY_RUN")
            _fb_path = os.environ.get("LIVE_FEE_BASELINE",
                                      os.path.join(_SRf.paths_for(_mode_f)["root"],
                                                   "fee_asset_baseline.json"))
            _fv = _VF.fee_asset_change_verdict(_trades, _load(_fb_path, None))
            if _fv["page"]:
                self.alarm(_fv["level"], _fv["message"])
            if _fv["baseline_write"]:
                try:
                    _save(_fb_path, _fv["baseline"])
                    _SRf.stamp_mode(_fb_path, _mode_f)
                except Exception as _e:      # noqa: BLE001
                    self.alarm("HIGH", f"fee-asset baseline write failed "
                                       f"({type(_e).__name__}) — next anchor re-pages "
                                       f"first-seen; noisy, not unsafe")
            # ★ Round 3 (review 31fa3e4e P1-3): the count now has a VOICE. A trade we cannot
            #   attribute may legitimately be ours (a flatten from an earlier process leaves no
            #   submit response here) — INFO, recorded. But when a row of THIS rebalance carries
            #   an UNKNOWN request on that symbol, an unattributed trade is exactly the fill that
            #   request may have produced: HIGH, named, and never folded into "known".
            _vl2 = getattr(self.executor, "venue_lock_report", None) or {}
            if _vl2.get("phase") == "topup" and _vl2.get("first_refused"):
                _st2 = self.broker.api_trading_status() if hasattr(self.broker, "api_trading_status") else {}
                self.alarm("HIGH", f"场所账户级锁 [-4400](E-0910-A, 补单相): 首拒 {_vl2['first_refused']}, 其后 "
                                   f"{_vl2.get('n_skipped', 0)} 张补单未发(skipped_venue_lock); apiTradingStatus: "
                                   f"locked={_st2.get('locked')} 预计解锁 {_st2.get('planned_recover_utc')}. 书将欠建, 下锚补齐。")
            _conf = _VF.last_leg_conflicts()
            if _conf:
                self.alarm("HIGH", f"订单归属冲突: {len(_conf)} 个 venue orderId 被两个不同 client id 的提交记录"
                                   f"声称, 保留首个、拒绝后者(手续费/成交按首个归属): {_conf[:3]}")
            if n_unattributed:
                _unk_syms = sorted({r.get("symbol") for r in self.executor.rows_orders
                                    if r.get("rebalance_id") == rebalance_id
                                    and r.get("filled_unknown_residual") is not None})
                self.alarm("HIGH" if _unk_syms else "INFO",
                           f"{n_unattributed} 笔成交无法归属到本次换仓的任何已知订单"
                           + (f"; 本锚有 UNKNOWN 请求的名: {_unk_syms[:6]} — 这些成交可能就是那些请求的结果, "
                              f"账本保留 UNKNOWN(不写 0 不写 known), 下锚对账按授权带判" if _unk_syms
                              else "(可能是别的进程/手工/平仓的成交; 只记录)"))
        except Exception as e:
            self.alarm("HIGH", f"commission/fills collection failed ({e}); fee_paid stays None, "
                               f"the fills table gets no rows for this anchor, and M1/M2 report "
                               f"those fills as unmeasured (never as zero-fee, never as no-fill)")

        # book update: what we held, plus what actually FILLED, from the emitted rows [B29]
        state = _load(STATE_PATH, {"positions": {}})
        _book = book_after_anchor(state.get("positions", {}), self.executor.rows_orders,
                                  rebalance_id)
        state["positions"] = _book["positions"]
        # ★ NOT an alarm on its own — an unreadable leg is already alarmed above, and the next
        # anchor re-reads the venue regardless. It is RECORDED because the cached book now has a
        # named gap rather than a value nobody can attribute. (Carried to the returned record
        # below rather than written here: `_out_b` does not exist yet at this point.)
        _book_report = {"book_cache_unknown_legs": _book["unknown"]}
        if _book["unknown"]:
            _book_report["book_cache_note"] = (
                f"{len(_book['unknown'])} leg(s) had an unreadable fill; those symbols keep their "
                f"previous cached value rather than being credited 0.0 or the target")
        _save(STATE_PATH, state)

        # ── persist the order rows ───────────────────────────────────────────────────────────
        # ★ THIS CALL WAS BROKEN IN TWO INDEPENDENT WAYS AND NEITHER COULD EVER FIRE:
        #   (1) `self.log` was None in every production construction (nobody passed log=), so the
        #       guard below never opened; and
        #   (2) it called `self.log.write("orders", row)` -- a method `PilotLogger` DOES NOT HAVE
        #       (its API is typed: .order(), .anchor(), ...). Had the guard ever opened, this
        #       would have raised AttributeError.
        # Meanwhile every anchor reported `rows_emitted: 110` and that number was TRUE -- the rows
        # really were built. They just never left memory. An honest number pointing at an artefact
        # that did not exist. Hence `rows_persisted` below: emitted is the numerator, persisted is
        # the denominator nobody printed.
        mine = [r for r in self.executor.rows_orders if r["rebalance_id"] == rebalance_id]
        n_rows, n_persisted, rejects = len(mine), 0, []
        if self.log is not None:
            for row in mine:
                try:
                    self.log.order(**row)
                    n_persisted += 1
                except Exception as e:
                    # a rejected row must not kill the anchor, and must not vanish either
                    rejects.append(f"{row.get('symbol')}/{row.get('order_type')}: "
                                   f"{type(e).__name__}: {str(e)[:120]}")
        if n_persisted != n_rows:
            self.alarm("HIGH", f"order rows: emitted {n_rows}, persisted {n_persisted}"
                               f"{' (no logger attached)' if self.log is None else ''}. "
                               f"{('first rejects: ' + '; '.join(rejects[:3])) if rejects else ''} "
                               f"— the pilot's entire output is reconstructed from these rows.")

        # ── persist the fills rows ───────────────────────────────────────────────────────────
        # Same emitted-vs-persisted discipline as the orders above, for the same reason: the
        # count that matters is the one produced at the FAR end of the path.
        n_fill_rows, n_fill_persisted, fill_rejects = len(fill_rows), 0, []
        # ★★ LED-01 (2026-09-13): the logger REFUSES a row that breaks the fills write contract (a second original
        #    for an existing (symbol, trade_id), a supersede that changes fact columns) — it returns False, writes the
        #    row to <day>/fills_quarantine.jsonl and never raises. Counted apart from rejects, one alarm per anchor.
        _q0 = len(getattr(self.log, "fill_quarantined", None) or [])
        _g0 = len(getattr(self.log, "fill_guard_errors", None) or [])
        n_fill_quarantined = 0
        if self.log is not None:
            for row in fill_rows:
                try:
                    if self.log.fill(**row) is False:
                        n_fill_quarantined += 1
                    else:
                        n_fill_persisted += 1
                except Exception as e:
                    fill_rejects.append(f"{row.get('symbol')}/{row.get('order_type')}: "
                                        f"{type(e).__name__}: {str(e)[:120]}")
        _qnew = (getattr(self.log, "fill_quarantined", None) or [])[_q0:]
        _gnew = (getattr(self.log, "fill_guard_errors", None) or [])[_g0:]
        if n_fill_quarantined or _gnew:
            import collections as _collections
            _kinds = dict(_collections.Counter(q.get("kind") for q in _qnew))
            self.alarm("HIGH", f"fills 写入合同违例: 本锚 {n_fill_quarantined} 行被拒入 fills.jsonl, 已隔离到 "
                               f"<日目录>/fills_quarantine.jsonl (类型 {_kinds}; 首个键 "
                               f"{[q.get('key') for q in _qnew[:3]]})"
                               + (f"; 其中隔离写入失败 {sum(1 for q in _qnew if q.get('quarantine_write_failed'))} 行"
                                  if any(q.get('quarantine_write_failed') for q in _qnew) else "")
                               + (f"; 合同守卫自身出错 {len(_gnew)} 次(这些行已按原行为写入): {_gnew[:2]}" if _gnew else "")
                               + " — 一笔成交一行原件 + 声明的 supersede 行; 锚照常完成, 隔离行待人工核对")
        if n_fill_persisted + n_fill_quarantined != n_fill_rows:
            self.alarm("HIGH", f"fill rows: built {n_fill_rows}, persisted {n_fill_persisted}"
                               f"{' (no logger attached)' if self.log is None else ''}. "
                               f"{('first rejects: ' + '; '.join(fill_rejects[:3])) if fill_rejects else ''} "
                               f"— M2 (markout) has no other input than this table.")
        _out_b = {"rebalance_id": rebalance_id, "k_cancel": cancels, "rows_emitted": n_rows,
                **_book_report,
                "rows_persisted": n_persisted,
                "fill_rows_built": n_fill_rows, "fill_rows_persisted": n_fill_persisted,
                **({"fill_rows_quarantined": n_fill_quarantined} if n_fill_quarantined else {}),
                **({"fill_rows_rejected": fill_rejects[:5]} if fill_rejects else {}),
                **({"n_trades_unattributed": n_unattributed}
                   if n_unattributed is not None else {}),
                # ★ the requote pass reports per anchor or not at all: without this line the
                #   PREREG's 主判 (reject notional share, 20 anchors) has no per-anchor record to
                #   be rebuilt from, and "it ran and did nothing" would look like "it never ran".
                **({"requote": getattr(self.executor, "requote_report", None)}
                   if getattr(self.executor, "requote_report", None) else {}),
                **({"rows_rejected": rejects[:5]} if rejects else {}),
                **({"stop_exit_carried": (getattr(self.executor, "stop_exit_report", None) or {}).get("carried")}
                   if (getattr(self.executor, "stop_exit_report", None) or {}).get("carried") else {}),     # E4
                  "n_topped_up": sum(1 for r in self.executor.rows_orders
                                     if r["rebalance_id"] == rebalance_id
                                     and r["order_type"] == "topup_taker")}
        # ★ [B26a] assert the combination AT THE ANCHOR, not three hours later at §4-5b.
        _gap = fill_collection_gap(_out_b)
        if _gap:
            self.alarm("HIGH", _gap)
            _out_b["fill_collection_gap"] = _gap
        return _out_b

    # ── phase C: the three account-state tables ─────────────────────────────────────────────
    def finalize_anchor(self, outA: Dict[str, Any], outB: Optional[Dict[str, Any]] = None,
                        now: Optional[float] = None) -> Dict[str, Any]:
        """Write the anchors / position_readback / daily_nav rows. ONE call site, at the end.

        ★ WHY ALL THREE HERE, AND WHY AFTER PHASE B
        They share one input: a single /fapi/v3/account read taken once the anchor's orders are
        done. Splitting them would mean three reads of the same account at three moments, and
        three chances for the three tables to disagree about what the book was.

        ★ WHY THEY ARE SEPARATE TABLES AT ALL (0C's structural finding, schema v2): an ORDER log
        can only reconstruct order-derived quantities. Positions, NAV and funding are account
        state; they flow through a different pipe and need their own stream. `executor.anchor_row`
        has existed since the port with NO CALLER — this is that caller.

        ★ WHAT IT REFUSES TO DO: in DRY_RUN there is no account, so no readback and no NAV row is
        written. Not an empty row, not a zero — nothing. The artefact assertion reports the
        absence as N/A for the mode, which is why the certification window was ruled to run on
        TESTNET rather than DRY_RUN.
        """
        now = now or time.time()
        out: Dict[str, Any] = {"anchors_row": False, "position_readback_rows": 0,
                               "daily_nav_row": False}
        if self.log is None:
            out["note"] = "no logger attached; nothing written"
            # ★ W6C-B13: even this says so in the verdict's vocabulary, so a reader never has to
            #   infer "no rows" from a missing key (see the block comment at `_book_observation`).
            out["book_observation"] = _book_observation("NO_LOGGER", 0, None,
                                                        "no logger attached; nothing written")
            return out
        ctx = getattr(self, "_anchor_ctx", None)

        # ── 1. one account read, used by all three ──────────────────────────────────────────
        snap = None
        _read_error = None
        try:
            snap = self.broker.account_snapshot()
        except Exception as e:
            self.alarm("HIGH", f"end-of-anchor account read failed ({e}) — position_readback and "
                               f"daily_nav have no input this anchor")
            out["account_read_error"] = str(e)[:200]
            _read_error = str(e)[:200]
        # ── 逐名止损条款计数(cf40ea21): 深度=unrealized/|notional| 于终锚读回, 连续 2 锚触发。
        #    snap=None ⇒ evaluate 恒等; ★ 且写入被正典 mode 判别式看门(环境形, 与 tests_deadman
        #    同源写法) — 电池 fixture 的合成快照(非 None!)曾于 02:23Z 写入 live 状态树, mock 的
        #    broker.mode 属性可伪造, 环境变量不可(review 第二洞, 2026-08-20)。
        if os.environ.get("LIVE_MODE", "DRY_RUN") == "LIVE":
            try:
                _pns = PNS.update_from_snapshot(snap, time.time())
                for _m in _pns["alarms"]:
                    self.alarm("HIGH", _m)
                out["per_name_stop"] = {"stopped": sorted(_pns["state"]["stopped"]),
                                        "counters": _pns["state"]["counters"],
                                        "cooldown_n": len(_pns["state"]["cooldown"])}
            except Exception as _e:
                self.alarm("HIGH", f"per_name_stop 计数更新失败({type(_e).__name__}: {str(_e)[:80]}) — "
                                   f"条款该锚失明(状态文件未动)")
        else:
            out["per_name_stop"] = "SKIPPED_NON_LIVE"

        # ── 2. position_readback: what the VENUE says we hold ───────────────────────────────
        # M5 reconciles our book against the venue, so the row must be the venue's number and must
        # say where it came from. Names we TARGETED but do not hold are written too, at 0.0: a
        # name missing from the venue's list and a name we never targeted are different facts,
        # and only the union distinguishes them.
        _write_truncated = None
        _rb_anchor_ts = None
        if snap is not None:
            venue = snap["positions_notional"]
            targeted = set((ctx or {}).get("target", {}))
            anchor_ts = (ctx or {}).get("anchor_ts") or now
            _rb_anchor_ts = float(anchor_ts)
            # ★★ [i-face2] THE THIRD SOURCE. `venue` holds only NONZERO positions (the venue
            # encodes flat as absence), so a name that leaves the universe AND goes to zero is
            # missing from both sets and drops out of §4-5b's comparison domain entirely — the
            # liquidation case the guard is named for. Carrying "held at the previous readback"
            # gives it an explicit 0.0 row; the carry terminates the next anchor, by construction.
            _prev_nz = prev_nonzero_symbols(os.path.dirname(self.log.dir), float(anchor_ts))
            for sym in sorted(readback_universe(venue, targeted, _prev_nz)):
                try:
                    self.log.position_readback(
                        anchor_ts=anchor_ts, symbol=sym,
                        venue_position_notional=float(venue.get(sym, 0.0)),
                        # ★★ [B30] THE QUANTITY, FROM THE SAME ONE ACCOUNT READ. §4-5b compares
                        # positions, and a position is contracts; the notional is contracts times
                        # a mark that moves between anchors. Without this column the guard had to
                        # compare notionals and was therefore a price-move detector (it flattened
                        # a $24.5k book on 2026-07-27 for a 3% move). Both calibers come out of
                        # `snap`, i.e. ONE /fapi/v3/account call — sourcing them from two calls
                        # would let a fill land in between and make N and Q describe different
                        # books, which is the same defect wearing different clothes.
                        venue_position_qty=float(
                            (snap.get("positions_contracts") or {}).get(sym, 0.0)),
                        source="fapi/v3/account@post_anchor",
                        held=sym in venue, targeted=sym in targeted,
                        read_ts=snap["read_ts"])
                    out["position_readback_rows"] += 1
                except Exception as e:
                    self.alarm("HIGH", f"position_readback row rejected for {sym}: {e}")
                    # ★ W6C-B13: the `break` below leaves every LATER name unwritten, and the short
                    #   readback that results is indistinguishable in the log from a full one. The
                    #   verdict below is where that stops being invisible.
                    _write_truncated = f"{sym}: {type(e).__name__}: {str(e)[:100]}"
                    break

        # ── 2b. W6C-B13: WHY there are or are not readback rows, said once, by the only code
        #        that knows. Four different facts write zero rows and the log shows one observable;
        #        the watchdog reads this instead of guessing (watchdog._book_observability).
        out["book_observation"] = _book_observation(
            ("READ_FAILED" if _read_error is not None else
             "NO_ACCOUNT" if snap is None else
             "WRITE_TRUNCATED" if _write_truncated else
             "OBSERVED" if out["position_readback_rows"] > 0 else "OBSERVED_EMPTY"),
            out["position_readback_rows"], _rb_anchor_ts,
            (f"account read raised: {_read_error}" if _read_error is not None else
             "DRY_RUN has no account (binance_broker.account_snapshot returns None by design)"
             if snap is None else
             f"logger refused a row and the write stopped there — {_write_truncated}"
             if _write_truncated else
             "the account was read and every name in the readback universe was written"
             if out["position_readback_rows"] > 0 else
             "the account was read and the readback universe was empty (flat venue, nothing "
             "targeted, nothing held at the previous readback) — observed, not missing"))

        # ── 3. anchors row: one per REBALANCE (not per wakeup) ──────────────────────────────
        # A HOLD/DERISK/FLATTEN anchor has no target vector, no captured mids and no panel hash —
        # four of the six not_null columns. Writing a row anyway would mean inventing them, so
        # the row exists exactly when a rebalance was attempted, and the artefact assertion is
        # conditioned on the same fact rather than expecting a row unconditionally.
        if ctx:
            realized, realized_src = None, "unavailable"
            if snap is not None:
                realized = sum(abs(v) for v in snap["positions_notional"].values())
                realized_src = "fapi/v3/account@post_anchor"
            else:
                st = _load(STATE_PATH, {})
                if st.get("positions"):
                    realized = sum(abs(v) for v in st["positions"].values())
                    realized_src = "cached book (no venue read; DRY_RUN or read failed)"
            try:
                row = self.executor.anchor_row(
                    anchor_ts=ctx["anchor_ts"], mids=ctx["mids"],
                    target_notional=ctx["target"], realized_gross=realized,
                    n_skipped=ctx["n_skipped"], regime=ctx["regime"],
                    factor_version=ctx["factor_version"], panel_hash=ctx["panel_hash"])
                row["realized_gross_source"] = realized_src
                row["rebalance_id"] = ctx.get("rebalance_id")
                row["regime_source"] = ctx.get("regime_source")
                row["opening_halted"] = bool(outA.get("off_schedule_halt")
                                             or outA.get("watchdog_halt")
                                             or outA.get("book_unobserved_halt"))
                # ★★ EXE-01: a halt that did NOT flatten the book (a proportional local response) is named on the row.
                #   Measured before this line existed (quant_research FX_W6C receipts, probe_third_anchor): after a local
                #   response the next halted anchor submitted nothing, position_break read it as `halted_intent_flat`
                #   (intent ZERO), the still-held book was a 99% "deviation", and §4-5e tripped the whole-book ladder —
                #   the proportional response undone one anchor later. Written only for that halt, so every other row
                #   is byte-identical.
                # ★★ W6C-B13 is the SECOND such halt and needs the same marker for the same
                #   reason: a run that refused to open because it could not see the book has sold
                #   nothing, so judging its no-submission anchor against intent ZERO would read the
                #   whole held book as a break and trip the ladder one anchor later — an
                #   instrument's doubt closing the book by the back door. `proportional_local`
                #   wins when both fired: it is the stronger statement about the same row.
                # ★★ W6C-I6 is the THIRD, and the most reachable: gate 0c refuses OPENING on a run
                #   that is not the scheduled anchor and keeps every reduce-only path, so that
                #   anchor closes nothing either. Without the marker it is judged against intent
                #   ZERO — measured on the real 2026-08-01 06:29Z off-schedule LIVE anchor with
                #   that day's real book: 96.39% of gross against a 1% limit, §4-5e tripped, all
                #   105 names flattened. Three LIVE off-schedule runs have already happened and
                #   were CLEAN only because the book was empty at the time.
                # ★ NOT when this run is EMPTYING the book on purpose: on a staleness-ladder
                #   FLATTEN the positions are going away, and intent ZERO is the right judgement.
                _wh = outA.get("watchdog_halt") or {}
                if _wh.get("state_kind") == "proportional_local" and _wh.get("book_flattened") is False:
                    row["halt_kind"] = "proportional_local"
                elif outA.get("book_unobserved_halt"):
                    row["halt_kind"] = "book_unobserved"
                elif outA.get("off_schedule_halt") and outA.get("action") != "FLATTEN":
                    row["halt_kind"] = "off_schedule"
                row["rows_persisted"] = (outB or {}).get("rows_persisted")
                # ★ the mixture travels with the row, not with the run log
                row["weights"] = ctx.get("weights")
                # ★ INTENT neutrality + what it cost to get there. Distinct from the venue-truth
                # neutrality added below: this one says the book we DECIDED was neutral, that one
                # says the book we ACHIEVED was. Both are needed — 16:01Z had intent +40.76 and
                # realised -6.92% of gross, and only having both separates planning from execution.
                row["reshape"] = ctx.get("reshape")
                # ★ WHICH BOOK, as a column (2026-08-22): downstream readers (watchdog/IC monitor/
                #   guard_twin) must not parse factor_version to learn it.
                row["book_source"] = ctx.get("book_source", "internal")
                if ctx.get("external_book"):
                    row["external_book"] = ctx["external_book"]
                # ── M3-BEGIN
                if ctx.get("m3_beta_overlay") is not None:
                    row["m3_beta_overlay"] = ctx["m3_beta_overlay"]
                # ── M3-END
                # ★ realised neutrality, measured from venue truth and recorded every anchor
                if snap is not None:
                    row.update(neutrality_from_snapshot(snap))
                    out["venue_net_over_gross"] = row.get("net_over_gross")
                # ── M3-BEGIN  the neutrality readers judge the book EX-OVERLAY when the leg was placed (the raw venue net stays
                #    on the row as `net_over_gross`; `net_ex_overlay_*` beside it). No leg ⇒ `_m3_nrow is row`.
                _m3_nrow = BO.neutrality_view(row, ctx.get("m3_beta_overlay"), venue_btc_usdt=(
                    None if snap is None else float((snap.get("positions_notional") or {}).get(BO.BTC, 0.0) or 0.0)))
                # ── M3-END
                # ★★★ THE -2022 RESOLUTION, RUN HERE BECAUSE THIS IS WHERE THE READBACK IS — and
                # BEFORE `log.anchor`, because a fact established after the write never reaches
                # the ledger. (My first draft put it below, next to the alarms; the alarm would
                # have fired and the row would have carried nothing. A hand-off point that
                # produces its fact after the hand-off is a shape this repo has paid for before.)
                # A -2022 means "no position to reduce": benign if the venue confirms flat, a
                # book/venue disagreement if it arrives while we believe we hold. `classify` has
                # always named that undecidability (`reduce_only_rejected_verify_position`), and
                # nothing has ever performed the deciding step — until the reduce-only tagging
                # landed, the rebalance path sent no reduceOnly orders at all.
                # ★ `snap` may be None (the account read failed above), passed through as None on
                #   purpose: the resolver then reports `unresolved` rather than reading a missing
                #   snapshot as "everything is flat", which would resolve every rejection benign
                #   at exactly the moment we can see least.
                _ro = RO.resolve(getattr(self.executor, "reduce_only_rejects", []),
                                 None if snap is None else snap.get("positions_notional"))
                if _ro["n"]:
                    row["reduce_only_rejects"] = _ro
                # ★★★ THE KNOWN-GAP LEDGER — what this anchor did NOT do, named and sized.
                # Two liquidations in eight hours had one shape: a leg ends, nothing downstream
                # picks the name up, and the residual becomes indistinguishable from an
                # unexplained position break. This writes down the ones we KNEW about.
                # ★ RECORD ONLY. No guard reads it; §4-5e/§4-6 consuming it as the underfill
                #   explanation set is a change to a stop-loss's consequence level and goes
                #   through B's pre-registration. Recording is free; teaching a stop-loss to
                #   forgive is not.
                try:
                    import order_disposition as _OD
                    _unk = _OD.unknown_reasons(self.executor.rows_orders)
                    if _unk:
                        # a terminal state with no cell in the matrix is a DEFECT, not a default
                        self.alarm("HIGH",
                                   f"终态处置矩阵缺格: {_unk} —— 有订单以矩阵未申报的终态结束, "
                                   f"其残差无人接手且无人记录。补 order_disposition.DISPOSITION。")
                    row["known_gaps"] = _OD.gaps(self.executor.rows_orders,
                                                 ctx.get("rebalance_id"))
                except Exception as e:
                    self.alarm("HIGH", f"known-gap ledger failed ({type(e).__name__}: {e}) — "
                                       f"this anchor's unfilled residuals are unrecorded")
                # ★ THE PRICE OF NEUTRALITY — measurement only, nothing acts on it. Accumulating
                #   5-10 anchors of this is the input to the lead's ruling on whether a neutrality
                #   top-up is worth its cost; writing it into the row is how those anchors exist
                #   to be counted later rather than being reconstructed by hand afterwards.
                _np = neutrality_price(_m3_nrow, self.executor.rows_orders, ctx.get("rebalance_id"))  # M3-ORIG:                 _np = neutrality_price(row, self.executor.rows_orders, ctx.get("rebalance_id"))
                if _np is not None:
                    row["neutrality_price"] = _np
                # ★★ THE CHASE EXPERIMENT'S OWN RECORD, plus an INDEPENDENT re-derivation of it.
                #    An assignment nobody can recompute is indistinguishable from one chosen after
                #    the outcome was known, so the artefact carries the seed, the rule, and the
                #    verdict of re-running that rule against the artefact's own numbers. The
                #    re-derivation is written whether it passes or fails: a checker that only
                #    records its successes is not a checker.
                _ce = getattr(self.executor, "_chase_experiment", None)
                if _ce:
                    try:
                        import chase_policy as _CP
                        _ce = dict(_ce, recompute=_CP.recompute_check(_ce))
                        if not _ce["recompute"]["ok"]:
                            self.alarm("HIGH",
                                       f"追价实验的臂别无法从产物自身重算: "
                                       f"{_ce['recompute']['mismatch'][:6]} —— 一个不能被重算的"
                                       f"分配与一个事后挑的分配无法区分, 本锚不得入样本。")
                    except Exception as e:
                        _ce = dict(_ce, recompute={"ok": None, "error": f"{type(e).__name__}: {e}"})
                    row["chase_experiment"] = _ce
                self.log.anchor(**row)
                out["anchors_row"] = True
                _txt = neutrality_alarm_text(_m3_nrow, self.executor.rows_orders,  # M3-ORIG:                 _txt = neutrality_alarm_text(row, self.executor.rows_orders,
                                             ctx.get("rebalance_id"))
                if _txt:
                    self.alarm("HIGH", _txt)
                if _ro["n"]:
                    _rt = RO.alarm_text(_ro, ctx.get("rebalance_id"))
                    if _rt:
                        self.alarm("HIGH", _rt)
            except Exception as e:
                self.alarm("HIGH", f"anchors row rejected ({e}) — M3/M4 lose this anchor's "
                                   f"target-vs-realized record and it cannot be rebuilt later")
                out["anchors_row_error"] = str(e)[:200]

        # ── 4. daily_nav: one row per UTC day, written by the first anchor that can ─────────
        # ★ The guard reads the FILE, not a flag in memory: each anchor is a new process, so an
        # in-memory "already written today" would be false at every anchor and produce six rows.
        # Reading the day's file also makes it self-healing — if the 00:00 anchor is missed, the
        # 04:00 one writes the row instead of the day having none.
        if snap is not None:
            try:
                import pilot_log as _PL
                # ★ THE DAY COMES FROM THE LOGGER, NOT FROM THE CLOCK. The guard asks "does this
                # day already have a NAV row?" and the writer decides which day's file the row
                # lands in — two derivations of one quantity. They agree except across a UTC
                # midnight: a logger opened at 23:59:59 writes into day X while a clock-derived
                # guard checks day X+1, finds it empty, and appends a SECOND row to X while X+1
                # gets none. Found by a test that fixed the logger's day and let the clock be
                # today; in production it would have surfaced once, at midnight, as a duplicate.
                day = self.log.day
                existing = _PL.read_day(os.path.dirname(self.log.dir), day).get("daily_nav", [])
                # ★★★ [B31] A ROW PER ANCHOR, NOT A ROW PER DAY — because §4-2/§4-4 read this and
                # a once-per-day snapshot is CAPTURED BEFORE THE DAY HAPPENS.
                # Measured on the real tree, 2026-07-28: the day's only row was written at 00:16Z
                # with the book FLAT — `realised_pnl 0.0, unrealised_pnl 0.0`, both honest at that
                # instant — and the book was rebuilt to $23,400 at 04:00Z. cond2 computes the
                # day's loss as `realised + unrealised` OF THAT ROW, so §4-2 would have read
                # 0.00% for the rest of the day no matter what the book did. cond4's drawdown
                # shares the input.
                # ★ THE FORM IS THE POINT: the code immediately below says a missing realised_pnl
                #   must stay None because "a zero would un-blind the stop-loss with a fabricated
                #   number". This 0.0 was not fabricated — it was MEASURED, and true, and then it
                #   went stale. A guard against fabrication does not guard against staleness, and
                #   the two arrive at the identical blind stop-loss.
                # ⇒ Appending is what an append-only table can do; EVERY reader therefore takes
                #   the day's LAST row (watchdog cond2, pilot_metrics.stoploss_inputs,
                #   ops/first_real_anchor). Sweeping the readers is not optional — this file's own
                #   comment three lines down records `fee_paid` as the first time a carrier was
                #   fixed without its consumers.
                # ★ NOT TOUCHED, DELIBERATELY: `_prev_nav` (the ACROSS-day comparison) already
                #   returns `rows[-1]` of an earlier day, which is the same "last of the day"
                #   rule. How an overnight unrealised loss should appear in the D+1 row is a
                #   question this change does not answer — the first crossing is 2026-07-29T00:0xZ
                #   and it should be observed before its semantics are chosen.
                out["daily_nav_rows_today_before"] = len(existing)
                prev = self._prev_nav(os.path.dirname(self.log.dir), day)
                eq = snap["equity"]
                # ── the realised half, from the venue's own ledger ───────────────────────
                # Without this the row carries realised_pnl=None and §4's daily-loss
                # stop-loss is BLIND for the day (it refuses to guess, correctly). A failure
                # here must leave None rather than 0.0 — a zero would un-blind the stop-loss
                # with a fabricated number, which is strictly worse than being blind.
                inc, inc_err = None, None
                try:
                    _day_start = _dt_day_start_ms(day)
                    inc = self.broker.income_since(_day_start)
                except Exception as e:
                    inc_err = f"{type(e).__name__}: {str(e)[:120]}"
                    self.alarm("HIGH", f"income ledger unreadable ({inc_err}) — realised P&L "
                                       f"stays UNKNOWN for {day} and the daily-loss stop-loss "
                                       f"is blind for that day")
                # ── M3-BEGIN  R10-A01: the leg's gross enters the row beside the sizing gross ({} when no M3 stage shaped the book)
                _m3nav = BO.nav_fields((ctx or {}).get("m3_beta_overlay"), self.gross, snap)
                # ── M3-END
                self.log.daily_nav(
                    # ★★ THE ROW RECORDS THE POLICY IT WAS WRITTEN UNDER. Without this, rows from
                    # the constant-GROSS era (gross pinned at 25,000, leverage drifting up to
                    # 5.4x) are indistinguishable from constant-LEVERAGE rows — and the leverage
                    # backstop, judging them by the new rule, would halt on history. Measured
                    # before this stamp existed: 5.425x on 2026-07-29 rows, i.e. an immediate
                    # false trip. A caliber change makes old rows incomparable; the only safe fix
                    # is to stamp the caliber INTO the row, not to hope the reader remembers.
                    sizing_policy=("constant_leverage_%.2f" % float(
                        (getattr(self, "_last_sizing", None) or {}).get("target_leverage") or 0)
                        if getattr(self, "_last_sizing", None) else "constant_gross_legacy"),
                    day=day, target_gross=self.gross, nav=eq,
                    # ★ None, never 0.0 — see the schema note. Separating realised from
                    # unrealised needs /fapi/v1/income (REALIZED_PNL); the equity snapshot
                    # cannot do it, and a fabricated zero here is a number a stop-loss acts on.
                    realised_pnl=(None if inc is None else inc["realised_pnl"]),
                    realised_pnl_source=(
                        f"UNAVAILABLE ({inc_err or 'no account in this mode'}) — the daily "
                        f"loss stop-loss is blind for this day" if inc is None else
                        "/fapi/v1/income since 00:00Z, sum of "
                        + "+".join(inc["realised_components"])),
                    realised_by_type=(None if inc is None else inc["by_type"]),
                    # round 4 (review A4): the per-asset split and the non-USDT assets are persisted
                    # beside the (USDT-assuming) sum, so a reader can see a foreign-unit row
                    realised_by_type_asset=(None if inc is None else inc.get("by_type_asset")),
                    realised_non_usdt_assets=(None if inc is None else inc.get("non_usdt_assets")),
                    realised_truncated=(None if inc is None else inc["truncated"]),
                    unrealised_pnl=snap["total_unrealized_profit"],
                    wallet_balance=snap["total_wallet_balance"],
                    margin_balance=snap["total_margin_balance"],
                    nav_source="equity = totalWalletBalance + totalUnrealizedProfit "
                               "(/fapi/v3/account)",
                    nav_ts=snap["read_ts"],
                    prev_day=(prev or {}).get("day"), prev_nav=(prev or {}).get("nav"),
                    equity_delta_since_prev=(None if not prev or prev.get("nav") is None
                                             else eq - float(prev["nav"])),
                    # ★ the condition travels WITH the number. An equity delta is P&L only if
                    # nothing was deposited or withdrawn, and this endpoint cannot see
                    # transfers — so the delta is not labelled "pnl" anywhere in the row.
                    external_flow_usdt=(None if inc is None else inc["external_flow"]),
                    external_flow_source=(
                        "UNAVAILABLE — equity_delta_since_prev is P&L ONLY IF no "
                        "deposit/withdrawal occurred, and we cannot say" if inc is None else
                        "/fapi/v1/income incomeType=TRANSFER since 00:00Z"),
                    **_m3nav,  # M3-LINE
                    mode=self.broker.mode)
                out["daily_nav_row"] = True
                # ── M3-BEGIN  after the fills: the actual combined position against the budget the leg was sized under
                for _m3sev, _m3msg in BO.post_fill_check(_m3nav, eq):
                    self.alarm(_m3sev, _m3msg)
                # ── M3-END
            except Exception as e:
                self.alarm("HIGH", f"daily_nav row failed ({e}) — the stop-losses that read NAV "
                                   f"have no input for {time.strftime('%Y-%m-%d', time.gmtime(now))}")
                out["daily_nav_error"] = str(e)[:200]
        return out

    @staticmethod
    def _prev_nav(root: str, day: str) -> Optional[Dict[str, Any]]:
        """The most recent daily_nav row STRICTLY BEFORE `day`, read from disk."""
        try:
            import pilot_log as _PL
            days = [d for d in _PL.available_days(root) if d < day]
            for d in reversed(days):
                rows = _PL.read_day(root, d).get("daily_nav", [])
                if rows:
                    return rows[-1]
        except Exception:
            pass
        return None

    def _scale_to(self, state: Dict[str, Any], frac: float) -> Dict[str, Any]:
        """Cut every position toward frac x its PRE-STALE snapshot. Idempotent: re-running at
        the same stage finds positions already at target and emits nothing. Reduce-only
        throughout, so it composes with the watchdog halt.

        ★ UNITS: live orders are sized in CONTRACTS taken directly from the venue, cut
        PROPORTIONALLY — price-free (a proportional cut needs no mid: target_contracts =
        ref_contracts x frac). The notional dict is bookkeeping only. A prior draft submitted
        notional differences as contract quantities; DRY_RUN hid it because readback is empty.

        ★ UNKNOWN QUANTITIES (R16RF-E1 / RFR-RECOVERY, independent review rounds 3–4, 2026-09-17).
        A quantity that is not a finite number is UNKNOWN — never a reference, never a cut, never zero.
        The pre-stale snapshot therefore records only KNOWN quantities and lists the unknown names in
        `state["stale_ref_unknown"]`. RECOVERY RULE, stated in advance so a retry can never shrink a base:
          * unknown at the snapshot → finite later: the FIRST finite reading observed during this stale
            period becomes that name's LATE reference (recorded in `state["stale_ref_late"][sym]` with the
            frac at adoption), set ONCE and never lowered by a later reading; it is NOT a claim about the
            pre-stale size (which was never read) — a HIGH alarm says so, and the cut toward frac x late
            reference applies from that anchor on. This is a RECOVERY POLICY CHOICE, not a derived guarantee
            (independent review round 5, 2026-09-17): opening is halted, but an order placed BEFORE the signal
            went stale can still fill late, so the late reading may sit above OR below the never-read pre-stale
            size — the cut can be smaller or larger than the proportional one. The choice is made because
            leaving the name at full exposure for the rest of the stage would defeat the ladder; the
            alternative (hold + alarm only, no cut) is a one-line switch and the operator's ruling.
          * unknown at the snapshot → absent later (the venue reports no position): resolved FLAT, alarmed,
            nothing to cut.
          * finite at the snapshot → unknown later → finite again: the ORIGINAL reference stands; the cut
            resumes. While unknown, the name is skipped by name and alarmed every anchor.
          * a finite name that was ABSENT at the snapshot and appears later is treated like the first case
            (late reference, reason "absent_at_snapshot") — the same silent-ignore family.
        Every anchor returns the still-unknown names (`derisk_unknown`), the names adopted this anchor
        (`derisk_recovered`) and the names resolved flat (`derisk_resolved_flat`); nothing is dropped silently."""
        cuts = []
        if self.broker.mode != "DRY_RUN":
            try:
                cur_c = self.broker.positions()                       # CONTRACTS, venue truth
            except Exception as e:
                self.alarm("HIGH", f"DERISK: venue readback failed ({e}); retry next anchor")
                return {"derisked": [], "note": "readback failed; no cuts this anchor"}
            # ★ R16RF-E1 (独立复审第三轮 2026-09-17): broker.positions() 现在把非有限数量原样交上来(未知≠零)。旧码把它
            #   写进 stale_ref_contracts、算 cut_c=NaN, `abs(NaN) < 1e-9` 为假, 于是 quantity=NaN reduce_only 真的进了 submit。
            #   规矩与 watchdog 同: 「存在但不是有限数 = 仓位未知」—— 不作参考、不定量、不当零; 具名列出并告警, 有限部分照常。
            def _fin(v):
                try:
                    return math.isfinite(float(v))
                except (TypeError, ValueError, OverflowError):
                    return False
            _unknown_now = sorted(k for k, v in cur_c.items() if not _fin(v))
            cur_f = {k: float(v) for k, v in cur_c.items() if _fin(v)}
            if _unknown_now:
                self.alarm("HIGH", f"DERISK: {len(_unknown_now)} name(s) returned a NON-FINITE quantity {_unknown_now[:5]} — "
                                   f"position UNKNOWN: not cut, not used as reference, not treated as flat")
            if state.get("stale_ref_contracts") is None:
                state["stale_ref_contracts"] = dict(cur_f)                    # only KNOWN quantities become the reference
                state["stale_ref_unknown"] = list(_unknown_now)
            ref_c = state["stale_ref_contracts"]
            unknown = list(_unknown_now)
            # ── RFR-RECOVERY: names with NO reference yet (unknown or absent at the snapshot) that are readable now ──
            _ref_unknown = [k for k in (state.get("stale_ref_unknown") or []) if k not in ref_c]
            _late = state.setdefault("stale_ref_late", {})
            recovered, resolved_flat = [], []
            for sym in sorted(set(_ref_unknown) | (set(cur_f) - set(ref_c))):
                if sym in cur_f:                                  # readable and finite now: adopt the LATE reference, once
                    ref_c[sym] = cur_f[sym]
                    _late[sym] = {"value": cur_f[sym], "frac_at_adoption": frac,
                                  "reason": "unknown_at_snapshot" if sym in _ref_unknown else "absent_at_snapshot",
                                  "rule": "first finite reading during this stale period; set once, never lowered"}
                    recovered.append(sym)
                    self.alarm("HIGH", f"DERISK: {sym} quantity now reads {cur_f[sym]} but had NO reference "
                                       f"({_late[sym]['reason']}) — LATE reference adopted = {cur_f[sym]} (not the pre-stale "
                                       f"size, which was never read); cut toward {frac:.0%} applies from this anchor")
                elif sym in _ref_unknown and sym not in cur_c:     # unknown at the snapshot, absent now: resolved FLAT
                    _late[sym] = {"value": 0.0, "resolved": "flat_on_recovery", "frac_at_resolution": frac}
                    resolved_flat.append(sym)
                    self.alarm("HIGH", f"DERISK: {sym} was UNKNOWN at the pre-stale snapshot and now reads FLAT "
                                       f"(absent from the venue's positions) — resolved, nothing to cut")
                # still non-finite: stays in stale_ref_unknown and in `unknown` (alarmed above every anchor)
            state["stale_ref_unknown"] = [k for k in (state.get("stale_ref_unknown") or [])
                                          if k not in recovered and k not in resolved_flat]
            for sym, ref_amt in ref_c.items():
                if sym in _unknown_now or not _fin(ref_amt):               # unknown now, or an unknown reference: skip by name
                    if sym not in unknown:
                        unknown.append(sym)
                    continue
                cut_c = cur_f.get(sym, 0.0) - float(ref_amt) * frac
                if not _fin(cut_c) or abs(cut_c) < 1e-9:
                    continue
                try:
                    self.broker.submit({"symbol": sym, "side": "sell" if cut_c > 0 else "buy",
                                        "quantity": abs(cut_c), "reduce_only": True, "tif": "IOC"},
                                       f"stale-signal ladder: DERISK to {frac:.0%}")
                    cuts.append(sym)
                except Exception as e:
                    cuts.append(f"{sym}:FAILED:{e}")     # ladder retries at the next anchor
            # bookkeeping follows proportionally (notional scales like contracts under a cut)
            for sym in list(state.get("positions", {})):
                ref_n = (state.get("stale_ref_positions") or {}).get(sym)
                if ref_n is not None:
                    state["positions"][sym] = ref_n * frac
            return {"derisked": cuts, "derisk_unknown": sorted(unknown), "derisk_recovered": recovered,
                    "derisk_resolved_flat": resolved_flat,
                    "note": f"gross scaled toward {frac:.0%} of pre-stale ref"
                            + (f"; {len(unknown)} name(s) UNKNOWN (non-finite) not cut" if unknown else "")
                            + (f"; {len(recovered)} name(s) adopted a LATE reference this anchor" if recovered else "")
                            + (f"; {len(resolved_flat)} name(s) resolved FLAT" if resolved_flat else "")}

        # DRY_RUN: no venue, notional bookkeeping only (smoke path; live path above)
        ref = state.get("stale_ref_positions") or {}
        for sym, ref_notional in ref.items():
            target = ref_notional * frac
            current = state.get("positions", {}).get(sym, 0.0)
            cut = current - target
            if abs(cut) < 1e-6:
                continue
            try:
                self.broker.submit({"symbol": sym, "side": "sell" if cut > 0 else "buy",
                                    "quantity": abs(cut), "reduce_only": True, "tif": "IOC"},
                                   f"stale-signal ladder: DERISK to {frac:.0%}")
                state["positions"][sym] = target
                cuts.append(sym)
            except Exception as e:
                cuts.append(f"{sym}:FAILED:{e}")
        return {"derisked": cuts, "note": f"gross scaled toward {frac:.0%} of pre-stale ref"}
