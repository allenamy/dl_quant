> **创建:** 2026-09-13 06:0xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (subagent T2) | **状态:** 已判 — criteria frozen in `PREREG_T2_carry_net_sizing_2026-09-13.md` sha256 **981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca** (`receipts/PREREG_FREEZE_sha.txt`, frozen 05:16:41Z before any κ estimate or arm run); no amendment; no arm, threshold or reading changed after any number | **作废条件:** a chain newer than v4 passing its gates; replacement of the archived A0 / NW / r15 ARM-S artifacts; a change of the pinned device b88e35a4… or the r18 device 9b8a6323… | **口径:** v4 (`CALIBER_PIN_v4_2026-09-11.md`), RAW accounting y4 from `meta_newprod_v4.npz`, cost `costb_PWR_G230k.json` λ=1.0; every table below is copied from `receipts/TABLES_T2.md`, rendered from receipts by `devices/t2_tables.py`
> **仪器:** single instrument pod2, CPU only; `nvidia-smi` 0 % / 2 MiB before and after every step; PIDs 333197 / 339489 `Tl` throughout, never signalled | **实盘零接触:** `~/dl_quant_live` and `~/wide_shadow` not opened; no API call; not committed

# RESULT T2 · Sizing the funding leg on expected net return (price edge − uncompensated carry)

## §0 One page

1. **Both positive controls passed, bitwise.** κ≡0 reproduces A0 and NW bit for bit on both constructions and both seeds (rec 10039×23 and W 10039×829, maxabs 0.0). κ≡1 on the seat construction reproduces the archived r15 ARM-S rec and W bit for bit, so its Δg is **−0.0928 (s42) / −0.0894 (s2027)** exactly. The lead's κ≡1 control is only definable for a seat-level construction; the name-level arm the lead described in (ii) has no archived counterpart, so a wiring check replaced it (12/12 fund-score vectors equal to an independent re-implementation). The prereg declared both constructions for that reason (§0 of the prereg).
2. **κ* is not a stable constant.** The walk-forward uncompensated fraction is at the clip value 1.0 on most refits from mid-2022 to mid-2023 (price did not compensate carry at all; noisy), 0.84–0.96 from 2023-08 to 2024-08, and then falls steadily to **0.226 at the 2026-08-01 refit, CI95 [−0.008, +0.460]**. W_ALPHA mean 0.727; first half 0.931, second half 0.524. The program's "≈ 23 %" is the value of the last two refits only.
3. **Holding carry fixed, the fund score has no identifiable positive price edge of its own.** |λ̂| < 2 SE at every refit except 2025-02 to 2025-04, where it is significantly negative (t −2.21 to −2.33); λ̂ is negative at every refit from 2024-08 to 2026-05, so λ⁺ is floored at 0 on 4572 of 9138 W_ALPHA anchors. On those anchors "expected net" is −κ*·carry alone. ARM-N therefore largely inverted the fund leg (mean correlation of the adjusted with the original fund score −0.20) and turned book carry from paid (+0.48) to received (−0.81 bps/anchor/unit gross).
4. **Verdicts against the frozen rule (A0 base, W_ALPHA, both seeds): nothing promoted.**

| arm | Δg s42 [CI95] | Δg s2027 [CI95] | Δτ | verdict |
|---|---|---|---|---|
| ARM-N (name, scalar κ*) | −0.3011 [−0.9486, +0.3600] | −0.2938 [−0.9426, +0.3707] | +86 % / +84 % | UNDECIDED (fails CI95 > 0, maxDD, HALT) |
| ARM-Nσ (name, κ* by σ_fund tercile) | +0.1693 [−0.4206, +0.7419] | +0.1857 [−0.4164, +0.7564] | +123 % / +120 % | **UNDECIDED (LEAK-SUSPECT)** |
| ARM-SK (seat, scalar κ*) | −0.0267 [−0.2432, +0.1909] | −0.0232 [−0.2361, +0.1829] | +20 % / +20 % | UNDECIDED (fails CI95 > 0, HALT) |

