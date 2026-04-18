# Project Principles — Distilled Guidance for Future Iterations

_Not rules, but tested wisdom. Each principle comes with the rationale, the empirical / literature source, and concrete triggers for when it applies. Written 2026-04-18 after synthesizing external quant-practice critique + our own experiment logs._

---

## 1. Chase breadth, not precision (Grinold-Kahn)

**Principle:** Information Ratio = IC × √(N_independent_signals). Once a single signal's IC is reasonable, marginal returns to pushing it higher are dwarfed by returns to adding independent signals.

**Source:** Clarke, de Silva, Thorley 2002 ("Portfolio Constraints and the Fundamental Law"); Alpha101 (Kakushadze 2015, avg correlation 15.9% across 101 factors → IR > any single factor).

**What it means for us:**
- Our V4 Pearson ≈ 0.10 on a **single asset, single model** is already near-industry-strong as a single signal (institutional cross-sectional factors typically IC 0.02-0.05).
- Pushing V4 alone to 0.12 is hard; **combining V4 + Ridge + XGBoost** (each ~0.08-0.10) with low correlation could lift realized IR 1.7-2× more cheaply.
- Apply: ensemble is higher-ROI than another architecture pass once single signal is ≥ Ridge baseline.

**When to invoke:** any time we're about to spend > 1 day on a single-model tweak and a cheap independent alternative exists.

---

## 2. Treat Probability of Backtest Overfitting (PBO) as a real tax

**Principle:** the more variants you test on the same small val set, the more your "best" is partially noise. Formalized by López de Prado.

**Our specific exposure:** R1+R2 smoke = 16 variants on 10-day val sets. Even though E_noattn replicated at 700d, other rankings (G_noconv better than A_noattn at 100d) did NOT replicate.

**Discipline:**
- **Never declare a winner from 100d smoke alone** — always re-validate at 700d before committing.
- **Cap variants per sweep at ~8** and require pre-registered hypothesis per variant.
- **Report Spearman AND Pearson** — if they diverge, outlier days are dominating and the "winner" is likely selected by noise.

**Anti-pattern we've already done:** promoted G_noconv to 700d based on 100d val_corr 0.126 — it underperformed no_attn alone at scale. Lesson reinforced.

---

## 3. Transfer Coefficient (TC) — the gap from theoretical IR to realized Sharpe

**Principle:** TC ≈ realized_IR / theoretical_IR. Retail and small teams typically have TC = 0.3 due to fees, slippage, discrete position sizing, trading-everything-equally. Institutions reach TC = 0.7-0.9 via position sizing, internal crossing, optimized execution.

**Our specific failure:** Fold 0 V4 test backtest showed `trade_rate=1.0, Sharpe=-390, net_pnl=-139 bps`. We trade every period regardless of confidence — burning cost.

**Action when applicable:**
- Always gate trades by confidence: `|q50| / (q90 - q10) > τ`. This is literally why we built the monotone quantile head.
- Sweep τ in backtest to find the trade_rate that maximizes net Sharpe.
- If V4's Pearson 0.10 signal lives mostly in high-confidence samples, gating dramatically lifts realized Sharpe even if paper IC doesn't move.

**Rule:** do not evaluate a model's "useful alpha" on `trade_rate=1.0`. Always report Sharpe(τ*) where τ* is the confidence-optimized threshold.

---

## 4. Attribute DL's alpha against simple baselines — know what your model is actually learning

**Principle:** a deep model's predictive correlation can be decomposed into:
- Linear momentum (past-return autocorrelation)
- Volatility factor (just predicting more when vol is high)
- Calendar factor (hour-of-day, day-of-week)
- **Residual — the actual non-linear increment DL is providing**

If the residual is small, DL is an expensive wrapper for Ridge. If the residual is large, DL is doing real work.

**Concrete procedure:**
```
Fit OLS: q50_predicted ≈ β₁·past_ret_60s + β₂·past_ret_300s + β₃·realized_vol_60s
                       + β₄·hour_sin + β₅·hour_cos + residual
Report:
  R² of the OLS         → what fraction of DL output is explained by simple factors
  Pearson(residual, y)  → DL's actual non-linear contribution
```

