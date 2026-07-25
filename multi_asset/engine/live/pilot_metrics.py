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
def m1_effective_cost(orders, regime_by_anchor):
    """bps/side. numerator = fees + |avg_fill_px - mid_at_anchor| slippage; denominator = filled
    notional, one-sided. Returned overall AND stratified by regime."""
    per_regime = defaultdict(lambda: {"fee": 0.0, "slip": 0.0, "den": 0.0, "n": 0})
    tot = {"fee": 0.0, "slip": 0.0, "den": 0.0, "n": 0}
    for o in orders:
        f = float(o["filled_notional"] or 0.0)
        if f <= 0:
            continue
        mid = float(o["mid_at_anchor"])
        slip = abs(float(o["avg_fill_px"]) - mid) / mid * f
        fee = float(o["fee_paid"] or 0.0)
        r = regime_by_anchor.get(o["anchor_ts"], "unknown")
        for acc in (per_regime[r], tot):
            acc["fee"] += fee; acc["slip"] += slip; acc["den"] += f; acc["n"] += 1
    def _c(a):
        return round((a["fee"] + a["slip"]) / a["den"] * BPS, 4) if a["den"] > 0 else None
    return {
        "c_bps_overall": _c(tot),
        "filled_notional_total": round(tot["den"], 2),
        "n_filled_orders": tot["n"],
        "by_regime": {r: {"c_bps": _c(a), "filled_notional": round(a["den"], 2),
                          "n_filled_orders": a["n"]}
                      for r, a in sorted(per_regime.items())},
    }


def m2_markout(fills):
    """maker-only, per CHILD fill, notional-weighted, D=60s. Positive = adverse (mid moved against)."""
    mk = [f for f in fills if f["order_type"] == "maker" and float(f["fill_notional"]) > 0]
    if not mk:
        return {"markout_bps": None, "n_fills": 0, "note": "no maker fills"}
    pairs = []
    for f in mk:
        sgn = 1.0 if f["side"] == "buy" else -1.0
        px = float(f["fill_px"])
        adverse = -sgn * (float(f["mid_at_fill_plus_60s"]) - px) / px * BPS
        pairs.append((adverse, float(f["fill_notional"])))
    return {"markout_bps": round(_wmean(pairs), 4), "n_fills": len(mk),
            "maker_notional": round(sum(w for _, w in pairs), 2),
            "sign_convention": "positive = adverse (mid moved against us 60s after the fill)"}


def m3_fill_rate(orders):
    """maker filled / maker intended on attempt_idx == 1 only."""
    num = sum(float(o["filled_notional"] or 0.0) for o in orders if o["order_type"] == "maker")
    den = sum(abs(float(o["intended_notional"] or 0.0)) for o in orders
              if o["order_type"] == "maker" and int(o["attempt_idx"]) == 1)
    n_multi = 0
    seen = defaultdict(int)
    for o in orders:
        if o["order_type"] == "maker":
            seen[(o["anchor_ts"], o["symbol"])] += 1
    n_multi = sum(1 for v in seen.values() if v > 1)
    return {"fill_rate": round(num / den, 5) if den > 0 else None,
            "maker_filled_notional": round(num, 2),
            "maker_intended_attempt1_notional": round(den, 2),
            "multi_maker_attempt_cases": n_multi,
            "definition": "denominator = intended_notional of attempt_idx==1 only (never summed "
                          "across attempts; attempt 2's intended is a residual)"}


def m4_turnover(orders, anchors):
    """TARGET-weight turnover is the gate (§3d vs 1466); realized reported alongside."""
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
    inferred = defaultdict(float)
    for o in sorted(orders, key=lambda x: x["anchor_ts"]):
        f = float(o["filled_notional"] or 0.0)
        if f > 0:
            inferred[o["symbol"]] += (1 if o["side"] == "buy" else -1) * f
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
    for o in orders:
        short = abs(float(o["intended_notional"] or 0.0)) - float(o["filled_notional"] or 0.0)
        if short > 1e-9:
            reasons[o["terminal_reason"]] += short
    return {"mean_abs_weight_error": round(sum(errs) / len(errs), 6) if errs else None,
            "max_abs_weight_error": round(max(errs), 6) if errs else None,
            "n_comparisons": len(errs),
            "venue_vs_inferred_drift_usd_max": round(max(drift), 6) if drift else None,
            "shortfall_notional_by_terminal_reason": {k: round(v, 2)
                                                      for k, v in sorted(reasons.items())},
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
    bad_examples = []
    for f in funding:
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
            "limit": 0.05, "wiring_error": bool(frac > 0.05), "examples": bad_examples,
            "note": ("bug detector, not an alpha test — a wiring error is a large deterministic "
                     "effect, so no statistical test is appropriate; active from day 1")}


def stoploss_inputs(navs):
    if not navs:
        return {"available": False, "note": "no daily_nav rows -- stop-losses NOT auditable"}
    navs = sorted(navs, key=lambda r: r["day"])
    pnl = [float(r["realised_pnl"]) + float(r.get("unrealised_pnl") or 0.0) for r in navs]
    gross = [float(r["target_gross"]) for r in navs]
    daily_ret = [p / g if g else 0.0 for p, g in zip(pnl, gross)]
    cum, peak, maxdd = 0.0, 0.0, 0.0
    for r in daily_ret:
        cum += r
        peak = max(peak, cum)
        maxdd = min(maxdd, cum - peak)
    return {"available": True, "n_days": len(navs),
            "worst_day_pct_of_target_gross": round(min(daily_ret) * 100, 4),
            "cumulative_pct_of_target_gross": round(cum * 100, 4),
            "max_drawdown_pct_of_target_gross": round(maxdd * 100, 4),
            "note": "denominated in TARGET gross per §9-F12"}


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
