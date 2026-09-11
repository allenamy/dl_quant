> **创建:** 2026-09-11 | **Session:** b9646a9e (round-2 time-series sleeve hunter) | **状态:** 结果(K=34: 30 预注册 + F9 四臂事后扩展并标注, GATE P 逐位通过, 零录取; 按冻结规则字面零 NEAR_MISS) | **预注册:** `PREREG_r2_timeseries_sleeves_2026-09-11.md` 同目录(AMENDMENT 1/2/3 写在任何候选数字之前; AMENDMENT 4 明确标注为读过前 30 臂之后的 K 扩展) | **作废条件:** 判据在看数字后被改; 触碰实盘

# RESULT · Round-2 TIME-SERIES sleeve family — 34 arms, 0 ADMITTED, 0 NEAR_MISS by the letter of the frozen rule

## 0. GATE P — VERIFIED BITWISE before anything was measured
Device `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`,
six knobs off, own tree `/workspace/uplift_2026-09-11/r2_ts/dev` (symlinks only; nothing written outside my namespace).
`np.array_equal` **True on 4/4** archived arms `V4_A0_{dyn,fix}_s{42,2027}`, both `d30_n2_c42_rec` (10039,23) and
`d30_n2_c42_W` (10039,829).

A0 reference, re-derived by me from the archive (`g = rec[:,18]/rec[:,5]`):
| span | n | g (bps/anchor/gross) | Sharpe |
|---|---|---|---|
| FULL CYCLE 2022-01-01 → 2026-08-10 20Z | 9918 | **+0.6627** | **1.316** |
| 2022-01-31 → 2026-08-31 | 10039 | +0.6152 | 1.213 |
| FROZEN 2025-03-01 → 2026-08-10 20Z | 3168 | +1.8937 | 3.043 |
Matches the brief's +0.663 / 1.32 / +1.894 / 3.04. **All numbers below use the n=9918 full cycle unless labelled.**

Second instrument receipt: my independent accounting `acct(W)` reproduces the device's own file-caliber columns from
the saved weight matrix to **max|Δ| 8.09e-06 bps** (net), 1.55e-07 (carry), 1.99e-08 (cost), 7.37e-09 (gross).
Round-1's defect (3) — approximate sleeve-injection parity, mean|dg| 0.0136 bps — **does not apply to this family**:
every blend delta here is a difference of two runs down the SAME float32 path, so the paired delta is exact.

