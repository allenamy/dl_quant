> **创建:** 2026-09-13 ~12:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (worker L4, dispatched by lead) | **状态:** RESULT — frozen verdict **NOT PASS (multiplicity)** under `PREREG_L4_carry_sleeve_hysteresis_2026-09-13.md` (sha256 ced2f73f…, frozen 2026-09-13T11:24:12Z, commit deb3af82) + `PREREG_AMENDMENT_1_L4_2026-09-13.md` (0f7c90d8…, 11:38:01Z, a1c3e09a, before any real-data run); §10–§11 are POST-HOC and change no reading or verdict; **not re-run by lead**; research only, proposes nothing | **作废条件:** any input sha in PREREG §7 changes; `L4_SERIES.npz` (8ba4ba1f…) or `RECEIPT_L4_run.json` (f94a1308…) replaced; a raw-price reconciliation of the forced-exit events (§11) shows B2 marks them correctly (then §0.7 falls) or that B1 is an artifact there (then §0.7 narrows)

# RESULT · L4 · Low-turnover delta-neutral funding carry sleeve with hysteresis (paper)

Units: sleeve returns in **bps per 4h anchor per unit of total sleeve capital** (spot fully funded + perp margin m = 0.5 × notional); Sharpe = mean/std × √2190; APR % = mean × 2190/100. A0 per unit capital = 2.0 × g (T6 `A0_PWR230k`, bps/anchor per unit gross). Every number below is in `receipts/pod2/TABLES_L4.md` (rendered by `devices/l4_tables.py` from `receipts/pod2/RECEIPT_L4_build.json` and `RECEIPT_L4_run.json`) or, for §10–§11, in `receipts/pod2/POSTHOC_L4_basis_reconcile.json` / `POSTHOC_L4_event_paths.json` and their stdout logs. W = 2022-01-31 00Z…2026-08-30 20Z (10,038 anchors); S2426 = 2024-01-01…2026-08-30 20Z.

## §0 One page

**VERIFIED (frozen devices, all gates green):**
1. **Verdict under the frozen rule: NOT PASS (multiplicity).** No arm is PASS_adj; A05, A06, A08 are PASS_unadj; the nested selection passes. The label comes from the frozen trichotomy (PREREG §5.3). What actually blocks each group differs:
   - **A01–A04 (h_in 2 / h_out 0.5)** pass P0, P2a, **P2b (Bonferroni-12)** and P3, and fail **only P1**: 2022 is negative by −0.005…−0.012 bps/anchor (APR −0.11…−0.26 %, CI95 includes 0) while positions exist in 36–38 % of 2022 anchors.
   - **A05–A08 (5 / 2)** pass P1 but their S2426 lower bound is below 0 at the Bonferroni level (A05 +0.1256 [+0.0126, +0.2737], Bonf −0.0265).
   - **A09–A12 (10 / 4)** fail P0 (positions in 12 % of S2426 anchors; none in 2022–2023).
2. **Hysteresis removes the turnover problem.** Break-even all-in cost per unit notional turnover over W is **62.7–109.3 bps** across arms (A01 76.9, A02 96.3), against 13.92 assumed. The frozen top-K rule of 09-05 broke even at 5.4/8.7. Spot at 5 or 15 bps moves S2426 net by only ±0.008–0.020.
3. **Income is real but small per unit capital, and 2023 is no longer empty for the low-entry arms.** A01: W net +0.2038 [+0.1133, +0.3154], APR +4.46 %, SR 3.63; by year −0.0099 / +0.2342 / +0.4674 / +0.1174 / +0.1854 (2022…2026). Positions sit in 75.5 % of 2023 anchors (A02 81.4 %), because held names stay while the EMA ≥ 0.5 (the default 1 bps/8h rate keeps them).
4. **ρ to A0 ≈ 0.** Over W, per anchor −0.009…+0.013 and per day −0.032…+0.009, every arm and both seeds. Per-year per-day ρ reaches −0.149 at most.
5. **Combination.** Equal capital (0.5·A0 + 0.5·sleeve) raises Sharpe and lowers return. A01/s42 W: SR 1.11 → 1.30, ΔSR +0.20 [+0.11, +0.31], mean 1.122 → 0.663 bps/anchor per capital, maxDD 46.4 % → 21.1 %. In 2023: −1.94 → −1.59 (ΔSR +0.35 [+0.14, +0.61]); both seeds agree. **Equal vol is INFEASIBLE** in every arm and window: λ_needed 14–335 against k_max 1.8 (spot leg levered 3×, perp margin unchanged).
6. **T6 framing.** Nested picks A03 (2023), then A02 (2024, 2025, 2026); nested S2426 +0.2127 [+0.0954, +0.3676], SR 5.31 ⇒ Nested PASS. DSR for the best S2426 arm (A02, SR 5.31): P(true SR > 0) = 1.000 at N_eff 1.37, 0.994 at N = 12, 0.989 at N = 18. But skew is −8.3 and kurtosis 462: the Sharpe sits on a fat left tail (see 7). N = 12 enters the trial ledger.

