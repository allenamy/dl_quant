> **创建:** 2026-09-13 15:2xZ | **Session:** aud-exec (team-lead brief §B) | **状态:** DRAFT — 未冻结; lead 审阅后冻结; 不改原预注册文件 | **作废条件:** lead 冻结版本入库(以冻结版为准), 或原预注册 `docs/PREREG_chase_restart_2026-09-01.md`(sha256 1a3f433325ae7509…)被替换

# DRAFT AMENDMENT 1 to PREREG_chase_restart_2026-09-01 — analysis population, stop counting, sensitivity

## 0. Scope and attestation
- **What this amends.** Only the *analysis population* and *how the frozen stop rule counts anchors*. It does not change:
  - the intervention (ARM_WEIGHTS 0.5/0.5, salt v2)
  - the estimator (paired within-anchor E[H−X], anchor-cluster bootstrap CI95)
  - the H and X definitions
  - the three pre-registered subgroups
  - the stop rule itself (n*₂ = 100 experimental anchors or 30 days, whichever first)
- **Written before any arm-difference reading.** The drafter computed H neither by arm nor pooled, computed no X, and loaded no price, mid or markout field. The only arm-level quantities the drafter has seen are cost-side taker notional, fees and counts from X-COST (`RESULT_X_COST.md` §2), which the original PREREG allows ("监控只看成本上界与臂平衡").
- **Why amend.** AUDIT_EXEC CFG-04 (842bbffa) found two populations the original text does not address:
  1. Flat-to-full rebuild anchors. At 09-13 12Z: arms chase 100 / no_chase 97 / forced 4, and a no-chase gap of 6,979 USDT = 3.0% of gross, against the registered skip-set envelope "37-500U/锚".
  2. Stop and exit residuals, which W9 (executor ef60f85, 2026-09-13 12:04Z) routes through flatten_only into the same top-up population. E4/R2′ (FX-EXEC) will remove them in code.
- **Where the population comes from (code, executor ef60f85):**
  - `live/binance_executor.py:1582-1624` `_plan_chase_experiment`: population = `from_partial` residuals of names that reached the venue. It skips names with unknown fills and zero residuals, and accounts `from_reject` residuals separately. There is **no reduce-only or exit filter**.
  - `live/chase_policy.py:282-398` `plan_experiment`: C (`neutral_only`) decides first over all names; its fill set becomes `chase_forced`; the randomised arms live inside C's skip set.
  - `in_sample = not excluded` (:387). `excluded_because` (:388) collects three reasons: no book net (:312), skip set < `MIN_ELIGIBLE` = 2 (:321), and the no_chase arm's own residual net > 3% of book gross (:333).
  - Excluded anchors put every randomised name on the control arm.
  - The arm gate is the last gate in the top-up loop (`binance_executor.py:1863`), so a name skipped at min-notional or spread is never treated.

## 1. Analysis population (replaces the implicit "all in_sample anchors, all randomised names")
A unit is a pair (anchor `a`, symbol `s`) with `s ∈ anchors.jsonl chase_experiment.randomised_over` for `a`. The unit is **in the analysis population** iff none of the exclusions below applies. Every exclusion uses only information fixed before the arm gate runs, so arm exchangeability is preserved.

**Anchor-level exclusions**

| id | rule | exact ledger fields | status |
|---|---|---|---|
| X-A1 | not in sample | `anchors.jsonl chase_experiment.in_sample != true` (reasons in `chase_experiment.excluded_because`) | unchanged from the design |
| X-A2 | halted | `anchors.jsonl opening_halted == true` | new (nothing can be treated) |
| X-A3 | rebuild | ρ_pre(a) < 0.50, where ρ_pre(a) = Σ over distinct symbols of \|`prev_w`\| taken from the first `orders.jsonl` row with `rebalance_id == a`, `order_type == "maker"`, `attempt_idx == 1`. `prev_w` = pre-trade venue notional / Σ\|target_notional\|, written by `plan()` from the phase-A readback before any order (`binance_executor.py:801-803`). Sub-type RESUME if the previous nominal anchor has `opening_halted == true` or a `FLATTEN-<ts>` batch lies between the two nominal times; else STEP_UP. | new |
| X-A4 | wrong rebalance id | rows whose `rebalance_id` is not the anchor's own (in particular `FLATTEN-<ts>` batches, `order_type == "protective_flatten"`) never enter H, X or the treated sets, whatever their `anchor_ts` | new (makes the design explicit; guards against attribution by time window) |

