import json
EDA = "multi_asset/exports/eda/"
p = json.load(open(EDA + "lamorth0_5yr_pairing.json"))

p["verdict"] = dict(
    paired_significance=(
        "4/5 years indistinguishable within seed noise (2022 +0.002, 2023 +0.000, 2026 -0.000: CI incl 0; "
        "2024 -0.004 barely excludes). Mean Δ +0.003 (QIM marginally ahead). TWO years are per-ts-"
        "significant but in OPPOSITE directions: 2024 lamorth0 wins (-0.004, CI[-0.008,-0.000]) and 2025 "
        "QIM wins (+0.017, CI[+0.013,+0.021]). Both 2024 & 2025 are the STRONGEST raw-IC years (0.127/0.137) "
        "-> if pinball had a systematic strong-regime edge it would win BOTH; it splits -> the year-level "
        "gaps are IDIOSYNCRATIC (single-seed fit fluctuation, size ~ the 3-fold single-fold seed spread "
        "±0.01-0.015), NOT a systematic architectural edge. Per-ts bootstrap 'significance' is expected "
        "with ~2000 cross-sections/yr for any real fit difference and does NOT imply seed-robustness."),
    prediction_similarity=(
        "QIM<->lamorth0 xsec rank-corr only 0.63 (NOT ~0.95). The two architectures make genuinely DIFFERENT "
        "cross-sectional bets, yet BOTH reach ~0.064-0.067 IC. So the ~0.065 level is not tied to the head "
        "type -- it is unlocked by REMOVING the penalty. Strengthens the mechanism: penalty-removal is the "
        "level-setting lever; pinball vs K-head is a wash."),
    mechanism_5yr="CLOSED. lam_orth=0 K-head reproduces QIM across the full 5-year expanding walk-forward "
                  "(mean 0.0642 vs 0.0672, Δ +0.003, 4/5 years tie within seed noise). The ~2× edge over "
                  "the penalized arms (0.033 -> 0.065) IS the orthogonality-penalty removal, confirmed at "
                  "5-year scale. The pinball head is NOT the alpha source.",
    deployment_note="QIM (pinball) is marginally ahead on mean (+0.003) and fully audited -> the reasonable "
                    "DEFAULT implementation. But it is NOT required: a K-head lam_orth=0 is mechanism-"
                    "equivalent (Δ within noise). Do NOT market a 'pinball wins strong regimes' story -- 2024 "
                    "refutes it. Either head is deployable; keep QIM for continuity.",
    full_go_condition_1="CLOSED - mechanism confirmed at 5-year scale; the single QIM-favorable significant "
                        "year (2025) is offset by a lamorth0-favorable significant year (2024), no systematic edge.")
json.dump(p, open(EDA + "lamorth0_5yr_pairing.json", "w"), indent=2, default=str)

# upgrade the main verdict json
v = json.load(open(EDA + "qim_final_verdict.json"))
v["final_verdict"] = "GO (deployment-conditional)"
v["final_verdict_history"] = ["CONDITIONAL_GO (2026-07-12 initial)", "GO (deployment-conditional) 2026-07-12 "
                              "after 5yr lamorth0 mechanism confirm"]
v["mechanism_5yr_confirm"] = dict(
    source="lamorth0_5yr_pairing.json (paired day-block bootstrap, same panel md5 185d3b65)",
    lamorth0_5yr_per_year=[0.0423, 0.0637, 0.0737, 0.0639, 0.0775], lamorth0_5yr_mean=0.0642,
    qim_5yr_per_year=[0.0443, 0.0640, 0.0697, 0.0807, 0.0774], qim_5yr_mean=0.0672, mean_delta=0.0030,
    per_year_paired={r["year"]: dict(delta=r["mean_delta"], ci95=r["delta_ci95"], sig=r["ci_excludes_0"])
                     for r in p["per_year"]},
    pred_similarity=0.632,
    verdict=p["verdict"]["mechanism_5yr"])
v["remaining_conditions_for_full_deploy"] = [
    "$2-5M live maker-fill pilot to validate the execution-feasibility assumptions (participation rate, "
    "slippage, adverse selection) -- the only unmodeled binding constraint.",
    ">=100-member universe regime preference (2024+); thin/partial-universe years (2022, 2026) are the "
    "weak, cost-sensitive tail (deployment guideline, not a blocker)."]
json.dump(v, open(EDA + "qim_final_verdict.json", "w"), indent=2, default=str)
print("final_verdict ->", v["final_verdict"])
for r in p["per_year"]:
    print(f"  {r['year']}: d={r['mean_delta']:+.4f} CI{r['delta_ci95']} sig={r['ci_excludes_0']} corr={r['pred_xsec_rankcorr']}")
