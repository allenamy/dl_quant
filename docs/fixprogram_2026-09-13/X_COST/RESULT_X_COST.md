> **创建:** 2026-09-13 15:0xZ | **Session:** aud-exec (team-lead brief "X-COST attribution + CFG-04/06 drafts") | **状态:** RESULT(只读测量; 未经 lead 复跑) | **作废条件:** live pilot_log 08-28..09-13 的 orders/fills/anchors 被改写(输入 sha 见 receipts/x_cost_periods.json), 或分解装置 bf41270f / 修订 72c1dfc5 被改

# RESULT · X-COST — why the maker share of rebalance fills fell (AUDIT_EXEC CHK-03)

## 0. Answer

The drop is real and it is almost entirely **two running experiments plus a scale effect**. It is not rebuilds, not a gross-multiplier change, and not visibly the placement eps change.

> **★ 更正 2026-09-16(独立复审 FXR-DOC-2, Codex 9f6384fb · FIXPROGRAM §12; 原句保留字节)。** 三处措辞过强, 以本框为准:
> 1. **下界写 0 是错的。** requote direct 臂的 11.3831 pp 依赖「历史转单率可搬到当前人口」这一**可交换性假设**; 不作该假设时**原模型自报 [−0.4178, +15.5642] pp**(本文 §4 行内即为 [−0.42, 15.56], 下面表格的「bounds 0 to +15.6」把下界截到 0, 作废)。
> 2. **chase 4.3531 / chase_forced 2.4401 pp 是「已成交桶份额」, 不是「关掉实验后的反事实」。** 桶恒等分解成立(93.1253% → 73.9049%, 降 19.2204 pp, 13 个成交桶), 但**政策的因果效应没有被识别**。
> 3. **约 5.14 USDT/日只在「成交额固定 + 5 bps 换 2 bps」两个假设下成立。**
> 4. **「执行成本侧没有隐藏缺陷」这一结论不被接受**: 首次 −5022 拒单率 **14.3% → 23.0% 的原因尚未测**; 价格、冲击、机会成本与分母变化**没有被该桶恒等式排除**。可保留的表述只有: **「已观测成交按当前规则无未分配余项; 实验桶增长解释了记账分类的变化」**。

On trading anchors, excluding rebuilds, maker share fell from **93.1% (S1a, 08-28 → 09-01 12Z) to 73.9% (S3, 09-08 → 09-13 12Z)**. That is +19.22 pp of taker share, decomposed exactly:

| Item | pp of D | Class | Status |
|---|---:|---|---|
| Requote experiment, direct arm (rejected makers go straight to IOC top-up) | **+11.4** (bounds 0 to +15.6; +9.7 under the log-share convention) ← **下界作废, 见 §0 更正框: [−0.4178, +15.5642]** | designed experiment cost, ends at readout (≥09-19 00Z) | component VERIFIED; the counterfactual split is INFERRED |
| Chase experiment, chase arm on in-sample anchors | **+4.4** | designed experiment cost, ends at the chase stop rule | VERIFIED |
| Neutrality-forced chases (chase_forced) | **+2.4** | standing policy; appears only after the 09-03 deposit (scale) | VERIFIED component; scale mechanism INFERRED |
| Other from_reject growth: bigger post-only reject pool, requote-arm and exempt IOC, net of the pre-experiment IOC share | **+1.0** | the reject-rate rise has a known root-cause family (single snapshot pricing × sequential submit), a fixable execution-engineering target; cause of the rise not measured | component VERIFIED; cause INFERRED |
| Everything else (maker-as-taker, unjoined, unsourced top-ups) | 0.00 | — | VERIFIED |

- **Cost of the drop.** At the S3 measured fee rates (maker 2.00 bps, taker 5.00 bps on USDT fills) and 14,862 USDT of rebalance fills per trading anchor, the fee side is about **0.86 USDT per anchor, ≈5.1 USDT/day**. About 3.0 USDT/day of that is the requote direct arm and 1.2 USDT/day the chase arm. The price side of taker vs maker fills is **not computed**; that is the experiments' outcome and is behind the barrier (§2).
- **Fixable defects inside the drop are small.**
  - Stop and full-exit residuals routed through chase or IOC (EXE-02): 0.42% of D in S3 is on target_w == 0 names.
  - Rebuild anchors randomised into the chase experiment (CFG-04): this *raises* maker share, so it does not explain the drop.
