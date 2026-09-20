#!/usr/bin/env python3
"""fcf_risk_weights.py — PREREG_fallback_counterfactual_2026-09-20 §4 concentration columns, per arm.
"每臂 … 必须报: 归一化后单名最大权重与有效名数(1/Σw²)的分布(中位、p95)"

THE PRODUCTION NORMALISATION THIS DEVICE REPRODUCES (E-0920-B: definition lines copied in, file:line + code).
exec_mirror/exec_tree_409ea16/live/external_book.py, parse_target:
L365:    w_in = {k: v for k, v in clean.items() if k in uset}
L367:    gross_in = float(sum(abs(v) for v in w_in.values()))
L370:    if gross_in <= 0.0:
L371:        return _err("bad_weights", "no non-zero weight inside the producer's universe")
L403:            # ★ `w` / `symbols` are the IN-UNIVERSE book; `gross_in` is the normaliser (design:
L404:            #   target = w / gross_in x NAV x gross_mult, so tails never dilute the live gross)
⇒ normalised weight of name i at anchor A = w_i / gross_in   (names outside the producer's universe are reported, never targeted)
⇒ single-name max        = max_i |w_i| / gross_in
⇒ effective names        = 1 / Σ_i (w_i / gross_in)²
⇒ amplification to 2×NAV = gross_mult / gross_in            (the prereg §4 "0.38-gross ⇒ ≈5.3×" quantity)
The universe rows are the SAME pinned PIT universe the judge uses, read through the judge's own adapter
(bt_objb_targets.universe_rows), sha-checked against the run config's pin.

E-0920-C (closed population, no benign encoding of "no measurement"):
  The closed population is every anchor of the judge window (n stated). An anchor where NO target file is written — F2's hold
  anchors, and any written-but-empty row — has NO concentration measurement: it is NOT recorded as 0, NOT recorded as 1, and NOT
  averaged in. It is carried in a NAMED subset `no_written_target` with its own count. Every persisted statistic carries its
  effective sample size n_measured, and both the whole-population count and the has-measurement count are printed.
  Two readings are reported side by side:
    written    — only anchors where this arm writes a file (the book it newly commands)
    effective  — the book actually held: at a hold anchor the previous written target is carried (the executor's on_unavailable
                 = hold). Anchors before the first written target of the window have no effective book either and stay named.

usage: fcf_risk_weights.py <run_config.json>
"""
import calendar, hashlib, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_objb_targets as OT

OUT = "/workspace/fallback_cf_2026-09-20"
H4 = 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def ts(x): return calendar.timegm(time.strptime(x, "%Y-%m-%dT%H:%M:%SZ"))    # the judge's own conversion (bt_driver_lib.ts)


def stat(v, n_pop, label):
    """every persisted statistic carries its effective sample size and the population it was taken from (E-0920-C)"""
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if len(v) == 0:
        return {"n_population": int(n_pop), "n_measured": 0, "median": None, "p95": None, "mean": None, "min": None, "max": None,
                "coverage": 0.0, "population": label, "note": "no measurement in this cell — NOT encoded as a value"}
    return {"n_population": int(n_pop), "n_measured": int(len(v)), "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
            "mean": float(v.mean()), "min": float(v.min()), "max": float(v.max()), "coverage": float(len(v) / n_pop) if n_pop else None,
            "population": label}


