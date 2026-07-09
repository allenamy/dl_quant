# DL v2 — acceptance protocol (PRE-REGISTERED, protocol-first)

> **创建:** 2026-07-09 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** pre-registration (locked BEFORE any v2 design lands) · **作废条件:** superseded once the design review runs and a v2 batch schedule is agreed; or if the CURRENT book changes (re-baseline).
> **交叉引用:** the deliverable `docs/2026-07-08_multi_asset_v2_portfolio_scorecard.md` (the CURRENT book = the baseline to beat) · the factory `multi_asset/eval/factor_pipeline.py` (5 gates, multi-baseline) · `multi_asset/eval/guard_fold_scorer.py` (strong-regime kill harness, single-asset) · memory `ma-v2-factor-state-2026-07-08`, `ma_v2_funding_ema_GO`, single-asset anti-patterns in `CLAUDE.md`.

## 0. One line

Every DL v2 design element (raw-book granularity, feature-crossing, regime adaptation, cross-asset dynamics, temporal+spatial adversarial structure, loss design) enters as a **gated arm** and is judged by the **SAME 5-gate factory vs the CURRENT book**, plus **DL-specific gates** (σ-collapse, seed-check, per-input-surface leak-audit, strong-regime kill-test). Protocol locked before the research/engineering memos land, so acceptance can't be reverse-fit to whatever the designs happen to produce.

## 1. The bar: what "ACCEPT" means

**Baseline to beat = the CURRENT book, not zero.** Book-1 (funding_ema + M0 DL, mega-cap) + Book-2 (SIZE sleeve, wide). A v2 element must add **incremental orthogonal value over the whole existing book** — the reject-by-default posture that killed semivar, 3 Alpha-101/GTJA survivors, GBDT-over-94-features, and 5 stage-2b heads. "Not worse than nothing" is not the bar; "adds beyond what we already have" is.

**The 5 gates (`factor_pipeline.run_factory`, multi-baseline mode, ≥3600 CL caliber):**
- **(a) standalone** xsec rank-IC, empirical within-ts shuffle-null **z ≥ 2.5** (NOT IC-IR-vs-0 — with 14 assets the null mean ≠ 0; a shuffled factor false-passed IR 0.86 / z 0.79).
- **(b) incremental** orthogonal IC over the book (per-ts multi-OLS residual of Y on ALL book factors), null **z ≥ 2.5**. This is the edge metric.
- **(c) orthogonality** max|corr| < 0.7 vs each book factor (necessary, not sufficient).
- **(d) ★ walk-forward Ridge ΔIC ≥ +0.003 + per-fold sign-consistency** — Ridge(Y~BOOK) vs Ridge(Y~BOOK+F), expanding folds. **THE decisive gate.** Pooled gate-b is optimistic; gate-d is the real bar (it killed every library survivor despite 96-way-selected z 3.6–4.7).
- **(e) net-cost L/S contribution** — Δ break-even + Δ net-Sharpe, [BOOK] vs [BOOK,F] Ridge-combined, cost grid {2,5,10} bps + stress, EMA-turnover sweep. Must not just have IC — must move the net-cost frontier.

Calibers: ≥3600 CL (dense-CL landmine); raw-y where absolute claims are made, clip-consistent for deltas (deltas cancel the clip); report **Pearson + Spearman**, divergence = flag.

## 2. DL-specific gates (ON TOP of the 5 — a v2 arm must clear these too)

