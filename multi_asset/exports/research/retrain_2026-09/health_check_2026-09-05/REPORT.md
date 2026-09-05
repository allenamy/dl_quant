> **创建:** 2026-09-05 04:3xZ – 05:4xZ UTC (v2: team-lead refinements of 05:0xZ — per-leg rank base `UMASK_SCOPE=m1`, binding cost vectors, execution bands, 附加 seat block) | **Session:** b9646a9e, teammate `health-check` | **状态:** complete — numbers only, **no admission verdict** (PREREG §3) | **预注册:** `docs/PREREG_live_form_health_check_2026-09-05.md` §0–§4 followed literally; the 10 PREREG arms were run under `UMASK_SCOPE=m1` (primary) after the lead's refinement; the earlier `UMASK_SCOPE=trade` runs are kept as sensitivity rows; 5 further runs (1 cost sensitivity + 4 seat-block arms) were ordered by the lead and are labelled 附加/sensitivity, never mixed into the PREREG tables | **作废条件:** device default path not bitwise-equal to the axisB reference (checked: PASS ×3, §T14); any change of the mask files, `cost_calib.json`, the pinned king, the F10 preds, the metas or the live seat file (sha256 in §T1/§T14/§11); any metric or window changed after numbers (one repair: the monthly table had included post-cut anchors in 2026-08 — fixed and re-run for every arm before this version). **[单仪器 pod2]**. Labels: **VERIFIED** = printed by a script quoted in §T14; **INFERRED** = derived from verified numbers with the reasoning stated; **UNRESOLVED** = not established here.

# Live-form full-history strict-causal health check — U-PIT universe, M1 per-leg rank base, dynamic seat, FTRIM, live fee-only cost, 2.0× / 2.5× / 3.0×

Read-only on `/workspace/data`, `/workspace/shadow_bundle_v3`, `/workspace/port_w10`, `/workspace/review_scratch/{rolling_king,combo_recheck,cadence_seats,jpline_rebuild,refute_*}` and on `~/wide_shadow` (three files read: `state/leg_returns_live.json`, `shadow_bundle.aug20260816_backup/leg_returns.npz`, `shadow_log.jsonl`); writes only under `/workspace/review_scratch/health_check/` (pod) and `…/scratchpad/review_caliber/health_check/` (Mac). No GPU.

## 0. What this is, in one paragraph