5. **The ceiling tripwire fired for ARM-Nσ and the §7 investigation failed.** Its point estimate exceeded 0.165 on both seeds. With a one-month-stale κ path the gain falls to +0.041 / +0.049 (24–26 % of itself); with a 4h-stale carry input it vanishes (−0.017 / −0.003); with look-ahead it roughly triples (path +0.54, carry +0.32). By the frozen rule that is the leak signature, so the +0.17 is not reported as an effect. The standing causality gates did pass (C1: the estimator never reads future rows; C2: positions up to T* are bitwise unchanged when every future return value and every future funding row is garbled), so the cause is not a future-row read by the estimator or the device; it is unresolved (§5).
6. **Even ignoring the tripwire, ARM-Nσ does not help where it matters.** Its gain is 2022 +0.76, 2023 +0.61 / +0.57, 2024 +0.54 / +0.52; it loses in 2025 (−0.59 / −0.48), in 2026 (−0.37 / −0.33), on KING_LIVE (−0.11 / −0.07) and in the replayed live window (−8.1 / −6.6 bps/anchor over 30 anchors). ARM-N has the same shape with larger 2025–2026 losses (2026 −3.24 / −3.23).
7. **The ceiling's premise did not describe what the name arms did.** P5 bounds an arm that stops paying the uncompensated part of 0.48 bps of carry (≤ 0.11). Both name arms instead flipped the book to receiving carry (Δcarry −1.29 / −1.24, about 11× the ceiling's premise) and paid for it in price (Δpnl −1.46 / −0.88) and turnover. The seat arm moved carry by only −0.07.
8. **Live window.** The replay covers only 2026-08-26 00Z → 08-30 20Z (30 anchors): ARM-N −0.93 / +0.08, ARM-Nσ −8.09 / −6.64, ARM-SK −0.017 / −0.0004 (5 day-clusters, CIs meaningless). September cannot be replayed for any PHI>0 book (F10 predictions end 2026-08-30 20Z). The per-name regression on 2026-08-26 → 09-10 (r6 extension, 91 anchors) reads b̂ 1.35, κ_raw −0.35 [−1.65, +0.95], λ̂ −11 bps per rank unit (SE 11 bps): price compensation of carry did not visibly break in the live window, while the fund score's own edge was negative; 16 clusters make both readings descriptive only.
9. **NW base changes nothing:** every Δg moves by ≤ 0.012 and every verdict is identical (§4). **Deployability:** none; every arm is a book-behaviour change and this round only measured.

## §1 Gates (positive controls first; `receipts/RECEIPT_T2_drive.json`, `RECEIPT_T2_kappa_main.json`)

| gate | run | reference | rec bitwise | W bitwise | extra |
|---|---|---|---|---|---|
| GATE P | GP_A0_s42 | archived A0 | True | True | cols equal True, T2_MODE off |
| GATE P | GP_NW_s42 | archived NW | True | True | cols equal True, T2_MODE off |
| GATE P | GP_A0_s2027 | archived A0 | True | True | cols equal True, T2_MODE off |
| GATE P | GP_NW_s2027 | archived NW | True | True | cols equal True, T2_MODE off |
| PC-0 | PC0N_A0_s42 | archived A0 | True | True | anchors through the rank path 4567 |
| PC-0 | PC0S_A0_s42 | archived A0 | True | True | seat kappa values used [0.0] |
| PC-0 | PC0N_NW_s42 | archived NW | True | True | anchors through the rank path 4567 |
| PC-0 | PC0S_NW_s42 | archived NW | True | True | seat kappa values used [0.0] |
| PC-0 | PC0N_A0_s2027 | archived A0 | True | True | anchors through the rank path 4567 |
| PC-0 | PC0S_A0_s2027 | archived A0 | True | True | seat kappa values used [0.0] |
| PC-0 | PC0N_NW_s2027 | archived NW | True | True | anchors through the rank path 4567 |
| PC-0 | PC0S_NW_s2027 | archived NW | True | True | seat kappa values used [0.0] |
| PC-1 | PC1S_A0_s42 | archived r15 S_s42 | True | True | Δg vs A0 W_ALPHA -0.0927614 → -0.0928 (target -0.0928, match True) |
| PC-1 | PC1S_A0_s2027 | archived r15 S_s2027 | True | True | Δg vs A0 W_ALPHA -0.0893916 → -0.0894 (target -0.0894, match True) |
| WIRE | WIRE_A0_s42 | independent re-implementation | — | — | (a) g differs on 100.0% of W_ALPHA anchors (pass True); (b) FZ_book bitwise 12/12 (pass True) |
| WIRE | WIRE_A0_s2027 | independent re-implementation | — | — | (a) g differs on 99.9% of W_ALPHA anchors (pass True); (b) FZ_book bitwise 12/12 (pass True) |

