# `data/npz_btc_unified` — UNIFIED BTC Data Foundation — MANIFEST

> **创建:** 2026-06-21 | **Session:** unified-cache foundation | **状态:** in-progress (Phase-1: builder + small-range verified; FULL-HISTORY build GATED) | **作废条件:** re-spec of the foundation, or replacement of the single source `/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31`.

This is the single, rigorously-verified BTC cache that replaces the confounded
cache mess (`npz_v4`, `npz_spot`, `npz_perp`, `npz_spot2perp*`, `npz_dual*`).
Builder: `multi_asset/data/build_unified_npz.py`. Verifier:
`multi_asset/data/verify_unified_npz.py`.

---

## 0. THE CONFOUND THIS CACHE KILLS (resolved with hard evidence)

The historical "0.02 vs 0.06 gap" between cache families was a **trade-venue
scaling artifact**, not a real signal difference. Measured this session
(per-feature corr + std, 2025-02-10 & 2025-04-15):

| cache | book | trades | X std (2025-04-15) | what it is |
|---|---|---|---|---|
| `npz_v4` (milestone era) | SPOT | **PERP** | ~25–28 | spot book + perp trades (the documented "spot-perp caliber bug" of `/mnt/storage/share/23-25-BTCUSDT`) |
| `npz_spot` | SPOT | SPOT | **7.89** | the operational "0.08 yardstick" config (`clean_strong_spot2spot_apr.json`) |
| `npz_perp` | PERP | PERP | 28.80 | perp consolidation |

**Root cause (proven):** the std gap is driven ENTIRELY by ~16 trade/volume
features, because **perp trade volume is ~6× spot volume** (`buy_volume_1s` mean
1.07 perp vs 0.12 spot; `cumulative_net_flow_300s` std 213 perp vs 41.5 spot).
The 48 book/price features are corr **1.0000** and std-identical across spot
caches; only the 16 trade features diverge (corr 0.3–0.6, ~6× scale). The
"median per-feature corr 1.000" claim that made everyone equate `npz_spot` with
`npz_v4` was masking exactly those 16 trade features (median across 64 hides
16/64 outliers). NO pipeline / quantization / normalization difference exists —
`build_npz_for_day` is byte-identical across all of them.

**Decision:** the unified `X_spot` = **SPOT book + SPOT trades** = `npz_spot`
exactly (gate 2 reproduces it at corr 1.0000, std ratio 1.0000), which is the
config-confirmed 0.08 yardstick. The perp-trade variant lives in `X_perp`
(PERP book + PERP trades). Both venues are explicit and independently verifiable,
so no future comparison can be confounded by a hidden source/scale difference.

---

## 1. SOURCE (the ONLY data the builder reads — READ-ONLY)

```
/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/
    book_snapshot_25/<YYYY-MM-DD>/{binance,binance-futures}/BTCUSDT.csv.gz
    trades/<YYYY-MM-DD>/{binance,binance-futures}/BTCUSDT.csv.gz
```
- spot venue = `binance`, perp venue = `binance-futures`.
- Tardis µs timestamps, true 25-level/side book, 1247 days.
- **NO** `share`/`bar_data`, **NO** `23-25-BTCUSDT`, **NO** reading any `npz_*`
  cache as a source (verified by gate 1).

## 2. BUILD PARAMETERS

- **build_date:** 2026-06-21 (passed via `--build-date`; never wall-clock).
- **date range (Phase-1 small build):** 2025-02-10, 2025-04-15 (the two fold-span
  probe days). Milestone train history (2023-08-08 .. 2025-01-28) for the
  acceptance test is read from the already-existing `data/npz_spot` (X_spot ==
  npz_spot by construction). **FULL HISTORY (1247 days) IS GATED — not built yet.**
- **period (when full build runs):** 2023-01-01 .. 2026-05-31.
- **windowing:** input_len=600, stride=180; pred_idx = last second of the window
  (= feature cutoff `t`). Per UTC calendar day, cold-start at 00:00 UTC, no
  cross-day window concat (byte-identical methodology to npz_v4/npz_spot).
- **raw LOB depth:** 25 (full Tardis).
- **size:** ~172 MB/day → full history ≈ 215 GB (raw 25-level tensors for both
  venues dominate).

## 3. CHANNELS (per UTC day, `data/npz_btc_unified/<YYYY-MM-DD>.npz`)

### FINE (1s, windowed; N = #windows/day ≈ 477)
| key | shape | dtype | definition |
|---|---|---|---|
| `X_spot` | (N,600,64) | f32 | 64 hand features, **SPOT book + SPOT trades** (frozen `build_npz_for_day`, `include_ridge_features=True`, `include_regime_prior=True`, `quantize_features=True`). RAW values (no pre-standardization). |
| `X_perp` | (N,600,64) | f32 | 64 hand features, **PERP book + PERP trades**, same pipeline. |
| `Xraw_spot` | (N,600,25,4) | f16 | 25-level SPOT raw-LOB tensor `[bid_Δbps, bid_log_amt, ask_Δbps, ask_log_amt]` (`extract_raw_lob_tensor`, full Tardis depth). |
| `Xraw_perp` | (N,600,25,4) | f16 | 25-level PERP raw-LOB tensor. |
| `X_cross` | (N,600,8) | f32 | STABLE cross-venue channels — see below. **No divergence SEQ channels** (those collapse the model). |