**Why this matters for us:** if residual-Pearson is < 0.05, then a much simpler feature-engineered Ridge would give us 90% of the value. We'd stop over-iterating on architecture.

**Threshold to worry:** simple-factor R² > 0.8 of the DL output. That means DL is mostly re-discovering momentum.

---

## 5. Model capacity MUST match signal strength at SNR < 1%

**Our empirical proof:** removing patch attention (3K params) lifted Pearson +0.055. Every subsequent "add a module" test HURT. Every "remove a module" test either helped or was neutral. Stated in CLAUDE.md; re-confirmed in our V4 audit.

**Operating rule:**
- New module must have an ablation showing positive ΔPearson at 700d val BEFORE being merged to the main path.
- Default bias: **if uncertain, don't add.**
- Tolerable param growth: < 5K per modification, with a clear hypothesis.

---

## 6. Defense against correlated-model failure (Oct 2025 lesson)

**Principle:** in Oct 2025 crypto flash crash, many institutional AI models failed simultaneously because their objectives/features were too similar — recursive panic selling when macro shock entered a regime none had seen in training. The lesson isn't "AI bad" but "correlated strategies fail together".

**When we ensemble (Principle 1):**
- Make models **meaningfully different**: different feature subsets, different loss functions, different architectures (Ridge vs XGBoost vs DL — not three DL seeds with same config).
- Test ensemble member correlation: if `cov(model_i_predictions, model_j_predictions) > 0.8`, the ensemble won't help on tails even if it looks good on average.

**Action when doing deep ensemble:** include at least one tree model (XGBoost) and one linear model (Ridge) alongside the DL. That's automatic diversity.

---

## 7. Risk-model / optimizer thinking still applies in single-asset

**Misread:** "We only have BTC, so Barra risk models don't apply." 

**Correct framing:** even on a single asset, our P&L has latent factor exposures across TIME:
- Volatility regime (low-vol → high-vol days)
- Trending vs mean-reverting regimes
- Liquidity regime (daily/weekly cycles)

**What to do:** periodically regress cumulative P&L against simple time-series factors:
- Past vol (realized_vol_1d)
- Regime (sign of past_return_1d)
- Hour / weekday dummies

If P&L is mostly explained by 1-2 of these, the model has no alpha above the regime itself.

---

## 8. Our tangible red flags (active monitoring)

From the external critique, mapped to our pipeline:

| Red flag | How to detect | What to do |
|---|---|---|
| DL Pearson is mostly momentum auto-correlation | Principle 4 attribution | Switch to simpler feature + larger breadth ensemble |
| Smoke winner doesn't replicate at 700d | Principle 2 discipline | Revert; don't commit from small-val wins |
| Sharpe is negative despite positive Pearson | Trade rate too high | Principle 3 — confidence gate |
| Ensemble gain < expected √N | Members are correlated | Principle 6 — diversify architectures |
| Improvement shows only in 1-2 outlier months | Concentration risk | Check month-by-month Spearman; don't rely on pooled metric |

---

## What we DO NOT take from the external critique

- HFT hardware defeatism — we're mid-frequency (180s), latency isn't our bottleneck.
- "Retreat to macro / illiquid long-tail" — crypto mid-freq is a viable lane for small teams; we don't retreat.
- "70% win-rate factor is always overfit" — in some market regimes this can be real. The real rule is: validate on rigorously-held-out time periods, not absolute skepticism.
- Institution-only techniques (internal crossing, colocated servers) — not relevant.

---

## When to re-read this doc

- Before launching any ablation sweep → check Principle 2.
- Before writing a backtest report → check Principles 3 and 4.
- Before proposing a new architecture module → check Principle 5.
- Before adding an ensemble member → check Principle 6.
- When stuck at a Pearson ceiling → check Principle 1 (breadth).
