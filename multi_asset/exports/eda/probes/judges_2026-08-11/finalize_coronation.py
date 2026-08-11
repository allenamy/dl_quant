import json
EDA = "multi_asset/exports/eda/"
c = json.load(open(EDA + "xattn_5yr_coronation.json"))

c["verdict"] = dict(
    ruling="CORONATION CONFIRMED — cross-asset attention is the 2nd real lever (regime-robust). Book to the ~0.08 level.",
    per_year_pairing=("xattn edge over lamorth0 POSITIVE & SIGNIFICANT in ALL 5 YEARS incl BOTH pre-registered "
                      "weak years (2022 +0.006 CI[.0015,.0107]; 2026 +0.021 CI[.0156,.0269]); also sig vs QIM "
                      "every year. weak_year_edge_holds=True → the 'strong-regime-only' downgrade hypothesis is "
                      "REFUTED. Regime-robust across crash-recovery(2022)/chop(2023)/strong(2024-25)/drift(2026)."),
    dynamic_static=("dyn-share mean 0.959, EVERY year >=0.93 (0.932/0.945/0.993/0.971/0.955). The 'too-good' "
                    "2025 +0.104 is 0.971 dynamic — NOT static-tilt inflated. static-shuffle negligible. "
                    "The +0.084 mean is genuine dynamic timing at 5yr scale."),
    net_cost=("xattn book turnover is HIGHER than QIM (~2.0 vs ~1.7, +15-40% — attention's different bets churn "
              "more, as the team lead suspected), BUT net Sharpe @5bps is BETTER in ALL 5 years (5.3/10.1/14.5/"
              "14.0/5.3 vs QIM 2.1/6.7/12.4/12.9/-0.1); ★ 2026 (weak year) xattn is net-POSITIVE at 5bps (+5.28) "
              "where QIM was underwater (-0.13). BE 8-14 bps (2024/25 slightly below QIM due to higher turnover, "
              "but higher IC dominates net Sharpe). Higher IC more than pays for the extra turnover."),
    execution_increment=("higher turnover (~2.0 vs 1.66) tightens capacity ~15-20%: revise the xattn book's start "
                         "to ~$4-8M gross (vs QIM's $5-10M), soft ceiling ~$40-80M (small-coin participation binds "
                         "~20% sooner). Net-Sharpe-per-AUM still better than QIM. The live maker-fill pilot is even "
                         "MORE important for a higher-turnover book. A full capacity re-sim is optional (linear "
                         "turnover scaling suffices for the revision)."),
    blend=("3-way blend (QIM+lamorth0+xattn equal) mean 0.0812 < single xattn 0.0835 — xattn is now too DOMINANT "
           "to blend down (dilution by the weaker QIM/lamorth0 costs ~0.002). Only 2022 (weak year) blend slightly "
           "beats xattn (0.0509 vs 0.0483); 4/5 years single xattn wins. ⇒ 3-way blend NOT recommended; the earlier "
           "QIM+lamorth0 blend (worth-considering when those were co-equal) is SUPERSEDED. Deploy single xattn."),
    deployment=("CHANGE deployment implementation to lamorth0+xattn (the xattn stack) — it DOMINATES both QIM and "
                "lamorth0 in every year (sig vs both). Book lifts from ~0.067 (QIM) to ~0.084 (xattn), +25%. Single "
                "implementation, NOT a blend."),
    too_good_2025=("no red flags: dyn-share 0.971 (dynamic), panel byte-identical (185d3b65 all three), sig CI "
                   "[.035,.045]. 2025 = strongest year for ALL arms (full-universe + high xsec dispersion → "
                   "attention captures relative-value best); benign breadth/dispersion explanation. Report the "
                   "MEAN 0.0835 as the headline, not the 0.104 peak."),
    recommend_seeds=("YES — recommend seed43/44 confirmation (G2 gate) before the final crown. The +0.019 mean edge "
                     "over lamorth0 exceeds the 3-fold single-fold seed spread (±0.01-0.015), so it is likely "
                     "seed-robust, BUT crowning a 2nd lever + the 2025 +0.104 peak warrant a 3-seed check. Cheap "
                     "vs the claim."),
    leaderboard_impact="reorders standings: unpenalized xattn (0.0835) is now #1, above QIM (0.0672) and lamorth0 "
                       "(0.0642). The penalty-dilution correction + cross-asset attention together roughly TRIPLE "
                       "the original penalized-arm leaderboard numbers.")
json.dump(c, open(EDA + "xattn_5yr_coronation.json", "w"), indent=2, default=str)
print("verdict merged into", EDA + "xattn_5yr_coronation.json")
print("weak_holds", c["weak_year_edge_holds"], "| means x", c["xattn_mean"], "blend3", c["blend3_mean"])
