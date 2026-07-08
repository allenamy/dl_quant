> **创建:** 2026-07-08 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** final · **作废条件:** book factors retrained / universe or horizon change / a new factory-ACCEPT factor added.

# Multi-asset v2 — FINAL portfolio scorecard (consolidation deliverable)

**Portfolio = two orthogonal books.** Book-1 (mega-cap, the scalable core) + Book-2 (wide breadth, small-capacity diversifier). Everything net-of-cost, honest raw-y, walk-forward OOS. Tools: `multi_asset/eval/{factor_scorer,factor_pipeline,ls_gate,gbdt_probe,portfolio_scorecard}.py`.

## Executive summary
- **Book-1 = funding_ema + M0 DL factor**, equal-risk z-blend: **net-Sharpe@2bps seed-median 3.83 (range 3.43–4.56 across 3 M0 seeds; orig-seed 4.56), break-even 34–41 bps/side, all-fold positive across all seeds, latency-flat, 5/7 months net-positive.** Two orthogonal (corr 0.107) net-cost-additive factors; the blend beats either alone. M0's IC is seed-robust (0.036, std 0.0012); its net-Sh has a seed band → headline the median 3.83, ensemble the seeds in production. **This is the deliverable's core.**
- **Book-2 = wide SIZE-premium sleeve**: cost-immune (net-Sharpe 2.11, turnover 0.0018) but capacity-capped (~$2.5M illiq ADV → single-digit-% deployable). A real diversifier, not scalable.
- Both are net-cost-tradeable; the whole tabular/library/DL-multi-head factor space beyond these was exhaustively tested and correctly rejected by the 5-gate factory.

## Book-1 scorecard (mega-cap, 14 USDT-perp, 1h; funding also validated at 2h)
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

- **The blend is the best line** — net-Sharpe 4.56 > either factor, all-fold positive (funding's weak fold-2 −0.22 is rescued by M0), latency-flat (funding's flatness stabilizes M0's mild 0.67 decay). Break-even 41 bps/side clears any realistic mega-cap taker cost (~2-5 bps) by ~8-20×.
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

## Honest limits
1. **★ CORRELATED DRAWDOWN — the single most important sizing fact.** 2025-09 is net-NEGATIVE for BOTH Book-1 factors simultaneously (funding −365 bps AND M0 −182 → blend −371). The intra-book diversification is PARTIAL (funding↔M0 corr 0.107) — the two factors CAN and DID draw down together in an adverse month. Size the book for a joint-drawdown regime, not for the average-month Sharpe; the 4.56 headline Sharpe does not imply the factors hedge each other.
2. **Short OOS window** (~7 months, 2025-02..2025-09). All stability numbers are on a small sample; not multi-year — the strongest caveat on every Sharpe here.
3. **funding regime-dependence:** magnitude is fold/regime-dependent (strong 2025-06 +740, weak/negative fold-2); direction is stable, strength varies.
4. **M0 monthly stability:** strong but the one negative month is 2025-09 (the correlated one); mildly faster-decaying than funding (0.67 at 3-6min).
5. **Book-2 capacity:** single-digit-% of $2.5M illiq ADV — a small sleeve; and Book-2's diversification of Book-1 is a same-timestamp ~0 correlation, not a hedge in a joint crypto-wide risk-off.
6. **M0 seed variance (now quantified, was the single-seed limit):** IC is seed-robust (0.036, std 0.0012, cross-seed corr 0.70-0.78 = same signal), but the blend net-Sh varies 3.43–4.56 across seeds — the orig-seed 4.56 headline was the top of the band; use the seed-median 3.83 and ensemble seeds in production. Single architecture; periodic retrain still advised.

## Deployment read
Deploy **Book-1 (funding + 3-seed-ensemble-M0 blend) as the scalable core** — the production config: net-Sharpe **3.92**, break-even 41 bps/side, all-fold positive, 6/7 months net-positive, latency-flat (3-seed ensemble beats any single seed and the median; single-model expectation is the median 3.83). 2h primary for funding, 1h for the blend. Add **Book-2 SIZE** as a small, capacity-capped diversifying sleeve — the cross-book correlation is confirmed ~0 (+0.08), so it genuinely diversifies the core. Everything else in the factor space (positioning, order-flow, semivar, price-vol on mega-caps, GBDT over all tabular features, 5 stage-2b DL heads) was exhaustively tested by the 5-gate factory and correctly rejected — these two books are what survived. Production caveats to carry: short OOS window, the 2025-09 correlated-drawdown month, funding regime-dependence, M0 single-seed (add seed-robustness + periodic retrain), Book-2 small capacity.
