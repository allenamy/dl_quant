#!/usr/bin/env /usr/bin/python3
"""0C signal-side audit — items C / D / F / G: do the produced facts reach a consumer?

C  exit / withheld path: what happens to a position in a name we may no longer open?
D  regime classifier: does its label change ANY trading decision?
F  factor health: what does the decay monitor actually judge, and how fresh is it?
G  funding missing: what does the factor become, and who reads the `blind` list?

Read-only. F makes one `ssh jpline cat <report>` (the same read the production check makes).
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

LIVE = os.path.expanduser("~/dl_quant_live")
for p in (os.path.join(LIVE, "signal"), os.path.join(LIVE, "vendor"),
          os.path.join(LIVE, "live"), os.path.join(LIVE, "ops")):
    sys.path.insert(0, p)

OUT = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/eda/0C_signal_audit_CDFG_wiring.json")


# ── C: a held position that is withheld from the target is never planned ────────────────────
def item_C():
    import binance_executor as BE
    import universe as UNI

    class _F:                       # minimal filter shim: the real one only supplies these
        f = {"ARKMUSDT": {"min_notional": 5.0}, "BTCUSDT": {"min_notional": 5.0}}

        @staticmethod
        def round_qty(sym, q):
            return round(q, 3)

    class _Shim:
        band_bps = 0.0
        filters = _F()

    target = {"BTCUSDT": 1000.0}                       # ARKM was popped by `_untradable`
    held = {"BTCUSDT": 900.0, "ARKMUSDT": 460.36}      # ARKM really is held in state/loop_state
    mids = {"BTCUSDT": 100000.0, "ARKMUSDT": 0.5}
    plans = BE.RebalanceExecutor.plan(_Shim(), target, held, mids)
    planned = {p["symbol"] for p in plans}

    # and the other branch: a held name that is NOT in the prediction set DOES get an exit
    cls_out = UNI.classify(["BTCUSDT", "ARKMUSDT"],
                           {"BTCUSDT": 0.01, "ARKMUSDT": 900.0, "DYMUSDT": 50.0},
                           {"BTCUSDT": "TRADING", "ARKMUSDT": "TRADING", "DYMUSDT": "TRADING"})
    exits = UNI.exit_orders(cls_out["exit_only_held"])

    return {
        "scenario": "ARKMUSDT is a prediction member, still TRADING, held 460 USDT, and is "
                    "withheld because the venue reports maxNotionalValue=0",
        "code_path": "anchor_loop.py:822  `for s_ in self._untradable: target.pop(s_, None)`  ->  "
                     "binance_executor.py:382  `for sym, tgt in target_notional.items()`",
        "symbols_planned": sorted(planned),
        "held_symbols": sorted(held),
        "orphaned_positions": sorted(set(held) - planned),
        "n_rows_for_arkm": sum(1 for p in plans if p["symbol"] == "ARKMUSDT"),
        "the_comment_above_the_code": "\"Existing positions are NOT withheld — a cap of 0 blocks "
                                      "opening, not closing\" (anchor_loop.py:666)",
        "measured_behaviour": "popping the symbol from `target` removes the CLOSING order too: "
                              "plan() iterates the target dict, so a held name that is not in it "
                              "produces no row at all — not even a labelled skip. The position is "
                              "not reduced, not logged, and not alarmed.",
        "the_other_branch_works": {
            "held_name_absent_from_predictions": "DYMUSDT",
            "classified_as": ("exit_only_held" if "DYMUSDT" in cls_out["exit_only_held"]
                              else "NOT ROUTED"),
            "exit_order_built": [o["symbol"] for o in exits],
            "note": "membership churn IS covered — a held name that drops out of the 110 is "
                    "exited with a reduce-only MARKET order. The hole is only for names that "
                    "stay IN the prediction set but become unenterable."},
        "live_state": {
            "ARKMUSDT_held_in_dry_run_state": json.load(
                open(os.path.join(LIVE, "state", "loop_state.json"))
            ).get("positions", {}).get("ARKMUSDT"),
            "ARKMUSDT_held_in_testnet_state": json.load(
                open(os.path.join(LIVE, "state", "testnet", "loop_state.json"))
            ).get("positions", {}).get("ARKMUSDT"),
            "note": "not yet materialised on TESTNET (ARKM was withheld before it was ever "
                    "entered). The reachable sequence is the opposite order: hold the name first, "
                    "then the venue zeroes its cap — which is what a venue does ahead of a "
                    "risk-limit change or a delisting."},
        "recorded_metric_is_wrong_too": {
            "field": "anchors record `n_zero_cap_withheld`",
            "value_recorded_every_anchor": 50,
            "true_number_withheld_from_our_book": 1,
            "true_name": "ARKMUSDT (from the alarm text in state/notify_audit.jsonl, 18 times)",
            "cause": "anchor_loop.py:681 computes `len(blocked & set(tradable + list(blocked)))`, "
                     "which is algebraically `len(blocked)` — the count of zero-cap symbols on the "
                     "WHOLE venue (50 of 730), not the count withheld from our 110. The number is "
                     "a venue property wearing the name of a book property."},
    }


# ── D: does the regime label change anything? ───────────────────────────────────────────────
def item_D():
    import regime_classifier as RC
    src = subprocess.run(
        ["grep", "-rn", "regime", "--include=*.py", LIVE + "/scheduler", LIVE + "/live",
         LIVE + "/signal", LIVE + "/ops"], capture_output=True, text=True).stdout.splitlines()
    consumers = [l for l in src if "tests_" not in l and "regime_classifier.py" not in l]
    return {
        "labels_the_classifier_can_emit": ["calm", "normal", "stress", "unknown"],
        "there_is_no_panic_level": True,
        "thresholds_bps_min": {"calm_max": RC.CALM_MAX, "stress_min": RC.STRESS_MIN},
        "consumers_found": {
            "compute_preds.py": "computes the label and stamps it into preds_latest.json",
            "anchor_loop.py:854-861": "copies the label onto the anchors log row",
            "pilot_metrics.py:73-215": "stratifies REALISED cost c by regime, after the fact",
            "watchdog.py:896-948": "crash-day markout guard, fires only on regime=='stress'"},
        "consumers_that_change_a_trading_decision": [],
        "exposure_is_never_scaled_by_regime": True,
        "the_only_exposure_scaler": "anchor_loop._scale_to, driven by the SIGNAL-STALENESS ladder "
                                    "(HOLD -> DERISK -> FLATTEN), not by regime",
        "stress_branch_execution_count": 0,
        "evidence": "state/testnet/watchdog/last_eval.json: \"no stress anchors among 19146 "
                    "fill(s) — guard had input, found no stress\"",
        "verdict": "the classifier is an ANALYSIS label, and its file says so (§9-F8: it exists so "
                   "that 'that day was stress' cannot be claimed after the fact). It is NOT a risk "
                   "control and nothing in the order path reads it. That is defensible as designed "
                   "— but it means the answer to 'what happens in stress?' is: exactly what "
                   "happens in calm, at the same gross.",
        "n_grep_hits_scanned": len(consumers),
    }


# ── F: what the decay monitor judges, and how fresh the thing it judges is ──────────────────
def item_F():
    import calendar
    import check_factor_health as CFH
    rep = CFH.fetch(timeout_s=25)
    if rep is None:
        return {"error": "report unreachable"}
    ev = CFH.evaluate(rep)

    def age_h(s):
        return round((time.time() - calendar.timegm(
            time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))) / 3600, 1)

    fr = rep.get("frontier") or {}
    src = open(os.path.join(LIVE, "ops", "check_factor_health.py")).read()
    body = src.split("def evaluate(")[1].split("\nLAST =")[0]
    reads_frontier = any(f'"{k}"' in body or f"'{k}'" in body
                         for k in ("frontier", "n_new_anchors", "advanced", "max_anchor_ts_ms"))
    return {
        "who_computes_it": "jpline shadow cron (0 9 * * *) -> exports/live/monitor/"
                           "daily_report.json; read over ssh by ops/check_factor_health.py, "
                           "invoked once per anchor from scheduler/run_anchor.py:443",
        "caliber_judged": rep.get("caliber"),
        "rolling_rank_ic": rep.get("rolling_rank_ic"),
        "decay_alarm_threshold": rep.get("decay_alarm_threshold"),
        "baseline_ic": rep.get("baseline_ic"),
        "margin_over_threshold": round(float(rep["rolling_rank_ic"])
                                       - float(rep["decay_alarm_threshold"]), 4),
        "report_age_h": age_h(rep["as_of"]), "max_stale_h": CFH.MAX_STALE_H,
        "current_verdict": {"ok": ev["ok"], "findings": ev["findings"],
                            "decay_judged": ev["decay_judged"]},
        "★_the_data_frontier": {
            "newest_scored_anchor_utc": fr.get("max_anchor_utc"),
            "frontier_age_h": age_h(fr.get("max_anchor_utc", "")) if fr.get("max_anchor_utc") else None,
            "n_new_anchors_since_previous_run": fr.get("n_new_anchors"),
            "advanced": fr.get("advanced"), "status": fr.get("status"),
            "published_by_the_producer": True,
            "read_by_evaluate()": reads_frontier,
            "note": "check_factor_health's own docstring says this is the signal that matters and "
                    "that it is 'consumed separately'. Grep over this repo finds the word only "
                    "inside that docstring; evaluate() reads as_of, caliber, rolling_rank_ic and "
                    "decay_alarm_threshold, and nothing else."},
        "what_happens_when_decay_trips": "one Telegram alarm, de-duplicated per episode "
                                         "(ops/alarm_episode.py). No block, no de-risk, no gross "
                                         "reduction — the anchor trades normally.",
    }


# ── G: funding missing ───────────────────────────────────────────────────────────────────────
def item_G():
    import funding_panel as FP
    import live_panel as LP
    import panel_build as PB
    syms = LP.panel_symbols()
    fc = LP.FundingCache(symbols=syms)
    kc = LP.KlineCache(symbols=syms)
    ts = kc.ts[-PB.WARMUP_RECOMMENDED_H:]
    rows = fc.as_rows(until_ms=int(ts[-1]))
    F, IH, prov = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)
    anchor = len(ts) - 1
    preds = json.load(open(os.path.join(LIVE, "state", "preds_latest.json")))
    members = set(preds["symbols"])
    nonfinite = [syms[j] for j in range(len(syms)) if not np.isfinite(F[anchor, j])]
    return {
        "value_when_a_symbol_has_no_settlements": "NaN (build_funding_grid leaves the column "
                                                  "unfilled; it is never defaulted to 0.0)",
        "value_when_settlements_exist_but_are_old": "the last settlement <= t, forward-filled "
                                                    "forever (causal searchsorted, funding_panel"
                                                    ".py:172) — a delisted coin keeps its final "
                                                    "rate for as long as the panel runs",
        "symbols_without_settlements_now": prov["symbols_without_settlements"],
        "nonfinite_funding_at_anchor_now": nonfinite,
        "any_of_them_a_member": sorted(set(nonfinite) & members),
        "consumer_of_the_blind_list": {
            "panel_build.py:313": "members with zero settlements -> raise FundingCaliberError",
            "compute_preds.py:143": "members with a non-finite CORRECTED value at the anchor -> "
                                    "raise RuntimeError",
            "where_it_surfaces": "refresh_preds catches both and returns ok=False WITHOUT writing "
                                 "preds_latest.json. The list itself never reaches the file — "
                                 "there is no `blind` field in preds_latest.json.",
            "consequence": "ONE symbol's funding outage suppresses the ENTIRE anchor's signal. "
                           "There is no per-symbol drop path. Consecutive failures walk the "
                           "staleness ladder (HOLD -> DERISK -> FLATTEN), so a single coin's data "
                           "gap is, after enough anchors, a reason the whole book is flattened.",
        },
        "why_this_is_deliberate": "xsr_fund ranks over EVERY column, so a coin dropping out shifts "
                                  "every other coin's rank channel (measured: composite 2.2e-02). "
                                  "Refusing to emit is the documented choice; the availability "
                                  "cost of that choice is what is unquantified.",
    }


def main():
    res = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for name, fn in (("C_exit_and_withheld", item_C), ("D_regime", item_D),
                     ("F_factor_health", item_F), ("G_funding_missing", item_G)):
        try:
            res[name] = fn()
        except Exception as e:
            res[name] = {"AUDIT_ERROR": f"{type(e).__name__}: {e}"}
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
