# RESULT · r18 · Foundation repair — causal eligibility (N2), warm-up book (WU), true rolling maxDD in the smoothing gate (N4)

> **Created:** 2026-09-12 | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (subagent r18-foundation) | **Branch:** research/book-uplift-2026-09-11 | **Status:** complete; every arm in the prereg reported; numbers rendered from receipts (`receipts/TABLES_r18.md`, `devices/r18_tables.py`) | **Prereg:** `PREREG_r18_foundation_2026-09-12.md` sha256 `51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c` + `PREREG_AMENDMENT_1_r18_2026-09-12.md` sha256 `f8c23823259ee542c29672958ee1f53e066f50022843e9b14e77f88b32994025` (definitional, written after GATE Y failed as registered and before any outcome number; both asserted by every device) | **Caliber:** v4 chain (`CALIBER_PIN_v4_2026-09-11.md`); pinned device `w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650` recomputed on the Mac and on pod2 (equal); derived device `devices/w10_sleeve_r18.py` sha256 `9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4` generated independently on both machines from each machine's pinned copy (equal); cost `costb_PWR_G230k.json` `295b4e7b…`; archived A0 `352ac36f…` (s42) / `aa44e18f…` (s2027) | **Invalidated by:** a newer chain than v4 passing its gates; replacement of the archived A0 arms; a change of the pinned device
> **LIVE ZERO-TOUCH (VERIFIED):** nothing in this round opens `~/dl_quant_live` or `~/wide_shadow`. pod2 CPU only: `nvidia-smi` 0 % / 2 MiB before and after every step; PIDs 333197 / 339489 `Tl` throughout, untouched. Env whitelist for every launch = `{PATH, HOME, LC_CTYPE}` (LC_CTYPE is injected by Python's PEP 538 locale coercion under `env -i`; the first launch without it was refused by the in-file gate and is recorded in `logs/`).

## §0 One page

1. **GATE P passed bitwise** on both seeds: the derived device with every knob at default reproduces the archived A0 `rec` (10039×23) and `W` (10039×829) with `np.array_equal` True, maxabs 0.0. Everything below is measured on the same book.
2. **N2 (eligibility from the return that closed at E, `isfinite(y4[i−1, m])`)** changes eligibility on **15 cells on 12 anchors over the whole history** (12 newly eligible = names that had a completed 4h path at E but are missing in the next 4h — BNXUSDT ×3, LUNAUSDT, EOSUSDT, ANCUSDT, KEEPUSDT, NUUSDT, 1000BTTCUSDT, YFIIUSDT, AKROUSDT, DODOUSDT; 3 newly ineligible = BNXUSDT at its first anchor after a data gap), **5 cells on W_ALPHA**. The reviewer's 108 / 108 / 3 / 0.01184 counts under the OLD rule reproduce exactly (GATE R); **the 3 held positions are no longer zeroed by future information** (W[i] ≠ 0 in all 3, exit at i+1 when the causal rule sees the gap). Δg vs A0: **+0.0020 [−0.004, +0.008] (s42) / +0.0102 [+0.000, +0.023] (s2027)** on W_FULL; +0.0021 / +0.0110 on W_ALPHA — the s2027 CI95 sits just above 0 but the move is 1/20 of the 0.23-bps resolution and Bonferroni-8 includes 0. **A causality defect, real and now closed; economically nil.** Accounting bound of the fix: 12 cells (Σ|sm| 0.047 over the whole history) hold a position whose forward return is unknown and is booked 0.
3. **WU (LEGS mask inside the warm-up return)**: the first 900 anchors (2022-01-31 .. 2022-06-29) now run `w3 = [0.5, 0, 0.5]` instead of `[1/3, 1/3, 1/3]`; **rev24 weight is exactly 0 on all 900 rows and `leg_rev24 ≠ 0` rows go 900 → 0**. The archived A0's worst anchor **2022-06-07 20Z: g −481.36 → −259.36, leg_rev24 −139.30 → 0, leg_fund −93.74 → −140.61** (the fund-only book carries more gross into the same crash); the worst UTC day (still 2022-06-07) **−11.17 % → −6.40 % at 2.0×**. Δg vs A0 on W_FULL −0.0099 [−0.135, +0.137]; on W_ALPHA the fix enters only through EMA / stop-layer state carried across row 900 (−0.0049 [−0.012, +0.001], last differing anchor 2024-02-07); KING_LIVE identical.
4. **NW = N2 + WU is the candidate new baseline.** W_FULL (n = 10038, the full LEGS=101 history including the 2022 stress): **g +0.5532 [+0.109, +1.023], Sharpe 1.115 (SE 0.467), matched turnover 0.05112** (s42) / **+0.5829 [+0.127, +1.076], 1.167, 0.05239** (s2027). W_ALPHA (n = 9138, the published window): **+0.6313 / 1.2846 / 0.05411** and **+0.6640 / 1.3411 / 0.05550** — paired Δ vs the archived A0 (0.6342 / 1.2912): **−0.0028 [−0.012, +0.007]** and **+0.0061 [−0.007, +0.021]**. Distance to A1x (0.6602 / 1.2857, n = 9199, different legs and axis, INFERRED): −0.029 / +0.006 unpaired. **No published verdict changes sign or CI95 status on W_ALPHA (0 / 22 arm×seed cells).** On KING_LIVE two cells move: r15 F05 s2027 (+0.017 → −0.001, an arm whose Δ was already indistinguishable from 0) and r16 X5 s2027 loses its lone CI95-excluding-0 reading (+0.114 [+0.003, +0.227] → +0.097 [−0.020, +0.213]; r16 had already reported it fails Bonferroni).
5. **Full-history tail of the fixed book at 2.0× (raw replay vol): maxDD −43.9 % / −44.5 %, worst day 2022-06-07 −6.40 %, halts 5 / 6 (1.09 / 1.31 per yr), alerts 23 / 26, P(1y true maxDD ≥ 25 %) 26.8 % / 33.1 %.** At 1.00×: maxDD −24.4 % / −24.8 %, 0 halts, P(1y true maxDD ≥ 25 %) 0 %. Under the ×1.4042 sensitivity (not a fact — the reviewer's same-period paired σ ratio is 0.656 [0.467, 1.008]) the 2.0× book has 18 halts, maxDD −65.7 % / −66.6 %, P(1y true maxDD ≥ 25 %) 59.9 % / 57.5 %; at 1.00× P = 15.0 % / 16.8 %.
6. **N4 / LEV12-FIX.** The corrected statistic reconciles to the reviewer to 1e-9 on all six arms (deployed s42, ×1.4042, L = 1.00: **15.34 %** true vs 8.62 % loss-from-start) and my `p_start_loss25` reproduces r12's stored `p_1y_dd_ge25` to 1e-9 on all 32 cells, so the two numbers differ only in the drawdown definition. Under the ≤ 10 % gate at ×1.4042 **no cell in r12's grid is feasible at L = 1.00** except the two α = 0.05, b = 1.25e-4 cells (6.4 % / 6.5 %); every other cell's max feasible L drops to **0.88** (0.75 for α ≥ 0.5). Round-12 claims: (a) deployed feasible at 1.00 — **FAIL** (15.3 %); (b) "+9.2 % at L = 1.00" for (0.05, 2.5e-4) — **FAIL, and it never passed its own gate** (r12's own P was 0.1005 > 0.10); (c) (0.10, 5e-4) feasible at 1.00 — **FAIL** (14.0 %); (d) "slower is better" **survives as a point estimate** (at the common feasible L = 0.88: deployed +0.3 % vs +8.2 % (0.05, 2.5e-4) vs +5.0 % (0.10, 5e-4), both seeds, archived and fixed book, both M) — one historical path, overlapping windows, no CI; (e) "2.0× infeasible for the whole grid" **reaffirmed** (stricter gate). The g-table and its Δg CIs do not depend on the gate and are untouched; on the fixed book the two slower corners read Δg +0.0725 [−0.093, +0.244] / +0.0430 [−0.094, +0.178] (s42) — CI contains 0, as in r12.
7. **Side finding (not pre-registered as a result; quantified, not fixed):** the pinned 5m cache's `ret5` channel is **hard-clipped at ±0.300048828125 per 5-minute bar** (953 bars exactly at the bound, none beyond). The accounting meta's `y4` is RAW (unclipped): on **590 cells / 196 anchors** the two disagree by > 1e-5 (max |Δ| 1.61; **397 cells on 2025-10 alone, 2025-10-10 20Z = the Oct-10 crash**; SOLVUSDT there: meta −48.4 %, clipped-compound +54.9 % — the E-0908-B signature). **Every one of the 590 cells contains a bound-hitting bar; no other cell differs** (`receipts/RECEIPT_r18_clipcheck.json`). The archived A0 traded 440 of them (Σ|W|·|Δy4|·1e4 = **1938 bps of NAV** over W_FULL — `W` is the un-normalised book, L1 ≈ 0.70 — against the archived A0's whole-history net of 3019 bps of NAV; max single cell 186 bps). The meta is the correct caliber per `CALIBER_PIN_v4`; the consequence is a rule, not a re-litigation: **no device may recompute returns from the cache's `ret5` channel** — extreme bars are wrong there by construction.

---

## §1 Gates (`receipts/RECEIPT_r18_drive_gateP.json`, `RECEIPT_r18_gates.json`, `RECEIPT_r18_clipcheck.json`)

| gate | result |
|---|---|
| **GATE P** C0_s42 vs archived A0 | `rec` bitwise True (10039×23, maxabs 0.0) · `W` bitwise True (10039×829, maxabs 0.0) · cols equal |
| **GATE P** C0_s2027 vs archived A0 | same, True / True / equal ⇒ **PASS** |
| **GATE R** reviewer's counts, OLD rule, archived A0 s42, W_ALPHA | future-missing-but-liquid cells **108**, anchors **108**, previously held **3**, prior gross **0.01183774127**, max |W| on those cells **0.0** (446 such cells on the full axis) ⇒ **PASS** (exact) |
| **GATE Y** as registered (plain-sum formula, 60 anchors) | NaN structure 0 mismatches (forward and closed) — the **window** is right; values maxabs 0.53 — the **formula** was wrong ⇒ **FAIL as registered**, kept in the receipt; AMENDMENT 1 |
| **GATE Y2** (AMENDMENT 1: Π(1+r)−1, all 10039 anchors, 3,453,205 finite cells) | NaN-structure mismatches **0 / 0** ⇒ **window PASS** (`y4[i]` is the forward 48-bar compounded return from E; `y4[i−1]` closes at E). Values agree wherever no bar is clipped; 590 cells differ (§8) |
| GATE E (env) | driver / gates / judge / lev / clipcheck all launched `env -i … <whitelist>`; whitelist `{PATH, HOME, LC_CTYPE}` non-empty and asserted in-file; every device run's exact env dict is in the receipt |

Derived device: `devices/mk_r18_device.py` applies 11 once-only replacements to the pinned source (diff `devices/w10_sleeve_r18.diff`, 114 lines); knobs `R18_ELIG, R18_WARM, R18_INSTR, SMA, SBAND` self-reported in `_CFG["R18"]` with the pinned and prereg sha. Each run reports `self_sha256` = the derived sha (asserted by the driver, E-0826-C). Each run 26–34 s; 12 runs, 6 in parallel, wall 54 s.

## §2 N2 — causal eligibility (`RECEIPT_r18_judge.json` → `N2`)

**Rule.** `ok = isfinite(y4[i−1, m])` at both sites (L160 `legs()`, L234 `run()`): the compounded 4h return over (E−4h, E] exists ⇔ ≥ 46 of the 48 bars ending at E are finite. Fully known at E. The liquidity filter (`qvk` = trailing-7-day mean log quote volume, `pod_fea_ext_clamp.py` L30) and the universe mask (age ≥ 30 d, trailing-30 d volume, monthly PIT) were causal already and are unchanged.

**Cells changed (device-counted and input-side agree):** whole history 15 (12 new-only, 3 old-only) on 12 anchors; W_ALPHA 5 (3 / 2). The reviewer's remaining 105 W_ALPHA cells (434 full-axis) have **both** the closed and the forward return NaN — post-delisting anchors kept "liquid" by the 7-day trailing volume — and stay ineligible for a causal reason.

| | s42 W_FULL | s42 W_ALPHA | s2027 W_FULL | s2027 W_ALPHA |
|---|---|---|---|---|
| Δg vs C0 | **+0.0020** | **+0.0021** | **+0.0102** | **+0.0110** |
| CI95 (k0 / k9) | [−0.004, +0.008] / same | [−0.004, +0.009] / [−0.004, +0.008] | [+0.000, +0.023] / [+0.000, +0.024] | [+0.000, +0.025] / [−0.000, +0.025] |
| CI99K (K=8) | [−0.006, +0.010] | [−0.006, +0.011] | [−0.002, +0.029] | [−0.003, +0.031] |
| Δpnl / Δcarry / Δcost | +0.0013 / −0.0010 / +0.0003 | +0.0012 / −0.0012 / +0.0003 | +0.0088 / −0.0017 / +0.0003 | +0.0095 / −0.0019 / +0.0004 |
| Δτ (matched) | +0.16 % | +0.19 % | +0.19 % | +0.22 % |
| anchors where g differs | 9285 / 10038 | 8479 / 9138 | 9150 / 10038 | 8344 / 9138 |

The change propagates to almost every anchor through the seat (the `legs()` series feed the trailing-900 msharpe) and the EMA state, but its size is 1/20 of the bootstrap resolution. **Reviewer's 3 cells** (both seeds): BNXUSDT 2022-08-10 00Z W[i−1] +0.00224 → C0 W[i] 0 / **N2 W[i] +0.00265**; BNXUSDT 2023-02-01 00Z +0.00942 → 0 / **+0.00942**; EOSUSDT 2025-05-21 08Z −0.00018 → 0 / **−0.00018**; in all three N2 exits at i+1 (W[i+1] = 0) when the causal rule sees the gap. **Unknown-return exposure under N2** (position held, forward return NaN, booked 0): 12 cells on 9 anchors, Σ|sm| 0.0474 (s42) / 0.0478 (s2027) over W_FULL; 3 cells / Σ|sm| 0.0122 on W_ALPHA; 0 under C0. With |4h returns| of delisting names plausibly O(10–50 %), the unbooked P&L is O(0.005–0.02) unit-gross over four years — below anything measured here.

## §3 WU — warm-up book (`RECEIPT_r18_judge.json` → `WU`)

Warm rows 0..899 = 2022-01-31 00Z .. 2022-06-29 20Z. Unique `w3` triples before `[1/3, 1/3, 1/3]` → after `[0.5, 0, 0.5]`; `w3_rev24 == 0` on all 900 rows after (asserted True); rows with `leg_rev24 ≠ 0`: 900 → 0; `w3_rev24` after row 900 is 0 in both (the LEGS mask always applied there).

| 2022-06-07 20Z | g | net_ex (bps) | gross_total | leg_king | leg_rev24 | leg_fund | pnl / carry / cost |
|---|---|---|---|---|---|---|---|
| before (archived) | **−481.36** | −368.01 | 0.7645 | 0 | **−139.30** | −93.74 | −480.34 / +0.79 / +0.23 |
| after (WU) | **−259.36** | −241.50 | 0.9311 | 0 | **0** | **−140.61** | −258.54 / +0.77 / +0.05 |

UTC day 2022-06-07 (6 anchors): Σg −566.61 → −323.66; day return at 2.0× **−11.17 % → −6.40 %**; Σ leg_rev24 −121.08 → 0; Σ leg_fund −123.41 → −185.12; per-anchor g [21.3, 10.0, 3.7, −34.7, −85.6, −481.4] → [7.3, 7.9, −3.2, −29.5, −46.8, −259.4]. It remains the worst UTC day of the full history on the fixed book (both seeds). The fund-only book runs more gross (0.93 vs 0.76 at that anchor) and takes a larger fund-leg hit, but loses the rev24 half.

Δg vs C0: W_FULL **−0.0099 [−0.135, +0.137]** (both seeds; the warm-up rows are identical across seeds because F10 has no prediction before 2023), W_ALPHA **−0.0049 [−0.012, +0.001]** (state carry-over only; last differing anchor 2024-02-07), KING_LIVE 0.0000. Δτ on W_FULL −10.8 % (the two-leg warm-up book trades less than the three-leg one).

## §4 NW — candidate new baseline (`RECEIPT_r18_judge.json` → `NW`, `C0`)

| arm | seed | window | n | g | CI95 | Sharpe (SE) | τ matched | pnl / carry / cost | netlong |
|---|---|---|---|---|---|---|---|---|---|
| C0 (= archived A0) | 42 | W_FULL | 10038 | +0.5608 | [+0.097, +1.040] | 1.1062 (0.467) | 0.05724 | +1.2109 / +0.4759 / +0.1743 | −0.024 |
| **NW** | 42 | W_FULL | 10038 | **+0.5532** | [+0.109, +1.023] | **1.1151** (0.467) | **0.05112** | +1.1886 / +0.4773 / +0.1582 | −0.028 |
| C0 | 42 | W_ALPHA | 9138 | +0.6342 | [+0.159, +1.118] | 1.2912 (0.490) | 0.05403 | +1.2813 / +0.4797 / +0.1675 | −0.025 |
| **NW** | 42 | W_ALPHA | 9138 | **+0.6313** | [+0.159, +1.116] | **1.2846** (0.490) | **0.05411** | +1.2774 / +0.4783 / +0.1677 | −0.025 |
| C0 | 42 | KING_LIVE | 5838 | +1.2058 | [+0.530, +1.898] | 2.1508 (0.612) | 0.07089 | | |
| NW | 42 | KING_LIVE | 5838 | +1.2088 | [+0.543, +1.904] | 2.1548 (0.612) | 0.07104 | | |
| C0 | 2027 | W_FULL | 10038 | +0.5824 | [+0.111, +1.072] | 1.1417 (0.467) | 0.05849 | +1.2282 / +0.4679 / +0.1779 | −0.026 |
| **NW** | 2027 | W_FULL | 10038 | **+0.5829** | [+0.127, +1.076] | **1.1673** (0.467) | **0.05239** | +1.2134 / +0.4686 / +0.1619 | −0.029 |
| C0 | 2027 | W_ALPHA | 9138 | +0.6579 | [+0.182, +1.147] | 1.3299 (0.490) | 0.05540 | +1.3004 / +0.4709 / +0.1715 | −0.027 |
| **NW** | 2027 | W_ALPHA | 9138 | **+0.6640** | [+0.188, +1.153] | **1.3411** (0.490) | **0.05550** | +1.3047 / +0.4688 / +0.1718 | −0.027 |
| NW | 2027 | KING_LIVE | 5838 | +1.2470 | [+0.578, +1.951] | 2.2046 (0.612) | 0.07344 | | |

Paired NW − C0: W_FULL **−0.0076 [−0.134, +0.140]** / **+0.0005 [−0.124, +0.147]**; W_ALPHA **−0.0028 [−0.012, +0.007]** / **+0.0061 [−0.007, +0.021]**; KING_LIVE +0.0030 [−0.007, +0.013] / +0.0179 [−0.000, +0.040]. Matched turnover on W_FULL −10.7 % / −10.4 % (warm-up book), on W_ALPHA +0.15 % / +0.18 %.

**Distances.** To the archived A0 on W_ALPHA (paired): **−0.0028 / +0.0061 bps, Sharpe −0.0066 / +0.0112** — 1/80 of the resolution. To A1x (0.6602 / 1.2857 on n = 9199, v4-native legs, upper bound 2026-09-10; quoted from `RESULT_r11_cost_tail_income_2026-09-12.md` L84; unpaired, INFERRED): NW W_ALPHA −0.029 / +0.004 (s42), +0.004 / +0.055 (s2027). **If NW replaces A0 as the baseline, the planning number does not move; the tail numbers on the first five months do (§5).**

Per-year g (W_FULL rows): 2022 **+0.005 → −0.042** (n 2010; the only year the fix touches materially), 2023 −0.649 → −0.648, 2024 +0.486 → +0.487, 2025 +0.677 → +0.685, 2026 +3.091 → +3.092 (s42); s2027 2022 +0.005 → −0.042, 2023 −0.612 → −0.613, 2024 +0.460, 2025 +0.759 → +0.807, 2026 +3.101.

## §5 Tail tables — W_FULL, UTC-day compounding, true peak-to-trough (full set for C0 / N2 / WU / NW, both seeds, in `receipts/TABLES_r18.md` T6)

**NW s42** (s2027 in parentheses where it differs by more than rounding):

| L | M | maxDD (peak→trough) | worst day | halts ≤−4 % | alerts ≤−2.68 % | halts/yr | P(1y true maxDD ≥ 25 %) | P(1y start-loss ≥ 25 %) [r12's] | median 1y ret | ann ret |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.00 | 1.0 | −24.4 % (−24.8 %) 2022-02-25→2024-07-18 | 2022-06-07 −3.22 % | **0** | 1 | 0.00 | **0.0 %** | 0.0 % | +4.1 % | +12.2 % |
| 1.25 | 1.0 | −29.7 % (−30.2 %) | −4.02 % | 1 | 4 (3) | 0.22 | 0.0 % | 0.0 % | +5.0 % | +15.3 % |
| 1.40 | 1.0 | −32.8 % (−33.2 %) | −4.50 % | 1 | 7 (8) | 0.22 | 4.2 % (4.5 %) | 1.0 % (1.8 %) | +5.6 % | +17.1 % |
| 1.50 | 1.0 | −34.7 % (−35.2 %) | −4.82 % | 1 | 7 (10) | 0.22 | 5.0 % (5.1 %) | 2.3 % (3.2 %) | +5.9 % | +18.4 % |
| **2.00** | 1.0 | **−43.9 % (−44.5 %)** | **−6.41 %** | **5 (6)** | **23 (26)** | **1.09 (1.31)** | **26.8 % (33.1 %)** | 21.2 % (20.6 %) | +7.5 % | +24.5 % |
| 2.50 | 1.0 | −52.0 % (−52.6 %) | −7.99 % | 9 (11) | 47 (50) | 1.97 (2.40) | 41.7 % (42.0 %) | 30.7 % (32.3 %) | +8.9 % | +30.5 % |
| 1.00 | 1.4042 | −40.3 % (−41.1 %) | −4.54 % | 1 | 7 (8) | 0.22 | **15.0 % (16.8 %)** | 8.4 % (9.8 %) | +0.5 % | +11.6 % |
| 1.25 | 1.4042 | −47.8 % (−48.7 %) | −5.66 % | 2 (3) | 12 (15) | 0.44 (0.66) | 27.7 % (33.9 %) | 23.1 % (23.5 %) | +0.4 % | +14.3 % |
| 1.40 | 1.4042 | −52.0 % (−52.8 %) | −6.34 % | 5 (6) | 23 (24) | 1.09 (1.31) | 39.1 % (41.5 %) | 26.8 % (30.5 %) | +0.2 % | +15.8 % |
| 1.50 | 1.4042 | −54.5 % (−55.4 %) | −6.79 % | 7 (8) | 26 (29) | 1.53 (1.75) | 43.6 % (44.1 %) | 32.1 % (34.2 %) | +0.1 % | +16.8 % |
| 2.00 | 1.4042 | −65.7 % (−66.6 %) | −9.02 % | **18** | 69 (71) | 3.93 | 59.9 % (57.5 %) | 50.3 % (51.4 %) | −0.8 % | +21.6 % |
| 2.50 | 1.4042 | −74.3 % (−75.2 %) | −11.25 % | 38 (40) | 117 (113) | 8.30 (8.74) | 89.3 % (87.5 %) | 58.3 % (59.2 %) | −2.0 % | +25.8 % |

Against the archived A0 at 2.0× raw: maxDD −46.0 % → −43.9 %, worst day −11.17 % → −6.40 %, halts 6 → 5 (s2027 7 → 6), alerts 24 → 23, P(1y true maxDD ≥ 25 %) 26.8 % → 26.8 % (unchanged: the binding windows are 2022-02 → 2024-07, which the warm-up fix only partly touches). The two columns "true" vs "start-loss" show the size of the N4 error on this book: at 2.0× raw 26.8 % vs 21.2 %; at 1.00× ×1.4042 15.0 % vs 8.4 %. **M = 1.4042 is a sensitivity, not a fact** (reviewer's same-period paired ratio 0.656 [0.467, 1.008]).

## §6 Published verdicts re-read against NW (archived r15 / r16 arms; `RECEIPT_r18_judge.json` → `published`)

All 22 arm×seed cells reproduce their published Δg vs A0 (e.g. r15 F s42 +0.0179, S −0.0928, SB +0.0840; r16 X0 −0.0054, X1 −0.5636, X5 +0.0192). Against NW on **W_ALPHA (the published window): 0 sign changes, 0 CI95-status changes** in 22 cells. On KING_LIVE: **2 cells move** — r15 F05 s2027 +0.0169 → −0.0010 (sign; an arm whose Δ was never distinguishable from 0), and **r16 X5 s2027 +0.1144 [+0.003, +0.227] → +0.0965 [−0.020, +0.213]** (its single CI95-excluding-0 cell no longer excludes 0; r16 already reported it fails Bonferroni-6 and ruled UNDECIDED). **Confound, stated:** every archived arm was run with N2/WU on; `Δ_vs_NW = Δ_vs_A0 − (NW − A0)` with NW − A0 = −0.0028 / +0.0061 on W_ALPHA. No verdict needs re-issuing on this evidence; a clean re-test would re-run each arm on the fixed device.

## §7 N4 / LEV12-FIX (`RECEIPT_r18_lev.json`)

Definitions per prereg §6; leverage grid = r12's **literal** values `[round(x, 2) for x in arange(0.25, 2.01, 0.125)]` (r12 and the reviewer computed at the rounded leverages 0.38 / 0.62 / 0.88 / …, so the grid is copied verbatim for exact reconciliation — my first pass used 0.875 etc. and differed by 1–18 windows at those points; disclosed). **Reconciliation: my `p_start_loss25` / halts / medians equal r12's stored `LEV12.json` to 1e-9 on all 32 cells and the old-gate feasible L matches on all 32; my `p_true_maxDD25` and `p_start_loss25` equal the reviewer's `RECEIPT_smoothing.json` to 1e-9 on all 6 arms × 15 leverages × 2 multipliers.**

Corrected gate at **M = 1.4042** (r12's caliber), selected cells; full 38-arm × 2-M table in `receipts/TABLES_r18.md` T8:

| cell | b/α | L=1: halts/yr | L=1: P start-loss (old) | **L=1: P true maxDD** | max feasible L old → **true** | median 1y at true-feasible L |
|---|---|---|---|---|---|---|
| deployed (0.10, 2.5e-4) s42 / s2027 | 0.0025 | 0.44 | 8.6 % / 9.8 % | **15.3 % / 16.8 %** | 1.00 → **0.88** | **+0.3 % / +0.4 %** |
| (0.05, 2.5e-4) s42 / s2027 | 0.0050 | 0.22 | 10.1 % / 10.7 % | **14.9 % / 15.0 %** | 0.88 → **0.88** | **+8.2 % / +8.8 %** |
| (0.10, 5.0e-4) s42 / s2027 | 0.0050 | 0.22 | 6.9 % / 7.0 % | **14.0 % / 16.0 %** | 1.00 → **0.88** | **+5.0 % / +5.8 %** |
| (0.05, 1.25e-4) s42 / s2027 | 0.0025 | 0.22 | 4.3 % / 4.5 % | **6.4 % / 6.5 %** | 1.00 → **1.00** | +4.2 % / +4.3 % |
| (0.05, 0) s42 | 0 | 0.22 | 4.5 % | **10.7 %** | 1.00 → 0.88 | +1.5 % |
| α = 0.15–0.30, any b | | 0.44 | 8–14 % | **16–18 %** | 0.88–1.00 → 0.88 | −0.2 … −5.6 % |
| α = 0.50 | | 0.44 | 12–15 % | **25 %** | 0.88 → 0.88 (0.75) | −4.5 … −5.3 % |
| α = 1.00 (instantaneous) | | 0.66–0.87 | 23–25 % | **35–39 %** | 0.75 → 0.75 | −8.2 … −8.4 % |
| **NW** (fixed, deployed corner) s42 / s2027 | 0.0025 | 0.22 | 8.4 % / 9.8 % | **15.0 % / 16.8 %** | 1.00 → **0.88** | **+0.5 % / +0.5 %** |
| NW_S05 (fixed, 0.05, 2.5e-4) | 0.0050 | 0.00 | 10.1 % / 10.5 % | **14.9 % / 15.0 %** | 0.88 → 0.88 | +8.2 % / +8.9 % |
| NW_B50 (fixed, 0.10, 5e-4) | 0.0050 | 0.22 | 6.9 % / 6.9 % | **14.0 % / 16.0 %** | 1.00 → 0.88 | +5.1 % / +5.9 % |

At **M = 1.0** (raw replay vol) the true gate binds through halts and maxDD at higher leverage: deployed feasible 1.62 → **1.50** (median 1y +5.6 % / +6.1 %), (0.05, 2.5e-4) 1.62 → 1.38 / 1.50 (+15.6 % / +18.2 %), (0.10, 5e-4) 1.62 → 1.50 (+12.4 % / +14.2 %); fixed book identical to ±0.1 pp.

**Round-12 claims under the corrected gate:**

| claim | verdict | evidence |
|---|---|---|
| (a) deployed corner feasible at L = 1.00, P = 0.086 | **FAIL** | true P = 15.3 % (s42) / 16.8 % (s2027) > 10 %; feasible L = 0.88 → median 1y +0.3 % |
| (b) (0.05, 2.5e-4) "+9.2 % at L = 1.00 / +8.2 % at 0.88" | **FAIL — and it never passed**: r12's own old-gate P at L = 1.00 was 0.1005 > 0.10 | true P 14.9 %; at its feasible 0.88 the median is +8.2 % (the number r12 printed in parentheses); on the fixed book +8.2 % / +8.9 % |
| (c) (0.10, 5e-4) feasible at 1.00, +5.6 % | **FAIL** | true P 14.0 % / 16.0 %; feasible 0.88 → +5.0 % / +5.8 % |
| (d) "slower is better" (b/α 0.005 beats the deployed 0.0025) | **survives as a POINT ESTIMATE only** | at the common true-feasible L = 0.88: +8.2 / +5.0 vs +0.3 (s42), +8.8 / +5.8 vs +0.4 (s2027); same ordering at M = 1.0, on the archived and on the fixed book. Overlapping 1y windows on one path (1323 windows ≈ 4.6 independent years); the underlying Δg CIs contain 0 (r12; fixed book +0.0725 [−0.093, +0.244] / +0.0430 [−0.094, +0.178]) |
| (e) at 2.0× the gate is infeasible for the whole grid | **REAFFIRMED** | no cell feasible at 2.0 under the true gate at either M (P true 53–95 % at ×1.4042; 24–68 % raw) |
| the r12 g-table / Δg CIs | **unchanged** | do not depend on the gate |

What did not survive: **every "risk-gate pass at L = 1.00" for the deployed corner and for both recommended slower corners**, and the "+9.2 %" headline (which r12's own receipt already contradicted). What survived: the direction, as a point estimate, and the infeasibility at 2.0×. The 09-05 memory `deepsmooth_band_deployed` and the r12 claim "在同一个可行杠杆 1.00 上" must be read with feasible L = 0.88.

## §8 Side finding — the 5m cache's `ret5` channel is clipped (`RECEIPT_r18_clipcheck.json`; not a pre-registered result)

Facts (VERIFIED): `dlnative_5m_wide829_f16_holefix2.npz` channel `ret5` (located by name in `ch`) has global min/max **∓0.300048828125** (float16 of 0.30); **953 bars sit exactly at the bound, 0 beyond it**. The accounting meta `meta_newprod_v4.npz` `y4` = Π(1+r)−1 over the forward 48 bars computed from **unclipped** returns: it equals the cache's clipped compound to ≤ 1.1e-10 on every cell whose window has no bound-hitting bar (3,452,615 cells), and differs on **exactly the 590 cells (196 anchors) that contain one** — 397 of them on 2025-10 (2025-10-10 20Z, the Oct-10 crash: SOLVUSDT meta −0.4837 vs clipped-compound +0.5495; RENDER −0.243 vs +0.545; KAS −0.226 vs +0.602 …), plus the 2022-05/06 LUNA / UNFI / BEL episodes (UNFI 2022-06-07 20Z meta +2.735 vs +1.130) and single extreme bars elsewhere. The archived A0 s42 traded 440 of the 590 cells; Σ|W|·|Δy4|·1e4 = **1938 bps of NAV** over W_FULL (1704 on W_ALPHA; `W` = un-normalised book weights, L1 ≈ 0.70), max single cell 186 bps (UNFI 2022-06-07 20Z, W −0.0116). For scale, the archived A0's total W_FULL net is 3019 bps of NAV (s42) / 3203 (s2027).

Reading: the meta is the RAW accounting caliber `CALIBER_PIN_v4` prescribes and is the correct one; the cache channel cannot represent a 5-minute move beyond ±30 %. Consequences: (i) **any device that recomputes 4h returns from the cache's `ret5` (Σ or Π) inherits E-0908-B on crash anchors** — including any "price-available flag" or regime primitive built from it on those bars; (ii) the discrepancy is not evidence about the archived A0's g (its `y4` comes from the meta), but it is a **bound on how wrong a cache-derived return series would be on this book**: an absolute-value sum of 1938 bps of NAV against a whole-history net of 3019 bps of NAV (the signed error could be much smaller; it was not computed because no published number uses cache-derived returns). No fix attempted here; flagged for the lead.

## §9 Environment, reproduction, labels, limitations

**pod2**: `/workspace/uplift_2026-09-11/r18_foundation/` — `dev/` (symlinks: `pod_backup_2026-08-21/{nets_histv2_-30_2_42.npy, nets_histv2_0_0_0.npy, slow_pred_hist_oos.npy → king_v4/SLOW_v4.npy, wide_fea_hist_meta.npz → refute_C6_2/altrun/meta_newprod_v4.npz, wide_panel_4h_hist_v2.npz → data/wide_panel_4h_v2ext.npz}`, `dlw_2026-08-22 → /workspace/dlw_v4raw`, `f8_2026-08-22 → health_check/dev_v4/f8_2026-08-22`), `arms/*.npz` (12 full artifacts, 155 MB, pod2 only), `receipts/`, `logs/`. Every input's realpath and sha256 is in `RECEIPT_r18_drive_gateP.json → inputs`. Repo copy holds `receipts/arms_rec/*.npz` (rec + R18A aux + config_json + source sha, 14 MB).

**Commands (verbatim, pod2, cwd `/workspace/uplift_2026-09-11/r18_foundation`):**
```
/workspace/venv/bin/python devices/mk_r18_device.py /workspace/uplift_2026-09-11/w10_sleeve.py devices/w10_sleeve_r18.py PREREG_r18_foundation_2026-09-12.md
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/r18_drive.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/r18_gates.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/r18_judge.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/r18_lev.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/r18_clipcheck.py PATH,HOME,LC_CTYPE
python3 devices/r18_tables.py .        # Mac, renders receipts/TABLES_r18.md
```
Load before the driver 2.80 → after 5.39 (other agents' work dominated the pod load of 7–8 later in the session; my post-driver steps were single-threaded).

**VERIFIED**: §1 gates; §2–§7 every number (computed this round from the receipts); §8 facts. **INFERRED**: the A1x reference values (quoted); the 1.4042 multiplier and its 0.656 [0.467, 1.008] counterpart (quoted from r11 / the reviewer); the identification of the accounting meta's builder with `pod_dlw_targets_ext.py` L93's `y4s` (the formula is verified against the cache, the provenance is from `CALIBER_PIN_v4`).

**Limitations.** (1) N2 and WU are causality / definition repairs; neither is an alpha result and neither should be read as one — the s2027 N2 CI95 just above 0 is 1/20 of the resolution. (2) W_FULL includes 2022-01-31 .. 2022-06-29 on which king (dead until 2024-01-01) and F10 (dead until 2023-01-01) contribute nothing: the "LEGS=101 book" there is the fund-only book, honestly labelled now, still a different regime from 2024+. (3) The published-verdict re-read is confounded as stated in §6. (4) The leverage statistics are single-path overlapping-window point estimates; the ≤ 10 % / ≤ 1 halt gate is r12's, not a ruling. (5) GATE Y was mis-specified in the registered prereg (formula); the amendment is definitional and was frozen before any outcome number, with the failing original kept in the receipt. (6) The cache-clip finding (§8) is outside the pre-registered readouts and is reported as a fact with a bound, not as a verdict on any published number.
