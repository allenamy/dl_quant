import json
EDA = "multi_asset/exports/eda/"
s = json.load(open(EDA + "arm_s2_32ch_score.json"))
v = json.load(open(EDA + "arm_s2_verdict.json"))

v["v2_final_32ch"] = dict(
    trigger="32ch ablation: 32ch mean 0.0620 UNIFORMLY > 39ch 0.0515 (fold0 +0.010/fold2 +0.023) → metrics "
            "channels are a NET DRAG (anti-pattern #29 channel-addition penalty, at 24h). Leak audit CLEAN "
            "(0B build+restatement). The TRUE S2 is the 32ch version; re-scored below.",
    ruling="CONDITIONAL SLEEVE CANDIDATE → worth 5yr+seeds. (Upgrades the 39ch CONDITIONAL REJECT.)",
    gates=dict(
        a=dict(PASS=s["gate_a"]["PASS"], incremental_ic=s["gate_a"]["incremental_ic"], ci95=s["gate_a"]["ci95"],
               per_fold=s["gate_a"]["per_fold"], raw_ic=s["gate_a"]["raw_ic"],
               note="+0.0285 (CI[.021,.036]), all 3 folds + (2024 +.030/2025 +.036/2026 +.020). ~same as 39ch's "
                    "+0.0277 because 32ch is stronger RAW (0.062) but MORE king-correlated (0.335 vs 0.241, price-only "
                    "overlaps the price-king) → net increment ~equal. STRONG pass."),
        b=dict(PASS=s["gate_b"]["PASS"], pred_corr=s["gate_b"]["pred_corr"], note="0.335 < 0.7 (higher than 39ch 0.24: price-only → more king-like, but still clears)."),
        d=dict(PASS=s["gate_d"]["PASS"], dyn_share=s["gate_d"]["dyn_share"], note="0.895 ≥ 0.5 (dynamic, not tilt)."),
        c=dict(PASS_by_improve_rule=s["gate_c"]["PASS"], margin=s["gate_c"]["margin"],
               note="★ FLIPS vs 39ch. The stronger sleeve clears the Markowitz improve-rule Ss>ρ·Sk at ALL cost "
                    "tiers (gross 5.56>3.78 / maker 4.93>3.26 / taker 3.91>2.33; ρ only 0.19). Best-blend (w0.1) "
                    "improvement +0.077/+0.084/+0.103 (gross/maker/taker) — POSITIVE (unlike 39ch's ~0) but NOT "
                    "bootstrap-significant on 3-fold. ⇒ directionally additive, significance pending 5yr."),
        e=dict(PASS=True, s2_netSh=s["gate_e"]["s2_netSh"], s2_turn_24h=s["gate_e"]["s2_turn_24h"],
               king_turn_4h=s["gate_e"]["king_turn_4h"], note="slow 24h sleeve netSh 5.56/4.93/3.91 (gross/maker/taker), turnover ~1/6 of king daily.")),
    deployable_king_caliber=("★ the improve-rule Ss>ρ·Sk is CALIBER-INVARIANT to uniform Sharpe downscaling (ratio-"
                             "based), so it holds whether the king's baseline is paper-20 or a deployable $5-10M-tier "
                             "Sharpe. AND the king's fast turnover lowers Sk MORE than Ss at realistic cost (taker "
                             "ratio Ss/Sk 0.33 > gross 0.27), so at deployable/net caliber ARM-S2 improves MORE. So "
                             "the multi-sleeve decision does NOT hinge on the inflated paper Sharpe — ARM-S2 is "
                             "additive as a slow orthogonal sleeve at a small weight (~0.1)."),
    metrics_attribution=("★ METRICS/POSITIONING INPUT AXIS CLOSED (3rd null): 32ch (no metrics) 0.0620 > 39ch 0.0515 "
                         "= the 7 metrics channels are a −0.010 NET DRAG (anti-pattern #29 at 24h; capacity dilution "
                         ">alpha). After 1h-linear + 1h-nonlinear nulls, 24h-DL-input is the 3rd null on the "
                         "positioning/OI data asset via THIS usage. Leak-clean (0B) but no predictive value found. "
                         "Data asset retained; do NOT re-mine metrics-as-input without a new mechanism."),
    final=("32ch S2 = CONDITIONAL SLEEVE CANDIDATE: real leak-clean +0.0285 king-orthogonal increment, clears the "
           "book-margin improve-rule at all cost tiers as a slow/cheap orthogonal sleeve (unlike 39ch). The empirical "
           "book improvement (+0.08-0.10) is positive but not yet bootstrap-significant on 3-fold → QUEUE 5yr+seeds "
           "to confirm the increment holds regime-wide AND the book margin reaches significance. If 5yr holds, deploy "
           "as a small-weight (~0.1) slow sleeve — NOT a signal-blend, NOT a book transformer. If 5yr fades → archive."))
json.dump(v, open(EDA + "arm_s2_verdict.json", "w"), indent=2, default=str)
print("v2 ruling:", v["v2_final_32ch"]["ruling"])