The live book (combo: rev24 leg off, king 55 / V2MAIN 45, FTRIM, M1 rank base, per-name stop d30_n2_c42, executor re-demean and constant gross 2.0×NAV) was replayed from 2022-01-31 to 2026-08-30 with the pod port device, strictly causal: yearly out-of-sample king (`slow_pred_pinned.npy`), walk-forward F10 predictions with a 60-anchor embargo, the seat produced by the device from its own out-of-sample leg returns, a point-in-time universe rebuilt every month from trailing 30-day quote volume, live M1 semantics per leg (king / rev24 / F10 ranked within the universe members, the fund leg ranked in the full 829-name base, trade set = members with qv4h ≥ 2.5e5, forced exit otherwise), and execution cost = the fees the live fills actually paid. Ten PREREG runs: U-PIT × {prod, log} × {s42, s2027} × {live fee-only cost, device default cost} = 8, plus U-FROZEN (today's 449 list projected back — look-ahead, upper bound only) × prod × {s42, s2027} × live cost = 2. Leverage is a post-hoc mapping of the same anchor series (NAV return = net per unit gross × L). Sensitivity and 附加 runs: the rank-base scope (`trade`, `members`), one fee+slippage cost vector, and the fixed live seat 0.21/0.79; plus a reconstruction of the live seat from the producer's own leg rows. All PREREG §2 metrics are in §T3–§T12, the seat block in §T13; this head only reads them out.

## 1. Bottom line (primary arms = U-PIT · m1 · prod caliber · live fee-only cost, seeds s42 / s2027; VERIFIED from results/M1_UPIT_prod_s{42,2027}_ccal.json)

| window | net bps/anchor per gross [CI95] | anchor Sharpe [CI95] | NAV %/yr at 2.0× (arith) | CAGR at 2.0× | max DD at 2.0× | worst day at 2.0× | days < −2% / < −5% (of n) |
|---|---|---|---|---|---|---|---|
| 2024 (incl. H1 warm-up) | +0.56 [−0.34, +1.52] / +0.59 [−0.33, +1.56] | 1.24 / 1.30 (CI includes 0) | +24.4 / +25.7 | +25.2 / +26.8 | 22.7 / 23.1 % | −3.41 / −3.32 % | 10 / 0 · 11 / 0 (366) |
| 2024-H1 ⚠ seat warm-up | −0.52 / −0.52 | −1.18 / −1.17 | −22.7 / −22.7 | −21.8 / −21.8 | 18.9 / 19.7 % | −3.41 / −3.32 % | 6 / 0 · 8 / 0 (182) |
| 2024-H2 | +1.62 [+0.36, +2.89] / +1.68 [+0.43, +2.95] | 3.53 / 3.66 | +71.0 / +73.7 | +99.3 / +104.7 | 8.3 / 7.2 % | −2.46 / −2.53 % | 4 / 0 · 3 / 0 (184) |
| 2025 | +0.65 [−0.44, +1.78] / +0.77 [−0.31, +1.87] | 1.14 / 1.34 (CI includes 0) | +28.5 / +33.6 | +28.9 / +35.6 | 21.0 / 17.8 % | −4.74 / −4.92 % | 22 / 0 · 22 / 0 (365) |
| 2026 → 08-10 | +3.19 [+1.71, +4.72] / +3.14 [+1.66, +4.68] | 4.96 / 4.90 | +139.7 / +137.7 | +288 / +281 (7.3 months: total +128 / +125 %) | 8.4 / 8.1 % | −3.92 / −4.04 % | 7 / 0 · 8 / 0 (222) |
| 2024 → 26 | **+1.21 [+0.57, +1.91] / +1.25 [+0.61, +1.97]** | **2.21 [1.06, 3.50] / 2.29 [1.13, 3.60]** | **+52.8 / +54.8** | **+64.8 / +68.1** | **22.7 / 23.1 %** (span 298 d, recovered) | −4.74 / −4.92 % | 39 / 0 · 41 / 0 (953) |
| 2025 → 26 | +1.61 [+0.69, +2.55] / +1.67 [+0.76, +2.58] | 2.69 / 2.78 | +70.5 / +73.0 | +95.6 / +100.4 | 21.0 / 17.8 % (span 164 / 101 d) | −4.74 / −4.92 % | 29 / 0 · 30 / 0 (587) |

Plain reading. Over the evaluation window (2024-01-01 → 2026-08-10, 5,718 anchors, 953 UTC days) the replayed live form earns about 1.2 bps per anchor per unit gross, which at the live 2.0× gross is 53–55 % of NAV per year arithmetic (65–68 % compounded), with a 23 % max drawdown that took about 300 days to recover (peak 2024-03, trough 2024-07, recovered 2025-01), a worst single day of −4.7 to −4.9 %, and no day worse than −5 %. The confidence interval of the mean excludes zero for 2024→26, 2025→26, 2024-H2 and 2026, but **not for the calendar years 2024 and 2025 taken alone**: 2024 is dragged by the seat warm-up half (H1 −23 %/yr at 2×), and 2025 is a moderate year (+29 / +36 % compounded at 2×, Sharpe 1.1–1.3) whose worst month (2025-04, −17.0 / −14.7 % at 2×) opened a 164-day (s42) / 101-day (s2027) drawdown. 2026 to the cut is exceptional (+3.1–3.2 bps per anchor, Sharpe ~5, no negative month, worst month +1.4 / +1.8 %) and dominates every multi-year average. Negative quarters at 2× (§T6): 2024-Q1 −2.5 / −3.0 %, 2024-Q2 −9.3 / −8.8 %, 2025-Q2 −5.8 / −1.4 %, 2025-Q4 −1.4 / −2.4 %. Negative months (§T7): 9 of 32 (2024-02 −6.5 %, 2024-04 −5.6 %, 2024-05 −0.8 %, 2024-06 −3.1 %, 2024-07 −4.4 %, 2025-04 −17.0 %, 2025-08 −1.8 %, 2025-11 −1.0 %, 2025-12 −4.1 %, s42 at 2×).

## 2. Leverage (§T5; primary arms, 2024→26 unless stated)

| L | arith %/yr | CAGR % | vol %/yr | max DD % (span days) | worst day % | worst week % | worst month % (2025-04) | days < −2 % / < −5 % / < −10 % of 953 | 8-anchor worst % | daily VaR99 / CVaR99 % | min equity/gross vs 1.5 % maintenance | after expected timing haircut, arith %/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 52.8 / 54.8 | 64.8 / 68.1 | 24.0 | 22.7 / 23.1 (298 / 298) | −4.74 / −4.92 | −11.4 / −11.0 | −17.0 / −14.7 | 39 / 0 / 0 · 41 / 0 / 0 | −7.3 / −8.1 | −2.95 / −3.66 · −2.91 / −3.86 | 0.48 (0 touches) | 48.7 / 50.6 |
| 2.5 | 66.0 / 68.5 | 85.0 / 89.7 | 29.9 | 27.7 / 28.2 (298 / 298) | −5.90 / −6.14 | −14.1 / −13.7 | −20.9 / −18.1 | 75 / 2 / 0 · 73 / 5 / 0 | −9.2 / −10.2 | −3.68 / −4.57 · −3.62 / −4.82 | 0.38 (0) | 60.9 / 63.2 |
| 3.0 | 79.2 / 82.2 | 107.0 / 113.3 | 35.9 | 32.5 / 33.1 (298 / 298) | −7.05 / −7.34 | −16.8 / −16.3 | −24.7 / −21.5 | 97 / 7 / 0 · 93 / 8 / 0 | −11.0 / −12.2 | −4.41 / −5.47 · −4.34 / −5.77 | 0.31 (0) | 73.0 / 75.8 |

Plain reading. Leverage scales the mean and the tails together: at 3× the same history gives a 32–33 % max drawdown, a worst week of −17 %, a worst month of −22 to −25 %, and 7–8 days worse than −5 % (there are none at 2×). Liquidation is never approached: with gross reset to L×NAV at every anchor the equity/gross ratio at the end of the worst anchor is 0.48 / 0.38 / 0.31 against a 1.5 % maintenance line, and the worst 8-anchor stretch (−7 to −12 % of NAV) does not change that. The rolling 90-day daily Sharpe over 2024→26 has p5 / median / p95 = −2.0 / 1.5 / 6.4 (s42) and −2.1 / 1.7 / 6.4 (s2027): one quarter in twenty looks like a Sharpe −2 quarter; the median quarter is ≈ 1.5–1.7, below the full-window 2.2–2.3 that the 2026 stretch produces. Turnover: the replay trades 0.080 / 0.075 of gross per anchor over 2024→26 (0.035 / 0.037 in 2026) against the live steady 0.048 [0.041, 0.055]; at 2× that is 0.16 / 0.15 of NAV per anchor. The last column applies the full-history timing haircut of §4 (nominal anchor → venue moment N+25 min): −4 %-points of arithmetic NAV return per year at 2×.

## 3. Regimes (§T8; 2024→cut; primary arms s42 / s2027; net bps/anchor per gross [CI95])

| slice (definition in §T8) | low tercile | mid tercile | high tercile |
|---|---|---|---|
| σ_fund, descriptive terciles (cuts 5.3 / 13.7 bps per 8h) | +0.39 [−0.66, +1.42] / +0.35 (σ mean 3.2) | +1.55 [+0.36, +2.71] / +1.56 (9.4) | +1.68 [+0.41, +2.91] / +1.84 (21.2) |
| σ_fund, causal expanding cuts (3.4 / 9.4 at window end) | +0.70 [−0.86, +2.24] / +0.54, n 553 | +0.02 [−1.37, +1.47] / +0.01, n 1,230 | +1.65 [+0.83, +2.46] / +1.74, n 3,935 |
| breadth = nsel, descriptive (cuts 266 / 330 names) | +0.43 [−0.60, +1.40] / +0.42 (249) | +2.00 [+0.76, +3.23] / +2.07 (299) | +1.19 [−0.05, +2.40] / +1.26 (366) |
| negative-funding share, descriptive (cuts 0.12 / 0.26) | +0.60 [−0.59, +1.77] / +0.53 (0.05) | +1.76 [+0.54, +3.00] / +1.82 (0.19) | +1.26 [+0.04, +2.34] / +1.40 (0.34) |
| BTC 30-day realised vol, descriptive (cuts 41 / 53 %) | +1.23 [+0.10, +2.40] / +1.32 (35 %) | +1.38 [+0.15, +2.61] / +1.51 (48 %) | +1.01 [−0.02, +2.06] / +0.93 (61 %) |

Plain reading. The book earns when funding rates are dispersed: the lowest-dispersion third of anchors (σ_fund ≈ 3 bps per 8h) returns +0.35 to +0.39 bps per anchor with a confidence interval that includes zero (≈ +15–17 %/yr at 2×), the middle and upper thirds +1.55 to +1.84 (≈ 68–81 %/yr at 2×) with intervals above zero; under the causal expanding cuts the mid bucket (σ ≈ 3.8, 1,230 anchors) is flat at 0.0. Breadth is not monotonic (mid tercile best; consistent with `AUDIT_live_vs_replay_2026-09-04` §6); the causal breadth terciles are degenerate because tradeable names trend upward (all but 358 of the 2024+ anchors fall in "high"). The share of negative-funding names helps mildly. BTC volatility does not matter. `regime_dash.py` has no breadth ("宽/窄档") definition (its bands are σ_fund / short-interval share / deep-negative share; `regime_hist_pct.json`, the dashboard's reference, carries n_elig percentiles p25 / p50 / p75 = 144 / 197 / 350 that the dash never computes), so breadth here is nsel terciles, stated as such; the rec's members count (nmember, the n_elig-style count) is in §T10: 254 / 277 / 404 / 449 for 2024-H1 / 2024-H2 / 2025 / 2026 under m1.

## 4. Cost, carry, turnover, and the execution bands the device cannot carry (§T9, §T9b, §T9d; primary arms 2024→26)

| item | value | label |
|---|---|---|
| turnover per anchor, fraction of gross | 0.080 / 0.075 (2026: 0.035 / 0.037; live steady 0.0477, CI [0.041, 0.055], cost-calib §7) | VERIFIED |
| cost with the live fee-only tiers (maker 1.80 / taker 4.50 bps, maker share 0.851 / 0.925 / 0.921 by tier; binding vector) | 0.167 / 0.157 bps per anchor per gross = 7.3 / 6.9 % of NAV per year at 2× (live: 2.035 bps per unit turnover = 0.093 bps of gross per anchor ≈ 2.0 % of gross per year at the live turnover) | VERIFIED |
| cost with the device default tiers | 0.210 / 0.197 = 9.2 / 8.6 % of NAV per year at 2× ⇒ the calibrated arm nets +0.044 / +0.040 bps per anchor more (§T9b) | VERIFIED |
| carry paid (funding, replay = panel rate × 4/interval) | 0.501 / 0.512 bps per anchor per gross = 21.9 / 22.4 % of NAV per year at 2×; 32 / 31 % of the gross price P&L (1.87 / 1.92) | VERIFIED |
| **maker price improvement vs the executor's anchor mid** (sensitivity arm: cost-calib fee+slippage vector −2.41 / +16.79 / 0.851 …, §T9d) | cost becomes −0.035 bps per anchor (a net rebate of 1.5 % of NAV per year at 2×); net +0.20 bps per anchor per gross above fee-only over 2024→26 (+0.19 for 2025→26, +0.10 for 2026; turnover × ≈ 2.5 bps) | VERIFIED arithmetic on an INFERRED-free vector (maker fills beat the N+24-min mid by +3.9 bps CI [3.5, 4.5]; taker top-ups lose 12.3 bps CI [2.8, 21.3], pooled) |
| **timing decay, nominal anchor N → venue moment N+24 min** — not in any COST_B vector | full-history instrument `pod_alpha_decay_20260904.out` (repo `multi_asset/exports/research/retrain_2026-09/`): book proxy 0.21·xz(king)+0.79·xz(fund) retains 91 % (2025) and 95 % (2026) of its mean at +25 min, 2024 proxy −0.04 → −0.13 bps; per leg king 85 / 81 / 81 %, fund 108 / 95 / 96 %, F10 86 / 54 / 107 % (2024 / 2025 / 2026). Applied as the **expected haircut**: 2024→26 mean 1.21 / 1.25 → 1.11 / 1.15 bps (52.8 / 54.8 → 48.7 / 50.6 %/yr at 2×); 2025→26 1.61 / 1.67 → 1.51 / 1.56 (70.5 / 73.0 → 66.3 / 68.5); 2026 3.19 / 3.14 → 3.03 / 2.99 (139.7 / 137.7 → 132.7 / 130.8); the small-sample live band is paper nominal − paper shifted = +2.85 bps of gross per anchor on 53 anchors (wide CI, cost-calib §9) | INFERRED (full history) / VERIFIED band (n = 53) |
| **execution vs paper** (real positions × Δmid − paper priced at the venue moment, n = 53, cost-calib §9) | +1.23 bps of gross per anchor, CI95 [−3.72, +6.10]: a wash within noise; the never-filled residual (8 % of intended per anchor, maker fill ratio 0.848 → 0.929 after top-ups) lives inside this band | VERIFIED, wide |
| +60 s markout (not consumed) | maker −6.2 bps notional-weighted, CI95 [−13.7, +1.3] on 5 % of fills chosen by symbol and fill order; taker top-ups −53 bps on 21 marks. Post-fill drift is common to the paper and the real book, so it is not an incremental cost against the paper book and would double-count the anchor-mid slippage above | INFERRED, reported as a band only |

Plain reading. The cost the replay charges (fees only, 7 % of NAV per year at 2×) is what the live fills paid. Two things sit outside the device: the maker price improvement, which if real adds about +0.2 bps per anchor (≈ +9 %/yr of NAV at 2×), and the timing decay from the nominal anchor to the moment the executor actually trades, which removes about 8 % of the mean (≈ −4 %/yr of NAV at 2× on 2024→26). The two roughly cancel; the live paper-vs-real reconciliation (+1.23 [−3.72, +6.10] bps per anchor at n = 53) is consistent with that and cannot resolve anything finer. The largest open item of the previous version — a possible adverse-selection cost implied by the markout sample — is now understood as not incremental against the paper book (cost-calib's semantics note) and is carried as a band only. Carry is a real and stable drain: 22 % of NAV per year at 2×, a third of the gross price P&L.

## 5. Seeds, calibers, universes, rank-base scope (§T3, §T9c, §T9e)

- **Seeds** (F10 s42 vs s2027): within 0.12 bps per anchor in every window (largest 2025: +0.65 vs +0.77).
- **Caliber** (prod = exchange-style Π(1+r)−1 vs log = Σ of 5-minute simple returns), m1: prod is slightly higher — 2024→26 +1.21 / +1.25 vs +1.15 / +1.19, 2024 +0.56 / +0.59 vs +0.46 / +0.47, 2025 +0.65 / +0.77 vs +0.63 / +0.73, 2026 +3.19 / +3.14 vs +3.15 / +3.11. The 7–10 % "log overstatement" quoted in PREREG §0 was the CAL=simple pseudo-convexity (E-0904-F), which both calibers here avoid; prod is the exchange caliber and is the primary.
- **U-FROZEN vs U-PIT** (m1, prod, live cost, §T9c): +0.45 / +0.52 bps per anchor over 2024→26 and +0.60 / +0.67 over 2025→26 (2024 +0.22 / +0.27, 2025 +0.69 / +0.79, 2026 +0.45 / +0.47; Sharpe 2.67 / 2.85 vs 2.21 / 2.29). This is the look-ahead in today's 449 list (names that turned out to be liquid winners), **not** an edge available to the live frozen list going forward; it is larger than under the `trade` scope (+0.24 / +0.31) because with m1 the universe also sets the king/F10 rank base.
- **Rank-base scope** (§T9e, prod, same seed and cost): m1 − trade (all legs on the 829 base) = +0.03 / +0.05 over 2024→26 and +0.13 / +0.18 over 2025→26, with opposite signs by year (2024 −0.13 / −0.17, 2025 +0.27 / +0.32, 2026 −0.09 / −0.05): the rank-base choice moves single years by ±0.1–0.3 bps per anchor (±4–13 %/yr at 2×) and nets to ≈ 0 over the window. m1 − members (every leg within the universe, the pre-M1 live form) = +0.025 / +0.030 over 2024→26, all of it in 2026 (+0.13 / +0.13 = ≈ +5.7 %/yr of NAV at 2×): the fund-base widening (M1) pays only when the base (597 finite-funding names in 2026) is much wider than the universe, and is ≈ 0 in 2024–2025 when the two nearly coincide. The seat is almost unchanged across scopes (§T13b).
- **U-PIT vs the M1+T400 reference form** (REF row, log/s42, default cost; the form of the 09-04 caliber revalidation): 2024→26 +1.11 (m1 log/42/def) vs +1.26 (REF); the difference is inside the caliber-and-scope noise above.

## 6. Caliber reconciliation with the earlier receipts (§T11)

The REF row reproduces the STATE.md 09-04 numbers exactly in the unit-book caliber: net_ex 2024 / 2025 = +0.149 / +0.359 bps per anchor, Sharpe 0.53 / 1.15. The m1 primary arm in the same caliber reads +0.107 / +0.203 (Sharpe 0.45 / 0.67) for 2024 / 2025 and +2.51 (4.94) for 2026. This report's numbers are higher because they are **per unit gross**: the blended unit book (0.55·king book + 0.45·F10 book) has a floating gross of 0.45–0.78 (mean 0.59 over 2024→26, §T10) because the two books partly cancel, and the executor re-levers the blend to a constant 2.0×NAV at every anchor, so the NAV return is net_ex / gross_total × 2, not net_ex × 2. PREREG §0 fixes this mapping; both calibers are listed in §T11. The executor's own re-levering adds turnover the rec does not carry (+2 / +3 / +8 % in 2024 / 2025 / 2026 = +0.003–0.006 bps per anchor at fee-only cost, `results/diff_quant.json`) — negligible.

## 7. 附加: 席位路径 — the seat the live book holds vs the seat the replay produces (§T13, §T5f, §T9f)

**What the live book holds.** The producer's seat window is its own rolling 950-row leg file: 836 rows seeded from the 08-16 package (`shadow_bundle.aug20260816_backup/leg_returns.npz` tail, 2026-03-28 20:00 → 2026-08-15 00:00, king booster 29ffaf58 = the pre-v3 king) plus 114 rows scored live at consecutive anchors (08-15 04:00 → 09-05 00:00). The v3 package's own leg history (10,176 rows, pinned king, 2022-01-08 → 2026-08-30) is loaded in front of that window and never enters the last-900 rule. Alignment proof (§T13a): the producer's printed w3 at all 117 shadow_log signal anchors is reproduced from the aligned rows within 0.025 (raw) / 0.018 (king share), mean 0.007, and exactly at the last anchor (0.1937 vs 0.1938; raw w3 [0.1696, 0.1247, 0.7057] at 2026-09-05 04Z) — VERIFIED; the residual is consistent with row placement around the two logged anchor gaps (08-18 12Z, 08-29 16Z) and is not resolved here.

**Seat trajectories** (king share = king / (king + fund); §T13b/c):

| series | 2024-H1 | 2024-H2 | 2025 | 2026 (to 08-30) | 2026-06 | 2026-07 | 2026-08 | at 2026-08-30 20Z | last |
|---|---|---|---|---|---|---|---|---|---|
| device dynamic seat, m1 arm | 0.523 | 0.921 | 0.742 | 0.383 | 0.290 | 0.299 | 0.311 | 0.328 | — |
| device dynamic seat, members arm (pre-M1 form) | 0.545 | 0.925 | 0.746 | 0.379 | 0.287 | 0.297 | 0.310 | 0.327 | — |
| device dynamic seat, trade arm | 0.421 | 0.941 | 0.687 | 0.375 | 0.289 | 0.294 | 0.291 | 0.296 | — |
| seat implied by the v3 package's own rows | — | — | — | — | 0.303 | 0.310 | 0.306 | 0.312 | 0.323 (09-05) |
| **live** (producer rows, reconstructed; producer's printed w3 where logged) | — | — | — | — | 0.175 | 0.238 | 0.225 (producer 0.226) | 0.215 | 0.194 (producer 0.194, 2026-09-05 04Z) |
| fixed-seat arm (state-faithful) | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | — |

**Where the difference comes from** (§T13d/e). Over the common window 2026-03-01 → 08-30 the fund leg is the same in every history (mean 6.4 / 6.3 / 5.3 bps per anchor, Sharpe 9.3 / 9.4 / 9.0 for live rows / v3 rows / device m1; correlation of the device fund leg with the live rows 0.89), but the **king leg is not**: 1.77 bps per anchor (Sharpe 2.9) in the producer's rows vs 2.81 (4.6) in the v3 package rows and 2.88 (4.7) in the device (correlation 0.73). The trailing-900 window the msharpe rule sees at 2026-08-31 00Z: king mean 1.59 bps (shp 0.055 per anchor) in the live rows vs 2.83 (0.095) in the v3 rows and 2.91 (0.097) in the device; fund 6.50 (0.20) vs 6.43 (0.20) vs 5.33 (0.19) ⇒ seat 0.21 vs 0.32 vs 0.34. **The live seat is lower because the king-leg history the producer carries (08-16 package seed + live scoring) shows roughly half the king-leg mean of the pinned-king rows over the same anchors; the fund leg does not differ.** At the last live anchor the trailing-900 king mean is down to 1.34 bps (shp 0.047) and the seat to 0.19.

**What the seat is worth** (§T9f, §T5f; prod, live cost, s42 / s2027): the fixed live seat 0.21/0.79 held through the whole history earns +0.50 / +0.52 bps per anchor per gross over 2024→26 (CI95 [−0.16, +1.18] / [−0.15, +1.18], includes zero; Sharpe 0.92 / 0.94) against +1.21 / +1.25 for the dynamic seat: Δ = −0.70 / −0.74 (2024 −1.33 / −1.38 with 2024-H2 at −1.75 / −1.80 = −77 %/yr at 2×; 2025 −0.76 / −0.83; **2026 +0.42 / +0.48**, i.e. in the fund-dominated 2026 the fixed 0.21 seat beat the dynamic seat: +3.61 / +3.62 vs +3.19 / +3.14, +158 / +159 %/yr at 2×). At 2.0× the fixed-seat form over 2024→26: +22.0 / +22.5 %/yr arithmetic, CAGR +21.1 / +21.7 %, max DD 49.1 / 49.2 % over a 763-day span, worst months 2024-11 −15.1 % and 2024-12 −14.7 %, 14 negative months of 32; over 2025→26: +56.9 / +58.2 %/yr, CAGR +70.3 / +72.7 %, max DD 21.3 / 20.5 %. The members-scope arm (pre-M1 form, seat legs over the universe) is within −0.03 bps per anchor of the m1 arm everywhere, so the seat gap is not a rank-base effect.

## 8. Where the replay still differs from the live book, with the size where known

| # | item | replay | live | size | label |
|---|---|---|---|---|---|
| 1 | universe | U-PIT: top-449 by trailing 30-day quote volume at each month start, ≥ 30 days listed (PREREG §0 row 1) | frozen 449 list `syms450.txt`, chosen 08-2x, no refresh | U-FROZEN − U-PIT = +0.45 / +0.52 (2024→26), +0.60 / +0.67 (2025→26) bps per anchor per gross = look-ahead of the frozen list, not a forward edge; tradeable names 2026: U-PIT 296, U-FROZEN 279 (§T2), live 232–234 (STATE 09-04) | VERIFIED |
| 2 | fund rank base (M1) | all names with finite fund EMA on the panel: 297 / 464 / 597 (2024 / 2025 / 2026, `results/diff_quant.json`) | 528 = venue TRADING ∪ live450 (PREREG_deploy_universe AMENDMENT, 09-04) | replay measure of the widening itself: m1 − members = +0.13 / +0.13 in 2026, ≈ 0 before (§T9e); the 597-vs-528 residual is not measured | VERIFIED (replay) |
| 3 | king / F10 rank base | within the universe members (m1) | within the universe members | matched by `UMASK_SCOPE=m1`; the alternative (829 base for every leg, `trade`) moves single years by ±0.1–0.3 and the window by +0.03 / +0.05 (§T9e) | VERIFIED |
| 4 | seat path | device msharpe-900 over its own legs: king share 0.52 / 0.92 / 0.74 / 0.38 (2024-H1 / H2 / 2025 / 2026), 0.33 at 08-30 | producer msharpe-900 over its own rolling rows: 0.21 at 08-30, 0.19 at 09-05 04Z, monthly 0.18–0.24 since June | king-leg history (§7): live rows' king leg ≈ half the pinned-king rows' mean over the same anchors, fund identical; value of the seat path: dynamic − fixed(0.21) = +0.70 / +0.74 bps per anchor over 2024→26, +0.31 / +0.34 over 2025→26, **−0.42 / −0.48 in 2026** (§T9f) — the largest known replay-vs-live gap, now quantified in both directions | VERIFIED |
| 5 | F10 end date | preds end 2026-08-10 20:00Z; the 2026 fold model was not saved (`/workspace/f8_2026-08-22/models` holds only the full-history `f10_live_s{42,2027}.pt`, forbidden for history) | live F10 v3 retrained to 08-30 | 08-11 → 08-30 (120 anchors) is not the live form: with the F10 leg absent the replay loses −4.2 bps per anchor per gross, −9.8 % of NAV at 2× in 20 days (§T12); the live book lost −0.65 % of NAV over 08-25→09-04 (STATE 09-05) — not comparable | VERIFIED |
| 6 | fills and price | every target filled at the anchor mid; cost = turnover × fee-only tiers | maker fill ratio 0.848 → 0.929 after top-ups, −5022 first refusal 25.5 %, unfilled 8 % of intended per anchor; maker fills beat the N+24-min mid by +3.9 bps, taker top-ups lose 12.3 bps | +0.20 bps per anchor per gross if the price improvement is carried (§T9d); execution-vs-paper band +1.23 [−3.72, +6.10] (n = 53) | VERIFIED |
| 7 | pricing moment | nominal 4h grid | executor trades N+23 → N+26 min | expected haircut ≈ 8 % of the mean (proxy retention 91 / 95 % in 2025 / 2026; 2024 −0.09 bps) = −4 %-points of NAV per year at 2× on 2024→26 (§2, §T5 last row); live band +2.85 bps per anchor on 53 anchors, wide | INFERRED / VERIFIED band |
| 8 | executor re-levering | rec turnover = Σ|Δ blended weights| / gross | book re-scaled to 2×NAV every anchor | +2.0 / +3.3 / +8.3 % turnover (2024 / 2025 / 2026) = +0.003 / +0.006 / +0.006 bps per anchor per gross at fee-only cost — negligible | VERIFIED |
| 9 | funding | panel rate × 4/interval | exchange settlement | −0.12 bps per anchor (PREREG §0, cited from the caliber review) | cited |
| 10 | membership look-ahead | meta membership / `sel` requires a finite forward y4 (≥ 46 of the next 48 5-minute bars) | unknowable at the anchor | affects names delisted within the next 4h only; not measured | UNRESOLVED, small |
| 11 | seat warm-up | pinned king is NaN before 2024 ⇒ the 900-anchor seat window is king-free until ~2024-06 (king share 0.52 in 2024-H1) | live seat seeded from a 900-row file, no warm-up | 2024-H1 −22.7 %/yr at 2× is flagged and carried in every 2024 and 2024→26 figure | VERIFIED |
| 12 | FTRIM and M1 dates | applied over the whole history | FTRIM from 09-02 12Z, M1 from 09-04 04Z | forward-equal; the pre-09-02 live book is not the replay form (FTRIM +0.21–0.23, M1 +0.06–0.09 bps per anchor, STATE 09-02 / 09-04) | cited |
| 13 | member cap | m1 / members: universe ∩ listed, no cap (449 in 2026) | producer NTOP = 400 by qvm among the universe (pre-M1 form) | a top-400 cap binds only when > 400 universe names have data (2026): not run; size unknown, bounded by the trade-scope sensitivity | UNRESOLVED, small |
| 14 | cost tiers, stop layer, ≥ 80 gate, band, EMA, cap, realized gross | identical rule (cost-calib §2 verified the tier rule against the producer; stop d30_n2_c42); gross assumed 100 % of L×NAV | same; realized 98.1–100.7 % of target (STATE 09-03/09-04) | ≤ 2 % scaling of every NAV number | VERIFIED / cited |

## 9. Device and universe-mask notes (what changed on disk and why)

- Device `w10_health.py` (sha256 8684d9a9…) = `rolling_king/w10_universe_recheck.py` (5424aceb…, = port `w10_universe.py` 64c70a44… + REF_SKIP guard) + three additions, all self-reported in `config_json` (`HEALTH` block with the device sha, `COST_B`, `COSTB_JSON`, `UMASK_SCOPE`): (a) `COSTB_JSON` cost-tier override; (b) `UMASK_SCOPE` ∈ {`members` (original semantics: the mask shrinks the member set = rank base and trade set of every leg), `trade` (mask restricts only `sel`, every leg ranked on the 829 base), `m1` (members = universe ∩ listed for king / rev24 / F10 and the trade set; the fund leg's z = rank position of each member among all finite fund-EMA values of the 829 base — `xz_in_base` semantics of `shadow_loop_v3.py` L471 / PREREG_deploy_universe §2d — in both the seat legs and the book)}; (c) the seat inputs (`legs()` series) saved in every artifact. **TRADE_TOPN must be unset (0)**: with 400 it would AND a second top-400-by-qvk cut onto the trade set that the live book does not have. Default path receipts: the pristine copy, the first patched copy and the m1 copy all reproduce the axisB `R0_pinned_log_s42` artifact bitwise on all four arrays with equal config (§T14, three PASS lines). `device.diff` (58 lines) is on the pod and the Mac.
- Masks (`build_umask.py`): U-PIT from the 5-minute cache channel `log_qv`, Σ expm1 over the 8,640 bars strictly before the first panel anchor of each month, names listed ≥ 30 days (listing = first finite `log_qv` bar; the cache's bar 0 is all-NaN, so names with data within the first three bars count as listed at the cache start), top 449, held for the month; U-FROZEN = `syms450.txt` (449 names, all present in the 829-symbol panel). Yearly counts and overlap in §T2: the two masks share 21 % / 27 % / 39 % / 65 % / 84 % of the 449 in 2022 … 2026.
- Cost files: `cost_calib.json` (cost-calib teammate, run 04:38:56Z, sha256 980384cc…) → `calib/costb_fee_steady.json` (9349ca63…, fee-only steady tiers, **the vector in the 6 calibrated arms**) and `calib/costb_feeslip_steady.json` (43b7aa4a…, fee+slippage-vs-anchor-mid, **sensitivity arm only**).
- Seat block: `align_live_rows.py` (Mac, read-only on `~/wide_shadow`) → `live_rows_aligned.json`; `signal_w3.json` (the producer's w3 per anchor, extracted read-only from `shadow_log.jsonl`); `seat_compare.py` (pod) → `results/seat_compare.json`.
- Metrics `health_metrics.py` (windows, leverage mapping, day-block bootstrap seed 20260905 × 2000, slices, liquidation proximity, rolling Sharpe; monthly table restricted to the cut in this version), tables `render_report.py`, gap sizes `diff_quant.py`. All commands verbatim in §T14 (`logs/commands.txt`).

## 10. Not verified, and risks not covered by any assertion here (TEAM_PROTOCOL §1)

- The execution bands of §4 (price improvement +0.2 bps, timing haircut −8 %) are carried as arithmetic on the calibration and on a full-history instrument, not as device runs; the live reconciliation at n = 53 cannot separate them.
- Single instrument (pod2); jpline was not used. The second-instrument rebuild of 09-05 found ≤ 0.04 bps per anchor between king sources, so this is unlikely to move the picture, but it was not re-checked here.
- Bootstrap blocks are UTC days; the EMA book has multi-day persistence, so the CIs are probably somewhat too narrow. A longer-block sensitivity was not pre-registered and was not run.
- The live-seat alignment reproduces the producer's w3 to 0.02, not exactly; the residual (row placement around two logged anchor gaps) was not chased. The conclusion of §7 (king-leg history, fund identical) does not depend on it.
- The seat rows the producer carries come from the 08-16 package; whether the king leg's weaker showing there is the older booster, the live scoring, or the universe form of those rows was not separated (no arm).
- The members-scope arm has no top-400 member cap (item 13 of §8).
- The breadth slice uses nsel terciles because `regime_dash.py` has no breadth cut; the memory's "宽档 +2.97 / 窄档 −2.00" came from a monthly-breadth tercile study of another era and is not reproduced here.
- The live overlap window (08-26 → 09-04) cannot be compared to the replay: the replay's F10 leg ends 08-10 and its panel ends 08-30. The paper-vs-real reconciliation on the live anchors is the cost-calib teammate's §9 (twin + funding +0.26 bps per anchor, CI95 [−8.50, +8.91], n = 53), cited, not recomputed.

## 11. Files (pod `/workspace/review_scratch/health_check/`, Mac `…/scratchpad/review_caliber/health_check/`)

`setup_dev.sh` · `run_arm.sh` · `chain_eq.sh` · `chain_all.sh` · `chain_m1.sh` · `rerun_metrics.sh` · `w10_universe_recheck.py` (pristine, 5424aceb…) · `w10_health.py` (8684d9a9…) · `device.diff` · `build_umask.py` (746700fd…) · `check_equiv.py` · `health_metrics.py` · `render_report.py` · `diff_quant.py` · `align_live_rows.py` · `seat_compare.py` · `live_rows_aligned.json` · `signal_w3.json` · `leg_returns_live.json` (copy, dd23827c…) · `masks/{umask_UPIT.npz ccb7a080…, umask_UFROZEN.npz 70470dbd…, btc_rv30.npz e1c31393…, mask_summary.json, listing.json, regime_series.npz}` · `calib/{cost_calib.json 980384cc…, costb_fee_steady.json 9349ca63…, costb_feeslip_steady.json 43b7aa4a…}` · `dev/probe_artifacts/*.npz`, `dev_alt/probe_artifacts/*.npz` (28 artifacts: 3 equivalence, 10 PREREG m1, 10 trade-scope, 5 sensitivity/附加; sha256 in `logs/chain_all.log` and `logs/chain_m1.log`) · `results/*.json|txt` (26 arms + `diff_quant.json` + `seat_compare.json`) · `logs/{commands.txt, check_equiv.log, chain_*.log, setup_dev.log, build_umask*.log, health_metrics_*.log, *.out}` · `REPORT_tables.md` · `REPORT.md`.

---

# Tables (generated by `render_report.py` from `results/*.json`; nothing hand-typed)
<!-- generated by render_report.py v2; every number is read from results/<tag>.json (health_metrics.py), results/seat_compare.json, masks/mask_summary.json, calib/costb_*.json, logs/* -->

### T1. Arms (device w10_health.py; artifact and results receipts)

| group | tag | form | n anchors | first → last | artifact sha256[:16] | results json sha256[:16] |
|---|---|---|---|---|---|---|
| PREREG §3 (UMASK_SCOPE=m1) + REF | eq_patched_pinned_log_s42 | REF: M1+T400 (trade set = top-400 by qvk), log, s42, device default cost — equivalence artifact, NOT a PREREG arm | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 8bfe59b6ebc0a8c4 | 201c2c474b4947a7 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_prod_s42_cdef | U-PIT · prod · s42 · device default cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 1a7697d71c2bfa53 | a99a98b06434a7d0 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_prod_s42_ccal | U-PIT · prod · s42 · live fee-only cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 32bfecb9cf9c0e5c | f8ca109b7cc76b77 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_prod_s2027_cdef | U-PIT · prod · s2027 · device default cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 733df8e7d0aa4a55 | 83cfd8a9c5635a27 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_prod_s2027_ccal | U-PIT · prod · s2027 · live fee-only cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | a2c5ec76dfac990b | 1c8ae5e2f0c74681 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_log_s42_cdef | U-PIT · log · s42 · device default cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | f8d7adde00510a3a | 703c4b9eff8ca8bb |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_log_s42_ccal | U-PIT · log · s42 · live fee-only cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | d0a51738b9c7cb1c | 161263d673710d98 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_log_s2027_cdef | U-PIT · log · s2027 · device default cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | c55f71dcd1bd44f9 | efb24f5eb73b665f |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UPIT_log_s2027_ccal | U-PIT · log · s2027 · live fee-only cost · UMASK_SCOPE=m1 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 10e64fdb56a62e37 | 6539b531bb28c01a |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UFROZEN_prod_s42_ccal | U-FROZEN · prod · s42 · live fee-only cost · UMASK_SCOPE=m1 | 10008 | 2022-01-31 00:00 → 2026-08-30 20:00 | 6c7935d398140d2f | 8574bd615e01fe49 |
| PREREG §3 (UMASK_SCOPE=m1) + REF | M1_UFROZEN_prod_s2027_ccal | U-FROZEN · prod · s2027 · live fee-only cost · UMASK_SCOPE=m1 | 10008 | 2022-01-31 00:00 → 2026-08-30 20:00 | 9ac04705fff7bbc7 | 068bb6ddacee05ff |
| sensitivity / 附加 | UPIT_prod_s42_ccal | sensitivity: UMASK_SCOPE=trade (all legs ranked on the 829 base), prod, s42, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 70dfe7512520784f | 289aececde7fbc73 |
| sensitivity / 附加 | UPIT_prod_s2027_ccal | sensitivity: UMASK_SCOPE=trade, prod, s2027, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 5ab79a6536dd3797 | 67631181f85d7bfd |
| sensitivity / 附加 | UPIT_prod_s42_cdef | sensitivity: UMASK_SCOPE=trade, prod, s42, device default cost (the one-run scope sensitivity asked for) | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 62ee9fa387e61e9d | 6de111417cd8bb93 |
| sensitivity / 附加 | MEM_UPIT_prod_s42_ccal | 附加 seat block: UMASK_SCOPE=members (pre-M1 live form: rank base = trade set = universe for every leg, seat legs over the universe), prod, s42, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 5b9fca02e1fe24d2 | fa62c4943c31854c |
| sensitivity / 附加 | MEM_UPIT_prod_s2027_ccal | 附加 seat block: UMASK_SCOPE=members, prod, s2027, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 44b862686bd9c1fa | 5cd8daaaf06ff13a |
| sensitivity / 附加 | FIX_UPIT_prod_s42_ccal | 附加 seat block: W3FIX=0.21,0,0.79 (the seat the live book holds today), m1, prod, s42, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 86e896df5460a783 | a4a2da2a304f3612 |
| sensitivity / 附加 | FIX_UPIT_prod_s2027_ccal | 附加 seat block: W3FIX=0.21,0,0.79, m1, prod, s2027, fee-only | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | f5b7c6d1cb8f1424 | 23b9912c76944da6 |
| sensitivity / 附加 | M1_UPIT_prod_s42_cslip | sensitivity: cost-calib fee+slippage-vs-anchor-mid vector, m1, prod, s42 | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 48ddb121c4c6e00c | 7b72c42db7c9997d |

### T2. Universe masks — yearly mean counts on the device's anchor grid (masks/mask_summary.json)

| year | U-PIT allowed | U-PIT tradeable | U-FROZEN allowed | U-FROZEN tradeable | no-mask tradeable (829 base) | allowed in both | both / 449 | tradeable in both |
|---|---|---|---|---|---|---|---|---|
| 2022 | 141.1 | 138.1 | 450.0 | 94.2 | 141.6 | 92.6 | 0.206 | 91.8 |
| 2023 | 178.9 | 176.3 | 450.0 | 124.5 | 187.7 | 119.9 | 0.267 | 118.9 |
| 2024 | 265.8 | 258.0 | 450.0 | 182.4 | 272.3 | 175.6 | 0.391 | 173.7 |
| 2025 | 403.5 | 354.3 | 450.0 | 292.2 | 386.0 | 289.8 | 0.646 | 268.1 |
| 2026 | 449.0 | 295.6 | 450.0 | 278.5 | 324.2 | 376.2 | 0.838 | 264.2 |

tradeable = mask ∧ qv4h ≥ 2.5e5 ∧ finite y4 (device `sel` without the ≥80 gate). Listings by year (first 5m bar): {'2022': 163, '2023': 99, '2024': 131, '2025': 241, '2026': 192}. BTC 30-day realised vol, yearly mean %: {'2022': 65.6, '2023': 43.6, '2024': 52.7, '2025': 45.1, '2026': 44.1}. `regime_hist_pct.json` (dashboard reference) n_elig percentiles p25 / p50 / p75 = 144 / 197 / 350.

U-PIT month rows (first 3 and last 3 of 56): 2022-01: listed 139, eligible 136, top 136, 449th 30d vol 285.8 M USDT; 2022-02: listed 139, eligible 136, top 136, 449th 30d vol 287.8 M USDT; 2022-03: listed 142, eligible 137, top 137, 449th 30d vol 228.3 M USDT; 2026-06: listed 726, eligible 556, top 449, 449th 30d vol 62.7 M USDT; 2026-07: listed 784, eligible 584, top 449, 449th 30d vol 57.1 M USDT; 2026-08: listed 826, eligible 635, top 449, 449th 30d vol 53.2 M USDT

### T3. Headline by window — PREREG arms (m1) and REF — mean net bps per anchor per unit gross [CI95, UTC-day block bootstrap 2000×] (executor caliber; ×2×2190/1e4 = %/yr of NAV at 2×)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 0.636 [-0.23, 1.53] | -0.247 — | 1.508 [0.23, 2.80] | 0.701 [-0.36, 1.75] | 3.209 [1.60, 4.81] | 1.260 [0.60, 1.97] | 1.649 [0.75, 2.61] |
| M1 PIT/prod/42/def | 0.552 [-0.35, 1.51] | -0.504 — | 1.596 [0.33, 2.86] | 0.574 [-0.52, 1.71] | 3.135 [1.65, 4.66] | 1.162 [0.52, 1.86] | 1.543 [0.62, 2.48] |
| M1 PIT/prod/42/cal | 0.557 [-0.34, 1.52] | -0.519 — | 1.621 [0.36, 2.89] | 0.651 [-0.44, 1.78] | 3.189 [1.71, 4.72] | 1.206 [0.57, 1.91] | 1.611 [0.69, 2.55] |
| M1 PIT/prod/2027/def | 0.584 [-0.34, 1.55] | -0.503 — | 1.659 [0.41, 2.93] | 0.703 [-0.38, 1.80] | 3.086 [1.60, 4.62] | 1.212 [0.58, 1.93] | 1.604 [0.70, 2.51] |
| M1 PIT/prod/2027/cal | 0.588 [-0.33, 1.56] | -0.519 — | 1.682 [0.43, 2.95] | 0.767 [-0.31, 1.87] | 3.143 [1.66, 4.68] | 1.252 [0.61, 1.97] | 1.666 [0.76, 2.58] |
| M1 PIT/log/42/def | 0.451 [-0.44, 1.38] | -0.570 — | 1.461 [0.23, 2.78] | 0.552 [-0.52, 1.65] | 3.100 [1.57, 4.65] | 1.107 [0.48, 1.82] | 1.516 [0.62, 2.45] |
| M1 PIT/log/42/cal | 0.458 [-0.43, 1.39] | -0.582 — | 1.487 [0.25, 2.80] | 0.625 [-0.45, 1.72] | 3.152 [1.62, 4.70] | 1.149 [0.52, 1.86] | 1.581 [0.69, 2.51] |
| M1 PIT/log/2027/def | 0.465 [-0.42, 1.38] | -0.564 — | 1.482 [0.26, 2.78] | 0.672 [-0.36, 1.73] | 3.058 [1.54, 4.57] | 1.148 [0.52, 1.86] | 1.575 [0.70, 2.48] |
| M1 PIT/log/2027/cal | 0.471 [-0.42, 1.39] | -0.576 — | 1.506 [0.29, 2.80] | 0.733 [-0.30, 1.79] | 3.113 [1.59, 4.62] | 1.187 [0.56, 1.90] | 1.633 [0.76, 2.54] |
| M1 FRZ/prod/42/cal | 0.780 [-0.19, 1.76] | 0.158 — | 1.395 [-0.01, 2.80] | 1.339 [0.13, 2.52] | 3.635 [1.84, 5.37] | 1.659 [0.93, 2.44] | 2.207 [1.18, 3.27] |
| M1 FRZ/prod/2027/cal | 0.858 [-0.14, 1.85] | 0.185 — | 1.523 [0.17, 2.91] | 1.554 [0.37, 2.75] | 3.617 [1.83, 5.35] | 1.767 [1.03, 2.54] | 2.334 [1.31, 3.39] |

### T3b. PREREG arms (m1) and REF — anchor Sharpe (√2190, leverage-invariant) [CI95]

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 1.41 [-0.54, 3.40] | -0.57 — | 3.20 [0.50, 5.81] | 1.26 [-0.64, 3.17] | 4.84 [2.44, 7.28] | 2.30 [1.09, 3.60] | 2.75 [1.25, 4.32] |
| M1 PIT/prod/42/def | 1.23 [-0.78, 3.30] | -1.15 — | 3.47 [0.75, 6.15] | 1.01 [-0.88, 3.04] | 4.87 [2.56, 7.18] | 2.13 [0.97, 3.42] | 2.57 [1.03, 4.15] |
| M1 PIT/prod/42/cal | 1.24 [-0.76, 3.32] | -1.18 — | 3.53 [0.80, 6.20] | 1.14 [-0.74, 3.17] | 4.96 [2.64, 7.27] | 2.21 [1.06, 3.50] | 2.69 [1.14, 4.26] |
| M1 PIT/prod/2027/def | 1.29 [-0.74, 3.39] | -1.14 — | 3.61 [0.91, 6.24] | 1.23 [-0.64, 3.24] | 4.81 [2.50, 7.16] | 2.21 [1.06, 3.52] | 2.68 [1.17, 4.23] |
| M1 PIT/prod/2027/cal | 1.30 [-0.74, 3.41] | -1.17 — | 3.66 [0.96, 6.30] | 1.34 [-0.53, 3.36] | 4.90 [2.58, 7.25] | 2.29 [1.13, 3.60] | 2.78 [1.26, 4.34] |
| M1 PIT/log/42/def | 1.01 [-0.98, 3.10] | -1.33 — | 3.18 [0.52, 5.86] | 0.99 [-0.92, 2.99] | 4.81 [2.44, 7.16] | 2.04 [0.88, 3.33] | 2.55 [1.04, 4.11] |
| M1 PIT/log/42/cal | 1.03 [-0.97, 3.11] | -1.35 — | 3.24 [0.58, 5.92] | 1.12 [-0.79, 3.12] | 4.89 [2.52, 7.24] | 2.12 [0.96, 3.41] | 2.66 [1.15, 4.23] |
| M1 PIT/log/2027/def | 1.05 [-0.96, 3.16] | -1.33 — | 3.25 [0.59, 5.91] | 1.20 [-0.65, 3.16] | 4.77 [2.41, 7.11] | 2.13 [0.97, 3.43] | 2.65 [1.18, 4.18] |
| M1 PIT/log/2027/cal | 1.07 [-0.95, 3.17] | -1.35 — | 3.30 [0.66, 5.95] | 1.31 [-0.55, 3.27] | 4.85 [2.49, 7.20] | 2.20 [1.04, 3.50] | 2.75 [1.27, 4.27] |
| M1 FRZ/prod/42/cal | 1.45 [-0.35, 3.28] | 0.28 — | 2.77 [-0.01, 5.37] | 2.10 [0.20, 3.99] | 5.10 [2.60, 7.50] | 2.67 [1.48, 3.92] | 3.30 [1.77, 4.90] |
| M1 FRZ/prod/2027/cal | 1.60 [-0.25, 3.43] | 0.32 — | 3.06 [0.36, 5.70] | 2.44 [0.58, 4.32] | 5.09 [2.57, 7.49] | 2.85 [1.66, 4.11] | 3.50 [1.97, 5.09] |

### T4. PREREG arms (m1) and REF — NAV at 2.0×: arithmetic %/yr · CAGR % · max DD % · worst UTC day % · days < −2% / < −5% / < −10% (n of days)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 27.8 · 29.6 · DD 19.6 · wd -4.27 · 7/0/0 of 366 | -10.8 · -11.8 · DD 15.1 · wd -4.27 · 3/0/0 of 182 | 66.1 · 89.5 · DD 9.7 · wd -2.84 · 4/0/0 of 184 | 30.7 · 31.9 · DD 15.9 · wd -4.23 · 21/0/0 of 365 | 140.6 · 290.9 · DD 10.9 · wd -3.82 · 12/0/0 of 222 | 55.2 · 68.7 · DD 19.6 · wd -4.27 · 40/0/0 of 953 | 72.2 · 99.0 · DD 15.9 · wd -4.23 · 33/0/0 of 587 |
| M1 PIT/prod/42/def | 24.2 · 24.9 · DD 22.5 · wd -3.41 · 10/0/0 of 366 | -22.1 · -21.3 · DD 18.7 · wd -3.41 · 6/0/0 of 182 | 69.9 · 97.1 · DD 8.4 · wd -2.47 · 4/0/0 of 184 | 25.1 · 24.6 · DD 21.5 · wd -4.76 · 22/0/0 of 365 | 137.3 · 279.3 · DD 8.4 · wd -3.93 · 7/0/0 of 222 | 50.9 · 61.6 · DD 22.5 · wd -4.76 · 39/0/0 of 953 | 67.6 · 89.9 · DD 21.5 · wd -4.76 · 29/0/0 of 587 |
| M1 PIT/prod/42/cal | 24.4 · 25.2 · DD 22.7 · wd -3.41 · 10/0/0 of 366 | -22.7 · -21.8 · DD 18.9 · wd -3.41 · 6/0/0 of 182 | 71.0 · 99.3 · DD 8.3 · wd -2.46 · 4/0/0 of 184 | 28.5 · 28.9 · DD 21.0 · wd -4.74 · 22/0/0 of 365 | 139.7 · 288.4 · DD 8.4 · wd -3.92 · 7/0/0 of 222 | 52.8 · 64.8 · DD 22.7 · wd -4.74 · 39/0/0 of 953 | 70.5 · 95.6 · DD 21.0 · wd -4.74 · 29/0/0 of 587 |
| M1 PIT/prod/2027/def | 25.6 · 26.6 · DD 23.1 · wd -3.32 · 11/0/0 of 366 | -22.0 · -21.3 · DD 19.5 · wd -3.32 · 8/0/0 of 182 | 72.7 · 102.6 · DD 7.4 · wd -2.54 · 3/0/0 of 184 | 30.8 · 31.8 · DD 18.3 · wd -4.93 · 22/0/0 of 365 | 135.2 · 271.3 · DD 8.1 · wd -4.05 · 8/0/0 of 222 | 53.1 · 65.2 · DD 23.1 · wd -4.93 · 41/0/0 of 953 | 70.3 · 95.0 · DD 18.3 · wd -4.93 · 30/0/0 of 587 |
| M1 PIT/prod/2027/cal | 25.7 · 26.8 · DD 23.1 · wd -3.32 · 11/0/0 of 366 | -22.7 · -21.8 · DD 19.7 · wd -3.32 · 8/0/0 of 182 | 73.7 · 104.7 · DD 7.2 · wd -2.53 · 3/0/0 of 184 | 33.6 · 35.6 · DD 17.8 · wd -4.92 · 22/0/0 of 365 | 137.7 · 280.7 · DD 8.1 · wd -4.04 · 8/0/0 of 222 | 54.8 · 68.1 · DD 23.1 · wd -4.92 · 41/0/0 of 953 | 73.0 · 100.4 · DD 17.8 · wd -4.92 · 30/0/0 of 587 |
| M1 PIT/log/42/def | 19.7 · 19.5 · DD 24.1 · wd -3.73 · 10/0/0 of 366 | -25.0 · -23.5 · DD 18.8 · wd -3.73 · 5/0/0 of 182 | 64.0 · 85.8 · DD 9.4 · wd -2.72 · 5/0/0 of 184 | 24.2 · 23.6 · DD 22.3 · wd -4.68 · 22/0/0 of 365 | 135.8 · 273.5 · DD 8.5 · wd -3.61 · 12/0/0 of 222 | 48.5 · 57.9 · DD 24.1 · wd -4.68 · 44/0/0 of 953 | 66.4 · 87.8 · DD 22.3 · wd -4.68 · 34/0/0 of 587 |
| M1 PIT/log/42/cal | 20.1 · 19.9 · DD 24.2 · wd -3.73 · 10/0/0 of 366 | -25.5 · -23.9 · DD 19.0 · wd -3.73 · 5/0/0 of 182 | 65.1 · 87.9 · DD 9.3 · wd -2.71 · 5/0/0 of 184 | 27.4 · 27.6 · DD 21.8 · wd -4.67 · 22/0/0 of 365 | 138.1 · 282.0 · DD 8.4 · wd -3.61 · 12/0/0 of 222 | 50.3 · 60.8 · DD 24.2 · wd -4.67 · 44/0/0 of 953 | 69.2 · 93.2 · DD 21.8 · wd -4.67 · 34/0/0 of 587 |
| M1 PIT/log/2027/def | 20.4 · 20.3 · DD 24.2 · wd -3.70 · 10/0/0 of 366 | -24.7 · -23.2 · DD 19.6 · wd -3.70 · 6/0/0 of 182 | 64.9 · 87.6 · DD 8.9 · wd -2.63 · 4/0/0 of 184 | 29.4 · 30.2 · DD 19.1 · wd -4.85 · 19/0/0 of 365 | 134.0 · 266.8 · DD 8.6 · wd -3.68 · 11/0/0 of 222 | 50.3 · 60.8 · DD 24.2 · wd -4.85 · 40/0/0 of 953 | 69.0 · 92.7 · DD 19.1 · wd -4.85 · 30/0/0 of 587 |
| M1 PIT/log/2027/cal | 20.6 · 20.6 · DD 24.2 · wd -3.70 · 10/0/0 of 366 | -25.2 · -23.6 · DD 19.7 · wd -3.70 · 6/0/0 of 182 | 66.0 · 89.6 · DD 8.8 · wd -2.62 · 4/0/0 of 184 | 32.1 · 33.7 · DD 18.6 · wd -4.84 · 19/0/0 of 365 | 136.3 · 275.7 · DD 8.6 · wd -3.67 · 11/0/0 of 222 | 52.0 · 63.5 · DD 24.2 · wd -4.84 · 40/0/0 of 953 | 71.5 · 97.6 · DD 18.6 · wd -4.84 · 30/0/0 of 587 |
| M1 FRZ/prod/42/cal | 34.2 · 36.8 · DD 17.1 · wd -5.18 · 14/1/0 of 366 | 6.9 · 3.8 · DD 12.2 · wd -5.18 · 7/1/0 of 182 | 61.1 · 79.8 · DD 9.8 · wd -2.67 · 7/0/0 of 184 | 58.7 · 72.9 · DD 17.2 · wd -4.79 · 25/0/0 of 365 | 159.2 · 367.7 · DD 9.8 · wd -4.57 · 15/0/0 of 222 | 72.7 · 99.3 · DD 17.2 · wd -5.18 · 54/1/0 of 953 | 96.7 · 151.9 · DD 17.2 · wd -4.79 · 40/0/0 of 587 |
| M1 FRZ/prod/2027/cal | 37.6 · 41.6 · DD 16.8 · wd -5.18 · 13/1/0 of 366 | 8.1 · 5.1 · DD 12.2 · wd -5.18 · 7/1/0 of 182 | 66.7 · 90.3 · DD 9.4 · wd -2.52 · 6/0/0 of 184 | 68.1 · 89.9 · DD 15.3 · wd -5.01 · 24/1/0 of 365 | 158.4 · 364.3 · DD 9.9 · wd -4.56 · 14/0/0 of 222 | 77.4 · 109.0 · DD 16.8 · wd -5.18 · 51/2/0 of 953 | 102.2 · 166.3 · DD 16.4 · wd -5.01 · 38/1/0 of 587 |

### T3s. Sensitivity and 附加 arms — mean net bps per anchor per unit gross [CI95, UTC-day block bootstrap 2000×] (executor caliber; ×2×2190/1e4 = %/yr of NAV at 2×)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| trade PIT/prod/42/cal | 0.691 [-0.18, 1.61] | -0.302 — | 1.673 [0.40, 3.02] | 0.383 [-0.65, 1.46] | 3.275 [1.77, 4.82] | 1.175 [0.54, 1.87] | 1.477 [0.58, 2.39] |
| trade PIT/prod/2027/cal | 0.754 [-0.11, 1.67] | -0.243 — | 1.740 [0.47, 3.08] | 0.448 [-0.58, 1.49] | 3.191 [1.69, 4.74] | 1.204 [0.57, 1.90] | 1.485 [0.61, 2.37] |
| trade PIT/prod/42/def | 0.680 [-0.19, 1.60] | -0.298 — | 1.647 [0.37, 3.00] | 0.315 [-0.72, 1.39] | 3.222 [1.71, 4.77] | 1.132 [0.49, 1.82] | 1.414 [0.52, 2.33] |
| members PIT/prod/42/cal | 0.552 [-0.35, 1.53] | -0.559 — | 1.651 [0.38, 2.95] | 0.670 [-0.41, 1.79] | 3.058 [1.58, 4.57] | 1.181 [0.55, 1.89] | 1.573 [0.66, 2.52] |
| members PIT/prod/2027/cal | 0.571 [-0.35, 1.53] | -0.575 — | 1.706 [0.44, 2.98] | 0.786 [-0.27, 1.88] | 3.011 [1.54, 4.49] | 1.222 [0.60, 1.93] | 1.627 [0.72, 2.53] |
| fixed-seat PIT/prod/42/cal | -0.772 [-1.62, 0.02] | 0.218 — | -1.751 [-2.87, -0.61] | -0.109 [-1.14, 0.94] | 3.611 [1.93, 5.32] | 0.503 [-0.16, 1.18] | 1.298 [0.41, 2.26] |
| fixed-seat PIT/prod/2027/cal | -0.792 [-1.64, -0.00] | 0.224 — | -1.797 [-2.92, -0.65] | -0.064 [-1.11, 0.98] | 3.621 [1.94, 5.34] | 0.515 [-0.15, 1.18] | 1.329 [0.43, 2.30] |
| M1 PIT/prod/42/fee+slip | 0.785 [-0.11, 1.75] | -0.351 — | 1.910 [0.65, 3.18] | 0.890 [-0.20, 2.01] | 3.284 [1.80, 4.81] | 1.407 [0.77, 2.11] | 1.796 [0.87, 2.73] |

### T3bs. Sensitivity and 附加 arms — anchor Sharpe (√2190, leverage-invariant) [CI95]

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| trade PIT/prod/42/cal | 1.55 [-0.42, 3.58] | -0.74 — | 3.52 [0.84, 6.20] | 0.69 [-1.15, 2.70] | 5.06 [2.73, 7.39] | 2.18 [1.00, 3.45] | 2.50 [0.98, 4.02] |
| trade PIT/prod/2027/cal | 1.70 [-0.26, 3.74] | -0.59 — | 3.68 [1.02, 6.32] | 0.81 [-1.00, 2.77] | 4.95 [2.64, 7.31] | 2.23 [1.06, 3.52] | 2.51 [1.03, 3.98] |
| trade PIT/prod/42/def | 1.53 [-0.44, 3.56] | -0.73 — | 3.46 [0.78, 6.16] | 0.57 [-1.28, 2.58] | 4.98 [2.64, 7.31] | 2.10 [0.92, 3.37] | 2.39 [0.88, 3.92] |
| members PIT/prod/42/cal | 1.21 [-0.78, 3.31] | -1.25 — | 3.58 [0.84, 6.29] | 1.19 [-0.69, 3.18] | 4.90 [2.51, 7.30] | 2.18 [1.01, 3.48] | 2.68 [1.11, 4.30] |
| members PIT/prod/2027/cal | 1.25 [-0.76, 3.34] | -1.28 — | 3.70 [1.00, 6.35] | 1.39 [-0.47, 3.40] | 4.83 [2.48, 7.17] | 2.26 [1.11, 3.57] | 2.77 [1.24, 4.35] |
| fixed-seat PIT/prod/42/cal | -1.84 [-3.87, 0.04] | 0.53 — | -4.11 [-6.83, -1.43] | -0.21 [-2.17, 1.75] | 4.97 [2.68, 7.35] | 0.92 [-0.30, 2.14] | 2.12 [0.66, 3.67] |
| fixed-seat PIT/prod/2027/cal | -1.89 [-3.91, -0.00] | 0.54 — | -4.22 [-6.95, -1.54] | -0.12 [-2.06, 1.85] | 4.99 [2.70, 7.37] | 0.94 [-0.27, 2.17] | 2.17 [0.69, 3.73] |
| M1 PIT/prod/42/fee+slip | 1.74 [-0.26, 3.84] | -0.80 — | 4.15 [1.44, 6.86] | 1.56 [-0.34, 3.58] | 5.10 [2.78, 7.41] | 2.57 [1.41, 3.87] | 3.00 [1.44, 4.56] |

### T4s. Sensitivity and 附加 arms — NAV at 2.0×: arithmetic %/yr · CAGR % · max DD % · worst UTC day % · days < −2% / < −5% / < −10% (n of days)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| trade PIT/prod/42/cal | 30.3 · 32.8 · DD 22.1 · wd -3.50 · 8/0/0 of 366 | -13.2 · -13.8 · DD 16.3 · wd -3.50 · 2/0/0 of 182 | 73.3 · 103.6 · DD 9.8 · wd -3.01 · 6/0/0 of 184 | 16.8 · 14.8 · DD 20.1 · wd -4.93 · 20/0/0 of 365 | 143.4 · 303.1 · DD 8.4 · wd -3.95 · 7/0/0 of 222 | 51.5 · 62.7 · DD 22.1 · wd -4.93 · 35/0/0 of 953 | 64.7 · 84.6 · DD 20.1 · wd -4.93 · 27/0/0 of 587 |
| trade PIT/prod/2027/cal | 33.0 · 36.6 · DD 20.9 · wd -3.44 · 7/0/0 of 366 | -10.6 · -11.5 · DD 15.8 · wd -3.44 · 2/0/0 of 182 | 76.2 · 109.8 · DD 9.2 · wd -2.69 · 5/0/0 of 184 | 19.6 · 18.1 · DD 17.5 · wd -4.20 · 20/0/0 of 365 | 139.8 · 288.7 · DD 8.1 · wd -4.03 · 8/0/0 of 222 | 52.8 · 64.8 · DD 20.9 · wd -4.20 · 35/0/0 of 953 | 65.1 · 85.3 · DD 17.5 · wd -4.20 · 28/0/0 of 587 |
| trade PIT/prod/42/def | 29.8 · 32.1 · DD 22.1 · wd -3.50 · 8/0/0 of 366 | -13.1 · -13.7 · DD 16.3 · wd -3.50 · 2/0/0 of 182 | 72.1 · 101.3 · DD 9.9 · wd -3.02 · 6/0/0 of 184 | 13.8 · 11.4 · DD 20.6 · wd -4.94 · 20/0/0 of 365 | 141.1 · 293.8 · DD 8.4 · wd -3.95 · 8/0/0 of 222 | 49.6 · 59.6 · DD 22.1 · wd -4.94 · 36/0/0 of 953 | 61.9 · 79.6 · DD 20.6 · wd -4.94 · 28/0/0 of 587 |
| members PIT/prod/42/cal | 24.2 · 24.8 · DD 22.9 · wd -3.34 · 10/0/0 of 366 | -24.5 · -23.2 · DD 19.8 · wd -3.34 · 6/0/0 of 182 | 72.3 · 101.9 · DD 8.3 · wd -2.46 · 4/0/0 of 184 | 29.4 · 30.1 · DD 21.0 · wd -4.74 · 20/0/0 of 365 | 134.0 · 267.6 · DD 8.2 · wd -3.91 · 8/0/0 of 222 | 51.7 · 63.1 · DD 22.9 · wd -4.74 · 38/0/0 of 953 | 68.9 · 92.7 · DD 21.0 · wd -4.74 · 28/0/0 of 587 |
| members PIT/prod/2027/cal | 25.0 · 25.9 · DD 23.8 · wd -3.25 · 12/0/0 of 366 | -25.2 · -23.8 · DD 20.8 · wd -3.25 · 9/0/0 of 182 | 74.7 · 106.8 · DD 6.9 · wd -2.53 · 3/0/0 of 184 | 34.4 · 36.8 · DD 17.8 · wd -4.92 · 20/0/0 of 365 | 131.9 · 260.1 · DD 7.9 · wd -3.95 · 8/0/0 of 222 | 53.5 · 66.0 · DD 23.8 · wd -4.92 · 40/0/0 of 953 | 71.3 · 97.3 · DD 17.8 · wd -4.92 · 28/0/0 of 587 |
| fixed-seat PIT/prod/42/cal | -33.8 · -29.9 · DD 35.9 · wd -3.91 · 13/0/0 of 366 | 9.5 · 8.2 · DD 8.8 · wd -3.52 · 5/0/0 of 182 | -76.7 · -54.4 · DD 33.3 · wd -3.91 · 8/0/0 of 184 | -4.8 · -7.2 · DD 21.3 · wd -4.38 · 18/0/0 of 365 | 158.2 · 362.0 · DD 9.2 · wd -4.35 · 15/0/0 of 222 | 22.0 · 21.1 · DD 49.1 · wd -4.38 · 46/0/0 of 953 | 56.9 · 70.3 · DD 21.3 · wd -4.38 · 33/0/0 of 587 |
| fixed-seat PIT/prod/2027/cal | -34.7 · -30.5 · DD 36.7 · wd -3.91 · 12/0/0 of 366 | 9.8 · 8.5 · DD 8.9 · wd -3.44 · 4/0/0 of 182 | -78.7 · -55.3 · DD 34.0 · wd -3.91 · 8/0/0 of 184 | -2.8 · -5.4 · DD 20.5 · wd -4.54 · 15/0/0 of 365 | 158.6 · 364.1 · DD 9.1 · wd -4.39 · 15/0/0 of 222 | 22.5 · 21.7 · DD 49.2 · wd -4.54 · 42/0/0 of 953 | 58.2 · 72.7 · DD 20.5 · wd -4.54 · 30/0/0 of 587 |
| M1 PIT/prod/42/fee+slip | 34.4 · 38.3 · DD 19.9 · wd -3.40 · 9/0/0 of 366 | -15.4 · -15.8 · DD 16.4 · wd -3.40 · 6/0/0 of 182 | 83.6 · 126.2 · DD 7.5 · wd -2.44 · 3/0/0 of 184 | 39.0 · 43.2 · DD 19.5 · wd -4.71 · 22/0/0 of 365 | 143.8 · 304.8 · DD 8.4 · wd -3.91 · 7/0/0 of 222 | 61.6 · 80.0 · DD 19.9 · wd -4.71 · 38/0/0 of 953 | 78.6 · 112.1 · DD 19.5 · wd -4.71 · 29/0/0 of 587 |

### T5. Leverage table — primary arms (U-PIT, m1, prod caliber, live fee-only cost), L ∈ {2.0, 2.5, 3.0}


**2024->26**

| metric | M1 PIT/prod/42/cal L=2.0 | M1 PIT/prod/42/cal L=2.5 | M1 PIT/prod/42/cal L=3.0 | M1 PIT/prod/2027/cal L=2.0 | M1 PIT/prod/2027/cal L=2.5 | M1 PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 52.82 | 66.02 | 79.22 | 54.83 | 68.54 | 82.24 |
| CAGR % | 64.77 | 85.01 | 106.99 | 68.11 | 89.71 | 113.30 |
| total % | 268.37 | 398.50 | 568.28 | 288.17 | 432.18 | 622.76 |
| vol %/yr | 23.95 | 29.94 | 35.93 | 23.98 | 29.97 | 35.97 |
| Sharpe daily | 2.21 | 2.21 | 2.21 | 2.30 | 2.30 | 2.30 |
| Sortino daily | 3.46 | 3.47 | 3.47 | 3.60 | 3.60 | 3.60 |
| maxDD % | 22.67 | 27.69 | 32.45 | 23.14 | 28.24 | 33.09 |
| maxDD span d | 297.67 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| recovered | True | True | True | True | True | True |
| longest DD d | 297.67 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| worst day % | -4.74 | -5.90 | -7.05 | -4.92 | -6.14 | -7.34 |
| worst week % | -11.41 | -14.14 | -16.81 | -11.01 | -13.65 | -16.25 |
| worst month % | -17.03 | -20.93 | -24.70 | -14.66 | -18.11 | -21.47 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 9 | 9 | 9 | 9 | 9 | 9 |
| n months | 32 | 32 | 32 | 32 | 32 | 32 |
| days<−2% | 39 | 75 | 97 | 41 | 73 | 93 |
| share<−2% | 0.04 | 0.08 | 0.10 | 0.04 | 0.08 | 0.10 |
| days<−5% | 0 | 2 | 7 | 0 | 5 | 8 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.54 | 0.54 | 0.54 | 0.55 | 0.55 | 0.55 |
| anchor p1 % | -1.33 | -1.67 | -2.00 | -1.35 | -1.68 | -2.02 |
| anchor p5 % | -0.76 | -0.95 | -1.14 | -0.76 | -0.95 | -1.14 |
| anchor min % | -4.32 | -5.40 | -6.48 | -4.57 | -5.71 | -6.86 |
| 8-anchor p5 % | -2.06 | -2.58 | -3.10 | -2.05 | -2.56 | -3.08 |
| 8-anchor min % | -7.30 | -9.15 | -11.02 | -8.09 | -10.16 | -12.24 |
| VaR99 day % | -2.95 | -3.68 | -4.41 | -2.91 | -3.62 | -4.34 |
| CVaR99 day % | -3.66 | -4.57 | -5.47 | -3.86 | -4.82 | -5.77 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.29 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -1.98 / 1.51 / 6.40 (n 874) | -1.97 / 1.51 / 6.40 (n 874) | -1.97 / 1.51 / 6.39 (n 874) | -2.08 / 1.71 / 6.40 (n 874) | -2.08 / 1.71 / 6.39 (n 874) | -2.07 / 1.71 / 6.39 (n 874) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0795 of gross = 0.1590 of NAV | 0.0795 of gross = 0.1988 of NAV | 0.0795 of gross = 0.2385 of NAV | 0.0748 of gross = 0.1496 of NAV | 0.0748 of gross = 0.1870 of NAV | 0.0748 of gross = 0.2244 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 1.112 bps → 48.7 %/yr (replay 1.206 → 52.8) | 1.112 bps → 60.9 %/yr (replay 1.206 → 66.0) | 1.112 bps → 73.0 %/yr (replay 1.206 → 79.2) | 1.154 bps → 50.6 %/yr (replay 1.252 → 54.8) | 1.154 bps → 63.2 %/yr (replay 1.252 → 68.5) | 1.154 bps → 75.8 %/yr (replay 1.252 → 82.2) |

**2025->26**

| metric | M1 PIT/prod/42/cal L=2.0 | M1 PIT/prod/42/cal L=2.5 | M1 PIT/prod/42/cal L=3.0 | M1 PIT/prod/2027/cal L=2.0 | M1 PIT/prod/2027/cal L=2.5 | M1 PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 70.55 | 88.18 | 105.82 | 72.97 | 91.21 | 109.45 |
| CAGR % | 95.60 | 128.83 | 166.55 | 100.38 | 135.84 | 176.37 |
| total % | 194.16 | 278.59 | 383.88 | 205.82 | 297.43 | 412.89 |
| vol %/yr | 26.24 | 32.80 | 39.36 | 26.25 | 32.82 | 39.38 |
| Sharpe daily | 2.75 | 2.75 | 2.74 | 2.86 | 2.86 | 2.86 |
| Sortino daily | 4.31 | 4.31 | 4.31 | 4.46 | 4.46 | 4.46 |
| maxDD % | 20.97 | 25.69 | 30.20 | 17.81 | 21.95 | 25.97 |
| maxDD span d | 164.33 | 164.33 | 164.33 | 101.00 | 101.33 | 101.83 |
| recovered | True | True | True | True | True | True |
| longest DD d | 164.33 | 164.33 | 164.33 | 104.67 | 104.67 | 109.50 |
| worst day % | -4.74 | -5.90 | -7.05 | -4.92 | -6.14 | -7.34 |
| worst week % | -11.41 | -14.14 | -16.81 | -11.01 | -13.65 | -16.25 |
| worst month % | -17.03 | -20.93 | -24.70 | -14.66 | -18.11 | -21.47 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 4 | 4 | 4 | 3 | 3 | 3 |
| n months | 20 | 20 | 20 | 20 | 20 | 20 |
| days<−2% | 29 | 52 | 63 | 30 | 49 | 62 |
| share<−2% | 0.05 | 0.09 | 0.11 | 0.05 | 0.08 | 0.11 |
| days<−5% | 0 | 2 | 6 | 0 | 5 | 8 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.57 | 0.57 | 0.57 | 0.58 | 0.58 | 0.58 |
| anchor p1 % | -1.46 | -1.82 | -2.18 | -1.44 | -1.79 | -2.15 |
| anchor p5 % | -0.84 | -1.05 | -1.26 | -0.83 | -1.04 | -1.25 |
| anchor min % | -4.32 | -5.40 | -6.48 | -4.57 | -5.71 | -6.86 |
| 8-anchor p5 % | -2.22 | -2.79 | -3.35 | -2.26 | -2.83 | -3.40 |
| 8-anchor min % | -7.30 | -9.15 | -11.02 | -8.09 | -10.16 | -12.24 |
| VaR99 day % | -3.28 | -4.10 | -4.92 | -3.77 | -4.70 | -5.62 |
| CVaR99 day % | -4.00 | -4.99 | -5.97 | -4.20 | -5.24 | -6.28 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.29 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -0.69 / 1.34 / 6.70 (n 508) | -0.69 / 1.34 / 6.69 (n 508) | -0.69 / 1.33 / 6.69 (n 508) | -0.49 / 1.59 / 6.44 (n 508) | -0.49 / 1.59 / 6.44 (n 508) | -0.49 / 1.59 / 6.44 (n 508) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0717 of gross = 0.1434 of NAV | 0.0717 of gross = 0.1792 of NAV | 0.0717 of gross = 0.2151 of NAV | 0.0653 of gross = 0.1306 of NAV | 0.0653 of gross = 0.1633 of NAV | 0.0653 of gross = 0.1959 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 1.514 bps → 66.3 %/yr (replay 1.611 → 70.5) | 1.514 bps → 82.9 %/yr (replay 1.611 → 88.2) | 1.514 bps → 99.5 %/yr (replay 1.611 → 105.8) | 1.564 bps → 68.5 %/yr (replay 1.666 → 73.0) | 1.564 bps → 85.6 %/yr (replay 1.666 → 91.2) | 1.564 bps → 102.7 %/yr (replay 1.666 → 109.4) |

**2026->cut**

| metric | M1 PIT/prod/42/cal L=2.0 | M1 PIT/prod/42/cal L=2.5 | M1 PIT/prod/42/cal L=3.0 | M1 PIT/prod/2027/cal L=2.0 | M1 PIT/prod/2027/cal L=2.5 | M1 PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 139.68 | 174.60 | 209.52 | 137.66 | 172.08 | 206.49 |
| CAGR % | 288.36 | 438.42 | 642.76 | 280.70 | 425.21 | 621.00 |
| total % | 128.24 | 178.41 | 238.58 | 125.49 | 174.23 | 232.52 |
| vol %/yr | 28.17 | 35.22 | 42.26 | 28.09 | 35.12 | 42.14 |
| Sharpe daily | 5.26 | 5.25 | 5.25 | 5.14 | 5.14 | 5.14 |
| Sortino daily | 9.39 | 9.39 | 9.39 | 8.95 | 8.95 | 8.96 |
| maxDD % | 8.40 | 10.41 | 12.39 | 8.08 | 10.02 | 11.93 |
| maxDD span d | 23.00 | 25.00 | 25.00 | 23.00 | 25.00 | 25.00 |
| recovered | True | True | True | True | True | True |
| longest DD d | 25.83 | 25.83 | 25.83 | 25.83 | 25.83 | 25.83 |
| worst day % | -3.92 | -4.89 | -5.85 | -4.04 | -5.04 | -6.03 |
| worst week % | -7.23 | -8.98 | -10.71 | -6.68 | -8.30 | -9.91 |
| worst month % | 1.41 | 1.69 | 1.95 | 1.76 | 2.13 | 2.47 |
| worst month | 202602 | 202602 | 202602 | 202602 | 202602 | 202602 |
| neg months | 0 | 0 | 0 | 0 | 0 | 0 |
| n months | 8 | 8 | 8 | 8 | 8 | 8 |
| days<−2% | 7 | 20 | 23 | 8 | 19 | 25 |
| share<−2% | 0.03 | 0.09 | 0.10 | 0.04 | 0.09 | 0.11 |
| days<−5% | 0 | 0 | 1 | 0 | 1 | 2 |
| share<−5% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.63 | 0.63 | 0.62 | 0.62 | 0.62 | 0.61 |
| anchor p1 % | -1.35 | -1.68 | -2.02 | -1.37 | -1.71 | -2.05 |
| anchor p5 % | -0.93 | -1.16 | -1.39 | -0.94 | -1.18 | -1.42 |
| anchor min % | -2.32 | -2.90 | -3.48 | -2.35 | -2.94 | -3.53 |
| 8-anchor p5 % | -2.10 | -2.64 | -3.18 | -2.19 | -2.75 | -3.30 |
| 8-anchor min % | -5.15 | -6.44 | -7.74 | -5.23 | -6.55 | -7.87 |
| VaR99 day % | -2.70 | -3.37 | -4.03 | -2.86 | -3.56 | -4.26 |
| CVaR99 day % | -3.15 | -3.93 | -4.70 | -3.57 | -4.44 | -5.32 |
| min equity/gross (anchor) | 0.49 | 0.39 | 0.32 | 0.49 | 0.39 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.47 | 0.38 | 0.31 | 0.47 | 0.37 | 0.31 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | 2.29 / 5.75 / 7.21 (n 143) | 2.29 / 5.75 / 7.21 (n 143) | 2.28 / 5.74 / 7.20 (n 143) | 2.49 / 5.50 / 7.01 (n 143) | 2.49 / 5.49 / 7.00 (n 143) | 2.48 / 5.48 / 6.99 (n 143) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0351 of gross = 0.0702 of NAV | 0.0351 of gross = 0.0877 of NAV | 0.0351 of gross = 0.1053 of NAV | 0.0370 of gross = 0.0740 of NAV | 0.0370 of gross = 0.0925 of NAV | 0.0370 of gross = 0.1110 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 3.030 bps → 132.7 %/yr (replay 3.189 → 139.7) | 3.030 bps → 165.9 %/yr (replay 3.189 → 174.6) | 3.030 bps → 199.0 %/yr (replay 3.189 → 209.5) | 2.986 bps → 130.8 %/yr (replay 3.143 → 137.7) | 2.986 bps → 163.5 %/yr (replay 3.143 → 172.1) | 2.986 bps → 196.2 %/yr (replay 3.143 → 206.5) |

**2024**

| metric | M1 PIT/prod/42/cal L=2.0 | M1 PIT/prod/42/cal L=2.5 | M1 PIT/prod/42/cal L=3.0 | M1 PIT/prod/2027/cal L=2.0 | M1 PIT/prod/2027/cal L=2.5 | M1 PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 24.38 | 30.48 | 36.57 | 25.74 | 32.17 | 38.60 |
| CAGR % | 25.15 | 31.57 | 37.99 | 26.85 | 33.80 | 40.79 |
| total % | 25.23 | 31.67 | 38.11 | 26.93 | 33.91 | 40.92 |
| vol %/yr | 19.73 | 24.66 | 29.59 | 19.78 | 24.72 | 29.67 |
| Sharpe daily | 1.18 | 1.19 | 1.19 | 1.25 | 1.25 | 1.25 |
| Sortino daily | 1.84 | 1.85 | 1.85 | 1.95 | 1.95 | 1.96 |
| maxDD % | 22.67 | 27.69 | 32.45 | 23.14 | 28.24 | 33.09 |
| maxDD span d | 297.67 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| recovered | True | True | True | True | True | True |
| longest DD d | 297.67 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| worst day % | -3.41 | -4.26 | -5.11 | -3.32 | -4.16 | -4.99 |
| worst week % | -5.47 | -6.81 | -8.13 | -4.98 | -6.20 | -7.40 |
| worst month % | -6.51 | -8.12 | -9.71 | -6.67 | -8.30 | -9.93 |
| worst month | 202402 | 202402 | 202402 | 202402 | 202402 | 202402 |
| neg months | 5 | 5 | 5 | 6 | 6 | 6 |
| n months | 12 | 12 | 12 | 12 | 12 | 12 |
| days<−2% | 10 | 23 | 34 | 11 | 24 | 31 |
| share<−2% | 0.03 | 0.06 | 0.09 | 0.03 | 0.07 | 0.08 |
| days<−5% | 0 | 0 | 1 | 0 | 0 | 0 |
| share<−5% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.50 | 0.50 | 0.50 | 0.51 | 0.51 | 0.51 |
| anchor p1 % | -1.12 | -1.40 | -1.69 | -1.11 | -1.38 | -1.66 |
| anchor p5 % | -0.61 | -0.76 | -0.92 | -0.60 | -0.75 | -0.90 |
| anchor min % | -3.15 | -3.94 | -4.73 | -3.11 | -3.88 | -4.66 |
| 8-anchor p5 % | -1.89 | -2.37 | -2.84 | -1.84 | -2.30 | -2.77 |
| 8-anchor min % | -3.99 | -5.00 | -6.01 | -3.79 | -4.74 | -5.69 |
| VaR99 day % | -2.38 | -2.97 | -3.56 | -2.45 | -3.06 | -3.66 |
| CVaR99 day % | -2.74 | -3.42 | -4.10 | -2.81 | -3.50 | -4.20 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.32 | 0.48 | 0.38 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -2.29 / -0.11 / 4.78 (n 287) | -2.28 / -0.10 / 4.78 (n 287) | -2.28 / -0.09 / 4.77 (n 287) | -2.37 / -0.20 / 5.60 (n 287) | -2.36 / -0.19 / 5.59 (n 287) | -2.36 / -0.18 / 5.59 (n 287) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0920 of gross = 0.1840 of NAV | 0.0920 of gross = 0.2300 of NAV | 0.0920 of gross = 0.2760 of NAV | 0.0900 of gross = 0.1800 of NAV | 0.0900 of gross = 0.2250 of NAV | 0.0900 of gross = 0.2700 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 0.467 bps → 20.4 %/yr (replay 0.557 → 24.4) | 0.467 bps → 25.6 %/yr (replay 0.557 → 30.5) | 0.467 bps → 30.7 %/yr (replay 0.557 → 36.6) | 0.498 bps → 21.8 %/yr (replay 0.588 → 25.7) | 0.498 bps → 27.2 %/yr (replay 0.588 → 32.2) | 0.498 bps → 32.7 %/yr (replay 0.588 → 38.6) |

**2025**

| metric | M1 PIT/prod/42/cal L=2.0 | M1 PIT/prod/42/cal L=2.5 | M1 PIT/prod/42/cal L=3.0 | M1 PIT/prod/2027/cal L=2.0 | M1 PIT/prod/2027/cal L=2.5 | M1 PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 28.50 | 35.62 | 42.74 | 33.62 | 42.02 | 50.43 |
| CAGR % | 28.88 | 35.98 | 42.91 | 35.63 | 44.92 | 54.24 |
| total % | 28.88 | 35.98 | 42.91 | 35.63 | 44.92 | 54.24 |
| vol %/yr | 24.95 | 31.19 | 37.43 | 25.04 | 31.30 | 37.56 |
| Sharpe daily | 1.14 | 1.14 | 1.14 | 1.37 | 1.37 | 1.37 |
| Sortino daily | 1.66 | 1.66 | 1.66 | 1.98 | 1.98 | 1.98 |
| maxDD % | 20.97 | 25.69 | 30.20 | 17.81 | 21.95 | 25.97 |
| maxDD span d | 164.33 | 164.33 | 164.33 | 101.00 | 101.33 | 101.83 |
| recovered | True | True | True | True | True | True |
| longest DD d | 164.33 | 164.33 | 164.33 | 101.00 | 101.33 | 101.83 |
| worst day % | -4.74 | -5.90 | -7.05 | -4.92 | -6.14 | -7.34 |
| worst week % | -11.41 | -14.14 | -16.81 | -11.01 | -13.65 | -16.25 |
| worst month % | -17.03 | -20.93 | -24.70 | -14.66 | -18.11 | -21.47 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 4 | 4 | 4 | 3 | 3 | 3 |
| n months | 12 | 12 | 12 | 12 | 12 | 12 |
| days<−2% | 22 | 32 | 40 | 22 | 30 | 37 |
| share<−2% | 0.06 | 0.09 | 0.11 | 0.06 | 0.08 | 0.10 |
| days<−5% | 0 | 2 | 5 | 0 | 4 | 6 |
| share<−5% | 0.00 | 0.01 | 0.01 | 0.00 | 0.01 | 0.02 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.53 | 0.53 | 0.53 | 0.56 | 0.56 | 0.56 |
| anchor p1 % | -1.50 | -1.88 | -2.25 | -1.45 | -1.81 | -2.17 |
| anchor p5 % | -0.78 | -0.98 | -1.18 | -0.80 | -1.00 | -1.20 |
| anchor min % | -4.32 | -5.40 | -6.48 | -4.57 | -5.71 | -6.86 |
| 8-anchor p5 % | -2.32 | -2.90 | -3.50 | -2.34 | -2.93 | -3.53 |
| 8-anchor min % | -7.30 | -9.15 | -11.02 | -8.09 | -10.16 | -12.24 |
| VaR99 day % | -3.44 | -4.29 | -5.13 | -3.93 | -4.89 | -5.85 |
| CVaR99 day % | -4.18 | -5.21 | -6.24 | -4.34 | -5.41 | -6.48 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.29 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -0.69 / 0.96 / 3.93 (n 286) | -0.69 / 0.96 / 3.93 (n 286) | -0.69 / 0.96 / 3.93 (n 286) | -0.34 / 1.31 / 4.77 (n 286) | -0.34 / 1.31 / 4.77 (n 286) | -0.34 / 1.31 / 4.76 (n 286) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0940 of gross = 0.1880 of NAV | 0.0940 of gross = 0.2350 of NAV | 0.0940 of gross = 0.2820 of NAV | 0.0826 of gross = 0.1652 of NAV | 0.0826 of gross = 0.2065 of NAV | 0.0826 of gross = 0.2478 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 0.592 bps → 25.9 %/yr (replay 0.651 → 28.5) | 0.592 bps → 32.4 %/yr (replay 0.651 → 35.6) | 0.592 bps → 38.9 %/yr (replay 0.651 → 42.7) | 0.698 bps → 30.6 %/yr (replay 0.767 → 33.6) | 0.698 bps → 38.2 %/yr (replay 0.767 → 42.0) | 0.698 bps → 45.9 %/yr (replay 0.767 → 50.4) |

### T5m. 附加 — UMASK_SCOPE=members arms (pre-M1 live form), L ∈ {2.0, 2.5, 3.0}


**2024->26**

| metric | members PIT/prod/42/cal L=2.0 | members PIT/prod/42/cal L=2.5 | members PIT/prod/42/cal L=3.0 | members PIT/prod/2027/cal L=2.0 | members PIT/prod/2027/cal L=2.5 | members PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 51.73 | 64.66 | 77.59 | 53.52 | 66.90 | 80.28 |
| CAGR % | 63.09 | 82.69 | 103.92 | 66.02 | 86.80 | 109.43 |
| total % | 258.63 | 382.31 | 542.69 | 275.70 | 411.15 | 589.02 |
| vol %/yr | 23.70 | 29.62 | 35.55 | 23.73 | 29.66 | 35.59 |
| Sharpe daily | 2.18 | 2.18 | 2.18 | 2.27 | 2.27 | 2.27 |
| Sortino daily | 3.39 | 3.40 | 3.40 | 3.54 | 3.54 | 3.54 |
| maxDD % | 22.91 | 27.98 | 32.80 | 23.84 | 29.06 | 34.00 |
| maxDD span d | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| recovered | True | True | True | True | True | True |
| longest DD d | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 | 297.83 |
| worst day % | -4.74 | -5.90 | -7.05 | -4.92 | -6.14 | -7.34 |
| worst week % | -11.41 | -14.14 | -16.81 | -11.01 | -13.65 | -16.25 |
| worst month % | -17.03 | -20.93 | -24.70 | -14.66 | -18.11 | -21.47 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 9 | 9 | 9 | 9 | 9 | 9 |
| n months | 32 | 32 | 32 | 32 | 32 | 32 |
| days<−2% | 38 | 74 | 99 | 40 | 69 | 94 |
| share<−2% | 0.04 | 0.08 | 0.10 | 0.04 | 0.07 | 0.10 |
| days<−5% | 0 | 2 | 7 | 0 | 4 | 7 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.54 | 0.54 | 0.54 | 0.55 | 0.55 | 0.55 |
| anchor p1 % | -1.32 | -1.65 | -1.98 | -1.32 | -1.65 | -1.98 |
| anchor p5 % | -0.75 | -0.93 | -1.12 | -0.75 | -0.94 | -1.12 |
| anchor min % | -4.22 | -5.28 | -6.33 | -4.44 | -5.55 | -6.66 |
| 8-anchor p5 % | -2.06 | -2.58 | -3.11 | -2.05 | -2.56 | -3.08 |
| 8-anchor min % | -7.30 | -9.15 | -11.02 | -8.09 | -10.16 | -12.24 |
| VaR99 day % | -2.96 | -3.70 | -4.43 | -2.85 | -3.56 | -4.27 |
| CVaR99 day % | -3.69 | -4.60 | -5.51 | -3.80 | -4.74 | -5.68 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.29 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -2.03 / 1.47 / 6.26 (n 874) | -2.03 / 1.47 / 6.26 (n 874) | -2.03 / 1.47 / 6.26 (n 874) | -2.15 / 1.72 / 6.33 (n 874) | -2.15 / 1.73 / 6.32 (n 874) | -2.14 / 1.73 / 6.32 (n 874) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0793 of gross = 0.1586 of NAV | 0.0793 of gross = 0.1982 of NAV | 0.0793 of gross = 0.2379 of NAV | 0.0746 of gross = 0.1492 of NAV | 0.0746 of gross = 0.1865 of NAV | 0.0746 of gross = 0.2238 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 1.088 bps → 47.6 %/yr (replay 1.181 → 51.7) | 1.088 bps → 59.6 %/yr (replay 1.181 → 64.7) | 1.088 bps → 71.5 %/yr (replay 1.181 → 77.6) | 1.125 bps → 49.3 %/yr (replay 1.222 → 53.5) | 1.125 bps → 61.6 %/yr (replay 1.222 → 66.9) | 1.125 bps → 73.9 %/yr (replay 1.222 → 80.3) |

**2025->26**

| metric | members PIT/prod/42/cal L=2.0 | members PIT/prod/42/cal L=2.5 | members PIT/prod/42/cal L=3.0 | members PIT/prod/2027/cal L=2.0 | members PIT/prod/2027/cal L=2.5 | members PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 68.92 | 86.15 | 103.38 | 71.29 | 89.11 | 106.93 |
| CAGR % | 92.68 | 124.66 | 160.86 | 97.28 | 131.38 | 170.24 |
| total % | 187.14 | 267.57 | 367.39 | 198.25 | 285.41 | 394.70 |
| vol %/yr | 25.75 | 32.19 | 38.63 | 25.78 | 32.23 | 38.67 |
| Sharpe daily | 2.71 | 2.71 | 2.71 | 2.84 | 2.83 | 2.83 |
| Sortino daily | 4.23 | 4.23 | 4.23 | 4.41 | 4.41 | 4.41 |
| maxDD % | 20.97 | 25.69 | 30.20 | 17.81 | 21.95 | 25.97 |
| maxDD span d | 164.33 | 164.33 | 164.33 | 99.50 | 99.50 | 101.00 |
| recovered | True | True | True | True | True | True |
| longest DD d | 164.33 | 164.33 | 164.33 | 129.67 | 135.67 | 135.83 |
| worst day % | -4.74 | -5.90 | -7.05 | -4.92 | -6.14 | -7.34 |
| worst week % | -11.41 | -14.14 | -16.81 | -11.01 | -13.65 | -16.25 |
| worst month % | -17.03 | -20.93 | -24.70 | -14.66 | -18.11 | -21.47 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 4 | 4 | 4 | 3 | 3 | 3 |
| n months | 20 | 20 | 20 | 20 | 20 | 20 |
| days<−2% | 28 | 50 | 64 | 28 | 46 | 62 |
| share<−2% | 0.05 | 0.09 | 0.11 | 0.05 | 0.08 | 0.11 |
| days<−5% | 0 | 2 | 6 | 0 | 4 | 7 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.57 | 0.57 | 0.57 | 0.58 | 0.58 | 0.58 |
| anchor p1 % | -1.43 | -1.79 | -2.15 | -1.41 | -1.76 | -2.12 |
| anchor p5 % | -0.82 | -1.02 | -1.22 | -0.83 | -1.04 | -1.25 |
| anchor min % | -4.22 | -5.28 | -6.33 | -4.44 | -5.55 | -6.66 |
| 8-anchor p5 % | -2.21 | -2.76 | -3.32 | -2.25 | -2.81 | -3.37 |
| 8-anchor min % | -7.30 | -9.15 | -11.02 | -8.09 | -10.16 | -12.24 |
| VaR99 day % | -3.29 | -4.11 | -4.92 | -3.70 | -4.61 | -5.51 |
| CVaR99 day % | -4.04 | -5.04 | -6.03 | -4.18 | -5.22 | -6.25 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.29 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -0.65 / 1.31 / 6.47 (n 508) | -0.66 / 1.31 / 6.47 (n 508) | -0.66 / 1.31 / 6.47 (n 508) | -0.57 / 1.61 / 6.36 (n 508) | -0.57 / 1.61 / 6.35 (n 508) | -0.58 / 1.61 / 6.35 (n 508) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0709 of gross = 0.1418 of NAV | 0.0709 of gross = 0.1773 of NAV | 0.0709 of gross = 0.2127 of NAV | 0.0646 of gross = 0.1292 of NAV | 0.0646 of gross = 0.1615 of NAV | 0.0646 of gross = 0.1938 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 1.478 bps → 64.7 %/yr (replay 1.573 → 68.9) | 1.478 bps → 80.9 %/yr (replay 1.573 → 86.1) | 1.478 bps → 97.1 %/yr (replay 1.573 → 103.4) | 1.527 bps → 66.9 %/yr (replay 1.627 → 71.3) | 1.527 bps → 83.6 %/yr (replay 1.627 → 89.1) | 1.527 bps → 100.3 %/yr (replay 1.627 → 106.9) |

**2026->cut**

| metric | members PIT/prod/42/cal L=2.0 | members PIT/prod/42/cal L=2.5 | members PIT/prod/42/cal L=3.0 | members PIT/prod/2027/cal L=2.0 | members PIT/prod/2027/cal L=2.5 | members PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 133.95 | 167.44 | 200.93 | 131.87 | 164.84 | 197.81 |
| CAGR % | 267.61 | 403.07 | 585.22 | 260.07 | 390.23 | 564.31 |
| total % | 120.74 | 167.14 | 222.38 | 117.98 | 162.97 | 216.36 |
| vol %/yr | 27.34 | 34.18 | 41.01 | 27.31 | 34.14 | 40.96 |
| Sharpe daily | 5.09 | 5.09 | 5.09 | 5.02 | 5.02 | 5.02 |
| Sortino daily | 8.80 | 8.81 | 8.81 | 8.64 | 8.64 | 8.65 |
| maxDD % | 8.15 | 10.10 | 12.02 | 7.89 | 9.79 | 11.65 |
| maxDD span d | 23.00 | 25.00 | 25.00 | 25.00 | 25.17 | 25.17 |
| recovered | True | True | True | True | True | True |
| longest DD d | 26.00 | 26.00 | 26.00 | 26.00 | 26.00 | 26.00 |
| worst day % | -3.91 | -4.87 | -5.83 | -3.95 | -4.92 | -5.88 |
| worst week % | -6.87 | -8.54 | -10.19 | -6.48 | -8.06 | -9.62 |
| worst month % | 0.29 | 0.30 | 0.28 | 0.96 | 1.13 | 1.28 |
| worst month | 202602 | 202602 | 202602 | 202602 | 202602 | 202602 |
| neg months | 0 | 0 | 0 | 0 | 0 | 0 |
| n months | 8 | 8 | 8 | 8 | 8 | 8 |
| days<−2% | 8 | 19 | 24 | 8 | 17 | 24 |
| share<−2% | 0.04 | 0.09 | 0.11 | 0.04 | 0.08 | 0.11 |
| days<−5% | 0 | 0 | 2 | 0 | 0 | 2 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.62 | 0.62 | 0.62 | 0.60 | 0.60 | 0.60 |
| anchor p1 % | -1.32 | -1.65 | -1.98 | -1.34 | -1.67 | -2.00 |
| anchor p5 % | -0.91 | -1.14 | -1.36 | -0.91 | -1.14 | -1.37 |
| anchor min % | -2.30 | -2.88 | -3.46 | -2.33 | -2.91 | -3.49 |
| 8-anchor p5 % | -2.16 | -2.71 | -3.25 | -2.21 | -2.76 | -3.32 |
| 8-anchor min % | -4.96 | -6.21 | -7.46 | -5.02 | -6.28 | -7.54 |
| VaR99 day % | -2.70 | -3.37 | -4.04 | -2.74 | -3.42 | -4.10 |
| CVaR99 day % | -3.50 | -4.37 | -5.22 | -3.54 | -4.42 | -5.29 |
| min equity/gross (anchor) | 0.49 | 0.39 | 0.32 | 0.49 | 0.39 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | 2.11 / 5.47 / 7.00 (n 143) | 2.10 / 5.47 / 7.00 (n 143) | 2.10 / 5.47 / 7.00 (n 143) | 2.17 / 5.41 / 6.88 (n 143) | 2.16 / 5.40 / 6.88 (n 143) | 2.16 / 5.40 / 6.88 (n 143) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0338 of gross = 0.0676 of NAV | 0.0338 of gross = 0.0845 of NAV | 0.0338 of gross = 0.1014 of NAV | 0.0356 of gross = 0.0712 of NAV | 0.0356 of gross = 0.0890 of NAV | 0.0356 of gross = 0.1068 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 2.905 bps → 127.3 %/yr (replay 3.058 → 134.0) | 2.905 bps → 159.1 %/yr (replay 3.058 → 167.4) | 2.905 bps → 190.9 %/yr (replay 3.058 → 200.9) | 2.860 bps → 125.3 %/yr (replay 3.011 → 131.9) | 2.860 bps → 156.6 %/yr (replay 3.011 → 164.8) | 2.860 bps → 187.9 %/yr (replay 3.011 → 197.8) |

### T5f. 附加 — fixed live seat W3FIX=0.21,0,0.79 arms (state-faithful), L ∈ {2.0, 2.5, 3.0}


**2024->26**

| metric | fixed-seat PIT/prod/42/cal L=2.0 | fixed-seat PIT/prod/42/cal L=2.5 | fixed-seat PIT/prod/42/cal L=3.0 | fixed-seat PIT/prod/2027/cal L=2.0 | fixed-seat PIT/prod/2027/cal L=2.5 | fixed-seat PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 22.03 | 27.54 | 33.05 | 22.54 | 28.18 | 33.81 |
| CAGR % | 21.13 | 25.94 | 30.48 | 21.73 | 26.73 | 31.45 |
| total % | 64.95 | 82.61 | 100.29 | 67.11 | 85.60 | 104.20 |
| vol %/yr | 23.94 | 29.93 | 35.91 | 23.98 | 29.97 | 35.97 |
| Sharpe daily | 0.92 | 0.92 | 0.92 | 0.94 | 0.94 | 0.94 |
| Sortino daily | 1.40 | 1.40 | 1.40 | 1.42 | 1.42 | 1.43 |
| maxDD % | 49.10 | 57.31 | 64.30 | 49.18 | 57.34 | 64.27 |
| maxDD span d | 763.33 | 790.50 | 792.50 | 763.17 | 764.83 | 792.50 |
| recovered | True | True | True | True | True | True |
| longest DD d | 763.33 | 790.50 | 792.50 | 763.17 | 764.83 | 792.50 |
| worst day % | -4.38 | -5.50 | -6.62 | -4.54 | -5.70 | -6.86 |
| worst week % | -10.09 | -12.48 | -14.81 | -10.06 | -12.44 | -14.76 |
| worst month % | -15.12 | -18.61 | -21.98 | -14.92 | -18.35 | -21.68 |
| worst month | 202411 | 202411 | 202411 | 202412 | 202412 | 202412 |
| neg months | 14 | 15 | 15 | 14 | 14 | 14 |
| n months | 32 | 32 | 32 | 32 | 32 | 32 |
| days<−2% | 46 | 69 | 96 | 42 | 69 | 100 |
| share<−2% | 0.05 | 0.07 | 0.10 | 0.04 | 0.07 | 0.10 |
| days<−5% | 0 | 3 | 8 | 0 | 3 | 9 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.49 | 0.49 | 0.49 | 0.49 | 0.49 | 0.49 |
| anchor p1 % | -1.33 | -1.66 | -1.99 | -1.35 | -1.69 | -2.02 |
| anchor p5 % | -0.76 | -0.95 | -1.14 | -0.76 | -0.96 | -1.15 |
| anchor min % | -5.51 | -6.89 | -8.27 | -5.64 | -7.05 | -8.46 |
| 8-anchor p5 % | -2.22 | -2.78 | -3.34 | -2.22 | -2.78 | -3.34 |
| 8-anchor min % | -6.37 | -7.97 | -9.58 | -6.38 | -7.99 | -9.60 |
| VaR99 day % | -3.09 | -3.85 | -4.61 | -3.08 | -3.84 | -4.60 |
| CVaR99 day % | -3.77 | -4.70 | -5.63 | -3.82 | -4.76 | -5.70 |
| min equity/gross (anchor) | 0.47 | 0.37 | 0.31 | 0.47 | 0.37 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.47 | 0.37 | 0.30 | 0.47 | 0.37 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -6.44 / -0.06 / 5.94 (n 874) | -6.45 / -0.06 / 5.94 (n 874) | -6.46 / -0.06 / 5.93 (n 874) | -6.39 / -0.05 / 5.96 (n 874) | -6.40 / -0.05 / 5.95 (n 874) | -6.42 / -0.05 / 5.95 (n 874) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0189 of gross = 0.0378 of NAV | 0.0189 of gross = 0.0473 of NAV | 0.0189 of gross = 0.0567 of NAV | 0.0189 of gross = 0.0378 of NAV | 0.0189 of gross = 0.0473 of NAV | 0.0189 of gross = 0.0567 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 0.430 bps → 18.8 %/yr (replay 0.503 → 22.0) | 0.430 bps → 23.6 %/yr (replay 0.503 → 27.5) | 0.430 bps → 28.3 %/yr (replay 0.503 → 33.1) | 0.440 bps → 19.3 %/yr (replay 0.515 → 22.5) | 0.440 bps → 24.1 %/yr (replay 0.515 → 28.2) | 0.440 bps → 28.9 %/yr (replay 0.515 → 33.8) |

**2025->26**

| metric | fixed-seat PIT/prod/42/cal L=2.0 | fixed-seat PIT/prod/42/cal L=2.5 | fixed-seat PIT/prod/42/cal L=3.0 | fixed-seat PIT/prod/2027/cal L=2.0 | fixed-seat PIT/prod/2027/cal L=2.5 | fixed-seat PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 56.85 | 71.07 | 85.28 | 58.23 | 72.79 | 87.35 |
| CAGR % | 70.32 | 92.40 | 116.37 | 72.66 | 95.70 | 120.81 |
| total % | 135.48 | 186.47 | 246.00 | 140.69 | 194.40 | 257.49 |
| vol %/yr | 26.82 | 33.52 | 40.23 | 26.87 | 33.59 | 40.31 |
| Sharpe daily | 2.11 | 2.11 | 2.11 | 2.16 | 2.16 | 2.16 |
| Sortino daily | 3.41 | 3.42 | 3.42 | 3.48 | 3.49 | 3.49 |
| maxDD % | 21.33 | 26.16 | 30.78 | 20.54 | 25.13 | 29.51 |
| maxDD span d | 400.17 | 400.17 | 400.33 | 304.50 | 306.67 | 306.67 |
| recovered | True | True | True | True | True | True |
| longest DD d | 400.17 | 400.17 | 400.33 | 304.50 | 306.67 | 306.67 |
| worst day % | -4.38 | -5.50 | -6.62 | -4.54 | -5.70 | -6.86 |
| worst week % | -7.72 | -9.59 | -11.43 | -7.59 | -9.42 | -11.24 |
| worst month % | -11.28 | -13.95 | -16.56 | -11.14 | -13.79 | -16.37 |
| worst month | 202501 | 202501 | 202501 | 202501 | 202501 | 202501 |
| neg months | 7 | 8 | 8 | 7 | 7 | 7 |
| n months | 20 | 20 | 20 | 20 | 20 | 20 |
| days<−2% | 33 | 46 | 65 | 30 | 46 | 67 |
| share<−2% | 0.06 | 0.08 | 0.11 | 0.05 | 0.08 | 0.11 |
| days<−5% | 0 | 3 | 6 | 0 | 3 | 7 |
| share<−5% | 0.00 | 0.01 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.50 | 0.50 | 0.50 | 0.52 | 0.51 | 0.51 |
| anchor p1 % | -1.37 | -1.72 | -2.06 | -1.39 | -1.73 | -2.08 |
| anchor p5 % | -0.86 | -1.07 | -1.29 | -0.85 | -1.06 | -1.27 |
| anchor min % | -5.51 | -6.89 | -8.27 | -5.64 | -7.05 | -8.46 |
| 8-anchor p5 % | -2.37 | -2.96 | -3.56 | -2.37 | -2.97 | -3.57 |
| 8-anchor min % | -6.37 | -7.97 | -9.58 | -6.38 | -7.99 | -9.60 |
| VaR99 day % | -3.36 | -4.19 | -5.02 | -3.47 | -4.32 | -5.17 |
| CVaR99 day % | -3.96 | -4.94 | -5.92 | -4.03 | -5.03 | -6.03 |
| min equity/gross (anchor) | 0.47 | 0.37 | 0.31 | 0.47 | 0.37 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.47 | 0.37 | 0.30 | 0.47 | 0.37 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -2.40 / 1.40 / 6.44 (n 508) | -2.40 / 1.40 / 6.44 (n 508) | -2.40 / 1.41 / 6.44 (n 508) | -2.15 / 1.40 / 6.41 (n 508) | -2.15 / 1.40 / 6.40 (n 508) | -2.15 / 1.40 / 6.40 (n 508) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0194 of gross = 0.0388 of NAV | 0.0194 of gross = 0.0485 of NAV | 0.0194 of gross = 0.0582 of NAV | 0.0194 of gross = 0.0388 of NAV | 0.0194 of gross = 0.0485 of NAV | 0.0194 of gross = 0.0582 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 1.236 bps → 54.1 %/yr (replay 1.298 → 56.9) | 1.236 bps → 67.7 %/yr (replay 1.298 → 71.1) | 1.236 bps → 81.2 %/yr (replay 1.298 → 85.3) | 1.265 bps → 55.4 %/yr (replay 1.329 → 58.2) | 1.265 bps → 69.2 %/yr (replay 1.329 → 72.8) | 1.265 bps → 83.1 %/yr (replay 1.329 → 87.3) |

**2026->cut**

| metric | fixed-seat PIT/prod/42/cal L=2.0 | fixed-seat PIT/prod/42/cal L=2.5 | fixed-seat PIT/prod/42/cal L=3.0 | fixed-seat PIT/prod/2027/cal L=2.0 | fixed-seat PIT/prod/2027/cal L=2.5 | fixed-seat PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 158.16 | 197.70 | 237.24 | 158.58 | 198.23 | 237.87 |
| CAGR % | 362.03 | 566.67 | 855.86 | 364.10 | 570.47 | 862.49 |
| total % | 153.67 | 217.04 | 294.72 | 154.36 | 218.14 | 296.39 |
| vol %/yr | 31.84 | 39.80 | 47.76 | 31.76 | 39.70 | 47.64 |
| Sharpe daily | 5.12 | 5.12 | 5.11 | 5.13 | 5.13 | 5.12 |
| Sortino daily | 9.07 | 9.08 | 9.09 | 9.09 | 9.10 | 9.10 |
| maxDD % | 9.16 | 11.35 | 13.49 | 9.10 | 11.26 | 13.39 |
| maxDD span d | 25.67 | 25.67 | 25.67 | 25.67 | 25.67 | 27.00 |
| recovered | True | True | True | True | True | True |
| longest DD d | 25.67 | 25.67 | 25.67 | 25.67 | 25.67 | 27.00 |
| worst day % | -4.35 | -5.42 | -6.48 | -4.39 | -5.47 | -6.54 |
| worst week % | -7.72 | -9.59 | -11.43 | -7.59 | -9.42 | -11.24 |
| worst month % | 3.15 | 3.91 | 4.66 | 3.38 | 4.19 | 5.00 |
| worst month | 202608 | 202608 | 202608 | 202608 | 202608 | 202608 |
| neg months | 0 | 0 | 0 | 0 | 0 | 0 |
| n months | 8 | 8 | 8 | 8 | 8 | 8 |
| days<−2% | 15 | 19 | 28 | 15 | 19 | 28 |
| share<−2% | 0.07 | 0.09 | 0.13 | 0.07 | 0.09 | 0.13 |
| days<−5% | 0 | 1 | 3 | 0 | 1 | 4 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.02 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.59 | 0.59 | 0.59 | 0.60 | 0.60 | 0.60 |
| anchor p1 % | -1.54 | -1.93 | -2.32 | -1.56 | -1.95 | -2.34 |
| anchor p5 % | -1.05 | -1.31 | -1.57 | -1.05 | -1.31 | -1.57 |
| anchor min % | -2.43 | -3.04 | -3.65 | -2.47 | -3.09 | -3.71 |
| 8-anchor p5 % | -2.44 | -3.07 | -3.70 | -2.50 | -3.13 | -3.77 |
| 8-anchor min % | -6.37 | -7.97 | -9.58 | -6.38 | -7.99 | -9.60 |
| VaR99 day % | -3.52 | -4.39 | -5.25 | -3.50 | -4.36 | -5.22 |
| CVaR99 day % | -3.93 | -4.90 | -5.86 | -3.92 | -4.89 | -5.85 |
| min equity/gross (anchor) | 0.49 | 0.39 | 0.32 | 0.49 | 0.39 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.47 | 0.37 | 0.30 | 0.47 | 0.37 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | 2.79 / 5.42 / 6.86 (n 143) | 2.79 / 5.41 / 6.85 (n 143) | 2.79 / 5.40 / 6.84 (n 143) | 2.70 / 5.42 / 6.85 (n 143) | 2.70 / 5.41 / 6.84 (n 143) | 2.70 / 5.40 / 6.83 (n 143) |
| turnover per anchor, replay (live steady 0.0477 of venue gross, CI [0.041, 0.055]) | 0.0225 of gross = 0.0450 of NAV | 0.0225 of gross = 0.0562 of NAV | 0.0225 of gross = 0.0675 of NAV | 0.0227 of gross = 0.0454 of NAV | 0.0227 of gross = 0.0568 of NAV | 0.0227 of gross = 0.0681 of NAV |
| after expected timing haircut (N → N+25 min; pod_alpha_decay proxy retention 2025 ×0.91, 2026 ×0.95, 2024 −0.09 bps): mean bps/anchor/gross → arith %/yr | 3.430 bps → 150.2 %/yr (replay 3.611 → 158.2) | 3.430 bps → 187.8 %/yr (replay 3.611 → 197.7) | 3.430 bps → 225.4 %/yr (replay 3.611 → 237.2) | 3.440 bps → 150.7 %/yr (replay 3.621 → 158.6) | 3.440 bps → 188.3 %/yr (replay 3.621 → 198.2) | 3.440 bps → 226.0 %/yr (replay 3.621 → 237.9) |

### T6. Calendar quarters — mean net bps per anchor per gross · NAV total return % at 2× (compounded) · max DD % at 2×

| arm | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 | 2026-Q3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 0.41 · 4.1% · DD 9.8 | -0.90 · -9.8% · DD 12.9 | 1.09 · 12.4% · DD 9.7 | 1.92 · 22.8% · DD 7.1 | 2.43 · 29.1% · DD 5.8 | -0.85 · -9.7% · DD 15.9 | 0.34 · 3.4% · DD 10.2 | 0.91 · 9.4% · DD 10.4 | 1.42 · 15.8% · DD 6.0 | 5.38 · 77.6% · DD 7.4 | 2.31 · 11.4% · DD 9.1 |
| M1 PIT/prod/42/def | -0.15 · -2.2% · DD 15.0 | -0.86 · -9.3% · DD 11.3 | 0.77 · 8.5% · DD 7.6 | 2.42 · 29.8% · DD 6.0 | 2.32 · 27.6% · DD 5.2 | -0.56 · -7.0% · DD 21.0 | 0.64 · 7.0% · DD 8.2 | -0.09 · -1.9% · DD 8.7 | 1.04 · 11.3% · DD 4.5 | 5.35 · 76.8% · DD 8.4 | 2.81 · 14.3% · DD 4.9 |
| M1 PIT/prod/42/cal | -0.18 · -2.5% · DD 15.2 | -0.86 · -9.3% · DD 11.3 | 0.82 · 9.1% · DD 7.6 | 2.42 · 29.7% · DD 5.9 | 2.39 · 28.6% · DD 5.2 | -0.44 · -5.8% · DD 20.5 | 0.72 · 7.9% · DD 8.1 | -0.04 · -1.4% · DD 8.6 | 1.11 · 12.1% · DD 4.5 | 5.40 · 77.8% · DD 8.4 | 2.86 · 14.6% · DD 4.9 |
| M1 PIT/prod/2027/def | -0.19 · -2.7% · DD 15.8 | -0.81 · -8.8% · DD 10.9 | 0.67 · 7.3% · DD 7.4 | 2.65 · 33.1% · DD 5.8 | 2.23 · 26.4% · DD 5.9 | -0.12 · -2.5% · DD 17.9 | 0.90 · 10.1% · DD 7.5 | -0.18 · -2.9% · DD 9.0 | 1.12 · 12.2% · DD 4.5 | 5.13 · 72.6% · DD 8.1 | 2.88 · 14.6% · DD 5.1 |
| M1 PIT/prod/2027/cal | -0.22 · -3.0% · DD 15.9 | -0.82 · -8.8% · DD 10.9 | 0.72 · 7.9% · DD 7.2 | 2.64 · 33.0% · DD 5.9 | 2.29 · 27.1% · DD 5.9 | -0.02 · -1.4% · DD 17.6 | 0.96 · 10.9% · DD 7.5 | -0.14 · -2.4% · DD 8.8 | 1.19 · 13.1% · DD 4.5 | 5.18 · 73.6% · DD 8.1 | 2.92 · 14.9% · DD 5.1 |
| M1 PIT/log/42/def | -0.42 · -5.0% · DD 16.9 | -0.72 · -7.9% · DD 9.8 | 0.78 · 8.6% · DD 9.4 | 2.14 · 25.9% · DD 6.1 | 2.04 · 23.8% · DD 5.7 | -0.81 · -9.6% · DD 22.0 | 0.72 · 8.0% · DD 7.4 | 0.28 · 2.3% · DD 8.9 | 1.12 · 12.2% · DD 4.7 | 5.39 · 77.7% · DD 8.1 | 2.36 · 11.8% · DD 6.7 |
| M1 PIT/log/42/cal | -0.44 · -5.2% · DD 17.0 | -0.72 · -7.9% · DD 9.9 | 0.84 · 9.3% · DD 9.3 | 2.14 · 25.8% · DD 6.0 | 2.11 · 24.7% · DD 5.7 | -0.70 · -8.4% · DD 21.5 | 0.79 · 8.7% · DD 7.4 | 0.32 · 2.7% · DD 8.8 | 1.19 · 12.9% · DD 4.7 | 5.43 · 78.6% · DD 8.1 | 2.40 · 12.0% · DD 6.7 |
| M1 PIT/log/2027/def | -0.48 · -5.6% · DD 17.9 | -0.65 · -7.2% · DD 9.4 | 0.64 · 6.9% · DD 8.9 | 2.33 · 28.5% · DD 6.0 | 1.97 · 22.9% · DD 6.5 | -0.40 · -5.4% · DD 18.5 | 0.87 · 9.8% · DD 6.9 | 0.25 · 2.0% · DD 8.7 | 1.07 · 11.6% · DD 4.7 | 5.33 · 76.6% · DD 7.8 | 2.38 · 11.9% · DD 6.8 |
| M1 PIT/log/2027/cal | -0.50 · -5.8% · DD 18.0 | -0.65 · -7.2% · DD 9.4 | 0.69 · 7.5% · DD 8.8 | 2.32 · 28.4% · DD 6.1 | 2.03 · 23.6% · DD 6.4 | -0.30 · -4.3% · DD 18.1 | 0.93 · 10.5% · DD 6.9 | 0.29 · 2.4% · DD 8.6 | 1.14 · 12.4% · DD 4.6 | 5.38 · 77.5% · DD 7.8 | 2.43 · 12.1% · DD 6.8 |
| M1 FRZ/prod/42/cal | 1.10 · 11.5% · DD 10.6 | -0.78 · -8.6% · DD 11.6 | 0.62 · 6.5% · DD 9.5 | 2.17 · 26.2% · DD 7.2 | 3.03 · 37.6% · DD 8.9 | 0.52 · 4.5% · DD 17.2 | 0.79 · 8.6% · DD 8.9 | 1.04 · 10.7% · DD 10.4 | 1.82 · 20.7% · DD 7.7 | 5.72 · 83.9% · DD 9.8 | 2.98 · 15.2% · DD 6.8 |
| M1 FRZ/prod/2027/cal | 1.12 · 11.8% · DD 10.5 | -0.75 · -8.3% · DD 11.6 | 0.47 · 4.8% · DD 9.4 | 2.58 · 32.0% · DD 6.1 | 3.25 · 40.8% · DD 7.7 | 1.03 · 10.5% · DD 15.3 | 0.98 · 10.9% · DD 8.0 | 0.99 · 10.0% · DD 10.9 | 1.71 · 19.3% · DD 8.0 | 5.68 · 83.1% · DD 9.9 | 3.21 · 16.5% · DD 6.4 |
| trade PIT/prod/42/cal | 0.50 · 5.1% · DD 10.8 | -1.10 · -11.7% · DD 13.6 | 0.93 · 10.4% · DD 9.8 | 2.42 · 29.7% · DD 5.8 | 2.44 · 29.3% · DD 5.4 | -1.43 · -15.3% · DD 19.6 | 0.48 · 5.1% · DD 7.6 | 0.07 · -0.3% · DD 8.5 | 1.28 · 14.2% · DD 4.5 | 5.43 · 78.5% · DD 8.4 | 2.86 · 14.5% · DD 5.0 |
| trade PIT/prod/2027/cal | 0.55 · 5.8% · DD 10.7 | -1.04 · -11.1% · DD 13.1 | 0.83 · 9.1% · DD 9.2 | 2.65 · 33.1% · DD 5.8 | 2.33 · 27.7% · DD 5.9 | -0.99 · -11.2% · DD 17.3 | 0.55 · 6.0% · DD 7.5 | -0.07 · -1.8% · DD 9.3 | 1.34 · 15.0% · DD 4.4 | 5.14 · 73.0% · DD 8.1 | 2.91 · 14.8% · DD 5.1 |
| trade PIT/prod/42/def | 0.50 · 5.2% · DD 10.8 | -1.10 · -11.6% · DD 13.5 | 0.87 · 9.7% · DD 9.9 | 2.42 · 29.7% · DD 5.9 | 2.37 · 28.4% · DD 5.5 | -1.53 · -16.2% · DD 20.1 | 0.41 · 4.3% · DD 7.6 | 0.03 · -0.7% · DD 8.7 | 1.22 · 13.4% · DD 4.6 | 5.39 · 77.6% · DD 8.4 | 2.81 · 14.3% · DD 5.1 |
| members PIT/prod/42/cal | -0.17 · -2.4% · DD 15.3 | -0.95 · -10.2% · DD 12.1 | 0.88 · 9.8% · DD 6.9 | 2.43 · 29.8% · DD 5.9 | 2.39 · 28.6% · DD 5.2 | -0.39 · -5.3% · DD 20.5 | 0.73 · 8.0% · DD 7.9 | -0.02 · -1.1% · DD 8.0 | 1.01 · 11.0% · DD 4.7 | 5.11 · 72.5% · DD 8.2 | 2.99 · 15.3% · DD 4.6 |
| members PIT/prod/2027/cal | -0.25 · -3.3% · DD 16.3 | -0.90 · -9.6% · DD 11.7 | 0.77 · 8.5% · DD 6.9 | 2.64 · 33.0% · DD 5.9 | 2.29 · 27.1% · DD 5.9 | 0.05 · -0.7% · DD 17.6 | 0.99 · 11.2% · DD 7.3 | -0.15 · -2.5% · DD 8.5 | 1.02 · 11.1% · DD 4.8 | 4.99 · 70.2% · DD 7.9 | 2.99 · 15.3% · DD 4.7 |
| fixed-seat PIT/prod/42/cal | 0.75 · 8.0% · DD 8.4 | -0.31 · -3.7% · DD 7.6 | -0.84 · -9.0% · DD 12.2 | -2.66 · -26.0% · DD 28.8 | -1.18 · -12.4% · DD 17.2 | -0.81 · -8.9% · DD 12.7 | 1.09 · 12.4% · DD 6.7 | 0.43 · 3.6% · DD 8.5 | 1.54 · 17.1% · DD 6.3 | 5.96 · 88.6% · DD 9.2 | 2.93 · 14.9% · DD 5.4 |
| fixed-seat PIT/prod/2027/cal | 0.78 · 8.3% · DD 8.3 | -0.33 · -3.9% · DD 7.8 | -0.87 · -9.4% · DD 12.5 | -2.72 · -26.5% · DD 28.9 | -1.15 · -12.2% · DD 17.2 | -0.67 · -7.6% · DD 12.2 | 1.14 · 13.0% · DD 6.6 | 0.39 · 3.2% · DD 8.7 | 1.49 · 16.4% · DD 6.2 | 5.95 · 88.3% · DD 9.1 | 3.12 · 16.0% · DD 4.9 |
| M1 PIT/prod/42/fee+slip | 0.04 · -0.2% · DD 13.8 | -0.74 · -8.1% · DD 10.2 | 1.10 · 12.5% · DD 7.3 | 2.72 · 34.1% · DD 5.6 | 2.73 · 33.4% · DD 5.1 | -0.10 · -2.3% · DD 19.2 | 0.92 · 10.3% · DD 8.0 | 0.05 · -0.4% · DD 8.3 | 1.22 · 13.5% · DD 4.5 | 5.47 · 79.3% · DD 8.4 | 2.94 · 15.0% · DD 4.9 |

### T7. Calendar months 2024-01 → 2026-08 (to cut) — NAV % at 2× (compounded) · mean bps/anchor per gross

| month | M1 PIT/prod/42/cal | M1 PIT/prod/2027/cal | M1 FRZ/prod/42/cal | fixed-seat PIT/prod/42/cal | members PIT/prod/42/cal | REF T400/log/42/def |
|---|---|---|---|---|---|---|
| 2024-01 | 3.4% · 0.93 | 5.2% · 1.41 | 1.9% · 0.59 | 3.7% · 1.01 | 3.4% · 0.94 | 0.6% · 0.20 |
| 2024-02 | -6.5% · -1.89 | -6.7% · -1.94 | 0.3% · 0.18 | -4.0% · -1.14 | -6.5% · -1.90 | -3.8% · -1.07 |
| 2024-03 | 0.9% · 0.33 | -1.2% · -0.25 | 9.1% · 2.46 | 8.5% · 2.26 | 0.9% · 0.34 | 7.5% · 2.00 |
| 2024-04 | -5.6% · -1.56 | -5.2% · -1.44 | -11.8% · -3.42 | -7.8% · -2.22 | -5.8% · -1.62 | -8.2% · -2.31 |
| 2024-05 | -0.8% · -0.20 | -0.7% · -0.16 | 6.0% · 1.58 | 6.4% · 1.69 | -1.4% · -0.35 | -0.1% · 0.00 |
| 2024-06 | -3.1% · -0.85 | -3.1% · -0.86 | -2.2% · -0.58 | -1.8% · -0.48 | -3.3% · -0.90 | -1.6% · -0.44 |
| 2024-07 | -4.4% · -1.18 | -3.8% · -1.02 | -6.8% · -1.88 | -8.7% · -2.43 | -3.7% · -0.99 | -4.7% · -1.28 |
| 2024-08 | 12.8% · 3.29 | 10.5% · 2.73 | 13.0% · 3.35 | -0.9% · -0.21 | 12.7% · 3.26 | 14.2% · 3.63 |
| 2024-09 | 1.1% · 0.35 | 1.5% · 0.45 | 1.2% · 0.37 | 0.5% · 0.15 | 1.1% · 0.34 | 3.3% · 0.93 |
| 2024-10 | 4.7% · 1.28 | 6.7% · 1.77 | 2.2% · 0.63 | 2.2% · 0.61 | 4.7% · 1.26 | 3.6% · 0.98 |
| 2024-11 | 15.7% · 4.14 | 17.2% · 4.51 | 11.5% · 3.10 | -15.1% · -4.47 | 15.8% · 4.17 | 13.9% · 3.71 |
| 2024-12 | 7.1% · 1.89 | 6.3% · 1.70 | 10.7% · 2.82 | -14.7% · -4.20 | 7.1% · 1.90 | 4.1% · 1.13 |
| 2025-01 | 13.2% · 3.38 | 12.8% · 3.27 | 14.6% · 3.71 | -11.3% · -3.17 | 13.2% · 3.38 | 13.2% · 3.37 |
| 2025-02 | 1.9% · 0.66 | 2.1% · 0.71 | -1.1% · -0.24 | -1.3% · -0.33 | 1.9% · 0.66 | 1.5% · 0.55 |
| 2025-03 | 11.4% · 2.96 | 10.4% · 2.72 | 21.5% · 5.31 | 0.0% · 0.05 | 11.4% · 2.96 | 12.3% · 3.19 |
| 2025-04 | -17.0% · -5.05 | -14.7% · -4.27 | -11.4% · -3.23 | -2.5% · -0.63 | -17.0% · -5.05 | -13.8% · -4.00 |
| 2025-05 | 7.4% · 2.08 | 7.4% · 2.07 | 4.5% · 1.37 | -0.8% · -0.17 | 7.4% · 2.08 | 3.8% · 1.09 |
| 2025-06 | 5.7% · 1.57 | 7.6% · 2.07 | 12.9% · 3.39 | -5.8% · -1.65 | 6.2% · 1.71 | 1.0% · 0.28 |
| 2025-07 | 6.1% · 1.63 | 7.5% · 1.98 | -1.8% · -0.45 | 2.8% · 0.76 | 5.9% · 1.56 | 4.5% · 1.20 |
| 2025-08 | -1.8% · -0.47 | 0.3% · 0.09 | -3.0% · -0.80 | -3.2% · -0.85 | -1.8% · -0.47 | -6.5% · -1.80 |
| 2025-09 | 3.5% · 1.01 | 2.8% · 0.82 | 14.0% · 3.72 | 13.0% · 3.45 | 3.9% · 1.10 | 5.9% · 1.65 |
| 2025-10 | 3.9% · 1.13 | 3.7% · 1.07 | 20.9% · 5.25 | 7.8% · 2.13 | 3.6% · 1.04 | 18.4% · 4.65 |
| 2025-11 | -1.0% · -0.20 | -1.1% · -0.21 | -2.7% · -0.63 | 0.7% · 0.30 | -0.6% · -0.08 | -0.5% · -0.04 |
| 2025-12 | -4.1% · -1.06 | -4.9% · -1.27 | -5.9% · -1.54 | -4.5% · -1.15 | -4.0% · -1.02 | -7.1% · -1.92 |
| 2026-01 | 4.8% · 1.30 | 4.8% · 1.30 | 3.3% · 0.95 | 6.0% · 1.62 | 4.4% · 1.20 | 6.3% · 1.70 |
| 2026-02 | 1.4% · 0.49 | 1.8% · 0.59 | 8.9% · 2.64 | 4.6% · 1.47 | 0.3% · 0.15 | 2.6% · 0.85 |
| 2026-03 | 5.4% · 1.48 | 6.0% · 1.62 | 7.3% · 1.95 | 5.6% · 1.53 | 6.0% · 1.61 | 6.2% · 1.67 |
| 2026-04 | 29.6% · 7.32 | 26.7% · 6.70 | 32.2% · 7.90 | 33.3% · 8.17 | 26.1% · 6.56 | 24.3% · 6.15 |
| 2026-05 | 6.4% · 1.78 | 7.1% · 1.95 | 5.4% · 1.53 | 6.2% · 1.74 | 6.3% · 1.75 | 10.5% · 2.78 |
| 2026-06 | 28.9% · 7.21 | 27.9% · 6.98 | 32.0% · 7.88 | 33.2% · 8.13 | 28.6% · 7.13 | 29.3% · 7.31 |
| 2026-07 | 12.2% · 3.18 | 12.3% · 3.22 | 14.0% · 3.62 | 11.4% · 3.01 | 12.8% · 3.33 | 8.0% · 2.19 |
| 2026-08 (to cut 08-10) | 2.1% · 1.85 | 2.3% · 2.01 | 1.0% · 0.98 | 3.2% · 2.70 | 2.2% · 1.94 | 3.1% · 2.69 |

### T8-sigma_fund. Slice 2024→cut: σ_fund (bps/8h, META members, 30-anchor trailing mean) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: bps/8h, 30-anchor trailing mean. Causal cuts at window end [3.3673, 9.3859]; descriptive (window) cuts [5.3069, 13.6993].

| bucket | M1 PIT/prod/42/cal | M1 PIT/prod/2027/cal | M1 PIT/log/42/cal | M1 PIT/log/2027/cal | M1 FRZ/prod/42/cal | fixed-seat PIT/prod/42/cal | REF T400/log/42/def |
|---|---|---|---|---|---|---|---|
| causal low (var mean 1.95) | 0.70 [-0.86, 2.24] · S 1.91 · 31%/yr · n 553 | 0.54 [-0.96, 2.00] · S 1.50 · 24%/yr · n 553 | 1.07 [-0.46, 2.59] · S 2.87 · 47%/yr · n 553 | 0.91 [-0.56, 2.33] · S 2.54 · 40%/yr · n 553 | 0.21 [-1.48, 1.84] · S 0.43 · 9%/yr · n 553 | -0.57 [-1.84, 0.67] · S -1.81 · -25%/yr · n 553 | 0.74 [-0.73, 2.21] · S 1.96 · 32%/yr · n 553 |
| causal mid (var mean 3.82) | 0.02 [-1.37, 1.47] · S 0.05 · 1%/yr · n 1230 | 0.01 [-1.40, 1.50] · S 0.02 · 0%/yr · n 1230 | -0.21 [-1.53, 1.16] · S -0.42 · -9%/yr · n 1230 | -0.22 [-1.55, 1.20] · S -0.42 · -10%/yr · n 1230 | 0.37 [-1.10, 1.73] · S 0.64 · 16%/yr · n 1230 | -1.11 [-2.34, 0.19] · S -2.27 · -49%/yr · n 1230 | 0.11 [-1.14, 1.42] · S 0.22 · 5%/yr · n 1230 |
| causal high (var mean 14.91) | 1.65 [0.83, 2.46] · S 2.87 · 72%/yr · n 3935 | 1.74 [0.93, 2.55] · S 3.03 · 76%/yr · n 3935 | 1.59 [0.77, 2.40] · S 2.79 · 70%/yr · n 3935 | 1.66 [0.85, 2.46] · S 2.93 · 73%/yr · n 3935 | 2.27 [1.30, 3.20] · S 3.48 · 99%/yr · n 3935 | 1.16 [0.32, 2.02] · S 1.97 · 51%/yr · n 3935 | 1.69 [0.86, 2.54] · S 2.93 · 74%/yr · n 3935 |
| descriptive low (var mean 3.19) | 0.39 [-0.66, 1.42] · S 0.86 · 17%/yr · n 1906 | 0.35 [-0.72, 1.36] · S 0.77 · 15%/yr · n 1906 | 0.32 [-0.70, 1.29] · S 0.70 · 14%/yr · n 1906 | 0.27 [-0.74, 1.24] · S 0.61 · 12%/yr · n 1906 | 0.54 [-0.47, 1.62] · S 1.01 · 24%/yr · n 1906 | -0.93 [-1.78, -0.09] · S -2.27 · -41%/yr · n 1906 | 0.48 [-0.46, 1.44] · S 1.05 · 21%/yr · n 1906 |
| descriptive mid (var mean 9.40) | 1.55 [0.36, 2.71] · S 2.79 · 68%/yr · n 1906 | 1.56 [0.41, 2.69] · S 2.82 · 68%/yr · n 1906 | 1.47 [0.32, 2.64] · S 2.70 · 64%/yr · n 1906 | 1.45 [0.31, 2.51] · S 2.68 · 63%/yr · n 1906 | 2.44 [1.05, 3.80] · S 3.88 · 107%/yr · n 1906 | -0.07 [-1.19, 1.02] · S -0.13 · -3%/yr · n 1906 | 1.74 [0.59, 2.87] · S 3.19 · 76%/yr · n 1906 |
| descriptive high (var mean 21.23) | 1.68 [0.41, 2.91] · S 2.72 · 73%/yr · n 1906 | 1.84 [0.60, 3.08] · S 2.98 · 81%/yr · n 1906 | 1.67 [0.40, 2.92] · S 2.70 · 73%/yr · n 1906 | 1.84 [0.61, 3.07] · S 2.99 · 80%/yr · n 1906 | 2.00 [0.57, 3.42] · S 2.88 · 87%/yr · n 1906 | 2.51 [1.04, 3.92] · S 3.83 · 110%/yr · n 1906 | 1.57 [0.23, 2.86] · S 2.49 · 69%/yr · n 1906 |

### T8-breadth_nsel. Slice 2024→cut: breadth = nsel (tradeable names) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: nsel = tradeable names in the book (sel = finite y4 & qv4h>=2.5e5 & universe); causal expanding terciles over the rec sequence since 2022. Causal cuts at window end [183.0, 288.0]; descriptive (window) cuts [266.0, 330.0].

| bucket | M1 PIT/prod/42/cal | M1 PIT/prod/2027/cal | M1 PIT/log/42/cal | M1 PIT/log/2027/cal | M1 FRZ/prod/42/cal | fixed-seat PIT/prod/42/cal | REF T400/log/42/def |
|---|---|---|---|---|---|---|---|
| causal low (var mean —) | n 0 | n 0 | n 0 | n 0 | n 0 | n 0 | n 0 |
| causal mid (var mean 259.47) | 4.99 [2.22, 7.61] · S 7.67 · 218%/yr · n 358 | 5.07 [2.32, 7.71] · S 7.79 · 222%/yr · n 358 | 4.58 [1.86, 7.24] · S 6.75 · 201%/yr · n 358 | 4.54 [1.81, 7.22] · S 6.69 · 199%/yr · n 358 | 5.94 [1.55, 10.27] · S 8.48 · 260%/yr · n 182 | 4.50 [1.23, 7.58] · S 6.11 · 197%/yr · n 358 | 4.43 [1.43, 7.54] · S 6.58 · 194%/yr · n 320 |
| causal high (var mean 307.54) | 0.95 [0.25, 1.61] · S 1.77 · 42%/yr · n 5360 | 1.00 [0.32, 1.64] · S 1.85 · 44%/yr · n 5360 | 0.92 [0.21, 1.57] · S 1.73 · 40%/yr · n 5360 | 0.96 [0.27, 1.59] · S 1.82 · 42%/yr · n 5360 | 1.52 [0.79, 2.28] · S 2.45 · 67%/yr · n 5536 | 0.24 [-0.44, 0.91] · S 0.44 · 10%/yr · n 5360 | 1.07 [0.40, 1.75] · S 1.99 · 47%/yr · n 5398 |
| descriptive low (var mean 249.22) | 0.43 [-0.60, 1.40] · S 0.94 · 19%/yr · n 1907 | 0.42 [-0.61, 1.44] · S 0.92 · 18%/yr · n 1907 | 0.34 [-0.66, 1.30] · S 0.75 · 15%/yr · n 1907 | 0.30 [-0.71, 1.27] · S 0.67 · 13%/yr · n 1907 | 0.50 [-0.53, 1.53] · S 0.94 · 22%/yr · n 1939 | 0.33 [-0.61, 1.24] · S 0.74 · 14%/yr · n 1907 | 0.88 [-0.11, 1.82] · S 1.91 · 38%/yr · n 1907 |
| descriptive mid (var mean 298.94) | 2.00 [0.76, 3.23] · S 3.35 · 87%/yr · n 1911 | 2.07 [0.82, 3.31] · S 3.48 · 91%/yr · n 1911 | 1.91 [0.69, 3.11] · S 3.25 · 84%/yr · n 1911 | 2.01 [0.81, 3.22] · S 3.44 · 88%/yr · n 1911 | 2.47 [1.19, 3.73] · S 3.84 · 108%/yr · n 1873 | 0.29 [-0.97, 1.56] · S 0.47 · 13%/yr · n 1911 | 1.92 [0.76, 3.06] · S 3.22 · 84%/yr · n 1943 |
| descriptive high (var mean 365.66) | 1.19 [-0.05, 2.40] · S 2.06 · 52%/yr · n 1900 | 1.26 [0.01, 2.47] · S 2.18 · 55%/yr · n 1900 | 1.19 [-0.03, 2.42] · S 2.09 · 52%/yr · n 1900 | 1.24 [0.06, 2.44] · S 2.18 · 54%/yr · n 1900 | 2.04 [0.56, 3.51] · S 2.99 · 90%/yr · n 1906 | 0.89 [-0.35, 2.21] · S 1.59 · 39%/yr · n 1900 | 0.97 [-0.28, 2.18] · S 1.68 · 42%/yr · n 1868 |

### T8-neg_fund_share. Slice 2024→cut: negative-funding share of members (30-anchor trailing mean) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: share of META members with 8h-equiv rate < 0, 30-anchor trailing mean. Causal cuts at window end [0.1247, 0.2686]; descriptive (window) cuts [0.1201, 0.2573].

| bucket | M1 PIT/prod/42/cal | M1 PIT/prod/2027/cal | M1 PIT/log/42/cal | M1 PIT/log/2027/cal | M1 FRZ/prod/42/cal | fixed-seat PIT/prod/42/cal | REF T400/log/42/def |
|---|---|---|---|---|---|---|---|
| causal low (var mean 0.04) | 0.83 [-0.31, 2.06] · S 1.66 · 36%/yr · n 1588 | 0.80 [-0.35, 2.06] · S 1.59 · 35%/yr · n 1588 | 0.75 [-0.37, 1.93] · S 1.51 · 33%/yr · n 1588 | 0.70 [-0.42, 1.88] · S 1.42 · 30%/yr · n 1588 | 1.45 [0.14, 2.78] · S 2.34 · 64%/yr · n 1588 | -1.38 [-2.53, -0.16] · S -2.82 · -61%/yr · n 1588 | 0.97 [-0.12, 2.08] · S 1.93 · 42%/yr · n 1588 |
| causal mid (var mean 0.18) | 1.36 [0.29, 2.44] · S 2.34 · 60%/yr · n 2182 | 1.43 [0.39, 2.50] · S 2.48 · 63%/yr · n 2182 | 1.27 [0.24, 2.33] · S 2.24 · 56%/yr · n 2182 | 1.33 [0.33, 2.37] · S 2.35 · 58%/yr · n 2182 | 1.80 [0.59, 3.02] · S 2.91 · 79%/yr · n 2182 | 1.18 [0.13, 2.21] · S 2.12 · 52%/yr · n 2182 | 1.23 [0.18, 2.29] · S 2.20 · 54%/yr · n 2182 |
| causal high (var mean 0.34) | 1.34 [0.24, 2.45] · S 2.47 · 59%/yr · n 1948 | 1.42 [0.30, 2.56] · S 2.58 · 62%/yr · n 1948 | 1.34 [0.21, 2.45] · S 2.44 · 59%/yr · n 1948 | 1.43 [0.32, 2.51] · S 2.59 · 63%/yr · n 1948 | 1.67 [0.43, 2.95] · S 2.67 · 73%/yr · n 1948 | 1.28 [0.05, 2.45] · S 2.23 · 56%/yr · n 1948 | 1.53 [0.35, 2.72] · S 2.70 · 67%/yr · n 1948 |
| descriptive low (var mean 0.05) | 0.60 [-0.59, 1.77] · S 1.18 · 26%/yr · n 1906 | 0.53 [-0.64, 1.70] · S 1.04 · 23%/yr · n 1906 | 0.58 [-0.56, 1.73] · S 1.18 · 25%/yr · n 1906 | 0.50 [-0.64, 1.62] · S 1.01 · 22%/yr · n 1906 | 1.41 [0.16, 2.67] · S 2.31 · 62%/yr · n 1906 | -1.42 [-2.46, -0.30] · S -2.84 · -62%/yr · n 1906 | 0.74 [-0.35, 1.81] · S 1.48 · 32%/yr · n 1906 |
| descriptive mid (var mean 0.19) | 1.76 [0.54, 3.00] · S 3.02 · 77%/yr · n 1906 | 1.82 [0.63, 3.04] · S 3.16 · 80%/yr · n 1906 | 1.58 [0.36, 2.80] · S 2.73 · 69%/yr · n 1906 | 1.62 [0.44, 2.78] · S 2.83 · 71%/yr · n 1906 | 2.08 [0.77, 3.51] · S 3.35 · 91%/yr · n 1906 | 1.41 [0.25, 2.53] · S 2.58 · 62%/yr · n 1906 | 1.64 [0.47, 2.86] · S 2.90 · 72%/yr · n 1906 |
| descriptive high (var mean 0.34) | 1.26 [0.04, 2.34] · S 2.29 · 55%/yr · n 1906 | 1.40 [0.15, 2.53] · S 2.52 · 61%/yr · n 1906 | 1.29 [0.09, 2.40] · S 2.34 · 57%/yr · n 1906 | 1.45 [0.24, 2.54] · S 2.60 · 63%/yr · n 1906 | 1.48 [0.14, 2.76] · S 2.34 · 65%/yr · n 1906 | 1.52 [0.25, 2.71] · S 2.57 · 66%/yr · n 1906 | 1.40 [0.12, 2.57] · S 2.44 · 61%/yr · n 1906 |

### T8-btc_rv30. Slice 2024→cut: BTC 30-day realised vol (annualised %) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: annualised %, 5m returns, 30 days. Causal cuts at window end [42.9338, 54.9238]; descriptive (window) cuts [40.8418, 53.437].

| bucket | M1 PIT/prod/42/cal | M1 PIT/prod/2027/cal | M1 PIT/log/42/cal | M1 PIT/log/2027/cal | M1 FRZ/prod/42/cal | fixed-seat PIT/prod/42/cal | REF T400/log/42/def |
|---|---|---|---|---|---|---|---|
| causal low (var mean 36.46) | 1.25 [0.24, 2.28] · S 2.31 · 55%/yr · n 2304 | 1.37 [0.38, 2.40] · S 2.55 · 60%/yr · n 2304 | 1.33 [0.33, 2.34] · S 2.53 · 58%/yr · n 2304 | 1.41 [0.44, 2.39] · S 2.70 · 62%/yr · n 2304 | 1.99 [0.84, 3.12] · S 3.22 · 87%/yr · n 2304 | 1.02 [-0.04, 2.07] · S 1.91 · 45%/yr · n 2304 | 1.38 [0.37, 2.38] · S 2.63 · 60%/yr · n 2304 |
| causal mid (var mean 51.82) | 1.18 [0.09, 2.25] · S 2.05 · 52%/yr · n 2318 | 1.17 [0.12, 2.26] · S 2.03 · 51%/yr · n 2318 | 0.98 [-0.10, 2.05] · S 1.71 · 43%/yr · n 2318 | 0.97 [-0.10, 2.04] · S 1.69 · 42%/yr · n 2318 | 1.35 [0.14, 2.57] · S 2.13 · 59%/yr · n 2318 | 0.12 [-0.92, 1.12] · S 0.20 · 5%/yr · n 2318 | 1.04 [-0.05, 2.11] · S 1.81 · 46%/yr · n 2318 |
| causal high (var mean 64.66) | 1.18 [-0.21, 2.62] · S 2.37 · 52%/yr · n 1096 | 1.17 [-0.21, 2.66] · S 2.32 · 51%/yr · n 1096 | 1.13 [-0.25, 2.52] · S 2.24 · 50%/yr · n 1096 | 1.18 [-0.16, 2.54] · S 2.34 · 52%/yr · n 1096 | 1.61 [-0.05, 3.21] · S 2.68 · 70%/yr · n 1096 | 0.24 [-1.21, 1.68] · S 0.46 · 10%/yr · n 1096 | 1.47 [0.03, 2.89] · S 2.79 · 64%/yr · n 1096 |
| descriptive low (var mean 35.11) | 1.23 [0.10, 2.40] · S 2.32 · 54%/yr · n 1906 | 1.32 [0.21, 2.46] · S 2.51 · 58%/yr · n 1906 | 1.38 [0.28, 2.53] · S 2.68 · 60%/yr · n 1906 | 1.43 [0.38, 2.53] · S 2.79 · 62%/yr · n 1906 | 2.05 [0.75, 3.36] · S 3.43 · 90%/yr · n 1906 | 1.00 [-0.18, 2.18] · S 1.90 · 44%/yr · n 1906 | 1.45 [0.41, 2.58] · S 2.82 · 64%/yr · n 1906 |
| descriptive mid (var mean 48.06) | 1.38 [0.15, 2.61] · S 2.28 · 60%/yr · n 1906 | 1.51 [0.31, 2.71] · S 2.51 · 66%/yr · n 1906 | 1.15 [-0.04, 2.42] · S 1.93 · 51%/yr · n 1906 | 1.29 [0.14, 2.53] · S 2.18 · 57%/yr · n 1906 | 1.40 [-0.01, 2.74] · S 2.10 · 61%/yr · n 1906 | 1.07 [-0.09, 2.30] · S 1.82 · 47%/yr · n 1906 | 1.17 [-0.09, 2.41] · S 1.95 · 51%/yr · n 1906 |
| descriptive high (var mean 61.10) | 1.01 [-0.02, 2.06] · S 2.01 · 44%/yr · n 1906 | 0.93 [-0.10, 1.96] · S 1.81 · 41%/yr · n 1906 | 0.92 [-0.08, 1.95] · S 1.81 · 40%/yr · n 1906 | 0.84 [-0.15, 1.88] · S 1.64 · 37%/yr · n 1906 | 1.53 [0.38, 2.82] · S 2.56 · 67%/yr · n 1906 | -0.55 [-1.61, 0.52] · S -1.05 · -24%/yr · n 1906 | 1.16 [0.16, 2.19] · S 2.21 · 51%/yr · n 1906 |

### T9. Turnover, cost and carry per window (per unit gross; cost_ex and carry_ex from the rec; shares = Σ over the window / Σ gross price P&L)

| arm | window | turnover/gross per anchor | cost bps/anchor/gross | cost %/yr NAV @2× | carry paid bps/anchor/gross | carry %/yr NAV @2× | gross price P&L bps/anchor/gross | cost share | carry share | net bps/anchor/gross |
|---|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 2024->26 | 0.0684 | 0.182 | 7.97 | 0.607 | 26.58 | 2.049 | 0.070 | 0.340 | 1.260 |
| REF T400/log/42/def | 2025->26 | 0.0629 | 0.188 | 8.25 | 0.851 | 37.29 | 2.689 | 0.052 | 0.329 | 1.649 |
| REF T400/log/42/def | 2026->cut | 0.0309 | 0.117 | 5.12 | 1.179 | 51.66 | 4.506 | 0.026 | 0.260 | 3.209 |
| M1 PIT/prod/42/def | 2024->26 | 0.0795 | 0.210 | 9.22 | 0.501 | 21.93 | 1.873 | 0.091 | 0.317 | 1.162 |
| M1 PIT/prod/42/def | 2025->26 | 0.0717 | 0.219 | 9.58 | 0.714 | 31.28 | 2.475 | 0.066 | 0.314 | 1.543 |
| M1 PIT/prod/42/def | 2026->cut | 0.0351 | 0.131 | 5.72 | 1.020 | 44.68 | 4.286 | 0.030 | 0.235 | 3.135 |
| M1 PIT/prod/42/cal | 2024->26 | 0.0795 | 0.167 | 7.30 | 0.501 | 21.93 | 1.873 | 0.070 | 0.317 | 1.206 |
| M1 PIT/prod/42/cal | 2025->26 | 0.0717 | 0.151 | 6.61 | 0.714 | 31.28 | 2.475 | 0.044 | 0.314 | 1.611 |
| M1 PIT/prod/42/cal | 2026->cut | 0.0351 | 0.077 | 3.36 | 1.020 | 44.68 | 4.286 | 0.018 | 0.235 | 3.189 |
| M1 PIT/prod/2027/def | 2024->26 | 0.0748 | 0.197 | 8.61 | 0.512 | 22.42 | 1.921 | 0.086 | 0.311 | 1.212 |
| M1 PIT/prod/2027/def | 2025->26 | 0.0653 | 0.200 | 8.74 | 0.733 | 32.09 | 2.536 | 0.063 | 0.312 | 1.604 |
| M1 PIT/prod/2027/def | 2026->cut | 0.0370 | 0.138 | 6.02 | 1.019 | 44.64 | 4.242 | 0.032 | 0.237 | 3.086 |
| M1 PIT/prod/2027/cal | 2024->26 | 0.0748 | 0.157 | 6.89 | 0.512 | 22.42 | 1.921 | 0.067 | 0.311 | 1.252 |
| M1 PIT/prod/2027/cal | 2025->26 | 0.0653 | 0.138 | 6.04 | 0.733 | 32.09 | 2.536 | 0.042 | 0.312 | 1.666 |
| M1 PIT/prod/2027/cal | 2026->cut | 0.0370 | 0.080 | 3.52 | 1.019 | 44.64 | 4.242 | 0.019 | 0.237 | 3.143 |
| M1 PIT/log/42/def | 2024->26 | 0.0751 | 0.200 | 8.77 | 0.513 | 22.49 | 1.821 | 0.086 | 0.327 | 1.107 |
| M1 PIT/log/42/def | 2025->26 | 0.0682 | 0.208 | 9.11 | 0.724 | 31.70 | 2.448 | 0.062 | 0.316 | 1.516 |
| M1 PIT/log/42/def | 2026->cut | 0.0332 | 0.125 | 5.46 | 1.028 | 45.00 | 4.252 | 0.029 | 0.240 | 3.100 |
| M1 PIT/log/42/cal | 2024->26 | 0.0751 | 0.158 | 6.91 | 0.513 | 22.49 | 1.821 | 0.066 | 0.327 | 1.149 |
| M1 PIT/log/42/cal | 2025->26 | 0.0682 | 0.144 | 6.29 | 0.724 | 31.70 | 2.448 | 0.041 | 0.316 | 1.581 |
| M1 PIT/log/42/cal | 2026->cut | 0.0332 | 0.073 | 3.20 | 1.028 | 45.00 | 4.252 | 0.017 | 0.240 | 3.152 |
| M1 PIT/log/2027/def | 2024->26 | 0.0707 | 0.187 | 8.20 | 0.525 | 23.01 | 1.861 | 0.082 | 0.322 | 1.148 |
| M1 PIT/log/2027/def | 2025->26 | 0.0620 | 0.190 | 8.30 | 0.742 | 32.50 | 2.506 | 0.059 | 0.314 | 1.575 |
| M1 PIT/log/2027/def | 2026->cut | 0.0348 | 0.130 | 5.71 | 1.024 | 44.86 | 4.213 | 0.030 | 0.241 | 3.058 |
| M1 PIT/log/2027/cal | 2024->26 | 0.0707 | 0.149 | 6.52 | 0.525 | 23.01 | 1.861 | 0.063 | 0.322 | 1.187 |
| M1 PIT/log/2027/cal | 2025->26 | 0.0620 | 0.131 | 5.74 | 0.742 | 32.50 | 2.506 | 0.039 | 0.314 | 1.633 |
| M1 PIT/log/2027/cal | 2026->cut | 0.0348 | 0.076 | 3.33 | 1.024 | 44.86 | 4.213 | 0.018 | 0.241 | 3.113 |
| M1 FRZ/prod/42/cal | 2024->26 | 0.0659 | 0.140 | 6.12 | 0.537 | 23.53 | 2.336 | 0.046 | 0.272 | 1.659 |
| M1 FRZ/prod/42/cal | 2025->26 | 0.0653 | 0.139 | 6.07 | 0.722 | 31.64 | 3.068 | 0.032 | 0.256 | 2.207 |
| M1 FRZ/prod/42/cal | 2026->cut | 0.0281 | 0.064 | 2.79 | 1.071 | 46.90 | 4.769 | 0.013 | 0.225 | 3.635 |
| M1 FRZ/prod/2027/cal | 2024->26 | 0.0623 | 0.133 | 5.81 | 0.550 | 24.07 | 2.449 | 0.043 | 0.264 | 1.767 |
| M1 FRZ/prod/2027/cal | 2025->26 | 0.0601 | 0.128 | 5.61 | 0.737 | 32.30 | 3.200 | 0.031 | 0.251 | 2.334 |
| M1 FRZ/prod/2027/cal | 2026->cut | 0.0290 | 0.066 | 2.87 | 1.071 | 46.90 | 4.753 | 0.014 | 0.225 | 3.617 |
| trade PIT/prod/42/cal | 2024->26 | 0.0721 | 0.151 | 6.63 | 0.547 | 23.94 | 1.873 | 0.064 | 0.336 | 1.175 |
| trade PIT/prod/42/cal | 2025->26 | 0.0656 | 0.138 | 6.06 | 0.765 | 33.52 | 2.381 | 0.042 | 0.333 | 1.477 |
| trade PIT/prod/42/cal | 2026->cut | 0.0341 | 0.075 | 3.28 | 1.022 | 44.77 | 4.372 | 0.017 | 0.232 | 3.275 |
| trade PIT/prod/2027/cal | 2024->26 | 0.0681 | 0.143 | 6.28 | 0.556 | 24.36 | 1.904 | 0.061 | 0.334 | 1.204 |
| trade PIT/prod/2027/cal | 2025->26 | 0.0600 | 0.127 | 5.57 | 0.780 | 34.17 | 2.393 | 0.041 | 0.337 | 1.485 |
| trade PIT/prod/2027/cal | 2026->cut | 0.0360 | 0.079 | 3.44 | 1.019 | 44.64 | 4.289 | 0.018 | 0.235 | 3.191 |
| trade PIT/prod/42/def | 2024->26 | 0.0721 | 0.195 | 8.52 | 0.547 | 23.94 | 1.873 | 0.084 | 0.336 | 1.132 |
| trade PIT/prod/42/def | 2025->26 | 0.0656 | 0.201 | 8.81 | 0.765 | 33.52 | 2.381 | 0.063 | 0.333 | 1.414 |
| trade PIT/prod/42/def | 2026->cut | 0.0341 | 0.128 | 5.61 | 1.022 | 44.77 | 4.372 | 0.029 | 0.232 | 3.222 |
| members PIT/prod/42/cal | 2024->26 | 0.0793 | 0.166 | 7.28 | 0.508 | 22.26 | 1.855 | 0.070 | 0.328 | 1.181 |
| members PIT/prod/42/cal | 2025->26 | 0.0709 | 0.149 | 6.53 | 0.731 | 32.00 | 2.453 | 0.043 | 0.327 | 1.573 |
| members PIT/prod/42/cal | 2026->cut | 0.0338 | 0.074 | 3.24 | 1.067 | 46.72 | 4.199 | 0.017 | 0.252 | 3.058 |
| members PIT/prod/2027/cal | 2024->26 | 0.0746 | 0.157 | 6.86 | 0.520 | 22.78 | 1.899 | 0.067 | 0.324 | 1.222 |
| members PIT/prod/2027/cal | 2025->26 | 0.0646 | 0.136 | 5.97 | 0.750 | 32.85 | 2.514 | 0.041 | 0.326 | 1.627 |
| members PIT/prod/2027/cal | 2026->cut | 0.0356 | 0.077 | 3.39 | 1.062 | 46.50 | 4.150 | 0.018 | 0.253 | 3.011 |
| fixed-seat PIT/prod/42/cal | 2024->26 | 0.0189 | 0.044 | 1.92 | 0.698 | 30.58 | 1.245 | 0.037 | 0.581 | 0.503 |
| fixed-seat PIT/prod/42/cal | 2025->26 | 0.0194 | 0.046 | 2.00 | 0.900 | 39.42 | 2.244 | 0.021 | 0.404 | 1.298 |
| fixed-seat PIT/prod/42/cal | 2026->cut | 0.0225 | 0.053 | 2.32 | 1.010 | 44.22 | 4.674 | 0.011 | 0.215 | 3.611 |
| fixed-seat PIT/prod/2027/cal | 2024->26 | 0.0189 | 0.044 | 1.92 | 0.698 | 30.57 | 1.256 | 0.036 | 0.574 | 0.515 |
| fixed-seat PIT/prod/2027/cal | 2025->26 | 0.0194 | 0.045 | 1.99 | 0.899 | 39.38 | 2.274 | 0.020 | 0.397 | 1.329 |
| fixed-seat PIT/prod/2027/cal | 2026->cut | 0.0227 | 0.053 | 2.33 | 1.008 | 44.14 | 4.682 | 0.011 | 0.214 | 3.621 |
| M1 PIT/prod/42/fee+slip | 2024->26 | 0.0795 | -0.035 | -1.53 | 0.501 | 21.93 | 1.873 | -0.015 | 0.317 | 1.407 |
| M1 PIT/prod/42/fee+slip | 2025->26 | 0.0717 | -0.034 | -1.49 | 0.714 | 31.28 | 2.475 | -0.010 | 0.314 | 1.796 |
| M1 PIT/prod/42/fee+slip | 2026->cut | 0.0351 | -0.018 | -0.78 | 1.020 | 44.68 | 4.286 | -0.004 | 0.235 | 3.284 |

### T9b. Δ(live fee-only − device default cost), m1, same universe/caliber/seed

paired by construction: identical books, only COST_B differs; mean net bps/anchor per gross (S = anchor Sharpe a vs b; cost = cost bps/anchor/gross a vs b)

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| M1 PIT/prod/42/cal − M1 PIT/prod/42/def | 0.005 (S 1.24 vs 1.23; cost 0.192 vs 0.197) | 0.077 (S 1.14 vs 1.01; cost 0.196 vs 0.272) | 0.054 (S 4.96 vs 4.87; cost 0.077 vs 0.131) | 0.044 (S 2.21 vs 2.13; cost 0.167 vs 0.210) | 0.068 (S 2.69 vs 2.57; cost 0.151 vs 0.219) |
| M1 PIT/prod/2027/cal − M1 PIT/prod/2027/def | 0.004 (S 1.30 vs 1.29; cost 0.188 vs 0.192) | 0.065 (S 1.34 vs 1.23; cost 0.173 vs 0.237) | 0.057 (S 4.90 vs 4.81; cost 0.080 vs 0.138) | 0.040 (S 2.29 vs 2.21; cost 0.157 vs 0.197) | 0.062 (S 2.78 vs 2.68; cost 0.138 vs 0.200) |
| M1 PIT/log/42/cal − M1 PIT/log/42/def | 0.007 (S 1.03 vs 1.01; cost 0.180 vs 0.188) | 0.072 (S 1.12 vs 0.99; cost 0.187 vs 0.259) | 0.052 (S 4.89 vs 4.81; cost 0.073 vs 0.125) | 0.043 (S 2.12 vs 2.04; cost 0.158 vs 0.200) | 0.065 (S 2.66 vs 2.55; cost 0.144 vs 0.208) |
| M1 PIT/log/2027/cal − M1 PIT/log/2027/def | 0.006 (S 1.07 vs 1.05; cost 0.177 vs 0.183) | 0.061 (S 1.31 vs 1.20; cost 0.165 vs 0.226) | 0.054 (S 4.85 vs 4.77; cost 0.076 vs 0.130) | 0.038 (S 2.20 vs 2.13; cost 0.149 vs 0.187) | 0.058 (S 2.75 vs 2.65; cost 0.131 vs 0.190) |

### T9c. Δ(U-FROZEN − U-PIT), m1, prod, live fee-only

unpaired books; U-FROZEN carries look-ahead selection

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| M1 FRZ/prod/42/cal − M1 PIT/prod/42/cal | 0.223 (S 1.45 vs 1.24; cost 0.142 vs 0.192) | 0.689 (S 2.10 vs 1.14; cost 0.184 vs 0.196) | 0.446 (S 5.10 vs 4.96; cost 0.064 vs 0.077) | 0.453 (S 2.67 vs 2.21; cost 0.140 vs 0.167) | 0.597 (S 3.30 vs 2.69; cost 0.139 vs 0.151) |
| M1 FRZ/prod/2027/cal − M1 PIT/prod/2027/cal | 0.270 (S 1.60 vs 1.30; cost 0.140 vs 0.188) | 0.786 (S 2.44 vs 1.34; cost 0.166 vs 0.173) | 0.474 (S 5.09 vs 4.90; cost 0.066 vs 0.080) | 0.515 (S 2.85 vs 2.29; cost 0.133 vs 0.157) | 0.668 (S 3.50 vs 2.78; cost 0.128 vs 0.138) |

### T9d. Δ(fee+slippage-vs-anchor-mid − fee-only) = maker price improvement vs the executor's anchor mid, m1, prod, s42

identical books; cost-calib tiers (−2.41 / 16.79 / 0.851 …) vs fee-only (1.80 / 4.50 …); the timing decay N → N+24 min is NOT in either vector

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| M1 PIT/prod/42/fee+slip − M1 PIT/prod/42/cal | 0.229 (S 1.74 vs 1.24; cost -0.037 vs 0.192) | 0.240 (S 1.56 vs 1.14; cost -0.044 vs 0.196) | 0.095 (S 5.10 vs 4.96; cost -0.018 vs 0.077) | 0.202 (S 2.57 vs 2.21; cost -0.035 vs 0.167) | 0.185 (S 3.00 vs 2.69; cost -0.034 vs 0.151) |

### T9e. Δ(rank-base choice): m1 − trade (all legs on the 829 base) and m1 − members (every leg within the universe)

unpaired books (different rank bases ⇒ different weights); prod, same seed and cost

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| M1 PIT/prod/42/cal − trade PIT/prod/42/cal | -0.134 (S 1.24 vs 1.55; cost 0.192 vs 0.172) | 0.267 (S 1.14 vs 0.69; cost 0.196 vs 0.177) | -0.086 (S 4.96 vs 5.06; cost 0.077 vs 0.075) | 0.031 (S 2.21 vs 2.18; cost 0.167 vs 0.151) | 0.134 (S 2.69 vs 2.50; cost 0.151 vs 0.138) |
| M1 PIT/prod/2027/cal − trade PIT/prod/2027/cal | -0.167 (S 1.30 vs 1.70; cost 0.188 vs 0.170) | 0.320 (S 1.34 vs 0.81; cost 0.173 vs 0.157) | -0.048 (S 4.90 vs 4.95; cost 0.080 vs 0.079) | 0.047 (S 2.29 vs 2.23; cost 0.157 vs 0.143) | 0.181 (S 2.78 vs 2.51; cost 0.138 vs 0.127) |
| M1 PIT/prod/42/cal − members PIT/prod/42/cal | 0.005 (S 1.24 vs 1.21; cost 0.192 vs 0.193) | -0.020 (S 1.14 vs 1.19; cost 0.196 vs 0.195) | 0.131 (S 4.96 vs 4.90; cost 0.077 vs 0.074) | 0.025 (S 2.21 vs 2.18; cost 0.167 vs 0.166) | 0.037 (S 2.69 vs 2.68; cost 0.151 vs 0.149) |
| M1 PIT/prod/2027/cal − members PIT/prod/2027/cal | 0.016 (S 1.30 vs 1.25; cost 0.188 vs 0.189) | -0.019 (S 1.34 vs 1.39; cost 0.173 vs 0.172) | 0.132 (S 4.90 vs 4.83; cost 0.080 vs 0.077) | 0.030 (S 2.29 vs 2.26; cost 0.157 vs 0.157) | 0.038 (S 2.78 vs 2.77; cost 0.138 vs 0.136) |
| M1 PIT/prod/42/def − trade PIT/prod/42/def | -0.128 (S 1.23 vs 1.53; cost 0.197 vs 0.184) | 0.259 (S 1.01 vs 0.57; cost 0.272 vs 0.246) | -0.087 (S 4.87 vs 4.98; cost 0.131 vs 0.128) | 0.030 (S 2.13 vs 2.10; cost 0.210 vs 0.195) | 0.129 (S 2.57 vs 2.39; cost 0.219 vs 0.201) |

### T9f. 附加 Δ(seat path): fixed live seat 0.21/0.79 − dynamic device seat (m1), and members − m1

unpaired books; the fixed-seat arm holds w3_king = 0.21 at every anchor of the whole history

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| fixed-seat PIT/prod/42/cal − M1 PIT/prod/42/cal | -1.329 (S -1.84 vs 1.24; cost 0.041 vs 0.192) | -0.759 (S -0.21 vs 1.14; cost 0.041 vs 0.196) | 0.422 (S 4.97 vs 4.96; cost 0.053 vs 0.077) | -0.703 (S 0.92 vs 2.21; cost 0.044 vs 0.167) | -0.313 (S 2.12 vs 2.69; cost 0.046 vs 0.151) |
| fixed-seat PIT/prod/2027/cal − M1 PIT/prod/2027/cal | -1.380 (S -1.89 vs 1.30; cost 0.041 vs 0.188) | -0.831 (S -0.12 vs 1.34; cost 0.041 vs 0.173) | 0.478 (S 4.99 vs 4.90; cost 0.053 vs 0.080) | -0.737 (S 0.94 vs 2.29; cost 0.044 vs 0.157) | -0.336 (S 2.17 vs 2.78; cost 0.045 vs 0.138) |
| members PIT/prod/42/cal − M1 PIT/prod/42/cal | -0.005 (S 1.21 vs 1.24; cost 0.193 vs 0.192) | 0.020 (S 1.19 vs 1.14; cost 0.195 vs 0.196) | -0.131 (S 4.90 vs 4.96; cost 0.074 vs 0.077) | -0.025 (S 2.18 vs 2.21; cost 0.166 vs 0.167) | -0.037 (S 2.68 vs 2.69; cost 0.149 vs 0.151) |

### T10. Replay form by year — mean gross of the unit book, members (nmember = universe ∩ listed under m1/members; 829 under trade), tradeable names (nsel), king seat w3_king, net long, stop fires, king/fund leg returns (bps/anchor unit-gross rank book)

| arm | window | gross_total | nmember | nsel | w3_king | w3_fund | net long | fires | leg_king | leg_fund |
|---|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42/def | 2024-H1 | 0.778 | 829 | 257 | 0.332 | 0.668 | -0.0017 | 235 | -0.412 | -0.007 |
| REF T400/log/42/def | 2024-H2 | 0.428 | 829 | 287 | 0.943 | 0.057 | -0.0039 | 123 | 2.760 | -0.222 |
| REF T400/log/42/def | 2025 | 0.531 | 829 | 375 | 0.673 | 0.327 | -0.0407 | 584 | 1.492 | 0.888 |
| REF T400/log/42/def | 2026->cut | 0.780 | 829 | 328 | 0.368 | 0.632 | -0.0614 | 415 | 1.157 | 3.350 |
| M1 PIT/prod/42/def | 2024-H1 | 0.653 | 254 | 247 | 0.523 | 0.477 | -0.0012 | 188 | -0.383 | -0.419 |
| M1 PIT/prod/42/def | 2024-H2 | 0.448 | 277 | 269 | 0.921 | 0.079 | -0.0038 | 119 | 2.697 | -0.278 |
| M1 PIT/prod/42/def | 2025 | 0.500 | 404 | 354 | 0.742 | 0.258 | -0.0282 | 461 | 1.111 | 0.602 |
| M1 PIT/prod/42/def | 2026->cut | 0.782 | 449 | 299 | 0.388 | 0.612 | -0.0560 | 367 | 1.173 | 3.455 |
| M1 PIT/prod/42/cal | 2024-H1 | 0.653 | 254 | 247 | 0.523 | 0.477 | -0.0012 | 188 | -0.383 | -0.419 |
| M1 PIT/prod/42/cal | 2024-H2 | 0.448 | 277 | 269 | 0.921 | 0.079 | -0.0038 | 119 | 2.697 | -0.278 |
| M1 PIT/prod/42/cal | 2025 | 0.500 | 404 | 354 | 0.742 | 0.258 | -0.0282 | 461 | 1.111 | 0.602 |
| M1 PIT/prod/42/cal | 2026->cut | 0.782 | 449 | 299 | 0.388 | 0.612 | -0.0560 | 367 | 1.173 | 3.455 |
| M1 PIT/prod/2027/def | 2024-H1 | 0.657 | 254 | 247 | 0.523 | 0.477 | -0.0014 | 195 | -0.383 | -0.419 |
| M1 PIT/prod/2027/def | 2024-H2 | 0.448 | 277 | 269 | 0.921 | 0.079 | -0.0050 | 128 | 2.697 | -0.278 |
| M1 PIT/prod/2027/def | 2025 | 0.521 | 404 | 354 | 0.742 | 0.258 | -0.0310 | 472 | 1.111 | 0.602 |
| M1 PIT/prod/2027/def | 2026->cut | 0.784 | 449 | 299 | 0.388 | 0.612 | -0.0527 | 360 | 1.173 | 3.455 |
| M1 PIT/prod/2027/cal | 2024-H1 | 0.657 | 254 | 247 | 0.523 | 0.477 | -0.0014 | 195 | -0.383 | -0.419 |
| M1 PIT/prod/2027/cal | 2024-H2 | 0.448 | 277 | 269 | 0.921 | 0.079 | -0.0050 | 128 | 2.697 | -0.278 |
| M1 PIT/prod/2027/cal | 2025 | 0.521 | 404 | 354 | 0.742 | 0.258 | -0.0310 | 472 | 1.111 | 0.602 |
| M1 PIT/prod/2027/cal | 2026->cut | 0.784 | 449 | 299 | 0.388 | 0.612 | -0.0527 | 360 | 1.173 | 3.455 |
| M1 PIT/log/42/def | 2024-H1 | 0.705 | 254 | 247 | 0.413 | 0.587 | 0.0013 | 192 | -0.357 | -0.395 |
| M1 PIT/log/42/def | 2024-H2 | 0.438 | 277 | 269 | 0.933 | 0.067 | -0.0040 | 116 | 2.588 | -0.270 |
| M1 PIT/log/42/def | 2025 | 0.520 | 404 | 354 | 0.717 | 0.283 | -0.0284 | 437 | 1.193 | 0.725 |
| M1 PIT/log/42/def | 2026->cut | 0.791 | 449 | 299 | 0.371 | 0.629 | -0.0556 | 352 | 1.161 | 3.756 |
| M1 PIT/log/42/cal | 2024-H1 | 0.705 | 254 | 247 | 0.413 | 0.587 | 0.0013 | 192 | -0.357 | -0.395 |
| M1 PIT/log/42/cal | 2024-H2 | 0.438 | 277 | 269 | 0.933 | 0.067 | -0.0040 | 116 | 2.588 | -0.270 |
| M1 PIT/log/42/cal | 2025 | 0.520 | 404 | 354 | 0.717 | 0.283 | -0.0284 | 437 | 1.193 | 0.725 |
| M1 PIT/log/42/cal | 2026->cut | 0.791 | 449 | 299 | 0.371 | 0.629 | -0.0556 | 352 | 1.161 | 3.756 |
| M1 PIT/log/2027/def | 2024-H1 | 0.707 | 254 | 247 | 0.413 | 0.587 | 0.0009 | 200 | -0.357 | -0.395 |
| M1 PIT/log/2027/def | 2024-H2 | 0.438 | 277 | 269 | 0.933 | 0.067 | -0.0061 | 124 | 2.588 | -0.270 |
| M1 PIT/log/2027/def | 2025 | 0.540 | 404 | 354 | 0.717 | 0.283 | -0.0328 | 459 | 1.193 | 0.725 |
| M1 PIT/log/2027/def | 2026->cut | 0.794 | 449 | 299 | 0.371 | 0.629 | -0.0516 | 348 | 1.161 | 3.756 |
| M1 PIT/log/2027/cal | 2024-H1 | 0.707 | 254 | 247 | 0.413 | 0.587 | 0.0009 | 200 | -0.357 | -0.395 |
| M1 PIT/log/2027/cal | 2024-H2 | 0.438 | 277 | 269 | 0.933 | 0.067 | -0.0061 | 124 | 2.588 | -0.270 |
| M1 PIT/log/2027/cal | 2025 | 0.540 | 404 | 354 | 0.717 | 0.283 | -0.0328 | 459 | 1.193 | 0.725 |
| M1 PIT/log/2027/cal | 2026->cut | 0.794 | 449 | 299 | 0.371 | 0.629 | -0.0516 | 348 | 1.161 | 3.756 |
| M1 FRZ/prod/42/cal | 2024-H1 | 0.854 | 450 | 168 | 0.043 | 0.957 | -0.0140 | 164 | -0.233 | -0.082 |
| M1 FRZ/prod/42/cal | 2024-H2 | 0.477 | 450 | 196 | 0.873 | 0.127 | -0.0034 | 80 | 2.118 | -0.397 |
| M1 FRZ/prod/42/cal | 2025 | 0.546 | 450 | 292 | 0.678 | 0.322 | -0.0339 | 466 | 1.565 | 1.186 |
| M1 FRZ/prod/42/cal | 2026->cut | 0.806 | 450 | 281 | 0.302 | 0.698 | -0.0693 | 411 | 0.870 | 4.520 |
| M1 FRZ/prod/2027/cal | 2024-H1 | 0.854 | 450 | 168 | 0.043 | 0.957 | -0.0139 | 164 | -0.233 | -0.082 |
| M1 FRZ/prod/2027/cal | 2024-H2 | 0.477 | 450 | 196 | 0.873 | 0.127 | -0.0051 | 84 | 2.118 | -0.397 |
| M1 FRZ/prod/2027/cal | 2025 | 0.566 | 450 | 292 | 0.678 | 0.322 | -0.0368 | 475 | 1.565 | 1.186 |
| M1 FRZ/prod/2027/cal | 2026->cut | 0.809 | 450 | 281 | 0.302 | 0.698 | -0.0661 | 406 | 0.870 | 4.520 |
| trade PIT/prod/42/cal | 2024-H1 | 0.743 | 829 | 247 | 0.421 | 0.579 | 0.0003 | 201 | -0.408 | -0.087 |
| trade PIT/prod/42/cal | 2024-H2 | 0.438 | 829 | 269 | 0.941 | 0.059 | -0.0033 | 125 | 3.025 | -0.208 |
| trade PIT/prod/42/cal | 2025 | 0.535 | 829 | 354 | 0.687 | 0.313 | -0.0373 | 484 | 1.424 | 0.764 |
| trade PIT/prod/42/cal | 2026->cut | 0.785 | 829 | 299 | 0.382 | 0.618 | -0.0584 | 374 | 1.164 | 3.144 |
| trade PIT/prod/2027/cal | 2024-H1 | 0.743 | 829 | 247 | 0.421 | 0.579 | -0.0008 | 211 | -0.408 | -0.087 |
| trade PIT/prod/2027/cal | 2024-H2 | 0.437 | 829 | 269 | 0.941 | 0.059 | -0.0056 | 129 | 3.025 | -0.208 |
| trade PIT/prod/2027/cal | 2025 | 0.554 | 829 | 354 | 0.687 | 0.313 | -0.0408 | 491 | 1.424 | 0.764 |
| trade PIT/prod/2027/cal | 2026->cut | 0.787 | 829 | 299 | 0.382 | 0.618 | -0.0562 | 373 | 1.164 | 3.144 |
| trade PIT/prod/42/def | 2024-H1 | 0.743 | 829 | 247 | 0.421 | 0.579 | 0.0003 | 201 | -0.408 | -0.087 |
| trade PIT/prod/42/def | 2024-H2 | 0.438 | 829 | 269 | 0.941 | 0.059 | -0.0033 | 125 | 3.025 | -0.208 |
| trade PIT/prod/42/def | 2025 | 0.535 | 829 | 354 | 0.687 | 0.313 | -0.0373 | 484 | 1.424 | 0.764 |
| trade PIT/prod/42/def | 2026->cut | 0.785 | 829 | 299 | 0.382 | 0.618 | -0.0584 | 374 | 1.164 | 3.144 |
| members PIT/prod/42/cal | 2024-H1 | 0.648 | 254 | 247 | 0.545 | 0.455 | -0.0003 | 182 | -0.278 | -0.277 |
| members PIT/prod/42/cal | 2024-H2 | 0.450 | 277 | 269 | 0.925 | 0.075 | -0.0028 | 118 | 2.691 | -0.303 |
| members PIT/prod/42/cal | 2025 | 0.505 | 404 | 354 | 0.746 | 0.254 | -0.0259 | 449 | 1.126 | 0.504 |
| members PIT/prod/42/cal | 2026->cut | 0.796 | 449 | 299 | 0.385 | 0.615 | -0.0511 | 375 | 1.161 | 3.402 |
| members PIT/prod/2027/cal | 2024-H1 | 0.653 | 254 | 247 | 0.545 | 0.455 | -0.0010 | 190 | -0.278 | -0.277 |
| members PIT/prod/2027/cal | 2024-H2 | 0.450 | 277 | 269 | 0.925 | 0.075 | -0.0042 | 128 | 2.691 | -0.303 |
| members PIT/prod/2027/cal | 2025 | 0.525 | 404 | 354 | 0.746 | 0.254 | -0.0297 | 466 | 1.126 | 0.504 |
| members PIT/prod/2027/cal | 2026->cut | 0.799 | 449 | 299 | 0.385 | 0.615 | -0.0481 | 368 | 1.161 | 3.402 |
| fixed-seat PIT/prod/42/cal | 2024-H1 | 0.876 | 254 | 247 | 0.210 | 0.790 | -0.0148 | 260 | 0.027 | 0.088 |
| fixed-seat PIT/prod/42/cal | 2024-H2 | 0.836 | 277 | 269 | 0.210 | 0.790 | -0.0262 | 301 | 0.587 | -1.158 |
| fixed-seat PIT/prod/42/cal | 2025 | 0.783 | 404 | 354 | 0.210 | 0.790 | -0.0879 | 836 | 0.328 | 1.081 |
| fixed-seat PIT/prod/42/cal | 2026->cut | 0.796 | 449 | 299 | 0.210 | 0.790 | -0.0716 | 409 | 0.647 | 4.509 |
| fixed-seat PIT/prod/2027/cal | 2024-H1 | 0.876 | 254 | 247 | 0.210 | 0.790 | -0.0145 | 259 | 0.027 | 0.088 |
| fixed-seat PIT/prod/2027/cal | 2024-H2 | 0.836 | 277 | 269 | 0.210 | 0.790 | -0.0246 | 298 | 0.587 | -1.158 |
| fixed-seat PIT/prod/2027/cal | 2025 | 0.778 | 404 | 354 | 0.210 | 0.790 | -0.0895 | 842 | 0.328 | 1.081 |
| fixed-seat PIT/prod/2027/cal | 2026->cut | 0.800 | 449 | 299 | 0.210 | 0.790 | -0.0711 | 415 | 0.647 | 4.509 |
| M1 PIT/prod/42/fee+slip | 2024-H1 | 0.653 | 254 | 247 | 0.523 | 0.477 | -0.0012 | 188 | -0.383 | -0.419 |
| M1 PIT/prod/42/fee+slip | 2024-H2 | 0.448 | 277 | 269 | 0.921 | 0.079 | -0.0038 | 119 | 2.697 | -0.278 |
| M1 PIT/prod/42/fee+slip | 2025 | 0.500 | 404 | 354 | 0.742 | 0.258 | -0.0282 | 461 | 1.111 | 0.602 |
| M1 PIT/prod/42/fee+slip | 2026->cut | 0.782 | 449 | 299 | 0.388 | 0.612 | -0.0560 | 367 | 1.173 | 3.455 |

### T11. Caliber reconciliation — unit replay book (net_ex, gross floats; = RECEIPT_EX / earlier STATE numbers) vs per-gross (executor caliber, this report)

| arm | window | unit-book net_ex bps/anchor | unit-book Sharpe | per-gross bps/anchor | per-gross Sharpe | mean gross_total |
|---|---|---|---|---|---|---|
| REF T400/log/42/def | 2024 | 0.149 | 0.53 | 0.636 | 1.41 | 0.602 |
| REF T400/log/42/def | 2025 | 0.359 | 1.15 | 0.701 | 1.26 | 0.531 |
| REF T400/log/42/def | 2026->cut | 2.512 | 4.83 | 3.209 | 4.84 | 0.780 |
| REF T400/log/42/def | 2024->26 | 0.780 | 2.16 | 1.260 | 2.30 | 0.617 |
| M1 PIT/prod/42/cal | 2024 | 0.107 | 0.45 | 0.557 | 1.24 | 0.550 |
| M1 PIT/prod/42/cal | 2025 | 0.203 | 0.67 | 0.651 | 1.14 | 0.500 |
| M1 PIT/prod/42/cal | 2026->cut | 2.510 | 4.94 | 3.189 | 4.96 | 0.782 |
| M1 PIT/prod/42/cal | 2024->26 | 0.704 | 2.05 | 1.206 | 2.21 | 0.585 |
| M1 PIT/prod/2027/cal | 2024 | 0.147 | 0.61 | 0.588 | 1.30 | 0.552 |
| M1 PIT/prod/2027/cal | 2025 | 0.268 | 0.86 | 0.767 | 1.34 | 0.521 |
| M1 PIT/prod/2027/cal | 2026->cut | 2.488 | 4.90 | 3.143 | 4.90 | 0.784 |
| M1 PIT/prod/2027/cal | 2024->26 | 0.739 | 2.13 | 1.252 | 2.29 | 0.595 |
| fixed-seat PIT/prod/42/cal | 2024 | -0.656 | -1.84 | -0.772 | -1.84 | 0.856 |
| fixed-seat PIT/prod/42/cal | 2025 | -0.152 | -0.37 | -0.109 | -0.21 | 0.783 |
| fixed-seat PIT/prod/42/cal | 2026->cut | 2.901 | 5.02 | 3.611 | 4.97 | 0.796 |
| fixed-seat PIT/prod/42/cal | 2024->26 | 0.366 | 0.83 | 0.503 | 0.92 | 0.814 |

### T12. 2026-08-11 → 2026-08-30 (after the F10 cut; F10 leg absent ⇒ NOT the live form; shown only because it overlaps the live window 08-26 →)

| arm | n anchors | mean bps/anchor/gross | Sharpe | NAV total % @2× | worst day % @2× |
|---|---|---|---|---|---|
| REF T400/log/42/def | 120 | -4.270 | -5.97 | -9.98 | -3.82 |
| M1 PIT/prod/42/def | 120 | -4.208 | -5.74 | -9.87 | -3.84 |
| M1 PIT/prod/42/cal | 120 | -4.164 | -5.68 | -9.77 | -3.84 |
| M1 PIT/prod/2027/def | 120 | -4.173 | -5.70 | -9.79 | -3.82 |
| M1 PIT/prod/2027/cal | 120 | -4.129 | -5.64 | -9.69 | -3.82 |
| M1 PIT/log/42/def | 120 | -4.460 | -5.88 | -10.43 | -3.91 |
| M1 PIT/log/42/cal | 120 | -4.416 | -5.82 | -10.33 | -3.91 |
| M1 PIT/log/2027/def | 120 | -4.392 | -5.79 | -10.28 | -3.92 |
| M1 PIT/log/2027/cal | 120 | -4.348 | -5.74 | -10.19 | -3.91 |
| M1 FRZ/prod/42/cal | 120 | -3.417 | -4.60 | -8.14 | -3.78 |
| M1 FRZ/prod/2027/cal | 120 | -3.323 | -4.47 | -7.94 | -3.76 |
| trade PIT/prod/42/cal | 120 | -4.340 | -5.87 | -10.15 | -3.82 |
| trade PIT/prod/2027/cal | 120 | -4.151 | -5.61 | -9.75 | -3.81 |
| trade PIT/prod/42/def | 120 | -4.383 | -5.93 | -10.25 | -3.82 |
| members PIT/prod/42/cal | 120 | -4.160 | -5.74 | -9.75 | -3.81 |
| members PIT/prod/2027/cal | 120 | -4.134 | -5.71 | -9.70 | -3.81 |
| fixed-seat PIT/prod/42/cal | 120 | -4.650 | -6.13 | -10.83 | -4.04 |
| fixed-seat PIT/prod/2027/cal | 120 | -4.600 | -6.06 | -10.73 | -4.03 |
| M1 PIT/prod/42/fee+slip | 120 | -4.080 | -5.56 | -9.59 | -3.83 |

### T13. 附加: 席位路径 — device seats vs the live seat (results/seat_compare.json)

**T13a. Live seat file alignment and proof** — {"source": "aug20260816_backup", "seed_rows": 836, "seed_first": "2026-03-28 20:00", "seed_last": "2026-08-15 00:00", "appended_rows_needed": 114, "consecutive_signal_rows_after_seed": 114, "first_signal_anchor": "2026-08-16 12:00", "last_signal_anchor": "2026-09-05 04:00", "method": "last <need> consecutive signal rows"}; proof (producer's own w3 reproduced from the aligned rows at every shadow_log signal anchor): {"n_anchors": 117, "max_abs_diff_w3_raw": 0.024588494441291964, "mean_abs_diff_w3_raw": 0.007339384299671577, "max_abs_diff_masked_king": 0.01841866436496309, "note": "producer prints w3 rounded to 4 decimals; a max diff <= 6e-5 means exact reproduction"}; live rows used 950 spanning ['2026-03-28 20:00', '2026-09-05 00:00']; file sha256 dd23827c0298ceeb.

**T13b. Seat trajectories (w3_king = king / (king + fund))**

| series | 2024-H1 | 2024-H2 | 2024 | 2025 | 2026 (to 08-30) | at 2026-08-10 20Z | at 2026-08-30 20Z | at last live anchor |
|---|---|---|---|---|---|---|---|---|
| device m1 (M1_UPIT_prod_s42_ccal) | 0.523 | 0.921 | 0.723 | 0.742 | 0.383 | 0.312 | 0.328 | — |
| device m1_s2027 (M1_UPIT_prod_s2027_ccal) | 0.523 | 0.921 | 0.723 | 0.742 | 0.383 | 0.312 | 0.328 | — |
| device trade (UPIT_prod_s42_ccal) | 0.421 | 0.941 | 0.682 | 0.687 | 0.375 | 0.295 | 0.296 | — |
| device members (MEM_UPIT_prod_s42_ccal) | 0.545 | 0.925 | 0.736 | 0.746 | 0.379 | 0.310 | 0.327 | — |
| device fixed (FIX_UPIT_prod_s42_ccal) | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | 0.210 | — |
| live (producer rows, reconstructed; ≥300 rows from 2026-05-17 20:00) | — | — | — | — | — | 0.214 | 0.215 | 0.194 (2026-09-05 04:00; producer printed 0.194, raw w3 [0.1696, 0.1247, 0.7057]) |
| v3 bundle rows (the package's own leg history, not what the producer's window holds) | — | — | — | — | — | — | 0.312 | — |

**T13c. Monthly mean seat on the overlap 2026-03 → 2026-09**

| month | producer_w3 | live_rows_reconstructed | v3_bundle_rows | device_m1 | device_m1_s2027 | device_trade | device_members | device_fixed |
|---|---|---|---|---|---|---|---|---|
| 2026-03 | — | — | 0.487 (n 186) | 0.479 (n 186) | 0.479 (n 186) | 0.501 (n 186) | 0.473 (n 186) | 0.210 (n 186) |
| 2026-04 | — | — | 0.458 (n 180) | 0.452 (n 180) | 0.452 (n 180) | 0.449 (n 180) | 0.447 (n 180) | 0.210 (n 180) |
| 2026-05 | — | 0.249 (n 85) | 0.380 (n 186) | 0.378 (n 186) | 0.378 (n 186) | 0.372 (n 186) | 0.372 (n 186) | 0.210 (n 186) |
| 2026-06 | — | 0.175 (n 180) | 0.303 (n 180) | 0.290 (n 180) | 0.290 (n 180) | 0.289 (n 180) | 0.287 (n 180) | 0.210 (n 180) |
| 2026-07 | — | 0.238 (n 186) | 0.310 (n 186) | 0.299 (n 186) | 0.299 (n 186) | 0.294 (n 186) | 0.297 (n 186) | 0.210 (n 186) |
| 2026-08 | 0.226 (n 91) | 0.225 (n 186) | 0.306 (n 186) | 0.311 (n 180) | 0.311 (n 180) | 0.291 (n 180) | 0.310 (n 180) | 0.210 (n 180) |
| 2026-09 | 0.208 (n 26) | 0.208 (n 26) | 0.323 (n 26) | — | — | — | — | — |

**T13d. Per-leg statistics over the common window 2026-03-01 → 2026-08-30 20Z (bps/anchor of the unit-gross rank book; Sharpe annualised √2190)**

| history | n | king mean | king Sharpe | fund mean | fund Sharpe | corr king vs live rows | corr fund vs live rows |
|---|---|---|---|---|---|---|---|
| live_rows | 919 | 1.772 | 2.86 | 6.434 | 9.34 | — | — |
| v3_bundle_rows | 1098 | 2.810 | 4.57 | 6.257 | 9.39 | — | — |
| device_m1 | 1098 | 2.877 | 4.67 | 5.283 | 9.01 | 0.734 | 0.886 |
| device_members | 1098 | 2.877 | 4.67 | 5.208 | 9.08 | 0.734 | 0.886 |

**T13e. Trailing-900 decomposition of the seat (what the msharpe rule sees) at 2026-08-31 00Z and at the last live anchor**

| history | king mean bps | king std | king shp/anchor | fund mean bps | fund std | fund shp/anchor | seat = king/(king+fund) |
|---|---|---|---|---|---|---|---|
| live_rows @2026-08-31 00Z | 1.592 | 29.17 | 0.0546 | 6.504 | 32.29 | 0.2015 | 0.2131 |
| v3_bundle_rows @2026-08-31 00Z | 2.828 | 29.65 | 0.0954 | 6.425 | 32.11 | 0.2001 | 0.3228 |
| device_m1 @2026-08-31 00Z | 2.908 | 29.93 | 0.0972 | 5.325 | 28.30 | 0.1882 | 0.3405 |
| device_members @2026-08-31 00Z | 2.908 | 29.93 | 0.0972 | 5.271 | 27.83 | 0.1894 | 0.3391 |
| live rows @2026-09-05 04:00 | 1.341 | 28.55 | 0.0470 | 6.256 | 32.01 | 0.1954 | 0.1937 |

### T14. Receipts

- `calib/costb_fee_steady.json` sha256[:16] 9349ca634747772d: tiers tier0_qv4h>=5e6: maker 1.8001 / taker 4.5001 bps, maker share 0.8511; tier1_qv4h>=1e6: maker 1.799 / taker 4.4988 bps, maker share 0.9246; tier2_rest: maker 1.7998 / taker 4.5002 bps, maker share 0.921. Source: cost_calib.json alternatives.steady_fee_only (steady 51 anchors 08-26 04Z -> 09-05 00Z; VERIFIED venue fees maker 1.80 / taker 4.50 bps with BNB discount; maker_share per tier = share of filled notional); binding per team-lead 2026-09-05 resolution. cost_calib.json sha256 980384ccce31ffc3….
- `calib/costb_feeslip_steady.json` sha256[:16] 43b7aa4aa173e595: tiers tier0_qv4h>=5e6: maker -2.4141 / taker 16.7919 bps, maker share 0.8511; tier1_qv4h>=1e6: maker -2.4382 / taker 16.7905 bps, maker share 0.9246; tier2_rest: maker -1.9323 / taker 16.792 bps, maker share 0.921. Source: cost_calib.json tiers[] = venue fee minus notional-weighted fill improvement vs the executor's own anchor mid (bookTicker mid at N+24 min; maker fills beat it by +3.9 bps CI [3.5, 4.5]; taker top-ups lose 12.3 bps CI [2.8, 21.3], pooled across tiers); SENSITIVITY ARM ONLY (team-lead resolution 2026-09-05); does not contain the nominal-grid -> venue-moment timing decay. cost_calib.json sha256 980384ccce31ffc3….
- Live book (cost-calib): {"maker_bps": -2.1211543349221844, "taker_bps": 16.791636221433123, "maker_share": 0.9128114176784381, "fill_ratio": 0.8481039083935302, "fill_ratio_after_topup": 0.9291118537392103, "cost_per_unit_turnover_bps": -0.4721749385689411, "turnover_per_anchor": 0.04549509156956227}; twin band: {"real_minus_paper_shifted_bps_per_anchor": 1.23, "ci95": [-3.72, 6.1], "n": 53, "twin_plus_funding_bps_per_anchor": 0.26, "ci95_tf": [-8.5, 8.91], "paper_nominal_minus_paper_shifted_bps_per_anchor": 2.85}; not used in the device: {"fee_plus_slippage_vs_anchor_mid (cost-calib tiers[])": [[-2.414, 16.792, 0.8511], [-2.438, 16.791, 0.9246], [-1.932, 16.792, 0.921]], "fee_minus_markout60_INFERRED": [[15.994487089823684, 73.27306826476746, 0.8511411862710598], [12.67495698586448, 2.5095534187378283, 0.9246422006649931], [-2.4192923680519813, 6.652850850356973, 0.9209652191948581]], "device_default": [[-0.25, 5.0, 0.85], [0.5, 6.0, 0.75], [2.0, 8.0, 0.55]]}.

`logs/check_equiv.log`:
```
PASS [pristine 5424aceb vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_pristine_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=5cd88da0ab1301b9 sha(ref)=b20ec4fba5695d51
PASS [w10_health.py default path vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=8bfe59b6ebc0a8c4 sha(ref)=b20ec4fba5695d51
CHAIN_EQ_DONE 2026-09-05T04:38:13Z
PASS [w10_health.py (m1 branch + legs saved) default path vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_patched2_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=5bc88b29ea8bc647 sha(ref)=b20ec4fba5695d51
```

`logs/chain_all.log`:
```
ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece  masks/umask_UPIT.npz
70470dbdb5e4c1870fa07ca025a6eba699bcf7daf5406e8305a70a50491222fa  masks/umask_UFROZEN.npz
e1c31393bb0d994debc9bd0347aba3c91867db9bdb6c54ae78912554bd499fc7  masks/btc_rv30.npz
ddb07d3c5b294bfaa8bc48148b64bac23db17c4e90c5f70108c3c0e92e53df27  calib/costb_fee_steady.json
METRICS rc=0 2026-09-05T04:51:22Z
e0f51864cb9c8fa1b394fd0365a80675cf32fb33813a9b1070796651708fb6b4  dev/probe_artifacts/w10_ablation_series_UPIT_log_s2027_ccal.npz
6d4b7d260a9121f222598f87a63b467b7df13be7417b78831113193be71ef175  dev/probe_artifacts/w10_ablation_series_UPIT_log_s2027_cdef.npz
33630cb0ac2b2f30526b71e8424553ec54af3f04f94325ca11688ef94957ba81  dev/probe_artifacts/w10_ablation_series_UPIT_log_s42_ccal.npz
be14ec12e4baf71c521b1f70bf01aa4395aff4366b2b194c3a93c4aab8f3563e  dev/probe_artifacts/w10_ablation_series_UPIT_log_s42_cdef.npz
8bfe59b6ebc0a8c49e81b08c6022b598db35af9f7cc40c6a0eb64349f65acdab  dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz
5cd88da0ab1301b97319edb5128d2edbd87ad92c38b1b4f5880e41554b9624b3  dev/probe_artifacts/w10_ablation_series_eq_pristine_pinned_log_s42.npz
f409a5fc62f61e3934c970ad5dc68727e12d481e311c5074c8629ffb80efb4b9  dev_alt/probe_artifacts/w10_ablation_series_UFROZEN_prod_s2027_ccal.npz
a146115af2fba0adb78323c8a63a9ba9c1cb82ce7d065aec6a68abd16d9edc98  dev_alt/probe_artifacts/w10_ablation_series_UFROZEN_prod_s42_ccal.npz
5ab79a6536dd379715a8015405fc3390406574829f5e1e145358de2979211d85  dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s2027_ccal.npz
d40e816f29c2920b792957e8a506932e10c174bcadae1f6f2adcaa3d0fd32f8d  dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s2027_cdef.npz
70dfe7512520784f5cf641738e24354715ac746227de6ba21086eca38dc2fdcc  dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s42_ccal.npz
62ee9fa387e61e9db3e9fc6a9690a1f7b8825b09d098ebe67e990339e8ebb933  dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s42_cdef.npz
1f2801daa8340ea7059cc31739e290e61f58ebf96d7c907a7678b86f0b0998a6  results/UFROZEN_prod_s2027_ccal.json
170fa29fcafe67782f15dc9b152cf849f0ac81ad13768c302a8e9d791e36d0e2  results/UFROZEN_prod_s42_ccal.json
64fa6328ffda3ed5cdf4a2bd6e3ba8c1347d9562365b77f039c908b09e44e42d  results/UPIT_log_s2027_ccal.json
f6280ea7a5def6a5497c32befd6b680ca2d18e52251c36d0924ffdb636709da7  results/UPIT_log_s2027_cdef.json
7251af9597c3c49dc057f63ea18458f584317328836280892c34b56df737a3ab  results/UPIT_log_s42_ccal.json
d5e6881b12d083868085ac4baa5442f396637d2f362a3f3d0c3903920a033993  results/UPIT_log_s42_cdef.json
8053b97607c5004105b75acf2eb606f04edea7ebab733853bcb5eecdd214f27a  results/UPIT_prod_s2027_ccal.json
127ef99da892bbf060cb054ba0eb3cb982993d8bb7909146de974fe4ef4544a7  results/UPIT_prod_s2027_cdef.json
9fc78224998832d53dc2fad73f75c239550c5f6c8916441c6b727ab776a4ff9d  results/UPIT_prod_s42_ccal.json
a1444dc3f681ead47bd1b9d0439f441908b671c9cc75109535710e26910d73d3  results/UPIT_prod_s42_cdef.json
19ee945bd238038ab8e360ea0c9093619da6ceadd25b811f8b278b8315639b9a  results/eq_patched_pinned_log_s42.json
CHAIN_ALL_DONE 2026-09-05T04:51:22Z
```

`logs/chain_m1.log`:
```
8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d  w10_health.py
9349ca634747772dcfc9adfb7a42a5c7b5b34f60bc7f31bc6fd95c4ae5d0fc42  calib/costb_fee_steady.json
43b7aa4aa173e5950695fe24fd69c5491eb34364f8f9d271cd792192dfa519ed  calib/costb_feeslip_steady.json
980384ccce31ffc3d0448e9405e84ce6687d1817c52f925391c5322cf27113ad  calib/cost_calib.json
ccb7a0805be2a106898467b5ffef3a8fd4813a659e044492c0a437b0e5d7aece  masks/umask_UPIT.npz
70470dbdb5e4c1870fa07ca025a6eba699bcf7daf5406e8305a70a50491222fa  masks/umask_UFROZEN.npz
METRICS_M1 rc=0 2026-09-05T05:20:17Z
10e64fdb56a62e378fda1631f484e7bde180a7dc0ff5c1e124f92ed8ddbbedd5  dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s2027_ccal.npz
c55f71dcd1bd44f9ac20576ea033e55559a9da8193ea32979782a8fba93dacf2  dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s2027_cdef.npz
d0a51738b9c7cb1c94ecb1019136b6fbb48bc8adb64a2a3b0edcee70f2de573d  dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s42_ccal.npz
f8d7adde00510a3a2519eee5a488aa79f8658668eef52e56c34e2066f709109e  dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s42_cdef.npz
9ac04705fff7bbc74981eaaab4888fa298ce2c9c2d163c5a16a0b3983837cea5  dev_alt/probe_artifacts/w10_ablation_series_M1_UFROZEN_prod_s2027_ccal.npz
6c7935d398140d2fa1dd52d1aec4e8b2ee4c88c16d54c788571ffcd9b9adb8e7  dev_alt/probe_artifacts/w10_ablation_series_M1_UFROZEN_prod_s42_ccal.npz
a2c5ec76dfac990b900fe787138bacec93a952c48cf18a72a760b5a7ae4a1266  dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_ccal.npz
733df8e7d0aa4a55b25e03a2f0d96d03e14cf9a1116bfaae2b1faca595ce825e  dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s2027_cdef.npz
32bfecb9cf9c0e5caebd4d77ad3ee5cf8334be3e75bf04b2cd66cb8550d9d12a  dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz
1a7697d71c2bfa5352e98c5d1b8da9588c2f5783dce7c31e5633764046f1eb92  dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_cdef.npz
48ddb121c4c6e00c916762a7d2716314e39efd4fe31edf2a9b557a6e53b5d2bd  dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_cslip.npz
44b862686bd9c1fa16bb10ddba5b5140c2b5ed09c0997639b376edf065dfea34  dev_alt/probe_artifacts/w10_ablation_series_MEM_UPIT_prod_s2027_ccal.npz
5b9fca02e1fe24d2c5e90846769105b7ac40b23cec88aeec89d834ecc49b8823  dev_alt/probe_artifacts/w10_ablation_series_MEM_UPIT_prod_s42_ccal.npz
f5b7c6d1cb8f14240610d25e23458c68283a2c0dc636c6f1a7826be054197e27  dev_alt/probe_artifacts/w10_ablation_series_FIX_UPIT_prod_s2027_ccal.npz
86e896df5460a783aa394ad178e5625bc53733ade08016df9f20e4d3fa7917f3  dev_alt/probe_artifacts/w10_ablation_series_FIX_UPIT_prod_s42_ccal.npz
fdf9093fbfe41e5f8891483f849ed4df2fa366ae5a0b2c05627fe94100afc575  results/M1_UFROZEN_prod_s2027_ccal.json
5ffa45c0422be2db06e1a31a8fd5f4365886820117acc92ec9a91feb6cb0bc49  results/M1_UFROZEN_prod_s42_ccal.json
1498a220a4289d1f6a3b2cf01183878cf917cb0b69fa8156ce3ffc1ae0dd6ebd  results/M1_UPIT_log_s2027_ccal.json
18cfb1120d59ccfb7da2f21ba9107d021f53d63741aa4db365947ff17b8fe9c2  results/M1_UPIT_log_s2027_cdef.json
aedf0fb32e2b66ca772ef45685f4e9d1050b5aaf76a413f3d600e5a870bd9c3e  results/M1_UPIT_log_s42_ccal.json
c35e92bca5a5726dbae897ea024ae47ac55eb6d56c962305d543ca73902ce8ca  results/M1_UPIT_log_s42_cdef.json
766e25a5b81fd7df7b584c139015dffd6c7640ade399f0da6c7ffd64a4876329  results/M1_UPIT_prod_s2027_ccal.json
60b51f3664819d1498037e2c604ac1d29eea66e5da3b31567a11e9a3c3b159f1  results/M1_UPIT_prod_s2027_cdef.json
db4e5aefce2c33bac9888076396f1e275244b7e35d4fc85615a269a79ea824ba  results/M1_UPIT_prod_s42_ccal.json
5de9fb2301d2167daaceb2b4f48da6d37e57d97583c22c2d7794f8f37846120d  results/M1_UPIT_prod_s42_cdef.json
8927634ddd38e0dfd918e5f65dbbe25053b980c432dca3ca9b7ec23bdbbaaa64  results/M1_UPIT_prod_s42_cslip.json
a55006f421be44749ac8beb74b135a51eaaaf77c1930b1ba9b92b62a2fbd8777  results/MEM_UPIT_prod_s2027_ccal.json
9f6f18a865d55715a1aa8efb671cf4783038f08f23f8c5c047c03a6fb7e77476  results/MEM_UPIT_prod_s42_ccal.json
c3dc049b44aca359dc218d703323946223706c80dcb6b481c61242592386dc9d  results/FIX_UPIT_prod_s2027_ccal.json
c19ca95a373e11ff1211cffce5872f3db8209a0f44cacf12960734cc9dc8787b  results/FIX_UPIT_prod_s42_ccal.json
CHAIN_M1_DONE 2026-09-05T05:20:18Z
METRICS_FINAL2 rc=0 2026-09-05T05:35:27Z
```

`logs/commands.txt` (every device run, verbatim):
```
CMD[eq_patched_pinned_log_s42] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:37:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=eq_patched_pinned_log_s42 /workspace/venv/bin/python ../w10_health.py
CMD[eq_pristine_pinned_log_s42] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:37:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=eq_pristine_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
END[eq_patched_pinned_log_s42] rc=0 2026-09-05T04:38:10Z
END[eq_pristine_pinned_log_s42] rc=0 2026-09-05T04:38:10Z
CMD[UPIT_log_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:44:12Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_log_s42_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_log_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:44:12Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_log_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:44:12Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_prod_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:44:12Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_prod_s42_cdef /workspace/venv/bin/python ../w10_health.py
END[UPIT_log_s42_cdef] rc=0 2026-09-05T04:44:46Z
END[UPIT_prod_s42_cdef] rc=0 2026-09-05T04:44:46Z
END[UPIT_prod_s2027_cdef] rc=0 2026-09-05T04:44:46Z
END[UPIT_log_s2027_cdef] rc=0 2026-09-05T04:44:46Z
CMD[UPIT_log_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_log_s42_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_log_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UPIT_log_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_log_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UPIT_log_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UPIT_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_log_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_log_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_prod_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UFROZEN_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UFROZEN.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UFROZEN_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[UFROZEN_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UFROZEN.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UFROZEN_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=42 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=UPIT_prod_s42_cdef /workspace/venv/bin/python ../w10_health.py
CMD[UPIT_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T04:50:30Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade FSEED=2027 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=UPIT_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
END[UPIT_log_s2027_ccal] rc=0 2026-09-05T04:51:04Z
END[UPIT_log_s42_cdef] rc=0 2026-09-05T04:51:04Z
END[UPIT_log_s2027_cdef] rc=0 2026-09-05T04:51:04Z
END[UPIT_log_s42_ccal] rc=0 2026-09-05T04:51:05Z
END[UPIT_prod_s42_cdef] rc=0 2026-09-05T04:51:05Z
END[UPIT_prod_s2027_ccal] rc=0 2026-09-05T04:51:05Z
END[UFROZEN_prod_s42_ccal] rc=0 2026-09-05T04:51:05Z
END[UFROZEN_prod_s2027_ccal] rc=0 2026-09-05T04:51:05Z
END[UPIT_prod_s42_ccal] rc=0 2026-09-05T04:51:05Z
END[UPIT_prod_s2027_cdef] rc=0 2026-09-05T04:51:05Z
CMD[eq_patched2_pinned_log_s42] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T05:18:53Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=eq_patched2_pinned_log_s42 /workspace/venv/bin/python ../w10_health.py
END[eq_patched2_pinned_log_s42] rc=0 2026-09-05T05:19:25Z
CMD[M1_UPIT_log_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=M1_UPIT_log_s42_cdef /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_prod_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=M1_UPIT_prod_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_prod_s42_cdef] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=M1_UPIT_prod_s42_cdef /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_log_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UPIT_log_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UPIT_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_prod_s42_cslip] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_feeslip_steady.json OUT_TAG=M1_UPIT_prod_s42_cslip /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_log_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UPIT_log_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_log_s2027_cdef] (cwd=/workspace/review_scratch/health_check/dev) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz OUT_TAG=M1_UPIT_log_s2027_cdef /workspace/venv/bin/python ../w10_health.py
CMD[M1_UPIT_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UPIT_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_UFROZEN_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UFROZEN.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UFROZEN_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_UFROZEN_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UFROZEN.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=M1_UFROZEN_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[MEM_UPIT_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=members UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=MEM_UPIT_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
CMD[FIX_UPIT_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json W3FIX=0.21,0,0.79 OUT_TAG=FIX_UPIT_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[MEM_UPIT_prod_s42_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=members UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=MEM_UPIT_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[FIX_UPIT_prod_s2027_ccal] (cwd=/workspace/review_scratch/health_check/dev_alt) 2026-09-05T05:19:26Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=2027 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json W3FIX=0.21,0,0.79 OUT_TAG=FIX_UPIT_prod_s2027_ccal /workspace/venv/bin/python ../w10_health.py
END[FIX_UPIT_prod_s42_ccal] rc=0 2026-09-05T05:19:54Z
END[FIX_UPIT_prod_s2027_ccal] rc=0 2026-09-05T05:19:55Z
END[MEM_UPIT_prod_s42_ccal] rc=0 2026-09-05T05:19:56Z
END[MEM_UPIT_prod_s2027_ccal] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_log_s42_cdef] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_prod_s2027_ccal] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_prod_s42_cslip] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_prod_s42_cdef] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_log_s42_ccal] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_log_s2027_ccal] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_prod_s2027_cdef] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_prod_s42_ccal] rc=0 2026-09-05T05:19:56Z
END[M1_UPIT_log_s2027_cdef] rc=0 2026-09-05T05:19:56Z
END[M1_UFROZEN_prod_s42_ccal] rc=0 2026-09-05T05:19:57Z
END[M1_UFROZEN_prod_s2027_ccal] rc=0 2026-09-05T05:19:58Z
```