**POST-HOC (written after reading T8; not a gate, changes no verdict), numbers VERIFIED, reading INFERRED:**

7. **The two basis markings disagree in sign.** On identical positions, marking with Binance perp/spot closes (B1) instead of the frozen premium index (B2) turns every arm negative. A01 S2426 goes from +0.266 to −0.696 (SR −1.43), W from +0.204 to −0.333.
   - The whole disagreement sits in **holds that ended by forced exit**: the spot pair stopped trading (a) or funding stopped (b). For A01 over W, normal exits (200 holds) give B2 +0.0397 / B1 +0.0296 bps/anchor (they agree), while forced (a) + (b) (21 holds) give B2 −0.028 / B1 −0.551.
   - 10 holds carry 84 % of \|B1 − B2\|; the median per-hold difference is −0.28 bps·capital. The names are AMB, LINA, MDT, DENT, BSW, BLZ, ALPHA, HIFI, DEGO, BNX, BAKE.
   - In these events **raw B2 is frozen for 6–24+ anchors** (AMB 2549.0, LINA 966.4, MDT 72.6, DENT 388.3, DEGO 83.5, KDA −216.7), while raw B1 climbs to +2,562…+34,805 bps before the spot or perp stops.
   - **INFERRED:** around spot or perp delistings the premium index stops tracking the Binance pair the sleeve would hold. If the B1 paths are real prices (spot crashing once deposits close while the perp keeps trading), the long-spot leg takes most of the loss and the sleeve's sign flips. **The frozen P&L is therefore not a safe reading of the tail, and this study cannot settle it:** neither instrument was validated on these events.

## §1 Gates (all passed before any reading was printed; `TABLES_L4.md` T0)

| gate | reading |
|---|---|
| G-IN | 10 inputs hashed; every sha named in PREREG §7 equal |
| G-ALIGN | symbols identical across T7 / r5 / trackA a1 order / ext cache (829); fund_aug keys ⊂ (827); W ⊂ T7 grid; r5 covers W + 2026-08-31 00Z; T6 ts == W |
| G-A0 | s42 FROZEN SR 2.9357130374 (published 2.93571303735249, tol 1e-9); s42 W_FULL 1.1061629689; s2027 FROZEN 2.9021472126 |
| G-FUND | 17,707 vision monthly zips: 2,352,933 / 2,352,933 fund_aug events matched, rates identical (max \|Δ\| 0.0); api unmatched 0, **vision unmatched 3,797**; true spacing = `funding_interval_hours` for 0.99971 of 2,352,249 |
| G-SETT | vs carry_layers `sett_tables.npz` on 10,176 anchors: 2,394,306 cells, max \|Δ\| 2.23e-09, presence mismatches 0 (45 cells excluded: same-hour duplicates / second-1 records) |
| G-UNITS | 8h events with \|rate\| ≥ 10 bps: sign(p_tw8) agrees 0.9885 (+, n 2,089) / 0.9971 (−, n 8,001); Spearman(B1, B2) 0.658 (n 274,092, \|B2\| ≥ 10 bps); median B1/B2 0.872 (\|B2\| ≥ 20 bps) |
| G-SYN | 25 synthetic world × arm cases equal to an independent pure-Python reference of PREREG §2.6 (positions identical, max accounting diff 8.9e-16); closed-form checks (entry, income, costs, exit anchor 126, basis telescope) exact; forced exits a/b/c at 85/106/95; K = 1 slot limit |
| G-CAUSAL | 20 cut anchors: all future data replaced ⇒ positions ≤ cut identical in 20/20 draws for all 12 arms; negative control (+50 bps on the last known window) changed positions at the cut in 20/20 draws |
| G-ACCT | identity 0.0; turnover vs holds 3.6e-15; per-hold basis telescope 0.0; basis total vs holds 7.1e-14; no NaN marks |

