> **创建:** 2026-07-08 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** in-progress (cross-book corr pending 0B's Book-2 return series) · **作废条件:** book factors retrained / universe or horizon change / a new factory-ACCEPT factor added.

# Multi-asset v2 — FINAL portfolio scorecard (consolidation deliverable)

**Portfolio = two orthogonal books.** Book-1 (mega-cap, the scalable core) + Book-2 (wide breadth, small-capacity diversifier). Everything net-of-cost, honest raw-y, walk-forward OOS. Tools: `multi_asset/eval/{factor_scorer,factor_pipeline,ls_gate,gbdt_probe,portfolio_scorecard}.py`.

## Executive summary
- **Book-1 = funding_ema + M0 DL factor**, equal-risk z-blend: **net-Sharpe@2bps 4.56, break-even 41 bps/side, all-fold positive, latency-flat, 5/7 months net-positive.** Two orthogonal (corr 0.107) net-cost-additive factors; the blend beats either alone. **This is the deliverable's core.**
- **Book-2 = wide SIZE-premium sleeve**: cost-immune (net-Sharpe 2.11, turnover 0.0018) but capacity-capped (~$2.5M illiq ADV → single-digit-% deployable). A real diversifier, not scalable.
- Both are net-cost-tradeable; the whole tabular/library/DL-multi-head factor space beyond these was exhaustively tested and correctly rejected by the 5-gate factory.

## Book-1 scorecard (mega-cap, 14 USDT-perp, 1h; funding also validated at 2h)
Walk-forward OOS ~2025-02..2025-09 (3 disjoint folds). Operating turnover = best-break-even EMA alpha. Cost = 2 bps/side (mega-cap taker-realistic).

| metric | funding_ema | M0 DL | **BLEND (equal-risk)** |
|---|---|---|---|
| rank-IC (per-ts) | +0.0186 | +0.0355 | **+0.0393** |
| break-even /side | 18.8 bps | 33.6 bps | **41.4 bps** |
| net-Sharpe @2bps | 2.08 | 4.15 | **4.56** |
| gross-Sharpe (0-cost) | 2.33 | 4.41 | 4.79 |
| operating turnover | 0.027 | 0.031 | 0.029 |
| net ann @2bps | +4,021 bps | +8,622 bps | **+9,965 bps** |
| per-fold net-Sharpe | [0.75, 7.2, −0.22] | [5.15, 6.21, 1.11] | **[3.7, 8.82, 1.2]** |
| months net-positive | 4/7 | 5/7 | **5/7** |
| max drawdown | −920 bps | −568 bps | −864 bps |
| latency decay (0/180/360s) | 1.0 / 1.0 / 1.0 | 1.0 / 0.67 / 0.67 | **1.0 / 1.0 / 1.0** |

- **The blend is the best line** — net-Sharpe 4.56 > either factor, all-fold positive (funding's weak fold-2 −0.22 is rescued by M0), latency-flat (funding's flatness stabilizes M0's mild 0.67 decay). Break-even 41 bps/side clears any realistic mega-cap taker cost (~2-5 bps) by ~8-20×.
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

## Cross-book correlation (the diversification claim)
Book-1 (mega-cap funding+M0) and Book-2 (wide SIZE) are on DISJOINT universes with orthogonal mechanisms (crowding-reversion ⊥ size-premium). Expected corr ≈ 0. **PENDING** 0B's Book-2 per-rebalance return series to verify by timestamp — will update this section (the diversification benefit hinges on it being ~0).

## Honest limits
1. **Short OOS window** (~7 months, 2025-02..2025-09). All stability numbers are on a small sample; not multi-year.
2. **Correlated drawdown month:** 2025-09 is net-negative for BOTH funding (−365 bps) and M0 (−182) → blend −371. The two book-1 factors are only mildly diversifying (corr 0.107) and can draw down together in an adverse month.
3. **funding regime-dependence:** magnitude is fold/regime-dependent (strong 2025-06 +740, weak/negative fold-2); direction is stable, strength varies.
4. **M0 monthly stability:** strong but one negative month (2025-09); mildly faster-decaying than funding (0.67 at 3-6min).
5. **Book-2 capacity:** single-digit-% of $2.5M illiq ADV — a small sleeve.
6. **M0 is a single trained model** (single seed, single architecture); production would want seed-robustness + periodic retrain.

## Deployment read
Deploy **Book-1 (funding+M0 blend) as the scalable core** (net-Sharpe 4.56, break-even 41 bps/side, all-fold positive) — 2h primary for funding, 1h for the blend. Add **Book-2 SIZE** as a small capacity-capped diversifying sleeve pending the cross-book-corr confirmation. Everything else in the factor space was tested and is exhausted.
