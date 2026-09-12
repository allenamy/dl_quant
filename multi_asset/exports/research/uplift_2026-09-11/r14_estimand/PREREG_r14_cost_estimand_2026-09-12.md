> **创建:** 2026-09-12 | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** FROZEN BEFORE ANY NUMBER FROM THE NEW DEVICE | **作废条件:** 任一钉住输入被重建; 或 rolling.npz 的 5m 行约定被证伪; 或 live ledger 的 mid_at_anchor 语义被证伪
> **分支:** research/book-uplift-2026-09-11 | **实盘零接触:** ~/dl_quant_live 与 ~/wide_shadow 全程只读

# PREREG r14 — IS THE POST-FILL MARKOUT ALREADY INSIDE THE REPLAY'S y4?

## §0 THE QUESTION, STATED AS A MEASUREMENT

The replay books, for anchor i and name s, `pnl_raw += sm[s] * y4[i,s]`
(`trackA/w10_sleeve.py` L329, device sha `b88e35a4…`), where `sm` is the weight AFTER
this anchor's trade (L312-313) and `y4` comes from the accounting meta (L69).

The desk does not transact at the instant `y4`'s window opens. The disputed quantity is therefore

    GAP(fill) = sgn * (F - P_ref(s, E)) / P_ref(s, E) * 1e4        [bps, + = COST to the book]

where F is the fill price, sgn = +1 for buy / -1 for sell, E is the canonical 4h grid instant
(00/04/08/12/16/20Z), and `P_ref(s,E)` is the price at which the replay's y4 window OPENS.

GAP is decomposed EXACTLY (no approximation; the identity is asserted in the device) as

    1 + GAP/1e4*sgn = (F / M) * (M / P_ref)
    slip  = sgn * (F/M - 1) * 1e4              <- the already-published "estimand A" quantity
    drift = sgn * (M/P_ref - 1) * 1e4          <- THE TERM NEITHER PUBLISHED ESTIMAND CONTAINS
    GAP   = sgn * ((1+sgn*slip/1e4)*(1+sgn*drift/1e4) - 1) * 1e4

M = `mid_at_anchor`, the venue mid captured at STEP 1 of the executor's anchor run
(`scheduler/anchor_loop.py` L5: "capture mid_at_anchor for every symbol (before any order exists)").

## §1 DECLARED IN ADVANCE — WHAT THE THREE INPUTS ARE, FROM SOURCE

These three facts are established from source BEFORE any new number and are the load-bearing
claims of this round. Each is re-asserted mechanically by the device.

**F1. `P_ref(s,E)` = the close of the 5-minute bar that CLOSES AT E.**
  - `wide_fea_v2ext_meta.y4` = Σ ret5 over cache rows **E..E+47** (window [E-5m, E+3h55m]).
  - `meta_newprod(_v4).y4`   = Π(1+ret5)-1 over cache rows **E+1..E+48** (window **[E, E+4h]**).
  Receipts already on disk, recomputed at machine precision by two independent devices:
  `allweather_2026-09-05/trackA/results/target_alignment_receipt.json` (max_abs 3.41e-07 for
  rows E+1..E+48 vs 0.448 for rows E..E+47) and
  `uplift_2026-09-11/r9_screen/CANDIDATE_3_COHORT_AGE_DECAY_CURVE_0/Y4DEF_r9screen.json`
  (VERDICT "PROD_E1_E48", median_abs_err 1.40e-10).
  Cache row convention (bar CLOSE time, not open time) is asserted by
  `label_code_check.py` L50-51: `CTS[Ei]==E_ts`, `CTS[Ei+1]-300==E_ts`, `CTS[Ei+48]==E_ts+14400`.
  ⇒ The v4 accounting caliber marks **anchor-close to anchor-close**, and the entry reference is
  the LAST-TRADE price stamped at E.

