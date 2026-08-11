import json
E = "multi_asset/exports/eda/"
d = json.load(open(E + "book_assembly_raw.json"))

d["judgment"] = dict(
    diversification=dict(
        verdict="PASS (real, mechanistically orthogonal at return level)",
        pairwise_daily_corr=dict(funding_dl=0.099, funding_size=0.039, dl_size=0.262),
        detail=("all three pairwise daily-return corr < 0.3 (passing bar). funding near-orthogonal to "
                "both (mega-cap crowding is a distinct mechanism); dl<->size 0.262 on the robust 489-day "
                "window (both wide, some shared xsec structure, 60d-rolling mean 0.25 but spikes to 0.68 "
                "in strong xsec regimes). funding pairs measured on 123d (short) but clearly near-zero."),
        free_downside=("diversification converts NEGATIVE single-leg worst-months (funding -2.41%, "
                       "size -0.45%) into POSITIVE portfolio worst-months (equal-wt +0.61%, inv-vol "
                       "+0.26%) -> real free downside protection.")),
    portfolio=dict(
        equal_weight=d["portfolios"]["equal_weight"],
        inverse_vol=d["portfolios"]["inverse_vol"],
        note=("in the 123d JOINT window (2025-favorable to DL, leg Sharpe dl=14.2 vs funding=3.1 size=2.7), "
              "blending LOWERS peak Sharpe vs DL-alone (11.5 vs 14.2) as expected when one leg dominates. "
              "The diversification value is downside/regime protection, not peak Sharpe in a DL-strong slice.")),
    weight_recommendation=dict(
        recommended_dl_weight="0.25-0.35 (inverse-vol / near equal-weight)",
        rationale=("in-window Sharpe & worst-month both rise monotonically with DL weight (0.6 best HERE), "
                   "but that is OVERFIT to the DL-favorable 2025 joint window. Over full DL history DL has "
                   "WEAK years (2022 BE 6.5bps, 2026 near-breakeven per verdict) that this window excludes; "
                   "funding/size carry those. Robust (regime-agnostic) choice = inverse-vol risk-parity "
                   "(DL~0.22, size~0.54, funding~0.24) or equal-weight -> positive worst-month, low "
                   "single-leg dependence. Do NOT set DL=0.6 off this window."),
        prefer="robustness over peak (per user rule)"),
    xattn_overlay_precheck=dict(
        per_year_xsec_rankcorr_vs_qim=d["xattn_overlay_precheck"],
        mean=0.42,
        verdict=("NOT redundant. xattn<->QIM prediction corr 0.28-0.51 (mean ~0.42) sits in the 0.4-0.7 "
                 "'real room' band (well below the 0.8 skip threshold). The attention mechanism makes "
                 "meaningfully different cross-sectional bets -> a 'lam_orth=0 + xattn' arm has genuine "
                 "orthogonal/ensemble potential. QUEUE the arm after the lamorth0_5yr confirmation run. "
                 "Caveat: pre-check used the EXISTING penalized xattn (lam_orth=1.0, IC 0.035); the "
                 "unpenalized xattn+attn is untested and could differ.")),
    binding_caveat=("The 3-way JOINT window is only 123 days (2025-02-27..2025-09-15), bounded by the "
                    "funding book's OOS coverage, AND it is a DL-strong regime. So portfolio Sharpe (10-14) "
                    "and the weight optimum are NOT full-cycle representative. ROBUST conclusions that "
                    "survive: (1) low pairwise corr (dl<->size 0.262 on 489d is the solid one), (2) positive "
                    "portfolio worst-months, (3) xattn not redundant. To finalize weights, EXTEND the funding "
                    "book OOS to full 2024-2026 so all three legs share a multi-year joint window."),
    leg_sharpe_caveat=("leg Sharpes (8-14) are signal-level, frictionless-fill (same caveat as the "
                       "execution-feasibility doc); real deployable Sharpe is lower."))

json.dump(d, open(E + "book_assembly.json", "w"), indent=2, default=str)
print("SAVED", E + "book_assembly.json")
