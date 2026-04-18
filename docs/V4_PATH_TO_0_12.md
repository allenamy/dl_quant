# Path to Pearson 0.12 — Synthesized from 3 Research Streams

**Context:** V4 no_attention hit Pearson 0.101 / Spearman 0.107 on fold 0. Beats Ridge (0.099) but 0.02 below spec target (0.12). Three independent analyses — internal bottleneck diagnostic, SOTA LOB literature 2024-2026, cross-domain low-SNR ML — converged on overlapping recommendations.

## Headline: our 0.10 Pearson is at/near the SOTA frontier for this exact task

Evidence from literature review (Agent 2):
- **Wang et al. 2025** (arXiv 2506.05764, *same Bybit BTCUSDT data as us*): XGBoost beats DeepLOB; ternary accuracy ~0.50 at 1s. Signal at 180s is dramatically weaker than 1s → 0.10 Pearson is *strong* evidence of real alpha.
- **Briola et al. 2025** (Deep LOB Forecasting, QF): MCC 0.01-0.29 for mid-price direction. Small-tick instruments cap at MCC ~0.10 regardless of architecture.
- **Stock ranking Transformer benchmark** (arXiv 2510.14156): IC-Spearman 0.073-0.077. Our Spearman 0.107 at single-asset, 180s is competitive with cross-sectional multi-stock ranking.

**So the path to 0.12 is not "add more architecture"** — it's cleaner inputs, smarter labels, and ensemble discipline. Confirms CLAUDE.md principle "预处理 > 架构" and our own smoke finding (removing patch attention +55% Pearson).

## Convergent top-3 priorities (evidence-ranked)

### P1 — Dense-train / sparse-eval (fix data sparsity — Agent 1's #1)

**Root cause diagnostic:** V4 at stride=180 has 108K train windows vs V3's ~250K at stride=60. 1.6:1 window-to-param ratio forces the val_corr peak at E5 and overfitting immediately after. Agent 1 identified this as the binding constraint.

**Action:**
- Regenerate NPZs with stride=60 (~4-5h on pod, 3× more windows)
- Keep eval stride=180 for honest non-overlapping metrics
- Only re-train fold 0 first; if Pearson jumps >0.02, commit to all folds