AMENDMENT 1 (before any real-data run): G-SYN world S3 showed the frozen entry rule re-admitting a name one anchor after a forced (b) exit, charging a round trip each cycle. Entry now also requires a funding event in the last 24 h. Nothing else changed.

## §2 Arms and the frozen rule (`TABLES_L4.md` T1)

| arm | h_in / h_out bps/8h | min_hold | K | S2426 net [CI95] · Bonf lower | S2426 SR | S2426 pos share | P1 years applying | ρ W anchor/day s42 | P0 P1 P2a P2b P3 | PASS adj / unadj |
|---|---|---|---|---|---|---|---|---|---|---|
| A01 | 2 / 0.5 | 3 | 10 | +0.2660 [+0.1342, +0.4285] · +0.0921 | 3.79 | 0.964 | **Y22 −0.010**, Y23 +0.234, Y24 +0.467, Y25 +0.117, Y26 +0.185 | +0.003 / −0.015 | ✓ ✗ ✓ ✓ ✓ | no / no |
| A02 | 2 / 0.5 | 3 | 20 | +0.2127 [+0.0962, +0.3690] · +0.0628 | 5.31 | 0.964 | **Y22 −0.005**, +0.211, +0.439, +0.065, +0.093 | +0.002 / −0.027 | ✓ ✗ ✓ ✓ ✓ | no / no |
| A03 | 2 / 0.5 | 9 | 10 | +0.2496 [+0.1198, +0.4177] · +0.0786 | 3.41 | 0.964 | **Y22 −0.012**, +0.233, +0.464, +0.109, +0.138 | +0.009 / −0.013 | ✓ ✗ ✓ ✓ ✓ | no / no |
| A04 | 2 / 0.5 | 9 | 20 | +0.2050 [+0.0895, +0.3609] · +0.0535 | 4.95 | 0.964 | **Y22 −0.006**, +0.211, +0.439, +0.061, +0.069 | +0.007 / −0.026 | ✓ ✗ ✓ ✓ ✓ | no / no |
| A05 | 5 / 2 | 3 | 10 | +0.1256 [+0.0126, +0.2737] · −0.0265 | 2.07 | 0.311 | Y24 +0.274, Y25 +0.018 | −0.006 / −0.025 | ✓ ✓ ✓ ✗ ✓ | no / **yes** |
| A06 | 5 / 2 | 3 | 20 | +0.1107 [+0.0136, +0.2572] · −0.0090 | 3.28 | 0.312 | Y24 +0.264, Y25 +0.009 | −0.009 / −0.032 | ✓ ✓ ✓ ✗ ✓ | no / **yes** |
| A07 | 5 / 2 | 9 | 10 | +0.1099 [−0.0026, +0.2635] · −0.0404 | 1.73 | 0.316 | Y24 +0.273, Y25 +0.009 | +0.002 / −0.025 | ✓ ✓ ✗ ✗ ✓ | no / no |
| A08 | 5 / 2 | 9 | 20 | +0.1029 [+0.0057, +0.2526] · −0.0172 | 2.93 | 0.317 | Y24 +0.264, Y25 +0.005 | −0.001 / −0.032 | ✓ ✓ ✓ ✗ ✓ | no / **yes** |
| A09 | 10 / 4 | 3 | 10 | +0.0600 [−0.0200, +0.1626] · −0.0526 | 1.12 | 0.120 | none | +0.002 / +0.000 | ✗ ✓ ✗ ✗ ✓ | no / no |
| A10 | 10 / 4 | 3 | 20 | +0.0490 [−0.0090, +0.1372] · −0.0255 | 1.72 | 0.120 | none | +0.004 / −0.002 | ✗ ✓ ✗ ✗ ✓ | no / no |
| A11 | 10 / 4 | 9 | 10 | +0.0485 [−0.0269, +0.1482] · −0.0578 | 0.85 | 0.120 | none | +0.009 / +0.001 | ✗ ✓ ✗ ✗ ✓ | no / no |
| A12 | 10 / 4 | 9 | 20 | +0.0432 [−0.0132, +0.1315] · −0.0275 | 1.44 | 0.120 | none | +0.010 / −0.002 | ✗ ✓ ✗ ✗ ✓ | no / no |