- **Device.** `devices/w10_sleeve_t2.py` sha256 **380d6265082c67742a8cf47f844d76cf0e3cc3ca25557b29bdaf6c747907d341**, generated by `mk_t2_device.py` from the r18 device (sha asserted) with 12 once-only replacements (diff 149 lines, `devices/w10_sleeve_t2.diff`); generated independently on the Mac and on pod2 from each machine's r18 copy, equal. Every run self-reported that sha (asserted by the driver). PC-0 exercised the rank-of-expected-net path on 4567 of the 10039 booked anchors (the rest are inactive by rule: before the first active refit, or λ⁺ = 0 with κ forced to 0), which is what makes the κ≡0 control informative for the name construction.
- **C1 (estimator future-invariance): PASS 12/12** refits (2022-06 … 2026-09): the scalar, σ-bin and diagnostic estimates are bitwise identical after replacing every y4 row with E_ts > T−8h and every panel funding row with ts > T−8h by seeded garbage (up to 9319 rows garbled).
- **C2 (device shuffle-future, T* = 2024-07-16 00Z): PASS** for the A0 baseline and all three arms on both seeds. Future y4 values permuted within row (4662 rows, 3,826,643 cells changed, NaN pattern kept) and future panel funding rows permuted (4656 rows, 10,546,563 cells changed); the re-estimated κ path is bitwise equal for every anchor ≤ T* (7326 later path cells differ, so the garbling bit); `W` rows ≤ T* bitwise equal (5383 rows), rec columns not involving y4[i*] bitwise equal ≤ T*, all rec columns bitwise equal < T*.
- **ENV.** Driver, estimator, judge and tripwire launched `env -i PATH=… HOME=/root … PATH,HOME,LC_CTYPE`; each asserts the whitelist and the absence of every caliber-flag prefix (including `T2`). Each device run received an exact env dict, written key by key to the receipt (e.g. `runs.N_A0_s42.env`: 26 keys).

## §2 The estimand κ* (`receipts/RECEIPT_T2_kappa_main.json`; full refit table in `TABLES_T2.md` T2)

Pooled within-anchor OLS `y_w = a_i + λ·FZ + b·c`, κ*_raw = 1 − b̂, monthly refit on an expanding window using anchors with E_ts ≤ T − 8h; y winsorised ±0.20 for estimation only; SE clustered by UTC day.

| refit T | anchors | λ̂ (return/rank) | SE λ̂ | b̂ | κ*_raw | SE b̂ | κ* used | σ-bin κ_raw low / mid / high | per-side κ⁺ / κ⁻ raw | unwinsorised κ_raw |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-07-01 | 905 | −8.04e-05 | 3.45e-04 | −0.082 | 1.082 | 1.366 | 1.000 | −0.10 / 2.83 / 0.97 | 6.45 / 0.90 | −0.183 |
| 2023-01-01 | 2009 | 1.97e-04 | 1.47e-04 | −0.308 | 1.308 | 0.347 | 1.000 | 2.09 / 2.46 / 1.27 | 6.45 / 1.26 | 1.322 |
| 2023-07-01 | 3095 | 9.94e-05 | 1.18e-04 | −0.046 | 1.046 | 0.357 | 1.000 | 1.55 / 2.47 / 1.00 | 4.30 / 1.00 | 1.057 |
| 2024-01-01 | 4199 | 3.85e-06 | 9.53e-05 | 0.120 | 0.880 | 0.253 | 0.880 | 1.67 / 1.21 / 0.86 | 3.86 / 0.84 | 0.972 |
| 2024-07-01 | 5291 | 3.88e-05 | 8.57e-05 | 0.158 | 0.842 | 0.223 | 0.842 | 1.30 / 0.58 / 0.85 | 3.14 / 0.80 | 0.896 |
| 2025-01-01 | 6395 | −1.43e-04 | 8.53e-05 | 0.444 | 0.556 | 0.217 | 0.556 | 0.84 / 0.96 / 0.53 | 2.59 / 0.50 | 0.571 |
| 2025-07-01 | 7481 | −1.66e-04 | 9.08e-05 | 0.466 | 0.534 | 0.182 | 0.534 | 1.50 / 0.50 / 0.53 | 0.50 / 0.54 | 0.529 |
| 2026-01-01 | 8585 | −9.91e-05 | 9.18e-05 | 0.517 | 0.483 | 0.144 | 0.483 | 1.69 / 0.44 / 0.48 | 1.01 / 0.46 | 0.569 |
| 2026-07-01 | 9671 | 5.48e-05 | 8.95e-05 | 0.686 | 0.314 | 0.110 | 0.314 | 1.51 / 0.21 / 0.32 | 1.19 / 0.28 | 0.245 |
| **2026-08-01** | 9857 | 4.38e-05 | 9.14e-05 | 0.774 | **0.226** | 0.119 | 0.226 | 1.45 / 0.10 / 0.23 | 1.16 / 0.19 | 0.167 |

