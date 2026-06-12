# Multi-Asset Overnight Progress — 2026-05-20 → 05-21

> **创建:** 2026-05-20 UTC+8 | **Session:** multi-asset autonomous overnight | **状态:** in-progress (rolling log)
> **作废条件:** 用户 2026-05-21 check-up 后归档
> 用户指示: 自主迭代，深入分析 + root-cause + 调研，直到达成目标 (avg per-asset Pearson 0.10)。

This doc is the single place to read what happened overnight. Updated as phases complete.

---


---

## ⚠️ CORRECTION (2026-05-21, after user review) — the BTC "gap" comparison was UNFAIR

The earlier "BTC-on-bar 0.033 << single-asset 0.072, 5-level loses half the signal" was **apples-to-oranges and the conclusion was premature** (user caught this):
- bar number = **Ridge, 47 hand features ONLY, no raw path**
- single-asset number = **DL (REG_arch), dual-path (hand + 20-level raw LOB)**
- conflates Ridge-vs-DL (single-asset DL was **+97% over Ridge**: 0.033→0.065 P), hand-only-vs-dual-path, period, AND 5-vs-25-level. LOB depth is likely the SMALLEST factor.
- **Current state honestly: only hand features + Ridge. No raw Path B, no DL, no architecture innovations yet.**

