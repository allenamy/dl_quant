> **创建:** 2026-09-05 04:3xZ – 05:0xZ UTC | **Session:** b9646a9e, teammate `health-check` | **状态:** complete — numbers only, **no admission verdict** (PREREG §3 "不做任何录取判决; 只报数字") | **预注册:** `docs/PREREG_live_form_health_check_2026-09-05.md` (§0–§4 followed literally; 10 device runs, none added or removed after numbers) | **作废条件:** device default path not bitwise-equal to the axisB reference (checked: PASS ×2, §T13); any change of the mask files, `cost_calib.json`, the pinned king, the F10 preds or the metas (sha256 in §T1/§T13/§10); any metric or window changed after numbers (none). **[单仪器 pod2]** — every number below comes from the pod port device only. Labels: **VERIFIED** = printed by a script quoted in §T13; **INFERRED** = derived from verified numbers with the reasoning stated; **UNRESOLVED** = not established here.

# Live-form full-history strict-causal health check — U-PIT universe, dynamic seat, FTRIM, M1 rank base, live fee-only cost, 2.0× / 2.5× / 3.0×

Read-only on `/workspace/data`, `/workspace/shadow_bundle_v3`, `/workspace/port_w10`, `/workspace/review_scratch/{rolling_king,combo_recheck,cadence_seats,jpline_rebuild,refute_*}`; writes only under `/workspace/review_scratch/health_check/` (pod) and `…/scratchpad/review_caliber/health_check/` (Mac). No live-machine contact; no GPU.

## 0. What this is, in one paragraph