**Name-level exclusions**

| id | rule | exact ledger fields | status |
|---|---|---|---|
| X-N1 | exit | the name's first attempt-1 maker row has `target_w == 0.0` exactly (per-name stop force_flat, producer-dropped held names, venue flatten_only clamps) | new |
| X-N2 | venue- or clause-constrained | `s ∈ anchors.jsonl reshape.clamped_after_reshape.names ∪ reshape.forced_flat_names ∪ external_book.held_exit` for anchor `a`. `clamped_after_reshape.names` = add_blocked ∪ flatten_only (`scheduler/anchor_loop.py:430-437`); add_blocked names send no order, and flatten_only names are also caught by X-N1. **Not visible in `anchors.jsonl`:** the clamp's `reduced` names and venue-cap reduce-only names, both of which enter `plan(reduce_only_syms=…)` at `anchor_loop.py:1961-1964` (see gap G1). | new |

**Notes on the definition**
- **X-A3 threshold 0.50.** Steady anchors sit near 1 (the leverage deadzone is ±10%). In 08-28 → 09-13 12Z exactly four non-halted anchors fall below 0.50, all of them the events CFG-04 is about:
  - 09-03 16Z STEP_UP, ρ 0.257 (deposit)
  - 09-07 04Z RESUME, ρ 0
  - 09-10 00Z RESUME, ρ 0
  - 09-13 12Z RESUME, ρ 0

  Source: X-COST receipts (`receipts/x_cost_periods.json` rebuild lists, device sha bf41270f), a non-outcome field. Sensitivity thresholds 0.25 and 0.75 are reported (§4).
- **Why the exclusions keep the randomisation valid.** Assignment is `sha256(seed|chase_arm_v2|symbol)` with seed = `rebalance_id`, independent of `target_w`, the clamp lists and ρ_pre. So dropping units on those covariates leaves the arms exchangeable within the remaining units. C's fill/skip decision and the tilt-abort guard still ran on the full set; the reading is conditional on that recorded decision, as in the original design.
- **Handover to code (E4/R2′).** From the first anchor on which FX-EXEC's E4/R2′ removal is live (its deploy receipt names the anchor), the in-code exclusion is authoritative.
  - The readout still applies X-N1/X-N2 to every anchor.
  - For anchors after the handover it asserts that no unit removed by X-N1/X-N2 is inside `randomised_over`.
  - Any mismatch is listed and the unit excluded; this is never silently accepted.

**Known gap G1.** Two kinds of reduce-only names that are not exits are not written to the ledger: the clamp's `reduced` names (held untradable, target cut toward the position) and venue-cap reduce-only names (`clamp_venue_cap` `reduce_only_syms`). Both are passed to `plan(reduce_only_syms=…)` (`anchor_loop.py:1961-1964`), so X-N2 cannot exclude them. The phase-A line of `state/anchor_runs.log` does carry `untradable_held.reduced`; it is a text log, not a ledger table.

- **Request to E4/R2′:** write a per-name `reduce_only` flag on order rows, or a `reduce_only_names` list in `chase_experiment`.
- **Until then:** the readout parses `untradable_held.reduced` from the phase-A log line of each anchor as a *secondary* source, applies it as exclusion X-N2b, and reports the count of units it removes. If an anchor's log line is missing, the anchor is flagged 'X-N2b unobservable' and kept.

## 2. Treated sets and paired eligibility (cost-side definitions; not changed, made explicit)
- **no_chase treated:** `orders.jsonl` row with `rebalance_id == a`, `order_type == "topup_taker"`, `terminal_reason == "skipped_no_chase_arm"`.
- **chase treated with X measurable:** row with `order_type == "topup_taker"`, `chase_arm == "chase"` (fallback `chase_arm_assigned`), `terminal_reason == "filled"`.
  - `filled_amount_unknown` rows are counted and reported but carry no X. They are excluded from the paired estimate and their share is reported per anchor.