**Decision (user): keep per-asset Pearson 0.1 + replicate single-asset architecture first.** Built the missing Path B (bar 5-level raw-LOB tensor, channels match single-asset). Fair experiment now running:
- **Run 1:** bar dual-path DL (47 hand + 5-level raw, REG_arch) on BTC → fair vs single-asset DL 0.065. Is the gap architecture or depth?
- **Run 2:** Run 1 + BTC 25-level raw tower (Approach B, user's proposal) → isolates depth's incremental lift.


## ✅ RUN 1 RESULT (fair dual-path DL, BTC fold-0) — 2026-06-09

Authoritative trainer test_preds (EMA-best), test 2025-02-09..05-09, clean:
**P=+0.030, S=+0.039, sigma_ratio=0.029** (raw-best P=+0.026 S=+0.037).
- vs bar Ridge: Pearson neg (fat-tail) -> DL +0.030; Spearman 0.033->0.039. **DL DID help.**
- vs single-asset 25-level DL fold-0 (~0.058 P): bar DL = ~52% P / ~65% S.
- => bar data is NOT weak/dead; DL extracts real signal. Gap to single-asset is
  consistent with DATA RICHNESS (5-level bar vs 25-level LOB), supporting the
  25-level hypothesis. NOT an architecture problem.
- LESSON: my epoch-8 manual peek (P=0.0015) UNDERESTIMATED; trust the pipeline's
  own test_preds eval (correct normalization/checkpoint). Don't conclude on partial peeks.

**PIVOT -> Run 2:** add BTC 25-level LOB (book_snapshot_25, resampled to bar 1s grid)
as a 2nd RawLOBEncoder(n_levels=25) tower. Test if depth closes 0.030->0.058.
(Caveat: Run 1 = 1 fold; 3-fold confirmation deferred.)

## TL;DR (updated live)

- **Phase 0 (infra):** ✅ DONE — branch `multi-asset`, bar_loader (bit-validated), CLAUDE.md, 47-feat builder (leak caught+fixed), feature cache (487d×14sym, 230k windows).
- **Phase 1 (EDA gates):** ✅ DONE — premise ALIVE but WEAK; key root-causes below.
- **Phase 3 (Approach-C floor):** ✅ probed — data-seam cost found.

### ⭐ Headline for check-up (honest, evidence-based)

1. **The multi-asset premise is alive but the bar-data signal is WEAK at the linear level.** Per-asset Ridge clean **Spearman all 14 positive, median +0.017** (BTC +0.033, FIL/ETC/BCH ~+0.032). Cross-sectional rank-IC **+0.011 (model) > +0.004 (beta-floor)** — real but small residual ranking alpha.
2. **Pearson was a misleading metric** — y excess-kurtosis **22–124** (ETH 124!) makes Pearson outlier-dominated/negative while the rank signal is genuinely positive. We evaluate on **Spearman / cross-sectional rank-IC** going forward (matches project metric discipline).
3. **BTC-on-bar (Spearman 0.033) ≪ single-asset 25-level (0.072)** — the 5-level bar data loses ~half the BTC signal. **Exactly your hypothesis.**
4. **Approach C (frozen single-asset model) has a data-seam cost:** the 25-level-book pipeline and bar pipeline have different mids + 180s grid offsets → projecting the proven BTC model onto bar alts loses ~60% (BTC self-sanity 0.025 vs 0.065). **⇒ Approach B (bring 25-level BTC *into* the bar pipeline as a native-grid BTC tower) is cleaner and higher-value than frozen-model C.**

### 🚀 LATE UPDATE — cross-sectional framing WORKS (the key positive result)

**Pooled cross-sectional Ridge: OOS rank-IC = +0.0395, IR = 15.3** (walk-forward, clean non-overlap) — **3.5× the per-asset Ridge xsec rank-IC (0.0114)**. Recipe: cross-sectionally z-score features across the 14 assets per timestamp + predict the market-neutral residual + pool. This is a genuinely tradeable long-short cross-sectional signal at the LINEAR baseline (pre-DL/cross-asset/25-level/factors). 

⇒ **Strongly favors pivoting the headline metric to cross-sectional rank-IC / portfolio IR** (the data structure — high common-factor β~0.70, weak per-asset, exploitable residual — is textbook market-neutral cross-sectional). Per-asset Pearson 0.10 remains hard; cross-sectional is where multi-asset breadth wins. DL + cross-asset attention + 25-level BTC should lift 0.0395 further.

### 🔑 Strategic decision for your input

The goal (avg per-asset Pearson **0.10**) is **very ambitious** given bar-data signal strength (Ridge Spearman 0.017; single-asset best was 0.065/0.072 *with* 25-level + heavy DL work). Realistic ladder: DL + cross-asset + 25-level-BTC could plausibly lift per-asset Spearman 0.017 → ~0.03–0.05; **cross-sectional rank-IC (long-short portfolio) is the more natural tradeable target** than per-asset Pearson 0.10. **My recommended priority:** (1) **Approach B** — 25-level BTC tower native to the bar grid (best structural ROI, fixes the BTC-weakness at the source); (2) **Approach A** shared-backbone DL for residual alpha; (3) cross-sectional rank-IC as the headline metric alongside per-asset. **Question for you:** keep pushing the per-asset-Pearson-0.10 framing, or pivot the headline to cross-sectional rank-IC / portfolio IR (which the data structure favors)?

---

## Decisions locked (with user, 2026-05-20)

- Repo: same dir, branch `multi-asset` off `reg-arch-final`, all code in `multi_asset/`, single-asset untouched.
- Target: predict raw per-asset y_600 (MAD-σ norm); dual-caliber eval (per-asset Pearson + cross-sectional rank-IC); demean predictions for bias.
- Universe: 14 USDT-perp primary.
- Reframing (measured): contemporaneous BTC→alt β ~0.70 dominant; lagged 600s lead-lag weak (~0.02); beta-projection floor ~0.045.

---

## Phase log

### Phase 0 — Infrastructure ✅
- 0.1 branch + skeleton + README + NAMING.md (resolves dual_path_v3 vs REG_arch ambiguity)
- 0.2 sync_to_server.sh + server dir + library import verified
- 0.3 bar_loader.py — reads share HDF5 read-only, reproduces QTY scaling bit-for-bit vs share loader, 3 tests green. (Root-caused 2 infra bugs: unanchored `data/` exclude blocked source dir.)
- 0.4 CLAUDE.md multi-asset charter (~140 lines)

### Phase 1 — EDA GO/NO-GO funnel ⏳

**A4 lead-lag — ✅ CONFIRMS reframing (with CIs):** contemporaneous BTC→alt corr 0.61–0.82 (ETH 0.82, BNB 0.71, DOG 0.70, SOL 0.66, XRP 0.61), tight CIs. Lagged trailing-BTC→alt-y600 is small & slightly NEGATIVE (−0.03 to −0.11); **residual-after-beta corr ~0, all CIs straddle zero** → NO tradeable lead-lag momentum at 600s. ⇒ lever = contemporaneous beta-projection + idiosyncratic residual alpha (NOT lead-lag features). The BTC market-factor token should encode CONTEMPORANEOUS BTC state, not lags.

**A6 target dist — ✅ HEALTHY:** per-asset MAD-σ 13bps (BTC) → 28bps (SOL); sign balance ~0.49–0.51 (no directional bias); **clean (stride≥600) autocorr ~0 (0.003–0.06)** → non-overlap eval is sound, no stale-mid artifact; fat tails (excess kurtosis 8–34, Hill α 2.3–3.3) → Spearman/robust matters. Per-asset MAD-σ normalization is necessary (2× vol spread).

**A7 cost tiers — ✅:** median spread BTC 0.017 / ETH 0.043 / BNB 0.185 / BCH 0.304 / SOL 0.454 / ETC 0.511 / LINK 0.767 / TRX 0.810 / DOG 0.877 / LTC 1.197 / XRP 1.771 / DOT 2.147 / ADA 2.355 / FIL 2.857 bps. Tiers — ultra-liquid: BTC,ETH; liquid: BNB,BCH,SOL,ETC; wide (maker-only): LTC,XRP,DOT,ADA,FIL. (depth-cost columns had a key-name bug in JSON — spread numbers are the usable signal; will recompute depth-to-move with A2.)

**A1 universe — ⚠️ FAILED silently** (24min run, no output file; stdout lost with dead subagent). Inefficient (loaded all 57 cols, needs 5). TO RE-RUN efficiently. Low blocking priority — A2 uses a verified-liquid window (2024-06→2025-09) so universe gating isn't on the critical path yet.

**A2 per-asset Ridge SNR (THE GATE) — ⏳ RUNNING:** feature cache build in progress (487 days × 14 syms, stride-180 + clean600, server-local NPZ). Ridge walk-forward + per-asset tiering pending cache completion (~30-60min, share-I/O bound). This answers: how many of 14 assets carry y_600 signal + does BTC-on-bar reach single-asset 0.065.

### Feature builder ✅ (Phase 2.1)
47 per-asset causal features, each mechanism-justified (returns/RV/OBI/book-slope/multi-level-OFI/deep-OFI/trade-flow/mid-asym/spread). TDD **caught a real look-ahead leak** (whole-day MAD norm leaked future→past); fixed with causal expanding-RMS scale. 7 tests green incl. causality perturbation test.

---

## Process lesson (logged)
Subagents launching long jpline jobs (cache build ~1hr) **over-poll and burn tokens** (one used 1.5M tokens polling). FIX: controller owns long-job waiting via background bash waiters (cheap, notified on completion); subagents only for quick compute-and-return work. Applying this going forward.

---

## Open questions / decisions made autonomously
(logged for user review tomorrow)
- Used verified-liquid window 2024-06-01→2025-09-30 (487 days) for A2 gate rather than full 3.9yr (avoids pre-listing poisoning + faster). Full-history walk-forward deferred to post-gate scale-up.
- A1 universe re-run deferred (failed, non-blocking; A2 window already liquidity-safe).

---

## Next when user returns

**Decision needed (above):** per-asset-Pearson-0.10 vs cross-sectional-rank-IC headline; Approach B vs A vs C priority.

**Ready-to-run next steps (pending your steer):**
1. **Approach B prototype** — add 25-level BTC (crypto_data/book_snapshot_25, 2023-01→2025-09) as a BTC tower native to the bar-cache grid (no cross-pipeline seam): build 25-level BTC features on the SAME stride-180 grid as the cache, add as cross-asset channels, re-run xsec Ridge gate → does BTC-derived signal lift alt rank-IC?
2. **Approach A shared-backbone DL** — wire the panel pipeline (Phase 2.4/2.5) + universal REG_arch over 14 syms + CrossAssetAttention; gate vs Ridge (does DL extract residual the linear model can't?).
3. **Feature deepening** — the strongest univariate signals are reversal (ret_mid_300s) + depth/OBI; current 47 feats are a first cut. Alpha-101/cross-sectional factors (Phase 4) gated on xsec Ridge ΔrankIC.
4. **A1 re-run** (failed silently; efficient 5-col version) to finalize the point-in-time universe.

**Known issues / housekeeping:**
- A1 universe audit failed silently (loaded 57 cols, needs 5); non-blocking (A2 window already liquidity-safe). Re-run queued.
- `_sa_btc_preds/` on server is a scratch copy of single-asset BTC preds (harmless; sync --delete will remove if not re-pushed).
- Subagents over-poll long jpline jobs (one burned 1.5M tokens). Going forward: controller owns long-job waits via background waiters; subagents only for quick compute.

**State:** all committed to branch `multi-asset` (HEAD f4c00e8). Feature cache + scratch are server-local (not synced). Single-asset `reg-arch-final` untouched & intact.

---

## UPDATE 2026-06-09 — Shallow-panel spatial ablation NEG → Temporal-Spatial build (Approach A)

> **创建:** 2026-06-09 UTC+8 | **Session:** multi-asset temporal-spatial build | **关键事件:** shallow-panel cross-asset ablation concluded (all NEG); seq_cache build + TemporalSpatialPanelModel + streaming trainer written & smoke-tested
> **状态:** in-progress | **作废条件:** M0/M1 3-fold results land

### Shallow CrossAssetPanelModel spatial ablation (3-fold, panel_cache last-token) — CONCLUSIVE NEG
Every spatial refinement on the last-token MLP panel HURTS monotonically:

| Config | xsec rank-IC | per-asset P | per-asset S | params |
|---|---|---|---|---|
| **Phase 0 baseline** | **0.0494** | **0.0328** | **0.0439** | 75,329 |
| +market token (P1) | 0.0454 | 0.0320 | 0.0413 | 87,937 |
| +factor split (P2) | 0.0449 | 0.0302 | 0.0370 | 92,162 |
| +composite_val+soft_rank (P3) | 0.0421 | 0.0206 | 0.0258 | 92,162 |

Conclusion: the shallow last-token panel is a **local optimum at per-asset P≈0.033**; spatial-mixing refinements (market token / factor split / composite val / soft rank) are EXHAUSTED. The market token is mechanistically redundant (cross-asset attention already constructs the common factor implicitly); composite_val triggers the anti-#24 init-epoch selection (fold-0 P went negative). **The lever is the TEMPORAL axis**, not spatial mixing of a last-token vector.

### Root cause of the 0.033 ceiling (verified)
- Single-asset full-temporal BTC on THIS bar data = **0.058 per-asset P** (proven, hand+raw DL).
- Last-token LINEAR per-alt Pearson ≈ **0** (even negative: alt_with_btc avg P=-0.0074); raw-BTC-feat injection makes it worse.
- The shallow panel threw away the 600-bar sequence + raw LOB that give single-asset its 0.058. → must restore temporal depth per asset, then add cross-asset on top.

### Temporal-Spatial model (Approach A) — built today
- **Data**: `build_seq_cache.py` → per-day all-asset contiguous arrays `F(S,T,44)+Xraw(S,T,5,4)+y+mask+ts` (487 days, ~150GB; one share pass). Avoids the 910GB windowed-NPZ explosion; windows sliced on the fly. RAW-aligned bit-identical to panel_cache at every pred bar (verified 0.0e+00).
- **Dataset**: `seq_panel_dataset.py` — reuses panel_cache for the panel index + train stats (apples-to-apples), streams 600-bar windows day-chunked (vectorized gather).
- **Model**: `temporal_spatial_panel.py` — shared Conformer temporal stem (d=32, 2 blocks, kernel=15) over (B·S,T,44) → per-asset embedding → toggleable cross-asset attention + market token + factor split → per-asset DAQH head. M0=56K / M1=73K / M2=77K params (healthy params:sample). Forward/grad verified.
- **Trainer**: `train_temporal_spatial.py` — streaming, loss = 0.10·pinball + 0.50·Huber(q50) + 0.20·soft_xsec_rank; val metric = 0.5·per-asset-P + 0.5·per-asset-S (the USER target); σ-gate BEST.
- **Milestones**: M0 pure temporal (GATE: per-asset P → ~0.058 single-asset), M1 +cross-asset attn (GATE ≥+0.003), M2 +market/factor (gate each). Spatial refinements re-gated on temporal embeddings (NOT assumed from shallow ablation).

### M0 (pure temporal, hand-features-only) 3-fold RESULT + pivot trigger (2026-06-09)
Pooled per-asset P=0.0249 S=0.0388 xsec-IC=0.0427 β=0.623 mono=0.915. per_fold_P=[0.0367,0.0208,0.0173] (declining).
Per-asset avg (sorted): bnb .054, ada .040, dot .037, **btc .034**, xrp .034, fil .028, eth .027, link .027, sol .026, etc .019, ltc .018, dog .012, bch .003, trx -.009.
**KEY: uniform weakness (no asset hits single-asset BTC 0.058), and BTC itself only 0.034 vs proven 0.058.** M0 omits the raw-LOB/deep-book path that gave single-asset its edge. → PIVOT: data-driven diagnosis workflow (wdor5z6iy) to quantify the deep-book lever (9-bucket cumulative depth profile), non-DL ceiling, and per-asset-Pearson-0.10 feasibility before committing the next build.

### Data deep-dive + loss research + residual pivot (2026-06-10)
**Deep-dive (wf wjohbkr4u) findings:**
- DD1 integrity: scaling/target CORRECT (bit-exact). BUT (a) btc_dualpath windowed_npz is STALE (old 47-feat, lacks ret_300/600s + raw flows; the 0.038 was on inferior features → current-feature ceiling untested). (b) Fat-tail Pearson: spread feats |z|=170-234 flip per-asset Pearson neg on 9/14; winsorize@5σ fixes; Spearman/rank-IC trustworthy.
- DD2 lead-lag: NEGATIVE for y_600. Grid: BTC→alt only at lag5-10s→H=60s (P=0.021), decays + FLIPS NEG for lag≥60s/H≥300s (contemp β=0.72 MEAN-REVERTS multi-min: BTC up→alt down, P=-0.018..-0.028). y_600 best cell straddles 0. Even y_60 lead-lag evaporates in multivariate Ridge (own feats capture it). Alts LEAD BTC short-lag (ETH/SOL/DOG→BTC +0.04). VERDICT: no lagged-BTC channel; multi-horizon≠lead-lag lever.
- DD3 factor: PC1=70% var, betas~1; common factor fwd barely predictable (P=0.013); RESIDUAL is the alpha (residual rank-IC 0.0254 t=10.4 vs raw 0.0126, leakage-clean).

**Loss research (wf w3akih16s) → design:** target=cross-sectional residual (demean+MAD-norm+clip±5); loss=0.30 Huber + 0.70 LambdaRankIC(Lin2026, rank-invariant, normalized O(1)) + 0.10 pinball, ALL on residual (no rank-vs-mag conflict, no gradient surgery). Head=plain monotonic 3-quantile (DROP DAQH). Eval reframed: cross-sectional rank-IC + IC-IR + long-short Sharpe primary; per-asset P/S = single-asset benchmark (winsorize for honesty).

**Plan:** R1 residual+cross-asset+LambdaRankIC (running, current feats, gate vs linear 0.0254). R2 multi-horizon = REGULARIZATION test (not lead-lag). R3 BTC-25-level (/mnt/storage/share/23-25-BTCUSDT) factor forecaster → reconstruct ŷ=β·f̂+r̂ to lift per-asset Pearson benchmark. R4 full REG_arch (DualPathLOBModelV3 built-in cross_asset_attn) on CURRENT features (0.038 was stale).

### R1 RESULT (2026-06-10): cross-sectional residual approach VALIDATED
R1 = TemporalSpatialPanel (Conformer d=32 + cross-asset attn n_xattn=2, current 44 feats) + residual target + LambdaRankIC loss.
**fold-0 clean TEST: xsec rank-IC=+0.0464, IC-IR=9.80** (val 0.0497→test 0.0464, minimal drift). per-asset P=0.018 S=0.022 (low, residual-by-design) mono=0.83.
=> **1.83× linear residual baseline (0.0254); DL beats linear by 83% (architecture EARNS complexity — the user's DL-edge thesis holds on the cross-sectional residual objective, unlike per-asset Pearson where DL≈linear).** Awaiting pooled 3-fold. Next: R4 full REG_arch (raw LOB+FiLM) on current feats, R2 multi-horizon regularization, R3 BTC-25-level factor reconstruction for per-asset benchmark.

### R1 POOLED 3-fold (2026-06-10) — VALIDATED multi-asset cross-sectional model
mean rank-IC=**0.0425** IC-IR=**9.00** per-fold=[0.0464,0.0486,0.0324] (ALL positive, no sign-flip). per-asset P=0.0179 mono=0.887 σ=0.037. n_params=73,380.
=> **1.67× linear residual baseline (0.0254)**; DL+cross-asset beats linear 67%, IC-IR ~9 significant. The cross-sectional residual long-short is the genuine, stable, tradeable multi-asset edge. Fold 2 weaker (regime). R4 (full REG_arch dual-path) auto-launching to test if raw-LOB backbone lifts it further.

### R4 full REG_arch (2026-06-10) — REFUTED; R1 Conformer is production
R4 (PanelREGArch full dual-path + raw-LOB + FiLM + cross-asset, 122K params): pooled rank-IC=0.0358 IC-IR=8.45 per-fold [0.040,0.040,0.027].
vs R1 (Conformer + cross-asset, 73K): rank-IC=0.0425. **R1 BEATS R4 by 19%.** The raw-LOB dual-path does NOT help the cross-sectional residual edge (slightly hurts — overfits thin signal). CONFIRMS: residual edge = cross-asset relative-value structure, NOT per-asset microstructure depth. Low-SNR favors the lean model. **R1 = production model.**
Next: (1) economic long-short backtest (net-of-fee Sharpe) from R1 preds; (2) BTC-25-level factor reconstruction (per-asset benchmark); (3) R1 spatial-capacity tuning.

### A1a NEUTRAL + y_180 horizon BREAKTHROUGH (2026-06-10)
**A1a multipool (architecture keystone): NEUTRAL, not banked.** Per-fold [0.0488,0.0474,0.0335] vs R1 [0.0464,0.0486,0.0324], pooled +0.0007 < +0.003 gate, fold-1 reversed. Inside the ~0.006 fold-noise band (exactly the adversarial reviewer's warning). Lesson reinforced: levers are objective/data-level, not architecture-level.
**R1-y180 (horizon lever) fold-0: rank-IC +0.0613, IC-IR 13.9, per-asset P 0.0335** — +32% over y_600 same-fold (0.0464), already above the 0.06 target on fold 0; per-asset P ~2×. Confirms the linear probe (y_180 carries ~2× signal). Economics tailwind: 3× rebalances/yr, faster edge decay per unit time. Pooled pending (folds 1-2).
Next: y_180 pooled → threshold/economics backtest on saved y_180 preds → magnitude-calibrated loss variant (user's tail strategy).

### y_180 POOLED (2026-06-10): rank-IC 0.0668, ALL folds > 0.06 — target exceeded via horizon lever
R1-y180: pooled rank-IC=**0.0668** IC-IR=15.4 per-fold [0.0613,0.0734,0.0656] (even weak-regime fold2 0.066). vs y_600 0.0425 → **+57%**. Per-asset (folds0-1): residual P avg 0.047 (FIL 0.092, DOT 0.075, SOL 0.071); raw P avg 0.028 (= P_resid×√0.30, mechanical dilution — model never predicts the market part; R3 BTC-25 factor reconstruction is the raw-caliber fix). Magnitude usable at y_180: decile spread 1.66bps/180s, tail escalation monotone (|z|>2: +1.16bps, 5.2% of cells) — threshold strategy has raw material (unlike y_600). Next: economics backtests (threshold+holding) on y_180.

### R3-v1 quick reconstruction test (2026-06-10, saved preds only, CPU)
Found: single-asset REG_arch (25-level, P=0.0646) has saved 3-fold test preds 2025-02-09..09-09 stride-180 — partial overlap with our windows. Quick recon ŷ=β·f̂+r̂ on the 17% overlapping rows: avg raw P 0.0182(resid-only)→0.0217(recon), optimal-combo UB 0.0283. **Factor leg attenuated to 1/3 strength (P(f̂,y_btc)=0.021 vs true 0.058-0.065)** by 61s phase offset + ≤180s staleness + 17% coverage (weak-regime slice). Concept directionally validated; **full R3 = retrain SA factor model on OUR fold layout (dual-horizon y_180+y_600, npz_v4 has both), predictions on 100% of our windows** — next overnight GPU job. Expected: raw P avg ~0.04-0.06, strong alts higher; then directional tail strategy on raw ŷ (retail-fee path).

### R3 因子融合:关键数据发现 (2026-06-10 下午)
1. **LABEL-FEED 差异(重大)**: tardis-25档 mid 与 bar-data mid 的 y_180 label 相关性仅 **0.891**(bar 波动高 31%, diff std 5.7bps)。单资产模型预测力的一部分是 feed 专属(corr(pred, label-diff)=0.041)。**部分解释了 bar-BTC 0.038 vs 25档 0.065 的老谜团 —— label 口径差,非纯信息差。**
2. **可迁移因子强度(3折, 对 bar label)**: P_bar≈0.070, S_bar≈0.092(own-label P 0.107)。因子腿仍强 ≫ bar-BTC 0.038。
3. **y_180 相位差是重构杀手**: f̂ 在我们网格 ffill 有 61-180s staleness,y_180 窗口仅 180s → P_factor 塌到 0.01;滚动 OLS 堆叠在噪声中学配比 → avg -0.008(失败)。修复 = 在 SA 时间戳上重推 r̂(zero-staleness 双腿),进行中。
4. 运维事故(已修复): r3 config 漏改 output_dir,y180 因子结果曾写入 singh_track_reg_arch(已抢救为 r3_factor_y180,原目录改名 *_OVERWRITTEN_BY_R3_20260610;原单资产存档可由 config 复现)。y600 因子运行已终止(label 价值打折,GPU 让位)。

### R3 融合最终结果 (2026-06-10 晚) — 相位对齐后融合成功
**方法**: 残差模型在 SA 时间戳上重推(零 staleness 双腿)→ z-score 50/50 堆叠 → bar 口径 raw y_180 评估(19.8k 对齐时点,3 折全覆盖)。
**结果**: 因子腿 0.038 + 残差腿 0.028 → **融合 raw P=0.0468, S=0.0565 (+66% over 残差单腿)**。逐币全正: BTC 0.070, FIL 0.062, ETC 0.061, DOT 0.057, ETH 0.047, 平均 0.047。**FIL/ETC/DOT 在统一口径下超过 bar-特征 BTC 上限(~0.04)** — "多币超 BTC" 在 raw 口径兑现。
**尾部经济性 (raw 方向策略)**: |z|>2 → 4.1% 时点, +1.46bps/笔, hit 53.6%; |z|>3 转负。**峰值边际 1.5bps < 零售 4bps RT; 在 ≤0.5bps/side 下高度可行**。
**全局结论**: 系统 alpha 真实(残差 rank-IC 0.0668 + raw 融合 0.047 + 经济上 0.5bps 档 Sharpe 6+),但单笔边际 ~1.5-2bps 属于低费率执行者的 alpha。单资产历史 Sharpe 4.4 部分为 label-feed 红利,统一口径下需折扣。
**交付物**: R1_y180 (残差模型+预测), r3_factor_y180 (25档因子+预测), sa_grid_preds.npz (对齐双腿), recon/backtest 脚本与全部 json。

### NX CP0 判定 (2026-06-10 晚) — y_1800 主线确认
linear xsec rank-IC: y600 0.0205(t9.8) / **y1800 0.0125(t3.2)** / y3600 0.0010(死)。σ_y: 36/61/86bps。尾部: |y1800|>25bps 占50%, >50bps 占25%。
**判定**: linear@1800≥0.012 → y_1800 主 horizon ✓;y_3600 砍掉(MTL={180,600,1800});费率数学优于计划(σ=61bps → IC 0.03 零售保本 / 0.045 显著盈利)。R1-y1800 早期 val ~0.050(dense, fold0)— 若干净三折坐实,DL 倍率 ~4×,衰减律被打破。链条继续: R1-y1800 → M1 → P1 预训练。

### NX S0 基线落地 (2026-06-10): R1-y1800 pooled rank-IC=0.0376 — 基线即在轨
三折 [0.0428, 0.0517, 0.0184] IC-IR=5.0。vs linear 0.0125 → **DL 倍率 3.0×(长 horizon 衰减律被打破)**。已越过 CP1 在轨阈值(0.035)与零售保本线(0.03)。σŷ/σy 0.013-0.029(幅度压缩,S6 isotonic 必修);fold2 弱 regime。链条:S1 M1-coarse y1800 已自动开跑(15:22)。

### NX CP1 初读 (2026-06-11 凌晨): 预训练 v1 = regime 拉平器
P1 预训练(881天, 排序即预文本, early-stop ep3 val 0.0584)→ fine-tune y1800 三折: [0.0382, 0.0304, 0.0408] pooled 0.0365。
**关键**: 漂移折 fold2 R1 0.018→P1ft 0.041 (+123%) — regime 多样性先验在漂移最严重处最有价值(回答了"预训练加重还是减轻 drift"——减轻,且集中在痛处)。代价: 稳定折回落(fold1 0.052→0.030),pooled 持平基线、未过 promote 门(vs M1 0.042)。根因假设: 全参数同LR微调的灾难性遗忘(staged-LR 是已知未实现项)→ **v2 = trunk 冻结/低LR 臂**。
运维: M1/R1 旧稀疏存盘导致 battery 仍失效,链后统一密集 repredict 重算全部判定。ft y600 进行中。

### P1ft-y600 三折全升 (2026-06-11 05:03): pooled 0.0476 — y_600 新高
P1 预训练 fine-tune @y600: [0.0528, 0.0513, 0.0385] vs R1 [0.046, 0.049, 0.032] — **三折一致 +0.005,NX 首个全折一致模块增益**(即便 v1 协议带统计错配)。y_1800 的 v1 受错配拖累(根因已修,v2 链自动接棒: 统计统一→repredict 记账→V2a LR/10 统计匹配→WiSE-FT)。30min 巡检 cron 在位。

### 正式配对判定 (2026-06-11 05:11, 密集 repredict 后):
- **M1 多尺度 vs R1 @y1800: Δ=+0.0061, P=0.987 → PASS** — NX 首个正式入账模块,M1 成为 incumbent。
- 去 pinball vs M1: Δ=−0.0062, P=0.031 → FAIL — **pinball 保留**(97% 置信去除有害;肉眼"中性"被配对检验推翻)。
- P1ft v1 vs M1 @y1800: Δ=−0.004 → FAIL(已知,根因=统计错配+LR;v2a 跑中)。

### 可交易输出 schema 承诺 (2026-06-11, 用户硬要求)
最终交付的预测工件(每时点×每币),保证策略层灵活使用:
1. **expected_residual_bps** — q50 × resid_sigma_asset × 1e4(de-norm 后,跨币可比)→ 多空排序/加权;
2. **calibrated_residual_bps** — isotonic m(ẑ) + 99.5% 支撑截断后(S6)→ 尾部/阈值开仓、conviction 加权;
3. **conviction_width_bps** — (q90−q10)×σ → 仓位倒数加权 / 不确定性过滤;
4. **tail_prob_up/dn** — TailBCE 校准概率(S6)→ P(tail)≥p* 开仓门;
5. **resid_sigma / β / f̂(可选因子腿)** — 重构 raw 口径 ŷ=β·f̂+r̂(绝对策略);
6. 健康元数据:σŷ/σy、折号、horizon。
今日已补: fold_preds.npz 携带 resid_sigma/mu/sd(de-norm 因子),归一化预测可还原 bps。S6(isotonic+TailBCE 校准)在 raw-path 之后排期,为策略层的"幅度可信"把关。

### 衰减分析 + val 方法论 (2026-06-11)
IC×距训练结束周数: M1 几乎不衰减(w0 0.050→w5 0.042); V2a 新鲜时仅追平(0.047)随后快衰(w1-3 ~0.02)。
**保留经验**: ① "新鲜模型"假说否定@y1800——M1 学到更持久结构, 生产重训频率可放宽; ② val 选择税量化: argmax 选择在 SE≈0.009 下高估 ~2×SE(val 0.067→week-0 test 0.047), 今后 val 解读一律扣税; ③ val 设计定案: 40天+细化+checkpoint平滑(S3后实验)。预训练终局定位: y600 增强器 + y1800 漂移保险(WiSE-FT 配比中)。

### S2 预训练线收口 (2026-06-11 10:54)
WiSE-FT battery FAIL (Δ=−0.0119); α 曲线向微调端单调,无插值甜点。y_1800 预训练三路全关(v1直调/v2统计匹配/WiSE),机制一致:稳定折=近期局部结构,旧先验无增益。**留存: y_600 预训练全折赢 0.0476; 漂移折保险知识; val选择税/衰减曲线方法论。** y_1800 incumbent = M1 0.0419。S4 双线性接棒。

### 三路审计 (2026-06-11) — 2 个 CRITICAL + 修复 + 经济前提撤回
> **状态:** final | 3 个独立审计 agent(eval/统计、标签/数据、经济)对 NX 全管线 go-through。

**A. 代码/统计层(已修复,commit 0b25ac9):**
1. **σ-gate 未实际执行(CRITICAL)** — trainer 文档写了 σ≥0.02 gate 但代码只查 isfinite;fold-1 多个 best ckpt 处于近塌缩区(σ 0.011-0.013 raw 计价)。已修:gate 强制执行。
2. **sigma_ratio 单位错配(MAJOR)** — 分母用 raw-y σ(≈1.8× residual σ@y1800),系统性低估塌缩风险。已修:分母改横截面 residual y,gate 阈值回归方法论的 0.02。今后日志里 σ 读数会比旧日志大 ~1.8×,跨日志比较须注意。
3. **覆盖混淆(MAJOR)** — M1 的 coarse 分支丢弃每日首小时行,而该时段 R1 的 IC 为负(−0.011),solo 数字白送 M1 ~+0.0010。已修:battery 双模型一律在 finite-pred 交集上计分。
4. bootstrap 机器本身验证无误(day-block 重采样、配对 ΔIC、CI 构造)。

**B. Provenance 钉死(CRITICAL→已解决):canonical y_1800 记账数字以 battery-on-dense-preds 为准** —— M1 0.0405 [0.0359/0.0482/0.0374],R1 0.0334 [0.0341/0.0411/0.0251],配对 Δ=+0.0061 P=0.987 PASS(交集计分后依然成立,且配对剔除首小时行属保守方向)。此前 trainer 日志数字(M1 0.0418/R1 0.0376)由旧 global-thinning 评估产生,作废不再引用。标签/泄漏审计干净(bar "day" 边界=14:05 UTC,已确认不影响折隔离)。

### y_600 费后经济性实测 (2026-06-11 15:00, P1ft_y600 真实预测, CPU 仿真)
> 工件: jpline /tmp/econ_y600.py + /tmp/econ_y600.json | 口径: 720s 非重叠 grid, 13,680 ts/120 天, 线性费用无冲击/滑点/资金费
- **信号侧**: eval-grid rank-IC 0.0475 (t=17.1), gross 1.16bps/期 ≈ 132bps/天, σ_xs=15.2bps — 与 1.55·IC·σ 公式吻合。**lag-1 (720s) pred rank-autocorr 仅 0.225**(y1800 是 0.436)→ y600 信号衰减快, 经济性完全取决于换手管理。
- **全量调仓 (V0)**: breakeven 0.55bps/side — taker≥1bps 全灭 (2bps: −345bps/天)。
- **滞回簿 (V2, EMA0.9 影子目标 + 0.15 不交易带, 换手 0.011/期)**: breakeven **10.9bps/side**; 2bps/side 下净 **+11.5bps/天, 年化 Sharpe 2.5, P(>0)=0.93**; 0.5bps 下 +13.4bps/天 Sharpe 2.9。
- **致命警示: fold 2 (2025-08~09) 所有 variant 费后≈0** (V2 Sharpe −0.02~−0.43)。pooled 正收益由 fold 0/1 扛 (Sharpe 5.9/2.2)。IC 跨折 0.053→0.051→0.038 衰减与 regime drift 已知 pattern 一致。
- 解读: ① "rank-IC 0.05 能否 beat 费率" = **能, 但只在持仓控制下** (滞回压换手 190×, IC 留存靠 rank 翻转的持续性); ② 距 single-asset 4.4 还差: 缺因子腿 (β·f̂ raw 重构)、缺尾部校准 (S6)、fold-2 regime 平。band 0.15 未调参 (无选择偏差, 也未优化)。

### y_600 经济性扩展: 监控频率 + 权重方案 (2026-06-11 15:40)
> 工件: jpline /tmp/econ_y600_ext.py + .json | y_180 逐步记账 (cache y_600 与 panel_ref 逐位一致, 对齐验证过)
- **监控频率结论: 180s 原生网格监控(交易仍只在突破带时)比 720s 同参数同记账 +31% 净收益** (@2bps: +17.3 vs +13.2 bps/天, Sharpe 3.2 vs 2.7)。带宽管成本, 监控频率管捕获——快衰减信号(lag-1 0.22)下早发现真迁移是纯增益。180s 全量调仓灾难 (BE 0.47bps)。
- **最稳健配置 H λ0.97 band0.10: @2bps 三折全正** [+28.5,+7.4,+6.9] bps/天, Sh [5.3,2.4,1.4], BE 8.7bps — 保守引用值。headline H λ0.9 b0.15 (+17.3/天) 的 fold2 ≈ 0, 且 band 选择有轻度 in-sample 性。
- **权重方案: rank 加权 pooled 最优; rank×|z| conviction 倾斜打平且唯一三折全正 @2bps** [1.7,3.6,1.7]; top-3 尾部簿低费档 Sharpe 最高 (5.9 @0.5bps) 但 2× 换手在 2bps 被侵蚀; **风险平价负贡献** (σ 离散度小, 打乱权重; 用的 proxy σ — P1ft tag 早于 resid_sigma 存盘改动, npz 里没有)。
- 综合: 零售 2bps 下可行配置存在且不止一个; 下一档证据 = S6 校准后的真 conviction 加权 + 因子腿叠加。

### EPv2-soft @y600 PARK-强信号 (2026-06-12 00:44) — 全轮最强模块结果
EPv2_y600 (P1ft recipe + 软门, 单轴): pooled **0.0488** vs P1ft 0.0476, Δ=+0.0013, **P=0.939, 三折全正** (+0.0011/+0.0023/+0.0006), mono 0.94/0.94/0.75。正式判定 FAIL (Δ<0.003 screen 门) → park。**但综合 y1800 (fold2 −0.008→+0.005) + y600 (三折全正 P 0.94), 软门 asset-conditioning 在 2 horizon × 4 独立折一致温和为正** — 生产组合配置候选组件, 终验 3-seed 时验证。y600 非正式最佳数字: 0.0488。

### S5 BTC-25 FiLM kill-test FAIL (2026-06-11 22:46) — 方向入账阴性
B25_y1800 (8 深档标量 FiLM, 恒等初始化, +512 params, btc25_state 对齐 100%): pooled 0.0401 vs M1 0.0405, Δ=−0.0004, P=0.434 → **纯中性, 冻结 tower 升级线关闭**。per-fold +0.0039/−0.0042/−0.0009。副信号: mono 0.61/0.07/0.67 — 与 M1L 长上下文同向, **deep-book/长上下文一类信息改善幅度形状但不动排序**, S6 校准子系统可作为它们的正确挂载点 (calib-conditioning 候选, 两条独立证据)。夜间接棒: EPv2-soft @y600 (对 y600 incumbent P1ft 的单轴叠加, fold2 正则修复跨 horizon 迁移测试)。

### EPNet-v2 PARK (2026-06-11 20:53) — fold2 根因修复被证实, 但净增量不可判
EPv2 (软门 [0.5,1.5]): pooled **0.0424** vs M1 0.0405, Δ=+0.0019, P=0.785 → 不达 promote/screen 门, **park 不入账** (y1800 铁律: 单 seed <+0.004 不可判)。per-fold Δ: +0.0010/−0.0002/**+0.0050** — **v1 的 fold2 −0.0080 被软门翻成 +0.0050 (摆动+0.013), "fold2 解在正则/先验"假设获得直接证据**。本轮唯一无负折模块。若未来组合配置需要 asset-conditioning, 用软门版本。S5 BTC25 FiLM 接棒 (20:57, btc25 对齐 100%)。

### M1L 4h-context FAIL (2026-06-11 18:44, 两折早杀)
M1L_y1800 (coarse 跨度 1h→4h @60s 池化, 同 token 数): fold0 +0.0299 (−0.0060) / fold1 +0.0454 (−0.0028), 双折皆负 → 杀, EPv2 接棒。**机制结论: 上下文跨度的甜点在 1h 附近** — M1 的增益不是"越长越好"的单调函数; 4h 换来每日 -16.7% 行覆盖 + 60s 粒度损失, 净负。**副信号: mono 0.56-0.59 (全场最高, M1 ~0.2) + per-asset S 上升** — 长上下文改善幅度形状/校准但伤 rank-IC, raw-path 设计可参考 (校准头可挂长上下文分支)。

### AP attn-pool FAIL (2026-06-11 17:35) — 模块轮三连败定式确认
AP_y1800 (learned-query pool 零初始化 blend, +66 params): pooled 0.0378 vs M1 0.0405, Δ=−0.0027, P=0.158 → FAIL。per-fold Δ: **fold0 +0.0061 / fold1 −0.0042 / fold2 −0.0101**。
**三连 FAIL 元模式 (bilinear/EPNet/AP 完全一致)**: 每个新增自由度都在 fold0(稳定 regime)有内容、在 fold2(漂移 regime)反噬, 配对门被 fold2 一票否决。M1 能 PASS 是因为 coarse 分支是**机制**(更长上下文)而非**拟合自由度**。⇒ 结论: y1800 在当前特征集上, 容量/表达力轴已彻底探完 (7 个变体), 唯余信息集扩展 (M1L 4h 今晚 / S5 BTC25 / raw-path) 与 regime 稳健性两条路。AP 的 mono 0.33-0.47 (vs M1 ~0.2) 仍是有价值的副信号, raw-path 设计时可复用 attn-pool 作为读出层候选。

### Target 工程 NO-GO + 线性天花板基准修正 (2026-06-11 16:00, workflow + 对抗审计)
> 工件: jpline /tmp/target_study{,2}.py + /tmp/target_study.json | 审计: β 因果性用合成 regime-switch 实证通过, eval 跨 variant 一致 PASS
- **β 调整残差 target: NO-GO**。T1(因果 60d β)/T2(cap 加权)/T3(β+clip3) 全部低于 +0.002 门或折间反号。机理前提为真((β_i−1)·m_t 占 T0 残差方差 ~18%, BTC 57%/TRX 50%)但**线性无害**: 该噪声与横截面 z-scored 特征近正交, 只抬训练 loss 不偏 coefficient。Pattern: T1/T3 在 fold2 +0.002~0.004 而 fold0/1 为负 → β 稳定性是 regime 性质, 非稳健杠杆。
- **重大副产物: 线性天花板基准修正**。CP0 引用的 0.0205/0.0125 无法复现来源; 正确口径(clip±5 + tuned α, 与训练 target 同构)的线性 ceiling = **y600 0.0445 / y1800 0.0313**(study X 与 committed phase3_xsec_ridge.json 逐位对账)。⇒ **DL 实际 uplift: y600 仅 +7% (0.0476/0.0445), y1800 +29% (0.0405/0.0313, 网格口径 caveat)**。此前"DL 倍率 3.2×, 衰减律被打破"的叙事作废。
- **战略含义(根因①强化)**: 44 维手工特征的信号几乎全部线性可提取——当前特征集上架构迭代无 2× 空间, **信息集扩展(raw-path)是唯一数学上可能的大杠杆**; y1800 的 DL 边际(+29%)比 y600(+7%)更真实。

### M3a EPNet FAIL (2026-06-11 15:01, battery 正式判定)
EP_y1800 (M1+逐资产输入门, 恒等初始化, +2.2K params): pooled 0.0385 vs M1 0.0405, 配对 Δ=−0.0020, P=0.245, CI[−0.0075,+0.0034] → FAIL。
**根因**: 全部败在 fold2 (−0.0080; fold0 +0.0024 / fold1 −0.0003)。fold2 val 创新高 (+0.0409, ep13) 但 test 最差 (0.0294) — **逐资产门给了 regime-specific 特征相关性的自由度, 在漂移折上学到不可迁移结构**(与 EPNet 在稳定折小幅为正一致)。Retry recipe (不排队, 留档): gate 范围收窄 [0.5,1.5] / gate 参数 wd 加重 / 或仅在 fold-stable 资产子集上开门。**机制方向入账**: asset-conditioning 有内容但当前形态过不了漂移折——与"预训练旧先验在漂移折反而有价值"互为镜像, 提示 fold2 的解在 regularization/先验而非容量。接棒: attn-pool A/B (15:05 开跑, +66 params 零初始化 blend)。

### S4 双线性 FAIL (2026-06-11 12:15, 两折早杀)
BL_y1800(M1+低秩双线性,零初始化门): fold0 0.0355 vs M1 0.0359(持平)、fold1 0.0434 vs 0.0482(−0.0048)。两折后配对 Δ 达 +0.004 门槛需 fold2 +0.017,数学上不可能 → 按"前两折定输赢"纪律早杀。**机理结论: 跨资产乘法交互(相对价值)在 attention 已有的线性混合之上无增量**——与 R4 重型逐资产容量、v3 gate 扩展同向,空间轴表达力不是瓶颈。接棒: M3a EPNet 输入门(12:20 开跑,链含 battery)。

**C. 经济前提撤回(CRITICAL)** — CP0 时写下的"σ=61bps → IC 0.03 零售保本"(本文件 2026-06-10 晚)基于 κ=2.0 的解析换手假设。在 M1_y1800 真实预测上实测:κ=1.21,gross=1.55·IC·26.3bps/期,pred rank-autocorr(1800s)=0.436 → 自然换手 0.93/期;在原宣称工作点(τ=0.41)**净 −0.63bps/期,Sharpe −4.4(2bps/side)**。深 EMA 持仓簿可转正(+1.1~+2.3)但 P(mean>0) 仅 0.74-0.90,统计不显著。**结论:y_1800 当前 IC 水平(0.0405)在零售费率下不可交易,"零售保本线 0.03"论断撤回。** 战略含义见正式汇报(同日)。