The live book (combo: rev24 leg off, king 55 / V2MAIN 45, FTRIM, M1 wider fund rank base, per-name stop d30_n2_c42, executor re-demean and constant gross 2.0×NAV) was replayed from 2022-01-31 to 2026-08-30 with the pod port device, strictly causal: yearly out-of-sample king (`slow_pred_pinned.npy`), walk-forward F10 predictions with a 60-anchor embargo, the seat produced by the device itself from its own out-of-sample leg returns, a point-in-time universe rebuilt every month from trailing 30-day quote volume, and execution cost taken from the live fills of 08-26 → 09-05. Ten device runs (PREREG §3): U-PIT × {prod, log} × {s42, s2027} × {live fee-only cost, device default cost} = 8, plus U-FROZEN (today's 449 list projected back — look-ahead, upper bound only) × prod × {s42, s2027} × live cost = 2. Leverage is a post-hoc mapping of the same anchor series (NAV return = net per unit gross × L). All metrics of PREREG §2 are in §T3–§T12; this head only reads them out.

## 1. Bottom line (primary arms = U-PIT, prod caliber, live fee-only cost, seeds s42 / s2027; VERIFIED from results/UPIT_prod_s{42,2027}_ccal.json)

| window | net bps/anchor per gross [CI95] | anchor Sharpe [CI95] | NAV %/yr at 2.0× (arith) | CAGR at 2.0× | max DD at 2.0× | worst day at 2.0× | days < −2% / < −5% (of n) |
|---|---|---|---|---|---|---|---|
| 2024 (incl. H1 warm-up) | +0.69 [−0.18, +1.61] / +0.75 [−0.11, +1.67] | 1.55 / 1.70 (CI includes 0) | +30.3 / +33.0 | +32.8 / +36.6 | 22.1 / 20.9 % | −3.50 / −3.44 % | 8 / 0 · 7 / 0 (366) |
| 2024-H1 ⚠ seat warm-up | −0.30 / −0.24 | −0.74 / −0.59 | −13.2 / −10.6 | −13.8 / −11.5 | 16.3 / 15.8 % | −3.50 / −3.44 % | 2 / 0 · 2 / 0 (182) |
| 2024-H2 | +1.67 [+0.40, +3.02] / +1.74 [+0.47, +3.08] | 3.52 / 3.68 | +73.3 / +76.2 | +103.6 / +109.8 | 9.8 / 9.2 % | −3.01 / −2.69 % | 6 / 0 · 5 / 0 (184) |
| 2025 | +0.38 [−0.65, +1.46] / +0.45 [−0.58, +1.49] | 0.69 / 0.81 (CI includes 0) | +16.8 / +19.6 | +14.8 / +18.1 | 20.1 / 17.5 % | −4.93 / −4.20 % | 20 / 0 · 20 / 0 (365) |
| 2026 → 08-10 | +3.28 [+1.77, +4.82] / +3.19 [+1.69, +4.74] | 5.06 / 4.95 | +143.4 / +139.8 | +303 / +289 (7.3 months: total +133 / +128 %) | 8.4 / 8.1 % | −3.95 / −4.03 % | 7 / 0 · 8 / 0 (222) |
| 2024 → 26 | **+1.18 [+0.54, +1.87] / +1.20 [+0.57, +1.90]** | **2.18 [1.00, 3.45] / 2.23 [1.06, 3.52]** | **+51.5 / +52.8** | **+62.7 / +64.8** | **22.1 / 20.9 %** | −4.93 / −4.20 % | 35 / 0 · 35 / 0 (953) |
| 2025 → 26 | +1.48 [+0.58, +2.39] / +1.49 [+0.61, +2.37] | 2.50 / 2.51 | +64.7 / +65.1 | +84.6 / +85.3 | 20.1 / 17.5 % | −4.93 / −4.20 % | 27 / 0 · 28 / 0 (587) |

Plain reading. Over the full evaluation window (2024-01-01 → 2026-08-10, 5,718 anchors, 953 UTC days) the replayed live form earns about 1.2 bps per anchor per unit gross, which at the live 2.0× gross is about 51–53 % of NAV per year arithmetic (63–65 % compounded), with a 21–22 % max drawdown that took about 285 days to recover, a worst single day of −4.2 to −4.9 %, and no day worse than −5 %. The confidence interval of the mean excludes zero for 2024→26, 2025→26, 2024-H2 and 2026, but **not for the calendar years 2024 and 2025 taken alone**: 2024 is dragged by the seat warm-up half (H1 −13 %/yr at 2×), and 2025 is a weak year (+15–18 % compounded at 2×, Sharpe 0.7–0.8) whose worst month (2025-04, −17.6 / −15.2 % at 2×) started a drawdown that only recovered after about a year (2025→26 max-DD span 364 / 331 days, §T5). 2026 to the cut is exceptional (+3.2–3.3 bps per anchor, Sharpe ~5) and dominates every multi-year average: 2024→26 without 2026 would be the 2024–2025 pair above. Negative quarters, explicitly (§T6, 2× total return): 2024-Q2 −11.7 / −11.1 %, 2025-Q2 −15.3 / −11.2 %, 2025-Q4 −0.3 / −1.8 %. Negative months (§T7): 10 / 8 of 32.

## 2. Leverage (§T5; primary arms, 2024→26 unless stated)

| L | arith %/yr | CAGR % | vol %/yr | max DD % (span days) | worst day % | worst week % | worst month % (2025-04) | days < −2 % / < −5 % / < −10 % of 953 | 8-anchor worst % | daily VaR99 / CVaR99 % | min equity/gross vs 1.5 % maintenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 51.5 / 52.8 | 62.7 / 64.8 | 23.7 | 22.1 / 20.9 (287 / 284) | −4.93 / −4.20 | −11.8 / −11.4 | −17.6 / −15.2 | 35 / 0 / 0 · 35 / 0 / 0 | −7.5 / −7.9 | −3.05 / −3.66 · −2.92 / −3.79 | 0.48 (0 touches) |
| 2.5 | 64.3 / 66.0 | 82.1 / 85.1 | 29.6 | 27.0 / 25.6 (288 / 284) | −6.13 / −5.23 | −14.6 / −14.1 | −21.6 / −18.8 | 67 / 1 / 0 · 62 / 5 / 0 | −9.4 / −9.9 | −3.81 / −4.56 · −3.65 / −4.72 | 0.38 (0) |
| 3.0 | 77.2 / 79.1 | 103.2 / 107.2 | 35.5 | 31.7 / 30.1 (291 / 284) | −7.33 / −6.25 | −17.3 / −16.7 | −25.5 / −22.2 | 87 / 6 / 0 · 89 / 9 / 0 | −11.4 / −12.0 | −4.57 / −5.47 · −4.37 / −5.66 | 0.31 (0) |

Plain reading. Leverage scales the mean and the tails together: at 3× the same history gives a 30–32 % max drawdown, a worst week of −17 %, a worst month of −22 to −25 %, and 6–9 days worse than −5 % (there are none at 2×). Liquidation is never approached: with gross reset to L×NAV at every anchor the equity/gross ratio at the end of the worst anchor is 0.48 / 0.38 / 0.31 against a 1.5 % maintenance line, and the worst 8-anchor stretch (−7.5 to −12 % of NAV) does not change that. The rolling 90-day daily Sharpe over 2024→26 has p5 / median / p95 = −2.1 / 1.1 / 6.4 (s42) and −1.9 / 1.3 / 6.4 (s2027): one quarter in twenty looks like a Sharpe −2 quarter, and the median quarter is ≈ 1.2, well below the full-window 2.2 that the 2026 stretch produces. Anchor Sharpe, Sortino and the day-count shares are leverage-invariant by construction (they change only through compounding), so the choice of L is a choice of drawdown and tail size, not of quality.

## 3. Regimes (§T8; 2024→cut; primary arms s42 / s2027; net bps/anchor per gross [CI95])

| slice (definition in §T8) | low tercile | mid tercile | high tercile |
|---|---|---|---|
| σ_fund, descriptive terciles (cuts 5.3 / 13.7 bps per 8h) | +0.46 [−0.51, +1.42] / +0.47 (σ mean 3.2) | +1.37 [+0.22, +2.51] / +1.37 (9.4) | +1.69 [+0.40, +2.94] / +1.77 (21.2) |
| σ_fund, causal expanding cuts (3.4 / 9.4 at window end) | +1.09 [−0.41, +2.61] / +0.98, n 553 | −0.09 [−1.32, +1.21] / −0.03, n 1,230 | +1.58 [+0.79, +2.39] / +1.62, n 3,935 |
| breadth = nsel, descriptive (cuts 266 / 330 names) | +0.58 [−0.38, +1.48] / +0.61 (249) | +1.99 [+0.73, +3.24] / +2.06 (299) | +0.95 [−0.23, +2.14] / +0.93 (366) |
| negative-funding share, descriptive (cuts 0.12 / 0.26) | +0.66 [−0.41, +1.77] / +0.60 (0.05) | +1.57 [+0.40, +2.75] / +1.62 (0.19) | +1.30 [+0.08, +2.40] / +1.40 (0.34) |
| BTC 30-day realised vol, descriptive (cuts 41 / 53 %) | +0.96 [−0.11, +2.05] / +1.00 (35 %) | +1.39 [+0.19, +2.63] / +1.48 (48 %) | +1.18 [+0.22, +2.23] / +1.13 (61 %) |

Plain reading. The book earns when funding rates are dispersed: the lowest-dispersion third of anchors (σ_fund ≈ 3 bps per 8h) returns +0.46 bps per anchor with a confidence interval that includes zero (≈ +20 %/yr at 2×), the middle and upper thirds +1.4 to +1.8 (≈ 60–80 %/yr at 2×) with intervals above zero. Under the causal expanding cuts the picture is the same but sharper: the mid bucket (σ_fund ≈ 3.8) is flat at −0.1 / 0.0 over 1,230 anchors. Breadth is not monotonic (mid tercile best, consistent with `AUDIT_live_vs_replay_2026-09-04` §6); the causal breadth terciles are degenerate because tradeable names trend upward through the history (all but 358 of the 2024+ anchors fall in the "high" bucket) and are reported only for completeness. The share of negative-funding names helps mildly (low bucket weakest, interval includes zero). BTC volatility does not matter. Note for the reader of `regime_dash.py`: that script has no breadth ("宽/窄档") definition (its bands are σ_fund / short-interval share / deep-negative share; `regime_hist_pct.json` carries n_elig percentiles 144 / 197 / 350 that the dash never computes), so breadth here is nsel terciles, stated as such.

## 4. Cost, carry, turnover (§T9, §T9b; primary arms 2024→26)

| item | value | label |
|---|---|---|
| turnover per anchor, fraction of gross | 0.072 / 0.068 (2026: 0.034 / 0.036; live steady mean 0.048, median 0.042 — cost-calib §7) | VERIFIED |
| cost with the live fee-only tiers (maker 1.80 / taker 4.50 bps, maker share 0.85–0.92) | 0.151 / 0.143 bps per anchor per gross = 6.6 / 6.3 % of NAV per year at 2× | VERIFIED |
| cost with the device default tiers | 0.195 / 0.182 = 8.5 / 8.0 % of NAV per year at 2× ⇒ the calibrated arm nets +0.04 bps per anchor more (§T9b) | VERIFIED |
| carry paid (funding, replay = panel rate × 4/interval) | 0.55 / 0.56 bps per anchor per gross = 24 % of NAV per year at 2×; 33 % of the gross price P&L | VERIFIED |
| gross price P&L | 1.87 / 1.90 bps per anchor per gross; net = price − carry − cost | VERIFIED |
| **markout sensitivity (not a device run)**: the INFERRED fee-minus-markout vector of cost-calib §8 is 12.34 (raw) / 12.82 (delay-reweighted) bps per unit turnover pooled vs 2.035 fee-only ⇒ +10.3 / +10.8 bps per unit turnover × turnover 0.072 = **+0.74 / +0.78 bps per anchor per gross of extra cost** (2025→26 at 0.066: +0.68 / +0.71; 2026 at 0.034: +0.35 / +0.37) | if real, 2024→26 net falls from +1.18 to ≈ +0.42 and the 2× arithmetic NAV from 51 % to ≈ 18 % per year | INFERRED (68 / 134 / 128 maker marks; taker leg on 9 / 10 / 2 marks; 5 % non-random coverage) |
| twin band (paper target vs real positions, VERIFIED, n = 53 live anchors, cost-calib §9) | paper(shifted 25 min) − twin = −1.23 bps per anchor of gross, CI95 [−6.10, +3.72]: the real positions' price P&L was 1.2 bps per anchor **better** than the paper book, i.e. the markout-implied drag is not visible in the live book, but a drag of up to ~6 bps per anchor cannot be excluded at n = 53 | VERIFIED, wide |

Plain reading. The cost the replay charges (fees only, 6–7 % of NAV per year at 2×) is what the live fills actually paid; whether there is an additional adverse-selection cost is **UNRESOLVED**: the markout sample says there might be a large one, the live paper-vs-real reconciliation says there is none so far, and neither instrument can decide it at 53 anchors (the STATE.md audit of 09-04 puts the resolution at ≈ 350 anchors). This is the single largest open item behind every NAV number in this report. Carry is a real and stable drain: a quarter of NAV per year at 2×, paid mostly on the long side.

## 5. Seeds, calibers, universes (§T3, §T9c)

- **Seeds** (F10 s42 vs s2027): every window within 0.07 bps per anchor; no seed effect.
- **Caliber** (prod = exchange-style Π(1+r)−1 vs log = Σ of 5-minute simple returns): 2024→26 prod +1.175 / +1.204 vs log +1.152 / +1.210 — within 0.03 bps; 2025 prod slightly lower (+0.38 vs +0.42), 2024 slightly higher. The 7–10 % "log overstatement" quoted in PREREG §0 was the CAL=simple pseudo-convexity (E-0904-F), which both calibers here avoid.
- **U-FROZEN vs U-PIT** (prod, live cost): +0.24 / +0.31 bps per anchor over 2024→26 and +0.39 / +0.45 over 2025→26, all of it in 2025 (+0.50 / +0.59) and 2026 (+0.20 / +0.22), none in 2024. This is the look-ahead in today's 449 list (names that turned out to be liquid winners), **not** an edge available to the live frozen list going forward. U-FROZEN also has the worse 2024 tail (max DD 26.2 %, worst day −5.33 % at 2×, one day below −5 %) because early in the history its tradeable set is thin (94 / 125 / 182 names in 2022 / 2023 / 2024, §T2).
- **U-PIT vs the M1+T400 reference form** (REF row, log/s42, default cost; the form of the 09-04 caliber revalidation): 2024→26 +1.11 (PIT log/42/def) vs +1.26 (REF); the U-PIT trade set is narrower than top-400-by-qvk in 2025 (354 vs 375 names) and in 2026 (299 vs 328), and the difference is inside the seed-and-caliber noise.

## 6. Caliber reconciliation with the earlier receipts (§T11)

The REF row reproduces the STATE.md 09-04 numbers exactly in the unit-book caliber: net_ex 2024 / 2025 = +0.149 / +0.359 bps per anchor, Sharpe 0.53 / 1.15 (and 2026 +2.51 to the cut, which becomes the banner's +2.01 once the F10-less 08-11→08-30 stretch is included). This report's numbers are higher because they are **per unit gross**: the blended unit book (0.55·king book + 0.45·F10 book) has a floating gross of 0.44–0.79 (mean 0.61 over 2024→26, §T10) because the two books partly cancel, and the executor re-levers the blend to a constant 2.0×NAV at every anchor, so the NAV return is net_ex / gross_total × 2, not net_ex × 2. PREREG §0 fixes this mapping; the unit-book figures are listed alongside in §T11 so that nothing is lost between the two calibers. The executor's own re-levering adds turnover that the rec does not carry; it is quantified in §7 item 8 and is negligible.

## 7. Where the replay still differs from the live book, with the size where known

| # | item | replay | live | size | label |
|---|---|---|---|---|---|
| 1 | universe | U-PIT: top-449 by trailing 30-day quote volume at each month start, ≥ 30 days listed (PREREG §0 row 1) | frozen 449 list `syms450.txt`, chosen 08-2x, no refresh | U-FROZEN − U-PIT = +0.24 / +0.31 (2024→26), +0.39 / +0.45 (2025→26) bps per anchor per gross = look-ahead of the frozen list, not a forward edge; tradeable names 2026: U-PIT 296, U-FROZEN 279 (§T2), live 232–234 (STATE 09-04) | VERIFIED |
| 2 | fund rank base (M1) | all names with finite fund EMA on the panel: 297 / 464 / 597 (2024 / 2025 / 2026, results/diff_quant.json) | 528 = venue TRADING ∪ live450 (PREREG_deploy_universe AMENDMENT, 09-04) | base widening 400 → all names: +0.06 to +0.09 bps per anchor (RESULT_universe_dyn / PREREG_deploy_universe §0, cited); the 597-vs-528 residual is not measured | INFERRED |
| 3 | king / F10 rank base | the same 829-listed base (xz over all finite scores) | within the universe members only (LGBM / F10 scored on members) | no arm; unknown | UNRESOLVED |
| 4 | seat path | device msharpe-900 over its own leg returns on the 829 base: w3_king 0.42 (2024-H1) / 0.94 (2024-H2) / 0.69 (2025) / 0.38 (2026) (§T10) | bundle seat file (900 OOS leg rows) + producer rows; king seat 0.21 on 09-04 | STATE 09-04 (same device family, per gross): fixed 0.21 seat 2024→26 +12.6 %/gross/yr vs dynamic +24.4 %/gross/yr ⇒ ≈ 0.5 bps per anchor per gross in favour of the dynamic path = the largest known replay-vs-live gap; PREREG §0 chose the dynamic (device) seat | INFERRED from STATE |
| 5 | F10 end date | preds end 2026-08-10 20:00Z; the 2026 fold model was not saved (`/workspace/f8_2026-08-22/models` holds only the full-history `f10_live_s{42,2027}.pt`, forbidden for history) | live F10 v3 retrained to 08-30 | 08-11 → 08-30 (120 anchors) is not the live form: with the F10 leg absent the replay loses −4.3 bps per anchor per gross, −10 % of NAV at 2× in 20 days (§T12); the live book lost −0.65 % of NAV over 08-25→09-04 (STATE 09-05) — not comparable | VERIFIED |
| 6 | fills | every target filled at the anchor mid; cost = turnover × tier fee vector | maker fill ratio 0.85 (0.93 after top-ups), −5022 first refusal 25.5 %, unfilled 8.3 % of intended per anchor (cost-calib §4–5) | twin band −1.23 [−6.10, +3.72] bps per anchor of gross (n = 53); markout-implied extra cost +0.74 / +0.78 bps per anchor if the INFERRED vector is real (§4) | VERIFIED band / INFERRED size |
| 7 | pricing moment | nominal 4h grid | executor trades N+23 → N+26 min | paper nominal +3.78 vs shifted +0.93 bps per anchor (n = 53, s.e. 4.5, cost-calib §9); full-history decay study: 5–10 % of book P&L (STATE 09-04) | INFERRED |
| 8 | executor re-levering | rec turnover = Σ|Δ blended weights| / gross | executor re-scales the whole book to 2×NAV every anchor ⇒ extra turnover when the blend's gross drifts | +2.0 / +3.3 / +8.3 % turnover (2024 / 2025 / 2026) = +0.003 / +0.006 / +0.006 bps per anchor per gross at fee-only cost (results/diff_quant.json) — negligible | VERIFIED |
| 9 | funding | panel rate × 4/interval | exchange settlement | −0.12 bps per anchor (PREREG §0, cited from the caliber review) | cited |
| 10 | membership look-ahead | meta membership / `sel` requires a finite forward y4 (≥ 46 of the next 48 5-minute bars) | unknowable at the anchor | affects names delisted within the next 4h only; not measured | UNRESOLVED, small |
| 11 | seat warm-up | pinned king is NaN before 2024 ⇒ the 900-anchor seat window is king-free until ~2024-06 (w3_king 0.42 in 2024-H1) | live seat seeded from a 900-row file, no warm-up | 2024-H1 −13.2 / −10.6 %/yr at 2× is flagged and carried in every 2024 and 2024→26 figure | VERIFIED |
| 12 | FTRIM and M1 dates | applied over the whole history | FTRIM from 09-02 12Z, M1 from 09-04 04Z | forward-equal; the pre-09-02 live book is not the replay form (FTRIM +0.21–0.23, M1 +0.06–0.09 bps per anchor, STATE 09-02 / 09-04) | cited |
| 13 | cost tiers, stop layer, ≥ 80 gate, band, EMA, cap | identical rule (cost-calib §2 verified the tier rule against the producer; stop d30_n2_c42) | same | — | VERIFIED |
| 14 | realized gross | assumed 100 % of L×NAV | realized 98.1–100.7 % of target (STATE 09-03/09-04) | ≤ 2 % scaling of every NAV number | cited |

## 8. Device and universe-mask notes (what changed on disk and why)

- Device `w10_health.py` = `rolling_king/w10_universe_recheck.py` (sha256 5424aceb…, = port `w10_universe.py` 64c70a44… + REF_SKIP guard) + two additions, self-reported in `config_json` (`HEALTH` block with the device sha, `COST_B`, `COSTB_JSON`, `UMASK_SCOPE`): (a) `COSTB_JSON` cost-tier override; (b) `UMASK_SCOPE=trade`. The original UMASK semantics shrink the **member set** (`m = m[_mk[m]]`, L127/L183), i.e. the rank base as well as the trade set; PREREG §0 row 2 asks for "MEMBERS_TOPN=829 (秩基) + UMASK (交易集)", which the original device cannot express, so `trade` restricts only `sel` (after qv4h ≥ 2.5e5) and out-of-universe names fall into the forced-exit set. **TRADE_TOPN must be unset (0)**: with 400 it would AND a second top-400-by-qvk cut onto the trade set that the live book does not have. Default path receipts: pristine copy and patched copy both reproduce the axisB `R0_pinned_log_s42` artifact bitwise on all four arrays with equal config (§T13). `device.diff` (33 lines) is on the pod and the Mac.
- Masks (`build_umask.py`): U-PIT from the 5-minute cache channel `log_qv` (the channel the meta builder averages into qvk), Σ expm1 over the 8,640 bars strictly before the first panel anchor of each month, names listed ≥ 30 days (listing = first finite `log_qv` bar; the cache's bar 0 is all-NaN, so names with data within the first three bars count as listed at the cache start), top 449, held for the month; U-FROZEN = `syms450.txt` (449 names, all present in the 829-symbol panel). Yearly counts and overlap in §T2: the two masks share 21 % / 27 % / 39 % / 65 % / 84 % of the 449 in 2022 … 2026.
- `cost_calib.json` (cost-calib teammate, run 04:38:56Z, sha256 87250dde…) → `calib/costb_fee_steady.json` (sha256 ddb07d3c…): fee-only steady vector per tier, maker share per tier; the INFERRED markout vectors are recorded in the same file under `not_used` with the reason.
- Metrics `health_metrics.py` (windows, leverage mapping, day-block bootstrap seed 20260905 × 2000, slices, liquidation proximity, rolling Sharpe), tables `render_report.py`, gap sizes `diff_quant.py`. All commands verbatim in §T13 (`logs/commands.txt`).

## 9. Not verified, and risks not covered by any assertion here (TEAM_PROTOCOL §1)

- The adverse-selection cost (markout) is UNRESOLVED; if the INFERRED vector is real, every NAV figure above is roughly 60 % too high for 2024→26 (§4).
- Single instrument (pod2); jpline was not used. The second-instrument rebuild of 09-05 found ≤ 0.04 bps per anchor between king sources, so this is unlikely to move the picture, but it was not re-checked here.
- Bootstrap blocks are UTC days; the EMA book has multi-day persistence, so the CIs are probably somewhat too narrow. A longer-block sensitivity was not pre-registered and was not run.
- The seat path (item 4) is the largest known gap and was not bridged by any arm (PREREG §0 fixed the dynamic seat).
- The breadth slice uses nsel terciles because `regime_dash.py` has no breadth cut; the memory's "宽档 +2.97 / 窄档 −2.00" came from a monthly-breadth tercile study of another era and is not reproduced here.
- The live overlap window (08-26 → 09-04) cannot be compared to the replay: the replay's F10 leg ends 08-10 and its panel ends 08-30. The paper-vs-real reconciliation on the live anchors is the cost-calib teammate's §9 (twin + funding +0.26 bps per anchor, CI95 [−8.50, +8.91], n = 53), cited, not recomputed.

## 10. Files (pod `/workspace/review_scratch/health_check/`, Mac `…/scratchpad/review_caliber/health_check/`)

`setup_dev.sh` · `run_arm.sh` · `chain_eq.sh` · `chain_all.sh` · `w10_universe_recheck.py` (pristine, 5424aceb…) · `w10_health.py` (2cce0909…) · `device.diff` · `build_umask.py` (746700fd…) · `check_equiv.py` · `health_metrics.py` (f655ebc9…) · `render_report.py` · `diff_quant.py` · `masks/{umask_UPIT.npz ccb7a080…, umask_UFROZEN.npz 70470dbd…, btc_rv30.npz e1c31393…, mask_summary.json, listing.json, regime_series.npz}` · `calib/{cost_calib.json 87250dde…, costb_fee_steady.json ddb07d3c…}` · `dev/probe_artifacts/*.npz`, `dev_alt/probe_artifacts/*.npz` (12 artifacts, sha256 in `logs/chain_all.log`) · `results/*.json|txt` (11 arms + diff_quant.json) · `logs/{commands.txt, check_equiv.log, chain_*.log, setup_dev.log, build_umask*.log, health_metrics_*.log, *.out}` · `REPORT_tables.md` · `REPORT.md`.

---

# Tables (generated by `render_report.py` from `results/*.json`; nothing hand-typed)
<!-- generated by render_report.py; every number is read from results/<tag>.json (health_metrics.py), masks/mask_summary.json, calib/costb_fee_steady.json, logs/* -->

### T1. Arms (device w10_health.py; artifact and results receipts)

| tag | form | n anchors | first → last | artifact sha256[:16] | results json sha256[:16] |
|---|---|---|---|---|---|
| eq_patched_pinned_log_s42 | REF: M1+T400 (trade set = top-400 by qvk), log, s42, device default cost — equivalence artifact, NOT a PREREG arm | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 8bfe59b6ebc0a8c4 | 19ee945bd238038a |
| UPIT_prod_s42_cdef | U-PIT · prod · s42 · device default cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 62ee9fa387e61e9d | a1444dc3f681ead4 |
| UPIT_prod_s2027_cdef | U-PIT · prod · s2027 · device default cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | d40e816f29c2920b | 127ef99da892bbf0 |
| UPIT_log_s42_cdef | U-PIT · log · s42 · device default cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | be14ec12e4baf71c | d5e6881b12d08386 |
| UPIT_log_s2027_cdef | U-PIT · log · s2027 · device default cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 6d4b7d260a9121f2 | f6280ea7a5def6a5 |
| UPIT_prod_s42_ccal | U-PIT · prod · s42 · live fee-only cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 70dfe7512520784f | 9fc78224998832d5 |
| UPIT_prod_s2027_ccal | U-PIT · prod · s2027 · live fee-only cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 5ab79a6536dd3797 | 8053b97607c50041 |
| UPIT_log_s42_ccal | U-PIT · log · s42 · live fee-only cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | 33630cb0ac2b2f30 | 7251af9597c3c49d |
| UPIT_log_s2027_ccal | U-PIT · log · s2027 · live fee-only cost | 10038 | 2022-01-31 00:00 → 2026-08-30 20:00 | e0f51864cb9c8fa1 | 64fa6328ffda3ed5 |
| UFROZEN_prod_s42_ccal | U-FROZEN · prod · s42 · live fee-only cost | 10008 | 2022-01-31 00:00 → 2026-08-30 20:00 | a146115af2fba0ad | 170fa29fcafe6778 |
| UFROZEN_prod_s2027_ccal | U-FROZEN · prod · s2027 · live fee-only cost | 10008 | 2022-01-31 00:00 → 2026-08-30 20:00 | f409a5fc62f61e39 | 1f2801daa8340ea7 |

### T2. Universe masks — yearly mean counts on the device's anchor grid (masks/mask_summary.json)

| year | U-PIT allowed | U-PIT tradeable | U-FROZEN allowed | U-FROZEN tradeable | no-mask tradeable (829 base) | allowed in both | both / 449 | tradeable in both |
|---|---|---|---|---|---|---|---|---|
| 2022 | 141.1 | 138.1 | 450.0 | 94.2 | 141.6 | 92.6 | 0.206 | 91.8 |
| 2023 | 178.9 | 176.3 | 450.0 | 124.5 | 187.7 | 119.9 | 0.267 | 118.9 |
| 2024 | 265.8 | 258.0 | 450.0 | 182.4 | 272.3 | 175.6 | 0.391 | 173.7 |
| 2025 | 403.5 | 354.3 | 450.0 | 292.2 | 386.0 | 289.8 | 0.646 | 268.1 |
| 2026 | 449.0 | 295.6 | 450.0 | 278.5 | 324.2 | 376.2 | 0.838 | 264.2 |

tradeable = mask ∧ qv4h ≥ 2.5e5 ∧ finite y4 (device `sel` without the ≥80 gate). Listings by year (first 5m bar): {'2022': 163, '2023': 99, '2024': 131, '2025': 241, '2026': 192}. BTC 30-day realised vol, yearly mean %: {'2022': 65.6, '2023': 43.6, '2024': 52.7, '2025': 45.1, '2026': 44.1}.

U-PIT month rows (first 3 and last 3 of 56): 2022-01: listed 139, eligible 136, top 136, 449th 30d vol 285.8 M USDT; 2022-02: listed 139, eligible 136, top 136, 449th 30d vol 287.8 M USDT; 2022-03: listed 142, eligible 137, top 137, 449th 30d vol 228.3 M USDT; 2026-06: listed 726, eligible 556, top 449, 449th 30d vol 62.7 M USDT; 2026-07: listed 784, eligible 584, top 449, 449th 30d vol 57.1 M USDT; 2026-08: listed 826, eligible 635, top 449, 449th 30d vol 53.2 M USDT

### T3. Headline by window — mean net bps per anchor per unit gross [CI95, UTC-day block bootstrap 2000×] (executor caliber; ×2×2190/1e4 = %/yr of NAV at 2×)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 0.636 [-0.23, 1.53] | -0.247 — | 1.508 [0.23, 2.80] | 0.701 [-0.36, 1.75] | 3.209 [1.60, 4.81] | 1.260 [0.60, 1.97] | 1.649 [0.75, 2.61] |
| PIT/prod/42/def | 0.680 [-0.19, 1.60] | -0.298 — | 1.647 [0.37, 3.00] | 0.315 [-0.72, 1.39] | 3.222 [1.71, 4.77] | 1.132 [0.49, 1.82] | 1.414 [0.52, 2.33] |
| PIT/prod/2027/def | 0.744 [-0.12, 1.67] | -0.239 — | 1.716 [0.45, 3.05] | 0.390 [-0.64, 1.43] | 3.135 [1.63, 4.68] | 1.165 [0.53, 1.87] | 1.428 [0.56, 2.31] |
| PIT/log/42/def | 0.667 [-0.19, 1.56] | -0.161 — | 1.486 [0.22, 2.79] | 0.350 [-0.67, 1.39] | 3.088 [1.54, 4.65] | 1.110 [0.48, 1.80] | 1.386 [0.53, 2.30] |
| PIT/log/2027/def | 0.706 [-0.14, 1.60] | -0.109 — | 1.511 [0.27, 2.83] | 0.479 [-0.52, 1.52] | 3.077 [1.55, 4.63] | 1.171 [0.55, 1.86] | 1.462 [0.60, 2.36] |
| PIT/prod/42/cal | 0.691 [-0.18, 1.61] | -0.302 — | 1.673 [0.40, 3.02] | 0.383 [-0.65, 1.46] | 3.275 [1.77, 4.82] | 1.175 [0.54, 1.87] | 1.477 [0.58, 2.39] |
| PIT/prod/2027/cal | 0.754 [-0.11, 1.67] | -0.243 — | 1.740 [0.47, 3.08] | 0.448 [-0.58, 1.49] | 3.191 [1.69, 4.74] | 1.204 [0.57, 1.90] | 1.485 [0.61, 2.37] |
| PIT/log/42/cal | 0.680 [-0.17, 1.58] | -0.162 — | 1.512 [0.25, 2.82] | 0.417 [-0.60, 1.46] | 3.139 [1.59, 4.70] | 1.152 [0.52, 1.84] | 1.446 [0.59, 2.36] |
| PIT/log/2027/cal | 0.717 [-0.13, 1.60] | -0.110 — | 1.536 [0.29, 2.85] | 0.535 [-0.46, 1.57] | 3.130 [1.60, 4.68] | 1.210 [0.58, 1.90] | 1.517 [0.66, 2.42] |
| FRZ/prod/42/cal | 0.689 [-0.32, 1.77] | -0.309 — | 1.676 [0.17, 3.22] | 0.887 [-0.24, 1.98] | 3.471 [1.69, 5.11] | 1.413 [0.68, 2.19] | 1.864 [0.91, 2.83] |
| FRZ/prod/2027/cal | 0.828 [-0.19, 1.90] | -0.162 — | 1.807 [0.33, 3.31] | 1.033 [-0.09, 2.10] | 3.416 [1.69, 5.08] | 1.509 [0.80, 2.26] | 1.934 [1.00, 2.91] |

### T3b. Anchor Sharpe (√2190, leverage-invariant) [CI95]

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 1.41 [-0.54, 3.40] | -0.57 — | 3.20 [0.50, 5.81] | 1.26 [-0.64, 3.17] | 4.84 [2.44, 7.28] | 2.30 [1.09, 3.60] | 2.75 [1.25, 4.32] |
| PIT/prod/42/def | 1.53 [-0.44, 3.56] | -0.73 — | 3.46 [0.78, 6.16] | 0.57 [-1.28, 2.58] | 4.98 [2.64, 7.31] | 2.10 [0.92, 3.37] | 2.39 [0.88, 3.92] |
| PIT/prod/2027/def | 1.68 [-0.28, 3.72] | -0.58 — | 3.63 [0.97, 6.27] | 0.70 [-1.10, 2.67] | 4.86 [2.55, 7.22] | 2.16 [0.99, 3.45] | 2.41 [0.93, 3.88] |
| PIT/log/42/def | 1.51 [-0.45, 3.58] | -0.39 — | 3.16 [0.50, 5.82] | 0.65 [-1.22, 2.63] | 4.75 [2.38, 7.16] | 2.08 [0.91, 3.38] | 2.37 [0.91, 3.93] |
| PIT/log/2027/def | 1.61 [-0.33, 3.62] | -0.27 — | 3.24 [0.59, 5.85] | 0.88 [-0.96, 2.78] | 4.77 [2.41, 7.10] | 2.20 [1.02, 3.53] | 2.51 [1.01, 4.05] |
| PIT/prod/42/cal | 1.55 [-0.42, 3.58] | -0.74 — | 3.52 [0.84, 6.20] | 0.69 [-1.15, 2.70] | 5.06 [2.73, 7.39] | 2.18 [1.00, 3.45] | 2.50 [0.98, 4.02] |
| PIT/prod/2027/cal | 1.70 [-0.26, 3.74] | -0.59 — | 3.68 [1.02, 6.32] | 0.81 [-1.00, 2.77] | 4.95 [2.64, 7.31] | 2.23 [1.06, 3.52] | 2.51 [1.03, 3.98] |
| PIT/log/42/cal | 1.54 [-0.42, 3.60] | -0.40 — | 3.22 [0.56, 5.88] | 0.77 [-1.10, 2.76] | 4.83 [2.46, 7.24] | 2.16 [0.98, 3.45] | 2.48 [1.01, 4.04] |
| PIT/log/2027/cal | 1.64 [-0.30, 3.64] | -0.27 — | 3.29 [0.64, 5.90] | 0.99 [-0.86, 2.88] | 4.85 [2.49, 7.20] | 2.27 [1.09, 3.60] | 2.60 [1.10, 4.14] |
| FRZ/prod/42/cal | 1.25 [-0.57, 3.21] | -0.55 — | 3.09 [0.32, 5.77] | 1.46 [-0.39, 3.31] | 5.15 [2.57, 7.54] | 2.34 [1.13, 3.63] | 2.94 [1.44, 4.47] |
| FRZ/prod/2027/cal | 1.52 [-0.36, 3.45] | -0.29 — | 3.41 [0.64, 6.11] | 1.71 [-0.14, 3.53] | 5.06 [2.57, 7.44] | 2.52 [1.32, 3.78] | 3.06 [1.58, 4.58] |

### T4. NAV at the live leverage 2.0× — arithmetic %/yr · CAGR % · max drawdown % · worst UTC day % · days < −2% / < −5% / < −10% (n of days)

| arm | 2024 | 2024-H1 | 2024-H2 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 27.8 · 29.6 · DD 19.6 · wd -4.27 · 7/0/0 of 366 | -10.8 · -11.8 · DD 15.1 · wd -4.27 · 3/0/0 of 182 | 66.1 · 89.5 · DD 9.7 · wd -2.84 · 4/0/0 of 184 | 30.7 · 31.9 · DD 15.9 · wd -4.23 · 21/0/0 of 365 | 140.6 · 290.9 · DD 10.9 · wd -3.82 · 12/0/0 of 222 | 55.2 · 68.7 · DD 19.6 · wd -4.27 · 40/0/0 of 953 | 72.2 · 99.0 · DD 15.9 · wd -4.23 · 33/0/0 of 587 |
| PIT/prod/42/def | 29.8 · 32.1 · DD 22.1 · wd -3.50 · 8/0/0 of 366 | -13.1 · -13.7 · DD 16.3 · wd -3.50 · 2/0/0 of 182 | 72.1 · 101.3 · DD 9.9 · wd -3.02 · 6/0/0 of 184 | 13.8 · 11.4 · DD 20.6 · wd -4.94 · 20/0/0 of 365 | 141.1 · 293.8 · DD 8.4 · wd -3.95 · 8/0/0 of 222 | 49.6 · 59.6 · DD 22.1 · wd -4.94 · 36/0/0 of 953 | 61.9 · 79.6 · DD 20.6 · wd -4.94 · 28/0/0 of 587 |
| PIT/prod/2027/def | 32.6 · 35.9 · DD 20.9 · wd -3.43 · 7/0/0 of 366 | -10.4 · -11.4 · DD 15.7 · wd -3.43 · 2/0/0 of 182 | 75.2 · 107.5 · DD 9.3 · wd -2.70 · 5/0/0 of 184 | 17.1 · 15.1 · DD 18.0 · wd -4.21 · 20/0/0 of 365 | 137.3 · 279.3 · DD 8.1 · wd -4.03 · 8/0/0 of 222 | 51.0 · 62.0 · DD 20.9 · wd -4.21 · 35/0/0 of 953 | 62.6 · 80.7 · DD 18.0 · wd -4.21 · 28/0/0 of 587 |
| PIT/log/42/def | 29.2 · 31.5 · DD 19.0 · wd -3.73 · 9/0/0 of 366 | -7.0 · -8.3 · DD 13.1 · wd -3.73 · 3/0/0 of 182 | 65.1 · 87.7 · DD 9.7 · wd -3.03 · 6/0/0 of 184 | 15.3 · 13.4 · DD 21.0 · wd -4.46 · 20/0/0 of 365 | 135.3 · 271.3 · DD 8.5 · wd -3.58 · 14/0/0 of 222 | 48.6 · 58.2 · DD 21.0 · wd -4.46 · 43/0/0 of 953 | 60.7 · 77.6 · DD 21.0 · wd -4.46 · 34/0/0 of 587 |
| PIT/log/2027/def | 30.9 · 33.7 · DD 17.8 · wd -3.70 · 8/0/0 of 366 | -4.8 · -6.2 · DD 12.5 · wd -3.70 · 3/0/0 of 182 | 66.2 · 89.8 · DD 9.0 · wd -2.75 · 5/0/0 of 184 | 21.0 · 19.9 · DD 17.9 · wd -4.04 · 17/0/0 of 365 | 134.8 · 269.6 · DD 8.7 · wd -3.69 · 14/0/0 of 222 | 51.3 · 62.5 · DD 17.9 · wd -4.04 · 39/0/0 of 953 | 64.0 · 83.6 · DD 17.9 · wd -4.04 · 31/0/0 of 587 |
| PIT/prod/42/cal | 30.3 · 32.8 · DD 22.1 · wd -3.50 · 8/0/0 of 366 | -13.2 · -13.8 · DD 16.3 · wd -3.50 · 2/0/0 of 182 | 73.3 · 103.6 · DD 9.8 · wd -3.01 · 6/0/0 of 184 | 16.8 · 14.8 · DD 20.1 · wd -4.93 · 20/0/0 of 365 | 143.4 · 303.1 · DD 8.4 · wd -3.95 · 7/0/0 of 222 | 51.5 · 62.7 · DD 22.1 · wd -4.93 · 35/0/0 of 953 | 64.7 · 84.6 · DD 20.1 · wd -4.93 · 27/0/0 of 587 |
| PIT/prod/2027/cal | 33.0 · 36.6 · DD 20.9 · wd -3.44 · 7/0/0 of 366 | -10.6 · -11.5 · DD 15.8 · wd -3.44 · 2/0/0 of 182 | 76.2 · 109.8 · DD 9.2 · wd -2.69 · 5/0/0 of 184 | 19.6 · 18.1 · DD 17.5 · wd -4.20 · 20/0/0 of 365 | 139.8 · 288.7 · DD 8.1 · wd -4.03 · 8/0/0 of 222 | 52.8 · 64.8 · DD 20.9 · wd -4.20 · 35/0/0 of 953 | 65.1 · 85.3 · DD 17.5 · wd -4.20 · 28/0/0 of 587 |
| PIT/log/42/cal | 29.8 · 32.2 · DD 18.9 · wd -3.73 · 9/0/0 of 366 | -7.1 · -8.3 · DD 13.1 · wd -3.73 · 3/0/0 of 182 | 66.2 · 89.8 · DD 9.7 · wd -3.02 · 6/0/0 of 184 | 18.3 · 16.7 · DD 20.5 · wd -4.45 · 20/0/0 of 365 | 137.5 · 279.6 · DD 8.5 · wd -3.57 · 14/0/0 of 222 | 50.5 · 61.2 · DD 20.5 · wd -4.45 · 43/0/0 of 953 | 63.3 · 82.3 · DD 20.5 · wd -4.45 · 34/0/0 of 587 |
| PIT/log/2027/cal | 31.4 · 34.4 · DD 17.8 · wd -3.70 · 8/0/0 of 366 | -4.8 · -6.2 · DD 12.5 · wd -3.70 · 3/0/0 of 182 | 67.3 · 91.9 · DD 9.0 · wd -2.73 · 5/0/0 of 184 | 23.4 · 22.9 · DD 17.5 · wd -4.04 · 17/0/0 of 365 | 137.1 · 278.4 · DD 8.7 · wd -3.69 · 13/0/0 of 222 | 53.0 · 65.3 · DD 17.8 · wd -4.04 · 38/0/0 of 953 | 66.4 · 88.1 · DD 17.5 · wd -4.04 · 30/0/0 of 587 |
| FRZ/prod/42/cal | 30.2 · 31.4 · DD 26.2 · wd -5.33 · 13/1/0 of 366 | -13.5 · -15.2 · DD 20.6 · wd -5.33 · 5/1/0 of 182 | 73.4 · 102.6 · DD 10.7 · wd -3.54 · 8/0/0 of 184 | 38.9 · 42.4 · DD 17.5 · wd -3.98 · 23/0/0 of 365 | 152.0 · 337.7 · DD 9.2 · wd -4.80 · 14/0/0 of 222 | 61.9 · 79.3 · DD 26.2 · wd -5.33 · 50/1/0 of 953 | 81.7 · 117.7 · DD 17.5 · wd -4.80 · 37/0/0 of 587 |
| FRZ/prod/2027/cal | 36.3 · 39.7 · DD 23.3 · wd -5.29 · 11/1/0 of 366 | -7.1 · -9.6 · DD 18.1 · wd -5.29 · 4/1/0 of 182 | 79.1 · 114.8 · DD 9.9 · wd -3.26 · 7/0/0 of 184 | 45.2 · 51.8 · DD 15.0 · wd -4.25 · 23/0/0 of 365 | 149.6 · 327.1 · DD 8.9 · wd -4.55 · 15/0/0 of 222 | 66.1 · 87.1 · DD 23.3 · wd -5.29 · 49/1/0 of 953 | 84.7 · 124.5 · DD 16.2 · wd -4.55 · 38/0/0 of 587 |

### T5. Leverage table — primary arms (U-PIT, prod caliber, live fee-only cost), L ∈ {2.0, 2.5, 3.0}


**2024->26**

| metric | PIT/prod/42/cal L=2.0 | PIT/prod/42/cal L=2.5 | PIT/prod/42/cal L=3.0 | PIT/prod/2027/cal L=2.0 | PIT/prod/2027/cal L=2.5 | PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 51.47 | 64.34 | 77.20 | 52.76 | 65.95 | 79.14 |
| CAGR % | 62.69 | 82.13 | 103.19 | 64.81 | 85.11 | 107.19 |
| total % | 256.32 | 378.48 | 536.67 | 268.58 | 399.17 | 569.89 |
| vol %/yr | 23.65 | 29.56 | 35.47 | 23.62 | 29.53 | 35.43 |
| Sharpe daily | 2.21 | 2.21 | 2.21 | 2.29 | 2.29 | 2.28 |
| Sortino daily | 3.45 | 3.45 | 3.45 | 3.56 | 3.56 | 3.56 |
| maxDD % | 22.10 | 27.00 | 31.65 | 20.93 | 25.62 | 30.10 |
| maxDD span d | 286.50 | 288.33 | 290.83 | 283.83 | 283.83 | 284.17 |
| recovered | True | True | True | True | True | True |
| longest DD d | 364.17 | 365.00 | 372.33 | 331.33 | 332.00 | 357.33 |
| worst day % | -4.93 | -6.13 | -7.33 | -4.20 | -5.23 | -6.25 |
| worst week % | -11.75 | -14.55 | -17.29 | -11.36 | -14.07 | -16.73 |
| worst month % | -17.59 | -21.61 | -25.47 | -15.21 | -18.77 | -22.22 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 10 | 10 | 10 | 8 | 8 | 9 |
| n months | 32 | 32 | 32 | 32 | 32 | 32 |
| days<−2% | 35 | 67 | 87 | 35 | 62 | 89 |
| share<−2% | 0.04 | 0.07 | 0.09 | 0.04 | 0.07 | 0.09 |
| days<−5% | 0 | 1 | 6 | 0 | 5 | 9 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.54 | 0.54 | 0.54 | 0.55 | 0.55 | 0.55 |
| anchor p1 % | -1.29 | -1.62 | -1.94 | -1.30 | -1.62 | -1.95 |
| anchor p5 % | -0.75 | -0.93 | -1.12 | -0.75 | -0.93 | -1.12 |
| anchor min % | -4.55 | -5.68 | -6.82 | -4.61 | -5.76 | -6.92 |
| 8-anchor p5 % | -2.03 | -2.55 | -3.07 | -2.01 | -2.51 | -3.02 |
| 8-anchor min % | -7.53 | -9.44 | -11.36 | -7.92 | -9.94 | -11.98 |
| VaR99 day % | -3.05 | -3.81 | -4.57 | -2.92 | -3.65 | -4.37 |
| CVaR99 day % | -3.66 | -4.56 | -5.47 | -3.79 | -4.72 | -5.66 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -2.13 / 1.11 / 6.43 (n 874) | -2.13 / 1.11 / 6.42 (n 874) | -2.13 / 1.11 / 6.42 (n 874) | -1.85 / 1.30 / 6.36 (n 874) | -1.85 / 1.30 / 6.35 (n 874) | -1.85 / 1.30 / 6.35 (n 874) |

**2025->26**

| metric | PIT/prod/42/cal L=2.0 | PIT/prod/42/cal L=2.5 | PIT/prod/42/cal L=3.0 | PIT/prod/2027/cal L=2.0 | PIT/prod/2027/cal L=2.5 | PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 64.69 | 80.86 | 97.03 | 65.06 | 81.32 | 97.59 |
| CAGR % | 84.63 | 112.96 | 144.61 | 85.32 | 113.95 | 145.97 |
| total % | 168.09 | 237.28 | 321.45 | 169.69 | 239.79 | 325.23 |
| vol %/yr | 25.91 | 32.39 | 38.87 | 25.91 | 32.39 | 38.86 |
| Sharpe daily | 2.58 | 2.57 | 2.57 | 2.61 | 2.60 | 2.60 |
| Sortino daily | 4.00 | 4.00 | 4.00 | 4.03 | 4.03 | 4.03 |
| maxDD % | 20.13 | 24.68 | 29.05 | 17.53 | 21.60 | 25.54 |
| maxDD span d | 364.17 | 365.00 | 372.33 | 331.33 | 332.00 | 357.33 |
| recovered | True | True | True | True | True | True |
| longest DD d | 364.17 | 365.00 | 372.33 | 331.33 | 332.00 | 357.33 |
| worst day % | -4.93 | -6.13 | -7.33 | -4.20 | -5.23 | -6.25 |
| worst week % | -11.75 | -14.55 | -17.29 | -11.36 | -14.07 | -16.73 |
| worst month % | -17.59 | -21.61 | -25.47 | -15.21 | -18.77 | -22.22 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 5 | 5 | 5 | 3 | 3 | 4 |
| n months | 20 | 20 | 20 | 20 | 20 | 20 |
| days<−2% | 27 | 49 | 61 | 28 | 44 | 64 |
| share<−2% | 0.05 | 0.08 | 0.10 | 0.05 | 0.07 | 0.11 |
| days<−5% | 0 | 1 | 5 | 0 | 5 | 8 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.56 | 0.56 | 0.56 | 0.56 | 0.56 | 0.56 |
| anchor p1 % | -1.41 | -1.77 | -2.12 | -1.37 | -1.71 | -2.05 |
| anchor p5 % | -0.83 | -1.04 | -1.24 | -0.84 | -1.04 | -1.25 |
| anchor min % | -4.55 | -5.68 | -6.82 | -4.61 | -5.76 | -6.92 |
| 8-anchor p5 % | -2.19 | -2.74 | -3.29 | -2.21 | -2.76 | -3.32 |
| 8-anchor min % | -7.53 | -9.44 | -11.36 | -7.92 | -9.94 | -11.98 |
| VaR99 day % | -3.28 | -4.10 | -4.92 | -3.71 | -4.62 | -5.52 |
| CVaR99 day % | -3.93 | -4.90 | -5.87 | -4.07 | -5.07 | -6.07 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -1.39 / 0.98 / 6.77 (n 508) | -1.39 / 0.98 / 6.76 (n 508) | -1.39 / 0.98 / 6.76 (n 508) | -1.05 / 1.14 / 6.38 (n 508) | -1.05 / 1.14 / 6.37 (n 508) | -1.05 / 1.14 / 6.36 (n 508) |

**2026->cut**

| metric | PIT/prod/42/cal L=2.0 | PIT/prod/42/cal L=2.5 | PIT/prod/42/cal L=3.0 | PIT/prod/2027/cal L=2.0 | PIT/prod/2027/cal L=2.5 | PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 143.45 | 179.31 | 215.17 | 139.77 | 174.72 | 209.66 |
| CAGR % | 303.07 | 463.95 | 685.08 | 288.67 | 438.92 | 643.54 |
| total % | 133.46 | 186.37 | 250.19 | 128.34 | 178.57 | 238.80 |
| vol %/yr | 28.34 | 35.42 | 42.51 | 28.23 | 35.29 | 42.35 |
| Sharpe daily | 5.35 | 5.34 | 5.34 | 5.19 | 5.19 | 5.19 |
| Sortino daily | 9.60 | 9.60 | 9.61 | 9.08 | 9.09 | 9.09 |
| maxDD % | 8.41 | 10.43 | 12.41 | 8.09 | 10.04 | 11.94 |
| maxDD span d | 25.00 | 25.00 | 25.17 | 25.17 | 25.17 | 25.17 |
| recovered | True | True | True | True | True | True |
| longest DD d | 25.83 | 25.83 | 25.83 | 25.83 | 26.00 | 26.00 |
| worst day % | -3.95 | -4.92 | -5.89 | -4.03 | -5.02 | -6.01 |
| worst week % | -7.22 | -8.97 | -10.69 | -6.74 | -8.38 | -10.00 |
| worst month % | 2.34 | 2.90 | 3.44 | 2.45 | 3.03 | 3.60 |
| worst month | 202608 | 202608 | 202608 | 202608 | 202608 | 202608 |
| neg months | 0 | 0 | 0 | 0 | 0 | 0 |
| n months | 8 | 8 | 8 | 8 | 8 | 8 |
| days<−2% | 7 | 20 | 24 | 8 | 18 | 25 |
| share<−2% | 0.03 | 0.09 | 0.11 | 0.04 | 0.08 | 0.11 |
| days<−5% | 0 | 0 | 1 | 0 | 1 | 2 |
| share<−5% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.62 | 0.62 | 0.62 | 0.61 | 0.61 | 0.61 |
| anchor p1 % | -1.35 | -1.69 | -2.03 | -1.37 | -1.71 | -2.05 |
| anchor p5 % | -0.94 | -1.17 | -1.41 | -0.95 | -1.19 | -1.42 |
| anchor min % | -2.34 | -2.93 | -3.51 | -2.35 | -2.94 | -3.53 |
| 8-anchor p5 % | -2.15 | -2.69 | -3.24 | -2.19 | -2.75 | -3.30 |
| 8-anchor min % | -5.18 | -6.48 | -7.79 | -5.24 | -6.56 | -7.89 |
| VaR99 day % | -2.73 | -3.40 | -4.07 | -2.85 | -3.55 | -4.25 |
| CVaR99 day % | -3.17 | -3.95 | -4.73 | -3.54 | -4.41 | -5.27 |
| min equity/gross (anchor) | 0.49 | 0.39 | 0.32 | 0.49 | 0.39 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.47 | 0.37 | 0.31 | 0.47 | 0.37 | 0.31 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | 2.58 / 5.85 / 7.31 (n 143) | 2.58 / 5.85 / 7.31 (n 143) | 2.57 / 5.84 / 7.30 (n 143) | 2.75 / 5.58 / 6.93 (n 143) | 2.74 / 5.58 / 6.92 (n 143) | 2.74 / 5.57 / 6.92 (n 143) |

**2024**

| metric | PIT/prod/42/cal L=2.0 | PIT/prod/42/cal L=2.5 | PIT/prod/42/cal L=3.0 | PIT/prod/2027/cal L=2.0 | PIT/prod/2027/cal L=2.5 | PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 30.27 | 37.84 | 45.40 | 33.04 | 41.30 | 49.55 |
| CAGR % | 32.81 | 41.73 | 50.90 | 36.55 | 46.75 | 57.34 |
| total % | 32.91 | 41.87 | 51.07 | 36.67 | 46.91 | 57.54 |
| vol %/yr | 19.47 | 24.34 | 29.21 | 19.40 | 24.25 | 29.10 |
| Sharpe daily | 1.53 | 1.53 | 1.53 | 1.68 | 1.68 | 1.68 |
| Sortino daily | 2.40 | 2.40 | 2.40 | 2.67 | 2.67 | 2.68 |
| maxDD % | 22.10 | 27.00 | 31.65 | 20.93 | 25.62 | 30.10 |
| maxDD span d | 286.50 | 288.33 | 290.83 | 283.83 | 283.83 | 284.17 |
| recovered | True | True | True | True | True | True |
| longest DD d | 286.50 | 288.33 | 290.83 | 283.83 | 283.83 | 284.17 |
| worst day % | -3.50 | -4.37 | -5.24 | -3.44 | -4.29 | -5.15 |
| worst week % | -5.38 | -6.69 | -7.99 | -5.38 | -6.69 | -7.98 |
| worst month % | -7.03 | -8.76 | -10.48 | -6.73 | -8.38 | -10.03 |
| worst month | 202404 | 202404 | 202404 | 202404 | 202404 | 202404 |
| neg months | 5 | 5 | 5 | 5 | 5 | 5 |
| n months | 12 | 12 | 12 | 12 | 12 | 12 |
| days<−2% | 8 | 18 | 26 | 7 | 18 | 25 |
| share<−2% | 0.02 | 0.05 | 0.07 | 0.02 | 0.05 | 0.07 |
| days<−5% | 0 | 0 | 1 | 0 | 0 | 1 |
| share<−5% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 |
| anchor p1 % | -1.04 | -1.30 | -1.56 | -1.04 | -1.30 | -1.56 |
| anchor p5 % | -0.60 | -0.75 | -0.90 | -0.57 | -0.72 | -0.86 |
| anchor min % | -3.19 | -3.99 | -4.79 | -3.17 | -3.97 | -4.76 |
| 8-anchor p5 % | -1.81 | -2.27 | -2.72 | -1.75 | -2.19 | -2.63 |
| 8-anchor min % | -4.31 | -5.39 | -6.48 | -3.92 | -4.91 | -5.91 |
| VaR99 day % | -2.32 | -2.90 | -3.47 | -2.42 | -3.02 | -3.61 |
| CVaR99 day % | -2.83 | -3.53 | -4.23 | -2.79 | -3.49 | -4.18 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.32 | 0.48 | 0.38 | 0.32 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -2.87 / 0.54 / 4.75 (n 287) | -2.87 / 0.54 / 4.74 (n 287) | -2.87 / 0.55 / 4.74 (n 287) | -2.65 / 0.51 / 5.57 (n 287) | -2.65 / 0.51 / 5.56 (n 287) | -2.65 / 0.51 / 5.56 (n 287) |

**2025**

| metric | PIT/prod/42/cal L=2.0 | PIT/prod/42/cal L=2.5 | PIT/prod/42/cal L=3.0 | PIT/prod/2027/cal L=2.0 | PIT/prod/2027/cal L=2.5 | PIT/prod/2027/cal L=3.0 |
|---|---|---|---|---|---|---|
| arith %/yr | 16.78 | 20.98 | 25.17 | 19.61 | 24.52 | 29.42 |
| CAGR % | 14.83 | 17.78 | 20.35 | 18.11 | 21.98 | 25.51 |
| total % | 14.83 | 17.78 | 20.35 | 18.11 | 21.98 | 25.51 |
| vol %/yr | 24.26 | 30.33 | 36.40 | 24.34 | 30.43 | 36.51 |
| Sharpe daily | 0.70 | 0.70 | 0.70 | 0.83 | 0.83 | 0.83 |
| Sortino daily | 0.99 | 0.99 | 0.99 | 1.17 | 1.17 | 1.17 |
| maxDD % | 20.13 | 24.68 | 29.05 | 17.53 | 21.60 | 25.54 |
| maxDD span d | 277.00 | 277.00 | 277.00 | 276.83 | 276.83 | 276.83 |
| recovered | False | False | False | False | False | False |
| longest DD d | 277.00 | 277.00 | 277.00 | 276.83 | 276.83 | 276.83 |
| worst day % | -4.93 | -6.13 | -7.33 | -4.20 | -5.23 | -6.25 |
| worst week % | -11.75 | -14.55 | -17.29 | -11.36 | -14.07 | -16.73 |
| worst month % | -17.59 | -21.61 | -25.47 | -15.21 | -18.77 | -22.22 |
| worst month | 202504 | 202504 | 202504 | 202504 | 202504 | 202504 |
| neg months | 5 | 5 | 5 | 3 | 3 | 4 |
| n months | 12 | 12 | 12 | 12 | 12 | 12 |
| days<−2% | 20 | 29 | 37 | 20 | 26 | 39 |
| share<−2% | 0.05 | 0.08 | 0.10 | 0.05 | 0.07 | 0.11 |
| days<−5% | 0 | 1 | 4 | 0 | 4 | 6 |
| share<−5% | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.02 |
| days<−10% | 0 | 0 | 0 | 0 | 0 | 0 |
| win day | 0.52 | 0.52 | 0.52 | 0.53 | 0.53 | 0.53 |
| anchor p1 % | -1.46 | -1.82 | -2.19 | -1.35 | -1.69 | -2.03 |
| anchor p5 % | -0.77 | -0.96 | -1.16 | -0.78 | -0.98 | -1.18 |
| anchor min % | -4.55 | -5.68 | -6.82 | -4.61 | -5.76 | -6.92 |
| 8-anchor p5 % | -2.21 | -2.77 | -3.33 | -2.23 | -2.81 | -3.38 |
| 8-anchor min % | -7.53 | -9.44 | -11.36 | -7.92 | -9.94 | -11.98 |
| VaR99 day % | -3.41 | -4.25 | -5.09 | -3.89 | -4.86 | -5.82 |
| CVaR99 day % | -4.08 | -5.09 | -6.09 | -4.14 | -5.17 | -6.19 |
| min equity/gross (anchor) | 0.48 | 0.38 | 0.31 | 0.48 | 0.38 | 0.31 |
| touches 1.5% (anchor) | 0 | 0 | 0 | 0 | 0 | 0 |
| min equity/gross (8 anchors) | 0.46 | 0.36 | 0.30 | 0.46 | 0.36 | 0.30 |
| touches 1.5% (8 anchors) | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling 90-day daily Sharpe p5 / median / p95 | -1.69 / 0.56 / 3.93 (n 286) | -1.69 / 0.55 / 3.93 (n 286) | -1.69 / 0.55 / 3.92 (n 286) | -1.08 / 0.65 / 3.52 (n 286) | -1.08 / 0.64 / 3.52 (n 286) | -1.08 / 0.64 / 3.51 (n 286) |

### T6. Calendar quarters — mean net bps per anchor per gross · NAV total return % at 2× (compounded) · max DD % at 2×

| arm | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 | 2026-Q1 | 2026-Q2 | 2026-Q3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 0.41 · 4.1% · DD 9.8 | -0.90 · -9.8% · DD 12.9 | 1.09 · 12.4% · DD 9.7 | 1.92 · 22.8% · DD 7.1 | 2.43 · 29.1% · DD 5.8 | -0.85 · -9.7% · DD 15.9 | 0.34 · 3.4% · DD 10.2 | 0.91 · 9.4% · DD 10.4 | 1.42 · 15.8% · DD 6.0 | 5.38 · 77.6% · DD 7.4 | 2.31 · 11.4% · DD 9.1 |
| PIT/prod/42/def | 0.50 · 5.2% · DD 10.8 | -1.10 · -11.6% · DD 13.5 | 0.87 · 9.7% · DD 9.9 | 2.42 · 29.7% · DD 5.9 | 2.37 · 28.4% · DD 5.5 | -1.53 · -16.2% · DD 20.1 | 0.41 · 4.3% · DD 7.6 | 0.03 · -0.7% · DD 8.7 | 1.22 · 13.4% · DD 4.6 | 5.39 · 77.6% · DD 8.4 | 2.81 · 14.3% · DD 5.1 |
| PIT/prod/2027/def | 0.56 · 5.8% · DD 10.7 | -1.04 · -11.0% · DD 13.1 | 0.77 · 8.5% · DD 9.3 | 2.66 · 33.2% · DD 5.7 | 2.28 · 27.0% · DD 5.9 | -1.08 · -12.0% · DD 17.5 | 0.49 · 5.3% · DD 7.6 | -0.11 · -2.2% · DD 9.4 | 1.28 · 14.1% · DD 4.4 | 5.09 · 72.0% · DD 8.1 | 2.87 · 14.6% · DD 5.2 |
| PIT/log/42/def | 0.51 · 5.3% · DD 10.5 | -0.83 · -9.0% · DD 11.0 | 0.80 · 8.8% · DD 9.7 | 2.17 · 26.2% · DD 6.1 | 2.08 · 24.3% · DD 5.4 | -1.63 · -17.1% · DD 20.6 | 0.49 · 5.3% · DD 7.1 | 0.48 · 4.5% · DD 8.7 | 1.18 · 12.9% · DD 4.6 | 5.28 · 75.6% · DD 8.0 | 2.41 · 12.0% · DD 6.6 |
| PIT/log/2027/def | 0.64 · 6.8% · DD 9.6 | -0.86 · -9.3% · DD 11.2 | 0.68 · 7.4% · DD 9.0 | 2.34 · 28.7% · DD 5.9 | 2.02 · 23.5% · DD 6.4 | -1.17 · -12.8% · DD 17.2 | 0.59 · 6.4% · DD 7.1 | 0.49 · 4.7% · DD 8.4 | 1.25 · 13.7% · DD 4.7 | 5.19 · 73.9% · DD 7.8 | 2.41 · 12.0% · DD 6.8 |
| PIT/prod/42/cal | 0.50 · 5.1% · DD 10.8 | -1.10 · -11.7% · DD 13.6 | 0.93 · 10.4% · DD 9.8 | 2.42 · 29.7% · DD 5.8 | 2.44 · 29.3% · DD 5.4 | -1.43 · -15.3% · DD 19.6 | 0.48 · 5.1% · DD 7.6 | 0.07 · -0.3% · DD 8.5 | 1.28 · 14.2% · DD 4.5 | 5.43 · 78.5% · DD 8.4 | 2.86 · 14.5% · DD 5.0 |
| PIT/prod/2027/cal | 0.55 · 5.8% · DD 10.7 | -1.04 · -11.1% · DD 13.1 | 0.83 · 9.1% · DD 9.2 | 2.65 · 33.1% · DD 5.8 | 2.33 · 27.7% · DD 5.9 | -0.99 · -11.2% · DD 17.3 | 0.55 · 6.0% · DD 7.5 | -0.07 · -1.8% · DD 9.3 | 1.34 · 15.0% · DD 4.4 | 5.14 · 73.0% · DD 8.1 | 2.91 · 14.8% · DD 5.1 |
| PIT/log/42/cal | 0.51 · 5.3% · DD 10.5 | -0.83 · -9.0% · DD 11.0 | 0.86 · 9.5% · DD 9.7 | 2.16 · 26.1% · DD 6.0 | 2.15 · 25.2% · DD 5.4 | -1.53 · -16.2% · DD 20.1 | 0.55 · 6.0% · DD 7.0 | 0.51 · 4.9% · DD 8.6 | 1.24 · 13.6% · DD 4.6 | 5.32 · 76.5% · DD 8.0 | 2.45 · 12.3% · DD 6.6 |
| PIT/log/2027/cal | 0.64 · 6.8% · DD 9.6 | -0.86 · -9.3% · DD 11.2 | 0.74 · 8.0% · DD 9.0 | 2.34 · 28.6% · DD 6.0 | 2.07 · 24.2% · DD 6.4 | -1.09 · -12.0% · DD 16.8 | 0.64 · 7.1% · DD 7.0 | 0.53 · 5.1% · DD 8.3 | 1.31 · 14.5% · DD 4.6 | 5.23 · 74.8% · DD 7.8 | 2.46 · 12.3% · DD 6.8 |
| FRZ/prod/42/cal | 0.81 · 8.3% · DD 11.5 | -1.43 · -14.9% · DD 17.6 | 0.84 · 9.2% · DD 10.7 | 2.51 · 30.8% · DD 7.3 | 2.94 · 36.3% · DD 8.8 | -0.39 · -5.2% · DD 17.5 | 0.06 · 0.3% · DD 9.3 | 0.96 · 9.9% · DD 10.5 | 1.40 · 15.5% · DD 6.7 | 5.68 · 83.2% · DD 9.2 | 3.12 · 16.0% · DD 6.4 |
| FRZ/prod/2027/cal | 0.96 · 10.0% · DD 10.2 | -1.28 · -13.5% · DD 16.1 | 0.81 · 8.9% · DD 9.9 | 2.80 · 35.1% · DD 6.2 | 3.16 · 39.5% · DD 7.6 | 0.23 · 1.4% · DD 15.0 | 0.05 · 0.2% · DD 8.1 | 0.73 · 7.1% · DD 11.9 | 1.44 · 16.0% · DD 6.6 | 5.47 · 79.0% · DD 8.6 | 3.21 · 16.5% · DD 6.7 |

### T7. Calendar months 2024-01 → 2026-08 (to cut) — NAV % at 2× (compounded) · mean bps/anchor per gross; primary arms and the REF form

| month | PIT/prod/42/cal | PIT/prod/2027/cal | FRZ/prod/42/cal | REF T400/log/42 |
|---|---|---|---|---|
| 2024-01 | 4.6% · 1.25 | 5.8% · 1.55 | 1.9% · 0.59 | 0.6% · 0.20 |
| 2024-02 | -5.6% · -1.61 | -5.8% · -1.69 | 0.1% · 0.11 | -3.8% · -1.07 |
| 2024-03 | 6.4% · 1.72 | 6.2% · 1.66 | 6.2% · 1.69 | 7.5% · 2.00 |
| 2024-04 | -7.0% · -1.98 | -6.7% · -1.89 | -10.0% · -2.86 | -8.2% · -2.31 |
| 2024-05 | -1.5% · -0.38 | -1.3% · -0.31 | -2.7% · -0.67 | -0.1% · 0.00 |
| 2024-06 | -3.5% · -0.98 | -3.4% · -0.95 | -2.9% · -0.78 | -1.6% · -0.44 |
| 2024-07 | -4.7% · -1.27 | -3.9% · -1.04 | -4.7% · -1.27 | -4.7% · -1.28 |
| 2024-08 | 14.5% · 3.68 | 11.9% · 3.06 | 12.6% · 3.24 | 14.2% · 3.63 |
| 2024-09 | 1.2% · 0.36 | 1.5% · 0.45 | 1.8% · 0.54 | 3.3% · 0.93 |
| 2024-10 | 4.8% · 1.29 | 6.7% · 1.77 | 2.2% · 0.64 | 3.6% · 0.98 |
| 2024-11 | 15.7% · 4.15 | 17.2% · 4.51 | 15.1% · 4.01 | 13.9% · 3.71 |
| 2024-12 | 7.0% · 1.87 | 6.5% · 1.74 | 11.2% · 2.92 | 4.1% · 1.13 |
| 2025-01 | 13.5% · 3.44 | 13.1% · 3.34 | 14.2% · 3.63 | 13.2% · 3.37 |
| 2025-02 | 2.1% · 0.72 | 2.2% · 0.74 | -1.3% · -0.29 | 1.5% · 0.55 |
| 2025-03 | 11.6% · 3.01 | 10.6% · 2.76 | 20.9% · 5.18 | 12.3% · 3.19 |
| 2025-04 | -17.6% · -5.24 | -15.2% · -4.45 | -11.7% · -3.34 | -13.8% · -4.00 |
| 2025-05 | 3.6% · 1.06 | 4.0% · 1.17 | -0.4% · 0.03 | 3.8% · 1.09 |
| 2025-06 | -0.8% · -0.19 | 0.7% · 0.23 | 7.9% · 2.13 | 1.0% · 0.28 |
| 2025-07 | 5.6% · 1.47 | 5.8% · 1.54 | -1.9% · -0.47 | 4.5% · 1.20 |
| 2025-08 | -2.0% · -0.53 | 0.0% · 0.02 | -3.4% · -0.91 | -6.5% · -1.80 |
| 2025-09 | 1.6% · 0.49 | 0.1% · 0.07 | 5.8% · 1.62 | 5.9% · 1.65 |
| 2025-10 | 5.0% · 1.41 | 4.8% · 1.36 | 21.2% · 5.29 | 18.4% · 4.65 |
| 2025-11 | -1.0% · -0.18 | -1.4% · -0.31 | -4.3% · -1.11 | -0.5% · -0.04 |
| 2025-12 | -4.1% · -1.03 | -4.9% · -1.28 | -5.3% · -1.37 | -7.1% · -1.92 |
| 2026-01 | 4.9% · 1.34 | 4.9% · 1.32 | 2.6% · 0.75 | 6.3% · 1.70 |
| 2026-02 | 2.7% · 0.88 | 2.6% · 0.84 | 5.6% · 1.69 | 2.6% · 0.85 |
| 2026-03 | 5.9% · 1.59 | 6.9% · 1.83 | 6.7% · 1.79 | 6.2% · 1.67 |
| 2026-04 | 30.0% · 7.42 | 26.7% · 6.70 | 31.7% · 7.78 | 24.3% · 6.15 |
| 2026-05 | 6.4% · 1.77 | 6.7% · 1.85 | 7.2% · 1.97 | 10.5% · 2.78 |
| 2026-06 | 29.0% · 7.23 | 27.9% · 6.99 | 29.8% · 7.40 | 29.3% · 7.31 |
| 2026-07 | 11.9% · 3.12 | 12.1% · 3.17 | 14.7% · 3.78 | 8.0% · 2.19 |
| 2026-08 (to cut 08-10) | -8.0% · -2.22 | -7.5% · -2.06 | -7.0% · -1.89 | -7.2% · -1.95 |

### T8-sigma_fund. Slice 2024→cut: σ_fund (bps/8h, META members, 30-anchor trailing mean) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: bps/8h, 30-anchor trailing mean. Causal cuts at window end [3.3673, 9.3859]; descriptive (window) cuts [5.3069, 13.6993].

| bucket | PIT/prod/42/cal | PIT/prod/2027/cal | PIT/log/42/cal | PIT/log/2027/cal | FRZ/prod/42/cal | REF T400/log/42 |
|---|---|---|---|---|---|---|
| causal low (var mean 1.95) | 1.09 [-0.41, 2.61] · S 2.94 · 48%/yr · n 553 | 0.98 [-0.45, 2.42] · S 2.72 · 43%/yr · n 553 | 1.26 [-0.20, 2.76] · S 3.45 · 55%/yr · n 553 | 1.14 [-0.28, 2.56] · S 3.19 · 50%/yr · n 553 | 0.15 [-1.66, 1.90] · S 0.30 · 7%/yr · n 553 | 0.74 [-0.73, 2.21] · S 1.96 · 32%/yr · n 553 |
| causal mid (var mean 3.82) | -0.09 [-1.32, 1.21] · S -0.17 · -4%/yr · n 1230 | -0.03 [-1.27, 1.26] · S -0.05 · -1%/yr · n 1230 | -0.06 [-1.27, 1.23] · S -0.11 · -2%/yr · n 1230 | 0.01 [-1.20, 1.27] · S 0.02 · 1%/yr · n 1230 | 0.29 [-1.18, 1.77] · S 0.50 · 13%/yr · n 1230 | 0.11 [-1.14, 1.42] · S 0.22 · 5%/yr · n 1230 |
| causal high (var mean 14.91) | 1.58 [0.79, 2.39] · S 2.78 · 69%/yr · n 3935 | 1.62 [0.82, 2.43] · S 2.84 · 71%/yr · n 3935 | 1.51 [0.69, 2.31] · S 2.69 · 66%/yr · n 3935 | 1.59 [0.80, 2.39] · S 2.84 · 70%/yr · n 3935 | 1.94 [1.02, 2.83] · S 3.12 · 85%/yr · n 3935 | 1.69 [0.86, 2.54] · S 2.93 · 74%/yr · n 3935 |
| descriptive low (var mean 3.19) | 0.46 [-0.51, 1.42] · S 1.04 · 20%/yr · n 1906 | 0.47 [-0.53, 1.41] · S 1.07 · 21%/yr · n 1906 | 0.47 [-0.49, 1.42] · S 1.07 · 21%/yr · n 1906 | 0.47 [-0.52, 1.40] · S 1.07 · 21%/yr · n 1906 | 0.43 [-0.68, 1.54] · S 0.80 · 19%/yr · n 1906 | 0.48 [-0.46, 1.44] · S 1.05 · 21%/yr · n 1906 |
| descriptive mid (var mean 9.40) | 1.37 [0.22, 2.51] · S 2.51 · 60%/yr · n 1906 | 1.37 [0.26, 2.47] · S 2.51 · 60%/yr · n 1906 | 1.37 [0.29, 2.45] · S 2.58 · 60%/yr · n 1906 | 1.36 [0.28, 2.39] · S 2.56 · 59%/yr · n 1906 | 2.23 [0.90, 3.52] · S 3.63 · 98%/yr · n 1906 | 1.74 [0.59, 2.87] · S 3.19 · 76%/yr · n 1906 |
| descriptive high (var mean 21.23) | 1.69 [0.40, 2.94] · S 2.75 · 74%/yr · n 1906 | 1.77 [0.50, 2.99] · S 2.88 · 77%/yr · n 1906 | 1.61 [0.33, 2.84] · S 2.63 · 71%/yr · n 1906 | 1.80 [0.53, 3.03] · S 2.94 · 79%/yr · n 1906 | 1.58 [0.21, 2.88] · S 2.43 · 69%/yr · n 1906 | 1.57 [0.23, 2.86] · S 2.49 · 69%/yr · n 1906 |

### T8-breadth_nsel. Slice 2024→cut: breadth = nsel (tradeable names) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: nsel = tradeable names in the book (sel = finite y4 & qv4h>=2.5e5 & universe); causal expanding terciles over the rec sequence since 2022. Causal cuts at window end [183.0, 288.0]; descriptive (window) cuts [266.0, 330.0].

| bucket | PIT/prod/42/cal | PIT/prod/2027/cal | PIT/log/42/cal | PIT/log/2027/cal | FRZ/prod/42/cal | REF T400/log/42 |
|---|---|---|---|---|---|---|
| causal low (var mean —) | n 0 | n 0 | n 0 | n 0 | n 0 | n 0 |
| causal mid (var mean 259.47) | 5.04 [2.27, 7.60] · S 7.74 · 221%/yr · n 358 | 5.14 [2.39, 7.78] · S 7.89 · 225%/yr · n 358 | 4.63 [1.98, 7.30] · S 6.83 · 203%/yr · n 358 | 4.60 [1.87, 7.29] · S 6.79 · 202%/yr · n 358 | 6.03 [1.72, 10.27] · S 8.65 · 264%/yr · n 182 | 4.43 [1.43, 7.54] · S 6.58 · 194%/yr · n 320 |
| causal high (var mean 307.54) | 0.92 [0.25, 1.55] · S 1.73 · 40%/yr · n 5360 | 0.94 [0.28, 1.57] · S 1.78 · 41%/yr · n 5360 | 0.92 [0.25, 1.55] · S 1.76 · 40%/yr · n 5360 | 0.98 [0.32, 1.60] · S 1.89 · 43%/yr · n 5360 | 1.26 [0.54, 2.00] · S 2.11 · 55%/yr · n 5536 | 1.07 [0.40, 1.75] · S 1.99 · 47%/yr · n 5398 |
| descriptive low (var mean 249.22) | 0.58 [-0.38, 1.48] · S 1.31 · 26%/yr · n 1907 | 0.61 [-0.35, 1.53] · S 1.37 · 27%/yr · n 1907 | 0.57 [-0.40, 1.46] · S 1.27 · 25%/yr · n 1907 | 0.57 [-0.36, 1.47] · S 1.28 · 25%/yr · n 1907 | 0.36 [-0.76, 1.45] · S 0.66 · 16%/yr · n 1939 | 0.88 [-0.11, 1.82] · S 1.91 · 38%/yr · n 1907 |
| descriptive mid (var mean 298.94) | 1.99 [0.73, 3.24] · S 3.31 · 87%/yr · n 1911 | 2.06 [0.79, 3.31] · S 3.45 · 90%/yr · n 1911 | 1.88 [0.60, 3.13] · S 3.17 · 82%/yr · n 1911 | 2.00 [0.78, 3.21] · S 3.39 · 88%/yr · n 1911 | 2.36 [1.16, 3.57] · S 3.81 · 104%/yr · n 1873 | 1.92 [0.76, 3.06] · S 3.22 · 84%/yr · n 1943 |
| descriptive high (var mean 365.66) | 0.95 [-0.23, 2.14] · S 1.69 · 42%/yr · n 1900 | 0.93 [-0.21, 2.09] · S 1.66 · 41%/yr · n 1900 | 1.00 [-0.16, 2.21] · S 1.83 · 44%/yr · n 1900 | 1.06 [-0.07, 2.21] · S 1.92 · 46%/yr · n 1900 | 1.55 [0.20, 2.97] · S 2.42 · 68%/yr · n 1906 | 0.97 [-0.28, 2.18] · S 1.68 · 42%/yr · n 1868 |

### T8-neg_fund_share. Slice 2024→cut: negative-funding share of members (30-anchor trailing mean) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: share of META members with 8h-equiv rate < 0, 30-anchor trailing mean. Causal cuts at window end [0.1247, 0.2686]; descriptive (window) cuts [0.1201, 0.2573].

| bucket | PIT/prod/42/cal | PIT/prod/2027/cal | PIT/log/42/cal | PIT/log/2027/cal | FRZ/prod/42/cal | REF T400/log/42 |
|---|---|---|---|---|---|---|
| causal low (var mean 0.04) | 1.04 [0.02, 2.16] · S 2.16 · 46%/yr · n 1588 | 1.05 [0.03, 2.17] · S 2.19 · 46%/yr · n 1588 | 1.04 [0.04, 2.16] · S 2.19 · 46%/yr · n 1588 | 1.07 [0.07, 2.16] · S 2.25 · 47%/yr · n 1588 | 1.31 [-0.01, 2.69] · S 2.13 · 57%/yr · n 1588 | 0.97 [-0.12, 2.08] · S 1.93 · 42%/yr · n 1588 |
| causal mid (var mean 0.18) | 1.07 [-0.02, 2.12] · S 1.87 · 47%/yr · n 2182 | 1.10 [0.04, 2.16] · S 1.95 · 48%/yr · n 2182 | 1.07 [0.04, 2.11] · S 1.92 · 47%/yr · n 2182 | 1.10 [0.10, 2.13] · S 2.00 · 48%/yr · n 2182 | 1.50 [0.31, 2.69] · S 2.47 · 66%/yr · n 2182 | 1.23 [0.18, 2.29] · S 2.20 · 54%/yr · n 2182 |
| causal high (var mean 0.34) | 1.41 [0.29, 2.52] · S 2.56 · 62%/yr · n 1948 | 1.44 [0.31, 2.56] · S 2.60 · 63%/yr · n 1948 | 1.34 [0.20, 2.47] · S 2.42 · 58%/yr · n 1948 | 1.44 [0.34, 2.55] · S 2.61 · 63%/yr · n 1948 | 1.40 [0.19, 2.61] · S 2.38 · 61%/yr · n 1948 | 1.53 [0.35, 2.72] · S 2.70 · 67%/yr · n 1948 |
| descriptive low (var mean 0.05) | 0.66 [-0.41, 1.77] · S 1.34 · 29%/yr · n 1906 | 0.60 [-0.46, 1.65] · S 1.23 · 26%/yr · n 1906 | 0.74 [-0.30, 1.80] · S 1.55 · 32%/yr · n 1906 | 0.71 [-0.32, 1.75] · S 1.49 · 31%/yr · n 1906 | 1.07 [-0.22, 2.29] · S 1.78 · 47%/yr · n 1906 | 0.74 [-0.35, 1.81] · S 1.48 · 32%/yr · n 1906 |
| descriptive mid (var mean 0.19) | 1.57 [0.40, 2.75] · S 2.74 · 69%/yr · n 1906 | 1.62 [0.46, 2.76] · S 2.86 · 71%/yr · n 1906 | 1.46 [0.33, 2.64] · S 2.60 · 64%/yr · n 1906 | 1.49 [0.38, 2.63] · S 2.68 · 65%/yr · n 1906 | 1.94 [0.72, 3.29] · S 3.15 · 85%/yr · n 1906 | 1.64 [0.47, 2.86] · S 2.90 · 72%/yr · n 1906 |
| descriptive high (var mean 0.34) | 1.30 [0.08, 2.40] · S 2.34 · 57%/yr · n 1906 | 1.40 [0.14, 2.53] · S 2.50 · 61%/yr · n 1906 | 1.26 [0.01, 2.38] · S 2.25 · 55%/yr · n 1906 | 1.43 [0.19, 2.55] · S 2.56 · 63%/yr · n 1906 | 1.23 [-0.04, 2.39] · S 2.07 · 54%/yr · n 1906 | 1.40 [0.12, 2.57] · S 2.44 · 61%/yr · n 1906 |

### T8-btc_rv30. Slice 2024→cut: BTC 30-day realised vol (annualised %) — mean net bps/anchor per gross [CI95] · anchor Sharpe · NAV %/yr at 2× (arith) · n

definition: annualised %, 5m returns, 30 days. Causal cuts at window end [42.9338, 54.9238]; descriptive (window) cuts [40.8418, 53.437].

| bucket | PIT/prod/42/cal | PIT/prod/2027/cal | PIT/log/42/cal | PIT/log/2027/cal | FRZ/prod/42/cal | REF T400/log/42 |
|---|---|---|---|---|---|---|
| causal low (var mean 36.46) | 0.97 [-0.01, 1.96] · S 1.87 · 43%/yr · n 2304 | 1.04 [0.07, 1.99] · S 2.01 · 46%/yr · n 2304 | 1.16 [0.21, 2.11] · S 2.29 · 51%/yr · n 2304 | 1.23 [0.27, 2.18] · S 2.45 · 54%/yr · n 2304 | 1.53 [0.43, 2.64] · S 2.59 · 67%/yr · n 2304 | 1.38 [0.37, 2.38] · S 2.63 · 60%/yr · n 2304 |
| causal mid (var mean 51.82) | 1.35 [0.29, 2.41] · S 2.37 · 59%/yr · n 2318 | 1.33 [0.26, 2.40] · S 2.33 · 58%/yr · n 2318 | 1.15 [0.08, 2.22] · S 2.03 · 50%/yr · n 2318 | 1.17 [0.12, 2.23] · S 2.07 · 51%/yr · n 2318 | 1.38 [0.18, 2.54] · S 2.20 · 60%/yr · n 2318 | 1.04 [-0.05, 2.11] · S 1.81 · 46%/yr · n 2318 |
| causal high (var mean 64.66) | 1.22 [-0.17, 2.63] · S 2.41 · 54%/yr · n 1096 | 1.28 [-0.12, 2.70] · S 2.51 · 56%/yr · n 1096 | 1.14 [-0.26, 2.55] · S 2.21 · 50%/yr · n 1096 | 1.24 [-0.14, 2.65] · S 2.39 · 54%/yr · n 1096 | 1.24 [-0.38, 2.84] · S 2.16 · 54%/yr · n 1096 | 1.47 [0.03, 2.89] · S 2.79 · 64%/yr · n 1096 |
| descriptive low (var mean 35.11) | 0.96 [-0.11, 2.05] · S 1.90 · 42%/yr · n 1906 | 1.00 [-0.07, 2.09] · S 1.98 · 44%/yr · n 1906 | 1.17 [0.18, 2.26] · S 2.40 · 51%/yr · n 1906 | 1.20 [0.22, 2.26] · S 2.47 · 53%/yr · n 1906 | 1.58 [0.39, 2.80] · S 2.80 · 69%/yr · n 1906 | 1.45 [0.41, 2.58] · S 2.82 · 64%/yr · n 1906 |
| descriptive mid (var mean 48.06) | 1.39 [0.19, 2.63] · S 2.29 · 61%/yr · n 1906 | 1.48 [0.30, 2.72] · S 2.47 · 65%/yr · n 1906 | 1.29 [0.07, 2.56] · S 2.16 · 56%/yr · n 1906 | 1.47 [0.30, 2.70] · S 2.49 · 64%/yr · n 1906 | 1.28 [-0.09, 2.53] · S 1.92 · 56%/yr · n 1906 | 1.17 [-0.09, 2.41] · S 1.95 · 51%/yr · n 1906 |
| descriptive high (var mean 61.10) | 1.18 [0.22, 2.23] · S 2.34 · 52%/yr · n 1906 | 1.13 [0.15, 2.20] · S 2.22 · 50%/yr · n 1906 | 1.00 [0.03, 2.00] · S 1.95 · 44%/yr · n 1906 | 0.96 [0.01, 2.01] · S 1.85 · 42%/yr · n 1906 | 1.38 [0.27, 2.60] · S 2.41 · 60%/yr · n 1906 | 1.16 [0.16, 2.19] · S 2.21 · 51%/yr · n 1906 |

### T9. Turnover, cost and carry per window (per unit gross; cost_ex and carry_ex from the rec; shares = Σ over the window / Σ gross price P&L)

| arm | window | turnover/gross per anchor | cost bps/anchor/gross | cost %/yr NAV @2× | carry paid bps/anchor/gross | carry %/yr NAV @2× | gross price P&L bps/anchor/gross | cost share | carry share | net bps/anchor/gross |
|---|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 2024->26 | 0.0684 | 0.182 | 7.97 | 0.607 | 26.58 | 2.049 | 0.070 | 0.340 | 1.260 |
| REF T400/log/42 | 2025->26 | 0.0629 | 0.188 | 8.25 | 0.851 | 37.29 | 2.689 | 0.052 | 0.329 | 1.649 |
| REF T400/log/42 | 2026->cut | 0.0309 | 0.117 | 5.12 | 1.179 | 51.66 | 4.506 | 0.026 | 0.260 | 3.209 |
| PIT/prod/42/def | 2024->26 | 0.0721 | 0.195 | 8.52 | 0.547 | 23.94 | 1.873 | 0.084 | 0.336 | 1.132 |
| PIT/prod/42/def | 2025->26 | 0.0656 | 0.201 | 8.81 | 0.765 | 33.52 | 2.381 | 0.063 | 0.333 | 1.414 |
| PIT/prod/42/def | 2026->cut | 0.0341 | 0.128 | 5.61 | 1.022 | 44.77 | 4.372 | 0.029 | 0.232 | 3.222 |
| PIT/prod/2027/def | 2024->26 | 0.0681 | 0.182 | 7.99 | 0.556 | 24.36 | 1.904 | 0.080 | 0.334 | 1.165 |
| PIT/prod/2027/def | 2025->26 | 0.0600 | 0.184 | 8.07 | 0.780 | 34.17 | 2.393 | 0.061 | 0.337 | 1.428 |
| PIT/prod/2027/def | 2026->cut | 0.0360 | 0.134 | 5.89 | 1.019 | 44.64 | 4.289 | 0.031 | 0.235 | 3.135 |
| PIT/log/42/def | 2024->26 | 0.0690 | 0.188 | 8.22 | 0.552 | 24.20 | 1.850 | 0.079 | 0.339 | 1.110 |
| PIT/log/42/def | 2025->26 | 0.0638 | 0.196 | 8.56 | 0.773 | 33.88 | 2.355 | 0.061 | 0.336 | 1.386 |
| PIT/log/42/def | 2026->cut | 0.0327 | 0.123 | 5.40 | 1.040 | 45.54 | 4.251 | 0.029 | 0.242 | 3.088 |
| PIT/log/2027/def | 2024->26 | 0.0652 | 0.176 | 7.70 | 0.562 | 24.63 | 1.909 | 0.074 | 0.330 | 1.171 |
| PIT/log/2027/def | 2025->26 | 0.0583 | 0.179 | 7.84 | 0.787 | 34.46 | 2.427 | 0.058 | 0.331 | 1.462 |
| PIT/log/2027/def | 2026->cut | 0.0343 | 0.129 | 5.64 | 1.037 | 45.42 | 4.242 | 0.030 | 0.242 | 3.077 |
| PIT/prod/42/cal | 2024->26 | 0.0721 | 0.151 | 6.63 | 0.547 | 23.94 | 1.873 | 0.064 | 0.336 | 1.175 |
| PIT/prod/42/cal | 2025->26 | 0.0656 | 0.138 | 6.06 | 0.765 | 33.52 | 2.381 | 0.042 | 0.333 | 1.477 |
| PIT/prod/42/cal | 2026->cut | 0.0341 | 0.075 | 3.28 | 1.022 | 44.77 | 4.372 | 0.017 | 0.232 | 3.275 |
| PIT/prod/2027/cal | 2024->26 | 0.0681 | 0.143 | 6.28 | 0.556 | 24.36 | 1.904 | 0.061 | 0.334 | 1.204 |
| PIT/prod/2027/cal | 2025->26 | 0.0600 | 0.127 | 5.57 | 0.780 | 34.17 | 2.393 | 0.041 | 0.337 | 1.485 |
| PIT/prod/2027/cal | 2026->cut | 0.0360 | 0.079 | 3.44 | 1.019 | 44.64 | 4.289 | 0.018 | 0.235 | 3.191 |
| PIT/log/42/cal | 2024->26 | 0.0690 | 0.145 | 6.36 | 0.552 | 24.20 | 1.850 | 0.060 | 0.339 | 1.152 |
| PIT/log/42/cal | 2025->26 | 0.0638 | 0.135 | 5.90 | 0.773 | 33.88 | 2.355 | 0.040 | 0.336 | 1.446 |
| PIT/log/42/cal | 2026->cut | 0.0327 | 0.072 | 3.16 | 1.040 | 45.54 | 4.251 | 0.017 | 0.242 | 3.139 |
| PIT/log/2027/cal | 2024->26 | 0.0652 | 0.137 | 6.02 | 0.562 | 24.63 | 1.909 | 0.057 | 0.330 | 1.210 |
| PIT/log/2027/cal | 2025->26 | 0.0583 | 0.124 | 5.41 | 0.787 | 34.46 | 2.427 | 0.038 | 0.331 | 1.517 |
| PIT/log/2027/cal | 2026->cut | 0.0343 | 0.075 | 3.29 | 1.037 | 45.42 | 4.242 | 0.017 | 0.242 | 3.130 |
| FRZ/prod/42/cal | 2024->26 | 0.0749 | 0.158 | 6.91 | 0.543 | 23.80 | 2.114 | 0.061 | 0.302 | 1.413 |
| FRZ/prod/42/cal | 2025->26 | 0.0680 | 0.144 | 6.29 | 0.758 | 33.22 | 2.766 | 0.039 | 0.289 | 1.864 |
| FRZ/prod/42/cal | 2026->cut | 0.0352 | 0.077 | 3.39 | 1.078 | 47.22 | 4.626 | 0.017 | 0.233 | 3.471 |
| FRZ/prod/2027/cal | 2024->26 | 0.0715 | 0.151 | 6.61 | 0.553 | 24.21 | 2.213 | 0.058 | 0.292 | 1.509 |
| FRZ/prod/2027/cal | 2025->26 | 0.0633 | 0.134 | 5.87 | 0.768 | 33.66 | 2.836 | 0.038 | 0.286 | 1.934 |
| FRZ/prod/2027/cal | 2026->cut | 0.0372 | 0.081 | 3.55 | 1.077 | 47.18 | 4.574 | 0.018 | 0.235 | 3.416 |

### T9b. Δ(live fee-only − device default cost), same universe/caliber/seed — mean net bps/anchor per gross (paired by construction: identical books, only COST_B differs)

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| PIT/prod/42/cal − PIT/prod/42/def | 0.012 (cost 0.184→0.172) | 0.069 (cost 0.246→0.177) | 0.053 (cost 0.128→0.075) | 0.043 (cost 0.195→0.151) | 0.063 (cost 0.201→0.138) |
| PIT/prod/2027/cal − PIT/prod/2027/def | 0.010 (cost 0.180→0.170) | 0.058 (cost 0.215→0.157) | 0.056 (cost 0.134→0.079) | 0.039 (cost 0.182→0.143) | 0.057 (cost 0.184→0.127) |
| PIT/log/42/cal − PIT/log/42/def | 0.013 (cost 0.175→0.162) | 0.067 (cost 0.239→0.173) | 0.051 (cost 0.123→0.072) | 0.042 (cost 0.188→0.145) | 0.061 (cost 0.196→0.135) |
| PIT/log/2027/cal − PIT/log/2027/def | 0.011 (cost 0.171→0.160) | 0.056 (cost 0.209→0.153) | 0.054 (cost 0.129→0.075) | 0.038 (cost 0.176→0.137) | 0.055 (cost 0.179→0.124) |

### T9c. Δ(U-FROZEN − U-PIT), prod caliber, live fee-only cost — mean net bps/anchor per gross (unpaired books; U-FROZEN carries look-ahead selection)

| pair | 2024 | 2025 | 2026->cut | 2024->26 | 2025->26 |
|---|---|---|---|---|---|
| FRZ/prod/42/cal − PIT/prod/42/cal | -0.002 (S 1.25 vs 1.55) | 0.504 (S 1.46 vs 0.69) | 0.196 (S 5.15 vs 5.06) | 0.238 (S 2.34 vs 2.18) | 0.387 (S 2.94 vs 2.50) |
| FRZ/prod/2027/cal − PIT/prod/2027/cal | 0.074 (S 1.52 vs 1.70) | 0.585 (S 1.71 vs 0.81) | 0.224 (S 5.06 vs 4.95) | 0.305 (S 2.52 vs 2.23) | 0.449 (S 3.06 vs 2.51) |

### T10. Replay form by year — mean gross of the unit book, tradeable names (nsel), king seat w3_king, net long, stop fires, king/fund leg returns (bps/anchor unit-gross rank book)

| arm | window | gross_total | nsel | w3_king | w3_fund | net long | fires | leg_king | leg_fund |
|---|---|---|---|---|---|---|---|---|---|
| REF T400/log/42 | 2024-H1 | 0.778 | 257 | 0.332 | 0.668 | -0.0017 | 235 | -0.412 | -0.007 |
| REF T400/log/42 | 2024-H2 | 0.428 | 287 | 0.943 | 0.057 | -0.0039 | 123 | 2.760 | -0.222 |
| REF T400/log/42 | 2025 | 0.531 | 375 | 0.673 | 0.327 | -0.0407 | 584 | 1.492 | 0.888 |
| REF T400/log/42 | 2026->cut | 0.780 | 328 | 0.368 | 0.632 | -0.0614 | 415 | 1.157 | 3.350 |
| PIT/prod/42/def | 2024-H1 | 0.743 | 247 | 0.421 | 0.579 | 0.0003 | 201 | -0.408 | -0.087 |
| PIT/prod/42/def | 2024-H2 | 0.438 | 269 | 0.941 | 0.059 | -0.0033 | 125 | 3.025 | -0.208 |
| PIT/prod/42/def | 2025 | 0.535 | 354 | 0.687 | 0.313 | -0.0373 | 484 | 1.424 | 0.764 |
| PIT/prod/42/def | 2026->cut | 0.785 | 299 | 0.382 | 0.618 | -0.0584 | 374 | 1.164 | 3.144 |
| PIT/prod/2027/def | 2024-H1 | 0.743 | 247 | 0.421 | 0.579 | -0.0008 | 211 | -0.408 | -0.087 |
| PIT/prod/2027/def | 2024-H2 | 0.437 | 269 | 0.941 | 0.059 | -0.0056 | 129 | 3.025 | -0.208 |
| PIT/prod/2027/def | 2025 | 0.554 | 354 | 0.687 | 0.313 | -0.0408 | 491 | 1.424 | 0.764 |
| PIT/prod/2027/def | 2026->cut | 0.787 | 299 | 0.382 | 0.618 | -0.0562 | 373 | 1.164 | 3.144 |
| PIT/log/42/def | 2024-H1 | 0.783 | 247 | 0.332 | 0.668 | -0.0002 | 222 | -0.412 | -0.007 |
| PIT/log/42/def | 2024-H2 | 0.435 | 269 | 0.943 | 0.057 | -0.0040 | 119 | 2.760 | -0.222 |
| PIT/log/42/def | 2025 | 0.543 | 354 | 0.673 | 0.327 | -0.0376 | 448 | 1.492 | 0.888 |
| PIT/log/42/def | 2026->cut | 0.793 | 299 | 0.368 | 0.632 | -0.0575 | 354 | 1.157 | 3.350 |
| PIT/log/2027/def | 2024-H1 | 0.783 | 247 | 0.332 | 0.668 | 0.0001 | 217 | -0.412 | -0.007 |
| PIT/log/2027/def | 2024-H2 | 0.436 | 269 | 0.943 | 0.057 | -0.0065 | 123 | 2.760 | -0.222 |
| PIT/log/2027/def | 2025 | 0.561 | 354 | 0.673 | 0.327 | -0.0416 | 473 | 1.492 | 0.888 |
| PIT/log/2027/def | 2026->cut | 0.796 | 299 | 0.368 | 0.632 | -0.0528 | 350 | 1.157 | 3.350 |
| PIT/prod/42/cal | 2024-H1 | 0.743 | 247 | 0.421 | 0.579 | 0.0003 | 201 | -0.408 | -0.087 |
| PIT/prod/42/cal | 2024-H2 | 0.438 | 269 | 0.941 | 0.059 | -0.0033 | 125 | 3.025 | -0.208 |
| PIT/prod/42/cal | 2025 | 0.535 | 354 | 0.687 | 0.313 | -0.0373 | 484 | 1.424 | 0.764 |
| PIT/prod/42/cal | 2026->cut | 0.785 | 299 | 0.382 | 0.618 | -0.0584 | 374 | 1.164 | 3.144 |
| PIT/prod/2027/cal | 2024-H1 | 0.743 | 247 | 0.421 | 0.579 | -0.0008 | 211 | -0.408 | -0.087 |
| PIT/prod/2027/cal | 2024-H2 | 0.437 | 269 | 0.941 | 0.059 | -0.0056 | 129 | 3.025 | -0.208 |
| PIT/prod/2027/cal | 2025 | 0.554 | 354 | 0.687 | 0.313 | -0.0408 | 491 | 1.424 | 0.764 |
| PIT/prod/2027/cal | 2026->cut | 0.787 | 299 | 0.382 | 0.618 | -0.0562 | 373 | 1.164 | 3.144 |
| PIT/log/42/cal | 2024-H1 | 0.783 | 247 | 0.332 | 0.668 | -0.0002 | 222 | -0.412 | -0.007 |
| PIT/log/42/cal | 2024-H2 | 0.435 | 269 | 0.943 | 0.057 | -0.0040 | 119 | 2.760 | -0.222 |
| PIT/log/42/cal | 2025 | 0.543 | 354 | 0.673 | 0.327 | -0.0376 | 448 | 1.492 | 0.888 |
| PIT/log/42/cal | 2026->cut | 0.793 | 299 | 0.368 | 0.632 | -0.0575 | 354 | 1.157 | 3.350 |
| PIT/log/2027/cal | 2024-H1 | 0.783 | 247 | 0.332 | 0.668 | 0.0001 | 217 | -0.412 | -0.007 |
| PIT/log/2027/cal | 2024-H2 | 0.436 | 269 | 0.943 | 0.057 | -0.0065 | 123 | 2.760 | -0.222 |
| PIT/log/2027/cal | 2025 | 0.561 | 354 | 0.673 | 0.327 | -0.0416 | 473 | 1.492 | 0.888 |
| PIT/log/2027/cal | 2026->cut | 0.796 | 299 | 0.368 | 0.632 | -0.0528 | 350 | 1.157 | 3.350 |
| FRZ/prod/42/cal | 2024-H1 | 0.754 | 168 | 0.421 | 0.579 | -0.0035 | 135 | -0.408 | -0.087 |
| FRZ/prod/42/cal | 2024-H2 | 0.457 | 196 | 0.941 | 0.059 | -0.0000 | 74 | 3.025 | -0.208 |
| FRZ/prod/42/cal | 2025 | 0.552 | 292 | 0.687 | 0.313 | -0.0225 | 460 | 1.424 | 0.764 |
| FRZ/prod/42/cal | 2026->cut | 0.785 | 281 | 0.382 | 0.618 | -0.0573 | 379 | 1.164 | 3.144 |
| FRZ/prod/2027/cal | 2024-H1 | 0.756 | 168 | 0.421 | 0.579 | -0.0045 | 136 | -0.408 | -0.087 |
| FRZ/prod/2027/cal | 2024-H2 | 0.456 | 196 | 0.941 | 0.059 | -0.0012 | 87 | 3.025 | -0.208 |
| FRZ/prod/2027/cal | 2025 | 0.572 | 292 | 0.687 | 0.313 | -0.0240 | 476 | 1.424 | 0.764 |
| FRZ/prod/2027/cal | 2026->cut | 0.788 | 281 | 0.382 | 0.618 | -0.0543 | 374 | 1.164 | 3.144 |

### T11. Caliber reconciliation — unit replay book (net_ex, gross floats; = RECEIPT_EX / earlier STATE numbers) vs per-gross (executor caliber, this report)

| arm | window | unit-book net_ex bps/anchor | unit-book Sharpe | per-gross bps/anchor | per-gross Sharpe | mean gross_total |
|---|---|---|---|---|---|---|
| REF T400/log/42 | 2024 | 0.149 | 0.53 | 0.636 | 1.41 | 0.602 |
| REF T400/log/42 | 2025 | 0.359 | 1.15 | 0.701 | 1.26 | 0.531 |
| REF T400/log/42 | 2026->cut | 2.512 | 4.83 | 3.209 | 4.84 | 0.780 |
| REF T400/log/42 | 2024->26 | 0.780 | 2.16 | 1.260 | 2.30 | 0.617 |
| PIT/prod/42/cal | 2024 | 0.177 | 0.67 | 0.691 | 1.55 | 0.589 |
| PIT/prod/42/cal | 2025 | 0.130 | 0.42 | 0.383 | 0.69 | 0.535 |
| PIT/prod/42/cal | 2026->cut | 2.582 | 5.04 | 3.275 | 5.06 | 0.785 |
| PIT/prod/42/cal | 2024->26 | 0.719 | 2.03 | 1.175 | 2.18 | 0.614 |
| PIT/prod/2027/cal | 2024 | 0.232 | 0.88 | 0.754 | 1.70 | 0.589 |
| PIT/prod/2027/cal | 2025 | 0.166 | 0.52 | 0.448 | 0.81 | 0.554 |
| PIT/prod/2027/cal | 2026->cut | 2.528 | 4.94 | 3.191 | 4.95 | 0.787 |
| PIT/prod/2027/cal | 2024->26 | 0.741 | 2.07 | 1.204 | 2.23 | 0.622 |

### T12. 2026-08-11 → 2026-08-30 (after the F10 cut; F10 leg absent ⇒ NOT the live form; shown only because it overlaps the live window 08-26 →)

| arm | n anchors | mean bps/anchor/gross | Sharpe | NAV total % @2× | worst day % @2× |
|---|---|---|---|---|---|
| REF T400/log/42 | 120 | -4.270 | -5.97 | -9.98 | -3.82 |
| PIT/prod/42/def | 120 | -4.383 | -5.93 | -10.25 | -3.82 |
| PIT/prod/2027/def | 120 | -4.194 | -5.66 | -9.84 | -3.81 |
| PIT/log/42/def | 120 | -4.310 | -5.64 | -10.11 | -3.89 |
| PIT/log/2027/def | 120 | -4.259 | -5.57 | -10.00 | -3.90 |
| PIT/prod/42/cal | 120 | -4.340 | -5.87 | -10.15 | -3.82 |
| PIT/prod/2027/cal | 120 | -4.151 | -5.61 | -9.75 | -3.81 |
| PIT/log/42/cal | 120 | -4.267 | -5.59 | -10.01 | -3.89 |
| PIT/log/2027/cal | 120 | -4.216 | -5.52 | -9.90 | -3.90 |
| FRZ/prod/42/cal | 120 | -3.371 | -4.55 | -8.04 | -3.75 |
| FRZ/prod/2027/cal | 120 | -3.280 | -4.42 | -7.84 | -3.76 |

### T13. Receipts

- COST_B override (calib/costb_fee_steady.json sha256[:16] ddb07d3c5b294bfa): tier0: maker 1.8001 / taker 4.5001 bps, maker share 0.8511, maker fill ratio 0.804 (after top-up 0.9446); tier1: maker 1.799 / taker 4.4988 bps, maker share 0.9246, maker fill ratio 0.8712 (after top-up 0.9422); tier2: maker 1.7998 / taker 4.5002 bps, maker share 0.921, maker fill ratio 0.8479 (after top-up 0.9207). Source: cost_calib.json calib.primary_steady.tiers (steady anchors n=51, 08-26 04Z -> 09-05 00Z), fee-only vector = VERIFIED per cost-calib REPORT §8; maker_bps/taker_bps = venue fee with BNB discount, maker_share = share of filled notional per tier. cost_calib.json sha256 87250dde4ff73be7…, its self_sha256 ff3ec02f1fa61367…, run 2026-09-05T04:38:56Z.
- Not used (INFERRED): fee − raw markout per tier [[15.99, 73.27, 0.851], [12.67, 2.51, 0.925], [-2.42, 6.65, 0.921]]; fee − delay-reweighted markout pooled {'maker_bps': 8.53, 'taker_bps': 57.75, 'maker_share': 0.913, 'per_unit_turnover_bps': 12.82}. Why: INFERRED: markout on a 5% non-random backfilled subset (68/134/128 maker marks; taker leg on 9/10/2 marks); PREREG §1 keeps the paper-vs-real twin band as the execution-discount band instead
- Twin band (cost-calib §9, n=53): paper(shifted) − twin -1.23 bps/anchor of gross, CI95 [-6.1, 3.72]; twin + funding 0.26 CI95 [-8.5, 8.91].

`logs/check_equiv.log`:
```
PASS [pristine 5424aceb vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_pristine_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=5cd88da0ab1301b9 sha(ref)=b20ec4fba5695d51
PASS [w10_health.py default path vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10038, 23), (10038, 23)), 'd30_n2_c42_W': ((10038, 829), (10038, 829)), 'S0_W': ((10038, 829), (10038, 829))} nan_in_mine {'d30_n2_c42_rec': 0, 'S0_rec': 0, 'd30_n2_c42_W': 0, 'S0_W': 0} config_equal(minus self-report keys)=True sha(mine)=8bfe59b6ebc0a8c4 sha(ref)=b20ec4fba5695d51
CHAIN_EQ_DONE 2026-09-05T04:38:13Z
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

`logs/commands.txt` (every device run, verbatim; earlier UPIT_*_cdef runs on the pre-fix mask were overwritten by the final chain — see the last CMD/END pair per tag):
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
```
