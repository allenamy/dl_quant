> **创建:** 2026-07-08 · **修订:** 2026-07-10 (full-history replay reversed the Book-1 headline — see §0) · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** revised · **作废条件:** book factors retrained / universe or horizon change / a new factory-ACCEPT factor added.

# Multi-asset v2 — portfolio scorecard (consolidation deliverable)

**Portfolio = two orthogonal books.** Book-1 (mega-cap core) + Book-2 (wide breadth, small-capacity diversifier). Everything net-of-cost, honest raw-y, walk-forward OOS. Tools: `multi_asset/eval/{factor_scorer,factor_pipeline,ls_gate,gbdt_probe,portfolio_scorecard,m0_replay_score,m0_persistence_diag}.py`.

## §0. ★ HEADLINE CORRECTION (2026-07-10, full-history replay, two-person confirmed) — the blend does NOT generalize

The original Book-1 headline (funding+M0 equal-risk blend, net-Sh 3.9–4.56) was a **2025-favorable-window result**. The full-history walk-forward replay (M0 retrained per year on prior data only, tested 2023/2024/2025; independently confirmed on two harnesses — 0C `m0_replay_score.py` + 0B `backtest_longshort`) shows:

- **M0 is net-cost tradeable ONLY in 2025.** Its rank-IC is genuinely regime-robust (+0.043/+0.033/+0.033, z 11–15 every year), but its **prediction persistence is regime-dependent** (weight-autocorr 0.27/0.18/0.51) — in 2023/24 the signal is fast/one-period, so under EMA-hold gross-Sharpe goes negative and turnover cost kills it (break-even <1 bps).
- **The equal-risk blend is dominated by funding-alone in all three years** — M0's 2023/24 turnover drag pulls the blend below funding.
- **funding_ema is the robust net-cost core** — deployable (EMA-hold) net-Sh@5bps positive every year. Its megacap-replay "2024 loss (−1.52)" was a **fixed-turnover caliber artifact**: funding's 0.98 persistence means EMA-hold rescues 2024 to +0.82 (full-rebalance −0.99).

**Deliverable conclusion (revised): Book-1's deployable core is funding_ema ALONE.** M0 is a real signal (IC-robust) but a **2025-window-conditional booster**, not a multi-year-additive leg. **New tradability KPI: prediction persistence (weight-autocorr) alongside IC** — a factor can be IC-robust yet net-cost-fragile if its signal is fast. Net-cost + persistence, not IC, is the gate. M0's highest-value fix = a **turnover-regularized loss** that trains for persistence (its flaw is intrinsic signal speed, a training-target problem — distinct from a cost-accounting problem). **[That fix was subsequently built and tested — see the CLOSING WORD subsection below: mechanism confirmed trainable, but insufficient to make M0 a standalone multi-year leg.]**

### Book-1 honest multi-year table (walk-forward, EMA-hold deployable, net-Sh@5bps; two-harness confirmed)
| test year | train | M0 rank-IC (z) | M0 persistence | M0 net-Sh@5 | funding net-Sh@5 | blend net-Sh@5 |
|---|---|---|---|---|---|---|
| 2023 | 2022 (1yr) | +0.043 (z15) | 0.27 | −2.1 | **+0.59** | −0.36 |
| 2024 | 2022-23 (2yr) | +0.033 (z11) | 0.18 | −1.7 | **+0.82** | −0.85 |
| 2025 | 2022-24 (3yr) | +0.033 (z12) | 0.51 | +1.2 | **+2.17** | +1.93 |

(EMA-hold α0.02 = the deployable operating point; a full-turnover convention reads M0 2023/24 at −22/−23, but you cannot profitably hold a persistence-0.18 signal at any α — both operating points are net-negative. funding weight-autocorr 0.97–0.99 all years. Single-seed-42; 3-seed ensemble confirm recommended, but the persistence mechanism is structural.)

