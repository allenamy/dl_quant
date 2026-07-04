> **创建:** 2026-07-04 UTC | **Session:** fable-regime-breakthrough (Stage-0B) | **状态:** final (PRE-REGISTRATION — FROZEN) | **作废条件:** 被 10-month OOS trajectory 结果取代或证伪

# Causal Regime-State Router — FROZEN Pre-Registration

**Purpose.** The frozen single-model search is SEALED: no single frozen model holds both strong months and drift months (the state pathway costs strong-month alpha regardless of wiring — affine FiLM / feature-stack / low-rank LoRA all regress 2025-10 to deploy 0.037–0.050 vs Run1-bugfix 0.079). The honest answer is a **causal regime router** over two specialist models, selected per-day by *what the market is* (positioning), NOT by *how each model has recently done* (trailing-model-IC — falsified: model recent-performance does not persist overnight, H4).

**This spec is FROZEN before seeing any of the 7 unseen months. No tuning after this commit. The router's real verdict = its OOS performance on the 7 months it was NOT built on.**

## Specialists
- **Run1-bugfix** (d1_*_run1): D1 fixed-regime-state substrate, NO state overlay / gain. Strong-month specialist (only strong-month winner: 2025-10 deploy 0.088).
- **Run2-state** (d1_*_run2): Run1 + 18-d positioning state (d_prior=24) + output gain. Drift specialist (2026-04 deleveraging deploy 0.046).
  (Drift-side model may be swapped for state-LoRA if lora_2026_01 proves the healthier drift model — decided separately; the router rule is unchanged.)

## FROZEN indicator + decision rule
- **Indicator:** `tt_15(d)` = causal trailing 15-day mean of daily-mean **tt_level** (top-trader long/short ratio; state-overlay channel index 11), using ONLY days strictly before decision day d.
- **Decision (per day d):**
  - `tt_15(d) < 0`  (net-short → deleveraging/drift)  → **Run2-state**
  - `tt_15(d) ≥ 0`  (net-long → strong/healthy)        → **Run1-bugfix**
- Lookback 15d, threshold 0.0 (sign) — both FROZEN. Per-day routing; a boundary day lacking 15d history routes to the trailing regime (rare).

## REJECTED axis (tested, falsified — NOT in the rule)
Trend-vs-chop (Kaufman efficiency ratio ER on trailing daily returns) was proposed to split strong-vs-choppy among net-long months. **FALSIFIED on the 3 built months:** the strong Run1-month 2025-10 is mean-reverting/CHOPPY (ER 0.236) while the drift Run2-month 2026-01 is slightly more trending (ER 0.365) — trend does NOT separate Run1 from Run2 (adding it MISROUTES 2025-10 to Run2, dropping router mean 0.0478→0.0461). A 3-zone tt rule with a fitted upper-threshold (to catch the net-long-extreme 2026-01) would classify all 3 but is overfit on 3 points — deliberately NOT added.

## In-sample result (3 built months — Run1+Run2 exist for 2025-10, 2026-01, 2026-04)
| month | Run1 dep | Run2 dep | oracle | tt_15 | router → | routed dep | match |
|---|---|---|---|---|---|---|---|
| 2025-10 | +0.0877 | +0.0584 | Run1 | +0.429 | Run1 | +0.0877 | ✓ |
| 2026-01 | +0.0092 | +0.0161 | Run2 | +1.146 | Run1 | +0.0092 | ✗ (Δ0.0069, toss-up hole) |
| 2026-04 | +0.0184 | +0.0464 | Run2 | −0.122 | Run2 | +0.0464 | ✓ |

MEAN deploy: **ROUTER +0.0478** > always-Run1 +0.0385 (+24%) > always-Run2 +0.0403 (+19%); ORACLE +0.0501 (router captures 95%). The 2 DECISIVE regime months route correctly; the miss is the 2026-01 hole (both models ~0.01).

## Known OOS risk
`tt_level` cleanly captures the deleveraging axis (net-short → Run2) but NOT strong-vs-choppy among net-long months. Extreme-net-long DRIFT months (2026-01 pattern) misroute to Run1. Cheap here (toss-up); could bite on an unseen net-long month where Run2 is strongly favored. This is the honest risk the OOS trajectory tests.

## OOS test (the finale)
Run 10-month Run1 + Run2 trajectories (2025-08..2026-05), apply THIS frozen router + the intraday self-assess deploy layer OFFLINE. Headline = router deploy on the **7 unseen months** vs always-Run1 / always-Run2 / oracle. If the router's OOS beats both single models (and closes a meaningful fraction of the oracle gap), the causally-routed specialist pair is the honest cross-regime deliverable. If it collapses to single-model parity OOS, the honest deliverable is "two specialists + the boundary is not causally routable — here is the oracle-vs-causal gap."

**Fold inventory (GPU cost):** Run1+Run2 exist for 2025-10 / 2026-01 / 2026-04 (3 mo). MISSING both: 2025-08, 2025-09, 2025-11, 2025-12, 2026-02, 2026-03, 2026-05 (7 mo) = **14 folds to run**. npz_v2arch_state covers all (2023-08..2026-05). Scorer: multi_asset/model/router_backtest.py.
