# RUNBOOK.md — running the four-leg market-neutral book

> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0B handoff) | **状态:** v1 | **作废条件:** 腿构成 / 权重 / 执行栈 / 引擎 canonical 变更; 或 pilot 回执改写成本假设

Operating manual for the shipped book. Pairs with `REPRODUCTION.md` (how to rebuild) and the
engine components in `multi_asset/engine/` (C1–C6). **Read §0 before quoting any Sharpe.**

---

## 0. ★ Caliber contract (three tiers — the single most important thing to get right)

The book is quoted at three distinct calibers. Conflating them is the fastest way to mislead
a partner or an allocator.

| tier | number | what it is | use for |
|---|---|---|---|
| **Structural** | net Sharpe **12.21** | frictionless upper bound: explicit 1.9 bps cost only, daily×√365, market-neutral, `--shaping cap` | signal-quality benchmark vs *research/signal* Sharpes |
| **Deployable-calibrated** | net Sharpe **10.84** | + isotonic magnitude calibration (`--shaping calibrated`, C3 on) so sizing/net-cost gates see real E[bps]; costs **−1.3** Sharpe | Kelly sizing, net-cost taker-gate math |
| **Deployable net** | **mid-single-digit, pending pilot** | + full maker-fill execution stack (adverse-selection markout, fill<1, queue, impact, capacity) | the only number that predicts live P&L |

**Rule of thumb: deployable ≈ 1/3 – 1/2 of structural.** The structural table is a **signal
ceiling, not a fund net-Sharpe.** Never benchmark it against an after-all-cost fund return.

---

## 1. The book — four legs

Cross-sectional, market-neutral, each leg L1-normalized to unit gross; book weights set capital
share. Engine `DEFAULT_WEIGHTS` (0C canonical) and the deployment-tilt band:

| leg | signal (source) | sign | rebalance cadence | canonical w | deploy band |
|---|---|---|---|---|---|
| **king** | DL 4h residual-reversal (`king_pred`, conformer+xattn, lam_orth=0) | **+1** | 4h | 0.30 | **0.35–0.40** |
| **funding** | `rank(funding_ema)` crowding-reversion | **−1** | 8h | 0.30 | 0.28 |
| **SIZE** | `z(size_dvol)` (small-cap tilt) | **+1** | 24h | 0.30 | 0.28 |
| **S2** | DL 24h slow factor (`s2_pred`) | **+1** | 24h | 0.10 | 0.10 |

- Canonical `DEFAULT_WEIGHTS = {king .30, s2 .10, funding .30, size .30}`, `DEFAULT_SIGNS =
  {king +1, s2 +1, funding −1, size +1}`. The deploy band shifts capital toward king (highest
  IC, most dynamic); keep S2 light (0.10) — it is a diversifier, not a driver.
- **funding MUST stay rank-weighted.** rank is naturally bounded (single-name ≤ 0.049, FTX-tail
  |max| 1.0). **Do NOT revert to z-weighting** — unbounded z concentrates a single name to 0.49
  and *requires* the C5 funding-risk hygiene (winsor/name-cap) to be tradeable. Under rank, C5 is
  bit-identically inert (kept wired as insurance for the z path only).

---

## 2. Execution — maker-fill only

**This book is NOT taker-viable.** Taker-tradeability was tested and rejected (even smart-tail);
the edge only survives as **maker** (maker-fill sim cost ≈ 0 bps at k≈60, 8–30× under taker).

- **Quoting window `k = 900 s`.** Passive limit orders worked over a 900 s maker window; execution
  is patient, not aggressive.
- **Participation ≤ 1%** of each coin's per-hour traded notional. This is the binding capacity
  constraint at scale (alt legs decay first when it bites).
- **Vol-gate (C2) = execution tactic ONLY — never de-lever.** On BTC realized vol > **18 bps/min**
  (24 h trailing window), the gate widens quotes (up to **2×**), shrinks slices (down to **0.3×**),
  and goes patient — **exposure_mult is pinned to 1.0**. The book is a *crisis beneficiary*
  (high-rvol Sharpe still +4.14, crisis-day leg-corr −0.05, worst-BTC-day combo mean +0.47);
  de-leveraging in stress *loses money and forfeits the tail hedge.* Do not add exposure modulation.
- **Netting (C6) = 4h-sync cross-leg netting.** Hold each leg's sub-portfolio at its own cadence,
  net across legs on a 4h-sync, and **trade only Δnet**. 4h-sync is the deployment spec. Effect:
  hedge 12.4%, gross-turn 857 → net-turn 751, **savings ≈ 202 bps/yr** (canonical; 284 bps/yr under
  the calibrated variant, hedge 17.4%).
- **Tail cap + calibration.** Canonical shaping = **99% position cap only** (`shaping='cap'`).
  **Isotonic C3 is OFF in canonical** — it is a net-negative reshaping here (−1.3 Sharpe; sparse
  tail saturation flattens high-conviction positions, cuts mean not variance, worse than cap-only
  even in a look-ahead oracle). Turn C3 **on only** for the deployable-calibrated magnitude the
  Kelly / net-cost-gate math needs (`--shaping calibrated`), and quote the −1.3 cost when you do.

---

## 3. Capacity

- **Start $5–10M**, soft cap **$40–80M**. Below the soft cap the ≤1% participation constraint is
  slack; above it, it binds and the **alt legs decay first** (BTC/ETH absorb size, small-caps do
  not). Scale in tranches and watch per-leg fill quality as you grow.

---

## 4. Pilot protocol (the binding go/no-go)

Run a **$2–5M** live maker pilot before any scale-up.

**GO if all hold (normal regime):**
- fill-rate **≥ 0.5** at the k=900 maker window;
- realized cost **≤ 2.5 bps** in normal regime;
- markout **≤ 2×** the tick-research baseline.

**STOP if:** realized cost **> 3.5 bps sustained** (the edge is thinner than the friction).

**★ Primary scientific output = alt-leg adverse selection.** The open question the pilot exists to
answer is whether the alt legs get *picked off* on fills (adverse selection on small-caps). That is
the first thing to measure, and it decides whether the deploy-band tilt toward king is right.

**★ Fill-receipt reflux protocol (contractual).** The partner MUST return **fill-level receipts**
for every pilot fill so we can run markout analysis:
`timestamp · symbol · side · fill_price · fill_size · quote_price_at_fill · mid_at_fill ·
mid_at_(fill + markout_window)` (plus the intended vs achieved slice). Without this reflux the
pilot produces a P&L number but **no diagnosis** — and the alt-leg adverse-selection question
(the whole point) stays unanswered. Make the reflux a delivery condition, not a nice-to-have.

---

## 5. Live monitoring & re-benchmarking

- **IC monitor (C4):** rolling rank-IC decay alarm + a champion/challenger switch stub (retrain
  hook — **not** wired to an automatic retrain; treat an alarm as a *finding*, retrain by hand).
- **The acceptance battery is a rolling instrument, not a one-shot.** Re-run
  `handoff/acceptance_battery.py` on each retrain / periodic re-benchmark; it judges *historical*
  OOS only and **cannot see the next regime**. Non-stationarity (lead-lag / correlation drift, core
  constraint #2) is real — pair the battery with the online IC monitor and a re-benchmark cadence.

---

## 6. What the structural Sharpe does NOT include (state it every time)

maker-fill slippage · adverse-selection markout · queue position · market impact · capacity limits.
The 12.21 is a **signal-quality upper bound.** Quote deployable expectations at mid-single-digit
until the pilot's net-of-execution scorecard says otherwise.