- **Level (M1, final refit 2026-08-01):** κ*_raw **0.226, CI95 [−0.008, +0.460]** (SE_day 0.119, SE_week 0.121). The CI excludes 1 but not 0: "price returns most of the carry" is supported at the end of the sample, the size of the uncompensated remainder is not pinned. λ̂ 4.4e-05 (SE 9.1e-05).
- **Stability:** κ* used on W_ALPHA ranged 0.226 → 1.000 over 51 refits; mean 0.727; first half 0.931, second half 0.524; 1824 anchors ran on a clipped κ*_raw > 1; 4572 anchors ran with λ⁺ floored at 0. A yearly refit (diagnostic d3) gives the same path in steps, κ_raw 2023-01 1.31, 2024-01 0.88, 2025-01 0.56, 2026-01 0.48 (W_ALPHA mean κ* 0.752, with 2022 uncovered).
- **State dependence (ARM-Nσ path):** κ* is highest when funding dispersion is low (mean κ* by bin 0.97 / 0.83 / 0.63 low → high σ_fund); the low-σ bin's κ_raw is above 1 at 44 of the 47 refits from 2022-11 on (below 1 only at 2023-05, 2025-01, 2025-02; 1.45 at the end), i.e. in low dispersion price did not compensate carry in this sample. Consistent in direction with `seat_is_blind_to_the_funding_fuel_gauge` (fund leg loses at σ < 4.75).
- **Per side (diagnostic d2):** at the end κ⁻_raw 0.19 (SE b⁻ 0.12; carry paid by shorts of negative funding is well compensated) and κ⁺_raw 1.16 (SE b⁺ 0.62; carry paid by longs of positive funding shows no compensation, poorly identified). This partial-slope reading is a different estimand from trackA's sleeve reading (trimming high-funding longs gave up 3.81 bps of price per bp of carry); the two are not in conflict and are not reconciled here.

## §3 Arms against the frozen rule — A0 base, W_ALPHA n = 9138 (`RECEIPT_T2_judge.json`)

| arm | seed | reference | Δg | CI95 | CI99-K (K=3) | Δpnl | Δcarry | Δcost | Δpnl/Δcarry | carry arm / base | τ matched arm / base | Δτ % | Sharpe arm / base | ΔSharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ARM-N | s42 | A0_s42 (GP_A0_s42) | **-0.3011** | [-0.9486, +0.3600] | [-1.1209, +0.5246] | -1.4556 | -1.2891 | +0.1346 | 1.13 | -0.8094 / 0.4797 | 0.10031 / 0.05403 | +85.7% | 0.623 / 1.291 | -0.668 |
| ARM-N | s2027 | A0_s2027 (GP_A0_s2027) | **-0.2938** | [-0.9426, +0.3707] | [-1.1149, +0.5562] | -1.4464 | -1.2879 | +0.1353 | 1.12 | -0.8170 / 0.4709 | 0.10187 / 0.05540 | +83.9% | 0.682 / 1.330 | -0.647 |
| ARM-Nσ | s42 | A0_s42 (GP_A0_s42) | **+0.1693** | [-0.4206, +0.7419] | [-0.5672, +0.8713] | -0.8759 | -1.2392 | +0.1940 | 0.71 | -0.7596 / 0.4797 | 0.12050 / 0.05403 | +123.0% | 1.541 / 1.291 | +0.250 |
| ARM-Nσ | s2027 | A0_s2027 (GP_A0_s2027) | **+0.1857** | [-0.4164, +0.7564] | [-0.5475, +0.8776] | -0.8591 | -1.2394 | +0.1946 | 0.69 | -0.7685 / 0.4709 | 0.12204 / 0.05540 | +120.3% | 1.622 / 1.330 | +0.292 |
| ARM-SK | s42 | A0_s42 (GP_A0_s42) | **-0.0267** | [-0.2432, +0.1909] | [-0.3041, +0.2199] | -0.0677 | -0.0716 | +0.0306 | 0.95 | 0.4081 / 0.4797 | 0.06482 / 0.05403 | +20.0% | 1.200 / 1.291 | -0.091 |
| ARM-SK | s2027 | A0_s2027 (GP_A0_s2027) | **-0.0232** | [-0.2361, +0.1829] | [-0.2830, +0.2179] | -0.0600 | -0.0688 | +0.0320 | 0.87 | 0.4021 / 0.4709 | 0.06660 / 0.05540 | +20.2% | 1.248 / 1.330 | -0.081 |

