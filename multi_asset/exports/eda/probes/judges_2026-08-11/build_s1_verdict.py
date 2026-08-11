import json
EDA = "multi_asset/exports/eda/"
r = json.load(open(EDA + "arm_s1_score.json"))
r["verdict"] = dict(
    ruling="CLOSE the 4h-re-mine AXIS + ARCHIVE. Not a 5th leg (redundant, hurts the book); only a "
           "marginal king-enhancement (+0.0006 IC, not worth a 2nd 4h model). The king has SATURATED the 4h "
           "horizon — same-arch residual re-mine yields diminishing returns.",
    gate_a=dict(PASS=r["gate_a_pass"], increment=r["increment_pooled"], ci95=r["increment_ci95"],
                note="+0.0181 vs YR4K (CI[.016,.021], all 4 years +). REAL but note: corr(YR4K,YR4)=0.989 so "
                     "this is near-full-dimension (no residual-space discount, per team-lead) — YET it does NOT "
                     "translate to book value (see below)."),
    gate_b=dict(PASS=r["gate_b_pass"], pred_corr=r["pred_corr_king"],
                note="0.36 vs king (<0.7) but MODERATE — S1 (same arch/4h) partially RE-LEARNED the king, so "
                     "much of its 'increment' is redundant."),
    king_merge=dict(fifty_fifty="HURTS −0.0072 (sig)", small_weight=r.get("king_merge_boost", {}),
                    note="★ 50/50 blend HURTS (king 0.0913→0.0841). Small-weight boost (w0.1) gives a TINY but "
                         "significant +0.0006 IC (0.0913→0.0919, +0.7%). Real but immaterial — not worth a 2nd "
                         "4h model; if wanted, capture via KING SEED-ENSEMBLING (cheaper)."),
    five_leg=dict(s1_book_corr_king=r["s1_king_book_corr"], leg_corr=r.get("s1_leg_corr", {}),
                  four_vs_five=r.get("five_leg", {}),
                  note="★ FAIL. S1↔king book-corr 0.477 (HIGH, same 4h horizon + same execution profile) → "
                       "redundant with the dominant king leg; adding S1 as a 5th leg HURTS the book (Sharpe "
                       "8.06→7.63, Δ −0.43). NOT a diversifier."),
    mechanism=("the xattn king (seed-robust) has SATURATED the 4h horizon. A re-mine of its residual with the "
               "SAME architecture finds a statistically-real +0.0181 increment, but it's MOSTLY REDUNDANT (pred-"
               "corr 0.36, book-corr 0.48) — the truly-orthogonal part contributes only +0.0006 IC. Same-horizon "
               "same-execution re-mine = diminishing returns."),
    contrast_with_S2=("S2 (24h): corr 0.22 to king, worst-year protection, 4-leg book improves → ACCEPT. S1 (4h): "
                      "corr 0.48, book-hurt, only +0.0006 merge → ARCHIVE. LESSON: HORIZON DIVERSITY (+different "
                      "execution profile) is what makes a supplementary factor book-worthy; a same-horizon re-mine "
                      "of a saturated king does not add, even with a statistically-real residual increment."),
    recommendation="ARCHIVE ARM-S1; CLOSE the 4h-re-mine axis (the king saturates 4h). If the marginal ~+0.0006 "
                   "4h lift is wanted, capture it by KING SEED-ENSEMBLING, not a separate residual-fit model. "
                   "Supplementary-factor phase: S2 (24h) = 1 ACCEPT; S1 (4h re-mine) = archive; metrics input axis "
                   "= closed. Remaining EV: genuinely DIFFERENT-horizon or DIFFERENT-mechanism factors only.")
json.dump(r, open(EDA + "arm_s1_verdict.json", "w"), indent=2, default=str)
print("ruling:", r["verdict"]["ruling"][:70])