## §3 Per-year table, representative arms (all 12 × 7 spans in `TABLES_L4.md` T2)

| arm | span | net [CI95] | income | basis (B2) | cost | turnover | deployed | position / empty share | no-candidate share | SR | maxDD % | APR % | holds (median anchors) | forced a/b/c |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 | Y22 | −0.0099 [−0.0258, +0.0039] | +0.0116 | −0.0053 | 0.0162 | 0.00116 | 0.042 | 0.357 / 0.643 | 0.932 | −0.77 | 0.34 | −0.22 | 17 (10) | 1/0/0 |
| A01 | Y23 | +0.2342 [+0.0882, +0.4133] | +0.2514 | +0.0264 | 0.0436 | 0.00314 | 0.415 | 0.755 / 0.245 | 0.666 | 6.79 | 0.15 | +5.13 | 47 (94) | 0/0/8 |
| A01 | Y24 | +0.4674 [+0.1820, +0.8428] | +0.4779 | +0.0301 | 0.0406 | 0.00291 | 0.564 | 1.000 / 0.000 | 0.561 | 8.20 | 0.56 | +10.24 | 50 (181) | 2/0/5 |
| A01 | Y25 | +0.1174 [−0.0104, +0.2236] | +0.2526 | −0.0662 | 0.0691 | 0.00496 | 0.308 | 0.942 / 0.058 | 0.484 | 1.47 | 1.53 | +2.57 | 84 (35.5) | 8/5/2 |
| A01 | Y26 | +0.1854 [+0.0346, +0.3615] | +0.1430 | +0.0999 | 0.0575 | 0.00413 | 0.231 | 0.942 / 0.058 | 0.556 | 2.57 | 0.62 | +4.06 | 42 (21.5) | 0/5/4 |
| A01 | W | +0.2038 [+0.1133, +0.3154] | +0.2375 | +0.0113 | 0.0450 | 0.00323 | 0.323 | 0.797 / 0.203 | 0.641 | 3.63 | 1.53 | +4.46 | 240 (42) | 11/10/19 |
| A02 | W | +0.1689 [+0.0895, +0.2686] | +0.1892 | +0.0082 | 0.0285 | 0.00205 | 0.263 | 0.810 / 0.190 | 0.641 | 5.02 | 0.76 | +3.70 | 305 (71) | 12/10/22 |
| A05 | Y23 | +0.1102 [−0.0040, +0.2896] | +0.1313 | +0.0035 | 0.0246 | 0.00177 | 0.089 | 0.143 / 0.857 | 0.911 | 6.08 | 0.15 | +2.41 | 24 (36) | 0/0/0 |
| A05 | W | +0.0954 [+0.0183, +0.1941] | +0.1285 | −0.0080 | 0.0251 | 0.00181 | 0.070 | 0.216 / 0.784 | 0.864 | 2.02 | 1.77 | +2.09 | 136 (31.5) | 8/7/2 |
| A09 | Y22 / Y23 | 0 (no position) | | | | | | 0.000 / 1.000 | 1.000 / 1.000 | | | | 0 | |
| A09 | W | +0.0349 [−0.0113, +0.0971] | +0.0505 | −0.0091 | 0.0065 | 0.00046 | 0.016 | 0.070 / 0.930 | 0.965 | 0.85 | 1.43 | +0.76 | 35 (30) | 2/5/1 |

Held names are 4h- or 8h-interval by true spacing (A01 0.691 / 0.309; almost no 1h names). Median log(spot/perp 24h quote volume) of held names is −1.36 (spot ≈ 26 % of perp volume). No same-hour duplicate event fell on a held name.

## §4 Break-even per unit notional turnover (W; all-in / implied spot / income-only, bps; `TABLES_L4.md` T3)

A01 76.9 / 73.0 / 73.4 · A02 96.3 / 92.4 / 92.3 · A03 74.8 / 70.9 / 73.0 · A04 95.1 / 91.1 / 92.4 · A05 66.7 / 62.8 / 71.1 · A06 80.3 / 76.4 / 82.7 · A07 62.7 / 58.7 / 70.0 · A08 77.2 / 73.3 / 81.6 · A09 89.0 / 85.1 / 108.5 · A10 109.3 / 105.3 / 123.5 · A11 74.6 / 70.7 / 102.2 · A12 98.0 / 94.1 / 118.5. Weakest year for A01–A04: 2022 (all-in 3.8–5.4, i.e. below the assumed cost). The 09-05 frozen top-K rule broke even at 5.36–8.70.

