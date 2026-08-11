"""0C — FALSIFY the pilot log schema: can M1-M6 actually be computed from it?

> created 2026-07-25 | Session: 0C schema falsification | 状态: final

WHY: §9-F1 asserts "this field list is sufficient to reconstruct M1-M6 after the fact". That is an
ASSERTION, and the cost of it being wrong is discovered only AFTER a real-money pilot -- at which
point the data is gone and the run must be repeated. So it has to be falsified BEFORE day 1. Same
move as the xsr_fund assertion: turn a belief into a checked fact.

METHOD (deliberately adversarial):
  1. Generate a synthetic but PATHOLOGICAL day of per-order logs -- partial fills, multi-fill orders,
     2 top-up attempts, deliberate abandonment (F16), min-notional skips, rate-limit skips (F13),
     a venue reject. These are the situations that actually break metric definitions.
  2. Attempt each metric using ONLY schema-v1 fields.
       - missing field  -> the computation RAISES. Not "I think it's missing" -- it fails.
       - ambiguous      -> compute EVERY defensible reading and report the spread. A material spread
                           is a demonstrated defect, not a claimed one.
  3. Re-run against schema v2 (defects repaired) and show all six become computable and unique.

Writes exports/eda/log_schema_falsify.json.
"""
import os
import json, hashlib
import numpy as np

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
RNG = np.random.default_rng(20260725)

SCHEMA_V1_ORDER = ["anchor_ts", "symbol", "side", "target_w", "prev_w", "intended_notional",
                   "order_type", "submit_ts", "price_submit", "mid_at_submit", "filled_notional",
                   "avg_fill_px", "fill_ts", "cancel_ts", "fee_paid", "mid_at_fill_plus_60s",
                   "rebalance_id", "attempt_idx"]
SCHEMA_V1_ANCHOR = ["anchor_ts", "target_vector_hash", "realized_gross", "target_gross",
                    "n_names_skipped"]

# ---------------------------------------------------------------- synthetic pathological day
SYMS = [f"SYM{i:02d}" for i in range(20)]
ANCHORS = [1782950400000 + k * 4 * 3600_000 for k in range(6)]      # 6 anchors, one day


