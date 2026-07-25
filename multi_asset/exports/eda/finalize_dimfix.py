import json, os
os.chdir("/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda")
j = json.load(open("funding_dimfix_rerun_raw.json"))
j["verdict"] = {
 "bug_confirmed_independently": {
   "control_corr": 1.0, "control_mean_abs_diff": 3.31e-12,
   "group_offset_rank_units": {"shipped": -0.3745, "normalised": 0.1463},
   "note": "independent rebuild matches 0B bit-for-bit (they reported 3.3e-12 too)"},
 "q1_funding_leg_economics": {
   "price_drift_pct_yr": {"shipped": -10.90, "normfix": -3.69},
   "carry_pct_yr": {"shipped": 11.62, "normfix": 12.17},
   "net_pct_yr": {"shipped": 0.72, "normfix": 8.48},
   "solo_sharpe": {"shipped": 0.07, "normfix": 0.83},
   "book_funding_pnl_pct_yr": {"shipped": 5.17, "normfix": 5.49},
   "read": ("the spurious group tilt was costing ~7.2pp/yr of price drift. Corrected, the leg is a clean "
            "carry trade: +12.2% carry, -3.7% price give-back, net +8.5%/yr. My original wording 'flips "
            "from negative to zero' must be corrected to 'flips from negative to WEAKLY POSITIVE "
            "(Sharpe 0.83)'. 0B's 'close to zero, not positive' is right for the PRICE-ONLY rank-IC arm; "
            "the carry-inclusive economic caliber is modestly positive. Both true, different calibers."),
   "carry_concentration_robust": {
     "top5pct_abs_rate8h_share": {"shipped": 56.1, "normfix": 56.9},
     "liquidity_tiers_normfix": {"calib": 13.9, "mid": 51.3, "small": 34.8},
     "read": ("concentration conclusion survives, so the HL-migration reasoning holds. But the small-tier "
              "share rises 29.4 -> 34.8%, so migrating to a large/mid-cap-only venue costs ~5pp more carry "
              "than the pre-fix estimate.")}},
 "q2_leg_weights": {
   "recommendation": "UNCHANGED -- king 0.45-0.55, recommend 0.50",
   "sweep_kw030": {"shipped": 12.66, "normfix": 12.70},
   "sweep_kw050": {"shipped": 15.46, "normfix": 15.37},
   "argmax": {"shipped": 0.70, "normfix": 0.70},
   "bootstrap_kw050_vs_030": {"shipped": [2.81, 2.22, 3.44], "normfix": [2.66, 2.07, 3.30]},
   "walk_forward_vs_always030": {"shipped": [15.33, 12.71], "normfix": [15.14, 12.87]},
   "max_regret": {"kw0.30": 2.98, "kw0.40": 1.20, "kw0.50": 0.34, "kw0.60": 0.22, "kw0.70": 0.47},
   "asymmetry_survives": True,
   "only_real_change": ("at delta=0.3 the optimal king weight moves 0.50 -> 0.40: the corrected funding leg "
     "does buy slightly more decay protection, exactly as predicted, but the effect is small and kw0.30's "
     "regret at that cell is still only 0.15. Evidence now leans to the LOWER half of the band "
     "(0.45-0.50 better supported than 0.50-0.55)."),
   "challenger_definition_unchanged": True},
 "q3_tail_attribution": {
   "verdict": "UNCHANGED -- the corrected funding leg still creates the tail",
   "FTX_2022_11_09": {"solo_funding": {"shipped": -0.0098, "normfix": -0.0098},
                      "book_kw030": {"shipped": -0.0094, "normfix": -0.0094},
                      "book_kw050": {"shipped": -0.0111, "normfix": -0.0111}},
   "mechanism": ("the FTX-day loss comes from EXTREME rate values dislocating the funding cross-section when "
     "a major entity collapses. The dimension artifact is a slow-moving GROUP LOCATION SHIFT and does not "
     "participate in a single-day gap event. 'Cutting funding weight trims that tail' stands.")},
 "dl_retrain_ruling": {
   "position": "AGREE with the ruling, but the stated reason is insufficient -- so I made it falsifiable, and it PASSES",
   "why_reason_insufficient": ("'the normalised arm is insignificant' judges funding as a SIGNAL. The DL uses it "
     "as a FEATURE, and an insignificant feature can still carry a structural group marker (4h coins sit 0.37 "
     "rank units low) that drifts over time as coins migrate. The right question is not 'is the factor "
     "significant' but 'did the artifact PROPAGATE into the DL predictions'."),
   "test_result": "PASS -- see dl_group_artifact_test",
   "second_channel_found": ("xsr_fund (ch 28) = centered pct-rank of funding_ema carries the same artifact -- "
     "a rank transform preserves a group-level shift. The DL sees it through TWO channels. Fixing funding_ema "
     "at source fixes xsr_fund automatically (same script), but this must be VERIFIED at the next panel rebuild.")},
 "impact_on_deliverables": {
   "funding_pnl_backfill.md": "2 numeric corrections, verdict unchanged",
   "fee_fill_sensitivity.md": "no change (the surface is built on turnover and cost, not the funding signal)",
   "leg_contribution_review.md": "1 correction (leg is weakly positive, not zero) + band centre nudged down; all conclusions stand",
   "pilot_protocol_prereg.md": "Section 5 calibration constants must be updated if the corrected factor is adopted",
   "pilot_protocol_section5_new_constants": {
     "current_weights": {"intercept": 182.3, "slope": 14.66, "vol_pct": 12.16, "breakeven_bps": 12.43},
     "challenger_king050": {"intercept": 248.7, "slope": 20.43, "vol_pct": 13.66, "breakeven_bps": 12.17}}},
 "md": "funding_dimfix_rerun.md"}
json.dump(j, open("funding_dimfix_rerun.json", "w"), indent=1, default=str)
print("wrote funding_dimfix_rerun.json")