- **The ≥90% deep-check baseline** describes policy A before 09-01 16Z and before the requote experiment. Under the experiments running now, a steady trading anchor's expected maker share is about 74-78% (S3: 73.9% ex-rebuild, 77.6% all).

## 1. Device chain (committed before each run)

| Commit | Object |
|---|---|
| 3eea1906 | `devices/x_cost_schema_census.py` — categorical value sets only, before any decomposition |
| 55aa2d3b | `devices/x_cost_decompose.py` (sha256 bf41270f…) — frozen identity, components, periods, rebuild rule, barrier |
| bcb3c0d5 | run-1 receipts + `devices/x_cost_amend_a1.py` (sha256 72c1dfc5…), committed before it ran |
| this commit | A1 receipts, `devices/x_cost_render.py` (arithmetic over receipts only), `receipts/x_cost_tables.md`, this RESULT |

**Frozen definitions** (full text in the device docstring):
- **Window:** nominal anchors 08-28 00Z … 09-13 12Z, 98 anchors.
- **Fill identity:** fills de-duplicated on (symbol, trade_id).
- **Maker share:** M/(M+T) over maker and topup_taker order types by `venue_maker_flag` (the CHK-03 caliber). FLATTEN batches (K1) sit outside D.
- **Taker notional:** T equals the sum of 13 mutually exclusive components, per anchor. Worst |T − Σ| = 7.3e-11 USDT; the run exits 3 above 1e-6.
- **Rebuild:** not halted and Σ|prev_w| < 0.50, from attempt-1 plan rows (pre-trade venue notional / target gross).
- **Periods:** P1/P2/P3 as briefed, plus the driver sub-periods declared before computing: S1a/S1b at the 09-01 16Z chase restart and eps 0.50; S2a at the 09-03 deposit; S2b at the 09-05 12Z requote experiment; S3.

**Run 1 data quality:**
- 58,395 fill rows read, 29,257 after de-duplication.
- 0 trade_ids shared by two symbols; 0 ambiguous top-up joins; 0 unmapped fills; 0 parse anomalies.
- Input sha256 identical at start and end; rc=0.

**Amendment A1** (device defect found reading run 1, fixed before any use of the affected numbers). Run 1's driver ratios (pooled maker fill ratio, residual pool / maker intent, first-attempt −5022 rate) counted halted anchors' blocked maker intent: 164k-235k USDT each, 4 anchors in S2b and 6 in S3. **Those three run-1 ratios are void.** The identity and component shares are unaffected, because halted anchors have D = 0. A1 recomputes them on non-halted anchors and adds the from_reject factorisation and the direct-arm counterfactual (rc=0, inputs unchanged).

## 2. Information barrier

**Not computed:**
- chase H or H−X, by arm or pooled
- any price, mid, markout or cost-vs-mid quantity for any arm
- any placement-arm split; `placement_arm` is never loaded

**How that is enforced:** rows are projected onto allow-lists at parse time. `_barrier_selfcheck()` requires every forbidden field name to appear exactly once, in its declaration, in both device files.

**Computed at arm level** (cost-side, allowed by the brief): taker notional of the requote direct arm (K2d) and requote arm (K2q); chase arm (K3ci) and chase_forced (K3f); the no-chase unfilled residual; USDT fees by component.

**Disclosure for the lead:** K2d vs K2q notional shows the *fee component* of the requote contrast (direct plans pay more taker fee). That direction is fixed by the design (direct = IOC). The price component, where the experiment's uncertainty lies, was not touched. The counterfactual in §4 deliberately uses the pre-experiment S2a conversion rate instead of the requote arm's in-experiment conversion.

## 3. Numbers

