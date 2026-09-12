> **创建:** 2026-09-12 | **状态:** FROZEN BEFORE THE RULING; written AFTER `r14_gap.py` produced its fill-weighted numbers and BEFORE any intent-weighted number exists | **修订对象:** `PREREG_r14_cost_estimand_2026-09-12.md` sha256 `bbedfdaa33644a82a05660dd50e38a65ffddef8ae3c06d509c643c7131183904` + AMENDMENT 1 sha256 `6207572a9dba8a32554b6c3a44467509e179127ae92084f2bf44f7fafb872594`

# PREREG AMENDMENT 2 — MY PRIMARY ESTIMATOR WAS CONDITIONED ON FILLING, WHICH IS THE ONE
# CONDITIONING THE QUANTITY IS KNOWN TO BE SELECTED ON. IT IS REPLACED BY AN INTENT-WEIGHTED ONE.

## The defect, stated plainly (mine)

§2 of the prereg made the PRIMARY "notional-weighted mean `drift` over all deduped live **fills**".
`drift` is `sgn·(P(E+25m)/P(E) − 1)`, a property of the price path over exactly the interval during
which a passive maker order either fills or does not. **A resting buy limit fills BECAUSE the price
came down.** Conditioning on `fill` therefore selects the sign of `drift` directly.

This desk has already measured that selection first-hand, and the number is in the deployed config:
`~/dl_quant_live/config/book.json` `_k_seconds_rollback_2026_08_10` —
"逆向选择已确证: 按方向调号的价格变动 **成交单 +3.66 vs 未成交 +5.48 bps** —— 挂不到的恰是模型更对的那一半".
Filled orders saw 1.82 bps LESS adverse movement than unfilled ones, on the same intent set.
(Memory entries `slippage_is_a_selection_effect`, `maker_slippage_is_negative`, `opportunity_gross_is_not_capturable`.)

**The replay assumes 100% of `Δw` is executed.** The quantity that reprices the replay is therefore
the drift weighted by **INTENT**, not by fills. The first run's fill-weighted reading
(`drift` −6.1168 bps/unit traded, ERA2) is hereby labelled a SELECTED reading and is retained only
as the numerator of the selection-effect measurement below. **It is not the ruling number.**

## What changes

**PRIMARY (replaced).** `drift_intent` = |intended_notional|-weighted mean of
`sgn(intended_notional)·(P(E+5k)/P(E) − 1)·1e4` over **attempt_idx == 1** rows of `orders.jsonl`
in ERA2, k = round((anchor_ts − E)/300). Attempt-1 intent is the anchor's full intended delta
(attempt-2 intent is the post-partial-fill residual and would double-count).
Units, windows, CI method (UTC-day block bootstrap, B=2000, `default_rng([20260905,k])`) unchanged.

**SECONDARY, added (all pre-declared here, none selected afterwards):**
 A2-1 `drift_fill` (the first run's reading) — reported ONLY as the selected comparator.
 A2-2 **SELECTION = `drift_fill` − `drift_intent`**, with its own CI. This is the fill-selection
      effect on the deployed execution, measured directly for the first time on this axis.
 A2-3 **FILL SHORTFALL**: filled notional / attempt-1 intent, and the drift on the UNFILLED
      complement. The replay books 100% of `Δw`; the desk books the fill rate.
 A2-4 **ERA1 CONTROL**: the same `drift_intent` computed on ERA1 (executor ran at E+~1min, k=0 by
      construction ⇒ the instrument must return exactly 0.0). A non-zero reading there is an
      instrument defect. Additionally, ERA1 is re-measured with k forced to 5 as a **placebo**:
      it asks "would this instrument manufacture a tilt out of an execution that did not wait?"
 A2-5 **PRE-ANCHOR PLACEBO**: the same statistic with the window `[E−5k, E]` (rows E−k+1..E)
      instead of `[E, E+5k]`, same signs, same weights. It separates "the trade sign is tilted
      against the window the desk waits through" from "the trade sign is tilted against recent
      returns in general" (a standing property of a rebalancing book, which would show up in BOTH).
 A2-6 **k SENSITIVITY**: k = 4 (to E+20m) vs k = 5 (to E+25m). The ledger mid is stamped at
      E+24m01s, so k=5 overshoots by 59 s and k=4 undershoots by 241 s; the pair brackets the truth.

**K (arm count) is now 1 primary + 6 (prereg §2) + 6 (this amendment) = 13.** Declared here, before
any intent-weighted number exists.

**DECISION RULE (§5) is amended in exactly one place, and it becomes STRICTER.** The ruling may not
be made on a fill-conditioned quantity. The all-in realised cost used in §5 becomes

    x_allin = drift_intent + slip_fill·(filled/intent) + fee_fill·(filled/intent)

i.e. the price terms that are only observable on fills are scaled by the share of intent they
actually cover, and the drift term — which the replay charges on 100% of `Δw` — is taken at full
weight from intent. If `drift_intent`'s CI95 contains zero, the §5 comparison is made on the point
estimate AND on both CI ends, and the ruling is **CANNOT_DISTINGUISH** unless every one of them
falls on the same side of MODEL = 2.9537.

**RECONCILIATION REQUIREMENT (new gate G6).** `drift_intent` measured here is the live-ledger
analogue of `exec_caliber_reconcile.py` (sha `e9d8daafa8bbb5ae…`, run 2026-09-05) term
`delta_w_t_minus_w_t-1` / `a_minus_c`, which read **+0.0805 / +0.1004 bps/anchor/gross on 2024→26**
(replay weights, historical cache, switch at row E+5 = E+25min — the same 25 minutes).
The two instruments must be compared explicitly in the result, in the SAME units, and any sign
disagreement must be reconciled before a ruling is issued (desk rule
`two_instruments_disagree_reconcile_first`). Conversion: bps/unit traded × turnover/gross.