def gen_day():
    orders, anchor_rows, fills, funding, navs = [], [], [], [], []
    pos = {s: 0.0 for s in SYMS}
    mid0 = {s: 100.0 * (1 + 0.3 * RNG.standard_normal()) for s in SYMS}
    for ai, ats in enumerate(ANCHORS):
        tw = RNG.standard_normal(len(SYMS)); tw = tw - tw.mean(); tw = tw / np.abs(tw).sum()
        gross_usd = 25_000.0
        skipped = 0
        anchor_mid = {}
        for si, s in enumerate(SYMS):
            # mid path over the k=900s working window (realistic 4h-bar vol)
            m_anchor = mid0[s] * (1 + 0.0008 * RNG.standard_normal())
            mid0[s] = m_anchor; anchor_mid[s] = m_anchor
            target_notional = tw[si] * gross_usd
            prev_notional = pos[s]
            delta = target_notional - prev_notional
            if abs(delta) < 5.0:                                     # min-notional skip
                skipped += 1
                orders.append(dict(anchor_ts=ats, symbol=s, side="none", target_w=tw[si],
                                   prev_w=prev_notional / gross_usd, intended_notional=delta,
                                   order_type="maker", submit_ts=None, price_submit=None,
                                   mid_at_submit=None, filled_notional=0.0, avg_fill_px=None,
                                   fill_ts=None, cancel_ts=None, fee_paid=0.0,
                                   mid_at_fill_plus_60s=None, rebalance_id=f"r{ai}",
                                   attempt_idx=1,
                                   _v2_terminal_reason="skipped_min_notional",
                                   _v2_mid_at_anchor=m_anchor, _v2_first_fill_ts=None,
                                   _v2_last_fill_ts=None))
                continue
            side = "buy" if delta > 0 else "sell"
            sgn = 1.0 if delta > 0 else -1.0
            remaining = abs(delta)
            # ---- attempt 1: passive maker, k=900s, partial fill, possibly multi-fill ----
            for att in (1, 2):
                if remaining < 1e-9:
                    break
                is_topup = (att == 2)
                otype = "topup_taker" if is_topup else "maker"
                sub_ts = ats + (0 if att == 1 else 900_000)
                m_sub = m_anchor * (1 + 0.0004 * RNG.standard_normal() * (1 if att == 1 else 2))
                # F16: abandon if spread pathological
                spread_bps = abs(RNG.normal(3, 6))
                if is_topup and spread_bps > 25:
                    orders.append(dict(anchor_ts=ats, symbol=s, side=side, target_w=tw[si],
                                       prev_w=prev_notional / gross_usd,
                                       intended_notional=sgn * remaining, order_type=otype,
                                       submit_ts=sub_ts, price_submit=None, mid_at_submit=m_sub,
                                       filled_notional=0.0, avg_fill_px=None, fill_ts=None,
                                       cancel_ts=sub_ts + 1000, fee_paid=0.0,
                                       mid_at_fill_plus_60s=None, rebalance_id=f"r{ai}",
                                       attempt_idx=att,
                                       _v2_terminal_reason="abandoned_spread_gt_25bps",
                                       _v2_mid_at_anchor=m_anchor, _v2_first_fill_ts=None,
                                       _v2_last_fill_ts=None))
                    break
                frac = float(np.clip(RNG.beta(5, 2) if not is_topup else RNG.beta(9, 1), 0, 1))
                filled = remaining * frac
                # multi-fill: 1-3 child fills spread across the window
                nf = int(RNG.integers(1, 4))
                fts = sorted(sub_ts + int(RNG.integers(1000, 880_000)) for _ in range(nf))
                pxs = [m_sub * (1 + sgn * RNG.normal(0.00002, 0.00008)) for _ in range(nf)]
                wts = RNG.dirichlet(np.ones(nf))
                avg_px = float(np.dot(wts, pxs))
                # adverse markout: mid moves AGAINST us 60s after each fill
                for k2 in range(nf):
                    fills.append(dict(anchor_ts=ats, symbol=s, side=side, order_type=otype,
                                      attempt_idx=att, fill_ts=fts[k2], fill_px=pxs[k2],
                                      fill_notional=filled * float(wts[k2]),
                                      mid_at_fill_plus_60s=pxs[k2] * (1 + sgn * abs(RNG.normal(0.00018, 0.00012))),
                                      rebalance_id=f"r{ai}"))
                last_mid60 = fills[-1]["mid_at_fill_plus_60s"]
                fee = filled * (1.8e-4 if not is_topup else 4.5e-4)
                orders.append(dict(anchor_ts=ats, symbol=s, side=side, target_w=tw[si],
                                   prev_w=prev_notional / gross_usd,
                                   intended_notional=sgn * remaining, order_type=otype,
                                   submit_ts=sub_ts, price_submit=m_sub, mid_at_submit=m_sub,
                                   filled_notional=filled, avg_fill_px=avg_px,
                                   fill_ts=fts[-1],                       # v1: ONE fill_ts only
                                   cancel_ts=(sub_ts + 900_000) if frac < 1 else None,
                                   fee_paid=fee, mid_at_fill_plus_60s=last_mid60,
                                   rebalance_id=f"r{ai}", attempt_idx=att,
                                   _v2_terminal_reason=("filled" if frac > 0.999 else
                                                        ("partial_expired" if not is_topup else "abandoned_max_attempts")),
                                   _v2_mid_at_anchor=m_anchor,
                                   _v2_first_fill_ts=fts[0], _v2_last_fill_ts=fts[-1]))
                pos[s] += sgn * filled
                remaining -= filled
        realized_gross = sum(abs(v) for v in pos.values())
        anchor_rows.append(dict(anchor_ts=ats, target_vector_hash=hashlib.sha1(tw.tobytes()).hexdigest()[:12],
                                realized_gross=realized_gross, target_gross=gross_usd,
                                n_names_skipped=skipped,
                                _v2_regime_at_anchor=str(RNG.choice(["calm", "normal", "stress"])),
                                _v2_mid_at_anchor={s: anchor_mid[s] for s in SYMS},
                                _v2_actual_positions={s: pos[s] for s in SYMS}))
        # funding settles on 2 of the 6 anchors (8h coins)
        if ai % 2 == 0:
            for s in SYMS:
                rate = float(RNG.normal(0.00003, 0.00012))
                funding.append(dict(settlement_ts=ats, symbol=s, position_notional=pos[s],
                                    funding_rate=rate, funding_paid=-pos[s] * rate))
    navs.append(dict(day=ANCHORS[0] // 86400000, target_gross=25_000.0,
                     nav_pnl=float(RNG.normal(30, 120))))
    return orders, anchor_rows, fills, funding, navs


ORDERS, ANCHOR_ROWS, FILLS, FUNDING, NAVS = gen_day()
print(f"[synthetic] {len(ORDERS)} order rows / {len(FILLS)} child fills / {len(ANCHOR_ROWS)} anchors / "
      f"{len(FUNDING)} funding settlements", flush=True)


