> **创建:** 2026-09-13 11:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker L4, dispatched by lead) | **状态:** PREREG — frozen before any sleeve, carry or combination number; paper study, research only (a spot leg in the executor needs the user's word; this study proposes nothing) | **作废条件:** any input sha256 in §7 differs at run time; T7 `T7_universe_elig.npz` (a530e123…) or T6 `T6_SERIES_s{42,2027}.npz` replaced; any change to §2–§6 after the first reading is printed (only a dated AMENDMENT written before readings may change them)

# PREREG · L4 · Low-turnover delta-neutral funding carry sleeve with hysteresis re-selection (paper)

Program: `../PROGRAM_uplift_r3_2026-09-13.md` §2 L4 (fact #8). Prior receipts: `docs/RESULT_carry_sleeve_diagnostic_2026-09-05.md` (device `allweather_2026-09-05/carry_sleeve_diag/carry_sleeve.py`): under the frozen top-K re-selection rule income +1.72 vs cost 4.47 bps/anchor per perp gross (K10/h5), break-even 5.4/8.7 bps per unit turnover, zero-cost income Sharpe 12–44 with ρ ≈ 0 to the book, 2023 71 % of anchors without a qualifying name; hysteresis was never evaluated. `docs/RESULT_carry_layers_2026-09-05.md`: funding paid is compensated by settlement-window price moves; for a hedged sleeve that effect can only reach P&L through the perp–spot basis, which this study marks (§2.5).

## §0 Question

Does a long-spot / short-perp funding carry sleeve that enters and exits on a trailing funding EMA with hysteresis, a minimum holding period and a maximum name count, costed at 3.92 bps (perp) + 10 bps (spot) per unit turnover and marked with the perp–index premium, earn a net return per unit of total capital (spot + perp margin) that is (i) positive in every year it is invested, (ii) bounded away from zero over 2024–2026, and (iii) weakly correlated with the A0 replay book? And does it add anything in 2023?

## §1 What was looked at before this freeze (disclosure)

- Documents: the program; the two RESULT docs above and memory notes `carry_sleeve_second_premium_diagnostic_2026_09_05`, `funding_transfer_priced_in_settlement_window`, `funding_settlement_window_momentum_dodge_refuted_2026_09_05`, `f2_basis_leg_judged_negative`; T5b RESULT §5.1/§6.3 (x0910 `f_fund_iv`); T6 RESULT (incl. §11) and `t6_compute.py`; T7 RESULT §5 (mapping rule, guard) and `t7_universe_pod2.py`; T8 RESULT header (A0 = r18 C0); r5_basis `build_panel.py` / `fetch.py`; allweather trackA `stream_a1.py`, `build_a1_spot.py`, `build_a2_premidx.py`, `coverage.json`, pod cleanup receipt.
- Data engineering only (no returns): file ranges and hashes (§7); `fund_aug.json.gz` = 827 names, first record 2021-12-01 00:00Z, last 2026-09-01 02:00Z; fundingTime ms remainders 0–4; second-of-hour 0 (2,474,222 records) or 1 (29); spacing histogram (4h 1,494,219 / 8h 896,348 / 1h 79,063 / 2h 3,653 / other ≤ 67); 47 same-hour record pairs with different rates (first examples AAPL/AMAT/AVGO/BABA/BX); vision monthly fundingRate zips carry `calc_time, funding_interval_hours, last_funding_rate`. Coverage on eligible cells (T7 `elig_NW`) by year 2022…2026: spot-mapped share 0.984 / 0.977 / 0.953 / 0.830 / 0.750; of mapped cells, trackA a1 `basis` finite 0.993 / 0.995 / 0.978 / 0.977 / 0.986 and r5 premium `p_last` finite 0.998 / 0.998 / 1.000 / 0.999 / 0.984.
- Not computed before this freeze: any funding-level or premium-level distribution, any EMA value, any sleeve position, income, basis, cost, net, Sharpe, correlation or combination.
- The prior study's published numbers (quoted in the program and the lead's task) were known; the thresholds in §3 are placed relative to Binance's baseline interest component (1 bps per 8h) and the prior study's h ∈ {5, 10} bps per settlement, not tuned on new data.

## §2 Definitions

### §2.1 Grid, windows, units
- 4h anchors E (00/04/08/12/16/20Z). Signal grid from 2021-11-30 20Z. **Evaluation window W** = 2022-01-31 00Z … 2026-08-30 20Z (10,038 anchors = T6 W_FULL axis); anchor i's return covers (E_i, E_i + 4h]. The sleeve starts flat at 2022-01-31 00Z; positions open at the end are marked, not liquidated.
- Years: **Y22** 2022-01-31…2022-12-31, **Y23**, **Y24**, **Y25**, **Y26** 2026-01-01…2026-08-30 20Z. **S2426** = 2024-01-01 00Z…2026-08-30 20Z. **FULL** = W.
- No anchor after 2026-08-30 20Z is traded (the last window ends 2026-08-31 00Z). **No panel `f_fund_iv` (v2ext, x0910 or any other) and no x0910 panel is read anywhere.**
- Sleeve returns: bps per anchor per unit of sleeve capital. Sharpe = mean / std(ddof=1) × √2190. APR % = mean × 2190 / 100. maxDD from Π(1 + r/1e4).

### §2.2 Funding records (income and signal)
- Source: pod2 `/workspace/fund_aug.json.gz` (fapi fundingRate full history pulled 2026-09-01; the source of the carry_layers settlement table `sett_tables.npz`, which is used as a gate in §6). Each record (fundingTime, rate) is one settlement event at hour S = ⌊fundingTime/1000/3600⌋ × 3600. All records are kept; same-hour duplicates count as separate events (count reported, including how many fall on held names).
- **Interval from true timestamps only**: each event sits at its own S, so a window sum over (E, E + 4h] contains 4 / 2 / 1 / 0-or-1 events for 1h / 2h / 4h / 8h names without reading any interval field. The spacing S_n − S_{n−1} is recorded per event and compared with the vision archive's `funding_interval_hours` (descriptive agreement share, §6 G-FUND).
- **A[i,k]** = Σ_{S ∈ (E_i, E_i + 4h]} rate_S (fraction); **NEV[i,k]** = number of events in that window.
- **Signal**: x_{i,k} = 2 × A[i−1,k] × 1e4 (bps per 8h: realised accrual over (E_{i−1}, E_i]); EMA_{i,k} = EMA_{i−1,k} + α (x_{i,k} − EMA_{i−1,k}), α = 1 − 2^(−1/6) (half-life 24h). Initialised EMA = x at the first anchor whose trailing window holds the name's first record; undefined before; **warm** from 18 anchors after initialisation. After a name's records stop, x = 0. EMA_i uses events with S ≤ E_i only.

### §2.3 Spot availability (T7-style mapping + guard)
- **Map**: pod2 `/workspace/review_scratch/allweather_trackA/spot/perp_to_spot_map.json` — 477 of 829 perps mapped by rule `same` (470) or `strip1000` (7, price_mult 1000) against the data.binance.vision spot symbol listing of 2026-09-05 (`s3_spot_symbols.json`, 3,695 symbols, USDT pairs). Unmapped perps (352, incl. tokenized equities and names without a USDT spot pair) are excluded. No manual rename table is added (conservative; declared).
- **Spot tradable at i**: trackA `a1_feat_shift0.npz` feature `basis` (spot close × mult, ffill ≤ 12 bars, over perp close, ffill ≤ 12 bars, minus 1, at the 5-minute row closing at E_i − 5 min) is finite.
- **Listed ≥ 1 day** (T7 "first day ≤ anchor − 1 day"): E_i ≥ (first anchor with spot tradable) + 86,400 s.
- **Price-identity guard** (T7 PASS threshold): |ln(1 + a1basis_{i,k})| ≤ ln 1.25 at anchor i; failing anchors are not enterable (counted).
- **spot_ok[i,k]** = mapped ∧ tradable ∧ listed ≥ 1 day ∧ guard.

### §2.4 Perp-side eligibility
- **elig[i,k]** = T7 `elig_NW[i,k]` (A0 causal rule: finite-qvk member ∩ UPIT_CRYPTO mask ∧ isfinite(y4[i−1]) ∧ qv4h ≥ 2.5e5; cross-checked by T7 against the archived r18 arms on 10,039 anchors with 0 mismatches). Anchors outside the T7 grid or without a panel row: no name eligible.

### §2.5 Basis
- **Primary B2**: r5_basis `basis_panel.npz` `p_last[i,k]` = Binance premium-index close of the 1h bar opening at E_i − 1h (premiumIndexKlines, data.binance.vision archive; causality asserted in `build_panel.py`) = perp premium over the price index, fraction. b̃ = B2 carried forward from its last finite value (for marking only). Entry requires finite p_last at E_i.
- **Cross-check B1** (descriptive only): b1 = 1 / (1 + a1basis) − 1 (Binance perp close over Binance spot close).
- **Not modelled** (declared): the second-order term (1 + r_spot)/(1 + b_in); index-vs-Binance-spot difference inside B2; spot borrow and margin interest; perp liquidation and margin top-ups; drift re-balancing of notionals; idle-cash yield; netting against A0's own positions; any capacity or spot-liquidity limit beyond §2.3/§2.4.

### §2.6 Sleeve state machine (per arm; decisions at E_i use data with timestamp ≤ E_i)
Held set H; per held name: n_sett (events received while held).
1. For each name held over window i−1: n_sett += NEV[i−1,k].
2. **Forced exit** (overrides the minimum hold) if any of: (a) spot not tradable at all of anchors i−5…i; (b) Σ NEV[i−6…i−1, k] = 0 (no funding event in (E_i − 24h, E_i]); (c) p_last non-finite at all of anchors i−5…i. Reasons counted.
3. **Normal exit**: EMA_{i,k} < h_out ∧ n_sett ≥ min_hold.
4. **Entry**: candidates = not held ∧ not exited at this anchor ∧ elig ∧ spot_ok ∧ warm ∧ p_last finite ∧ EMA_{i,k} ≥ h_in; ranked by EMA descending (tie: lower symbol index); fill up to K − |H|. Held names are never swapped for better candidates.
5. **Notional** per held name n = 1 / (K (1 + m)) per unit sleeve capital, **m = 0.5** (perp margin 50 % of notional; spot leg fully funded). Undeployed capital earns 0. Deployed share = |H| / K.

### §2.7 Accounting (bps per anchor per unit sleeve capital)
- income_i = Σ_k n_{i,k} × A[i,k] × 1e4 (short perp receives positive funding).
- basis_i = Σ_k n_{i,k} × (b̃_k(E_i) − b̃_k(E_{i+1})) × 1e4 (long spot / short perp gains when the premium falls; telescopes to b̃_in − b̃_out over a hold).
- turnover_i = Σ_k |n_{i,k} − n_{i−1,k}| (notional per unit capital, per leg); cost_i = (c_perp + c_spot) × turnover_i, c_perp = 3.92, **c_spot = 10 (base)**, sensitivities 5 and 15.
- **net_i = income_i + basis_i − cost_i.**
- **A0**: g = T6 `T6_SERIES_s{42,2027}.npz` column `A0_PWR230k_s{seed}` (net_ex/gross_total, bps/anchor/unit gross; r18 C0 = archived A0); per unit capital a_i = G_A × g_i, **G_A = 2.0** (live constant gross).

## §3 Arms (12, fixed; N = 12 enters the program's trial ledger)

| arm | h_in (bps/8h) | h_out (bps/8h) | min_hold (events) | K |
|---|---|---|---|---|
| A01 | 2 | 0.5 | 3 | 10 |
| A02 | 2 | 0.5 | 3 | 20 |
| A03 | 2 | 0.5 | 9 | 10 |
| A04 | 2 | 0.5 | 9 | 20 |
| A05 | 5 | 2 | 3 | 10 |
| A06 | 5 | 2 | 3 | 20 |
| A07 | 5 | 2 | 9 | 10 |
| A08 | 5 | 2 | 9 | 20 |
| A09 | 10 | 4 | 3 | 10 |
| A10 | 10 | 4 | 3 | 20 |
| A11 | 10 | 4 | 9 | 10 |
| A12 | 10 | 4 | 9 | 20 |

Fixed before any number, not arms (researcher choices, declared): EMA half-life 24h, warm-up 18 anchors, forced-exit windows (6 anchors / 24h), guard ln 1.25, m = 0.5, G_A = 2.0, bootstrap block 30 days, B = 20,000. Cost sensitivities, B1 and m = 1.0 are readings, not arms, and never select anything.

## §4 Readings (per arm, base cost, B2, both A0 seeds where A0 enters)

- **R1 per-year table** (Y22…Y26, S2426, FULL): anchors; net mean with CI95 (§4.1); income, basis, cost means; turnover mean; deployed share; **position share** (anchors with |H| ≥ 1); **empty-anchor share** (= 1 − position share); no-candidate share (anchors where no name meets the entry conditions other than "not held"); Sharpe; σ; maxDD; APR %; completed holds; median hold length (anchors); forced exits by reason.
- **R2 net Sharpe**: in R1.
- **R3 break-even per unit turnover** (FULL, S2426, per year): all-in = (income + basis) / turnover; implied spot = all-in − 3.92; income-only = income / turnover.
- **R4 ρ to A0**: Pearson of net_i with a_i per anchor, and of UTC-day sums per day; FULL and per year; seeds 42 and 2027.
- **R5 combination** (FULL, S2426, per year; both seeds): **equal capital EC** r = 0.5 a + 0.5 net: Sharpe, mean, maxDD, ΔSharpe(EC − A0) with paired CI95 (§4.1). **Equal vol EV**: λ_needed = σ(a)/σ(net) on that window; the most the spot leg can be levered (3×, perp margin unchanged) scales returns per capital by k_max = (1 + m)/(1/3 + m) = 1.8; if λ_needed ≤ 1.8 report EV r = 0.5 a + 0.5 λ_needed net (borrow cost not modelled), else **INFEASIBLE** with λ_needed.
- **R6 T6 framing**: (i) nested walk-forward selection over the 12 arms, T6 segments 2023 / 2024 / 2025 / 2026→08-30 20Z, expanding training from 2022-01-31, pick = highest training net Sharpe (std 0 ⇒ not selectable; tie ⇒ lower arm number); nested series, its per-segment table and the pass-rule evaluation of §5.2; (ii) DSR (T6 `psr`/`sr0` formulas) for the arm with the highest S2426 net Sharpe: P(true SR > 0) at N_eff (participation ratio of the 12 S2426 net series, floored at 2), N = 12, and N = 18 (+ the prior sleeve study's 6 arms); (iii) EC increment of the nested-selected sleeve over A0 on the nested span: ΔSharpe and Δmean with paired CI95.
- **R7 2023**: per arm Y23 net mean, position share, ΔSharpe(EC − A0) in Y23 for both seeds; "adds in 2023" = Y23 net mean > 0 ∧ Y23 ΔSharpe > 0 for both seeds (descriptive, not a gate).
- **R8 sensitivities** (descriptive; same positions): c_spot 5 and 15 (R1 means / Sharpe / S2426 CI and the §5 rule evaluated at that cost); basis excluded (income − cost); B1 instead of B2 for marking; m = 1.0 (levels × 0.75, EC recomputed); CI with T6 i.i.d. day blocks and with 7-day blocks.
- **Descriptive**: per-anchor correlation of B1 and B2 basis P&L on held names; interval mix of held names by true spacing; median trackA `qvr_24h` (log spot/perp 24h quote volume) of held names; same-hour duplicate events received; exits marked with a stale b̃.

### §4.1 Bootstrap
Circular block bootstrap over UTC days inside the window: block 30 days, blocks per draw = ⌈n_days/30⌉, truncated to n_days; statistic = Σ day sums / Σ day anchor counts (mean) or the Sharpe of the concatenated days' anchors; B = 20,000; rng `numpy.random.default_rng([20260913, 4, arm_no, span_code, purpose_code])`; quantiles `numpy.percentile` (linear). Paired statistics use the same day draws for both series.

## §5 Frozen pass rule (for later user consideration; not a deployment rule)

### §5.1 Per arm (base cost 10, B2)
- **P0** position share over S2426 ≥ 0.30.
- **P1** for every year in {Y22, Y23, Y24, Y25, Y26} whose position share ≥ 0.30: net mean > 0.
- **P2a** S2426 net mean CI95 lower bound (2.5 % quantile) > 0. **P2b** Bonferroni for 12 arms: the 0.025/12 quantile (0.2083 %) > 0.
- **P3** ρ ≤ 0.30 per anchor **and** per day over FULL, for **both** A0 seeds.
- PASS_adj = P0 ∧ P1 ∧ P2b ∧ P3; PASS_unadj = P0 ∧ P1 ∧ P2a ∧ P3.

### §5.2 Nested selection (T6 framing)
Nested PASS = position share of the nested series over S2426 ≥ 0.30 ∧ net mean > 0 in each nested calendar year (2023…2026) whose position share ≥ 0.30 ∧ S2426 CI95 lower bound > 0 ∧ ρ ≤ 0.30 per anchor and per day over the nested span (2023-01-01…2026-08-30 20Z), both seeds.

### §5.3 Study verdict
- **PASS** (for user consideration): ≥ 1 arm PASS_adj ∧ Nested PASS.
- **FAIL**: no arm PASS_unadj.
- **NOT PASS (multiplicity)**: otherwise.
No other reading (sensitivities, B1, m, EC/EV, DSR, 2023) changes the verdict; each is reported next to it.

## §6 Gates (all must pass before any reading is printed; a failed gate ⇒ stop, no readings, dated AMENDMENT)

| gate | device | rule |
|---|---|---|
| G-IN | build | every input sha256 equals §7 where a value is given; others recorded |
| G-ALIGN | build | symbols identical (829, same order) across T7, r5, a1, and every fund_aug key ⊂ them; W ⊂ T7 grid; r5 ts ⊇ W ∪ {2026-08-31 00Z}; a1 E_ts ⊇ W; T6 ts == W |
| G-A0 | build | T6 series: s42 FROZEN (2025-03-01…2026-08-10 20Z) SR = 2.93571303735249 ± 1e-9; s42 W_FULL SR = 1.1062 ± 5e-5; s2027 FROZEN SR = 2.9021 ± 5e-5 |
| G-FUND | build | vision monthly zips (pod2 `/workspace/wide_multisrc/funding`, 2022-01…2026-07) vs fund_aug matched by (symbol, hour): ≥ 90 % of fund_aug events in (symbol, month)s that have a zip are matched and ≥ 99 % of matched events have \|Δrate\| ≤ 1e-9; unmatched counts both ways and the spacing-vs-`funding_interval_hours` agreement share are reported |
| G-SETT | build | A and NEV vs carry_layers `sett_tables.npz` on shared anchors, excluding cells holding a same-hour duplicate or a second-of-hour-1 record: event presence agrees on every cell and max \|A − nansum(R)\| ≤ 1e-7 |
| G-UNITS | build | (i) among 8h-spaced events at anchors in W with \|rate\| ≥ 10 bps: sign(r5 `p_tw8` at E = S) = sign(rate) in ≥ 90 % for each sign; (ii) on elig ∧ mapped cells in W with both finite and \|p_last\| ≥ 10 bps: Spearman(b1, p_last) ≥ 0.3; median b1/p_last over cells with \|p_last\| ≥ 20 bps in [0.5, 2.0] |
| G-SYN | run | synthetic one-name world (8h events at +10 bps, b ≡ 0 then a planted premium path, then rate −10 bps): entry anchor, per-anchor income (n × 10 bps on event windows), entry/exit cost, exit anchor from an independent EMA recursion, telescoped basis — all exact to 1e-9 |
| G-CAUSAL | run | 20 random cut anchors i* in W (rng [20260913, 4, 99]): replace every event with S > E_{i*} and every elig / spot / a1 / B2 value at anchors > i* with random values ⇒ positions at all anchors ≤ i* bitwise identical for all 12 arms; negative control: add +50 bps to every A[i*−1] ⇒ positions at i* change for ≥ 1 arm in ≥ 1 draw (count reported) |
| G-ACCT | run | net == income + basis − cost (≤ 1e-9); turnover recomputed from positions; Σ basis over each completed hold == n (b̃_in − b̃_out) (≤ 1e-9) |

## §7 Inputs (sha256 asserted by the build device)

| input (pod2) | sha256 |
|---|---|
| `/workspace/fund_aug.json.gz` | 8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2 (= carry_layers `sett_receipt.json`) |
| `/workspace/review_scratch/allweather_trackC/carry_layers/data/sett_tables.npz` | f1c336298fc872997d3f8d9ae3093cc6e123705d11508fe049448082d5fa03cc |
| `/workspace/uplift_r2_2026-09-13/T7/receipts/T7_universe_elig.npz` | a530e123a13d172272a1f36c300eccba945ec8d2303f32556db844c65e256bfb |
| `/workspace/review_scratch/allweather_trackA/features/a1_feat_shift0.npz` | 8136537f593a65004b2df7ae335a37b093188cf534c02b43b41449703eca307a (= trackA `MANIFEST_pod.txt`) |
| `/workspace/review_scratch/allweather_trackA/spot/perp_to_spot_map.json` | b17eb0ba8fb50894bd268cdc79ba382d8c6bf07a43f38886ad8bfab9d0ee717a (= local trackA receipt copy) |
| `/workspace/review_scratch/allweather_trackA/spot/s3_spot_symbols.json` | d2b21f1e8aa1eec8dca45f27911a98d3c6503a482dbe776caf0b230f4b3cdd9d |
| `/workspace/uplift_2026-09-11/r5_basis/basis_panel.npz` | f974317a4988916549cfb0a3a03c2114a69c8370cb9845e8c964fc4dfde08310 (no earlier record; built 2026-09-11 14:21Z by `build_panel.py` fde76150…) |
| `/workspace/uplift_r2_2026-09-13/T6/receipts/T6_SERIES_s42.npz` | a3120f298395cf03346bbdf038aaca2dcfbed25df28a25207788da940d98351e (= T6 `RECEIPT_T6_extract.json`) |
| `/workspace/uplift_r2_2026-09-13/T6/receipts/T6_SERIES_s2027.npz` | 74d4b88d602a0093d999be1f7c546abda832cb1acf1bd3064b82ca9fd6d3a3ee |
| `/workspace/wide_multisrc/funding/<SYM>/<YYYY-MM>.zip` | per-zip sha recorded in the build receipt (gate input only) |

## §8 Devices, runs, outputs

- `devices/l4_build.py` (pod2): gates G-IN…G-UNITS, writes `/workspace/uplift_r3_2026-09-13/L4/work/l4_inputs.npz` + `RECEIPT_L4_build.json`. `devices/l4_run.py` (pod2): asserts the build receipt and inputs sha, gates G-SYN/G-CAUSAL/G-ACCT, then the 12 arms and all readings, `RECEIPT_L4_run.json` + `L4_SERIES.npz` (per-anchor series, registry per T6 §11.1). `devices/l4_tables.py` (local): renders `receipts/TABLES_L4.md` from the receipts only.
- Devices are committed before they run. Runs: foreground, `env -i` whitelist asserted in-device, `nice -n 10 taskset -c 40-47` (8 cores), CPU only, pod2 PIDs 333197 / 339489 untouched, writes < 500 MB (dd probe before larger), no exchange API and no network. Each run leaves stdout, rc and a SUMMARY line; commands transcribed verbatim in the RESULT.
- `RESULT_L4.md` carries every number from `TABLES_L4.md`, verified vs inferred separated, marked "not re-run by lead". `SHA256SUMS` via `uplift_r2_2026-09-13/T6/devices/t6_sha_guard.py`. Commits use explicit pathspecs.

## §9 Limits declared in advance

Paper, single instrument per quantity. Premium index is perp vs a multi-venue index, not Binance spot mid (B1 is the Binance-only cross-check but uses last-trade closes). Spot availability is USDT pairs from a listing taken 2026-09-05 plus anchor-level trading evidence; delisted spot pairs whose archives vanished would be missed. Costs are given numbers; thin spot pairs may cost more than 15 bps. Returns per capital depend on m (Sharpe, signs, CIs and ρ do not). EC/EV use G_A = 2.0 and ignore cross-margining and position netting. The 2022 year starts flat on 2022-01-31. This study cannot say anything about execution, borrow availability or capacity; it can only say whether the paper carry survives its own costs and basis, when it is invested, and how it co-moves with A0.