- **(G1) σ-collapse guard** — σŷ/σy ≥ 0.02 **per fold**; below → hard REJECT, no exceptions. The collapse (σŷ→0) is the real guard, not β (β is量纲, IC is alpha — never gate on β level). Loss/architecture changes are the classic collapse trigger (anti-pattern #20: L2/dir_huber primary collapses σ in low SNR; pinball-L1 must stay primary).
- **(G2) seed-check on ANY accept** — ≥3 seeds; **headline the seed-MEDIAN, not the lucky seed**. Require IC seed-robust (small std, cross-seed pred corr > 0.5 = same signal); report net-cost as a **seed band**; if the accept hinges on one seed → REJECT. (The M0 seed story: IC robust std 0.0012, but net-Sh band [3.43, 4.56] → headline the median 3.83 / 3-seed-ensemble 3.92, never the band top.) An accept that's a single-seed fluke is not an accept.
- **(G3) leak-audit per NEW input surface** — every new input path gets an **independent 6-point audit** BEFORE its IC is trusted: (i) windows strictly ≤ t; (ii) causal normalization, train-only per fold; (iii) te disjoint + embargo ≥ horizon; (iv) shuffle-future null → IC → 0; (v) oracle sanity (a known-future feature should light up, a known-null should not); (vi) independent recompute of the headline IC by the other person. **The raw-book path is the highest-risk surface** — book-snapshot timestamp alignment, quote staleness, and future-book bleed are new leak vectors that M0's aggregated-sequence path didn't have. A z-7 result on a new surface is belt-and-suspenders-audited, not trusted on face.
- **(G4) ★ strong-regime kill-test for ANY regime-conditioning / state / adversarial / cross-asset-dynamics arm** — **pre-register "must not lose > X in the best months"** and test the STRONG regime FIRST (guard-first, fail-fast). **Single-asset lesson (hard-won, 10+ experiments): state pathways ate strong-month alpha under EVERY wiring** — FiLM, gain, LoRA, causal router, concat-fusion, tail/mag-weighted loss all regressed the crown-jewel strong months (−0.029 cd) even when they helped drift months. So: any arm that conditions on regime or adds expressive state must clear a strong-month floor — if it regresses the best-regime IC by more than the pre-registered threshold (proposed: **Δcd < −0.005 on the strongest fold = KILL**, mirroring `guard_fold_scorer`), it's killed regardless of drift-month gains. The book's edge lives in the strong regime; protect it.

## 3. Staging rule (proposed)

- **Rank by EV/cost** from the research + engineering memos. Cheapest, highest-EV first. **Loss changes rank first** (zero new params, no new data path, no new leak surface — §4).
- **Small pre-registered batches: 1–2 elements per GPU run.** NOT one mega-model with everything on. A mega-model is unattributable (can't tell which element helped/hurt) and pays the channel-addition penalty (#29: each added channel ≈ −0.013 unless it earns ≥ +0.003 alpha — the bar is net-incremental). Single-asset established that 5/5 single-axis changes were NEG and the base was a local optimum — you only learn that by testing one axis at a time.
- **Gated flags, bit-identical OFF.** Every element behind a flag; with the flag off the run is **bit-identical to the M0 baseline** (verify byte-identity before each batch). This gives clean ablation and protects the baseline from contamination.
- **Pre-register each batch's read** (pass/kill thresholds, strong-regime floor) BEFORE the GPU run. No moving goalposts after seeing the fold-0 print.
- **Budget discipline:** each batch is a single locked run; no mid-run iteration; kill gates per fold (σ/liveness). Multi-seed only on a candidate that already passed single-seed gate-d (don't spend 3× GPU on a dead arm).

## 4. Loss-experiment harness (the FIRST v2 batch — cheapest, fastest, highest-info)

**Rationale:** loss changes are zero-new-params, reuse the exact M0 pipeline (no new data/leak surface), and directly target the deployment metric (rank-IC) and the binding constraint (net-cost/turnover). Run FIRST — it tells us whether a deployment-aligned objective helps before we spend GPU on architecture.

**Apples-to-apples protocol:** SAME M0 architecture (d32/2blk/k15, funding-residual y_3600 target), SAME 3 folds, SAME ≥3 seeds — **only the loss changes**. Baseline loss = M0's current (pinball 1.0 + soft-rank 0.1 + huber 0.0). Each candidate swaps or ADDS exactly one term:

| candidate | mechanism | risk / guard |
|---|---|---|
| **soft-Spearman / LambdaRankIC (listwise)** | directly optimize rank-IC = the deployment + factory metric; ~zero added params | anti-pattern #15: rank-loss REPLACE → val→test drift. Use as **AUX w ≤ 0.1**, pinball stays primary; must pass gate-d walk-forward before accept. |
| **turnover-regularized** | penalize period-to-period weight churn → directly buys net-cost break-even (the binding constraint) | must not collapse σ; check the IC↔turnover trade is net-cost-positive not just lower-turnover. |
| **multi-task vol aux** | predict realized vol as an aux head; vol is the cheap-persistent target, acts as a regularizer | AUX weight ≤ 0.30 (anti-pattern #25 safe band); must not dilute the primary rank signal. |
| **cost-aware sample weighting** | down-weight high-cost / low-tradability names & up-weight the tradeable tail | keep it a weighting, not a target-reshape; watch for strong-regime regression (G4). |

**Acceptance:** each loss arm goes through the full factory (5 gates + G1–G4) vs the CURRENT book, seed-median headline. **σ-collapse guard is especially load-bearing here** (loss is the classic collapse lever). Report per-loss: seed-median rank-IC + Pearson, gate-d ΔIC + per-fold signs, net-cost Δ (BE + net-Sh), σŷ/σy, and the val→test drift check (train-IC vs test-IC gap — the rank-loss failure signature). A loss arm ACCEPTS only if it beats the M0 baseline loss on gate-d + net-cost at the seed-median, not just at one lucky seed.

## 5. Reject-by-default priors (carried from single + multi-asset — avoid re-paying)

- **Channel-addition penalty (#29):** each added input/channel ≈ −0.013 unless it earns ≥ +0.003 net alpha → default net-negative. The bar is incremental-over-book, always.
- **Capacity must match signal (R² < 1%):** deeper/wider/long-context backbones collapsed 6× on single-asset; **parameter pooling** (params:sample flip) is the multi-asset lever, not raw capacity. A bigger v2 model is guilty until proven incremental.
- **β is量纲, IC is alpha:** never gate on β level, never reward "β improvement" (rescale-invariant); σŷ/σy is the collapse guard, IC/rank-IC is the only alpha judge.
- **Dense-CL landmine / clip-caliber:** ≥3600 CL for 1h targets; raw-y for absolute, clip-consistent for deltas.
- **No post-hoc tricks in the innovation phase:** SWA/EMA/seed-ensemble are production-phase only (grounded, not val-fitting); the factory judges the raw arm.
- **Net-cost is the tradability verdict, not IC:** an arm can be IC-positive and net-cost-negative (rank-right/magnitude-wrong — funding 2024). Gate-e is mandatory, not a formality.

## 6. Workflow / division

- Three memos converge for the design review: **research** (web sweep, EV/cost of each element), **engineering** (0B, buildability + new-input-surface cost + leak-surface map), **this protocol** (acceptance). Design review ranks + schedules batches only after all three land.
- Each accepted-into-testing element → I score through the factory (same tools: `factor_pipeline` 5-gate multi-baseline, `guard_fold_scorer` strong-regime, `portfolio_scorecard`/`ls_gate` net-cost, `m0_replay_score` caliber). **Guard-first + two-person independent verification on any ACCEPT** (engine/node identity, shuffle-null, leak-audit recompute) — an accept isn't real until both clear it.
- **Priority order while the M0 full-history replay is running:** replay scoring (R1–R5) takes precedence the moment `train/m0_fullhist_wf/` folds land; this protocol + the loss-harness design are the CPU fill in between.
