> **创建:** 2026-07-02 10:55 +08 | **Session:** fable-regime-breakthrough Phase-1 | **状态:** final (appendix) | **作废条件:** 无(原始记录)

# Phase-1 完整产出 — regime-breakthrough-p1 workflow (5 mappers + 6 root-cause + verify + gaps)



---

## MAP: results-history

# Map — BTC perp y_600 results & experiment history

## 1. Honest per-month results (caliber: DENSE = stride-180 overlapping Pearson; cd-CLEAN = non-overlap ≥600s, per-UTC-day corr averaged; λ_q=0.1, 450d rolling monthly retrain, EMA no-peek — `docs/2026-06-28_FINAL_y600_deliverable.md` §1)

| month | DENSE-P | cd-CLEAN-P | β | regime |
|---|---|---|---|---|
| 2025-08 | .0355 | .0385 | 1.82 (σ .019 near-gate) | normal |
| 2025-09 | .0583 | .0578 | 1.41 | normal |
| 2025-10 | .0785 | .0813 | 1.70 | STRONG |
| 2025-11 | .0427 | .0679 | 0.82 | strong |
| 2025-12 | .0188 | .0458 | 0.67 | choppy |
| 2026-01 | .0150 | .0121 | 0.46 | drift |
| 2026-02 | .0113 | .0157 | 0.38 | drift |
| 2026-03 | .0224 | .0210 | 0.52 | drift |
| 2026-04 | .0183 | .0307 | 0.19 | drift |
| 2026-05 | .0176 | .0166 | 0.32 | drift |

Pooled: DENSE .0318 / cd-CLEAN .0387 (headline); IC-IR 1.70; 10/10 months positive; β UNSTABLE [.19,1.82]. Vs new mandate ≥0.08/month: only 2025-10 meets it. Legacy 0.0646 = 5σ-clip+EMA-demean caliber (honest raw 0.037/0.043).

## 2. Lever → verdict (evidence: deliverable doc, `docs/v2_autonomous_overnight_2026_06_24.md`, PARADIGM doc, dualsrc memory)

