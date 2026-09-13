> **创建:** 2026-09-13 15:3xZ | **Session:** aud-exec (team-lead brief §C) | **状态:** DRAFT — 未冻结; lead 审阅后冻结(冻结 = 本文 sha 入库, 先于任何读数) | **作废条件:** lead 冻结版入库; 或窗口内 placement eps / 动作集改变; 或任何人在冻结前计算了 09-05 12:00Z 之后的按臂 placement 结果(见 §0 声明)

# DRAFT PREREG — placement bandit eps 0.50: full-coverage re-read (AUDIT_EXEC CFG-06)

## 0. Why, and what is already known
- **History.** `config/book.json` `placement_bandit.eps` has been 0.50 since 2026-09-01 16Z. It was adopted on the once-only main read (`multi_asset/exports/eda/RESULT_placement_bandit_read_2026-09-01.md`): ΔV +1.658 [+1.102, +2.280] **and** "不毒" (markout60 behind −1.67±2.43 vs join −1.24±1.25). That markout rested on 15% coverage.
- **The voiding.** `docs/RESULT_requote_and_behind_live_causal_2026-09-05.md` §3 (PREREG sha 5ed36216, device `multi_asset/exports/live/exec_requote_behind_2026-09-05/analyse_requote_behind.py` sha256 f36d0155…, data 08-12..09-05) measured, at coverage 0.95:
  - paired ITT all-in cost behind − join **−4.84 [−20.68, +1.88]** bps per unit of intended notional
  - markout60 behind **−7.69** vs join **−2.40**, **Δ −5.28 [−14.19, −0.33]**

  It voided the 09-01 "不毒" sentence, kept eps 0.50 without expanding, and required this re-read on full-coverage markout plus paired ITT.
- **Original design constraints still binding** (PREREG_placement_bandit_2026-08-12, sha256 f657efde…):
  - actions {join, behind-1-tick}
  - attempt-1 main maker only; reduce_only exempt
  - deterministic assignment `sha1(f"{rebalance_id}:{symbol}")` last byte < round(eps×256) → behind (`live/placement_bandit.py:8`)
  - fail-closed eps 0
  - death clause §4-2: "behind 的 markout 显著更毒 ⇒ 关闭"
- **Drafter's barrier attestation.**
  - The drafter has computed no placement-arm outcome of any kind (no markout, no ITT, no fill rate by arm) for any window.
  - X-COST loaded no `placement_arm` field. It reported pooled maker fill ratios and first-attempt −5022 rates by period (`RESULT_X_COST.md` T3), pooled over both arms.
  - **At freeze the lead must attest** that nobody has computed an arm-level placement outcome for anchors after 2026-09-05 12:00Z. If someone has, W0 (§1) moves to the freeze time.

## 1. Window (frozen at freeze)
- **W0:** the first nominal anchor ≥ **2026-09-05 12:00Z** (first anchor after the 09-05 review read its data).
- **W1:** the last nominal anchor < **2026-10-03 12:00Z** (28 calendar days). Halts do not extend it.
- **Excluded anchors** (listed in the readout, never inferred):
  - `opening_halted == true`
  - REBUILD: not halted and ρ_pre < 0.50, defined exactly as in `DRAFT_AMENDMENT_chase_restart_population_2026-09-13.md` §1 X-A3
  - any row whose `rebalance_id` is not the anchor's own (FLATTEN batches)
- **Eps change.** If `placement_eps` on any attempt-1 maker row in the window differs from 0.50, the window ends at the anchor before it.
- **Other policy changes** (`requote_p`, chase `weights`, `k_seconds`) do not end the window. Assignment is independent of them, so the contrast stays unbiased and reads as an average over the window's policy mix. Stratified readings are reported (§4).
- **Expected precision** (INFERRED, scaled from the 09-05 CIs by √(25 days / trading days)):

  | trading days | A half-width | E half-width |
  |---:|---:|---:|
  | ~24 (28 calendar minus halts) | ≈ ±11.5 bps | ≈ ±7.0 bps |
  | 14 | ≈ ±15 bps | ≈ ±9 bps |

  An UNDECIDED reading is therefore likely, and **the UNDECIDED default in §3 is the rule that matters most**.

## 2. Population and calibers
**Plans.** A plan is (anchor, symbol) with an attempt-1 maker row carrying `placement_arm ∈ {join, behind}`; `exempt` is excluded. The plan is built as in the 09-05 device's plan block, with the fixes listed here.

**A — paired ITT all-in cost** (bps per unit of intended notional; negative means behind is cheaper):
- For each plan: Σ over its filled order rows (attempt-1 maker, requote attempt-2 maker, every `topup_taker` row with the same `rebalance_id` and symbol) of |filled_notional| × (side-signed (avg_fill_px − mid_at_anchor)/mid_at_anchor × 1e4 + fee bps), divided by |intended_notional| of the attempt-1 row. The unfilled remainder counts as 0 and its share is reported per arm.
- **Fee (fix F1).** Use `fee_paid`/|notional| only when `fee_paid` is finite and not (`fee_all_usdt is False` without `fee_conversion`). Otherwise use the nominal rate for the row type: maker rows 2.00 bps, top-up rows 5.00 bps (the USDT rates measured in X-COST S3). The imputed notional share is reported per arm. The 09-05 device folded unknown fees to 0; that is not repeated.
- **Pairing** (as 09-05): per anchor, notional-weighted arm means; anchor weight w = min(Σ intended of join, Σ intended of behind); Δ = Σ w(mb − mj) / Σ w. Anchors lacking an arm are dropped and counted.