- **Paired-eligible anchor:** after §1 exclusions it has ≥ 1 no_chase-treated unit and ≥ 1 chase-treated unit with measurable X.

## 3. Stop rule under the amendment (frozen rule kept)
- **Count.** n*₂ counts **paired-eligible anchors** (§2) with nominal time ≥ 2026-09-01T16:00Z (first anchor under PREREG 1a3f433325ae).
- **Clock.** The 30-day clock is calendar time from 2026-09-01T16:00Z to 2026-10-01T16:00Z. Halts do **not** extend it.
- **Stop point.** The earlier of the anchor at which the count reaches 100 and the last nominal anchor < 2026-10-01T16:00Z. H of the last counted anchor needs the next anchor's mid; if that next anchor is missing, that anchor is dropped from the count and the readout says so.
- **Readout.** Exactly once, after the stop point, on the §1 population.
- **Halted and excluded anchors are listed explicitly in the readout, never inferred.** Known so far (window 09-01 16Z → 09-13 12Z; X-COST receipts; the list continues to the stop point):
  - halted: 09-06 12Z, 16Z, 20Z; 09-07 00Z; 09-09 20Z; 09-12 16Z, 20Z; 09-13 00Z, 04Z, 08Z (10 anchors)
  - rebuild: 09-03 16Z STEP_UP; 09-07 04Z, 09-10 00Z, 09-13 12Z RESUME
  - flatten-adjacent (a `FLATTEN-<ts>` batch inside the anchor's H horizon; see sensitivity S-F): 09-06 08Z, 09-09 16Z, 09-12 12Z
- **Both counts are printed at the stop point:** the amended count, and the count under the original reading (`in_sample` anchors), labelled.

## 4. Readings
- **Decision reading (primary).** Paired within-anchor E[H−X] on the §1 population. CI95 by anchor-cluster bootstrap (unchanged). The three subgroups are applied inside the §1 population.
- **Sensitivity readings.** Each is labelled "SENSITIVITY — not the decision reading" and none can change the verdict:
  - S-FULL: pre-amendment full population (all `in_sample` anchors, all `randomised_over` units, no X-A2…X-N2)
  - S-ρ25 / S-ρ75: X-A3 threshold 0.25 or 0.75
  - S-F: additionally exclude flatten-adjacent anchors
  - S-RB: rebuild anchors only (descriptive; expected tiny n)
- **Report beside every reading:** arm balance (counts and |residual| notional per arm) and the no-chase unfilled notional as % of gross per anchor. The latter is the cost upper bound the original PREREG monitors.

## 5. Open design question — noted, not decided
On flat-to-full rebuild anchors the executor still randomises. At 09-13 12Z the no-chase arm left 6,979 USDT (3.0% of gross) unfilled until the next anchor. The tilt-abort guard did not fire because it tests the no_chase arm's *net*, not gross.

This amendment only removes such anchors from the *analysis*, so the code still pays the unfilled-gross cost there while producing no usable evidence. Options for the lead or user (book behaviour, needs its own ruling):
- (a) make REBUILD a fourth `excluded_because` reason in `plan_experiment` (everyone chases)
- (b) keep randomising (status quo)
- (c) exclude RESUME only and keep STEP_UP

None is chosen here.

## 6. Receipts this draft relies on
- AUDIT_EXEC register 842bbffa (CFG-04, EXE-02).
- X-COST commits 55aa2d3b / bcb3c0d5 / fdee4894: rebuild and halted lists; D6 definition frozen before any number.
- Code at executor ef60f85 (tree ed2f8819): line references above.
- `anchors.jsonl` fields confirmed present in the 08-28 → 09-13 schema census (`receipts/x_cost_schema_census.json`): `chase_experiment.{in_sample, excluded_because, randomised_over, arm_assigned, arm_counts, arm_notional_usdt, book_gross_usdt}`, `reshape.{clamped_after_reshape, forced_flat_names}`, `external_book.{held_exit, nominal_ts}`, `opening_halted`.
