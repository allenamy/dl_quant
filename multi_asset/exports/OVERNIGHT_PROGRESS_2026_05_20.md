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
