# Engine A — paradigm-race LEADERBOARD (live results)

> **创建:** 2026-07-11 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** live (updated as arms land) · **交叉引用:** pre-registration `docs/2026-07-11_EngineA_leaderboard_prereg.md` · tools `wideA_score.py` (5-col + dynamic split), `wideA_leakaudit.py`, `wide_null_calib.py`, `wide_fillcost.py`.

**Race metric = shuffle-future-adjusted DYNAMIC IC** (excludes static cross-sectional tilt so paradigms compete on genuine timing skill). Headline = the 6-head equal-risk ENSEMBLE (no per-fold-best selection bias). Net-cost at REALISTIC wide-book cost {2.3 mega / 5.0 mega+mid-capped / 9.5 full-book} bps, EMA-hold operating point (the wide book is mid+small-cap, not mega). All on ≥4h-CL × MEMBER110, target YR4 (=incremental-over-[funding+zoo] by construction).

## Standings

| rank | arm | naive IC | **DYNAMIC IC** (z) | static tilt | gate-d per-fold (sign) | net-Sh @2.3/5.0/9.5 | persist | verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **xattn** (cross-asset attn) | +0.0408 | **+0.0313** (13.6) | +0.0094 | [.035/.040/.048] ✓ | +2.04 / +1.81 / +1.42 | 0.77 | ★ **LEADER** (+0.0068 dyn over ref) |
| 2 | **Conformer** (M0 paradigm) | +0.0312 | +0.0245 (11.1) | +0.0068 | [.033/.031/.030] ✓ | +1.66 / +1.39 / +0.95 | 0.66 | REFERENCE BAR |
| — | pred-smooth λ0.3 | +0.0151 | +0.0130 (4.9) | +0.0021 | [.005/.006/.034] ✓ | +0.46 / −0.36 / −0.99 | 0.75 | REJECT (below bar + net-negative) |
| — | IPCA resmom_24h (K=3 best) | +0.0059 | n/a (factor) z3.0 | — | [.008/.009/**.001**] | (tiny IC) | — | REJECT — DECAYING (fold-2→~0) + raw-IC ~0 (residual-only, fragile) + 4-5× below bar |
| pending | QIM, aux-MTL | — | — | — | — | — | — | GPU race ~1-2h |

## Read

- ★ **The wide-universe multi-head DL is a real positive** — not the paradigm-null. Both Conformer and xattn add leak-free, net-cost-tradeable (at realistic wide-book cost, EMA-held, mega+mid-capped) incremental timing alpha over [funding+zoo].
- ★ **xattn (cross-asset attention) leads** — dynamic +0.0313, 28% over the Conformer bar, net-cost better at every tier, gate-d clean and *increasing* across folds. Cross-sectional structure across the 140-coin universe is exploitable signal beyond a per-asset temporal backbone.
- **pred-smooth λ0.3 validates the dynamic metric:** its naive +0.0151 hides a weak dynamic (+0.0130, below the bar) and it's net-NEGATIVE at realistic cost. The pred-smoothing dispersed the 6 heads (2 went negative), dragging the ensemble — not a timing lever (0B predicted this). Its static tilt is tiny, so the failure is dispersion, not static-inflation.
- **Selection-bias note:** per-fold-best-head numbers (e.g. pred-smooth 0.0338) overstate; the ENSEMBLE is the honest, deployable, comparable metric.

## Gates (pre-registered, all arms scored identically)

null-z ≥ 2.5 (IC ≥ 0.0047 at N≈110; FWER z ≥ 3.0 for the winner) · gate-d walk-forward ΔIC ≥ +0.003 + per-fold sign-consistent · no-temporal-leak (shuffle-future dyn-z ≥ 5) · fill-window (4h ≫ 5min; persistence-confirmed slow) · net-cost > 0 at realistic wide-book cost. Winner also gets: full independent leak-audit + 3-seed confirm before any deploy claim.

## Next

Remaining arms (IPCA / QIM / aux-MTL) must beat **xattn's dynamic +0.0313** to lead. If none does, xattn is the paradigm winner (pending its leak-audit + 3-seed). If no arm beat the Conformer, the read would have been "Conformer sufficient" — but xattn already cleared it, so cross-asset attention is the paradigm lever so far.