| arm | A0 verdict | flags | clauses (s42 / s2027) | M2 carry reduced | tripwire | NW reading |
|---|---|---|---|---|---|---|
| ARM-N | **UNDECIDED (fails: CI95 lower > 0, maxDD not worse, HALT not worse)** | — | CI95 lo>0 False/False; maxDD not worse False/False; HALT not worse False/False; C2 True | True | not_fired | same |
| ARM-Nσ | **UNDECIDED (LEAK-SUSPECT)** | BELOW-RESOLUTION | CI95 lo>0 False/False; maxDD not worse True/True; HALT not worse False/False; C2 True | True | fired_fail | same |
| ARM-SK | **UNDECIDED (fails: CI95 lower > 0, HALT not worse)** | BELOW-RESOLUTION | CI95 lo>0 False/False; maxDD not worse True/True; HALT not worse False/False; C2 True | True | not_fired | same |

- No arm is REJECT: every CI95 upper bound is above 0, including ARM-N's (the name arms rebuild the fund leg, so their paired Δ is nearly as noisy as an unpaired one).
- "maxDD not worse" and "HALT not worse" are single-path point comparisons inside the decision rule, not a statistical non-inferiority proof.
- **What the arms did to the book** (T10): ARM-N used the rank-of-expected-net path on 100 % of anchors, ranked the fund leg on −κ*·carry alone on 50.0 %, changed ~286 names' fund score per anchor, mean |ΔFZ| 0.322, mean corr(adjusted, original) **−0.199**. ARM-Nσ: 98.2 % / 39.6 % / ~283 names / 0.286 / **−0.045**. ARM-SK moved the seat toward king: w3_king 0.638 vs 0.462 (2022 0.50 vs 0.16, 2023 0.45 vs 0.18, 2024 0.91 vs 0.71, 2025 0.79 vs 0.71, 2026 0.38 vs 0.36), a shift of +0.176, i.e. 87 % of ARM-S's +0.202 (r15 §8, s42) at mean κ 0.73.
- **Mechanism readouts:** M2 engaged for all three (book carry reduced on both seeds). M1: κ* identified only as "< 1" at the end of the sample (§2).

## §4 Tail, per year, KING_LIVE, NW base

**Tail, W_TAIL n = 10038, fixed 2.0× NAV, UTC-day compounding, NAV prepend 1.0 (A0 base):**

| arm | seed | maxDD arm / base | peak→trough arm | worst day arm (ret) | HALT arm / base | ALERT arm / base | ann ret arm / base |
|---|---|---|---|---|---|---|---|
| ARM-N | s42 | -0.5113 / -0.4599 | 2025-09-01→2026-07-02 | 2025-09-12 (-0.1014) | 14 / 6 | 40 / 24 | 0.1177 / 0.2473 |
| ARM-N | s2027 | -0.4907 / -0.4646 | 2025-09-01→2026-07-02 | 2025-09-12 (-0.0986) | 14 / 7 | 37 / 27 | 0.1318 / 0.2588 |
| ARM-Nσ | s42 | -0.2998 / -0.4599 | 2025-09-01→2025-10-18 | 2025-09-12 (-0.1014) | 9 / 6 | 34 / 24 | 0.3612 / 0.2473 |
| ARM-Nσ | s2027 | -0.2556 / -0.4646 | 2025-09-01→2025-10-18 | 2025-09-12 (-0.0986) | 9 / 7 | 32 / 27 | 0.3833 / 0.2588 |
| ARM-SK | s42 | -0.3392 / -0.4599 | 2022-04-03→2024-07-18 | 2022-06-07 (-0.1117) | 8 / 6 | 27 / 24 | 0.2325 / 0.2473 |
| ARM-SK | s2027 | -0.3550 / -0.4646 | 2022-04-03→2024-07-18 | 2022-06-07 (-0.1117) | 9 / 7 | 25 / 27 | 0.2457 / 0.2588 |