## 1. Headline
**The structural premise is confirmed and the family is empty.**
A0 demeans every anchor's cross-section, so a time-series bet is structurally a different bet — and the data agree:
**all 33 time-series sleeve arms have |corr to A0's g on the full cycle| ≤ 0.1163; 31 of 33 are ≤ 0.090**
(the two exceptions are F6_PARA_th12 at −0.1106 and F9_IVFRAC_z90 at −0.1160). The 34th arm, F4b, is not a sleeve —
it rescales A0 itself and correlates +0.963 with it, exactly as its construction implies. That is the cleanest
orthogonality any round has produced (round-1's Amihud sleeve: +0.204).
**But no arm reaches the Sharpe 1.50 bar.** Best standalone full-cycle Sharpe = **1.319 ± 0.47** (F5_VOLTS_6_42),
and that arm's edge decays monotonically to nothing (9.11 → 0.22 bps/anchor/gross, 2022 → 2026) with a frozen-window
Sharpe of 0.229 and an out-of-fit stress window of −5.89 bps/anchor.

**Architectural finding that matters more than any single arm:** the live executor re-demeans the non-zero set
(`smr[nz] -= smr[nz].mean()`, device L~330, blueprint `dl_quant_live/signal/legs.py:124`). A directional sleeve is
annihilated by that operator. I therefore also built F8 — the dollar-neutral, executor-legal expression of the same
five timing signals (beta rotation: long low-beta half / short high-beta half, signed by the timing signal).
**All five F8 arms earn nothing: |Sharpe| ≤ 0.19 except the breadth one at −1.10.** So the time-series axis is not
merely thin — **the only expression this book can hold is precisely the expression that has no return**, and any
admission from this family would arrive with a deployment blocker attached.

## 2. All arms, full cycle (n=9918), same span, same warm-up (position 0 before anchor 900)
`lvl` = mean(net)/mean(gross) bps/anchor/unit gross; `SR` on the allocated-budget series; `ρA0` on the full cycle.
ICk0 / ICk−1 are Spearman of the raw signal against the market return at that lag.

| arm | SR full | lvl | SR frozen | SR 2024on | oof bps (n=121) | ICk0 | ICk−1 | ρA0 | carry frac |
|---|---|---|---|---|---|---|---|---|---|
| F5_VOLTS_6_42 | **1.319** | 6.124 | 0.229 | 0.935 | −5.888 | 0.0437 | 0.0130 | −0.036 | 0.006 |
| F4_XDISP_z180 | 0.913 | 3.911 | **1.459** | 1.290 | −2.916 | 0.0464 | 0.0575 | −0.078 | 0.014 |
| F5_VOLTS_12_90 | 0.607 | 2.626 | −0.203 | 0.807 | −6.680 | 0.0354 | 0.0116 | −0.016 | 0.017 |
| F4_XDISP_z90 | 0.567 | 2.391 | 0.761 | 0.793 | −5.217 | 0.0398 | 0.0517 | −0.061 | 0.023 |
| F1_TSMOM_L42 | 0.466 | 2.141 | 0.889 | 0.754 | +0.260 | 0.0067 | 0.1323 | −0.075 | −0.098 |
| F1_TSMOM_L12 | 0.422 | 2.063 | 0.627 | 0.842 | +1.854 | 0.0055 | 0.2616 | −0.074 | −0.098 |
| F1_TSMOM_L6 | 0.410 | 2.152 | 0.071 | 0.547 | +1.160 | −0.0287 | 0.3561 | −0.057 | −0.101 |
| F4_XDISP_z360 | 0.390 | 1.645 | 1.460 | 1.249 | −1.481 | 0.0511 | 0.0644 | −0.029 | −0.001 |
| F1_TSMOM_L180 | 0.322 | 1.295 | −0.100 | 0.130 | +2.954 | 0.0135 | 0.0822 | −0.024 | −0.150 |
| F1_TSMOM_L90 | 0.262 | 1.121 | −0.021 | 0.224 | +3.269 | 0.0137 | 0.1008 | −0.068 | −0.158 |
| F1_TSMOM_L30 | 0.259 | 1.224 | 0.407 | 0.535 | +0.431 | 0.0067 | 0.1594 | −0.070 | −0.166 |
| F5_VOLTS_30_180 | 0.242 | 1.056 | −1.816 | 0.853 | −5.811 | 0.0287 | 0.0164 | +0.014 | 0.087 |
| F2_AGGFUND_z360 | 0.231 | 1.005 | −0.604 | −0.076 | +1.069 | 0.0006 | 0.1206 | −0.061 | **0.455** |
| F8_BROT_F3_FUNDSURP_z180 | 0.181 | 0.107 | 0.535 | 0.293 | −1.202 | −0.0194 | 0.1391 | +0.033 | 0.091 |
| F2_AGGFUND_z90 | 0.178 | 0.765 | −0.587 | −0.253 | +1.062 | −0.0098 | 0.1288 | −0.031 | **0.436** |
| F8_BROT_F1_TSMOM_L42 | 0.159 | 0.094 | 0.403 | 0.166 | −0.521 | 0.0067 | 0.1323 | −0.009 | **0.904** |
| F6_PARA_th12 | 0.103 | 6.573 | 0.336 | 0.068 | −7.875 | — | — | −0.111 | −3.624 |
| F3_FUNDSURP_z180 | 0.068 | 0.307 | −0.015 | −0.454 | −1.998 | −0.0194 | 0.1391 | +0.071 | 0.008 |
| F2_AGGFUND_z180 | 0.058 | 0.251 | −0.771 | −0.471 | +0.715 | −0.0060 | 0.1247 | −0.041 | **1.595** |
| F3_FUNDSURP_z90 | 0.023 | 0.097 | −0.093 | −0.588 | −2.743 | −0.0128 | 0.1453 | +0.059 | **0.499** |
| F6_PARA_th8 | −0.010 | −0.380 | 0.162 | −0.091 | +2.134 | — | — | −0.090 | **46.5** |
| F3_FUNDSURP_z360 | −0.004 | −0.020 | 0.087 | −0.344 | −2.106 | −0.0194 | 0.1329 | +0.084 | −0.264 |
| F8_BROT_F2_AGGFUND_z180 | −0.085 | −0.051 | 0.712 | 0.186 | +0.264 | −0.0060 | 0.1247 | −0.009 | 0.341 |
| F8_BROT_F5_VOLTS_12_90 | −0.152 | −0.088 | 0.482 | 0.360 | −1.120 | 0.0354 | 0.0116 | +0.009 | −0.135 |
| F7_BREADTH_z90 | −0.217 | −1.016 | −0.808 | 0.496 | −3.102 | −0.0380 | 0.3398 | +0.012 | −0.020 |
| F7_BREADTH_z360 | −0.383 | −1.859 | −0.991 | 0.011 | −2.379 | −0.0358 | 0.3453 | +0.016 | −0.038 |
| F7_BREADTH_z180 | −0.396 | −1.895 | −0.842 | 0.211 | −2.622 | −0.0376 | 0.3420 | +0.004 | −0.013 |
| F6_PARA_th5 | −0.435 | −9.409 | −0.341 | −0.759 | +4.279 | — | — | −0.046 | **1.291** |
| F8_BROT_F7_BREADTH_z180 | −1.099 | −0.685 | −0.416 | −0.472 | −1.189 | −0.0376 | 0.3420 | +0.015 | 0.027 |
| F4b_DISP_GROSSSCALE | (not a sleeve — see §5) | | | | | | | +0.963 | |

## 3. The one NEAR_MISS, attacked
### F5_VOLTS_6_42 — vol term structure (σ over the last 6 anchors / σ over the last 42 anchors, both ending on the bar that closes at E; z over 360; causal walk-forward sign; position tanh(z)·sign)
| | full (9918) | frozen (3168) | 2024on (5718) | oof (121) |
|---|---|---|---|---|
| net bps/anchor | +0.9765 | +0.0760 | +0.5807 | **−5.8883** |
| Sharpe | **1.319** | 0.229 | 0.935 | −7.568 |
| lvl bps/anchor/gross | 6.124 | 0.759 | 4.399 | −25.95 |
| CI95 (day-block, 2000, rng[20260905,k]) | [+0.298, +1.685] | [−0.474, +0.612] | [−0.119, +1.317] | [−13.71, +0.635] |
| **CI BONF30** (α=0.05/30) | **[−0.084, +2.117]** | [−0.706, +0.914] | [−0.520, +1.694] | [−20.14, +2.786] |

- **carry fraction of net 0.006** — this is a PURE PRICE bet, not the closed carry axis. pnl 1.0162, carry −0.0060, cost 0.0456.
- **ρ to A0 = −0.036** (s42) / −0.041 (s2027); ρ to XIB_LAG50 = −0.029; ρ to the market return +0.074.
- **placebo A (per-anchor permuted feature, 200 draws)**: mean −0.0907 bps, 95% band [−0.361, +0.254], **0/200 ≥ real**.
- **placebo B (circular-shift of the feature through the same operator, 200 draws — preserves marginal AND
  autocorrelation, destroys alignment)**: mean −0.0543, [−0.804, +0.564], **0/200 ≥ real**.
- **static-exposure control**: mean position is −0.0263 (48% of anchors short, 42% long). A PERMANENT full-gross short
  of the same basket earns **−0.364 bps/anchor, Sharpe −0.112**; a permanent long +0.346 / +0.106. The 6.12 bps/anchor/
  gross cannot come from level exposure.
- **position-level IC vs the market**: k−2 0.0080, k−1 0.0213, **k0 0.0306**, k+1 0.0228, k+2 0.0197 — peak at 0, forward
  beats backward. PASSES (f).
- **dose response (gain on tanh(gain·z))**: 0.25 → +0.0712, 0.5 → +0.4892, 1.0 → +0.9765, 2.0 → +1.1339, 4.0 → +1.1825
  bps/anchor. Monotone and saturating. PASSES (g).
- **execution sensitivity** (EMA α, the deployed chain is 0.1): 0.1 → SR 1.319, 0.2 → 1.143, 0.3 → 1.074, 0.5 → 0.884,
  1.0 (no smoothing) → 0.827. The deployed chain is the BEST case; my construction did not handicap it.
- **years positive 5/5** in level — but **monotonically decaying**: 9.111 / 6.935 / 5.591 / 1.800 / 0.223.
- **sign instability, the mechanism problem**: the walk-forward sign is negative on 0.0% of 2022 anchors, 4.3% of 2023,
  16.2% of 2024, 25.7% of 2025 and **68.6% of 2026**. Under a FIXED +1 sign (diagnostic only — choosing it after seeing
  the walk-forward answer would be sign-mining) the yearly profile is 9.54 / 5.93 / 5.23 / 7.35 / **0.67** and full-cycle
  Sharpe 1.215, frozen −0.005. Either specification says the same thing: **the relationship inverted in 2026.**

**VERDICT REJECTED — and the rule, not my judgement, decides it.** It passes six of eight gates: (b) (c) (d) (e) (f) (g).
It fails (a): 1.319 < 1.50. It also fails (h): the in-book blend at w=0.10 is +0.1669 g CI95 [+0.057, +0.276] on the
full cycle but **BONF30 [−0.014, +0.335]**, and on the frozen window it is +0.0105 [−0.091, +0.113] — nothing where it
would have to work. My frozen NEAR_MISS clause reads "(a) in [1.20, 1.50) … **with everything else passing**", and (h)
does not pass, so the literal verdict is REJECTED. **I am reporting the rule defect rather than the favourable reading:**
requiring (h) of an arm that already fails (a) makes the NEAR_MISS category close to vacuous, because a sub-1.5 sleeve
will essentially never clear a Bonferroni-30 blend interval. Under the INTENT of that clause this is the family's
nearest miss. Under its LETTER it is rejected. Round 3 should fix the rule before it reuses it; it must not fix it
here, after the number.

### F4_XDISP_z180 — cross-sectional dispersion of trailing 24h returns as a market-timing signal (σ_XS over sel, panel row of E; z over 180; walk-forward sign)
Rejected on the frozen full-cycle rule but reported because **its time profile is the mirror image of F5's**:
| | full | frozen | 2024on | oof |
|---|---|---|---|---|
| Sharpe | 0.913 | **1.459** | 1.290 | −5.001 |
| net bps/anchor | +0.8035 | +0.6238 | +0.9818 | −2.916 |
| CI95 | [−0.020, +1.613] | [−0.158, +1.375] | [+0.138, +1.862] | [−7.479, +1.807] |
| CI BONF30 | [−0.491, +2.023] | [−0.544, +1.802] | [−0.476, +2.380] | [−10.49, +4.037] |
- by-year level 2.076 / 2.444 / 7.015 / 4.202 / 1.730 — **5/5 positive and still alive in 2026**, unlike F5.
- carry fraction 0.014 (pure price); ρA0 −0.078; mean position −0.0276.
- **fails (f) decisively at the POSITION level**: posIC vs the market k−2 **0.0509**, k−1 **0.0420**, k0 **0.0258**,
  k+1 0.0256, k+2 0.0176. The book it builds is more correlated with what has already happened than with what comes
  next — the same shape that killed round-1's TBF. Signal-level: ICk0 0.0464 vs ICk−1 0.0575, same direction.
- placebo A (permuted feature, 200 draws): mean −0.0447 [−0.320, +0.260], 0/200 ≥ real — clean.
  placebo B (circular shift through the operator, 200 draws): mean +0.0391 [−0.694, +0.735], **3/200 ≥ real,
  empirical p = 0.015** — passes at 5% but NOT at any Bonferroni level, and materially weaker than F5's 0/200.
- dose response +0.042 / +0.432 / +0.804 / +1.055 / +1.051 at gain 0.25 / 0.5 / 1 / 2 / 4 — monotone, saturating.
- full-cycle CI95 on the level [−0.029, +1.577] contains zero.
- exec sensitivity: α 0.1 → 0.913 full / 1.459 frozen; α 0.2 → **1.113 / 2.243**; α 0.3 → 0.938 / 2.050; α 1.0 → 0.719 / 1.959.
- in-book blend w=0.10 frozen: delta g **+0.1381 CI95 [+0.005, +0.281]**, base Sharpe 2.766 → **2.999**; BONF30 [−0.094, +0.345].
**VERDICT REJECTED** (full-cycle Sharpe 0.913 < 1.20, and ICk−1 > ICk0). It is the most interesting failure in the set
and the one I would re-open first if round 3 gets a longer high-dispersion sample.

## 4. The project's own clue, measured: F6 parabolic-onset continuation is EMPTY in backtest at v4 caliber
PREREG_crash_continuation_parabolic_stratum_2026-09-06 §1, tradeable 4h expression (AMENDMENT 3: no EMA, no band,
full round-trip cost, because the mechanism is a one-anchor event). 5m source = pinned holefix2 cache; trigger =
3-day gain ≥ +20% over the 864 bars ending at E AND the running cumulative 5m return inside [E−4h, E] reached ≤ −θ.
| θ | events/anchor | anchors with event | net bps/anchor (full) | Sharpe | CI95 | by-year level | carry frac |
|---|---|---|---|---|---|---|---|
| 5% | 1.189 | 4322 | −1.0143 | −0.435 | [−3.485, +1.259] | +27.97 / +14.57 / −60.30 / −13.48 / +6.44 | 1.291 |
| 8% | 0.484 | 2514 | −0.0175 | −0.010 | [−1.680, +1.543] | −29.91 / +54.62 / −70.39 / −3.21 / +16.38 | 46.5 |
| 12% | 0.199 | 1318 | +0.1231 | +0.103 | [−0.966, +1.179] | +97.23 / +30.34 / −113.81 / −17.23 / +26.46 | −3.624 |
All three CI95 contain zero; every yearly profile changes sign. **Mechanism of the failure, which is the useful part:**
the price P&L is POSITIVE at every θ (+0.637 / +0.958 / +0.637 bps/anchor) and the **carry bill eats it**
(+1.309 / +0.815 / +0.446). A name that has just fallen 5–12% intra-anchor carries a NEGATIVE funding rate — shorts
are already crowded — so shorting the continuation pays the funding, not receives it. Same shape as round-1's carry
verdict: the bill is the price of the trade. The forward gate (theta8 P layer 41/200) is untouched by this; this
closes only the BACKTEST side.

## 5. Other honest failures, each a real result
- **F4b dispersion → A0 gross scaling** (the one exposure-control arm in my K): base g +0.6804 → +0.5025,
  paired delta **−0.1779 CI95 [−0.186, −0.170]**, Sharpe 1.178 → 0.870, ρ to A0 +0.963. An INDEPENDENT signal
  reproducing round-1's 396-variant exposure-control refutation, with a tighter interval.
- **F1 TSMOM has no forward power at the 4h anchor**: ICk0 ≤ 0.0137 at every lookback while ICk−1 runs to 0.3561.
  The signal is a near-tautological function of its own recent past and knows nothing about the next 4h.
- **F2/F3 aggregate funding is the closed carry axis, not a new bet**: best Sharpe 0.231, and every arm with a
  positive level has carry fraction 0.436–1.595 — the net IS the carry. Consistent with
  `funding_transfer_priced_in_settlement_window` and round-1's carry verdict.
- **F7 breadth is anti-persistent**: the causal walk-forward sign rule picks the wrong sign consistently
  (Sharpe −0.217 / −0.383 / −0.396). Breadth's relation to the next 4h flips faster than a 720-anchor fit can track.
- **F8 beta rotation — the executor-legal expression — earns nothing** (|SR| ≤ 0.19 except breadth at −1.10),
  including for the two signals that DO work directionally. The timing value lives in net exposure.

## 6. The arithmetic, with the real correlations rather than the zero-correlation upper bound
Optimal (in-sample, therefore an UPPER BOUND) mean-variance combination, full cycle n=9918:
| combination | SR |
|---|---|
| XIB_LAG50 alone (my re-measurement: g +1.1633, ρ to A0 +0.8887) | **2.275** |
| + F5_VOLTS_6_42 (ρ −0.029) | 2.664 |
| + F4_XDISP_z180 (ρ −0.062) | 2.508 |
| + both (ρ between sleeves +0.137) | **2.804** |
| A0 alone | 1.316 |
| A0 + both | 2.077 |
Frozen window: XIB alone 3.880 → + both 4.288 (all of it from F4; F5 gets weight 0.032).
2024-on: XIB alone 3.197 → + both 3.652.
**Even granting in-sample-optimal weights and a sleeve that has stopped working, the full-cycle total is 2.80 — still
below 3.0, and 0.42 SE under it.** The goal is not reached by this family.

## 7. Multiplicity
K = 30 declared before any arm was measured (§4 of the PREREG + AMENDMENT 1). Bonferroni two-sided α = 0.05/30 =
0.001667, z = 3.14, bootstrap percentiles 0.0833 / 99.9167. **No arm's in-book blend delta survives BONF30 on any
window.** The two placebos are confirmatory and not counted in K. The fixed-sign variants in §3 are diagnostics
reported after the walk-forward answer was known and are explicitly NOT admissible arms.

## 8. Artifacts
- pod2 `/workspace/uplift_2026-09-11/r2_ts/` — `sleeve_core.py` (sha256 3bcbf7b8528d3cce…), `drive1.py` (26 arms),
  `drive3.py` (placebos/dose/static), `drive4.py` (exec sensitivity, in-book blend, portfolio), `drive5.py` (BONF30),
  `drive_f6.py` (parabolic + gross-scaling), `offcheck.py` (f_rev_24h offset spectrum), `diag.py`, `port3.py`,
  `gateP.sh`, `dev/` (my own symlink tree), `out/*.json`, `out/*.npz`, `logs/*`.
- repo `multi_asset/exports/research/uplift_2026-09-11/r2_timeseries/` — this file and the PREREG.
- Causality receipt: `f_rev_24h` offset spectrum peaks at shift 0 (corr 0.9686) against the trailing 6-anchor sum of
  y4; −1 0.8326, +1 0.7814. It is the strictly trailing 24h return, not a centred window (cf. the betaadj_ret24 leak).

## 9. F9 — funding-INTERVAL term structure (K extension to 34, declared after the first 30 were read)
`IVFRAC` = fraction of `sel` names the venue has moved to 1h/2h funding (`f_fund_iv ≤ 2`): mean 0.00496,
max 0.0828, non-zero on 30.7% of anchors. Full cycle n=9918:
| arm | SR full | lvl | SR frozen | SR 2024on | oof bps | ρA0 | CI95 full |
|---|---|---|---|---|---|---|---|
| F9_IVFRAC_z90 | −0.198 | −0.798 | 0.521 | 0.252 | −3.340 | — | — |
| F9_IVFRAC_z180 | −0.340 | −1.512 | −0.532 | −0.150 | −2.757 | — | — |
| F9_IVFRAC_z360 | −0.103 | −0.446 | −0.500 | 0.026 | −2.200 | — | — |
| F9d_IVTERM_XS (long iv=8 / short iv=4, dollar-neutral, executor-legal) | −0.015 | −0.045 | −0.627 | 0.093 | +2.249 | — | — |
**Zero admissions.** The venue's funding-interval structure carries no tradeable signal in either the time-series
or the cross-sectional expression. (Sharpes are reported on the same allocated-budget convention; full detail in
`out/r2ts_f9.json`.)

## 10. What round 3 should take from this, and what it should not
1. **Do not re-run this family.** 34 arms across trend, aggregate funding level, funding surprise, funding-interval
   term structure, cross-sectional dispersion, vol term structure, breadth, beta rotation and the parabolic-onset
   event stratum produced zero admissions. The best arm is at 1.32 ± 0.47 with a monotone decay to zero and a
   negative out-of-fit window. New evidence required to reopen: a materially longer high-dispersion sample, or a
   data source this panel does not carry (spot-perp basis, options-implied vol, venue open interest).
2. **The orthogonality result is worth keeping even though the returns are not.** |ρ to A0| ≤ 0.111 across all 34
   arms is the strongest decorrelation any round has measured. If a time-series signal with real forward power is
   ever found, the diversification arithmetic will be close to the theoretical upper bound. The bottleneck is the
   signal, not the correlation.
3. **The architectural constraint is the deeper finding and it is cheap to check before building anything.**
   The executor re-demeans the non-zero set, so net exposure cannot be held. Round 3 should decide FIRST whether a
   directional sleeve is even on the table — that is a book-behaviour change requiring pre-registration and a user
   ruling — before spending compute on directional backtests. As measured here, the executor-legal expression
   (dollar-neutral beta rotation) of every timing signal earns |Sharpe| ≤ 0.19.
4. **Fix gate (h) before reusing the rule.** Requiring a Bonferroni-K in-book blend interval of an arm that already
   fails the standalone bar makes NEAR_MISS vacuous. Either drop (h) from NEAR_MISS or state the two verdicts
   separately. Do it in the next PREREG, never in the next RESULT.
5. **The gap to the goal is not closed and this family cannot close it.** With in-sample-optimal weights — an upper
   bound — XIB_LAG50 + both best sleeves reaches 2.804 on the full cycle against a 3.0 target and an SE of 0.47.
   The arithmetic in the brief asked for a sleeve of standalone Sharpe ≈ 1.83 at zero correlation; the best this
   family offers is 1.32 at ρ = −0.03, and that one has stopped working.

## 11. Placebo gradient across the four attacked arms — the cleanest single diagnostic in this round
Placebo B is a circular shift of the raw feature through the identical operator: it preserves the feature's marginal
distribution AND its autocorrelation and destroys only its alignment with the market. `frac_ge_real` = share of 200
draws that matched or beat the real arm, i.e. an empirical p-value.
| arm | SR full | placebo A (permuted feature) frac≥real | **placebo B (circular shift) frac≥real** | posIC k0 | posIC k−1 | posIC k−2 |
|---|---|---|---|---|---|---|
| F5_VOLTS_6_42 | 1.319 | 0.000 | **0.000** | **0.0306** | 0.0213 | 0.0080 |
| F4_XDISP_z180 | 0.913 | 0.000 | 0.015 | 0.0258 | 0.0420 | **0.0509** |
| F5_VOLTS_12_90 | 0.607 | 0.000 | 0.095 | 0.0179 | **0.0245** | 0.0067 |
| F4_XDISP_z360 | 0.390 | 0.005 | **0.225** | 0.0280 | 0.0483 | **0.0613** |
The placebo p-value tracks the standalone Sharpe monotonically, and **only F5_VOLTS_6_42 has a position whose IC peaks
at k = 0.** Every dispersion arm's book is more correlated with the two anchors that already happened than with the
next one. The permuted-feature placebo (A) passes everything — it shreds the autocorrelation and so charges every draw
a cost penalty; **placebo B is the one that discriminates**, and round 3 should use it as the default TS placebo.
Dose responses, for the record: F4_XDISP_z360 is NOT monotone (−0.040 / +0.101 / +0.339 / +0.341 / +0.350 — flat past
gain 1); F5_VOLTS_12_90 is monotone but only reaches Sharpe 0.952 at gain 4.