### ★ CLOSING WORD on the DL-leg (M0 rescue arc, 2026-07-11) — both rescue paths tested
Two independent rescue paths were run against M0's fast-signal defect. **Usage-layer** (tail-gate / funding-filter / rebalance-timing, `m0_usage_sweep.py`): ALL 14 variants REJECT — no way to *trade* a one-period signal net-cost-positive (`m0_usage_sweep`). **Training-side** (Δpred-penalty persistence loss, P1b, λ-ladder 0.1→0.3, `p1b_verdict.py`): the terminal three-way read —

| | M0 | P1b λ0.1 | P1b λ0.3 |
|---|---|---|---|
| persistence 2023 / 2024 / 2025 | 0.26 / 0.18 / 0.51 | 0.47 / 0.37 / 0.38 | 0.46 / **0.65** / **0.77** |
| net-Sh@5 2023 / 2024 / 2025 | −2.1 / −1.8 / +1.4 | −1.5 / −0.0 / +0.9 | −1.6 / −0.2 / **+1.8** |

1. **M0-standalone-multi-year = CLOSED NEGATIVE.** 2023-type immature/chop regimes are untradeable at *any* dose — 2023 persistence stalls at 0.46 (<0.5) and net-cost at −1.6; the dosing window is capped by the 2023 IC boundary (already −20% at λ0.3) + σ compression (0.012–0.019). Net-cost never reaches ≥2/3 positive.
2. **The persistence mechanism = CONFIRMED TRAINABLE** — the arc's lasting methodological win. The Δpred penalty makes the DL signal holdable (2024 0.18→0.65, 2025 0.51→0.77 clear 0.5) *without* cratering the good year (2025 net-Sh 1.4→1.8, IC preserved) — validating "regularize away unholdable fast noise." Persistence is now a trainable objective, not just a diagnostic KPI.
3. **★ The conditional-booster of record is now P1b_lambda03, not original M0** — it strictly improves the 2025-regime booster (net-Sh 1.37→1.84, persistence 0.77). If the DL booster is ever deployed in a 2025-like (holdable) regime, use `P1b_lambda03`.
4. **★ UNSOLVED — the activation condition.** How to know *ex-ante* that we're in a "holdable" regime is not solved. A causal persistence-regime detector would be required before any conditional deployment of the booster; without it, the DL leg stays **PARKED** *at taker economics*. Deployable core is unchanged and complete without it: funding_ema + EMA-hold + vol-target. **(This "parked" is revised by the execution-economics addendum below — the DL leg is execution-gated, not unconditionally dead.)**

### ★★ EXECUTION-ECONOMICS ADDENDUM (2026-07-11) — the verdicts were TAKER-conditional; the DL leg is EXECUTION-GATED, not dead
The "not tradeable" calls above assumed taker economics (1.7–5 bps/side). Top props execute maker/rebate (~0.2–1 bps effective). Re-scored on a prop-grade cost grid (`execution_economics.py`) with the **cost-optimal operating point** (at cheap cost it flips from EMA-hold to full-turnover — you rebalance fully to capture the fast signal when churn is cheap):

| candidate | net-Sh @ 0.2 / 0.5 / 1.0 / 1.7 bps (2023) | (2024) | (2025) | tradeable below |
|---|---|---|---|---|
| **M0** | +2.87 / +1.26 / −0.93 / −1.42 | +0.37 / −0.99 / −1.08 / −1.20 | +1.79 / +1.76 / +1.72 / +1.66 | 2023 ≤0.5, 2024 ≤0.2, 2025 ≤1.7+ |
| **λ0.3-M0** | +0.67 / −0.59 / … | +0.26 / +0.08 / +0.05 / +0.01 | +2.34 / … / +1.99 | 2023 ≤0.2, 2024 ≤1.7, 2025 ≤1.7+ |
| **funding** | +1.50 / +1.43 / +1.32 / +1.16 | +1.16 / … / +1.06 | +3.57 / … / +3.16 | ALL ≤1.7+ (robust) |
| 3-seed ensemble (2025) | +5.24 / +4.09 / +3.41 / +3.33 | — | — | ≤1.7+ (de-noised) |
| fast-micro baseline (2025) | +1.30 / −0.58 / −1.97 / −2.33 | — | — | ≤~0.4 (sub-BE) |
| **★ 0B fill-sim (data-supported effective cost @ M0 actual churn)** | **≈0 @k=60** (+0.05/−0.07/+0.17); −0.44/−0.32/−0.12 @k=180 patient | (funding: +0.20/+0.08/+0.02 @k=60; −0.24/−0.15/−0.30 @k=180) | | **≈0–0.2 bps realistic, « taker 1.7** |