Both name arms move their worst day to 2025-09-12 (−10.1 % / −9.9 % at 2×; A0's is 2022-06-07 at −11.2 %, NW's −6.4 %) and add halt days. The shallower maxDD of ARM-Nσ and ARM-SK also comes with more halt days.

**Per calendar year, A0 base (Δg; full g and Sharpe per arm × seed × base in `TABLES_T2.md` T7):**

| arm | seed | 2022 (from 06-30) | 2023 | 2024 | 2025 | 2026 (to 08-30) |
|---|---|---|---|---|---|---|
| A0 g / Sharpe | s42 | +0.1586 / 0.48 | −0.6485 / −1.94 | +0.4865 / 1.09 | +0.6770 / 1.19 | +3.0913 / 4.52 |
| ARM-N Δg | s42 / s2027 | +0.578 / +0.578 | +0.814 / +0.783 | +0.531 / +0.530 | −0.749 / −0.690 | **−3.239 / −3.233** |
| ARM-Nσ Δg | s42 / s2027 | +0.764 / +0.764 | +0.614 / +0.567 | +0.544 / +0.519 | −0.592 / −0.481 | −0.374 / −0.330 |
| ARM-SK Δg | s42 / s2027 | 0.000 / 0.000 | +0.135 / +0.118 | +0.317 / +0.289 | −0.447 / −0.433 | −0.177 / −0.108 |