## §5 Correlation with A0 (`TABLES_L4.md` T4)

Over W, every arm and seed: per anchor −0.009…+0.013, per day −0.032…+0.009. The largest per-year magnitude is 2022 per day (−0.122…−0.149, arms that hold positions). **P3 passes everywhere.**

## §6 Combination with A0 (`TABLES_L4.md` T5; A0 per capital = 2 × g)

| arm · seed | span | A0 SR | EC SR | ΔSR [CI95] | EC mean / A0 mean | EC / A0 maxDD % | λ_needed (k_max 1.8) |
|---|---|---|---|---|---|---|---|
| A01 · s42 | W | 1.11 | 1.30 | +0.20 [+0.11, +0.31] | +0.663 / +1.122 | 21.1 / 46.4 | 18.0 INFEASIBLE |
| A01 · s42 | S2426 | 2.15 | 2.38 | +0.23 [+0.11, +0.38] | +1.339 / +2.412 | 9.0 / 23.6 | 16.0 INFEASIBLE |
| A01 · s42 | Y23 | −1.94 | −1.59 | +0.35 [+0.14, +0.61] | −0.531 / −1.297 | 14.1 / 28.9 | 19.4 INFEASIBLE |
| A01 · s2027 | W | 1.14 | 1.34 | +0.20 [+0.11, +0.31] | +0.684 / +1.165 | 21.5 / 46.9 | 18.2 INFEASIBLE |
| A02 · s42 | W | 1.11 | 1.27 | +0.17 [+0.09, +0.27] | +0.645 / +1.122 | 21.5 / 46.4 | 30.1 INFEASIBLE |
| A05 · s42 | W | 1.11 | 1.20 | +0.09 [+0.02, +0.19] | +0.608 / +1.122 | 23.3 / 46.4 | 21.5 INFEASIBLE |

EC improves Sharpe because it adds a small positive mean at near-zero vol while halving A0's capital; it does not raise return. With m = 1.0 the A01 S2426 EC SR is 2.32 instead of 2.38. No equal-vol combination is feasible under the frozen leverage definition.

## §7 T6 framing (`TABLES_L4.md` T6)

| segment | selected (training SR) | OOS net | OOS SR | OOS position share |
|---|---|---|---|---|
| 2023 | A03 (the 8 selectable arms are all negative on 2022 training; A03 best at −0.75; A09–A12 held nothing in 2022, so they are not selectable) | +0.2333 | 6.61 | 0.755 |
| 2024 | A02 (4.94) | +0.4393 | 10.52 | 1.000 |
| 2025 | A02 (7.30) | +0.0652 | 1.61 | 0.942 |
| 2026→08-30 | A02 (5.47) | +0.0927 | 2.57 | 0.942 |

- Nested S2426: +0.2127 [+0.0954, +0.3676], SR 5.31, position share 0.964, ρ +0.002 / −0.027 (s42) ⇒ **Nested PASS**. The nested series starts in 2023 (T6 segments), so it never sees the negative 2022 that fails A01–A04 on P1.
- EC increment of the nested sleeve over A0 on 2023-01-01…2026-08-30: SR 1.37 → 1.59, ΔSR +0.21 [+0.11, +0.34] (s2027: 1.42 → 1.63, same ΔSR and CI); Δmean CI95 [−1.298, +0.089].
- DSR (A02, S2426): PSR(0) 1.000; P(true SR > 0) 1.000 at N_eff 1.37 (SR0 0.76) / 0.994 at N = 12 (SR0 2.45) / 0.989 at N = 18 (SR0 2.73). Skew −8.27, kurtosis 461.6.
- **Trial ledger: N_L4 = 12.** The POST-HOC diagnostics select nothing and are not trials.

## §8 2023 reading (`TABLES_L4.md` T7)

A01–A08 "add in 2023" under the descriptive definition (2023 net > 0 and 2023 ΔSR(EC − A0) > 0 for both seeds). A01 +0.2342 (position share 0.755, ΔSR +0.35/+0.35); A02 +0.2115 (0.814, +0.31/+0.31); A05 +0.1102 (0.143, +0.16/+0.16). A09–A12 hold nothing in 2023, so they add nothing. Under B1 marking (§10) the 2023 reading is not re-derived.