- **★ Reframe (official record): the M0/DL-leg is EXECUTION-GATED — dead at taker (1.7–5 bps), tradeable at maker/rebate (≤0.5 bps) IF fills hold at high turnover.** At ≤0.2 bps M0 is net-positive all three years (the fast 2023 signal taker-cost killed is its *strongest*, +2.87); funding is fatter and positive at every tier.
- **Execution capability picks the variant:** at ULTRA-low cost (0.2 bps, full-churn) **original M0** wins (2023 +2.87 fast-capture); at moderate cost (0.5–1.7) **λ0.3-M0** wins (2024 holds positive to 1.7 via persistence — the penalty is the "cost-tolerance" version). The persistence penalty and cheap execution are substitute levers for the same defect.
- **Netting is NOT a lever here:** funding + λ0.3-M0 as one book nets out only **3–5%** of turnover (funding trades too rarely — turnover 0.08–0.13 vs M0's 1.1–1.8 — to offset M0's flips). Netting becomes a lever only with *many uncorrelated fast alphas*, not a 2-signal book.
- **Execution-feasibility context (research memo):** top-tier maker fee ≈ **0.0%** (effective cost is adverse selection, not fees); adverse selection lives at **5s–5min** vs our **~60min** alpha horizon (our edge outlives the microstructure window — favorable); a proper execution scheduler retains **~75–90%** of the alpha; and **N=14 breadth is the binding constraint** — even execution-gated-alive, the book is Sharpe ~1–1.5 without a breadth cushion. So the "IF fills hold" is *plausible for a top desk* (alpha outlives adverse selection, high retention), and the real ceiling becomes breadth, not cost.
- **★ Fill-sim confirmation (0B `makerfill_sim.py`, 0C two-person cross-checked):** simulating M0's *actual* rebalance orders worked passively at the touch from the 1s book/flow (conservative queue-join-at-back, cancels-ahead excluded) gives a data-supported effective cost of **≈0 bps at a realistic k=60s working horizon** (M0 +0.05/−0.07/+0.17 per year; funding +0.20/+0.08/+0.02) — i.e. spread capture ≈ adverse selection, **far below taker 1.7 (8–30×), so execution-open is CONFIRMED.** Three honesty caveats from the cross-check: (1) the cost is **k-dependent** — it only goes net-*negative* (M0 −0.44/−0.32/−0.12) at a patient k=180s working horizon (the most-favorable k in the sweep), so we headline the conservative near-zero, not "paid to trade"; (2) the negative-mean regime sits on **fat adverse markout tails** (p10 −8 to −19 bps) — a real silent-bleed risk, so a −0.15 mean is not a robust −0.15 cost; (3) the average is unweighted-over-14-assets and the sub-taker cost is driven by the **wide-spread alts** (fil/xrp/link, half-spread 1–1.9 bps → spread to capture) which also carry the fattest tails, while mega-caps (btc/eth, half-spread ~0.02) net ~zero. Net: **effective cost is near-zero and robustly sub-taker at realistic execution; the "net-negative / paid-to-trade" version requires patient (180s) working and is tail-fragile.** This closes the operative open cell — the execution-gated conclusion is data-supported, not just theoretical.
- **k-sensitivity table (the caveat, made explicit) — effective cost bps/side by passive working horizon k:**

  | k (sec) | M0 (2023/24/25) | funding (2023/24/25) | read |
  |---|---|---|---|
  | 30 | +0.48 / +0.22 / +0.40 | +0.64 / +0.34 / +0.25 | positive (short working = little spread captured) |
  | **60 (realistic headline)** | **+0.05 / −0.07 / +0.17** | **+0.20 / +0.08 / +0.02** | **≈0 — the conservative deployable number** |
  | 180 (patient upside) | −0.44 / −0.32 / −0.12 | −0.24 / −0.15 / −0.30 | net-negative but most-favorable k + fat tails |

  The whole "you get paid to trade" claim lives only in the k=180 row, and that row sits on markout p10 −8 to −19 bps. Headline = the k=60 ≈0 (robustly sub-taker); k=180 is labeled patient-execution upside, not the base case. (Full per-asset × per-year × k detail + markout p10/p90 in `/tmp/makerfill_full.log`; `makerfill_sim.py` committed 1682b1b.)

