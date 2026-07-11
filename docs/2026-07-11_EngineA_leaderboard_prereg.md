# Engine A — paradigm-race leaderboard, PRE-REGISTERED (locked before any arm runs)

> **创建:** 2026-07-11 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** pre-registration (locked before results) · **作废条件:** the wide panel (wide_dl.npz) is rebuilt / baseline book changes / the arm set is re-scoped after review.
> **交叉引用:** task #45 (Engine A, USER flagship) · `multi_asset/exports/wide_dl.npz` (03e4c8b) · scorecard `docs/2026-07-08_multi_asset_v2_portfolio_scorecard.md` (§0 standing fill-window law) · factory `multi_asset/eval/factor_pipeline.py` · memory `ma-v2-dlv2-phase-launched`.

## 0. One line

Every backbone arm (Conformer reference + the research top-5) runs the **same** wide-DL config and is judged by the **same 5-column read** on the wide panel; one leaderboard, **most-incremental-net-cost-tradeable-and-execution-feasible wins**. Locked before any arm runs so the winner can't be reverse-fit.

## 1. Panel + targets (wide_dl.npz — 140 coins / 13,176 h / 26 causal channels)

- **Primary target = YR4** (4h return, residual-on-[funding+zoo]). Predicting YR4 IS the "incremental orthogonal alpha over the book" metric **by construction** (the baseline is already residualized out). Aux = YR1 (1h), YR24 (24h).
- **Baseline book = [funding + zoo]** (the 8 `baseline_cols`); membership = **MEMBER110** (causal point-in-time, no survivorship); clean masks CL{1,4,24} = ≥horizon non-overlap.
- Why 4h primary: it is comfortably **long-horizon** (≫ the ~5s–5min fill window — see §4), so it is execution-feasible by design; 1h/24h aux widen the paradigm's learning without changing the tradeability frontier.

## 2. The identical read (leaderboard columns) — every arm scored the same

Each backbone arm: same WidePanelData (168h windows, variable-membership mask), same K=6 orthogonal heads, pred_smooth λ from start, same folds/seed, gated **bit-identical off**; **only the backbone changes.** Then:

| col | metric | tool |
|---|---|---|
| (a) INCREMENTAL IC | pooled rank-IC(pred, YR4) on CL4 × MEMBER110 + empirical-null **z** (re-derived N≈110, §3) | `factor_pipeline` |
| (b) PERSISTENCE | weight-autocorr (the tradability KPI) | `m0_persistence_diag` |
| (c) ★ FILL-WINDOW | entry-lag IC decay 30/60/120s → % surviving = alpha-horizon (the STANDING GATE, §4) | `y180_filldecay` |
| (d) NET-COST | L/S net-Sh at prop cost {0.2,0.5,1.0} bps + break-even (4h rebalance = low turnover, cost-tolerant) | `execution_economics` |
| (e) ★ WALK-FORWARD gate-d | expanding-fold ΔIC over baseline + **per-fold sign-consistency** — THE decisive gate | `factor_pipeline.gate_d` |

**Leaderboard = one table, rows = arms, ranked by (e) gate-d ΔIC among the arms that PASS (a) null-z AND (c) fill-window AND (d) net-cost.** Most-incremental-wins. The Conformer (M0 paradigm) is the **reference row** — a new paradigm must beat it *incrementally* to justify its complexity (channel/complexity-addition penalty still applies).

## 3. Pre-registered acceptance bars (wide universe, re-derived at N≈110)

- **(a) empirical-null z ≥ 2.5 per-arm.** ★ Re-derived on wide_dl.npz (200 within-ts shuffles, 3,113 usable ts, median breadth **110 assets/ts**): **null_mean = +0.00010 (≈0), null_std = 0.00184 → IC ≥ +0.0047 for z=2.5.** ★ Key finding: **at N≈110 the small-N null-mean bias is GONE** (0.0001 vs materially-≠0 at N=14) — so IC-vs-0 is approximately valid here, but we keep the empirical-null z for rigor. The absolute bar is far below the wide-universe zoo ICs (0.01–0.05), so significance is easy; **the binding constraints are gate-d + fill-window + net-cost, not gate-a.**
- **★ FWER correction for the race:** with ~36 arms (≈6 backbones × K=6 heads) the *leaderboard winner* must additionally clear **FWER z ≥ 3.0** (Bonferroni 0.05/36 → z=2.99 → **IC ≥ +0.0056**) — a best-of-36 selection needs a stricter bar than any single arm — or survive a **held-out block** (pre-committed final fold untouched during the race).
- **(e) gate-d ΔIC ≥ +0.003 + per-fold sign-consistent** — the real bar; pooled null-z is necessary-not-sufficient (it passed everything that gate-d later killed at N=14).
- **Orthogonality:** the K=6 heads must be mutually max|corr| < 0.7 AND each incremental over [baseline + already-accepted heads]; the YR4 residual target handles the [funding+zoo] baseline.
- **σ-collapse guard** σŷ/σy ≥ 0.02 per fold (hard reject); **seed-check** on any ACCEPT (headline seed-median, not the lucky seed).

## 4. ★ Fill-window law as a STANDING GATE (new, permanent)

*Execution-open economics revives a signal only if alpha-horizon ≫ the ~5s–5min adverse-selection/fill window.* Operationalized: **any arm's factor whose entry-lag decay retains < 50% of its IC at 60s (alpha-horizon < ~5min) AUTO-FLAGS execution-infeasible and is DROPPED from the leaderboard regardless of IC.** Calibration anchors: M0 (60-min) retains ~75–90% → pass; y180 (3-min, 12% at 60s) → fail. A y_4h target *should* have an hours-scale alpha-horizon (safe by design), but it is **measured per-arm** — a powerful backbone can learn a fast sub-signal that looks incremental on IC but is uncapturable. This makes execution-feasibility a first-class, pre-registered filter, not an afterthought.

## 5. The arms (the race)

- **Conformer (M0 paradigm) = REFERENCE** (the incumbent bar).
- **Research top-5 backbones** (from the research memo): conditional-autoencoder (Chen–Pelger–Zhu / GKX latent-factor), SSM (S4/Mamba), cross-asset graph (GNN), KAN, +1 per the memo's ranking. Each swaps only the backbone into the same WidePanelData + K=6 heads + pred_smooth + kill-gates.

## 6. Verdict framing (locked)

- **Winner** = the backbone with the highest gate-d ΔIC among those passing null-z (a) + fill-window (c) + net-cost (d) + sign-consistency (e) + FWER/holdout.
- **If NO arm clears (c)+(d)+(e)** → "wide-DL paradigm null" — the honest negative (the wide universe gave the zoo/factor-mining revival, but the DL *backbone* race adds nothing net-cost-tradeable over [funding+zoo]).
- A win must be **incremental over the Conformer reference**, not just positive — complexity is only justified by net-cost-tradeable incremental alpha that clears the standing gates.

## 7. Division

0B: WidePanelData layer + trainer adaptation + launch the arms (GPU). 0C (me): this pre-registration; score every arm through the identical read; maintain the leaderboard; two-person-verify any ACCEPT (engine identity, shuffle-null, leak-audit, fill-window). No arm's result is real until it clears the pre-registered bars here.
