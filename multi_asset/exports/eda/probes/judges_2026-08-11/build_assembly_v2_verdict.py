import json
E = "multi_asset/exports/eda/"
v2 = json.load(open(E + "book_assembly_v2_raw.json"))
main = json.load(open(E + "book_assembly.json"))

v2["judgment"] = dict(
    diversification=dict(
        verdict="EXCELLENT (upgraded from v1 'PASS')",
        pairwise_daily_corr_multiyear=dict(funding_dl=0.075, funding_size=-0.031, dl_size=-0.152),
        detail=("on the full multi-year window all three pairs are near-zero-to-NEGATIVE (v1's dl<->size "
                "+0.262 was a 123d artifact; full history = -0.152 because DL's strong 2024/25 are SIZE's "
                "weak years). Leg LEADERSHIP ROTATES across regimes -> genuine complementary exposure."),
        leadership_rotation=dict(
            y2022="SIZE +1.69 carries weak DL(+0.34)/funding(-0.44) post-FTX chop",
            y2024="DL +12.36 carries weak funding(-1.57)/SIZE(-0.20)",
            y2025="DL +12.43 & funding +2.9 carry weak SIZE(-2.09)",
            y2026="funding +1.69 & SIZE +1.95 carry weak DL(-0.11) -- VALIDATES the narrative")),
    narrative_2026=("★ KEY TEST PASSED: in 2026H1 DL is flat-negative (per-year Sharpe -0.11, worst full-"
                    "year for DL) but the equal-risk portfolio still returns per-year Sharpe +2.07, carried "
                    "entirely by funding/SIZE. The 'weak DL year covered by funding/SIZE' thesis is confirmed "
                    "on out-of-window data."),
    portfolio=dict(
        equal_risk=v2["portfolios"]["equal_risk"],
        note=("equal-risk (=v1 inverse-vol) Sharpe 5.28 over 2022-08..2026-06. Lower than DL-alone frictionless "
              "8.21, but DL is capacity-limited (~5.5 deployable @ $25M per exec-feasibility) AND near-zero in "
              "2026; the portfolio trades peak Sharpe for regime-robustness + weak-year coverage. All FULL years "
              "positive (2023 +5.35, 2024 +6.6, 2025 +8.29, 2026 +2.07); worst-month/-year sit in the PARTIAL "
              "2022 tail (Sep-Dec post-FTX, all legs weak).")),
    weight_recommendation=dict(
        recommended_dl_risk_budget="0.35-0.40",
        update_vs_v1=("REFINES v1. v1 (123d, DL-strong 2025 only) cautioned DL<=0.25-0.35 fearing regime-overfit. "
                      "The multi-year window RESOLVES that fear: DL weight up to 0.4 is robustly best -- portfolio "
                      "Sharpe RISES with DL weight (0.2->3.19, 0.3->4.78, 0.4->6.16) AND worst-year improves "
                      "(-5.68 -> -4.76 -> -3.84) AND 2026 stays protected (+2.48/+2.20/+1.78) because funding/SIZE "
                      "keep 30% each at wdl=0.4. So the real cap on DL weight is NOT regime-overfit but (a) DL "
                      "capacity limits (~$10-25M) and (b) preserving weak-year (2026) coverage."),
        recommendation=("DL risk-budget ~0.35-0.40, funding/SIZE ~0.30-0.325 each. Equal-risk (0.33 each) is the "
                        "conservative default (Sharpe 5.28). Do NOT exceed DL~0.45: 2026 protection erodes and DL "
                        "is capacity-limited so its frictionless 8.21 overstates its deployable weight."),
        caveat=("DL Sharpe 8.21 is frictionless-signal-level; funding/SIZE are also capacity-bound. Post-impact, "
                "DL's edge shrinks MORE than the liquid mega-cap funding leg -> at real deployment scale the "
                "effective DL advantage narrows, arguing for the lower end (~0.35) not higher.")),
    binding_caveat=("all leg Sharpes are frictionless-signal-level (no market impact); real deployable lower "
                    "(see qim_execution_feasibility). funding leg = raw full-turnover crowding-reversion "
                    "(reproduces megacap_funding_replay per-year net-Sh within 0.03); its DEPLOYED EMA-hold number "
                    "is higher but regime-cherry-picked. 2022 is a PARTIAL joint year (starts 2022-08-31)."))

main["v2_full_history"] = v2
json.dump(main, open(E + "book_assembly.json", "w"), indent=2, default=str)
print("MERGED v2 into", E + "book_assembly.json")
print("equal_risk:", json.dumps(v2["portfolios"]["equal_risk"]))
for k, s in v2["dl_weight_sensitivity"].items():
    print(f"  wdl={k}: Sharpe {s['sharpe']} worstYr {s['worst_year']} 2026 {s['per_year_sharpe'].get('2026')}")