**★ Phase conclusion, corrected final record:** not "factor space exhausted" but **"a signal portfolio priced by execution capability."** funding_ema + EMA-hold + vol-target is the taker-robust deployable core (any execution); the DL leg (M0 / λ0.3-M0) is an execution-gated add-on that a maker/rebate desk can trade on the shelved years; breadth (N=14) is the remaining binding constraint on total Sharpe.

## Executive summary (of the detailed sections below)
- **Book-1 deployable core = funding_ema alone** (see §0): crowding-reversion, EMA-persistent (latency-flat), net-cost-positive every test year 2023-25. The §"Book-1 scorecard" table below is the **2025-window (fold-C) detail** — real, but the favorable window; read it with §0.
- **M0 DL factor** — real, IC-robust, leak-audit-clean; taker-tradeable only in 2025, but **EXECUTION-GATED not dead** (see §0 execution-economics addendum): at maker/rebate ≤0.5 bps it flips net-positive on the shelved years (2023/24). Rescue arc CLOSED at taker economics (both usage-layer + training-side fixes tested); an execution-gated add-on for a maker/rebate desk; λ0.3-trained version of record; conditional-deploy still needs a causal persistence-regime detector.
- **Book-2 = wide SIZE-premium sleeve**: cost-immune (net-Sharpe 2.11, turnover 0.0018) but capacity-capped (~$2.5M illiq ADV). A real diversifier, not scalable.
- The whole tabular/library/DL-multi-head factor space beyond these was exhaustively tested and correctly rejected by the 5-gate factory.

## Book-1 scorecard — 2025-WINDOW detail (mega-cap, 14 USDT-perp, 1h)
> ★ This table is the **2025 favorable-window** measurement (the original headline). It is superseded as the deliverable headline by §0's multi-year table — M0's strength here is 2025-specific. Kept for the 2025-window detail (funding numbers here are consistent with the multi-year result; the blend numbers do NOT generalize). Note: the "operating turnover = best-break-even EMA alpha" convention below over-credits unprofitable fast signals (picks full-turnover) — the deployable point is net-Sh-optimal EMA-hold (see §0); it matters only off-2025.

Walk-forward OOS ~2025-02..2025-09 (3 disjoint folds). Operating turnover = best-break-even EMA alpha. Cost = 2 bps/side (mega-cap taker-realistic).