Every arm gains in 2023 and 2024 (the name arms also in 2022; ARM-SK's 2022 Δg is exactly 0 although its seat moves, because king and F10 are both dead before 2023, so the book is the fund leg alone and the seat weight cancels in the L1 normalisation) and loses in 2025 and 2026, the years the fund leg's price edge was richest. ARM-Nσ's 2026 g stays high (+2.72 / +2.77, Sharpe 4.26 / 4.33) but below A0's (+3.09).

**KING_LIVE (W_ALPHA ∩ ts ≥ 2024-01-01, n = 5838), A0 base:** ARM-N −0.8865 [−1.8900, +0.0395] / −0.8634 [−1.8614, +0.0639]; ARM-Nσ −0.1104 [−0.9339, +0.6554] / −0.0671 [−0.8930, +0.7181]; ARM-SK −0.0925 [−0.4680, +0.2645] / −0.0804 [−0.4313, +0.2613]. All negative on both seeds.

**NW base (robustness reading, Δ vs NW of the same seed):** ARM-N −0.3010 / −0.3021; ARM-Nσ +0.1679 / +0.1740; ARM-SK −0.0289 / −0.0348; CIs, decomposition, turnover and tail clauses as on A0 (T5/T6); every verdict identical.

## §5 Ceiling tripwire and §7 investigation (`receipts/RECEIPT_T2_tripwire.json`)

**Fired:** ARM-Nσ only (Δg +0.1693 / +0.1857 > 0.165). ARM-N and ARM-SK did not fire.

| offset (ARM-Nσ, A0 base, W_ALPHA) | s42 Δg [CI95] | s2027 Δg [CI95] | ratio to offset 0 (s42 / s2027) | role |
|---|---|---|---|---|
| 0 (as registered) | +0.1693 [−0.4206, +0.7419] | +0.1857 [−0.4164, +0.7564] | 1 / 1 | — |
| κ path one refit stale | +0.0411 [−0.5725, +0.6430] | +0.0486 [−0.5729, +0.6484] | 0.24 / 0.26 | **gate: ≥ 0.5 → FAIL** |
| carry input one anchor stale (row j−1) | −0.0169 [−0.6070, +0.5441] | −0.0028 [−0.5870, +0.5593] | −0.10 / −0.01 | **gate: ≥ 0.5 → FAIL** |
| κ path one refit look-ahead | +0.5364 [−0.0160, +1.0969] | +0.5445 [−0.0059, +1.1050] | 3.17 / 2.93 | reported |
| carry input one anchor future (row j+1) | +0.3244 [−0.2834, +0.8991] | +0.3144 [−0.2886, +0.8853] | 1.92 / 1.69 | reported |

**⇒ §7 FAIL ⇒ UNDECIDED (LEAK-SUSPECT); the +0.17 is not an effect.** What is and is not known about the cause:
- **Ruled out (VERIFIED):** the estimator reading future rows (C1) and the device reading future returns or funding rows (C2).
- **Checked from source (VERIFIED):** the panel builder (`runpod_scripts/workspace_mirror/pod_panel_ext.py` sha256 db7f0474…, identical to pod2 `/workspace/pod_panel_ext.py`) sets `f_fund_now` at anchor E to the last settled rate with fundingTime ≤ E (`searchsorted(side="right")`, NaN if older than 12h). The rate is known at E, so the panel is causal, but with zero latency: when a settlement lands on the anchor, that just-settled rate is used at E, while the live executor trades about 24 minutes later.
- **One candidate explanation tested and not supported (POST-HOC, no verdict weight, `receipts/POSTHOC_T2_settlement_hour_split.json`):** if the gain lived in the post-settlement drift that a zero-latency book captures, it would concentrate at 00/08/16Z anchors, where 8h names settle. It does the opposite: ARM-Nσ Δg at 00/08/16Z −0.3168 [−1.085, +0.478] / −0.2869, at 04/12/20Z +0.6553 [−0.174, +1.434] / +0.6584; by hour, 00Z −1.21 / −1.11 and 04Z +1.33 / +1.43.
- **Not resolved:** whether the collapse with a 4h-stale carry input comes from 4h-interval names (whose rate changes every anchor), from EMA path dependence, or from over-fitting of the monthly σ-bin estimates (the 3× look-ahead spike says the arm's value depends heavily on the current month's estimate). The discriminating checks — Δg split by each name's settlement interval, and re-pricing the arm from the executor's trade time — were not run.

## §6 Live window

- **Replay part (2026-08-26 00Z → 08-30 20Z, n = 30, 5 UTC days; A0 base):** ARM-N g +3.70 / +4.60 vs A0 +4.62 / +4.51 (Δg −0.93 / +0.08); ARM-Nσ g −3.47 / −2.13 (Δg **−8.09 / −6.64**, Δpnl −10.98 / −9.52, Δcarry −3.30); ARM-SK Δg −0.017 / −0.0004. Day-block CIs over 5 days are printed in T8 and are uninformative by construction.
- **Not replayable:** 2026-09-01 → 09-11. The r6 extension has no F10/V2MAIN predictions after 2026-08-30 20Z (every PHI>0 book, A0 included), and 2026-08-31 is contaminated (E-0911-B).
- **Estimand on the live window (diagnostic d4, r6 extension tree, prefix bitwise equal to the incumbent meta and panel, September umask = the 2026-08-31 00Z row carried forward):** 91 anchors, 21,789 name-anchors, 16 day clusters: b̂ 1.348, κ_raw −0.348, CI95 [−1.651, +0.955] (SE_day 0.665, SE_week 0.222); λ̂ −1.11e-03 (SE 1.09e-03); per side κ⁺_raw 3.43 (SE b⁺ 2.90), κ⁻_raw −0.39 (SE b⁻ 0.66). Descriptive: the point estimates say price kept compensating carry and the fund score's own edge was negative, the opposite of "compensation broke" (T1's H4). The day-clustered interval excludes κ = 1, but with 16 clusters it is not a reliable interval (the week-clustered SE of b̂ is 0.22 against 0.66 by day, a sign the clustering itself is unstable); this does not settle H4.

## §7 Could not verify, limitations, incidents