### T1 Maker share by period
| period | anchors | halted | rebuild | D (USDT) | maker share | median anchor | min–max anchor | ex-rebuild |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| P1 | 34 | 0 | 0 | 69,895 | 92.6% | 94.5% | 73.5–100.0% | 92.6% |
| P2 | 30 | 4 | 2 | 438,111 | 83.8% | 83.1% | 56.1–100.0% | 80.4% |
| P3 | 34 | 6 | 2 | 770,057 | 77.6% | 77.2% | 55.9–100.0% | 73.9% |
| S1a | 27 | 0 | 0 | 54,969 | 93.1% | 95.0% | 74.8–100.0% | 93.1% |
| S1b | 7 | 0 | 0 | 14,926 | 90.4% | 93.1% | 73.5–96.7% | 90.4% |
| S2a | 15 | 0 | 1 | 198,808 | 80.7% | 87.6% | 76.0–95.9% | 87.9% |
| S2b | 15 | 4 | 1 | 239,303 | 86.3% | 73.1% | 56.1–100.0% | 76.1% |
| S3 | 34 | 6 | 2 | 770,057 | 77.6% | 77.2% | 55.9–100.0% | 73.9% |

**Rebuild anchors:**
- 09-03 16Z STEP_UP (Σ|prev_w| 0.257, deposit): maker share 76.0%.
- 09-07 04Z RESUME and 09-10 00Z RESUME: maker share 100%. Every top-up sent at those two anchors ended `abandoned_max_attempts` (68 and 71 rows), consistent with the E-0910-A venue lock family (not re-verified here).
- 09-13 12Z RESUME: maker share 68.6%.

In S2b and S3, the low-maker-share periods, excluding rebuilds *lowers* maker share (86.3 → 76.1%, 77.6 → 73.9%). Rebuilds offset the drop rather than drive it. In S2a the deposit step-up anchor is the exception.

### T2 Taker components, % of D (non-halted, ex-rebuild)
| component | S1a | S1b | S2a | S2b | S3 | Δ S3−S1a |
|---|---:|---:|---:|---:|---:|---:|
| K2d from_reject top-up, requote arm direct | 0.00 | 0.00 | 0.00 | 9.88 | 15.56 | +15.56 |
| K2q from_reject top-up, requote arm requote | 0.00 | 0.00 | 0.00 | 3.12 | 3.17 | +3.17 |
| K2e from_reject top-up, exempt (reduce-only) | 0.00 | 0.00 | 0.00 | 0.00 | 0.57 | +0.57 |
| K2n from_reject top-up, no arm (pre-experiment) | 6.87 | 6.73 | 6.45 | 0.00 | 0.00 | −6.87 |
| K3ci from_partial, chase arm, in-sample | 0.00 | 2.83 | 4.00 | 6.63 | 4.35 | +4.35 |
| K3f from_partial, chase_forced | 0.00 | 0.00 | 1.67 | 4.22 | 2.44 | +2.44 |
| **taker total** | 6.87 | 9.56 | 12.12 | 23.85 | 26.10 | **+19.22** |

K3co, K3nc, K3n, K4, K5, K6 and K7 are 0.00 in every sub-period. Overlay (not additive): taker notional on target_w == 0 names is 1.17 / 1.17 / 1.02 / 2.24 / 0.42 % of D in S1a / S1b / S2a / S2b / S3.

### T3 Drivers (A1; non-halted, ex-rebuild)
| indicator | S1a | S1b | S2a | S2b | S3 |
|---|---:|---:|---:|---:|---:|
| first-attempt −5022 plans / plans (%) | 11.6 | 9.0 | 14.3 | 19.6 | 23.0 |
| rejected intent / maker intent | 0.221 | 0.218 | 0.231 | 0.213 | 0.282 |
| from_reject IOC notional / rejected intent | 0.248 | 0.258 | 0.262 | 0.576 | 0.597 |
| maker intent / D | 1.255 | 1.195 | 1.068 | 1.061 | 1.145 |
| maker fills / maker intent (pooled over placement arms) | 0.742 | 0.757 | 0.823 | 0.718 | 0.645 |
| no-chase unfilled residual / maker intent | 0.0810 | 0.0548 | 0.0283 | 0.0460 | 0.0428 |
| residual below min-notional floor / maker intent | 0.0035 | 0.0027 | 0.0024 | 0.0016 | 0.0013 |
| median target notional per name (USDT) | 171 | 176 | 706 | 674 | 907 |
| external_book.gross_mult | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 |