| metric | funding_ema | M0 DL | **BLEND (equal-risk)** |
|---|---|---|---|
| rank-IC (per-ts) | +0.0186 | +0.0355 | **+0.0393** |
| break-even /side | 18.8 bps | 33.6 bps | **41.4 bps** |
| net-Sharpe @2bps | 2.08 | 4.15 | **4.56** |
| net-Sharpe @5bps (stressed) | 1.71 | 3.75 | **4.21** |
| net-Sharpe @10bps (stressed) | 1.09 | 3.10 | **3.63** |
| gross-Sharpe (0-cost) | 2.33 | 4.41 | 4.79 |
| operating turnover | 0.027 | 0.031 | 0.029 |
| net ann @2bps | +4,021 bps | +8,622 bps | **+9,965 bps** |
| per-fold net-Sharpe | [0.75, 7.2, −0.22] | [5.15, 6.21, 1.11] | **[3.7, 8.82, 1.2]** |
| months net-positive | 4/7 | 5/7 | **5/7** |
| max drawdown | −920 bps | −568 bps | −864 bps |
| latency decay (0/180/360s) | 1.0 / 1.0 / 1.0 | 1.0 / 0.67 / 0.67 | **1.0 / 1.0 / 1.0** |

- **In the 2025 window the blend is the best line** — net-Sharpe 4.56 > either factor here. ★ But this does NOT generalize (§0): on the full-history walk-forward the blend is dominated by funding-alone every year, because M0's 2023/24 fast-signal turnover drag contaminates the equal-risk mix. Read this line as a 2025-window property, not a deployable multi-year expectation.
- **Stressed-cost robustness:** the blend holds net-Sharpe 4.21 @5 bps/side and 3.63 @10 bps/side — even at a punitive 10 bps it's strongly net-positive. Funding alone weakens (2.08→1.09) but stays positive; M0 and the blend are cost-robust.
- **Weighting sensitivity (headline = equal-risk):** an IC-weighted blend gives net-Sharpe 4.61 @2bps (BE 41.8) — only marginally above equal-risk's 4.56. Since the IC weights would be fitted on the ~7-month OOS (overfit risk) for a trivial gain, **equal-risk is the headline**; IC-weighting is reported only as this sensitivity check (the result is robust to the weighting choice).
- **funding_ema** — the crowding-reversion core: 2h is even stronger (BE 33.8, net-Sh higher — see the 2h reference below); latency-flat; regime-dependent magnitude (fold-2 weak) but all-fold-positive in the blend.
- **M0 DL factor** — the raw-sequence Conformer factor (funding-residual target): highest single-factor net-Sharpe (4.15), all-fold positive, quantile-mono +1.0; slightly faster (latency 0.67 at 3-6min) but still tradeable. Leak-audit PASSED (6 checks, IC independently reproduced).
- **funding at 2h (primary-horizon reference):** BE 33.8 bps/side, net-Sharpe positive at every cost tier incl. 10 bps, mono +0.70, latency-flat. Funding predicts better at 2h (8h-stamped). NOTE: M0 is 1h-trained, so the 2-factor BLEND is reported at 1h; a 2h blend needs M0 retrained at 2h.

## Book-2 scorecard (wide, 110 point-in-time USDT-perp, 1h; 0B's ledger, 0C cross-checked)
Per-coin cost by DVOL tercile (2/5/10 bps base) + stress to 50 bps illiq; causal point-in-time MEMBER mask.

| cluster | net-Sharpe (base) | turnover | break-even | cost robustness | verdict |
|---|---|---|---|---|---|
| **SIZE** | **2.11** | 0.0018 | 219 bps | **cost-IMMUNE (net-Sh 1.96 @50bps illiq)** | the deployable piece |
| low-vol | 0.97 | 0.094 | 9.4 bps | breaks ~22 bps illiq | conditional-on-cost |
| COMBINED slow | 1.41 | 0.078 | 12 bps | marginal (0.71@20, 0.02@30 bps illiq) | marginal at realistic cost |
| fast (reversal, price-vol) | — | high | 0.6-1.4 bps | dies (cost trap) | REJECT |

- **SIZE is the robust deployable Book-2 factor** (turnover 0.0018 → barely trades → cost-immune). Fast reversal / price-vol clusters die to the cost trap (consistent with their mega-cap factory gate-d rejects).
- **Capacity caveat (load-bearing):** the SIZE/low-vol signal lives in the illiquid tercile (median daily ~$2.5M ADV); a 5-10% ADV cap bounds the sleeve to single-digit-% of that → **small-capacity**. Real diversifier, not scalable.