## §9 Sensitivities (`TABLES_L4.md` T8; same positions)

| arm | S2426 net at c_spot 5 / 10 / 15 | PASS_unadj at 5 / 15 | basis excluded S2426 net (SR) | **B1 marking S2426 net (SR) · W net** | S2426 CI95 iid-day · 7-day |
|---|---|---|---|---|---|
| A01 | +0.2859 / +0.2660 / +0.2460 | no / no | +0.2546 (13.09) | **−0.6960 (−1.43) · −0.3333** | [+0.1945, +0.3323] · [+0.1758, +0.3662] |
| A02 | +0.2245 / +0.2127 / +0.2010 | no / no | +0.2045 (15.05) | **−0.2663 (−1.10) · −0.0989** | [+0.1689, +0.2558] · [+0.1376, +0.2965] |
| A05 | +0.1374 / +0.1256 / +0.1137 | yes / yes | +0.1385 (7.90) | **−0.4308 (−1.66) · −0.2374** | [+0.0553, +0.1897] · [+0.0396, +0.2195] |
| A06 | +0.1186 / +0.1107 / +0.1029 | yes / yes | +0.1165 (9.10) | **−0.1673 (−1.28) · −0.0852** | [+0.0678, +0.1530] · [+0.0403, +0.1942] |
| A08 | +0.1107 / +0.1029 / +0.0952 | yes / no | +0.1128 (8.39) | **−0.1752 (−1.34) · −0.0902** | [+0.0619, +0.1431] · [+0.0335, +0.1862] |

Correlation of per-anchor B1 and B2 basis P&L on invested anchors: +0.13 (A01–A04) to +0.30 (A09–A12). The frozen 30-day block CI is the widest of the three block choices.

## §10 POST-HOC · where B1 and B2 disagree (`devices/l4_posthoc_basis_reconcile.py`, `devices/l4_posthoc_event_paths.py` v2; both committed before running; both first assert the 12 base net series equal `L4_SERIES.npz` bitwise: 12/12)

Basis P&L summed by exit reason, bps per anchor over W, with the number of holds (`POSTHOC_L4_event_paths.json` `split_by_exit_reason`):

| arm | normal: holds · income · B2 · B1 | forced a (spot stopped): holds · B2 · B1 | forced b (funding stopped): holds · B2 · B1 | forced c (premium missing): holds · B2 · B1 |
|---|---|---|---|---|
| A01 | 200 · +0.1833 · +0.0397 · +0.0296 | 11 · −0.0231 · **−0.2989** | 10 · −0.0052 · **−0.2516** | 19 · −0.0006 · −0.0050 |
| A02 | 261 · +0.1603 · +0.0223 · +0.0180 | 12 · −0.0115 · **−0.1494** | 10 · −0.0026 · **−0.1258** | 22 · −0.0002 · −0.0024 |
| A05 | 119 · +0.1015 · +0.0201 · −0.0072 | 8 · −0.0232 · **−0.2822** | 7 · −0.0046 · −0.0461 | 2 · −0.0003 · −0.0053 |
| A09 | 27 · +0.0346 · +0.0130 · +0.0089 | 2 · −0.0173 · **−0.1790** | 5 · −0.0046 · −0.0384 | 1 · −0.0002 · −0.0077 |

Concentration (A01, `POSTHOC_L4_basis_reconcile.json`): 247 holds, per-hold B1 − B2 percentiles 1/5/25/50/75/95/99 = −520.8 / −35.5 / −2.5 / **−0.28** / +1.0 / +6.2 / +45.8 bps·capital. The top 10 holds carry 84 % of \|difference\|. Seven holds breach the price-identity guard (|ln spot/perp| > ln 1.25) while held, and they carry −4,852 of the −5,391 total. Excluding those 7 holds, W basis is B1 −0.0162 vs B2 +0.0374 bps/anchor.

Largest events (raw paths over the last 24 anchors, `l4_posthoc_event_paths_stdout.log`):