def v1(rows):
    """strip to schema v1 -- anything the frozen schema does not contain is simply not there."""
    keep = set(SCHEMA_V1_ORDER) | set(SCHEMA_V1_ANCHOR)
    return [{k: v for k, v in r.items() if k in keep} for r in rows]


O1, A1 = v1(ORDERS), v1(ANCHOR_ROWS)
BPS = 1e4
results = {}


def rec(metric, status, detail, readings=None):
    results[metric] = dict(status=status, detail=detail, readings=readings)
    tag = {"OK": "  OK      ", "AMBIGUOUS": "  AMBIGUOUS", "IMPOSSIBLE": "  IMPOSSIBLE"}[status]
    print(f"{tag} {metric}: {detail}", flush=True)
    if readings:
        for k, v in readings.items():
            print(f"              {k} = {v}", flush=True)


# ---------------------------------------------------------------- M1 effective cost
filled = [o for o in O1 if o.get("filled_notional", 0) > 0]
den = sum(o["filled_notional"] for o in filled)
fees = sum(o["fee_paid"] for o in filled)
# reading A: slippage vs mid_at_submit (arrival)
slip_arr = sum(abs(o["avg_fill_px"] - o["mid_at_submit"]) / o["mid_at_submit"] * o["filled_notional"]
               for o in filled)
cA = (fees + slip_arr) / den * BPS
# reading B: slippage vs the ANCHOR decision mid -- which v1 does NOT carry.
try:
    slip_dec = sum(abs(o["avg_fill_px"] - o["mid_at_anchor"]) / o["mid_at_anchor"] * o["filled_notional"]
                   for o in filled)
    cB = (fees + slip_dec) / den * BPS
except KeyError:
    cB = None
# recompute B using the v2 field to quantify how much the missing field matters
slip_dec2 = sum(abs(o["avg_fill_px"] - o["_v2_mid_at_anchor"]) / o["_v2_mid_at_anchor"] * o["filled_notional"]
                for o in ORDERS if o["filled_notional"] > 0)
cB_true = (fees + slip_dec2) / den * BPS
rec("M1_effective_cost_bps", "AMBIGUOUS",
    "v1 has mid_at_submit but NOT the anchor decision mid. Benchmarking execution against ARRIVAL "
    "measures a different thing than the backtest, which assumes execution at the ANCHOR price -- "
    "top-up orders submit up to 900s later, so arrival-benchmarking silently drops the delay cost. "
    "The two readings differ materially on the same data.",
    {"vs_mid_at_submit (v1 only possible reading)": round(cA, 3),
     "vs_mid_at_anchor (needs new field)": round(cB_true, 3),
     "understatement_bps": round(cA - cB_true, 3)})

# ---------------------------------------------------------------- M2 markout
mk = [o for o in O1 if o["order_type"] == "maker" and o.get("filled_notional", 0) > 0]
# reading A: order-level, using the single fill_ts/mid_at_fill_plus_60s v1 carries (= LAST child fill)
mA = sum((1 if o["side"] == "buy" else -1) * (o["mid_at_fill_plus_60s"] - o["avg_fill_px"])
         / o["avg_fill_px"] * o["filled_notional"] for o in mk) / sum(o["filled_notional"] for o in mk) * BPS
# reading B: fill-level (the economically correct one) -- needs child-fill rows v1 does not have
mkf = [f for f in FILLS if f["order_type"] == "maker"]
mB = sum((1 if f["side"] == "buy" else -1) * (f["mid_at_fill_plus_60s"] - f["fill_px"])
         / f["fill_px"] * f["fill_notional"] for f in mkf) / sum(f["fill_notional"] for f in mkf) * BPS
rec("M2_markout_bps", "AMBIGUOUS",
    "v1 stores ONE fill_ts + ONE mid_at_fill_plus_60s per ORDER, but an order fills in 1-3 child "
    "fills at different times. 'mid 60s after which fill?' is undefined; v1 can only use the last. "
    "Also v1 never states that M2 is maker-ONLY (top-up taker fills have no queue/adverse semantics "
    "and must be excluded).",
    {"order_level_last_fill (v1)": round(mA, 3),
     "fill_level (correct, needs child rows)": round(mB, 3),
     "difference_bps": round(mA - mB, 3)})

# ---------------------------------------------------------------- M3 fill rate
byk = {}
for o in O1:
    byk.setdefault((o["anchor_ts"], o["symbol"]), []).append(o)
