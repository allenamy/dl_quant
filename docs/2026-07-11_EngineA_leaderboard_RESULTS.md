# Engine A — paradigm-race LEADERBOARD (live results)

> **创建:** 2026-07-11 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** live (updated as arms land) · **交叉引用:** pre-registration `docs/2026-07-11_EngineA_leaderboard_prereg.md` · tools `wideA_score.py` (5-col + dynamic split), `wideA_leakaudit.py`, `wide_null_calib.py`, `wide_fillcost.py`.

**Race metric = shuffle-future-adjusted DYNAMIC IC** (excludes static cross-sectional tilt so paradigms compete on genuine timing skill). Headline = the 6-head equal-risk ENSEMBLE (no per-fold-best selection bias). Net-cost at REALISTIC wide-book cost {2.3 mega / 5.0 mega+mid-capped / 9.5 full-book} bps, EMA-hold operating point (the wide book is mid+small-cap, not mega). All on ≥4h-CL × MEMBER110, target YR4 (=incremental-over-[funding+zoo] by construction).

## Standings

| rank | arm | naive IC | **DYNAMIC IC** (z) | static tilt | gate-d per-fold (sign) | net-Sh @2.3/5.0/9.5 | persist | verdict |
|---|---|---|---|---|---|---|---|---|
| **1** | **★ QIM q50** (single pinball head) | +0.0704 | **+0.0601** (24.4) | +0.0103 | [.054/.069/**.088**]↑ ✓ | **+8.32 / +5.08 / +2.60** | 0.66 | ★★ **PARADIGM-SHIFT LEADER** — 2× the field, leak-free, folds *increasing*; pending lam_orth=0 confirm + 3-seed |
| 2 | xattn (cross-asset attn) | +0.0408 | +0.0313 (13.6) | +0.0094 | [.035/.040/.048] ✓ | +2.04 / +1.81 / +1.42 | 0.77 | strong (best K-head arm) |
| 3 | aux-MTL (1h/24h aux) | +0.0348 | +0.0271 (12.1) | +0.0077 | [.027/.037/.041] ✓ | +2.36 / +2.15 / +1.81 | 0.73 | above bar (aux supervision helps) |
| 4 | Conformer (M0 paradigm) | +0.0312 | +0.0245 (11.1) | +0.0068 | [.033/.031/.030] ✓ | +1.66 / +1.39 / +0.95 | 0.66 | REFERENCE BAR |
| — | pred-smooth λ0.3 | +0.0151 | +0.0130 (4.9) | +0.0021 | [.005/.006/.034] ✓ | +0.46 / −0.36 / −0.99 | 0.75 | REJECT (below bar + net-negative) |
| — | IPCA resmom_24h (K=3 best) | +0.0059 | n/a (factor) z3.0 | — | [.008/.009/**.001**] | (tiny IC) | — | REJECT — DECAYING (fold-2→~0) + residual-only fragile |

★★ **QIM = the finding of the race.** A single unconstrained 25-quantile pinball head (q50) scores DYNAMIC +0.0601 — **~2× the best K-head orthogonality arm (xattn +0.0313)** — leak-free (shuffle-future z24.4), net-cost ~3× the field (+5.08 @5bps), and per-fold *increasing* (not decaying). Both QIM heads beat the field (imean +0.0573 dyn), so it's the **single-distributional-head-on-residual approach** that's the lever, not q50 specifically. **Mechanism (0B's hypothesis): the K-head `lam_orth=1.0` orthogonality penalty dilutes the signal ~2×** — forcing 6 heads apart costs alpha; an unconstrained head captures it. ★ DECISIVE CONFIRM PENDING: a K-head run with `lam_orth=0` — if it recovers ~+0.06, the orthogonality-dilution mechanism is proven and the paradigm is "drop K-head orthogonality, use a distributional point head"; if it stays ~+0.03, QIM's edge is the pinball loss itself. Plus 3-seed robustness before crowning.

## Read

- ★ **The wide-universe multi-head DL is a real positive** — not the paradigm-null. Both Conformer and xattn add leak-free, net-cost-tradeable (at realistic wide-book cost, EMA-held, mega+mid-capped) incremental timing alpha over [funding+zoo].
- ★ **xattn (cross-asset attention) leads** — dynamic +0.0313, 28% over the Conformer bar, net-cost better at every tier, gate-d clean and *increasing* across folds. Cross-sectional structure across the 140-coin universe is exploitable signal beyond a per-asset temporal backbone.
- **pred-smooth λ0.3 validates the dynamic metric:** its naive +0.0151 hides a weak dynamic (+0.0130, below the bar) and it's net-NEGATIVE at realistic cost. The pred-smoothing dispersed the 6 heads (2 went negative), dragging the ensemble — not a timing lever (0B predicted this). Its static tilt is tiny, so the failure is dispersion, not static-inflation.
- **Selection-bias note:** per-fold-best-head numbers (e.g. pred-smooth 0.0338) overstate; the ENSEMBLE is the honest, deployable, comparable metric.

## Gates (pre-registered, all arms scored identically)

null-z ≥ 2.5 (IC ≥ 0.0047 at N≈110; FWER z ≥ 3.0 for the winner) · gate-d walk-forward ΔIC ≥ +0.003 + per-fold sign-consistent · no-temporal-leak (shuffle-future dyn-z ≥ 5) · fill-window (4h ≫ 5min; persistence-confirmed slow) · net-cost > 0 at realistic wide-book cost. Winner also gets: full independent leak-audit + 3-seed confirm before any deploy claim.

## Next

Remaining arms (IPCA / QIM / aux-MTL) must beat **xattn's dynamic +0.0313** to lead. If none does, xattn is the paradigm winner (pending its leak-audit + 3-seed). If no arm beat the Conformer, the read would have been "Conformer sufficient" — but xattn already cleared it, so cross-asset attention is the paradigm lever so far.