**F2. `mid_at_anchor` is NOT the mid at E.** It is the mid at the executor's anchor-run start.
  Measured first-hand below from `anchor_ts mod 14400`. The name invites the inference that it is
  the mid at the anchor instant; that inference is the error this round tests (E-0825-H family).

**F3. The replay's cost model contains no adverse-selection term.**
  `r3k_impact/r3k_mkcostb.py` L67: `maker_bps = fee_mk + I`, `taker_bps = fee_tk + spread/2 + I`,
  with `I = max(book-walk VWAP_vs_mid - half_spread, 0)` (L58, "excess_of_half_spread").
  `CAL_BASE.known_limits[2]`: "no temporary/permanent decomposition and **no queue/adverse-selection term**".

## §2 PRIMARY ESTIMAND, FROZEN

**PRIMARY** = notional-weighted mean `drift` over all deduped live fills in the DEPLOYED execution
era (ERA2, defined in §3), in bps per unit traded notional.
This is the quantity that is in **neither** published estimand and that decides the sign.

**SECONDARY (pre-declared, not selected after the fact):**
 S1 notional-weighted `slip`  (must reproduce the archived `tier_stats.json` mk/tk slip — GATE G1)
 S2 notional-weighted `GAP`   (= the full disputed quantity of the task's STEP 2)
 S3 same three, split by `order_type` ∈ {maker, topup_taker, protective_flatten}
 S4 same three, split by liquidity decile of causal trailing-4h quote volume
 S5 same three, split by era (ERA1 pre-2026-08-22 / ERA2 on-and-after)
 S6 same three, split by `attempt_idx`

**K (total arm count) = 1 primary + 6 pre-declared secondary families = 7.** No arm is selected
after seeing a number; the primary is fixed by this document. No threshold below is a function of
any number produced by this device.

## §3 WINDOWS, CALIBERS, UNITS — FROZEN

- **ERA1** = live anchors with `anchor_ts mod 14400 < 600` (executor ran within 10 min of E).
- **ERA2** = live anchors with `anchor_ts mod 14400 >= 600`. **ERA2 is the deployed form.**
  The split is defined on a MECHANICAL property of the ledger, not on a date chosen after looking.
- Cache coverage: `~/wide_shadow/state/rolling.npz` (40-day rolling tail). Anchors outside its
  span are EXCLUDED and counted; the exclusion is reported, never silently dropped.
- **Units**: all per-fill quantities are **bps per unit traded notional**.
  Conversion to the book statistic `g` (bps per 4h anchor per unit gross) uses the MATCHED replay
  turnover caliber **0.0540270 = E[t_i/g_i]** for repricing the REPLAY's own cost model, and the
  LIVE caliber **0.10864** for anything measured as realised live cash. Raw `turnover_mean`
  0.03032 is NEVER used (E-0911 turnover trap; ratio 1.78189, not 1/mean_gross_total=1.4375).
- **CI95**: UTC-day block bootstrap, B=2000, `numpy.default_rng([20260905, k])`, k enumerated per
  statistic in the receipt. Blocks are UTC days of `fill_ts`.
- **Resolution floor**: 0.23 bps/anchor/gross at book level. A book-level point estimate below it
  is NOT a result and will be reported as such.

## §4 GATES — ALL MUST PASS BEFORE ANY NUMBER IS QUOTED

- **G1 REPRODUCTION.** Restricted to 2026-08-01T04Z..2026-09-11T04Z and using the archived slip
  definition (fill vs `mid_at_anchor`), the device must reproduce `infra1_cost/tier_stats.json`
  tier-level `mk_slip_bps` and `tk_slip_bps` to within **0.10 bps** in all three tiers.
  FAILS ⇒ my dedupe / sign / BNB handling differs from the archived instrument and no number is quoted.
- **G2 AXIS BY NAME.** Every symbol is located in the 829 panel axis **by name**
  (`shadow_bundle/config.json.symbols_panel`), never by position. Unmatched symbols are counted
  and excluded; the count is in the receipt.
- **G3 ROW CONVENTION.** The device asserts on `rolling.npz`: `diff(ts) == 300` everywhere, and
  every anchor row satisfies `ts % 14400 == 0`. FAILS ⇒ abort.
- **G4 IDENTITY.** `max |(1+sgn*slip/1e4)*(1+sgn*drift/1e4) - (1+sgn*GAP/1e4)| <= 1e-12`.
- **G5 ENV WHITELIST (E-0826-D).** The device reads **NO** environment variable. It asserts the
  **explicitly empty set** and writes that assertion into the receipt as an enumerated field.

## §5 DECISION RULE — FROZEN BEFORE THE FIRST NUMBER

Let `x_gap` = notional-weighted GAP (bps/unit traded, ERA2), `x_fee` = BNB-converted realised fee
(bps/unit traded), `MODEL` = 2.9537 (costb_PWR_G230k `book_avg_bps_per_unit_turnover`, sha
`295b4e7b462373e4…`).

- **RULE B (ESTIMAND_B_MODEL_UNDERCHARGES)** iff `x_gap + x_fee > MODEL` **and** the CI95 of
  `x_gap + x_fee` excludes MODEL from below, **and** the excess is of the order claimed by the
  markout term structure (≥ 3.0 bps/unit traded, i.e. the r11 `fee_plus_adverse_60s` 5.9873 or
  `fee_plus_adverse_steady` 9.5011 are reproduced).
- **RULE A (ESTIMAND_A_MODEL_OVERCHARGES)** iff `x_gap + x_fee < MODEL` **and** the CI95 of
  `x_gap + x_fee` excludes MODEL from above.
- **CANNOT_DISTINGUISH** otherwise — in particular if the CI95 of `x_gap + x_fee` contains MODEL.

Separately and independently, the DOUBLE-COUNTING question is ruled by F1 + the arithmetic of the
window, not by a threshold: markout over `[t_fill, t_fill + D]` is inside `[E, E+4h]` **iff**
`t_fill >= E` and `t_fill + D <= E + 4h`. The device measures the share of deduped fill notional
satisfying this for D ∈ {60s, 5m, 15m, 1h} and reports it. A share ≥ 0.95 at a given D means the
replay's own mark already carries that D-horizon markout for ≥95% of traded notional, and charging
it is double-counting THAT interval.

## §6 WHAT WOULD FALSIFY MY OWN READING

1. If `drift` is statistically indistinguishable from zero on ERA2, then `mid_at_anchor` being 24
   minutes late costs nothing and the published estimand A is complete as it stands.
2. If `drift` is large and NEGATIVE (a credit), the replay is pessimistic about entry and the
   correction goes the other way.
3. If G1 fails, my instrument and the archived one are not measuring the same thing and nothing
   here may be quoted against the archived numbers.
4. `rolling.npz` is the LIVE PRODUCER's cache, not the pod v4 cache. It is the same construction
   formula (`shadow_loop_v3.py` L242 "与 pod_build_wide 逐字同公式") but it is NOT the pinned v4
   artifact. Every number derived from it is labelled **LIVE-CACHE lineage**, and the ruling is
   stated so that it does not depend on the third decimal of that cache.

## §7 ENV WHITELIST (E-0826-D)

`r14_gap.py` reads the environment variable set: **{ } — EXPLICITLY EMPTY, ASSERTED AT RUNTIME**
by overriding `os.environ.get` to raise, and by asserting that none of
`["LEGS","PHI","CAL","MEMBERS_TOPN","COSTB_JSON","PANEL_IN","V2","OUT_TAG","W3FIX","FTRIM",
"UMASK_SCOPE","SLOW_NPY","FPRED","FSEED","LOOK","WRULE","TRADE_TOPN","UMASK_NPZ","SHADOW_OFFSET_MIN"]`
is present in `os.environ`.