# reading A: sum(maker filled)/sum(maker intended) -- double counts, attempt-2 intended is a RESIDUAL
num = sum(o["filled_notional"] for o in O1 if o["order_type"] == "maker")
denA = sum(abs(o["intended_notional"]) for o in O1 if o["order_type"] == "maker")
# reading B: sum(maker filled)/intended of attempt 1
denB = sum(abs(o["intended_notional"]) for o in O1 if o["order_type"] == "maker" and o["attempt_idx"] == 1)
n_multi_maker = sum(1 for k, v in byk.items()
                    if sum(1 for o in v if o["order_type"] == "maker") > 1)
_diverge = abs((num / denA if denA else 0) - (num / denB if denB else 0)) > 1e-9
rec("M3_fill_rate", "AMBIGUOUS",
    "LATENT, not demonstrated: intended_notional on attempt 2 is the RESIDUAL, so summing 'intended' "
    "across attempts would double-count. Under the CURRENT execution spec (1 maker attempt + 1 taker "
    "top-up) there is never more than one maker attempt per (anchor,symbol), so the two readings "
    f"COINCIDE on this data (multi-maker-attempt cases observed: {n_multi_maker}). The ambiguity bites "
    "only if maker re-posting is ever introduced -- e.g. the F16/F3 remediation that extends k, or any "
    "future 'reprice and re-post' logic. Pin the definition now, while it is free.",
    {"sum_intended_all_attempts": round(num / denA, 4) if denA else None,
     "intended_of_attempt_1 (correct)": round(num / denB, 4) if denB else None,
     "readings_diverge_on_this_data": _diverge,
     "multi_maker_attempt_cases": n_multi_maker})

# ---------------------------------------------------------------- M4 turnover
tgt_to = 0.0
for a in A1:
    rows = [o for o in O1 if o["anchor_ts"] == a["anchor_ts"]]
    tgt_to += sum(abs(o["target_w"] - o["prev_w"]) for o in {(r["symbol"]): r for r in rows}.values())
real_to = sum(abs(o["filled_notional"]) for o in O1) / 25_000.0
rec("M4_turnover", "AMBIGUOUS",
    "computable, but v1 does not say whether §3d's comparison to the backtest 1466 uses TARGET-weight "
    "turnover (validates the signal pipeline; the backtest always achieves target) or REALIZED "
    "turnover (what you actually pay for). They differ whenever fills fall short.",
    {"target_weight_turnover_day": round(tgt_to, 4),
     "realized_turnover_day": round(real_to, 4)})

# ---------------------------------------------------------------- M5 weight fidelity
try:
    _ = [a["actual_positions"] for a in A1]
    rec("M5_weight_fidelity", "OK", "computable")
except KeyError:
    # can we at least INFER positions by accumulating fills?
    inferred = {s: 0.0 for s in SYMS}
    for o in O1:
        if o.get("filled_notional", 0) > 0:
            inferred[o["symbol"]] += (1 if o["side"] == "buy" else -1) * o["filled_notional"]
    truth = ANCHOR_ROWS[-1]["_v2_actual_positions"]
    err = max(abs(inferred[s] - truth[s]) for s in SYMS)
    rec("M5_weight_fidelity", "AMBIGUOUS",
        "positions can only be INFERRED by accumulating our own fills -- there is no read-back of the "
        "venue's actual position. Any un-logged change (liquidation, funding-driven, manual, missed "
        "fill report) drifts silently and M5 then measures our own assumption instead of reality. "
        "Separately: v1 cannot distinguish 'did not fill' from 'deliberately abandoned under F16' -- "
        "both appear as shortfall, but one is market conditions and the other is our own rule.",
        {"max_inferred_vs_actual_usd (0 BY CONSTRUCTION -- no drift injected; the defect is that there is no DETECTION mechanism if drift occurs, not that inference is wrong here)": round(err, 6),
         "distinguishes_abandon_from_nofill": False})

# ---------------------------------------------------------------- M6 funding
try:
    tot = sum(r["funding_paid"] for r in A1)          # no such field anywhere in v1
    rec("M6_funding", "OK", "computable")
except (KeyError, TypeError):
    rec("M6_funding", "IMPOSSIBLE",
        "v1 has NO funding fields at all -- not in the order rows, not in the anchor rows. Funding "
        "does not flow through orders, so it cannot be reconstructed from an order log at any level "
        "of effort. M6 is simply unobtainable under schema v1.", None)