1. **The cause of the ARM-Nσ §7 failure** (§5). Its verdict is LEAK-SUSPECT under the frozen rule, not a demonstrated leak.
2. **The lead's κ≡1 control does not exist for the name construction.** It was met exactly on the seat construction; the name construction got a wiring check instead (prereg §0). ARM-SK is a dose between A0 and ARM-S, not an expected-net seat: the realized leg price already contains the compensation, so subtracting κ*·carry with κ* < 1 adds the compensated part back.
3. **λ is not identified.** With the fund score's partial edge floored at 0 on half of W_ALPHA, ARM-N ranks half the sample on −κ*·carry alone. That is what the registered estimand implies; a construction that keeps the fund leg's direction (for example a per-side κ, diagnostic d2) was not pre-registered and was not run.
4. **Baseline limits carried from r15/r18:** the archived A0 carries v3-lineage model legs; king is dead before 2024-01-01 and F10 before 2023-01-01, so 2022–2023 (where every arm gains) is a fund-dominated book. Single instrument; cost model POWER λ = 1.0 (turnover +84 % to +123 % on the name arms makes their Δg sensitive to it; the in-book marginal cost is inside Δg).
5. **No null family** beyond C1/C2/§7 (the κ path is estimated, so there is no dose to match).
6. **Incident, driver:** the first driver launch completed waves 1–2 (28 device runs, every gate PASS, `receipts/logs/t2_drive_launch1_killed_in_wave3_garble.log`) and then stalled building the C2 garbled tree, because a loop re-read the compressed meta/panel members once per row. I killed my own driver process (PID 553962, verified by command line; protected PIDs untouched), patched the loop to read each member once and write through tmp + rename, and relaunched. The relaunch reused the 28 cached artifacts (same device sha and env dicts), so `RECEIPT_T2_drive.json` records them as `cached` with their gates recomputed from the artifacts; wave 3 and the garbled estimator ran fresh. The first launch's driver sha was not recorded; it differed from the final `t2_drive.py` only in that wave-3 block, whose outputs it never produced.
7. **Incident, estimator (before its first run):** moment sums and 2×2 / 3×3 inverses were moved from BLAS/LAPACK to explicit numpy sums and closed forms, so C1 and the C2 path comparison can demand bitwise equality. Judge: the pre-tripwire receipt is kept as `RECEIPT_T2_judge_pre_tripwire.json`; the final receipt was built after `RECEIPT_T2_tripwire.json` existed.
8. The lead has not re-run the key numbers; nothing here enters STATE.

## §8 Receipts and verbatim commands

- Prereg: `PREREG_T2_carry_net_sizing_2026-09-13.md` (981293b0…), `receipts/PREREG_FREEZE_sha.txt`.
- Devices (`devices/`, identical sha on the Mac and pod2): `mk_t2_device.py` e843a7bc…, `w10_sleeve_t2.py` 380d6265… (+ `.diff`), `t2_kappa.py` 23b5af6b…, `t2_drive.py` 9847229e…, `t2_judge.py` 02d88984…, `t2_tripwire.py` 5578d4ea…, `t2_tables.py`, `t2_posthoc_hour_split.py` (post-hoc).
- Receipts (`receipts/`): `RECEIPT_T2_kappa_main.json` (refits, C1, d1–d4), `RECEIPT_T2_kappa_garbled.json`, `RECEIPT_T2_drive.json` (gates, env dicts, input realpaths + sha, C2), `RECEIPT_T2_judge.json`, `RECEIPT_T2_judge_pre_tripwire.json`, `RECEIPT_T2_tripwire.json`, `POSTHOC_T2_settlement_hour_split.json`, `TABLES_T2.md`, `kpath/` (main, stale1, lookahead1, garbled κ paths), `arms_rec/` (rec + T2 aux + config for the 4 baselines and 12 arms, `SHA256_arms_rec.json`), `logs/` (every device, estimator, driver, judge and tripwire log). Full artifacts with W: pod2 `/workspace/uplift_r2_2026-09-13/T2/arms/` (765 MB), garbled tree `dev_garbled/` (217 MB).
- Commands (pod2, cwd `/workspace/uplift_r2_2026-09-13/T2`):
```
/workspace/venv/bin/python devices/mk_t2_device.py /workspace/uplift_2026-09-11/r18_foundation/devices/w10_sleeve_r18.py devices/w10_sleeve_t2.py PREREG_T2_carry_net_sizing_2026-09-13.md
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_kappa.py PATH,HOME,LC_CTYPE main
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_drive.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_judge.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_tripwire.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_judge.py PATH,HOME,LC_CTYPE
```
(the driver itself launches `env -i PATH=… HOME=/root /workspace/venv/bin/python devices/t2_kappa.py PATH,HOME,LC_CTYPE garbled` for C2). Mac, cwd = this directory:
```
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t2_tables.py .
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t2_posthoc_hour_split.py .
```
- `SHA256SUMS.txt` covers every file in this directory.

## §9 Number labels
§1–§6 numbers: **VERIFIED** (computed this round on pod2 from the archived inputs, rendered from receipts). The hour split in §5 and the panel-builder reading are **VERIFIED as facts** but **POST-HOC** (not pre-registered, no verdict weight). The explanation of the §7 failure is **not established**. Program facts P1/P4/P5 and trackA/r15 numbers are **INFERRED** here (quoted from their receipts).
