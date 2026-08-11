import json
EDA = "multi_asset/exports/eda/"
core = json.load(open(EDA + "arm_s2_core.json"))
book = json.load(open(EDA + "arm_s2_book.json"))

v = dict(
    title="ARM-S2 (24h supplementary factor) — 0C gate verdict", created="2026-07-13", auditor="0C",
    arm="wideA_s2_y24_c1 (lam_orth=0 + xattn + 39ch incl 7 metrics, YR24, 3-fold, test 2024-2026)",
    verdict="CONDITIONAL REJECT into the book as-is — passes 4/5 gates but FAILS the decisive book-margin "
            "gate (c). The +0.0277 king-orthogonal increment is REAL/large/dynamic, but the king dominates "
            "so ARM-S2 does not lift the combined book. Two REQUIRED pre-accept follow-ups (leak + 32ch).",
    gates=dict(
        a_incremental_ic=dict(PASS=core["gate_a_pass"], pooled=core["incremental_ic_pooled"],
                              ci95=core["incremental_ci95"], per_fold=[p["incremental_ic"] for p in core["per_fold"]],
                              raw_ic=core["raw_resid_ic_pooled"],
                              note="+0.0277 pooled (54% of raw 0.0515 survives removing the 4h king); all 3 folds "
                                   "positive (2024 +0.024/2025 +0.046/2026 +0.013); CI excludes 0. STRONG pass."),
        b_pred_corr=dict(PASS=core["gate_b_pass"], corr=core["pred_corr_king"],
                         note="0.24 vs king (24h vs 4h = genuinely different bets); well below 0.7."),
        d_dyn_share=dict(PASS=core["gate_d_pass"], dyn=core["dyn_share_orth"],
                         note="0.944 — the increment is dynamic timing, NOT static tilt. ★ but dyn-share does NOT "
                              "catch a DYNAMIC publish-lag leak in the metrics channels (see follow-up)."),
        c_book_margin=dict(PASS=book["gate_c_pass_maker"],
                           daily_corr_king=book["margin_maker1p9"]["corr"],
                           king_sharpe=dict(gross=book["margin_gross"]["king_sh"], maker=book["margin_maker1p9"]["king_sh"], taker=book["margin_taker5"]["king_sh"]),
                           s2_sleeve_sharpe=book["s2_sleeve_netSh"], s2_breakeven_bps=book["s2_breakeven_bps_approx"],
                           weight_sweep_maker={w: book["margin_maker1p9"]["sweep"][w]["impr"] for w in book["margin_maker1p9"]["sweep"]},
                           note="★ FAIL: no ARM-S2 weight (0.1-0.5) at any cost significantly improves the combined "
                                "book; best (taker5, w=0.1) +0.04 NOT sig; equal/50-50 DILUTES −3.3. The king's "
                                "(paper) Sharpe 12-20 so dominates ARM-S2's sleeve 3.4-4.9 that a 4×-weaker "
                                "orthogonal (corr 0.20) sleeve barely moves the book = the 3-way-dilution lesson."),
        e_net_cost=dict(PASS=True, s2_sleeve_netSh=book["s2_sleeve_netSh"], breakeven_bps=book["s2_breakeven_bps_approx"],
                        turnover_s2_24h=book["margin_maker1p9"]["s2_turn"], turnover_king_4h=book["margin_maker1p9"]["king_turn"],
                        note="24h SLOW sleeve: netSh 4.9 gross / 4.35 maker / 3.45 taker5; BE 16.8 bps; daily "
                             "turnover ~6× lower than the king (its natural edge). Standalone positive.")),
    required_followups=[
        "★ METRICS LEAK AUDIT (blocking): the 7 metrics channels (funding/OI/positioning) have SETTLEMENT/PUBLISH "
        "lag. The +0.0277 increment is only valid if those channels used ≤t-KNOWN (published) values, not "
        "future-settled ones. dyn-share (0.944) does NOT catch a dynamic publish-lag leak. REQUIRES 0B's channel "
        "build script + a lag-sensitivity / shuffle-future-on-metrics test before the increment can be trusted.",
        "32ch ABLATION (attribution): is the +0.0277 increment from the 24h PRICE horizon (clean — a 24h "
        "momentum/reversal orthogonal to the 4h king is expected) or from the METRICS channels? A 32ch (no-metrics) "
        "run at the same protocol isolates it. If 32ch ≈ 39ch → metrics add nothing (no leak risk, but no data "
        "value either); if 39ch ≫ 32ch → metrics drive it (and the leak audit is CRITICAL). Needs a GPU run."],
    deployment_nuance=("gate (c) FAIL is amplified by the king's frequency-inflated PAPER Sharpe (20). If deployed "
                       "as a SEPARATE SLOW/CHEAP capacity sleeve (3-leg-book logic: funding+DL+SIZE accepted legs "
                       "weaker than the DL leg on diversification/capacity/cost grounds), ARM-S2 has NARROW value "
                       "(low corr 0.20, cheap slow turnover, adds capacity). That call needs the king's DEPLOYABLE "
                       "(not paper) Sharpe + a multi-sleeve deployment decision — not a signal-blend."),
    bottom_line="Do NOT blend ARM-S2 into the king signal (dilutes). The increment is real but book-immaterial "
                "given king dominance. Resolve the metrics leak audit + 32ch ablation FIRST; if clean and the "
                "deployment goes multi-sleeve, ARM-S2 is a candidate slow sleeve at a small weight, not a book lift.")
json.dump(v, open(EDA + "arm_s2_verdict.json", "w"), indent=2, default=str)
print("verdict:", v["verdict"][:80])
print("gates: a", core["gate_a_pass"], "b", core["gate_b_pass"], "c", book["gate_c_pass_maker"], "d", core["gate_d_pass"], "e True")
