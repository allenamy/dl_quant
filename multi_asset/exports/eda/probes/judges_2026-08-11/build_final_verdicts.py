import json
EDA = "multi_asset/exports/eda/"
g = json.load(open(EDA + "arm_s2_seeds.json"))
g["verdict"] = ("G2 PASS - S2 increment is SEED-ROBUST. 3 seeds increment [.0285/.0389/.0332] all positive, "
                "CoV 12.7%; raw IC [.062/.073/.065] CoV 7%; all 32ch/H24 (config-verified, byte-consistent panel "
                "1c8ad451, not stale). Combined with the 5yr regime-robustness (all 5 years +), the king-orthogonal "
                "increment is confirmed real + regime-robust + seed-robust.")
json.dump(g, open(EDA + "s2_g2_seeds.json", "w"), indent=2, default=str)

d = json.load(open(EDA + "book_assembly_4leg_raw.json"))
d["verdict"] = dict(
    ruling="S2 FORMALLY INTO BOOK (4-leg). Adding S2 improves the 3-leg book on ALL metrics.",
    three_vs_four="3-leg equal-risk Sh 6.60 / worstMo -2.84 / 2026 Sh 5.91 -> 4-leg (S2 w0.10) Sh 7.10 / worstMo "
                  "-2.42 / 2026 Sh 6.61. Monotone improvement in S2 weight (Sh 6.60->6.87->7.10->7.27 at w "
                  "0/.05/.10/.15; worstMo -2.84->-2.20; worst-year 2026H1 lifts every step).",
    diversification="S2<->king corr 0.224 (24h vs 4h), S2<->SIZE 0.002 (near-zero) - S2 is a genuine 4th "
                    "diversifier; in the FULL book its low corr to ALL legs makes it unambiguously additive "
                    "(unlike the pairwise king-blend which was directional-not-significant - the multi-leg "
                    "context is what realizes the diversification value).",
    worst_year_protection="CONFIRMED - 2026H1 (the king's weak book-year) per-year Sharpe rises 5.91->6.61 "
                          "(w0.10) ->6.83 (w0.15); worst-month floor lifts -2.84->-2.42. S2 protects the weak year.",
    recommended_weights="S2 risk budget ~0.10 (balanced default; team-lead prior + modest standalone S2 Sharpe "
                        "4.16 argues against over-tilting to a single 24h DL factor). Keep the 3 core legs at the "
                        "book_assembly v2 proportions (DL-king 0.35-0.40, funding/SIZE ~0.28 each) scaled to 0.90. "
                        "Sensitivity w0.05-0.15 ALL improve; 0.10 base, 0.15 aggressive upper bound. inverse-vol "
                        "(Sh 5.89) UNDER-weights the king -> not recommended; use risk-budget with the king-tilt.",
    caveat="leg Sharpes are signal-level (frictionless-inflated, esp the fast king); the DECISION rests on the "
           "corr structure + worst-year protection + monotone book improvement, which are caliber-robust. S2 is a "
           "DIVERSIFICATION sleeve (real regime+seed-robust increment, protects 2022/2026), not a Sharpe headline.")
json.dump(d, open(EDA + "book_assembly_4leg.json", "w"), indent=2, default=str)
print("saved; s2<->king", d["s2_king_corr"], "s2<->size", d["s2_size_corr"])