## Cross-book correlation (the diversification claim) — CONFIRMED ~0
Book-1 (mega-cap funding+M0) and Book-2 (wide SIZE) are on DISJOINT universes with orthogonal mechanisms (crowding-reversion ⊥ size-premium). Empirical hourly-aligned return correlation (n=2,640 common hours, 0B's Book-2 return series):
- **Book-1(blend) ↔ Book-2(SIZE): +0.088**
- **Book-1(blend) ↔ Book-2(COMBINED-slow): +0.075**

Both **near-zero** → the diversification claim holds. Combining the two books is genuinely diversifying (a ~0-correlation return stream added to the core), so the portfolio Sharpe exceeds either book alone at the same gross exposure. This is the payoff of the two-disjoint-universe design.

## M0 leak-audit — PASSED (6/6, 0B, independently cross-checked)
M0's z-7 result was belt-and-suspanders leak-audited (the standard for a strong DL result after a uniformly-null tabular space): (1) input windows end at the decision bar t, no future bars; (2) causal residualization (y forward [t,t+3600]; funding ffill≤t); (3) per-fold normalization fit on TRAIN rows only; (4) test disjoint with a 22-day train→test boundary gap ≫ horizon + embargo. Plus caliber-parity: M0's IC independently recomputed on a fresh ≥3600 non-overlap grid = **+0.0355, matching gate-a exactly** (not overlap-inflated). A dense-CL export landmine was caught + fixed (scored on the canonical ≥3600 CL, so the ACCEPT stands). **z7 is real, not a leak artifact. M0 is FINAL.**

## M0 seed-stability (3 seeds: orig + s43 + s44) — IC-robust; net-Sh reported as seed-median
Closes the single-seed limit. (1) **Standalone rank-IC is seed-robust:** +0.0355 / +0.0353 / +0.0380 (mean +0.0363, std 0.0012) — all three seeds land at ~0.036, the signal is not a per-seed fluke. (2) **Same signal:** cross-seed pred correlation 0.70 / 0.75 / 0.78 — the seeds find the same factor (not identical, DL stochasticity, but clearly one underlying signal). (3) **Blend net-Sharpe is seed-DEPENDENT in magnitude:** @2bps 4.56 (orig) / 3.43 (s43) / 3.83 (s44) → **seed-median 3.83, range [3.43, 4.56]**, all-fold positive every seed, BE 34–41 bps/side. The original seed's 4.56 was the TOP of the band. **★ Honest headline = the seed-MEDIAN 3.83, not the lucky single seed** (the tables above show the orig-seed run; discount to ~3.8 for the deployable expectation). (4) **★ 3-SEED ENSEMBLE = the production config (verified):** averaging the 3 seed preds → M0 IC 0.0386, blend **net-Sh@2bps 3.92** (BE 41, @5/@10 3.62/3.11), all-fold positive [2.74, 8.69, 1.02], **6/7 months net-positive** — ABOVE the single-seed median (3.83) and MORE stable month-to-month than any single seed (6/7 vs 5/7). Ensembling both de-noises and lifts, as expected from the 0.70-0.78 cross-corr.

Verdict: **IC seed-robust + same-signal; net-cost tradeable every seed. The DEPLOYABLE config is the 3-seed ENSEMBLE: net-Sh 3.92, BE 41, 6/7 months positive, all-fold positive** — strictly better and more stable than any single seed. Headline the ensemble 3.92 (or the median 3.83 for single-model); NOT the lucky orig-seed 4.56.

## ★ funding_ema full-history regime-robustness (2020→2026, 0B replay, 0C cross-checked) — NOT all-weather
The scorecard's ~7-month window (2025-02..09) turns out to be a FAVORABLE one. Full-history per-year (1h; 2h mirrors it):

| year | rank-IC | z | gross-Sh | net-Sh | note |
|---|---|---|---|---|---|
| 2020 | ~0 | −0.03 | — | −0.33 | null (early perp market) |
| 2021 | +0.018 | 2.26 | +0.99 | +0.83 | positive |
| 2022 | +0.007 | 1.38 | −0.21 | −0.45 | weak/negative (bear) |
| 2023 | +0.006 | 1.61 | +1.26 | +0.91 | positive |
| **2024** | **+0.014** | **5.64** | **−1.11** | **−1.52** | **★ IC-strong but NET-NEGATIVE** |
| 2025 | +0.015 | 3.31 | +3.30 | +2.87 | best year (our window) |
| 2026 | +0.014 | 3.19 | +2.26 | +1.62 | positive (partial) |

- **Long-run net-Sharpe ≈ +0.56 (all years) / +0.71 (excl. 2020), median +0.83, range [−1.52, +2.87].** Funding_ema is **NOT all-weather** — it has genuine LOSING years (2020, 2022, 2024) and strong years (2021/23/25/26). The 4.56/3.92 scorecard headline sits on 2025, the single best year.
- **★ 2024 is the rank-right/magnitude-wrong signature, and it's REAL (not a harness artifact):** strongest IC (z 5.64) yet gross-Sh −1.11 (negative even at ZERO cost, so not a cost/turnover effect). The crowding-reversion ranked correctly on typical moves but LOST on the big moves — in a persistent-crowding/trending year the extreme moves run with the crowd before reverting. This is the factor's core risk: correct ordering ≠ profitable when the tails go the wrong way. Audited: arithmetic internally consistent (BE/gross/net signs, cost drag), and the pattern is HORIZON-ROBUST (2h: 2024 −1.61, 2025 +2.69).
  - **★ 2024 per-period characterization (0B series, 0C cross-checked, 8,784 hourly obs):** the loss is **BOTH tail-concentrated AND broadly mildly-negative**. Tail: the **worst 5 days = −0.186 = 81% of the year's net gross-sum (−0.232)** — i.e. the *net* annual loss is dominated by a handful of catastrophic days (2024-12-03 −7.3%, 2024-03-02, 2024-01-10, 2024-11-15, 2024-02-19), all high-|move| days where crowded-funding coins continued instead of reverting. Broad base: **hourly win-rate 0.493, daily 0.459, months 5/12 positive** — a persistent mild negative drift underneath the tails. So the read is *not* "one freak day" and *not* "uniformly rank-wrong": the ranking is genuinely right (IC +0.0137 z5.64) but the dollar-weighted book loses because (a) a small persistent bias and (b) a few extreme days where the reversion thesis failed hardest. Deployment implication: a per-day exposure cap / vol-target / tail-de-risk overlay could have salvaged 2024 to roughly break-even, but NOT made it a winner (the ~50/50 broad base remains) — this is a risk-overlay note, not an alpha claim. The gross-negative verdict is unchanged.
- Cross-check vs the scorecard: my 2025-02..09 funding net-Sh 2.08 is consistent with (and slightly below) the replay's full-2025 +2.87 — my window included the weak 2025-09. Turnover note: the replay runs higher turnover (0.044–0.068) than the scorecard's operating alpha (0.027), so the replay net-Sh is a conservative (higher-cost) estimate; the regime pattern holds regardless.
- **★ TURNOVER-CALIBER RECONCILIATION (2026-07-10):** this per-year table is the **fixed/higher-turnover** megacap caliber. On the **deployable EMA-hold (low-turnover)** caliber — the way you'd actually trade a 0.98-persistence factor — funding 2024 flips to **+0.82** (full-rebalance −0.99 ≈ this table's −1.52) and funding is net-positive all of 2023-25 (see §0). So funding's "losing years" here are partly a fixed-turnover artifact; funding pays when HELD. (2020/21/22 not re-checkable on the seq-grid — bar_1s starts 2022.) The honest read: funding is direction-robust + magnitude-regime-dependent, deployable EMA-held.
- **Implication for the deliverable (revised):** ★ M0 is NOT the stronger/more-consistent factor — the full-history replay reversed that (§0). **funding_ema alone is the robust core**; M0 helps only in 2025. Report Book-1's deployable expectation as **funding-alone, ~+0.6–2 net-Sh regime-dependent**, not the retired blend headline.