def main():
    CFG = json.load(open(sys.argv[1]))
    for x in sys.argv[2:]:                      # extra frozen configs may only ADD runs; pins/window/production config must match
        E = json.load(open(x))
        assert E["pins"] == CFG["pins"] and E["window"] == CFG["window"] and E["current_production_config"] == CFG["current_production_config"]
        CFG["runs"] = CFG["runs"] + E["runs"]
    anchors = np.arange(ts(CFG["window"]["first_anchor"]), ts(CFG["window"]["last_anchor"]) + 1, H4, dtype=np.int64)
    assert len(anchors) == CFG["window"]["n_anchors"], (len(anchors), CFG["window"]["n_anchors"])
    PM = np.load(CFG["pins"]["price_full_meta"]["path"], allow_pickle=True); SY = [str(s) for s in PM["symbols"]]
    frs = ts(CFG["window"]["full_recipe_start"])
    # venue tradability, the JUDGE's own pinned definition (RUN_CONFIG current_production_config.venue_tradable:
    # "tradability_v1 state_W24H == 2 at A"); used for the staleness column, never to change a weight
    TRZ = np.load(CFG["pins"]["tradability"]["path"], allow_pickle=True)
    assert [str(s) for s in TRZ["symbols"]] == SY, "tradability symbol axis"
    TRS = np.asarray(TRZ["state_W24H"]); tr_row = {int(t): i for i, t in enumerate(TRZ["anchor_ts"].astype(np.int64))}
    # the archived (F0) kinds define the fallback subsample, shared by every arm
    T0 = OT.load_targets(CFG["runs"][0]["targets"]["sources"], reading="scaled", arm="A0", n_sym=len(SY))
    _, _, kind0, _ = OT.book_for_window(T0, anchors, len(SY))
    assert CFG["runs"][0]["arm"] == "OBJB_F0", CFG["runs"][0]["arm"]
    fb = kind0 == 1
    doc = {"device": "fcf_risk_weights.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": "docs/PREREG_fallback_counterfactual_2026-09-20.md §4 concentration columns",
           "run_config": {"path": os.path.abspath(sys.argv[1]), "sha256": sha(sys.argv[1])},
           "gross_mult": float(CFG["current_production_config"]["gross_mult"]),
           "window": {"first_anchor": CFG["window"]["first_anchor"], "last_anchor": CFG["window"]["last_anchor"],
                      "n_anchors": int(len(anchors)), "full_recipe_start": CFG["window"]["full_recipe_start"]},
           "fallback_subsample": {"definition": "anchors where the ARCHIVED (F0) reading wrote the king file = the preflight failed",
                                  "n": int(fb.sum()), "n_in_full_recipe_window": int((fb & (anchors >= frs)).sum())},
           "utc": iso(time.time()), "arms": {}}
    GM = doc["gross_mult"]

    for r in CFG["runs"]:
        arm = r["arm"].replace("OBJB_", "")
        T = OT.load_targets(r["targets"]["sources"], reading="scaled", arm=r["targets"]["arm"], n_sym=len(SY))
        W, fresh, kind, cnt = OT.book_for_window(T, anchors, len(SY))
        PIT = OT.universe_rows(r["targets"]["universe"]["path"], r["targets"]["universe"]["sha256"], anchors, SY)
        n = len(anchors)
        mx = np.full(n, np.nan); eff = np.full(n, np.nan); amp = np.full(n, np.nan); gin = np.full(n, np.nan)
        emx = np.full(n, np.nan); eeff = np.full(n, np.nan); eamp = np.full(n, np.nan)
        unt = np.full(n, np.nan); eunt = np.full(n, np.nan); age = np.full(n, np.nan)
        no_written = []; no_effective = []
        last = None; last_w = None; last_k = None
        for k in range(n):
            trad = TRS[tr_row[int(anchors[k])]]
            if fresh[k]:
                w = W[k] * PIT[k]                              # the in-universe book: production targets w_in only
                g = float(np.abs(w).sum())
                if g > 0.0:
                    wn = w / g; nz = wn[wn != 0.0]
                    mx[k] = float(np.abs(nz).max()); eff[k] = float(1.0 / np.square(nz).sum()); amp[k] = GM / g; gin[k] = g
                    unt[k] = float(np.abs(wn[trad != 2]).sum())
                    last = (mx[k], eff[k], amp[k]); last_w = wn; last_k = k
                else:
                    no_written.append(int(anchors[k]))         # written row with no in-universe weight: the executor refuses it -> HOLD
            else:
                no_written.append(int(anchors[k]))
            if last is None: no_effective.append(int(anchors[k]))
            else:
                emx[k], eeff[k], eamp[k] = last
                eunt[k] = float(np.abs(last_w[trad != 2]).sum())   # the CARRIED book measured against THIS anchor's tradability
                age[k] = float(k - last_k)                         # anchors since the book was last refreshed (0 = refreshed here)
        cells = {"whole_window": np.ones(n, bool), "full_recipe_window": anchors >= frs,
                 "fallback_subsample": fb, "fallback_subsample_full_recipe": fb & (anchors >= frs),
                 "non_fallback_anchors": ~fb}
        A = {}
        for cname, m in cells.items():
            npop = int(m.sum())
            A[cname] = {
                "written": {"single_name_max_weight": stat(mx[m], npop, f"{cname}/written"),
                            "effective_names_1_over_sumw2": stat(eff[m], npop, f"{cname}/written"),
                            "amplification_gross_mult_over_gross_in": stat(amp[m], npop, f"{cname}/written"),
                            "gross_in": stat(gin[m], npop, f"{cname}/written"),
                            "n_no_written_target": int(np.isnan(mx[m]).sum())},
                "effective_book_held": {"single_name_max_weight": stat(emx[m], npop, f"{cname}/effective"),
                                        "effective_names_1_over_sumw2": stat(eeff[m], npop, f"{cname}/effective"),
                                        "amplification_gross_mult_over_gross_in": stat(eamp[m], npop, f"{cname}/effective"),
                                        "untradable_weight_share": stat(eunt[m], npop, f"{cname}/effective"),
                                        "book_age_in_anchors_since_last_refresh": stat(age[m], npop, f"{cname}/effective"),
                                        "n_no_effective_book": int(np.isnan(emx[m]).sum())}}
            A[cname]["written"]["untradable_weight_share"] = stat(unt[m], npop, f"{cname}/written")
        def hold_runs(sel):
            """consecutive-hold run lengths inside `sel`: how long this arm goes without rebalancing.
            A run is counted with its START anchor, and its length is the true unbroken length (runs are not cut at the cell edge —
            cutting them would understate the longest hold, which is exactly the risk being measured)."""
            out = []; cur = 0; st = None
            for k in range(n):
                if not fresh[k] or np.isnan(mx[k]):
                    if cur == 0: st = k
                    cur += 1
                elif cur:
                    if sel[st]: out.append(cur)
                    cur = 0
            if cur and sel[st]: out.append(cur)
            return out
        allsel = np.ones(n, bool); frsel = anchors >= frs
        HR = {}
        for lab, sel in (("whole_window", allsel), ("full_recipe_window", frsel)):
            runs_ = hold_runs(sel)
            HR[lab] = {"n_runs": len(runs_), "longest_anchors": int(max(runs_)) if runs_ else 0,
                       "longest_hours": (int(max(runs_)) * 4 if runs_ else 0), "longest_days": round(int(max(runs_)) * 4 / 24, 1) if runs_ else 0,
                       "median_anchors": float(np.median(runs_)) if runs_ else None,
                       "p95_anchors": float(np.percentile(runs_, 95)) if runs_ else None, "total_hold_anchors": int(sum(runs_))}
        HR["note"] = ("a run = consecutive anchors at which this arm writes no usable target, so the executor carries the previous book unchanged; "
                      "0 runs means the arm rebalances at every anchor. A run is attributed to the cell of its START anchor and reported at its "
                      "true unbroken length, never truncated at the cell edge.")
        doc["arms"][arm] = {"tag": r["tag"], "counts_in_window": cnt, "cells": A, "consecutive_hold_runs": HR,
                            "named_no_measurement": {"no_written_target": {"n": len(no_written), "first": [iso(a) for a in no_written[:3]],
                                                                          "last": [iso(a) for a in no_written[-3:]],
                                                                          "reason": "no file is written at this anchor (hold), or the written row has no in-universe "
                                                                                    "weight; there is NO concentration measurement — not 0, not 1 (E-0920-C)"},
                                                     "no_effective_book": {"n": len(no_effective), "anchors": [iso(a) for a in no_effective[:5]],
                                                                           "reason": "before this arm's first written target of the window there is no book to measure"}}}
        print(f"{arm}: written max-w median {A['whole_window']['written']['single_name_max_weight']['median']}"
              f" p95 {A['whole_window']['written']['single_name_max_weight']['p95']}"
              f" (n_measured {A['whole_window']['written']['single_name_max_weight']['n_measured']}/{n})", flush=True)

    # the prereg §4 gate on F1: "若 F1 的单名最大权重 p95 超过 F0 的 1.5 倍 … 只能标 (C) 不可判"
    if "F0" in doc["arms"] and "F1" in doc["arms"]:
        for cell in ("whole_window", "full_recipe_window", "fallback_subsample", "fallback_subsample_full_recipe"):
            f0 = doc["arms"]["F0"]["cells"][cell]["written"]["single_name_max_weight"]["p95"]
            f1 = doc["arms"]["F1"]["cells"][cell]["written"]["single_name_max_weight"]["p95"]
            doc.setdefault("prereg_s4_F1_concentration_gate", {})[cell] = {
                "F0_p95": f0, "F1_p95": f1, "ratio": (f1 / f0 if f0 else None), "threshold": 1.5,
                "breached": (bool(f1 > 1.5 * f0) if (f0 and f1) else None),
                "rule": "PREREG §4: if F1's single-name max weight p95 exceeds 1.5x F0's, F1 can only be labelled (C) undecidable "
                        "even if its return is better"}
    p = f"{OUT}/receipts/FCF_RISK_WEIGHTS.json"
    json.dump(doc, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
    print("FCF_RISK_WEIGHTS VERDICT=PASS arms=" + ",".join(doc["arms"]) + " receipt_sha256=" + sha(p), flush=True)


if __name__ == "__main__":
    main()