**E — markout60 on maker fills** (bps; positive means price moved in our favour after the fill):
- Fills: `order_type == "maker"` rows of the plan's `rebalance_id` and symbol, de-duplicated on **(symbol, trade_id), last row wins** (fix F2; the 09-05 device keyed on trade_id).
- A fill is **marked** iff `mid_at_fill_plus_60s` is finite and > 0 and `mark_window_s == 60`. Per `ops/backfill_markout.py:295-320` this value is the first aggTrade price ≥ fill_ts+60s within 60 s, not a mid. Terminal statuses `no_trade_within_window` / `aggtrades_window_expired` are unmarked.
- markout = side × (mark − fill_px)/fill_px × 1e4, weighted by fill notional, over marked fills.
- **Coverage rule (frozen).** Coverage per arm = marked notional / maker-fill notional. **E is READABLE only if coverage ≥ 0.90 in both arms and |cov_behind − cov_join| ≤ 0.03.** Otherwise E is NOT READABLE and every E-condition in §3 evaluates false; the readout says so.
- CI as 09-05 (pooled arm means per bootstrap sample); a within-anchor paired E is a sensitivity reading.

**Intervals.** UTC-day block bootstrap, 2000 resamples, **seed 20260913**; CI95 = 2.5 / 97.5 percentiles. Exactly one primary reading after W1.

**Secondary** (reported, never decisive): realised/intended; maker-leg fill share; first-attempt −5022 rate; maker fill price vs anchor mid conditional on fill; top-up notional shares (from_partial / from_reject); all per arm.

## 3. Decision rule (frozen at freeze; evaluated in this order; the output is a *proposal to the user*, since any eps change is book behaviour)
A_lo / A_hi and E_lo / E_hi are CI95 bounds.

| # | condition | proposal |
|---|---|---|
| 1 | A_lo > 0 (behind significantly costlier) | **STOP behind: eps → 0** |
| 2 | E readable ∧ E_hi < −1.0 ∧ A_hi ≥ 0 (significantly more toxic beyond the 09-05 margin, and not significantly cheaper) | **STOP behind: eps → 0** (original death clause §4-2 with the 09-05 margin) |
| 3 | A_hi < 0 ∧ E readable ∧ E_lo > −1.0 (significantly cheaper and not more toxic beyond the margin) | **KEEP eps 0.50**; "不毒" re-established on full coverage |
| 4 | anything else, incl. mixed (A_hi < 0 ∧ E_hi < −1.0) or E NOT READABLE | **REVERT eps → 0.35** (proposed default; see §5 D1) |

- The −1.0 bps toxicity margin is carried over unchanged from the 09-05 frozen rule.
- No mid-window reading of any arm difference, except the safety lines in §4.

## 4. Safety lines and stratified reports
**Safety lines** (daily, after the 00Z anchor; evaluated by someone who does not read the primary; output is a boolean and the triggering day only):
- **SL1** behind absolute maker fill rate < 15% on a UTC day with ≥ 100 behind plans ⇒ eps → 0 and investigate (original §3).
- **SL2** `placement_arm` or `placement_eps` missing on attempt-1 maker rows of any trading anchor ⇒ eps → 0, fix, restart the window count (original §4).
- **SL3** three consecutive UTC days on which the day's paired A exceeds +30 bps with ≥ 100 behind plans each day ⇒ eps → 0 and investigate. Mirrors the requote experiment's safety line.
- **SL4** `config/book.json` eps ≠ 0.50 at any anchor, or `placement_eps` on rows ≠ 0.50 ⇒ the window ends (§1) and the change is reported.

**Stratified and sensitivity readings** (labelled, never decisive):
- by `requote_p` value on the plan rows
- by chase `weights` on the anchor
- rebuild anchors only
- within-anchor paired E
- fees excluding imputed rows
- pooled with the combo-era 09-05 window (08-26..09-05), labelled "REUSES DATA ALREADY READ"

## 5. Design questions for the lead (not decided in this draft)
- **D1 — UNDECIDED default.** REVERT 0.35 (proposed) or KEEP 0.50 (the 09-05 status quo)?
  - For REVERT: the 09-01 adoption needed ΔV > 0 *and* not toxic; the second leg is void, so the adoption is not re-established.
  - For KEEP: the 09-05 disposition kept 0.50, and A's point estimate there favoured behind.
  - Given §1's precision, D1 is the most likely outcome driver.
- **D2 — window length.** 28 days (proposed) or 14 days (end ≈ 2026-09-19 12Z, aligned with the requote readout; wider CIs). A 14-day window makes rule 4 near-certain.
- **D3 — scope of "stop behind".** eps 0 (join only, the original fail-closed state) or eps 0.10 (the original sampling rate, keeps learning)? The draft uses eps 0 because that is the original death-clause action.

## 6. Receipts this draft relies on
- PREREG_placement_bandit_2026-08-12 (f657efde…); RESULT_placement_bandit_read_2026-09-01; RESULT/PREREG_requote_and_behind_live_causal_2026-09-05 (5ed36216) and its device (f36d0155…).
- `ops/backfill_markout.py` (mark semantics, 60 s window since 2026-09-05).
- X-COST RESULT fdee4894: fee rates; pooled period indicators only.
- AUDIT_EXEC 842bbffa CFG-06.