### T4 / T5 from_reject growth split
- **Factorisation, S2a → S3** (share 6.45% → 19.30%): the reject pool (RI/MI ×1.222) contributes +2.35 pp, IOC conversion (×2.282) +9.68 pp, and intent per fill (×1.072) +0.82 pp (log-share allocation).
- **Direct-arm counterfactual.** Direct plans, had they been re-quoted, are assumed to convert to IOC at the pre-experiment S2a rate c0 = 0.2616 (S1a: 0.2476). That makes the attributable direct-arm share **11.38 pp** in S3 ex-rebuild (11.61 with the S1a c0), within bounds [−0.42, 15.56]. With rebuilds included it is 7.58 pp. S2b ex-rebuild: 7.29 pp.

## 4. Driver-by-driver reading

1. **Chase 50/50 restart (09-01 16Z).**
   - VERIFIED: K3ci is 0 in S1a (policy A) and 2.83 / 4.00 / 6.63 / 4.35 pp afterwards. Under policy A those names would not have been sent, so the attributable share equals K3ci.
   - Not modelled: residuals left unfilled may be re-traded as maker at the next anchor.
2. **Placement eps 0.35 → 0.50 (same anchor, 09-01 16Z).** No detectable effect on the maker share.
   - S1a → S1b (7 anchors): the whole −2.7 pp change is K3ci (+2.83); from_reject share is flat (6.87 → 6.73).
   - Pooled first-attempt −5022 rate fell 11.6 → 9.0% and pooled maker fill ratio rose 0.742 → 0.757. Both are consistent with the 09-05 finding that behind lowers rejects.
   - INFERRED: confounded with the chase restart, n = 7, and no arm split by barrier.
3. **Requote randomisation (09-05 12Z).**
   - VERIFIED: K2d and K2q replace K2n from S2b on, and IOC conversion of rejected intent roughly doubles, 0.26 → 0.58-0.60.
   - INFERRED: attributable share ≈ 11.4 pp (counterfactual) or 9.7 pp (log-share).
4. **Gross 1.5 → 2.0 (09-03).** **Not supported by the ledger.** `external_book.gross_mult` is 2.0 on all 98 anchors from 08-28. The 09-03 event is the deposit: median target notional per name rose ×4.1 (171 → 706 USDT, 907 by S3).
   - Scale effect (INFERRED): chase_forced fills appear only after it (0 → 1.67-4.22 pp) and the below-floor residual pool shrinks (0.35 → 0.13% of intent). More neutrality fills clear the venue floor.
5. **Post-only reject rate.** Rose from 14.3% (S2a) to 19.6% (S2b) and 23.0% (S3) of plans; rejected intent per maker intent 0.231 → 0.282.
   - Contributes ≈ +2.4 pp through the reject pool (T4).
   - Cause not measured. Candidates: more names per anchor and longer sequential submission after M1 (09-04), the September volatility regime, bigger per-name orders after the deposit.
   - The known root-cause family (one book snapshot priced for 30-110 s of sequential submits; STATE §2, 09-05 reject-rate review) makes this an execution-engineering target, not a ledger defect. Any change is book behaviour and needs a prereg.
6. **Residual size.** The chase population's unfilled no-chase residual is 4.3% of maker intent in S3, vs 8.1% under policy A (where every skip-set name was withheld).
7. **Rebuilds and resumes.** They raise maker share in P2 and P3; see T1.
8. **Halted days** (no rebalance fills, excluded from every ratio in A1):
   - S2b: 09-06 12Z, 16Z, 20Z; 09-07 00Z
   - S3: 09-09 20Z; 09-12 16Z, 20Z; 09-13 00Z, 04Z, 08Z