## Honest limits (revised 2026-07-10)
1. **★ M0 DOES NOT GENERALIZE — the single most important finding (§0).** M0's net-cost edge is 2025-window-only; in 2023/24 it's net-negative and drags the blend. Root cause = regime-dependent prediction persistence (weight-autocorr 0.18–0.51). The prior "blend net-Sh 3.9–4.56" is RETIRED as a deployable headline. Deployable Book-1 = funding_ema alone.
2. **funding is the robust leg, but regime-dependent in MAGNITUDE + turnover-caliber-sensitive.** Direction is stable (crowding-reversion every fold); strength varies by regime. On the deployable EMA-hold caliber it's net-positive 2023-25; but the megacap FIXED-TURNOVER replay shows losing years (2020/22/24 at high turnover) — funding pays only when held (its 0.98 persistence is the whole point). Size to ~+0.6–2 net-Sh, deploy EMA-held.
3. **2025-09 correlated drawdown (2025-window observation):** both Book-1 factors were net-negative that month simultaneously (funding −365 bps, M0 −182) — even in the good year the two didn't hedge. Now secondary to limit #1, but a live joint-drawdown caution for any funding+M0 combination.
4. **M0 single-seed-42 in the replay:** the net-Sh magnitudes have seed variance; the 3-seed ensemble confirm is recommended before any M0 re-admission. (The persistence mechanism is structural, so the qualitative 2025-only finding is unlikely to flip.)
5. **Book-2 capacity:** single-digit-% of $2.5M illiq ADV — a small sleeve; its diversification of Book-1 is a same-timestamp ~0 correlation, not a hedge in a joint crypto-wide risk-off.
6. **New tradability KPI carried forward:** prediction persistence (weight-autocorr) is now scored alongside IC for every factor — M0 taught us an IC-robust factor can be net-cost-fragile if its signal is fast. Net-cost + persistence, not IC, is the gate.