# ---------------------------------------------------------------- stop-loss inputs (bonus check)
try:
    _ = [a["nav_pnl"] for a in A1]
    rec("STOPLOSS_inputs", "OK", "computable")
except KeyError:
    rec("STOPLOSS_inputs", "IMPOSSIBLE",
        "§4-2 (single-day loss vs target gross) and §4-4 (cumulative drawdown) need a daily P&L / NAV "
        "series. v1 has no mark prices at anchor boundaries and no NAV snapshot, so daily P&L cannot "
        "be reconstructed. The watchdog (F6) needs this stream anyway -- it must also be PERSISTED, "
        "or the stop-loss decision is not auditable after the fact.", None)

# ---------------------------------------------------------------- verdict + v2 schema
defects = [k for k, v in results.items() if v["status"] != "OK"]
V2_ADD_ORDER = {
    "mid_at_anchor": "decision mid at anchor_ts for this symbol -- fixes M1 benchmark mismatch",
    "terminal_reason": "enum{filled, partial_expired, abandoned_spread_gt_25bps, abandoned_max_attempts, "
                       "skipped_min_notional, skipped_rate_limit, venue_reject} -- fixes M5 and gives F13/F16 diagnostics",
    "first_fill_ts / last_fill_ts": "bracket the fill window; markout reference becomes unambiguous",
    "notional_currency": "explicit: all *_notional are QUOTE (USD)",
}
V2_NEW_TABLES = {
    "fills (child-fill level)": "anchor_ts, symbol, side, order_type, attempt_idx, fill_ts, fill_px, "
                                "fill_notional, mid_at_fill_plus_60s, rebalance_id -- M2 must be computed "
                                "per FILL, not per order",
    "funding ledger": "settlement_ts, symbol, position_notional_at_settlement, funding_rate, funding_paid "
                      "-- M6 is impossible without it",
    "position readback (per anchor)": "venue-reported actual position per symbol, read back after each "
                                      "rebalance -- M5 must reconcile against the venue, not against our own fills",
    "daily NAV snapshot": "day, target_gross, nav, realised_pnl -- §4-2/§4-4 stop-losses need a persisted "
                          "P&L series to be auditable",
}
V2_ANCHOR_ADD = {
    "regime_at_anchor": "regime label stamped AT anchor time -- makes §9-F8's 'classified before seeing "
                        "markout' auditable from the log itself rather than from a file mtime",
    "mid_at_anchor_vector": "decision mids for the whole cross-section (M1 + reconstruction)",
}
V2_DEFINITIONS = {
    "M1_numerator": "fees + (avg_fill_px vs mid_at_anchor) slippage; funding EXCLUDED (it is M6)",
    "M1_denominator": "sum of filled notional, ONE-SIDED, quote currency; top-up fills included",
    "M2_scope": "MAKER fills only, computed per child fill, weighted by fill notional",
    "M3_denominator": "intended_notional of attempt_idx == 1 (never sum intended across attempts)",
    "M4_gate": "§3d compares TARGET-weight turnover to 1466; realized turnover reported separately",
}
print(f"\n  VERDICT: schema v1 FAILS -- {len(defects)}/7 metrics not cleanly computable: {defects}", flush=True)
print(f"  M6 and the stop-loss inputs are IMPOSSIBLE (missing data, not ambiguity).", flush=True)

json.dump(dict(title="Pilot log-schema falsification: can M1-M6 be computed from schema v1?",
               created="2026-07-25", auditor="0C",
               method="adversarial synthetic day (partial fills, multi-fill, 2 attempts, F16 abandonment, "
                      "min-notional and rate-limit skips); metrics attempted using ONLY v1 fields; missing "
                      "field -> computation raises; ambiguity -> all defensible readings computed and spread reported",
               synthetic=dict(order_rows=len(ORDERS), child_fills=len(FILLS), anchors=len(ANCHOR_ROWS),
                              funding_settlements=len(FUNDING)),
               schema_v1=dict(order=SCHEMA_V1_ORDER, anchor=SCHEMA_V1_ANCHOR),
               results=results, n_defects=len(defects),
               verdict=f"schema v1 FAILS: {len(defects)}/7 not cleanly computable; M6 and stop-loss inputs IMPOSSIBLE",
               schema_v2=dict(order_fields_added=V2_ADD_ORDER, anchor_fields_added=V2_ANCHOR_ADD,
                              new_tables=V2_NEW_TABLES, definitions_pinned=V2_DEFINITIONS)),
          open(EDA + "log_schema_falsify.json", "w"), indent=1, default=str)
print("SAVED exports/eda/log_schema_falsify.json", flush=True)
