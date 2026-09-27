#!/usr/bin/env python3
"""s1_rule_check.py — alloc's independent, mechanical re-application of the frozen S1 rule to the judge receipts.
Written and committed 2026-09-27 ~05:1xZ, while the S1 network executor was still in CHECKSUM (no build / fit / judge receipt existed).
Rule: docs/DECISION_RULE_nonfunding_sources_2026-09-27.md §1 (lead, 54866038b) via AMENDMENT_L2_NC_population_2026-09-27 §3 (2838b830d);
definitional choices adopted by the lead: main verdict only for the SAME model detected in both seeds and both segments.
Order is fixed: (1) resolution  (2) leakage VOID gates  (3) main. A later stage is not read when an earlier one stops.
It recomputes every decision from the per-cell numbers in the receipts and compares with the judge's own VERDICT / eligible / passing
fields; any disagreement prints DISAGREE and exits 2 (the judge's verdict is then not reported as the result).
usage: python3 s1_rule_check.py RECEIPT_L2N_judge_RESOLUTION.json [RECEIPT_L2N_judge_MAIN.json]
"""
import json, sys

SEEDS = ("42", "2027"); MODELS = ("R", "L"); SEGS = ("pre2026", "2026")
TH_IC = 0.015          # lead §1 main: in-population rank IC >= 0.015
TH_SD = 0.02           # lead §1 collapse guard: sd(yhat)/sd(y) >= 0.02


def lo(c): return c["ci95"][0]


def main():
    R = json.load(open(sys.argv[1])); out = {"stage1_resolution": {}, "agree": True}
    elig = []
    for m in MODELS:
        det = {f"s{s}|{k}": (R["cells"][f"s{s}|{m}|PLANT"][k] is not None and lo(R["cells"][f"s{s}|{m}|PLANT"][k]) > 0) for s in SEEDS for k in SEGS}
        null_det = {f"s{s}|{k}": (R["cells"][f"s{s}|{m}|NULL"][k] is not None and lo(R["cells"][f"s{s}|{m}|NULL"][k]) > 0) for s in SEEDS for k in SEGS}
        out["stage1_resolution"][m] = {"plant_detected": det, "null_detected(expect all False)": null_det}
        if all(det.values()): elig.append(m)
    out["eligible_models"] = elig
    if sorted(elig) != sorted(R["eligible_models"]) or (R["VERDICT"] == "RESOLUTION_OK") != bool(elig):
        out["agree"] = False; out["DISAGREE"] = f"resolution: recomputed {elig} vs judge {R['eligible_models']} / {R['VERDICT']}"
    if not elig:
        out["RESULT"] = "STOP at stage 1: RESOLUTION_FAIL (no model detects the planted IC 0.015 in both segments for both seeds)"
        return out
    if len(sys.argv) < 3:
        out["RESULT"] = "stage 1 passed; MAIN receipt not given"; return out
    M = json.load(open(sys.argv[2]))
    void = []
    for s in SEEDS:
        for m in MODELS:
            L = M["cells"][f"s{s}|{m}"]["leakage"]; spec = {int(h): v for h, v in L["spectrum"].items()}
            peak = max([h for h in (0, 1, 2, 3) if h in spec], key=lambda h: abs(spec[h]))
            sf_ok = L["shuffle_future_IC"] <= L["shuffle_future_null_p97.5"]
            if peak != 0 or not sf_ok: void.append(f"s{s}|{m}")
            out.setdefault("stage2_leakage", {})[f"s{s}|{m}"] = {"forward_peak_h": peak, "shuffle_future_ok": sf_ok}
    judge_void = M["VERDICT"] == "VOID"
    if bool(void) != judge_void:
        out["agree"] = False; out["DISAGREE"] = f"leakage: recomputed void {void} vs judge {M['VERDICT']}"
    if void:
        out["RESULT"] = f"STOP at stage 2: VOID (leakage gate failed in {void})"; return out
    passing = []
    for m in elig:
        ok = True; det = {}
        for s in SEEDS:
            A = M["cells"][f"s{s}|{m}"]["A"]; sd = M["cells"][f"s{s}|{m}"]["sd_ratio"]
            for k in SEGS:
                c = A[k]; det[f"s{s}|{k}"] = None if c is None else {"IC": c["IC"], "lo": lo(c), "ok": c["IC"] >= TH_IC and lo(c) > 0}
                ok &= c is not None and c["IC"] >= TH_IC and lo(c) > 0
            same_sign = A["pre2026"] is not None and A["2026"] is not None and (A["pre2026"]["IC"] > 0) == (A["2026"]["IC"] > 0)
            ok &= same_sign and sd >= TH_SD
            det[f"s{s}|same_sign"] = same_sign; det[f"s{s}|sd_ratio"] = sd
        out.setdefault("stage3_main", {})[m] = det
        if ok: passing.append(m)
    out["passing_models"] = passing
    if sorted(passing) != sorted(M.get("passing_models", [])) or M["VERDICT"].startswith("PASS") != bool(passing):
        out["agree"] = False; out["DISAGREE"] = f"main: recomputed {passing} vs judge {M.get('passing_models')} / {M['VERDICT']}"
    out["RESULT"] = ("PASS at stage 3 (next = lead writes the book-layer prereg; same-population beta-matched replacement, "
                     "no one-sided short reduction, risk endpoints)" if passing else "FAIL at stage 3 (no eligible model meets IC >= 0.015, lower > 0, "
                     "same sign, both segments, both seeds)")
    return out


if __name__ == "__main__":
    o = main(); print(json.dumps(o, indent=1)); sys.exit(0 if o["agree"] else 2)