| hold (A01 unless noted) | exit | B2 P&L / B1 P&L (bps·capital) | raw B2 into exit | raw B1 into exit | spot trading / funding events |
|---|---|---|---|---|---|
| MDTUSDT 2024-05-15 → 2025-06-20 | forced b | −2.8 / −2,138.6 | 72.6 constant for all 24 anchors | +28,674 … +34,805 (+32,094 at exit) | spot trading throughout; funding events stop 6 anchors before exit |
| AMBUSDT 2025-02-19 → 02-25 | forced a | −175.1 / −1,807.5 | 107.5 then 2,549.0 constant | +132 → +27,125, then missing | spot stops 6 anchors before exit; funding continues |
| LINAUSDT 2025-03-26 → 03-29 | forced a | −64.1 / −799.1 | 966.4 constant from the jump | +31.6 → +12,830.8 (last finite +12,017.8), then missing | spot stops; funding continues |
| DENTUSDT 2026-04-19 → 04-22 | forced b | −21.9 / −291.1 | 388.3 constant | +589 → +5,205 (+4,463 at exit) | spot trading; funding stops |
| BSWUSDT 2025-07-02 → 07-05 | forced a | +1.2 / −170.1 | moving around 0 | +61.6 → +2,562.5, then missing | spot stops |
| RAYUSDT 2022-11-15 → 2023-02-25 | forced c | 0.0 / +201.7 | 378.0 constant, then missing | −2,169 … −1,565 | spot trading |

**VERIFIED:** (i) the sign flip between markings is carried by forced-exit holds, and normal-exit holds agree within 0.01 bps/anchor; (ii) raw B2 (`r5_basis/basis_panel.npz` `p_last`) repeats one value for 6 to 24+ consecutive anchors in these events; (iii) raw B1 moves by 10²–10⁴ bps in the same anchors.
**NOT VERIFIED:** whether the constant B2 values are archive rows or panel artifacts; whether the B1 closes are tradeable prices (MDT at perp ≈ 4.3 × spot for days is suspicious); what a real sleeve would have exited at.

## §11 Reading (INFERRED) and what would settle it

- Hysteresis fixes the cost side the 09-05 diagnostic identified (`docs/RESULT_carry_sleeve_diagnostic_2026-09-05.md` §0.6 「成本侧的决定量是换仓规则」). Under B2 marking the sleeve is a small, near-zero-ρ positive stream that is invested in 2023. Under the frozen rule it still does not pass: 2022 is slightly negative for the low-entry arms, and the mid arms fail multiplicity.
- The binding risk is elsewhere: **spot or perp delistings of the small names the sleeve holds**. When a spot pair stops (deposits closed) or a perp stops, the hedge breaks. B1 shows perp/spot gaps of thousands of bps in the anchors before the market disappears. The frozen premium index is flat there, so frozen P&L excludes exactly the events that decide the sign. The earlier diagnostic called its income "an upper bound because basis was not modelled" (§4 of that doc). This study adds the premium-index basis, but the tail is still unmeasured, so the upper-bound caveat still holds, through delistings rather than gradual convergence.
- To settle it (not done; needs lead scope):
  - (a) Pull 1m spot klines, perp klines and markPriceKlines from data.binance.vision on pod2 for the forced-exit symbol-days (the 15 largest are listed in `POSTHOC_L4_event_paths.json`; A01 alone has 40 forced-exit holds, 21 of them type a or b) and rebuild the hedged P&L with realistic exit timing.
  - (b) Pre-register an announcement-based exit using L3's delisting data, then re-run the 12 arms (a new family: the prior N carries over).
  - (c) Re-check B2 staleness on all held cells before any B2-marked number is quoted again.
- Program reading: on B2 marking, the sleeve meets the program's screening criteria (ρ ≈ 0, invested in 2023) but adds only mean at equal capital, and equal vol is infeasible. It cannot be the "S₂ 3–4, equal vol" second book of fact #6 in any case.

## §12 Verified vs inferred

**Verified (receipts):** all gates; all numbers in §0.1–§0.6, §2–§9 (frozen devices); the verdict label and per-arm rule flags; §10 decomposition, concentration, raw paths and the 12/12 series equality of both POST-HOC devices.
**Inferred:** that the sleeve's economics are decided by delisting events; that the premium index is the wrong instrument there; that B1 reflects real losses; the interpretation of EC as mean-only value; everything in §11.

## §13 Limits and deviations