**Expected lift:** +0.01 to +0.02 Pearson (refutable — if val_corr still peaks at 0.066, data isn't the binding constraint)
**Effort:** 1 day (4-5h regen + 2-3h training)
**Risk:** Label overlap within a 180s-horizon bar at stride=60 means labels are ~67% correlated across windows. V3 used this config successfully; our V4 just needs to catch up.

### P2 — Savitzky-Golay input/label smoothing (cleaner inputs — Agent 2's #1)

**Published evidence on our exact data:** Wang 2025 reports **+7pp accuracy gain** from SG filtering on Bybit BTCUSDT (0.43 → 0.52 ternary at 500ms). Their thesis: *"Better Inputs Matter More Than Stacking Another Hidden Layer"* directly explains our 0.061→0.101 jump from removing patch attention.

**Action:**
- Add SG pre-filter to microstructure feature extraction (polyorder 2-3, window matched to sub-horizon)
- Also apply TLOB-style decoupled label smoothing: target = mean(mid[t+170..t+190]) instead of mid[t+180] — removes label tick noise without leakage

**Expected lift:** +0.01 to +0.02 Pearson, primarily from cleaner targets
**Effort:** 0.5 day (feature pipeline + NPZ regen + test eval)
**Risk:** Low — SG is well-understood, label smoothing is a standard trick

### P3 — SWA / checkpoint averaging (extract more from current weights — Agent 3's #1)

**Why it matches our failure mode exactly:** val_corr peaks at E5 (0.066) then oscillates 0.049-0.059 for 8 more epochs before patience fires. Izmailov 2018 and Kaddour et al. ICLR 2025 show this is the textbook SWA scenario — oscillating iterates live in the same flat basin, averaging them moves to the basin center.

**Action:**
- Save top-K checkpoints (by val_corr) during training, e.g., K=5 surrounding the peak epoch
- At eval time: load each, accumulate prediction, take median (robust to one bad run)
- Or proper SWA: `torch.optim.swa_utils.AveragedModel` with constant LR for final 25% of epochs

**Expected lift:** +0.003 to +0.015 Pearson
**Effort:** 2-4h code change, can re-apply to existing fold_0 if we save mid-training checkpoints (future runs)
**Risk:** If oscillation is inter-basin (not intra-basin), averaging hurts — unlikely given small Pearson-Spearman gap indicates stable signal extraction.

## Secondary priorities (strong evidence, smaller gains)

### P4 — Multi-seed deep ensemble (+0.005 to +0.012, Agent 3's #2)

Train 5 identical models from different seeds, aggregate predictions by middle-60% trimmed mean. Standard in empirical asset pricing (Gu/Kelly/Xiu RFS 2020) and Kaggle finance competitions. Cost: 5× training compute per config.

### P5 — Lower peak LR + cosine decay (Agent 1's #2)

Val_corr peaks exactly at E5, the moment warmup ends. Drop base_lr 6e-4 → 3e-4 (against sqrt-scaling but signal is too weak for large-batch noise), and switch from `ReduceLROnPlateau` to cosine decay from peak. Expected lift: small but cheap.

### P6 — Tighter y-winsorization (Agent 1's #3)

`y_norm=(y_median, y_sigma, 5.0)` clips to ±5σ. Pinball loss gradient is linear outside the band — fat tails dominate. Drop clip to 3.0 or use winsorized std instead of MAD. Small lift, trivial change.

## Bugs/waste identified (fix opportunistically)

- **RawLOBEncoder wastes ~520 params** (d_raw=16 but spatial_stack outputs 32, projected down) — `src/model/raw_lob_encoder.py:42`
- **GDCN operates in 64-dim feature space = 24% of model** — could project to d_model before GDCN. Test `n_cross_layers=1` and early-projection variant.
- **Patch embedding constructed even when `use_attention=False`** — 19K wasted params inflating AdamW state. One-line fix in `dual_path_model_v3.py:290`.

## De-prioritized (evidence against)

- **Multi-horizon parallel heads**: Agent 2 confirms this is not what literature recommends. Zhang 2021 uses *sequential* conditioning (Seq2Seq) not parallel loss. We already empirically confirmed multi-horizon hurt convergence.
- **Mixup / C-Mixup on financial features** (Agent 3): synthetic interpolations in feature space create targets in noise region; for LOB tensors, mixed bid/ask depth profiles violate no-arbitrage.
- **Knowledge distillation** (Agent 3): requires a bigger/better teacher. In SNR < 1% no such teacher exists.
- **Mamba/SSM architectures** (Agent 2): no published evidence on sub-minute crypto LOB.

## Red flags we should internalize

1. **We are overinvested in architecture, underinvested in labels.** TLOB's entire +3.7 F1 claim comes from relabeling. CLAUDE.md lists 18 architecture/feature tasks but only 1 label task.
2. **XGBoost beats DeepLOB on our exact data** (Wang 2025). We should re-verify V4 actually beats XGBoost on V4 features, not just Ridge.
3. **Our 700-day training window assumption is untested.** LOB non-stationarity → a rolling 60-180 day retrain may beat a single 700-day train. Worth an ablation.

## Recommended execution order (next 48h)

Assuming current 4-fold no_attention training (PID 38620) completes successfully:

**Day 1 (6-8h):**
1. Add SWA to trainer_v2.py (code change only) — apply retroactively to best_model.pt checkpoints from the 4-fold run for pooled IC re-computation
2. Launch Savitzky-Golay smoothing experiment — add to feature pipeline, regen NPZ for test subset (100 days), run smoke variant
3. In parallel, kick off stride=60 NPZ regen in background (~5h) — this is long lead time

**Day 2 (6-8h):**
4. Train fold 0 on stride=60 NPZ with no_attention config. If test Pearson > 0.12, commit to full 3-fold run.
5. Train fold 0 on SG-smoothed features. Compare.
6. If both individually help, combine.
7. Multi-seed ensemble as final safety net.

## Expected outcome

Combined lift from P1 + P2 + P3 (if additive): **0.101 → 0.125-0.150 Pearson** — plausibly clearing spec target.
If only P1 is material: **0.101 → 0.115-0.120** (just shy of target, beats Ridge + V3 with room).
If nothing materially moves: **~0.10 is our ceiling at 700d stride=180** — document as the real frontier for this asset/horizon.

Above 0.14 is likely the SNR floor without alternative data (funding rate, perp-spot basis, cross-venue aggregated flow) per Agent 3.

## Sources

(Key citations from the 3 agents; full list in individual agent reports)
- Wang, Ma, Gu 2025 — *Exploring Microstructural Dynamics in Crypto LOB*, arXiv 2506.05764 (our exact data)
- Berti & Kasneci 2025 — *TLOB*, arXiv 2502.15757 (label decoupling)
- Izmailov et al. 2018 — *SWA*, arXiv 1803.05407
- Kaddour et al. ICLR 2025 — *When/Where/Why Average Weights*, arXiv 2502.06761
- Gu/Kelly/Xiu 2020 — *Empirical Asset Pricing via ML*, RFS (seed-ensembling in finance)
- Briola et al. 2025 — *Deep LOB Forecasting: A Microstructural Guide*, Quantitative Finance
- Wang, Ma, Cohen 2025 — *Pre-training Time Series Models with Stock Data Customization*, arXiv 2506.16746 (Masked MA)