## Deployment read (revised 2026-07-10 — see §0)
Deploy **Book-1 = funding_ema ALONE as the scalable core** — the only multi-year-robust net-cost factor: deployable (EMA-hold) net-Sh@5bps positive every test year (2023 +0.59 / 2024 +0.82 / 2025 +2.17), crowding-reversion, latency-flat, EMA-persistent (weight-autocorr 0.98). 2h primary (funding is 8h-stamped, stronger at 2h). **Do NOT deploy the funding+M0 blend as a multi-year config** — the blend is 2025-window-only (M0 drags it in 2023/24). **M0 is parked as a 2025-conditional booster**: real IC (regime-robust) but net-cost-tradeable only in a persistent regime; re-admit it to the book only after (a) the turnover-regularized-loss fix restores persistence off-2025, and (b) a 3-seed ensemble confirm. Add **Book-2 SIZE** as a small, capacity-capped diversifying sleeve (cross-book corr ~0). Everything else in the factor space (positioning, order-flow, semivar, price-vol on mega-caps, GBDT over all tabular features, 5 stage-2b DL heads) was exhaustively tested by the 5-gate factory and correctly rejected. Production caveats: funding is regime-dependent in MAGNITUDE (direction stable, strength varies) — size to ~+0.6-2 net-Sh not the 2025 peak; the megacap fixed-turnover replay shows funding can lose at high turnover, so deploy EMA-held (low-turnover) where its persistence pays; Book-2 small capacity.