9. **FLATTEN batches.** 468,140 USDT of taker notional in P3 (09-09 16:45Z and 09-12 12:47Z), outside the CHK-03 caliber. Counting them would make the drop look far larger; they are a watchdog response, not rebalance execution.

## 5. Defects vs designed costs

| Part | Size | Classification | Owner / next step |
|---|---:|---|---|
| Requote direct arm IOC | ≈11.4 pp | designed experiment cost, temporary | CFG-05 readout ≥09-19 00Z; no action before |
| Chase arm IOC | 4.4 pp | designed experiment cost, temporary | chase stop rule (100 experimental anchors / 30 days); CFG-04 amendment for population |
| Neutrality-forced chases | 2.4 pp | standing policy, scale-dependent | none (policy); record in K5 baseline |
| Reject pool growth | ≈2.4 pp (log-share) / ≈1.0 pp (additive residual) | execution engineering; cause unmeasured | candidate prereg (quote refresh before submit); not a ledger defect |
| Stop / exit residuals routed through chase or IOC | 0.42% of D in S3 (overlay) | defect vs clause (EXE-02) | FX-EXEC E4 / R2′ |
| Deep-check baseline ≥90% | — | DOC_STALE | K5: replace with a component-level baseline (S3 ex-rebuild: maker 73.9%, K2d 15.6, K2q 3.2, K3ci 4.4, K3f 2.4) |

## 6. Verified vs inferred
- **VERIFIED** (script output over the frozen window):
  - maker share per period and anchor
  - the exact 13-component identity and every component share
  - rebuild and halted classes
  - gross_mult = 2.0 throughout
  - fee rates 2.00 / 5.00 bps on USDT fills in S3
  - reject rates, intent ratios and conversion ratios pooled over arms (A1)
  - the resume anchors' top-ups all abandoned
- **INFERRED:**
  - the direct-arm counterfactual (assumes re-quote conversion stayed at the pre-experiment rate)
  - the log-share allocation convention
  - the scale mechanism behind chase_forced
  - the null eps effect
  - candidate causes of the reject-rate rise
  - the E-0910-A link at the resume anchors
  - USDT/day translations, which cover fees only

## 7. Limits
- Notional-weighted, so large anchors dominate. S1b has 7 anchors.
- Concurrent changes not separated: FTRIM (09-02 12Z), M1 universe (09-04), the deposit (09-03), executor deploy b681ca5 (09-12 06:05Z).
- BNB-era fees (to 09-04) are not converted.
- Dynamic effects (unfilled residuals re-traded later) are not modelled.
- No price or markout component (barrier).
- The chase and requote conclusions are about taker volume and fees only, not about whether either experiment is worth its cost.

## 8. Reproduce
```bash
cd /Users/haosiyu/Desktop/quant_research/docs/fixprogram_2026-09-13/X_COST
PYTHONDONTWRITEBYTECODE=1 python3 devices/x_cost_decompose.py receipts   # exits 4 if live inputs changed since run (sha in receipts)
PYTHONDONTWRITEBYTECODE=1 python3 devices/x_cost_amend_a1.py receipts
PYTHONDONTWRITEBYTECODE=1 python3 devices/x_cost_render.py receipts
```
Receipts (sha256 prefix):
- x_cost_per_anchor.json 2c4783ea
- x_cost_periods.json 4af8439d
- x_cost_decompose_run.log 0819a14c
- x_cost_a1.json 18da0251
- x_cost_amend_a1_run.log 4fc41e93
- x_cost_attribution.json aa5e1ff9
- x_cost_tables.md 533043b2
- x_cost_schema_census.json 829847e0

The device's sha check compares start and end of its own run only. To confirm a rerun used the same inputs, compare its `inputs` block with `receipts/x_cost_periods.json`. Later appends should not change the numbers: markout supersede copies carry the same trade and notional and are de-duplicated, and anchors after 09-13 12Z are outside the window. A rewrite of in-window rows would change them.