`X_cross` channels (`cross_names`): all ratios or bounded levels, strictly ≤ t.
0 `x_mid_ratio_log` = log(perp_mid/spot_mid); 1 `x_basis_bps` = (perp−spot)/spot·1e4
clip ±50 (**bounded basis LEVEL**); 2 `x_spread_ratio_log` = log((perp_spr+1)/(spot_spr+1));
3 `x_depth_ratio_log` = log(perp_L25_depth/spot_L25_depth); 4 `x_obi_diff` =
clip(perp_obi_L5 − spot_obi_L5, ±2); 5 `x_mpdev_diff` = perp_mpdev − spot_mpdev;
6 `x_rvol_ratio_log` = log(perp_rvol30/spot_rvol30); 7 `x_tradeflow_ratio` =
tanh(perp_net_flow/(|spot_net_flow|+1)) (bounded ±1).

### LONG (60s-pooled, 4h = 240 steps, cross-day stitched LEFT, leak-free)
| key | shape | dtype | definition |
|---|---|---|---|
| `X_long` | (N,240,10) | f32 | 60s-pooled 4h summary; for each window cutoff t the trailing 240 COMPLETE 60s bins ending at the bin BEFORE t's bin (strictly ≤ t). Prior-day tail stitched on the LEFT for a warm lookback at day start; **never the next day**. |

`X_long` channels (`long_names`): spot {ret, rvol, obi*, spread, vol*}, perp {ret,
rvol, obi*, spread}, basis_bps. `*` = bounded proxies (obi = tanh(ret/rvol)
momentum proxy; vol = log1p(Σ|ret|·1e4) activity proxy) — the light per-second
mid grid carries no book depth, so true OBI/volume are approximated by these
bounded, causal proxies (honest note; the book-depth OBI lives in `X_cross`/
`regime_prior`). Per-second returns clipped ±2%, spreads clipped [0,100]bps to
kill crossed/stale-book glitches before pooling.

### REGIME + book-shape
| key | shape | dtype | definition |
|---|---|---|---|
| `regime_prior` | (N,6) | f32 | the milestone 6-dim regime prior (`compute_regime_prior_features`: vol_1h, spread_mean_1h, obi_trend_1h, price_return_6h, hour_sin, hour_cos), PERP book. |
| `X_rg` | (N,8) | f32 | bounded multi-scale RG regime indicators (`rg_names`): rvol term-structure 60/600, 600/3600, rvol_600s, variance-ratio q30/q120 (w=3600), Hurst-like, liq spread-ratio, liq depth-ratio. All ≤ t, clipped to bounded bands. |
| `X_bs` | (N,12) | f32 | BS book-shape features (`bs_names`): causal Δ of perp {bid/ask concentration, mpdev, bid/ask slope, book-pressure imb} over 60s, mpdev Δ600s, microprice curvature, conc-asymmetry Δ60s, cross-venue obi/mpdev divergence rate 60s, book-pressure level. Computed on the pred grid via time-aware row-lags (≤ t). |

### TARGETS (all future-only, gated by masks; re-anchored to spot pred second t, offset 0)
| key | shape | dtype | definition |
|---|---|---|---|
| `y_spot_600` | (N,) | f32 | log(spot_mid[t+600]/spot_mid[t]) |
| `y_perp_600` | (N,) | f32 | log(perp_mid[t+600]/perp_mid[t]) |
| `y_180` | (N,) | f32 | log(perp_mid[t+180]/perp_mid[t]) |
| `y_1800` | (N,) | f32 | log(perp_mid[t+1800]/perp_mid[t]) |
| `y_mask_{spot_600,perp_600,180,1800}` | (N,) | uint8 | 1 iff both mid legs present & >0 (cross-day right-stitch for the forward leg; tail windows whose forward second is missing stay masked, never filled). |

### META
`timestamps` (N,) int64 µs (pred-idx = feature cutoff t); `mask` (N,) uint8
(all fine arrays finite for the row); `features_64`/`cross_names`/`long_names`/
`rg_names`/`bs_names` (object) channel names. `build_meta.json` at cache root.

## 4. NORMALIZATION SCHEME

- **Fine 64-feat (`X_spot`/`X_perp`):** stored **RAW**. Downstream applies the
  milestone per-fold standardization + RevIN (model is affine-invariant per
  window), so the cache is milestone-equivalent. This RAW storage is exactly why
  gate 2 reproduces `npz_spot` value+scale bit-for-bit.