- Paper; fixed m = 0.5 (Sharpe, signs, CIs, ρ invariant; levels and EC not). Borrow, margin interest, liquidation, drift rebalancing, idle-cash yield, capacity and spot depth are not modelled. Spot availability uses USDT pairs from a 2026-09-05 listing plus anchor-level trading evidence, with no manual renames (352 perps excluded).
- fund_aug lacks 3,797 settlement records that exist in the vision archive (G-FUND "vision unmatched"; 0.16 % of matched volume). Which names they are was not checked.
- The sleeve starts flat on 2022-01-31. The nested selection cannot see 2022 (T6 segments).
- Deviations: `TABLES_L4.md` was rendered into `receipts/pod2/` rather than `receipts/` (same content, device run with that directory). The launch shell of the first pod2 run contained a stray nested `ssh` that exited 255 locally; the build itself ran to rc=0 (`receipts/pod2/l4_build_rc.txt`). POST-HOC event-path v1 (committed) was stopped after 3 events for speed, with no result used; its partial log is kept, and v2 (committed before running) produced §10.

## §14 Reproduction (commands as run) and files

pod2, `/workspace/uplift_r3_2026-09-13/L4` (CPU only; `nvidia-smi` 0 % / 2 MiB before and after; PIDs 333197 / 339489 `Tl` before and after; launched as `nohup bash work/<name>_cmd.sh`, files in `receipts/pod2/*_cmd.sh`):
```
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4_build.py PATH,HOME,LC_CTYPE work > work/l4_build_stdout.log 2>&1; echo rc=$? > work/l4_build_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4_run.py PATH,HOME,LC_CTYPE work > work/l4_run_stdout.log 2>&1; echo rc=$? > work/l4_run_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4_posthoc_basis_reconcile.py PATH,HOME,LC_CTYPE work devices/l4_run.py > work/l4_posthoc_stdout.log 2>&1; echo rc=$? > work/l4_posthoc_rc.txt
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 taskset -c 40-47 /workspace/venv/bin/python devices/l4_posthoc_event_paths.py PATH,HOME,LC_CTYPE work devices/l4_run.py work/POSTHOC_L4_basis_reconcile.json > work/l4_posthoc_event_paths_stdout.log 2>&1; echo rc=$? > work/l4_posthoc_event_paths_rc.txt
```
local, `multi_asset/exports/research/uplift_r3_2026-09-13/L4`:
```
python3 devices/l4_tables.py receipts/pod2 > receipts/pod2/l4_tables_stdout.log 2>&1; echo "rc=$?" > receipts/pod2/l4_tables_rc.txt
```
Summary lines, all rc=0:
- `SUMMARY l4_build G-IN=True G-ALIGN=True G-A0=True G-FUND=True(match 1.0000 eq 1.0000) G-SETT=True(maxd 2.23e-09 mis 0) G-UNITS=True ALL=True out_sha256=3d9d3466ce007873 elapsed=268s self_sha256=e3ff9846bf4e9b5a`
- `SUMMARY l4_run G-SYN=True G-CAUSAL=True G-ACCT=True | arms PASS_adj=[] PASS_unadj=['A05', 'A06', 'A08'] | nested PASS=True (picks ['A03', 'A02', 'A02', 'A02']) | DSR best A02 SR 5.31 P(SR>0) N_eff 1.000 N12 0.994 N18 0.989 | VERDICT=NOT PASS (multiplicity) | elapsed=87s self_sha256=cfa2517120979a46`
- `SUMMARY l4_posthoc_basis_reconcile (POST-HOC) series_equal=12/12 …`
- `SUMMARY l4_posthoc_event_paths v2 (POST-HOC) series_equal=12/12 events=15 …`
- `SUMMARY l4_tables lines=404 verdict=NOT PASS (multiplicity)`

Commits: deb3af82 (PREREG), a1c3e09a (AMENDMENT 1), c089dcef (devices, before running), bae1c4b9 (POST-HOC reconcile device, before running), 0d30a1f9 (POST-HOC event-path v2, before running), plus this RESULT commit. Files and hashes: `SHA256SUMS` (written by `uplift_r2_2026-09-13/T6/devices/t6_sha_guard.py`). `*.npz` are git-ignored repo-wide. `receipts/pod2/L4_SERIES.npz` is local and on pod2. `l4_inputs.npz` (3d9d3466…, 55 MB) is on pod2 `work/` and in `/Users/haosiyu/cc_tmp/l4/`.
