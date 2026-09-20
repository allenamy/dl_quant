#!/usr/bin/env python3
"""fcf_semantics_control.py — POSITIVE CONTROL on the W_ENTRY / W_CARRY split, computed from the receipt alone.

THE GAP THIS CLOSES (raised by p2-aggregation-fix, who owns the aggregator). My §6 reports "46 of 50 assertion cells have
W_ENTRY == W_CARRY". A production receipt on its own **cannot distinguish**:
    (a) the semantics flag is wired and this data simply has few pre-base halts, from
    (b) the semantics flag was never wired, in which case the two readings are the same computation and agree everywhere.
Today 4 cells differ, so (b) is excluded by incidence. But an arm set that came back with ZERO differing cells would look
identical under (a) and (b) — and that is exactly when the wrong conclusion is cheap. Structurally the same defect as my own
demotion drill reporting `checked=284` twice because `--without-arm` was never wired.

THE CONTROL (p2's construction, no device change and no rerun needed). `day_stop_events_in_scope` counts every flatten under
W_CARRY but only those at or after the base under W_ENTRY, so per path
    pre_base_flattens = W_CARRY.day_stop_events_in_scope - W_ENTRY.day_stop_events_in_scope
and a cell MUST differ **iff** H == "never" and that difference is > 0 for at least one path. This device computes the PREDICTED
differing set and asserts it equals the OBSERVED differing set recorded in `assertions[].W_ENTRY_equals_W_CARRY`.

HOW TO READ THE THREE OUTCOMES, stated before the numbers:
  predicted == observed, both non-empty -> the flag is wired AND this data exercises the split. Positive control PASSES.
  predicted non-empty, observed empty   -> the flag is NOT wired. REFUSE.
  predicted == observed == empty        -> the flag's wiring is UNTESTED by this data. That is a fact to PRINT, not a green;
                                           the device says so explicitly rather than reporting a pass.
usage: fcf_semantics_control.py <P2_receipt.json> <out.json>
"""
import hashlib, json, os, sys, time

OUT = "/workspace/fallback_cf_2026-09-20"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    SRC, OUTP = sys.argv[1], sys.argv[2]
    P2 = json.load(open(SRC))
    doc = {"device": "fcf_semantics_control.py", "self_sha256": sha(os.path.abspath(__file__)),
           "source": {"path": SRC, "sha256": sha(SRC)},
           "control": "p2-aggregation-fix's receipt-only positive control on the W_ENTRY / W_CARRY split",
           "rule": "a cell MUST differ iff H == 'never' and some path has W_CARRY.day_stop_events_in_scope > W_ENTRY's",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": [], "cells": []}
    FAILS = []

    def check(n, ok, d=None):
        doc["checks"].append(dict(check=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:280] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    # the two sides key the base differently: `assertions[].base` is a bare timestamp, `runs[].bases` is a label that ENDS in
    # that timestamp. Normalise to the timestamp. (The first run of this device REFUSED on exactly this — counts matched 4 vs 4
    # while the sets did not — which is the comparison doing its job rather than a tolerance hiding it.)
    def base_ts(x): return x.split("@")[-1].strip()

    observed = {}
    for a in P2["assertions"]:
        observed[(a["run"], base_ts(a["base"]), str(a["H"]))] = not a["W_ENTRY_equals_W_CARRY"]

    predicted = {}; prebase_by_cell = {}
    consistency = []
    for nm, r in P2["runs"].items():
        for B, bd in r["bases"].items():
            per_H = {}
            for H, hd in bd.items():
                we = {p["seed"]: p["day_stop_events_in_scope"] for p in hd["W_ENTRY"]["per_path"]}
                wc = {p["seed"]: p["day_stop_events_in_scope"] for p in hd["W_CARRY"]["per_path"]}
                pre = {s: wc[s] - we[s] for s in we if s in wc}
                per_H[H] = pre
                n_pos = sum(1 for v in pre.values() if v > 0)
                predicted[(nm, base_ts(B), str(H))] = (str(H) == "never") and n_pos > 0
                prebase_by_cell[(nm, base_ts(B), str(H))] = {"n_paths_with_pre_base_flattens": n_pos,
                                                    "total_pre_base_flattens": sum(v for v in pre.values() if v > 0)}
            # the pre-base flatten count is a property of the BASE, not of the resume rule: it must agree across H
            base_sets = {H: tuple(sorted(v.items())) for H, v in per_H.items()}
            consistency.append((nm, B, len(set(base_sets.values())) == 1))
    check("pre_base_flatten_count_is_the_same_under_every_H_for_a_given_base",
          all(ok for _, _, ok in consistency), dict(n_base_cells=len(consistency),
                                                    n_inconsistent=sum(1 for _, _, ok in consistency if not ok)))

    keys = sorted(set(observed) | set(predicted))
    pred_set = sorted(k for k in keys if predicted.get(k))
    obs_set = sorted(k for k in keys if observed.get(k))
    for k in keys:
        doc["cells"].append({"run": k[0].split("arm ")[-1].rstrip(")"), "base": k[1], "H": k[2],
                             "predicted_to_differ": bool(predicted.get(k)), "observed_to_differ": bool(observed.get(k)),
                             **prebase_by_cell.get(k, {})})
    check("predicted_differing_set_equals_observed_differing_set", pred_set == obs_set,
          dict(n_predicted=len(pred_set), n_observed=len(obs_set),
               predicted_not_observed=[f"{a.split('arm ')[-1].rstrip(')')}|{b}|H={h}" for a, b, h in sorted(set(pred_set) - set(obs_set))][:5],
               observed_not_predicted=[f"{a.split('arm ')[-1].rstrip(')')}|{b}|H={h}" for a, b, h in sorted(set(obs_set) - set(pred_set))][:5]))

    if pred_set:
        check("the_split_is_EXERCISED_by_this_data_so_the_flag_is_demonstrably_wired", True,
              dict(n_cells_that_differ=len(pred_set),
                   cells=[f"{a.split('arm ')[-1].rstrip(')')}|H={h}" for a, b, h in pred_set][:8],
                   meaning="a never-wired flag would make the two semantics identical everywhere; they are not"))
    else:
        check("the_split_is_EXERCISED_by_this_data", False,
              dict(finding="UNTESTED: no cell is predicted to differ, so this data cannot tell a wired flag from an unwired one. "
                           "This is printed as a fact, NOT reported as a pass."))

    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_SEMANTICS_CONTROL VERDICT={doc['VERDICT']} checks={len(doc['checks'])} "
          f"predicted={len(pred_set)} observed={len(obs_set)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