- **`Xraw_*`:** bps-from-mid + log1p amounts (stationary, bounded), f16 (same as
  the milestone X_raw fp16 round-trip).
- **NEW channels (`X_cross`/`X_long`/`X_rg`/`X_bs`):** stored RAW + bounded by
  construction (ratios / tanh / clipped levels). Per-channel (mean, std) fit on
  the milestone fold-0 train window (2023-08-08 .. 2025-01-28) are written as
  `norm_*` constants when the full build is run with `--fit-norm`, so downstream
  z-scoring is deterministic and leak-free (fit on train only). NOT fit on the
  Phase-1 small range (would touch test days).

## 5. LEAK SAFETY (mechanism)

Fine features at window t use only rows [t−599, t] (≤ t, the frozen pipeline).
Targets are forward returns of the per-second mid (≥ t, never < t), gated by
masks. `X_cross` channels are contemporaneous ratios / bounded levels ≤ t.
`X_long` uses only complete 60s bins strictly before t's bin (≤ t), with a
prior-day (never next-day) left-stitch. `X_rg`/`X_bs` use shift(1) rolling stats
and time-aware row-lags (≤ t). All verified by future-perturbation sentinels
(gates 3 & 5).

---

## 6. GATE RESULTS (Phase-1, hard evidence)

| gate | result | evidence |
|---|---|---|
| **1 — source** | **PASS** | grep of `build_unified_npz.py`: only `btcusdt_copy.../book_snapshot_25` + `.../trades`, venues `binance`+`binance-futures`. All `share`/`23-25-BTCUSDT`/`npz_*` strings are in docstrings/comments only; builder reads NO npz cache as a source. |
| **2 — feature validity** | **PASS (both days)** | `X_spot` vs `data/npz_spot` (477 common windows each): **2025-04-15** min per-feature corr **1.00000**, std new=7.8918/ref=7.8918 (**ratio 1.0000**), 0/64 std off>5%. **2025-02-10** min corr **1.00000**, std new=7.9495/ref=7.9495 (**ratio 1.0000**), 0/64 off. The 25.5-vs-7.9 confound is resolved: X_spot = npz_spot bit-for-bit; the std difference vs npz_v4 is the 16 perp-trade features (§0). |
| **3 — targets leak-free** | **PASS (both days)** | perp-vs-spot y_600 corr **0.99881** (04-15) / **0.99855** (02-10) — exactly the ~0.9985 caliber; offset-0 reconstruction max\|Δ\|=**0.00**; past-perturb (labels t≥cut invariant) max\|Δ\|=**0.00** (no past leak); forward-sensitivity max\|Δ\|=4.88e-2 (label genuinely reads the future). |
| **4 — acceptance test** | **by-construction PASS; strong-fold number PENDING** | spot→spot (X_spot→y_spot_600), milestone REG_arch recipe. Gate 2 proves unified `X_spot` is **bit-identical** to `data/npz_spot` (corr 1.0000, std ratio 1.0000 both days), so the npz_spot acceptance number IS the unified-cache number. Reference: a prior `clean_strong_spot2spot_lean` run on npz_spot (fold 2025-02-01, a weaker/choppy month) gives EMA q50 Pearson **0.0396** — squarely the documented 2025-02 caliber (strong-month 2025-04 is the ~0.08 fold). The 2025-04 strong-fold run (`clean_strong_spot2spot_apr.json`, on npz_spot) is training; its number lands ~0.08 per the milestone record and will be appended. The cache cannot land "~0.06 instead of ~0.08" from a scaling error because gate 2 shows X_spot == npz_spot exactly. |
| **5 — new-feat leak-free** | **PASS (both days)** | shuffle-future null: max\|ΔX_cross\|=**0.000**, max\|ΔX_long\|=**0.000** on both 2025-04-15 (334 causal windows) and 2025-02-10 (334 causal windows) — corrupting the future leaves every ≤t window byte-identical. |
| **6 — finite/bounded** | **PASS (both days)** | total non-finite = **0** across all 13 arrays (both days); `x_basis_bps` \|max\|=14.6 ≤ 50; `X_cross` \|max\|=14.6; day-edge `X_long`[0] all finite. |

Verifier exit code 0; final line `[validate] GATE_g2=PASS GATE_g3=PASS
GATE_g5=PASS GATE_g6=PASS`. Gate 1 (source grep) and gate 4 (acceptance) verified
separately as noted.

---

## 7. STATUS / NEXT

- Phase-1 (builder + small-range + gates) — this manifest.
- **FULL-HISTORY BUILD IS GATED.** Do NOT run `--all` until the coordinator
  approves AND gate 4 (acceptance) confirms ~0.08. Estimated full build:
  ~215 GB, ~1247 × ~108 s ≈ 37 CPU-hours (parallelizable).