| Lever | Verdict |
|---|---|
| deeper-perp tower d_perp 16→32 + gate α.02 | **WIN** strong DENSE .052→.080 (2025-04); regime-dependent |
| dp48 (32→48) | NEG (over-param) |
| regime FiLM/bias (`adaptive`) | WIN both regimes vs nobasis; but "CLEAN 0.105" later shown cross-day-pooling-inflated |
| mh180 (y_180 aux) | +0.0139 CLEAN single-fold strong; conflicts on weak folds; multi-fold never run |
| long-context ModernTCN/X_long (3 tests incl real-X_long) | NEG (strong −.020/−.024) |
| basis-SEQ/LEVELS FiLM | β-collapse (−2.95) — the dualsrc breaker |
| basis-dynamics additive | choppy Ridge +.0076 but strong −.014, pooled net-NEG; corr-flip falsified |
| snapshot-skip / OBI skip | ABANDONED (choppy signal in window-mean; 0.169 Ridge = bid-ask bounce, −1.9bps net) |
| regime-MoE | real gain only +.012 (2025-08); σ-collapse on drift; FAIL |
| OI-router MoE / unified all-levers / regime-gated gates | all FAIL (gates stay .51; weak-fold regression) |
| choppy-specialized training (low-trend days) | WIN .0167→.0311 OOS — refuted the 0.044 linear ceiling |
| rolling monthly retrain + patience≥10 | WIN (+40% vs frozen, β→1; σ-collapse was patience, not window) |
| λ_quantile 0.5 (2b) | WASH same-checkpoint (pooled −.007 DENSE) |
| funding 8h / premium 5m/1m / OI/L-S | all below +.003 gate (best +.0027); 4h "+0.19" = overlap inflation; clean ~.02 @30-60min |
| perp trades / perp-64 concat | Ridge −.0099 / −.0098 (#29) |
| spot-target switch | negligible (ratio 0.96) |
| multi-agg, adaptive-norm, spectral, V-REx, recency-online, Koopman, mutation-factors, within-fold TTA | all null/hurt/leak on choppy-drift (mapping drift = random walk, IC-corr .036) |
| Trading: short-only/funding-gated/tail-hold/4-exits | all converge: clean drift-neutral ~1-3.4bps < cost, z≈1.6-1.97; long/short asymmetry = holding×downtrend artifact |

## 3. Retracted/corrected (fragile knowledge)

1. 2b λ0.5 "+0.013-0.020" → wash (mismatched checkpoints).
2. Spot-target lever: "2x" → "0.2%" → "1.33x" → final ~0.96 negligible (3 reversals in one day).
3. MoE "+0.0395 nearly-doubled" → broken-β(0.62) baseline; real +0.012.
4. TTA 2026-02 lift → shuffle-null leak.
5. "Regime causally learnable, IC +0.5" → degenerate AR1 label + vol-persistence.
6. Ridge 0.169/0.111 ceiling → non-tradeable bounce (`pt_vwap_return_1s`).
7. Cross-day-pooled CLEAN (strong "0.105≥0.10 MET") → inflated; honest within-month 0.05-0.067.
8. "Recency always hurts" → conditionally helps; rolling beats frozen.
9. "funding/OI absent on disk" → stale; they exist (`data/funding/`).
10. Milestone 4.4/2.8 Sharpe superiority → annualization (~15-24×) + regime (92% fold-0) + caliber; no real IC gap.
11. "Choppy 0.044 ceiling / Ridge>DL" → caliber artifact; DL=Ridge parity, specialized DL exceeds snapshot.
12. Long-ctx NEG verdict twice invalidated (bug, degraded feats) before final clean NEG.
13. "long dead/short alive" → symmetric signal (~+0.8bps/side drift-neutral).

## 4. Open threads never closed

- **Liquidations/derivative_ticker**: only untested orthogonal source; infra-gated (192.168.8.11 FFData not in rsync); mechanism case POSITIVE (high-funding short edge +1.83bps, §8.4).
- **mh180 multi-fold validation**; rich-regime 14-descriptor FiLM (+0.0125 single strong fold) — both single-fold only.
- **Positioning-regime transfer-break** (`signflip_rootcause.py`): in-month signal exists 9/10 months (2026-02 +0.065 in-month!) but prior→test map breaks at funding/OI/L-S inversions — diagnosed, never exploited (conditional-recency untried).
- Choppy-specialized val→test drift gap (0.053→0.031) unresolved.
- Short-edge never falsified on a sustained up-trend month.
- corr(yhat, d_basis) mechanism check pending (§10.6/10.7).
- Deliverable doc header says "in-progress (7/10 months)" though table shows 10 — 2026-03/04/05 aggregate re-run flagged but doc not marked final.


---

## MAP: code-architecture

FINDINGS — model/training/data map (final λ_q=0.1 walk-forward paradigm)

**Config identity:** final runs = `configs/walkforward/wf_YYYY_MM.json` (25 files, 2024-06..2026-05): train_days=450, lambda_quantile=0.1, use_ema=true, monthly `fold_test_starts`; aggregated EMA no-peek from `experiments_local/wfEMA/` via `multi_asset/eval/final_deliverable_l01.py` → `exports/final_l01/`. `configs/wf550/` = 550d variant (patience 10, ep32); `configs/lossab/` = λ_q A/B (Q02..Q10).

**Input tensors** (cache `data/npz_v2arch`, `multi_asset/data/build_v2arch_npz.py`):
- `X` (N,600,88) f32 = 64 SPOT hand feats (spot book+trades) + 16 PERP-trade channels (`PERP_TRADE_IDX`, :131,:391) + 8 bounded cross-venue channels incl. `x_basis_bps` clip±50, mid-ratio, spread/depth/OBI/mpdev/rvol/tradeflow diffs (:140-147, :400). Builder docstring "72" is stale; code writes 88.
- `X_raw` (N,600,20,4) SPOT LOB → Path-B tower; `X_raw_perp_deep` (N,600,20,4) PERP LOB → gated residual (`use_perp_residual=true`, d_perp=32, α_init=0.02).
- `regime_prior` (N,6) = vol_1h, spread_mean_1h, obi_trend_1h, price_return_6h, hour_sin, hour_cos — SPOT-derived, causal rolling (`src/features/regime_prior_features.py:82-107`).
- Target: leak-free re-anchored perp log-return [t, t+600] (`build_perp_y_clean.py:81-129`).
- **NO funding, OI, liquidations, positioning anywhere.** Basis only via the 8 cross channels.
- Sequence: 600×1s window, stride 180s; model context = 10 min only.

**Normalization:** per-fold static per-channel z (mean/std from 450d train only, clip±10, `src/training/dataset.py:554`; stats `train_dual_lob.py:870-872`); y = (y−med)/σ_train clip±5σ (`train_dual_lob.py:878`, `dataset.py:620-623`); RevIN per-instance/per-window on X only (`dual_lob_regarch.py:491-492`); raw books & regime_prior fed raw.

**Regime conditioning today:** (a) `use_film_multistage`: FiLMGate (affine γ,β zero-init, `src/model/film_gate.py:38-84`) at conformer block1/block2/final-pool, driven by the raw 6-dim regime_prior; (b) `use_regime_film`: extra FiLM on pooled h_pred driven by RegimeFeatureExtractor — 6 vol stats of feature-0 computed on **post-RevIN** x_feat, **batch z-scored** (`src/model/regime_film.py:64-101`); (c) `use_regime_bias`: zero-init MLP(6→16→1) additive output bias (`dual_path_model_v3.py:875-884`). All causal; all **purely affine**. RegimeMoE / rich-regime / OI-regime / snapshot-skip exist in `dual_lob_regarch.py` but are OFF in the final configs.

**Loss** (dul_config): 0.1·pinball(q10/50/90) + 0.5·utility_rank(α=0) + 0.5·dir_huber(δ=2, w_wrong=0 ⇒ plain Huber) + 0.1·sign-BCE (tail_focal_1p5) + 0.3·mag_focal_huber(clip 0.3-3.0); λ_pearson=λ_calib=λ_beta_calib=0.

**Checkpoint/EMA:** composite 0.5P+0.5S val selector, σ-gate σŷ/σy≥0.02 + 5e-4 margin (`train_dual_lob.py:532-546`); **low-σ fallback ckpt persisted when gate never fires** (:589-638, flagged in metrics.json); EMA decay 0.999 with warmup guard; test preds denormalized with train σ (:720-721). Fold: train 450d → embargo 1d → val 45d → embargo 1d → test 28d (`_build_folds` :747-768); lr 8.49e-4, batch 512, wd 0.01, ep25/pat5.

**FLAGS — cross-regime adaptation limiters:**
1. Regime-FiLM extractor consumes post-RevIN x_feat → vol_1200≈const, mean_feat0≈0; absolute-vol regime info destroyed before the gate — `dual_lob_regarch.py:492,637` + `regime_film.py:81-97`.
2. Extractor batch z-scores its 6 descriptors → regime is relative-to-batch; a uniformly-shifted regime month is invisible at eval — `regime_film.py:98-101`.
3. Regime gates see only 6 spot price/book descriptors; no funding/OI/basis/positioning input despite `data/funding/*.csv` existing — `regime_prior_features.py:82-107`, wf config d_prior=6.
4. All regime conditioning affine (γ⊙h+β + scalar bias) — cannot flip momentum↔reversion functional form; RegimeMoE coded but OFF — `dual_lob_regarch.py:68-129` vs `configs/walkforward/wf_2025_10.json`.
5. Static 450d-frozen x_mean/x_std + y_σ applied to drifted 2026 test months — `train_dual_lob.py:870-880`, `dataset.py:554`.
6. y clipped ±5σ_train — fat-tail regimes saturate labels — `dataset.py:620-623`.
7. Uniform-weight 450d window (~15 months), no recency weighting/online update — `wf_*.json training.train_days`.
8. Amplitude anchor only λ_q=0.1 vs 1.4 total rank/direction weight → σŷ/σy collapse in drift months (2026 MISCAL rows) — wf dul_config; lossab Q10 tested λ_q=1.0.
9. Fallback persists σ<0.02 checkpoints → 2026 headline numbers can come from miscalibrated ckpts — `train_dual_lob.py:597-604`.
10. `X_long` 4h context built into cache but never read by LOBDatasetV2 → only 600s context reaches the model — `build_v2arch_npz.py:47`.
11. regime_prior fed unnormalized → vol_1h scale drift 2024→2026 shifts FiLM operating point — `dual_lob_dataset.py:177-187`.
12. Val=45d pre-test checkpoint selection under documented month-to-month concept drift → stale selection for the test month — `train_dual_lob.py:755-761`.
13. Perp book enters only as tanh(α)·g scalar-gated residual (α_init 0.02) — squeezable to ~0, nothing monitors it — `dual_lob_regarch.py:541-543`.
14. 2/6 prior dims are hour_sin/cos (session features previously net-negative) — `regime_prior_features.py:104-107`.


---

## MAP: data-assets

## LOCAL data/funding/ (all Binance-API sourced, verified head/tail)

| file | rows | range (UTC) | granularity | columns |
|---|---|---|---|---|
| btcusdt_funding.csv | 7,438 | 2019-09-10 → 2026-06-24 | 8h (settled) | fundingTime_ms, datetime_utc, fundingRate, markPrice (empty early) |
| btcusdt_premium_index_5m.csv | 356,887 | 2023-02-01 → 2026-06-24 04:30 | 5m OHLC | openTime_ms, datetime_utc, pidx_open/high/low/close |
| btcusdt_premium_index_1m.csv | 1,784,435 | 2023-02-01 → 2026-06-24 04:49 | 1m OHLC | same schema |
| btcusdt_metrics_5m.csv | 356,412 | 2023-02-01 → 2026-06-23 | 5m | create_time, symbol, sum_open_interest, sum_open_interest_value, count/sum_toptrader_long_short_ratio, count_long_short_ratio, sum_taker_long_short_vol_ratio |

Same relative paths mirrored on server (referenced by `multi_asset/data/add_funding_channels.py:20-21`).

## SERVER caches (`/mnt/storage/private/work_hsy/quant_research_multi_asset/`)

Best model = configs/wf550/*.json → `npz_dir: data/npz_v2arch` (`wf550_2025_10.json:5`), `tv_overlay_dir: ""`, use_perp_residual+regime_film.

| cache | size | coverage | content (build_meta.json) |
|---|---|---|---|
| **data/npz_v2arch** (PRODUCTION input) | 160G | 2024-01-01 → 2026-05-31 (871 day-npz) | X (N,600,88)=64 SPOT hand + 16 PERP-trade (pt_*) + 8 cross (incl **x_basis_bps**); X_raw spot LOB (20,4); X_raw_perp_deep perp LOB (20,4); X_long (240,10) 4h 60s-pooled incl l_basis_bps; regime_prior 6-dim = vol_1h/spread_mean_1h/obi_trend_1h/price_return_6h/hour_sin/cos (`src/features/regime_prior_features.py:15-22`) — **no funding/OI anywhere** |
| data/npzv4_dual (older wf configs) | 70G | 2023-01-01 → 2025-09-30 (978) | spot64 + 8 cross only |
| multi_asset/exports/btc25_raw_perp | 8.5G | 2024-06-01 → **2025-09-30** (484) | 104-ch perp raw book f16 |
| multi_asset/exports/seq_cache | 143G | 2024-06-01 → **2025-09-30** (487) | spot seq features |
| data/npz_perp 139G; npz_spot2perp_clean 66G; btc_feat64_perp 12G; btc_trade_perp 1.3G | | sources for v2arch | |

## DECISIVE TABLE — feature family → on disk → fed to best model

| family | on disk? | FED? |
|---|---|---|
| spot book L25 | YES (Tardis spot; npz_spot2perp_clean) | YES — 64 hand feats + 20/25-level raw |
| perp book L25 | YES (Tardis binance-futures; btc25_raw_perp 104ch) | YES — X_raw_perp_deep 20 levels (perp-residual tower) |
| spot trades | YES (Tardis trades/binance) | YES — inside spot64 tradeflow feats |
| perp trades | YES (btc_trade_perp) | YES — 16 pt_* channels |
| **funding rate 8h** | **YES (2019→now)** | **NO** — only experimental `npz_v2arch_fundch` (add_funding_channels.py); wf550 reads plain npz_v2arch |
| **premium index 1m/5m** | **YES (2023-02→now)** | **NO** — nowhere in X/regime_prior |
| **OI 5m** | **YES (2023-02→now)** | **NO** |
| **top-trader L/S ratio** | **YES** | **NO** |
| **taker L/S vol ratio** | **YES** | **NO** |
| basis (spot−perp) | derived from both books | PARTIAL — x_basis_bps 1s level (600s window) + l_basis_bps 4h pooled; no funding-anchored/mark-price basis, no multi-day dynamics |

**HEADLINE — on-disk-but-NOT-fed:** funding rate, premium index (1m!), OI, top-trader L/S, taker L/S — the entire positioning/derivatives-pressure family, i.e. exactly the drift-2026 inversion channel hypothesized in add_funding_channels.py:6-7. Only linear-additive Ridge (+0.0012) and FiLM/router forms were tested; raw-channel DL feed exists as script but is NOT in production configs.

**Granularity/coverage caveats:** funding 8h = step function vs 1s grid (ffill ≤t, 3 updates/day — slow-moving conditioner, not per-window signal); premium 1m is the only fast proxy of funding pressure (600s window sees 10 bars); metrics 5m ffill with create_time≤t alignment. Gaps: btc25_raw_perp + seq_cache END 2025-09-30 — missing the entire 2025-10→2026-05 eval span (npz_v2arch covers it); metrics/premium start 2023-02 (no 2023-01); Tardis raw ends 2026-05-31 while funding CSVs run to 2026-06-24.


---

## MAP: prior-regime-work

## (1) Exact prior regime findings

**A. OBI-snapshot skip-path** (memory `choppy_regime_ceiling_obi_snapshot.md`, 10-agent workflow):
- Original claim: choppy y600 ceiling = stationary Ridge on 6 last-timestep OBI feats **P 0.0438 CLEAN**; last-ts OBI IC 0.045 vs mean-over-600s 0.0045 (10× destruction) → Conformer averaging destroys the snapshot; recommended zero-init linear skip (last-ts feats → DAQH head, ~224 params) to lift DL 0.025→0.038-0.042.
- SELF-REFUTED in same memory's UPDATE: choppy-SPECIALIZED REG_arch hit OOS **0.0311** > OBI-snapshot 0.029; OBI added only **+0.0007** on top → focused training, not skip-path, was the lever.
- `docs/v2_autonomous_overnight_2026_06_24.md` killed it three times over: (i) L1169-1188 D3 test — window-MEAN Ridge **+0.0267** BEATS last-step **+0.0175** (both +0.0293), falsifying "Conformer averages away OBI"; apples-to-apples same fold/caliber Ridge 0.0293/0.0315 ≈ DL 0.0284/0.0294, DL-adaptive CLEAN 0.0402 > Ridge → "no DL bug, skip-path MOOT". (ii) Re-justified 2026-06-26 when Ridge CLEAN 0.169 (2025-10)/0.111 (2025-11) proved leak-safe (10-seed permute-train-y null ~0.007, 23×). (iii) Decomposition: 0.169 = ONE feature `pt_vwap_return_1s.last` (univ −0.1725) = **bid-ask bounce** — book-MID 1s-return collapses to +0.0349; net-of-cost −1.89bps taker/−0.29bps maker. snap3 DL runs: 2025-08 skip +0.046 < base +0.057; 2025-09 +0.072 but β=2.73 σ=0.026 (degenerate). **ABANDONED as "IC-without-PnL trap"** (doc L2129-2260).

**B. Front-b basis-dynamics** (c7e3c6c, 2026-06-23): X=88 Ridge on 2026-05 choppy CLEAN 0.0360 → +basis-dyn(8)+regime(2) **0.0437 = +0.0076** (passes +0.003 gate); revised in-data choppy linear ceiling ~0.044. Features (`multi_asset/data/add_basis_dynamics.py` L26-35, 10-ch X_basis block, all ≤t): basis_rel, basis_ema_fast(60), basis_ema_slow(300), basis_z (z-vs-roll300 equilibrium), basis_vol (std60 of Δbasis), basis_mom_60/300, basis_ar1_120 (reversion strength), leadlag_5 (perp↔spot rolling-corr asymmetry k=1..5), arb_pressure (perp_obi_L5 − spot_obi_L5). Regime feats (`add_regime_features.py` L43): rg_vol_pct, rg_trend_strength, rg_basis_regime.

**B DL-integration status** (doc L729-880): (i) broadcast-into-X (dp32_aug X=98, `configs/v2arch/dp32_aug_2026_05.json`): val P −0.007..+0.002, σ collapsed — FAILED; (ii) proper FiLM-additive path (regime_prior 6→16 + use_regime_bias, dp32_rpadd): **3× infra failure** (worker deadlock / lazy-stall / preload hang) — "DL-translation of the +0.0076 remains unconfirmed (infra-blocked)"; (iii) same additive path on STRONG 2025-04: 0.0636/0.1022 vs baseline 0.075/0.113 = **−0.011..−0.016 CLEAN, FAILS gate**; Ridge apples-to-apples confirmed regime-specificity (strong −0.0137 vs choppy +0.0076). 6ab2bf1 filed it as "marginal".

## (2) Status table

| Lever | Recommended by | Implemented? | Died on |
|---|---|---|---|
| OBI/snapshot skip-path | obi_snapshot memory | **YES** — `dual_lob_regarch.py` L270/343-364/749-771 `use_snapshot_skip` (zero-init Linear(n_feat,3)+configs *snap*.json), default OFF | 0.169 = bid-ask bounce (mid +0.035, net −1.9bps); snap3 DL worse/degenerate; DL≈Ridge parity on choppy |
| Basis-dyn+regime → DL input | c7e3c6c | **PARTIAL** — cache+builders exist; choppy DL never cleanly ran (infra); strong DL NEGATIVE | choppy: infra-blocked, unconfirmed; strong: −0.011..−0.016 (regime-specific dilution) |
| Choppy-specialized training | obi memory UPDATE | YES (`train_choppy_focus.py`) | Won (0.0167→0.0311 OOS) but val→test drift 0.053→0.031 irreducible (concept drift = random walk) |
| Long-context (k51/101 γ-FiLM) | front-a/b | YES | Strong −0.023..−0.028 (1e73b45); choppy +0 (efe0baf) |
| regime FiLM+bias ("adaptive") | 6ab2bf1 | YES — production | Survived: strong 0.105/choppy 0.040 CLEAN |
| regime-MoE / OI-MoE / gated-unified / mutation | dccc66d | YES | MoE +0.012 only (0.040 claim retracted β-artifact); gates cosmetic ~0.51; OI unusable all 4 wirings |
| Recency/online retrain | nonstationarity memory | YES | HURTS (recent-60d −0.019 vs all-history +0.0152) |

## (3) Recommended but never built (headline)

1. **DL-side confirmation of the +0.0076 choppy basis-dynamics lift** — the only PASSED-gate choppy lever whose DL translation was never executed (infra-blocked 3×, then deprioritized as "marginal"). The lever is proven linear-real, regime-specific (needs choppy-conditional application, not naive additive).
2. **Funding/OI/liquidations as model INPUT channels** — deferred ≥3 sessions as "the 0.06 needs orthogonal data" answer; dccc66d dumped the data (`dump_binance_funding.py`/`dump_binance_metrics.py`, `data/funding/*`) and gated OI (unusable) but funding/premium-index as DL sequence channels never reached a committed DL run.
3. **Bounce-free instantaneous features** — the 0.169 thread proved a huge last-tick reversion exists; the mid-based (tradeable) variant (+0.0349) was measured but never engineered as a feature/skip input.
4. **regime-conditional lever routing done causally** — every attempt used learned gates (failed, ~0 gradient) or future-y stratification (banned); a hand-specified causal regime switch (e.g., rg_trend_strength threshold picking adaptive-vs-mh180) was diagnosed as needed (mh180 CLEAN 0.1165 strong but hurts weak) yet never tested.


---

## MAP: caliber-target

FINDINGS

**(1) Implemented caliber definitions** (honest_aggregate_causal.py L29-39; final_deliverable_l01.py L30-45; eval_caliber.py L55-83). Inputs: `q = predictions[:,1]` (q50, std-units, y standardized as (y_raw − y_median)/y_sigma at train time), stride-180s test rows.
- **DENSE**: plain `pearsonr(q, y)` over ALL month rows (labels overlap 3-4×). No clip, no demean. Pooled = unweighted mean of per-month DENSE-P.
- **per-day-CLEAN**: group by UTC day (`ts//86400e6`); per day, greedy non-overlap keep (Δts≥600e6 µs, single offset 0); day kept only if >20 rows AND q.std>1e-12; Pearson/Spearman per day; month = unweighted day-mean; pooled = unweighted month-mean. No clip/demean, but per-day corr **implicitly day-demeans** (strips drift — why CLEAN 0.0387 > DENSE 0.0318).
- eval_caliber "CLEAN" is a **different caliber**: month-level (not per-day) non-overlap, 4-offset average, and it APPLIES the npz mask (aggregators don't). β everywhere = cov(y,q)/var(q) (y-on-ŷ slope).

**(2) Strictest defensible 0.08 target**: for EVERY calendar month (min, not mean), fixed pre-registered checkpoint rule (always-EMA, no per-month picking), mask-applied rows, full ≥28-day test windows: (a) per-day-CLEAN Pearson ≥0.08 with collapsed/short days counted as 0 (not dropped); (b) companion DENSE ≥0.06 (guards against day-demean-only signal); (c) health gates: σŷ/σy≥0.02, β∈[0.5,1.8] (the causal-script band), decile bin-Spearman ≥0.8, P/S divergence <30%; (d) day-level block-bootstrap 90% CI lower bound >0. Current 2025-08 (N=4417≈9.2 days) and 2025-09 (N=3600≈7.5 days) are partial-month tests weighted equally in pooled — must re-run full.

**(3) Coverage gap**. Trainer needs test_start(10th) − (450 train + 45 val + 1 embargo) ≈ −496d of cache. Current trajectory cache `npz_v2arch` (server data/npz_v2arch): **2024-01-01 → 2026-05-31, 872 days, 160GB (~190MB/day)**. Back-extension to 2025-01 (7 new months 2025-01..07) needs cache from ~2023-09-01 → **build 2023-09-01..2023-12-31 (~122 days, ~23GB) of npz_v2arch**; to 2024-07 (13 months) needs ~2023-03-01 → **build ~306 days (~58GB)**. Tardis (2023-01-01 start) covers both; absolute earliest 450d-caliber test month = 2024-06. GPU: 7×2-4h = **14-28 GPU-h** (2025-01 target) or 13×2-4h = **26-52 GPU-h** (2024-07), single 3090; cache build is CPU/IO. Note: configs/walkforward/wf_2024_06..wf_2025_07.json already exist but point at `npzv4_dual` (2023-01-01→2025-09-30, exists, 70GB, spot-64+8-cross layout, train_days=700) — NOT apples-to-apples with the npz_v2arch/450d trajectory.

**(4) Bugs/inconsistencies**:
- **Mask ignored**: npz files carry `mask` (66-91 padded rows/month, y≡0); honest_aggregate_causal.py L22-28 and final_deliverable_l01.py L22-28 never apply it (eval_caliber does). Measured deflation up to +0.0009 P (2025-09), ~811 bogus rows total, and they leak into both production CSVs (L109/L156) → likely present in exports/final_l01/y600_backtest_dataset.csv.
- **Health-gate mismatch**: causal script `healthy = σ≥0.02 ∧ 0.5≤β≤1.8` (L40) vs final_deliverable `σ≥0.02 ∧ β>0` (L87) — "%healthy" not comparable across reports.
- eval_caliber.py L68-70: `span`/`offs` computed then discarded; loop uses `range(n_offsets)` (dead code, behavior coincidentally OK).
- eval_caliber `_score` returns P=0.0 (not NaN) on collapse — collapsed models read as 0, unflagged.
- perday_clean silently drops collapsed/short days → partially-collapsed months inflated.
- DA: final_deliverable counts q==0 rows; eval_caliber excludes |q|≤1e-12.
- Aggregator clean = single offset (offset-choice noise); eval_caliber = 4-offset mean with off-std.

Files: /Users/haosiyu/Desktop/quant_research/multi_asset/eval/{honest_aggregate_causal.py, eval_caliber.py, final_deliverable_l01.py}; configs/{walkforward,wf550}/; server caches /mnt/storage/private/work_hsy/quant_research_multi_asset/data/{npz_v2arch,npzv4_dual}.


---

# ROOT-CAUSE FINDINGS (adversarially verified)



## H1-collapse-mode — SUPPORTED (conf: high)

**Verification:** refutes=0
- held: NOT REFUTED. I recomputed the load-bearing numbers two ways from /Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv: (A) an independent code path (per-month every-4th-row non-overlap subsample at two phase offsets, gap-asserted >=720s, manual numpy cov/corr, no scipy) and (B) a from-scratch re-implementation of their greedy >=600s subsample (scripts: scratchpad/verify_h1.py, verify_h1b.py). Results: (1) Greedy path reproduces the finding EXACTLY: drift CLEAN per-day P = 0.0171/0.0234/0.0101/0.0182/0.0103 (claimed 0.017/0.023/0.010/0.018/0.010); beta strong/normal/drift = +30.80/+15.82/+5.05 (claimed 30.8/15.8/5.1); drift IC_conf=+0.0303 vs rest +0.0002, pnl_conf +0.80bps vs all -0.02bps (exact); drift bot-decile hit 53.2% z=+2.54 n=1608 vs top 50.8% z=+0.65 (exact); strong bot 57.6% z=+3.93 / top 54.2% z=+2.16 (exact); sub-split IC_conf 2026-01..03 = 0.0485/0.0569/0.0574, 2026-04/05 = +0.0084/-0.0082 (matches 0.049-0.057 and +0.008/-0.008). (2) The verdict-carrying patterns survive my independent subsample: DENSE per-month P (subsample-free) matches claim to 4 decimals (drift 0.0154/0.0315/0.0095/0.0123/0.0185, all positive → sign-flip ruled out); drift rest-80% IC = +0.0006 (literally zero) vs IC_conf +0.0218; bot-decile z=+2.95 vs top z=+0.70 (short-tilt confirmed); beta attenuation 21.8→12.0→3.9 (5-6x drop confirmed); 2026-04 sigma_p=0.1075 is max of all months while cov collapses (overconfidence confirmed). (3) Flaw check: the within-month top-20% |pred| threshold has mild descriptor look-ahead, so I stress-tested with a fully causal trailing 30-day q80 threshold (shifted 1 row): drift IC_conf=+0.0251, pnl_conf=+0.83bps — conclusion unchanged, gate result is not a look-ahead artifact. Demeaned pred is consistent with causal EMA init (first row = 0), and eval correctly uses raw y_true_ret_bps. Two minor caveats that do NOT change the verdict: (a) internal wording inconsistency — the finding says '2026-05 CLEAN P = -0.002' while its own table (and my reproduction) gives +0.010; (b) per-month CLEAN values carry subsample-phase sensitivity of ±0.02 (e.g., 2026-03 clean P spans -0.014 to +0.041 across phases; strong-group IC_conf 0.075 vs 0.116), so month-level clean numbers should be read as noisy while the group-level tail-only/short-tilt/beta-attenuation conclusions are robust across all three subsamples and the causal gate.
- held: Mode classification survives all adversarial checks; every headline number reproduces exactly. (1) Market-drift/base-rate confound on the short-side claim is dead: drift base P(y<0)=50.0% (per-month 49.2-50.9%, mean y -0.54..+0.24bps), so bot-decile hit 53.2% has z=+2.57 vs base (= finding's +2.54), day-clustered t=+2.25, day-block-bootstrap P(hit<=50%)=0.003. (2) Gate look-ahead circularity is dead: fully causal gates match or beat the within-month gate (expanding IC +0.0312/pnl +1.12bps; 10d-rolling +0.0329/+0.93bps vs +0.0303/+0.80bps). (3) Vol confound only refines: trailing-vol-only gate reproduces 70% of the gated IC (+0.0213) but NONE of the directional pnl (-0.07bps vs +0.80); within-day |pred| gate keeps IC +0.0297 (not a day-picker); double-sort shows the edge concentrates in high-vol half (IC +0.0414, pnl +1.42bps vs low-vol +0.0137, +0.11bps) - tail survival is a |pred|-x-vol interaction, |pred| adds real direction beyond vol. (4) Rest-80% zero confirmed (+0.0002, Spearman +0.0081); beta attenuation robust with non-overlapping day-block CIs (strong 30.8 [19.1,39.7] vs drift 5.05 [-1.2,10.3]); not-sign-flip and Spearman-lockstep confirmed per month. STRONGEST SURVIVING CAVEAT: the drift tail-survival magnitude is statistically marginal under overlap-aware stats - drift gated daily-IC t=+1.15 (46% neg days), gated daily pnl t=+1.50, pooled gated IC day-block bootstrap 95% CI [-0.0035,+0.0645] with P(IC<=0)=0.039; per-month gated ICs 2026-01..03 (0.049-0.057) are individually non-significant (P(<=0)=0.05/0.09/0.19); dropping the top-3 of 134 drift days cuts gated IC 0.0303->0.0177 and pnl 0.80->0.38bps (concentration consistent with the finding's own weekly-flicker claim). The robustly significant surviving component is specifically the short-side tail hit rate (p=0.003) plus the high-vol-conditional gate pnl. Secondary softening: on demeaned-y the drift long-side tail is z=+1.90, not fully dead - the short-tilt design implication is directionally right in tradeable raw y (z +0.67 vs +2.57) but weaker as pure model-skill asymmetry. Cosmetic: finding quotes 2026-05 CLEAN P as both -0.002 and 0.010 in one sentence; reproduction gives +0.0103 per-day-CLEAN. Design implications should treat 'recoverable 0.03-0.06 gated IC in 2026-01..03' as a wide-CI point estimate, not a bankable floor.

**Key numbers:** MODE = TAIL-ONLY SURVIVAL (short-side-tilted) + severe beta attenuation; NOT sign-flip, NOT intact-ranking, NOT fully uniform. (1) Sign-flip ruled out: per-month CLEAN P all positive in drift except 2026-05 (-0.002≈0): 2026-01..05 CLEAN P = 0.017/0.023/0.010/0.018/0.010 (DENSE 0.015/0.032/0.010/0.012/0.019); daily-IC AC1=-0.033 (no persistent negative regime), 15/21 drift weeks positive. (2) Intact-ranking ruled out: Spearman collapses in lockstep — drift CLEAN S 0.006/0.018/0.015/0.027/0.030 vs strong 0.051/0.059. (3) Tail-only survival: within-month top-20%-|pred| gate (CLEAN): drift IC_conf=+0.0303, rest-80% IC=+0.0002 (literally zero); strong IC_conf=+0.1163 vs rest +0.0218. Per-trade pre-cost: drift conf +0.80bps vs all-trades -0.02bps. (4) Short-side asymmetry: drift bottom-decile hit 53.2% (binomial z=+2.54, n=1608, significant) vs top-decile 50.8% (z=+0.65, dead); strong months bot 57.6% (z=+3.93) / top 54.2% (z=+2.16). (5) Beta attenuation with RISING pred scale: CLEAN beta(y~pred) strong +30.8 → normal +15.8 → drift +5.1; σŷ/σy rises 0.0029→0.0036 (2026-04 σp=0.109, max of all months, beta=1.74) — overconfident, no variance collapse. Mechanism: cov(p,y) CLEAN falls 4-6× (0.13–0.16 strong → 0.017–0.035 drift, 2026-05 negative) while σy stays high (20–26bps in 2026-01..03 ≈ strong 23–27) — genuine covariance loss, not scale artifact. Vol content survives: Spearman(|pred|,|y|) drift +0.120 vs strong +0.166. Significance (CLEAN daily-IC): strong t=+4.97 (25% neg days), normal t=+1.89 (39%), drift t=+1.72 (48% neg days ≈ coin-flip daily). Sub-split: 2026-01..03 confidence-gated IC 0.049–0.057 (recoverable); 2026-04/05 dead even gated (+0.008/-0.008). Drift signal flickers weekly: 9/21 weeks IC≥+0.036 (max +0.099 = strong-month level), 6/21 negative, zero persistence.

**Evidence:** Data: /Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv (111,954 rows, stride 180s). Method: pandas/scipy local. DENSE = all stride-180 rows per month. CLEAN = greedy non-overlap subsample >=600s apart (~3,360 rows/full month), per-UTC-day Pearson (days with >=20 pairs), averaged; t-stat over daily ICs. Beta = OLS slope y_true_ret_bps ~ y_pred_demeaned. Tails = within-month deciles / top-20% |y_pred_demeaned| on CLEAN rows; hit = sign agreement, tail hit = P(y>0|top dec) / P(y<0|bot dec) with binomial z. Cov decomposition per month on CLEAN. Weekly IC = CLEAN Pearson per ISO week (n>=100). Scripts (reproducible): /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/h1_diag.py, h1_diag2.py, h1_diag3.py. Full per-month table computed for 2025_08..2026_05 covering P/S dense+clean, %neg days, σŷ/σy, beta, tail means/ICs, hit rates.

**Design implication:** Per-month P>=0.08 in 2026 is NOT reachable by recalibrating/gating the existing signal: total surviving covariance caps recoverable IC at ~0.03-0.06 confidence-gated for 2026-01..03 and ~0 for 2026-04/05 — new conditioning information is required for the mean-direction call. Concretely: (a) the 80% low-|pred| region is pure noise in drift — any design should confidence-gate (top-quintile |pred|) for trading and for loss weighting, since that is where 100% of surviving signal lives; (b) fix overconfidence structurally — prediction scale GROWS (σp up to 0.109) exactly when information dies (beta 30.8→5.1), so add a causal rolling beta/scale recalibration layer (predicts when the model is stale) rather than more capacity; (c) the surviving edge is asymmetric: short-side tail is significant in drift (z=+2.54), long-side dead (z=+0.65) — a short-tilted or side-conditional head is the highest-yield cheap change; (d) vol-ranking content (|pred|~|y| S=0.12) survives drift — usable as a causal regime/confidence feature; (e) drift alpha flickers at weekly scale with zero persistence (9/21 weeks at strong-month IC levels) — the design target should be a causal week-level regime identifier (e.g., funding/OI/basis state) that predicts WHEN the momentum-flavored signal pays, not a better unconditional predictor; (f) note 2025-08/09 'normal' months are themselves insignificant (t<1) — the stable-0.08 mandate fails in 5 of 10 months for reasons beyond 2026 drift, so the fix must generalize, not just patch 2026.



## H2-descriptors-IC — REFUTED (conf: High on the refutation of a stable/deployable gating signal (split-half collapse is large-n and monotone across months; gating lifts fail both bootstrap and shuffle-null). Medium on whether the 2025-only vol→IC relation was real vs selection (p=0.026 pooled, 12 tests) — irrelevant either way since it is gone in 2026.)

**Key numbers:** All ICs are per-day-CLEAN caliber (Pearson within UTC day on non-overlap >=600s rows, n̄=110/day, 260 days, 2025-08-10→2026-05-31; pooled mean-of-daily IC +0.0366). (1) Daily IC is mostly noise: std 0.1183 vs sampling SE 0.0955 → implied true signal std ≈0.070; daily-IC AR1=+0.035; lag-1 IC predicts next-day IC at rho=+0.043 (p=0.51). (2) Pooled lag-1 Spearman (n=244 calendar-consecutive days): best = prior-day mean|y| +0.143 (p=0.026), realized-vol +0.120 (p=0.060), pidx_std(premium-index 5m vol) +0.111 (p=0.085), trend +0.085; funding mean/std, OI %chg, toptrader LS, taker LS all null (|rho|<=0.055). 12 descriptors tested → best p=0.026 fails Bonferroni (0.004). (3) DECISIVE non-stationarity: split-half Spearman — mean|y|: 2025 (n=108) +0.348 p=0.0004 vs 2026 (n=136) −0.027 p=0.75; realized-vol +0.312→−0.040; pidx_std +0.219→+0.071. Per-month sign decays monotonically: +0.81(08) +0.58(10) +0.26(01) → −0.20(04) −0.39(05). The relation is dead exactly in the 2026 drift regime the mandate targets. (4) Honest causal gating (expanding-quantile threshold, 40-day burn-in): best gate pidx_std>expanding-median keeps 132/204 days, pooled dailyIC 0.0386→0.0453 (+0.0067) but bootstrap 95% CI [−0.0041,+0.0178], P(lift<=0)=0.109, within-month-shuffle null P=0.140 (NOT significant); monthly floor 0.0191→0.0173 (worse). mean|y|/vol gates: pooled +0.004 (shuffle P=0.518), 2026_04 gated −0.0055, 2026_05 keeps 1 day at −0.219 → floor 0.0191→−0.219 (catastrophic). Rank-weighting by mean|y|: pooled 0.0386→0.0448 but 2026_05 0.0203→0.0005. No variant moves any weak month toward 0.08; strong months (2025-10 0.085→0.11-0.12 gated) get stronger, i.e. gating only concentrates existing regime dependence.

**Evidence:** Data: exports/final_l01/y600_backtest_dataset.csv (111,954 rows, stride 180s confirmed via timestamp diffs); data/funding/btcusdt_funding.csv, btcusdt_premium_index_5m.csv, btcusdt_metrics_5m.csv. Method: greedy per-UTC-day non-overlap subsample (>=600s apart, 28,169 rows); per-day IC = corr(y_pred_raw, y_true_ret_bps), days with n>=30 kept (260); same-day descriptors (rv=std, trend=|Σy|/Σ|y|, AR1, mean|y| on non-overlap y_true) + external daily aggregates (funding mean/std; pidx_close mean/std; OI last-of-day %chg; toptrader/taker LS means) all shifted lag-1 and joined only where prior calendar day exists (244 days). Tests: pooled + per-month + month-demeaned Spearman; between-month (n=10) decomposition; tercile splits with t-test; causal gating sim with expanding-quantile thresholds (burn-in 40d) reporting per-month gated IC, kept-day counts, monthly floor; 10k day-level bootstrap + 10k within-month label-shuffle null on the pooled lift. Scripts: scratchpad h2_daily.py / h2_part2.py / h2_part3.py; daily table at scratchpad/h2_daily_table.csv (absolute: /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/).

**Design implication:** Do not build day-level IC gating/weighting into the improvement design — it cannot deliver the stable per-month >=0.08 mandate and actively worsens the monthly floor. Three structural reasons: (a) the only descriptors with any signal (prior-day activity/vol family: mean|y|, realized vol, premium-index vol) had their IC-predictive relation collapse from rho ~+0.31..0.35 in 2025 to ~0/negative in 2026 — the gate goes blind precisely in the drift regime it is needed for, so any gate fit on history will misfire forward; (b) daily IC is ~80% sampling noise (n≈110 clean obs/day) with zero persistence (AR1 0.035), so even a perfectly stationary rho-0.14 descriptor explains ~2% of observed daily-IC variance — the ceiling on any day-conditioning lever is a few thousandths of pooled IC, never a floor-raiser; (c) gating is multiplicative on existing regime dependence: it upgrades already-good months (2025-10 → 0.11-0.12) and defunds weak months (2026-04/05 → near-zero days kept or negative IC). Implication for the >=0.08-stable design: the weak-month deficit (2026 IC 0.012-0.031) must be closed at the per-timestamp signal level (regime-robust features/targets or orthogonal data, e.g. liquidations), not by turning days on/off; the funding/OI/positioning daily aggregates tested here carry zero IC-conditioning information (|rho|<=0.055) and should not be revisited as day-level gates. If a mild pooled-IC boost is ever wanted in production, pidx_std-weighted sizing is the least-bad variant (+0.0067 pooled, insignificant, floor-neutral-to-slightly-worse) — but it must be framed as a sizing overlay, not a regime fix.



## H3-momentum-state — REFUTED (conf: high)

**Key numbers:** All numbers on non-overlap subsample (>=600s apart, 720s spacing, 28,169 of 111,954 rows) of exports/final_l01/y600_backtest_dataset.csv; ICpool = pooled Pearson(y_pred_raw, y_true_ret_bps) on non-overlap rows; ICclean = per-day-CLEAN (within-UTC-day Pearson on non-overlap rows, averaged over days); month = dataset fold label. (a) 10 monthly pairs (VR3 of y_true [Var(30min-agg)/(3*Var(600s))], AR1, ICpool, ICclean): 2025_08 (1.141, +0.048, 0.026, 0.037); 2025_09 (0.866, -0.053, 0.037, 0.032); 2025_10 (0.642, -0.137, 0.079, 0.086); 2025_11 (0.934, -0.016, 0.080, 0.066); 2025_12 (0.974, +0.017, 0.029, 0.046); 2026_01 (0.986, -0.061, 0.042, 0.030); 2026_02 (1.016, -0.020, 0.017, 0.019); 2026_03 (0.923, -0.040, 0.035, 0.019); 2026_04 (1.024, -0.008, 0.020, 0.031); 2026_05 (0.918, -0.065, 0.002, 0.016). Rank-corr(state, monthly IC) n=10: VR3 vs ICpool = -0.406 (p=0.24), VR3 vs ICclean = -0.115 (p=0.75), AR1 vs ICpool = -0.224 (p=0.53); Pearson VR3 vs ICpool = -0.582 (p=0.077) — direction NEGATIVE: the best month (2025_10, IC 0.079/0.086) is the MOST mean-reverting (VR3 0.642, AR1 -0.137), opposite of H3. (b) Causal daily gate (prior UTC day VR3>=1 -> TREND; 254 days with valid prior state): TREND ICpool +0.0509 / ICclean +0.0463 (106 days, 41.7%); CHOP ICpool +0.0226 / ICclean +0.0327 (148 days, 58.3%); TREND-CHOP per-day-IC diff +0.0136, t=0.88, p=0.382, day-bootstrap 95% CI [-0.0165, +0.0430] — NOT significant. Excluding strong folds 2025_10/11: TREND ICclean 0.0318 vs CHOP 0.0259, t=0.34, p=0.738 — the apparent gate edge is mostly the strong-month regime, not a within-month causal state. Stricter gates are NON-monotonic: VR3>=1.15 ICclean 0.0448 (24% of days); VR3>=1.3 ICclean 0.0305 (11%); deep-chop VR3<0.75 ICclean 0.0461 (21%) — deep chop is as good as trend. No causal daily state reaches 0.06. (c) Choppy-class days: signal ALIVE and positive, not dead, not flipped — CHOP original ICclean +0.0327, per-day IC mean +0.0327, t=+3.64, p=0.0004, only 41% of chop days have IC<0; flipped (-y_pred) is negative in ALL 10 fold-months (ICclean -0.011 to -0.059, pooled -0.0327). (d) Intraday prior-2h-state -> next-2h IC (2,780 windows) and prior-4h -> next-4h (1,373): all four states (efficiency ratio, AR1, VR2, vol) tercile HI-LO per-window t-tests p=0.31-0.81; quintile ICs non-monotonic noise (e.g., 2h prior_VR2: Q1 -0.014, Q2 +0.076, Q3 +0.013, Q4 +0.077, Q5 +0.039); no bucket forms a stable >=0.06 state. Highest causal-state IC found anywhere: prior-day VR3>=1 ICpool 0.0509 at 42% coverage — still below 0.06 and statistically indistinguishable from unconditional (pooled all-days ICclean baseline 0.0387).

**Evidence:** Data: /Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv (111,954 stride-180s rows, 2025-08-10 to 2026-05-31). Method: greedy non-overlap subsample keeping rows >=600s apart (spacing mode 720s, 28,169 rows); per-month AR1 computed only over contiguous 720s pairs; VR(q) = Var(sum of q consecutive non-overlap 600s returns)/(q*Var(single)) with q=3 (~30min; note the prompt's "5x" divisor is an arithmetic slip since 30min = 3x600s — VR5 (~50min) also computed, same conclusions: rank-corr VR5 vs ICpool -0.188 p=0.60); Spearman/Pearson over the 10 (state, IC) pairs via scipy.stats. Daily gate: per-UTC-day VR3/AR1 from that day's non-overlap y_true, day classified by PRIOR calendar day's value (strictly causal; days without a valid prior day dropped, 254/266 remain); class ICs as pooled Pearson + per-day-CLEAN; significance via Welch t on per-day ICs + 10k day-level bootstrap. Flip test: Pearson(-y_pred_raw, y_true) on choppy-class rows, per fold-month and pooled; demeaned-caliber (y_pred_demeaned vs y_true_demeaned_bps) cross-check gave same ordering (TREND ICclean_dm 0.0505 vs deep-chop 0.0530). Intraday: 7200s/14400s windows keyed on timestamp_ms; prior-window state (Kaufman ER=|sum r|/sum|r|, AR1, VR2, vol of ~10/20 non-overlap returns) required to be the immediately preceding contiguous window; next-window rows bucketed by tercile/quintile of the causal state (thresholds full-sample — mild threshold look-ahead, biases TOWARD finding an effect, none found); HI-LO tested via per-window IC Welch t. Scripts: scratchpad h3_abc.py, h3_d.py, h3_rob.py (scratchpad dir /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad). Caveat: dataset `month` is fold label, not strict calendar month (e.g., fold 2025_10's TREND days include 2025-11-03/05/06); day-level stats use true UTC days so conclusions unaffected.

**Design implication:** Do NOT build a trend/chop gate and absolutely do NOT sign-flip in choppy states: the signal is positive and significant in BOTH states (chop ICclean +0.033, t=3.6; flip is uniformly value-destroying across all 10 fold-months), and no causal price-path state (daily or 2h/4h; VR, AR1, efficiency ratio, vol) creates a >=0.06 region — best causal gate hits only 0.051 pooled / 0.046 clean at 42% coverage, indistinguishable from unconditional. Deeper: the monthly IC variation is NOT explained by y_true trendiness at 10-30min scale — the association is directionally NEGATIVE (best month 2025_10 is the most mean-reverting, VR3 0.64 / AR1 -0.14), so the standing "momentum-flavored signal pays in trending regimes" narrative (memory: single_asset_regime_dependence) is wrong at this state definition and should be retired as a design driver. The 2026 drift-month decay (IC 0.002-0.042) is a month-scale concept-drift/feature problem, not a gateable price-path regime; the >=0.08-stable mandate must be pursued via orthogonal conditioning data (e.g., funding/premium/OI state from data/funding/*.csv) or model/feature adaptation, not via trend-state gating or flipping of the existing prediction.



## H4-staleness — REFUTED (conf: high)

**Key numbers:** All numbers per-day-CLEAN caliber (>=600s non-overlap within UTC day, per-day Pearson averaged) on y_pred_raw vs y_true_ret_bps; anchor check: pooled mean 0.0389 vs briefed 0.0387 (match). (1) Pooled within-month decay: month-FE regression of per-day IC on day-of-month, slope -0.00024/day (se 0.00086, t=-0.28, p=0.78, n=266 days) = -0.007 IC over 30d — NULL. (2) Drift months (2026_01..05): Pearson slope -0.00175/day (p=0.102, NOT significant, -0.053/30d), but (a) SPEARMAN caliber slope -0.00009/day p=0.92 — dead null, P/S divergence flags the Pearson slope as tail-driven artifact; (b) leave-one-out: dropping 2026_04 (known mid-month choppy-to-trending regime flip) cuts slope 41% to -0.00104 p=0.41; (c) half-month H2-H1 drift mean -0.0146 t=-1.04 n=5, dominated by 2026_04's -0.0609. (3) Non-drift 2025 months slope is POSITIVE +0.00123/day (p=0.36; Spearman +0.00109 p=0.39) — a staleness mechanism would decay everywhere; opposite sign in 2025 indicates day-of-month IC is regime composition, not model age. (4) Month-boundary vintage-refresh test (staleness ~30d -> ~1d overnight): mean first-3-days(M+1) minus last-3-days(M) jump +0.0071 (t=+0.34, n=9 adjacent boundaries; pooled-corr version +0.0085); into drift months specifically -0.0051 (n=5) — NO refresh benefit exactly where H4 predicts the largest; all individual jumps (+0.12 to -0.09) within within-month 3-day-block null (std 0.102, n=75). (5) Upper bound: even taking the non-significant drift Pearson slope at face value, online adaptation (mean staleness 15.5d->1d) recovers +0.025 IC vs drift-month mean IC 0.0234 and gap-to-0.08 of 0.057 — under half the gap, and Spearman-null + boundary-null imply true recoverable ~0.

**Evidence:** Data: /Users/haosiyu/Desktop/quant_research/exports/final_l01/y600_backtest_dataset.csv (111,954 stride-180 rows, 2025_08..2026_05). Method: greedy >=600s-apart subsample within each UTC day (28,169 clean rows, 266 days); per-day Pearson and Spearman IC; (a) week-of-month pivot per month; (b) month-fixed-effect OLS of per-day IC on day-of-month, pooled/drift/non-drift, plus per-month slopes and leave-one-month-out; (c) boundary jump last-3 vs first-3 days per adjacent month pair, with within-month 3-day-block deltas as noise null; sanity replicated on demeaned caliber (drift slope -0.00224 p=0.050 but same 2026_04 dependence and Spearman null). Scripts: /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/h4_staleness.py and h4_robust.py (python3, pandas 3.0.2 + scipy). Prior-memory check (choppy_y600_nonstationarity_mechanism.md): my numbers SUPPORT it — it claims recency HURTS (Ridge recent-30/60/120d all worse than all-history; 2026-02 online60 -0.020 vs static +0.032) and that drift is month-scale near-orthogonal concept JUMPS (consecutive-month mapping cosine +0.030, random-walk, unpredictable), not smooth decay; I find no smooth within-month decay, no vintage-refresh jump, and boundary jumps indistinguishable from within-month regime noise — fully consistent, zero contradiction.

**Design implication:** Online/faster-than-monthly retraining is NOT a promising lever for the >=0.08 stable mandate: the model does not measurably age within a month (staleness 1-30d on a 450d window contributes ~0 IC; cleanest causal test — the monthly vintage refresh — produces no IC jump, and none in drift months). Monthly rolling retrain is already at the adaptation-cadence ceiling; drift-month underperformance (2026 mean per-day-CLEAN 0.0234) is a month-scale P(y|X) concept JUMP that is in place from day 1 of the month, consistent with the random-walk mapping-drift memory. Budget should go to (i) orthogonal, more-stationary conditioning inputs (funding/premium/OI files already in data/funding/) and (ii) regime-conditional deployment/sizing, not adaptation machinery (DDG-DA, online SGD, weekly retrain). Caveat: this bounds staleness only at the 1-30-day scale over a 450d window; sub-daily adaptation untested here, but prior recency evidence (recent-window Ridge strictly worse) argues the same direction. Watch-item: 2026_04-style mid-month regime flips (H1 0.0636 -> H2 0.0027) are the real intra-month failure mode — a causal regime detector that de-risks after a flip is the actionable version of 'adaptation', not model refitting.



## H5-funding-conditioning — REFUTED (conf: high — 260 days / 28,169 non-overlap rows, 5 conditioners all null at day scale with consistent t<1.2; the one positive (funding×short-side) replicates under row-level Welch (p=0.0018), day-clustering (p=0.016), and day-drift removal (p=0.018); upper-bound calc is closed-form and in-sample-generous, so the true achievable lift is even smaller.)

**Key numbers:** Baseline per-day-CLEAN mean daily Pearson (raw caliber, 260 days) = 0.0366 (official 0.0387; demeaned caliber 0.0464). Tercile mean daily IC [T1/T2/T3, per-day-CLEAN]: (a) funding level 0.0380/0.0370/0.0348, T3−T1=−0.003, p=0.86; (b) |funding| 0.0303/0.0531/0.0265, non-monotone, p=0.84; (c) prior-day OI %chg 0.0510/0.0272/0.0315, p=0.29; (d) top-trader L/S 0.0330/0.0387/0.0381, p=0.76; (e) premium-index vol 0.0257/0.0374/0.0468, monotone, T3−T1=+0.021, p=0.27 (only survivor of month-FE check: month-demeaned Spearman ρ=+0.121, p=0.052; all others |ρ|<=0.08, p>0.22). Decile×funding (non-overlap rows, per-day y_pred_demeaned deciles, bps/600s): state drift +0.02/−0.05/−0.50 by funding tercile; SHORT bot-decile mean y_true: F1=+1.25 (shorting LOSES), F2=−1.83, F3=−2.33 (t=2.82); interaction F3−F1=−3.59 bps, Welch t=−3.13 p=0.0018, day-clustered t=−2.43 p=0.016, day-drift-removed diff=−2.99 t=−2.38 p=0.018 → sign FLIP, stronger than the known "3x"; LONG top-decile +0.53/+1.04/+1.05, interaction n.s. (p=0.64 row, p=0.58 clustered) — funding conditions ONLY the short side; extreme funding top decile: short bot-dec mean y=−2.60 bps (t=1.94). HONEST UPPER BOUND (perfect tercile day-reweighting, w_s=μ_s → sqrt(Σf_sμ_s²), per-day-CLEAN): funding 0.0366 (+0.0000), |funding| 0.0384 (+0.0018), OI chg 0.0380 (+0.0014), ttls 0.0367 (+0.0001), pidx-vol 0.0376 (+0.0010); joint pidxvol×OI 9-cell IN-SAMPLE 0.0400 (+0.0034, overfit-generous). Day-level oracle (weight by realized IC_d, ceiling of ANY day-scale conditioner) = 0.1246 — day IC variance is huge (std 0.119) but these variables explain ~1% of it. Intra-day: 1h blocks (n=5627, within-block IC overlap-inflated, mean ~0.11 DENSE-within-hour) all conditioner |ρ|<=0.021 p>0.11; 4h blocks (n=1398, mean 0.060) best = |OI chg| day-demeaned ρ=+0.068 p=0.011 (1 of ~20 tests, fails Bonferroni), pidx level ρ=−0.048 p=0.072 → conditioning info, such as it is, is day-scale (premium-vol) not intra-day; 5m OI/premium movement does NOT predict hour-scale IC.

**Evidence:** Data: exports/final_l01/y600_backtest_dataset.csv (111,954 stride-180 rows, 2025-08-10→2026-05-31) + data/funding/btcusdt_funding.csv (8h prints), btcusdt_metrics_5m.csv (OI, top-trader L/S), btcusdt_premium_index_5m.csv. Method: greedy >=600s non-overlap subsample (28,169 rows, 266 days); per-day-CLEAN IC = within-UTC-day Pearson(y_pred_raw, y_true_ret_bps) on non-overlap rows, days with >=30 rows (260 days), averaged. Conditioners strictly PRIOR: last 8h funding print known at day start (+60s tol for the 00:00:00.00x print; first row is 00:10); prior-day OI close-to-close %chg and prior-day mean top-trader L/S from 5m metrics shifted 1 day; prior-day std of 5m pidx_close. Terciles rank-based over 260 eval days; Welch t on T3-vs-T1 daily ICs; month-demeaned Spearman for regime confound. Decile test: per-day deciles of y_pred_demeaned on non-overlap rows × row-level prior funding print terciles; interaction via Welch on row means, re-tested day-clustered (per date×tercile means) and day-demeaned. Upper bound: closed form — scale day preds by state weight w_s, pooled per-day-CLEAN IC = Σ_s f_s w_s μ_s / sqrt(Σ_s f_s w_s²), maximized at w_s=μ_s giving sqrt(Σ_s f_s μ_s²). Intra-day: 1h/4h block IC (dense rows, overlap-inflated within block — flagged) vs prior-window 5m OI %chg, pidx move/vol/level, Spearman raw + day-demeaned. Scripts: scratchpad/h5_main.py, h5_decile_bound.py, h5_intraday.py (session scratchpad); reproduce with python3, pandas 3.0.2. Note my non-overlap baseline is 0.0366 vs the officially reported 0.0387 (slightly different non-overlap row selection; all deltas computed within my caliber).

**Design implication:** Do NOT build funding/OI/positioning conditioning (FiLM/gating/regime-embedding) into the model expecting IC lift toward the 0.08 mandate — the perfect-conditioning ceiling is +0.002-0.003 pooled on a 0.0366 base. Two narrow, justified uses only: (1) execution-side SHORT GATE: take bottom-decile shorts only when prior 8h funding is in the upper tercile (>0.0044bp/8h) — worth ~3 bps/trade on the short side, sign-flips otherwise; suppress shorts at low/negative funding; (2) optionally a small position-size scalar from prior-day premium-index vol (only monotone conditioner that nominally survives month FE, worth <=+0.001 IC). The day-IC oracle (0.1246 vs 0.0366) proves enormous exploitable regime variance EXISTS, but funding/OI/positioning explain ~1% of it — the regime-indicator search should move to other variables (e.g., realized microstructure/trend-state), not derivatives positioning.



## H6-regime-matched-training — REFUTED (conf: moderate-high: three independent measurements (window similar-fraction, 5-NN in-window counts, nearest-in-window distance) all contradict the required pattern, with explicit counter-examples; limited by n=10 months and the monthly granularity of the descriptor space.)

**Key numbers:** Similar-fraction of 450d window (top-quintile z-distance, day-weighted; test-month descriptors are oracle, favorable to H6): strong(2025-10/11)=0.330 > drift(2026-01..05)=0.243 > normal(2025-08/09/12)=0.222 — ordering is OPPOSITE to H6 for drift-vs-strong, and drift months are BETTER-represented than normal months despite per-day-CLEAN Pearson 0.0231 (drift) vs 0.0384 (normal) vs 0.0758 (strong). Per-month table (similar_frac / clean_P per-day-CLEAN): 2025-08 0.138/0.0372, 2025-09 0.271/0.0316, 2025-10 0.324/0.0856, 2025-11 0.336/0.0660, 2025-12 0.258/0.0464, 2026-01 0.327/0.0303, 2026-02 0.138/0.0194, 2026-03 0.204/0.0191, 2026-04 0.273/0.0310, 2026-05 0.273/0.0155. Cross-month corr(similar_frac, clean_P) n=10: Spearman rho=+0.311 p=0.382 (MAD-robust rho=+0.494 p=0.147); continuous mean-window-z-distance vs clean_P rho=-0.079 p=0.829. 5-NN in-window counts: drift mean 2.4/5 ≈ normal 2.3/5 (strong 3.5/5) — every 2026 month already has 2-3 of its 5 nearest analogues inside its window. Nearest in-window z-distance: drift 1.687 ≈ strong 1.668. Decisive counter-examples: 2026-01 similar_frac 0.327 (equal to strong) yet P=0.0303; 2025-08 lowest frac 0.138 yet healthy P=0.0372; best month 2025-10 has its true nearest analogue (2024-10, d=1.010) OUTSIDE its window (in-window nearest d=1.813, largest gap 0.803) yet P=0.0856; 2025-12 has the closest in-window analogue of all (d=0.853) yet only P=0.0464. Premise partially true but mechanistically inert: 2026 months' global nearest analogues are often out-of-window 2023-24 chop months (2026-05→2023-09 d=0.918; 2026-03→2024-09 d=1.328), but in-window analogue availability does not co-move with P. 2026-02 is a genuine outlier with NO close analogue anywhere (rv 0.822 = max of 40 months; mean z-dist 4.315) — no sampling scheme can supply what history lacks. Test-month OWN descriptors vs clean_P: all n.s. except fund_mean rho=+0.515 p=0.128 (confounded with the 2026 era itself). Caliber check: monthly-avg of my per-day-CLEAN P = 0.0382 vs stated pooled 0.0387 — caliber consistent.

**Evidence:** Data: (1) Binance public klines api.binance.com/api/v3/klines symbol=BTCUSDT interval=1d, paginated startTime 1672531200000→endTime 1780271999999, 1247 daily rows 2023-01-01..2026-05-31, saved to scratchpad/btc_daily_2023_2026.csv. (2) /Users/haosiyu/Desktop/quant_research/data/funding/btcusdt_funding.csv (8h funding), btcusdt_premium_index_5m.csv (from 2023-02), btcusdt_metrics_5m.csv (OI, from 2023-02). (3) exports/final_l01/y600_backtest_dataset.csv (111,954 rows, months 2025-08..2026-05). Method: monthly descriptors 2023-01..2026-05 (41 months; 2023-01 dropped for missing pidx/OI → 40 complete): rv=std(daily log-ret)*sqrt(365), trend=Kaufman efficiency |Σr|/Σ|r|, AR1(daily r), fund_mean, fund_std, pidx_vol=std(5m pidx_close), oi_chg=(OI_end−OI_start)/OI_start; z-scored across 40 months (robustness rerun with median/MAD); euclidean distance in 7-dim z-space; candidates = all months strictly before test month (rolling retrain semantics); 450d window = [month_start−450d, month_start−1d] (all windows start ≥2024-05, no missing-descriptor days); top-quintile = k=round(0.2·n_cands) closest candidates; similar_frac = day-weighted share of window days in top-quintile months. Per-month clean_P = within-UTC-day Pearson (y_pred_raw vs y_true_ret_bps) on non-overlapping ≥600s-apart rows (greedy subsample of stride-180 rows), days≥20 samples, averaged across days per month. Correlations via scipy pearsonr/spearmanr. All scripts in /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f/scratchpad/ (monthly_regime_descriptors.csv, h6_similar_fraction.csv, h6_final_table.csv).

**Design implication:** Do not build regime-matched training-data selection/weighting: the 450d windows of drift months already contain 2-3 of their 5 nearest regime analogues, drift months are no worse-represented than normal months (0.243 vs 0.222 similar-fraction), and window regime-composition does not predict per-month Pearson even with oracle knowledge of the test regime (continuous measure rho≈0). The binding constraint on 2026 performance is signal availability in the test month itself, not training-data coverage — consistent with the previously established choppy-regime ceiling (~0.03-0.044 regardless of training set). If regime conditioning is pursued, spend the effort at inference/feature level (causal regime indicators, e.g., funding level — the only descriptor with any positive lead, rho=+0.515 p=0.13 but era-confounded) rather than data reweighting. Special case: 2026-02-type outlier regimes (max-history rv, no analogue at any lag) are irreducible by any sampling scheme and argue for uncertainty-aware position sizing instead. Caveats: n=10 test months, monthly descriptors from ~30 daily obs are noisy (AR1 se≈0.18), and the 7-dim descriptor space is H6's own specification — a finer (e.g., weekly or intraday-microstructure) similarity space was not tested and would be the only remaining rescue for this hypothesis family.



---

# COMPLETENESS CRITIC (gaps)

MISSING/UNVERIFIED ITEMS, RANKED (Phase-1 completeness critique):

1. **Positioning family tested only as day-scale IC-conditioner, never as model INPUT.** H5 "REFUTED" covers conditioning of existing preds; data-assets shows funding/premium-1m/OI/toptrader-LS/taker-LS on disk, NOT in X/regime_prior. Prior tests were linear-additive Ridge (+0.0012) and FiLM/router only; `multi_asset/data/add_funding_channels.py` + `npz_v2arch_fundch` exist but never ran in production configs. "Dead as conditioner" ≠ "dead as nonlinear feature" — especially given H5's ONE surviving significant structure (short-decile×funding flip, day-clustered t=−2.43 p=0.016) got zero follow-up: no causal gated variant, no 2026-04/05 sub-split, single computation.

2. **All regime-conditioning FAILs predate fixing the two structural bugs.** code-architecture FLAGS 1-2: regime-FiLM extractor eats post-RevIN x_feat (absolute vol destroyed) and batch-z-scores descriptors (uniform regime shift invisible). Every "regime FiLM/MoE/gated FAIL" verdict used a mechanism blind to regime level. No post-fix retest exists.

3. **H6 refuted a correlation, not the intervention.** 2026 months' nearest analogues are 2023-24 chop months — outside every 450d window AND outside npz_v2arch itself (starts 2024-01). Training WITH those analogues (back-built cache, ~58GB/306d quantified in caliber-target; longer window; analogue-weighted sampling) was never run. wf550 (550d) configs exist; results absent from Phase-1.

4. **Checkpoint-selection axis unexamined in drift.** Verified now: local `experiments_local/wfEMA/*/fold_0/metrics.json` has NO fallback/σ-gate flag (13 keys), so whether drift folds used the low-σ fallback ckpt is UNVERIFIED. New datum: best_epoch = 16/18/15/18/16 for 2026-01..05 vs 4/7/10/11 for 2025-08..12 — drift folds select near patience-exhaustion; val-selection health (composite 0.5P+0.5S on a 45d val that is itself drift) never audited. β∈[0.19,1.82] instability likewise unexplained.

5. **mh180 (y_180 aux): +0.0139 CLEAN single-fold, multi-fold NEVER run** — flagged in the map, contradicts "禁止单 fold 声称有效", still open. Similarly choppy-specialized training, the only weak-regime WIN (0.0167→0.0311 OOS), is absent from Phase-1; its "died on val→test..." note is truncated/unresolved.

6. **Statistical power: n=10 months, 2 partial.** 2025-08 (9.2d) / 2025-09 (7.5d) are partial tests weighted equally; every cross-month "refutation" (H3 p=0.24-0.77, H6 p=0.38) is underpowered at n=10. Back-extension to 2024-06 (13 more months, 26-52 GPU-h) is quantified but undone — H2's split-half sign-flip especially needs a third era.

7. **2026-04/05 "dead even gated" has no root cause.** H1's sub-split is a single computation; 2026-05 negative cov, 2026-02 no-analogue outlier — no data-quality check (cache ends 2026-05-31), no feature-drift decomposition (which of the 88 channels' train-z distributions shifted).

8. **Descriptor set for day-IC prediction is narrow vs oracle headroom 0.1246**: 12 price/funding descriptors explain ~1% of day-IC variance; untested: liquidations (never pulled from Tardis), cross-asset dispersion/alt-BTC state (13 alts on disk, unused), calendar/session, order-flow persistence. Verified mask leak is real but tiny: 82 y_true==0 rows in exports/final_l01/y600_backtest_dataset.csv (16 in 2025-12, 13 in 2026-01) — fix, but not a driver.

9. **Scale mismatch untested:** conditioning evidence is day-scale (pidx_std) yet model context is 10min + NEG-tested 4h X_long; day-scale state as raw input feature (beyond 6h regime_prior) never tried. Target-side (vol-normalized y, drift-specific horizon) also untouched.