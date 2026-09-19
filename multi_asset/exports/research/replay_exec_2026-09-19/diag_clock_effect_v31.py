#!/usr/bin/env python3
"""replay_exec 2026-09-19 · diagnostic (not a verdict): the before / after effect of withdrawing v3's readback clamp (review 5b R5B-03).

  before = exec_sim v3 (fea90ee9): fills of anchor A moved to 1 s before A's own live readback (1.57% / 0.32% of scheduled notional),
           judged earlier under the pre-revision gate 31650235; its receipts carry per-window MEANS only (no per-seed path artifacts), so
           gate v2 cannot verify them — here they are only fed through gate v2's pure judge function, as numbers.
  after  = exec_sim v3.1 (fills at their own simulated time), means RECOMPUTED from the per-seed path artifacts by gate v2's provenance
           check (the same numbers gate v2 judges).
Both sides go through v1b_gate.judge_v1b on the same live population; the output lists every W / T item side by side.
usage: diag_clock_effect_v31.py <out.json>
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1_gate as V1
import v1b_gate as G
import exec_sim as ES

PAIRS = {"CAL": ("SIM_v3_live_CAL_continuous_20260826_20260918.json", "SIM_v31_live_CAL_continuous_20260826_20260918.json", "CAL"),
         "HIST_DIAG": ("SIM_v3_live_HOLDOUT_20260911_20260918.json", "SIM_v31_live_HIST_DIAG_20260911_20260918.json", "HIST_DIAG"),
         "HIST_DIAG_CONTINUOUS": ("SIM_v3_live_CAL_continuous_20260826_20260918.json", "SIM_v31_live_CAL_continuous_20260826_20260918.json", "HIST_DIAG_CONTINUOUS")}


def summary(items):
    out = {}
    for k, it in items.items():
        if k.startswith("W_"):
            out[k] = {x: it.get(x) for x in ("mean_abs_err_over_scale", "p90_err_over_tol", "max_err_over_tol", "n_windows_outside_tol", "pass")}
        elif k.startswith("T_"):
            out[k] = {x: it.get(x) for x in ("ratio", "total_diff", "pass")}
        else:
            out[k] = {"pass": it.get("pass")}
    return out


def main():
    out_p = sys.argv[1]
    M = ES.WideMirror(L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    inputs = {k: G.APPROVED_HISTORICAL[k][0] for k in ("manifest", "live_g", "transfers")}
    M.manifest = json.load(open(inputs["manifest"]))
    res = {}
    for lab, (before_f, after_f, gate_label) in PAIRS.items():
        live_w = G.population(gate_label)
        lt, _ = V1.live_turnover(M, live_w)
        pop = {L.nominal(w["t0"]) for w in live_w}
        b = [w for w in json.load(open(os.path.join(HERE, before_f)))["windows"] if L.nominal(w["t0"]) in pop]
        ap = os.path.join(HERE, after_f)
        viol, rec = G.check_provenance(json.load(open(ap)), gate_label, ap, M, inputs, check_calibration=False)
        a = [w for w in rec["mean"] if L.nominal(w["t0"]) in pop] if rec.get("mean") else []
        vb, ib = G.judge_v1b(b, live_w, lt, label=gate_label, declared=G.population(gate_label))
        va, ia = G.judge_v1b(a, live_w, lt, label=gate_label, declared=G.population(gate_label)) if a else (None, {})
        res[lab] = {"before_v3_clamp": {"judge_verdict": vb, "items": summary(ib), "note": "pure-judge numbers only; unverifiable under gate v2"},
                    "after_v31": {"judge_verdict": va, "items": summary(ia), "provenance_violations_excluding_calibration": viol}}
        print(lab, "before", vb, "after", va, {k: (round(ib[k].get("p90_err_over_tol") or 0, 3), round(ia[k].get("p90_err_over_tol") or 0, 3))
                                              for k in ib if k.startswith("W_")})
    doc = {"device": "diag_clock_effect_v31.py", "device_sha256": L.sha_file(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "v1b_gate_sha256": L.sha_file(os.path.join(HERE, "v1b_gate.py")),
           "note": "diagnostic, not a verdict: the verdicts of record are the V1B2_GATE_v31_* receipts", "pairs": res}
    with open(out_p + ".part", "w") as fh:
        json.dump(doc, fh, indent=1, default=str)
    os.replace(out_p + ".part", out_p)


if __name__ == "__main__":
    main()
