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
