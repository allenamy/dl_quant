import json
EDA = "multi_asset/exports/eda/"
s = json.load(open(EDA + "arm_s2_5yr_score.json"))
v = json.load(open(EDA + "arm_s2_verdict.json"))

v["v3_final_5yr"] = dict(
    ruling="QUALIFIED PASS — S2 (32ch) qualifies as a SMALL-WEIGHT (~0.1) SLOW DIVERSIFICATION SLEEVE; "
           "formal add pending the seed battery. Value = real regime-robust increment + worst-year "
           "protection, NOT a headline Sharpe lift.",
    increment=dict(pooled=s["incremental_ic_pooled"], ci95=s["incremental_ci95"],
                   per_year={x["year"]: x["incremental_ic"] for x in s["per_year"]},
                   sign_consistent=s["sign_consistent"],
                   note="+0.0289 pooled (CI[.023,.034]); ALL 5 YEARS POSITIVE (2022 +.018 / 2023 +.037 / 2024 "
                        "+.034 / 2025 +.020 / 2026 +.042); regime-robust. ★ 2026 has the LARGEST increment "
                        "(+.042) = the king's weak book-year → diversification confirmed at the increment level."),
    pred_corr=dict(pooled=s["pred_corr_pooled"], note="0.31 < 0.7."),
    book_margin=dict(
        improve_rule_all_tiers=all(s["book_margin"][c]["improve_rule"] for c in s["book_margin"]),
        best_blend={c: dict(w=s["book_margin"][c]["best_blend"]["w"], impr=s["book_margin"][c]["best_blend"]["impr"],
                            sig=s["book_margin"][c]["best_blend"]["sig"]) for c in s["book_margin"]},
        per_year_king_vs_comb_taker5=s["book_margin"]["5.0"]["per_year_king_vs_comb"],
        note="★ improve-rule Ss>ρ·Sk holds at ALL cost tiers (ρ 0.22; taker Ss/Sk 0.42). Best-blend Sharpe "
             "improvement +0.11 (maker w0.1) / +0.19 (taker w0.2) — POSITIVE at all tiers but NOT bootstrap-"
             "significant even at 5yr (noisy Sharpe-diff estimator). ★ BUT per-year: combined ≥ king ~every "
             "year (no year worse) AND LIFTS THE KING'S WORST BOOK-YEAR — at taker5 the king's worst year 2026 "
             "(+5.26) → combined +5.75, raising the worst-year floor 5.26→5.39. Genuine worst-year/downside "
             "protection = the diversification value the pooled-Sharpe bootstrap under-credits (same profile as "
             "the funding/SIZE legs in the 3-leg book: weaker standalone, low-corr, worst-year-protecting)."),
    checks=dict(panel_md5=s["panel_md5"], ts_aligned_king=s["ts_aligned_king"], nch=s["nch"],
                clean_24h="CL 24h grid; king coverage full per year (n=365/365/366/365/180)",
                fold_2022_sigma_health="2022 short-train (2021-only) fold: increment +0.0182 POSITIVE, not "
                                       "degenerate → σ healthy",
                metrics="32ch (metrics dropped, input axis closed — v2)"),
    gates_summary="(a) PASS strong (regime-robust increment) / (b) PASS / (d) PASS (dyn 0.895 from 3-fold) / "
                  "(e) PASS (slow cheap sleeve) / (c) DIRECTIONAL PASS: improve-rule all tiers + worst-year "
                  "protection + no-year-worse, though pooled Sharpe-lift not bootstrap-sig.",
    decision=("QUALIFIED PASS → add S2 as a ~0.1-weight slow 24h sleeve to the book (4-leg: funding / DL-king / "
              "SIZE / S2-24h), FORMAL after the seed battery (seed43/44) confirms seed-robustness. The honest "
              "framing: S2 is a DIVERSIFICATION / worst-year-protection sleeve (real regime-robust increment, "
              "protects the king's weak 2022/2026), NOT a headline Sharpe lifter (the marginal lift is positive "
              "but not statistically confirmed). Once seeds pass, 0C recomputes the 4-leg risk weights."),
    caveats=["marginal book Sharpe-lift POSITIVE (+0.11-0.19) but NOT bootstrap-significant even at 5yr — the "
             "book case rests on worst-year protection + improve-rule, not a significant pooled lift.",
             "king paper-Sharpe still frequency-inflated; the improve-rule (ratio-based) + worst-year metric are "
             "the caliber-robust evidence.",
             "seed battery (seed43/44) still running — formal add awaits seed-robustness confirmation."])
json.dump(v, open(EDA + "arm_s2_verdict.json", "w"), indent=2, default=str)
print("v3 ruling:", v["v3_final_5yr"]["ruling"][:90])
