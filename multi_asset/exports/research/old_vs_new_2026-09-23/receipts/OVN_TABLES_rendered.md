<!-- rendered by ovn_render.py from OVN_STATS.json sha256 660ea5584fee439d4189b0de221da79614e4a50b3d82c136eb5b08eaa773c81a; OVN_EXT.json sha256 2384e4799ff8cd6b7ea68c7b5d5bdb4ff5b176738695fda4bd629db24e787775 -->

### Verdict lines (AMENDMENT 1: each NEW seed must pass G1–G5 against BOTH OLD and OLD_HOLD)

- NEW_s42 vs OLD: G1=FAIL (+8.506 bps/day, 97.5% CI 30d [-0.370, +21.191]) · G2=PASS (3/3) · G3=PASS · G4=PASS · G5=PASS · all=FAIL
- NEW_s42 vs OLD_HOLD: G1=FAIL (+5.979 bps/day, 97.5% CI 30d [-1.354, +15.482]) · G2=PASS (2/3) · G3=FAIL · G4=PASS · G5=PASS · all=FAIL
- NEW_s2027 vs OLD: G1=FAIL (+7.142 bps/day, 97.5% CI 30d [-0.836, +18.266]) · G2=PASS (3/3) · G3=PASS · G4=PASS · G5=PASS · all=FAIL
- NEW_s2027 vs OLD_HOLD: G1=FAIL (+4.615 bps/day, 97.5% CI 30d [-1.909, +12.928]) · G2=PASS (2/3) · G3=FAIL · G4=PASS · G5=PASS · all=FAIL
- **VERDICT = UNDECIDED** — AMENDMENT 1: PASS iff both NEW seeds pass G1..G5 against OLD AND against OLD_HOLD; REVERSE iff both seeds' G1 97.5% interval (30-day blocks) upper bound vs OLD_HOLD < 0; else UNDECIDED (which control each seed passed is listed)
- which control each seed passed: {"NEW_s42": {"OLD": false, "OLD_HOLD": false}, "NEW_s2027": {"OLD": false, "OLD_HOLD": false}}; original prereg verdict vs OLD only (superseded, transparency): UNDECIDED

### G1–G5 for NEW_s42: measured vs gate, against each control

| # | gate | vs OLD | vs OLD_HOLD |
|---|---|---|---|
| G1 | pre-2026 d̄ mean > 0 and 97.5% two-sided lower bound (30-day blocks) > 0 | +8.506 bps/day; 97.5% [-0.370, +21.191] (30d); 95% [+0.564, +19.190]; 5d-block 97.5% [+0.610, +18.363]; 915 d × 32 paths → **FAIL** | +5.979 bps/day; 97.5% [-1.354, +15.482] (30d); 95% [-0.482, +14.239]; 5d-block 97.5% [-0.784, +13.756]; 915 d × 32 paths → **FAIL** |
| G2 | ≥ 2 of 3 segments with mean d̄ > 0 | 2023H2 +6.098 / 2024 +4.804 / 2025 +13.431 → 3/3 → **PASS** | 2023H2 -0.259 / 2024 +3.052 / 2025 +12.059 → 2/3 → **PASS** |
| G3 | NEW worst-segment Sharpe ≥ control worst − 0.10; pre-2026 maxDD (path mean) not worse than control by > 2 pp | worst-seg Sharpe NEW -0.783 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -18.1% vs ctrl -38.4% (need ≥ -40.4%) ok → **PASS** | worst-seg Sharpe NEW -0.783 vs ctrl -0.669 (need ≥ -0.769) FAIL; maxDD5m NEW -18.1% vs ctrl -29.0% (need ≥ -31.0%) ok → **FAIL** |
| G4 | G1 point estimate keeps sign under fee×1.25 / slip×1.5 / fill×0.9 | fee_x1.25 +8.763; slip_x1.5 +8.944; fill_x0.9 +8.377 (base +8.506) → **PASS** | fee_x1.25 +6.034; slip_x1.5 +6.061; fill_x0.9 +5.988 (base +5.979) → **PASS** |
| G5 | pre-2026 §4-2 day-stop events (path mean) NEW ≤ 1.25 × control | NEW 3.94 vs limit 8.05 (ctrl 6.44) → **PASS** | NEW 3.94 vs limit 7.15 (ctrl 5.72) → **PASS** |

G1 with the partial first day included (sensitivity): vs OLD: +8.572 bps/day, changes G1: False; vs OLD_HOLD: +6.048 bps/day, changes G1: False. 2026 segment mean d̄ (report only): vs OLD +1.429 bps/day; vs OLD_HOLD +1.483 bps/day

### G1–G5 for NEW_s2027: measured vs gate, against each control

| # | gate | vs OLD | vs OLD_HOLD |
|---|---|---|---|
| G1 | pre-2026 d̄ mean > 0 and 97.5% two-sided lower bound (30-day blocks) > 0 | +7.142 bps/day; 97.5% [-0.836, +18.266] (30d); 95% [+0.042, +16.751]; 5d-block 97.5% [-0.912, +16.774]; 915 d × 32 paths → **FAIL** | +4.615 bps/day; 97.5% [-1.909, +12.928] (30d); 95% [-1.198, +11.815]; 5d-block 97.5% [-1.835, +12.051]; 915 d × 32 paths → **FAIL** |
| G2 | ≥ 2 of 3 segments with mean d̄ > 0 | 2023H2 +5.892 / 2024 +4.077 / 2025 +10.844 → 3/3 → **PASS** | 2023H2 -0.465 / 2024 +2.325 / 2025 +9.472 → 2/3 → **PASS** |
| G3 | NEW worst-segment Sharpe ≥ control worst − 0.10; pre-2026 maxDD (path mean) not worse than control by > 2 pp | worst-seg Sharpe NEW -0.888 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -17.6% vs ctrl -38.4% (need ≥ -40.4%) ok → **PASS** | worst-seg Sharpe NEW -0.888 vs ctrl -0.669 (need ≥ -0.769) FAIL; maxDD5m NEW -17.6% vs ctrl -29.0% (need ≥ -31.0%) ok → **FAIL** |
| G4 | G1 point estimate keeps sign under fee×1.25 / slip×1.5 / fill×0.9 | fee_x1.25 +7.484; slip_x1.5 +7.689; fill_x0.9 +7.122 (base +7.142) → **PASS** | fee_x1.25 +4.755; slip_x1.5 +4.805; fill_x0.9 +4.733 (base +4.615) → **PASS** |
| G5 | pre-2026 §4-2 day-stop events (path mean) NEW ≤ 1.25 × control | NEW 4.62 vs limit 8.05 (ctrl 6.44) → **PASS** | NEW 4.62 vs limit 7.15 (ctrl 5.72) → **PASS** |

G1 with the partial first day included (sensitivity): vs OLD: +7.306 bps/day, changes G1: False; vs OLD_HOLD: +4.782 bps/day, changes G1: False. 2026 segment mean d̄ (report only): vs OLD +0.766 bps/day; vs OLD_HOLD +0.821 bps/day

### C1 quantified: OLD_HOLD − OLD (same model, only the failure action differs; NOT a criterion)

| quantity | value |
|---|---|
| G1-form | +2.527 bps/day; 97.5% [-2.639, +8.605] (30d); 95% [-2.010, +7.709]; 5d-block 97.5% [-2.699, +8.099]; 915 d × 32 paths → FAIL |
| G2-form | 2023H2 +6.357 / 2024 +1.752 / 2025 +1.372 → 3/3 → PASS |
| G3-form | worst-seg Sharpe NEW -0.669 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -29.0% vs ctrl -38.4% (need ≥ -40.4%) ok → PASS |
| G5-form | NEW 5.72 vs limit 8.05 (ctrl 6.44) → PASS |

### Per segment, R-main (base cost cell, scaled reading): 32-path mean [2.5%, 97.5%]

| segment | arm | Sharpe (full UTC days) | total return | CAGR | maxDD 5m | worst day | §4-2 day stops | per-name stops | turnover/gross per anchor | n windows / full days |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023H2 | OLD | -1.82 [-2.00, -1.59] | -15.8% [-17.2%, -14.1%] | -28.9% [-31.2%, -26.0%] | -22.0% [-23.2%, -20.8%] | -3.04% [-3.17%, -2.92%] | +0.0 [+0.0, +0.0] | +55 [+52, +59] | 0.1158 | 1109 / 184 |
| 2023H2 | OLD_HOLD | -0.67 [-0.90, -0.48] | -5.3% [-7.2%, -3.7%] | -10.1% [-13.7%, -7.1%] | -12.8% [-13.9%, -11.6%] | -2.85% [-2.97%, -2.78%] | +0.0 [+0.0, +0.0] | +57 [+54, +61] | 0.0878 | 1109 / 184 |
| 2023H2 | NEW_s42 | -0.78 [-0.99, -0.49] | -5.0% [-6.6%, -2.6%] | -9.5% [-12.6%, -5.2%] | -14.8% [-16.1%, -13.1%] | -3.08% [-3.64%, -2.65%] | +0.3 [+0.0, +1.0] | +75 [+69, +79] | 0.0538 | 1109 / 184 |
| 2023H2 | NEW_s2027 | -0.89 [-1.12, -0.59] | -4.4% [-6.4%, -2.2%] | -8.5% [-12.2%, -4.2%] | -15.0% [-16.0%, -14.0%] | -4.09% [-4.90%, -3.68%] | +1.0 [+0.8, +1.0] | +87 [+83, +91] | 0.0545 | 1109 / 184 |
| 2024 | OLD | +0.95 [+0.77, +1.06] | +18.3% [+14.1%, +20.8%] | +18.2% [+14.1%, +20.8%] | -26.9% [-28.3%, -25.7%] | -4.31% [-4.47%, -4.20%] | +1.0 [+1.0, +1.0] | +258 [+251, +268] | 0.0867 | 2196 / 366 |
| 2024 | OLD_HOLD | +1.21 [+1.06, +1.36] | +25.8% [+22.0%, +29.7%] | +25.8% [+22.0%, +29.6%] | -24.6% [-26.2%, -23.4%] | -4.30% [-4.49%, -4.01%] | +1.0 [+0.8, +1.0] | +307 [+295, +323] | 0.0655 | 2196 / 366 |
| 2024 | NEW_s42 | +1.85 [+1.67, +2.00] | +41.0% [+36.1%, +44.8%] | +40.9% [+36.0%, +44.6%] | -13.7% [-14.9%, -12.4%] | -3.75% [-4.38%, -3.42%] | +0.2 [+0.0, +1.0] | +357 [+317, +376] | 0.0649 | 2196 / 366 |
| 2024 | NEW_s2027 | +1.73 [+1.57, +1.91] | +37.4% [+33.3%, +42.0%] | +37.2% [+33.2%, +41.9%] | -12.9% [-14.2%, -11.7%] | -3.71% [-4.39%, -3.15%] | +0.4 [+0.0, +1.0] | +471 [+438, +500] | 0.0537 | 2196 / 366 |
| 2025 | OLD | +0.21 [-0.06, +0.43] | +2.2% [-4.9%, +7.9%] | +2.2% [-4.9%, +7.9%] | -27.7% [-30.0%, -26.3%] | -4.62% [-5.04%, -4.28%] | +5.4 [+4.0, +7.0] | +480 [+469, +490] | 0.0963 | 2190 / 365 |
| 2025 | OLD_HOLD | +0.42 [+0.28, +0.58] | +7.6% [+3.8%, +12.1%] | +7.6% [+3.8%, +12.1%] | -19.6% [-22.8%, -18.5%] | -6.90% [-7.20%, -6.68%] | +4.8 [+4.0, +6.0] | +668 [+576, +691] | 0.0559 | 2190 / 365 |
| 2025 | NEW_s42 | +1.89 [+1.69, +2.05] | +65.6% [+56.0%, +73.4%] | +65.6% [+56.0%, +73.4%] | -12.4% [-13.2%, -11.8%] | -4.78% [-4.96%, -4.42%] | +3.3 [+2.0, +4.0] | +644 [+567, +661] | 0.0512 | 2190 / 365 |
| 2025 | NEW_s2027 | +1.65 [+1.47, +1.86] | +51.3% [+43.6%, +61.6%] | +51.3% [+43.6%, +61.6%] | -12.1% [-12.9%, -11.5%] | -4.46% [-4.80%, -4.32%] | +3.2 [+3.0, +4.0] | +525 [+514, +532] | 0.0451 | 2190 / 365 |
| pre2026 | OLD | +0.12 [-0.04, +0.24] | +1.8% [-6.7%, +9.4%] | +0.7% [-2.7%, +3.6%] | -38.4% [-39.8%, -36.8%] | -4.62% [-5.04%, -4.36%] | +6.4 [+5.0, +8.0] | +793 [+782, +806] | 0.0964 | 5495 / 915 |
| pre2026 | OLD_HOLD | +0.53 [+0.45, +0.63] | +28.3% [+22.3%, +35.7%] | +10.4% [+8.4%, +12.9%] | -29.0% [-30.6%, -27.5%] | -6.90% [-7.20%, -6.68%] | +5.7 [+5.0, +7.0] | +1031 [+932, +1071] | 0.0661 | 5495 / 915 |
| pre2026 | NEW_s42 | +1.44 [+1.35, +1.55] | +121.9% [+110.3%, +135.3%] | +37.4% [+34.5%, +40.6%] | -18.1% [-20.3%, -15.8%] | -4.78% [-4.96%, -4.42%] | +3.9 [+3.0, +5.2] | +1075 [+958, +1109] | 0.0572 | 5495 / 915 |
| pre2026 | NEW_s2027 | +1.28 [+1.21, +1.39] | +98.6% [+89.6%, +110.5%] | +31.4% [+29.0%, +34.5%] | -17.6% [-19.5%, -15.8%] | -4.49% [-4.90%, -4.32%] | +4.6 [+4.0, +6.0] | +1083 [+1047, +1113] | 0.0504 | 5495 / 915 |
| 2026 | OLD | +4.15 [+3.87, +4.45] | +130.6% [+117.2%, +142.7%] | +252.4% [+221.9%, +280.5%] | -18.2% [-19.9%, -16.6%] | -4.61% [-4.73%, -4.49%] | +1.6 [+1.0, +3.4] | +329 [+318, +339] | 0.0482 | 1453 / 242 |
| 2026 | OLD_HOLD | +4.15 [+3.82, +4.43] | +130.3% [+114.6%, +142.7%] | +251.7% [+216.2%, +280.6%] | -18.1% [-19.8%, -16.5%] | -4.61% [-4.73%, -4.48%] | +1.6 [+1.0, +3.4] | +326 [+315, +335] | 0.0484 | 1453 / 242 |
| 2026 | NEW_s42 | +4.25 [+4.00, +4.54] | +138.3% [+124.2%, +151.2%] | +270.3% [+237.6%, +300.9%] | -19.7% [-20.9%, -18.2%] | -4.81% [-5.05%, -4.40%] | +2.6 [+2.0, +3.2] | +320 [+312, +329] | 0.0485 | 1453 / 242 |
| 2026 | NEW_s2027 | +4.25 [+3.95, +4.60] | +134.7% [+121.9%, +150.1%] | +261.8% [+232.5%, +298.2%] | -19.4% [-20.4%, -18.2%] | -4.58% [-4.92%, -4.19%] | +2.1 [+1.0, +3.0] | +322 [+313, +331] | 0.0479 | 1453 / 242 |

### Cash decomposition, R-main: bps per anchor per unit target gross, 32-path mean (identity g = price − funding paid − fee − unknown, max err printed)

| segment | arm | g | price & trading | funding paid | fee | unknown excluded | identity max err |
|---|---|---|---|---|---|---|---|
| 2023H2 | OLD | -0.738 | -0.172 | +0.278 | +0.288 | +0.000 | 6.3e-11 |
| 2023H2 | OLD_HOLD | -0.208 | +0.146 | +0.136 | +0.218 | +0.000 | 7.9e-11 |
| 2023H2 | NEW_s42 | -0.202 | -0.053 | +0.014 | +0.135 | +0.000 | 6.6e-11 |
| 2023H2 | NEW_s2027 | -0.179 | +0.017 | +0.059 | +0.138 | +0.000 | 4.9e-11 |
| 2024 | OLD | +0.425 | +0.869 | +0.227 | +0.217 | +0.000 | 8.5e-11 |
| 2024 | OLD_HOLD | +0.567 | +0.925 | +0.194 | +0.164 | +0.000 | 9.2e-11 |
| 2024 | NEW_s42 | +0.829 | +1.146 | +0.155 | +0.162 | +0.000 | 1.1e-10 |
| 2024 | NEW_s2027 | +0.768 | +1.059 | +0.158 | +0.134 | +0.000 | 1.1e-10 |
| 2025 | OLD | +0.130 | +1.110 | +0.735 | +0.246 | +0.000 | 1.1e-10 |
| 2025 | OLD_HOLD | +0.236 | +0.816 | +0.436 | +0.144 | +0.000 | 1.0e-10 |
| 2025 | NEW_s42 | +1.232 | +1.784 | +0.420 | +0.131 | +0.000 | 1.2e-10 |
| 2025 | NEW_s2027 | +1.022 | +1.531 | +0.393 | +0.116 | -0.000 | 1.2e-10 |
| pre2026 | OLD | +0.073 | +0.755 | +0.440 | +0.243 | +0.000 | 1.1e-10 |
| pre2026 | OLD_HOLD | +0.279 | +0.724 | +0.278 | +0.167 | +0.000 | 1.0e-10 |
| pre2026 | NEW_s42 | +0.782 | +1.158 | +0.232 | +0.144 | +0.000 | 1.2e-10 |
| pre2026 | NEW_s2027 | +0.678 | +1.037 | +0.232 | +0.128 | -0.000 | 1.2e-10 |
| 2026 | OLD | +2.988 | +4.179 | +1.069 | +0.123 | +0.000 | 1.2e-10 |
| 2026 | OLD_HOLD | +2.983 | +4.174 | +1.068 | +0.123 | +0.000 | 1.1e-10 |
| 2026 | NEW_s42 | +3.101 | +4.326 | +1.099 | +0.125 | +0.000 | 1.3e-10 |
| 2026 | NEW_s2027 | +3.047 | +4.269 | +1.099 | +0.123 | +0.000 | 1.3e-10 |

### Certified MEAN PATH (descriptive; the published headline convention)

| segment | arm | Sharpe | total return | maxDD 5m |
|---|---|---|---|---|
| 2023H2 | OLD | -1.82 | -15.8% | -22.0% |
| 2023H2 | OLD_HOLD | -0.67 | -5.3% | -12.6% |
| 2023H2 | NEW_s42 | -0.79 | -5.0% | -14.8% |
| 2023H2 | NEW_s2027 | -0.90 | -4.4% | -15.0% |
| 2024 | OLD | +0.96 | +18.3% | -26.9% |
| 2024 | OLD_HOLD | +1.21 | +25.8% | -24.6% |
| 2024 | NEW_s42 | +1.86 | +41.0% | -13.7% |
| 2024 | NEW_s2027 | +1.74 | +37.4% | -12.9% |
| 2025 | OLD | +0.21 | +2.2% | -27.6% |
| 2025 | OLD_HOLD | +0.42 | +7.6% | -19.5% |
| 2025 | NEW_s42 | +1.90 | +65.6% | -11.9% |
| 2025 | NEW_s2027 | +1.66 | +51.3% | -11.8% |
| pre2026 | OLD | +0.12 | +1.7% | -38.4% |
| pre2026 | OLD_HOLD | +0.54 | +28.3% | -28.9% |
| pre2026 | NEW_s42 | +1.45 | +121.9% | -18.1% |
| pre2026 | NEW_s2027 | +1.29 | +98.7% | -17.5% |
| 2026 | OLD | +4.18 | +130.6% | -18.1% |
| 2026 | OLD_HOLD | +4.18 | +130.3% | -18.1% |
| 2026 | NEW_s42 | +4.28 | +138.3% | -19.7% |
| 2026 | NEW_s2027 | +4.28 | +134.7% | -19.4% |

### Cost cells and the literal (fixed-380) reading: path-mean Sharpe / total return (report only)

| cell | segment | OLD | OLD_HOLD | NEW_s42 | NEW_s2027 |
|---|---|---|---|---|---|
| fee_x1.25 | pre2026 | S +0.00 / -4.6% | S +0.45 / +22.6% | S +1.37 / +113.0% | S +1.23 / +92.2% |
| fee_x1.25 | 2026 | S +4.10 / +128.2% | S +4.11 / +128.3% | S +4.21 / +136.5% | S +4.21 / +133.2% |
| slip_x1.5 | pre2026 | S -0.08 / -8.8% | S +0.39 / +18.8% | S +1.32 / +107.0% | S +1.18 / +87.2% |
| slip_x1.5 | 2026 | S +4.07 / +126.8% | S +4.08 / +126.9% | S +4.17 / +134.5% | S +4.19 / +131.9% |
| fill_x0.9 | pre2026 | S +0.12 / +2.2% | S +0.51 / +27.1% | S +1.43 / +120.0% | S +1.28 / +98.9% |
| fill_x0.9 | 2026 | S +4.13 / +129.8% | S +4.13 / +129.6% | S +4.28 / +139.7% | S +4.26 / +135.3% |
| lit | pre2026 | S -0.34 / -23.5% | not run (by design) | S +0.89 / +40.6% | S +0.83 / +34.6% |
| lit | 2026 | S +4.01 / +123.7% | not run (by design) | S +4.27 / +139.6% | S +4.27 / +136.0% |

### 2026-08-31T04Z → 2026-09-18T20Z (DESCRIBE ONLY; OLD = certified OBJB_A0X run)

| arm | total return | Sharpe (full days) | maxDD 5m | worst day | g | day stops | d̄ vs OLD (point, bps/day) |
|---|---|---|---|---|---|---|---|
| OLD | -5.4% | -2.43 | -10.8% | -3.75% | -2.295 | 1.00 | — |
| NEW_s42 | -5.9% | -2.89 | -11.2% | -3.73% | -2.554 | 1.00 | -3.63 (18 d) |
| NEW_s2027 | -5.6% | -2.66 | -10.9% | -3.73% | -2.413 | 1.00 | -2.06 (18 d) |

Control, NEW X run vs NEW main run on shared anchors ≤ 2026-08-30T20Z: {"NEW_s42": {"shared_anchors": 9138, "max_abs_diff_window_return": 0.0, "bitwise_equal": true}, "NEW_s2027": {"shared_anchors": 9138, "max_abs_diff_window_return": 0.0, "bitwise_equal": true}}

### R-P (§4-4 −25 % from the base's starting equity, permanent halt) and R-P2 (day stop + named resume delay), FULL_RECIPE base 2023-06-30T04Z — report only

| arm | R-P halted paths | R-P median halt anchor | R-P end return (P-halt / no-halt) | R-P2 H=12h W_ENTRY: paths hit −25 % | median −25 % anchor | end return P2 / no halt |
|---|---|---|---|---|---|---|
| OLD | 32/32 | 2024-03-18T16:00:00Z | -25.3% / +134.6% | 32/32 | 2024-03-18T16:00:00Z | -25.3% / +134.6% (n_eff 32) |
| OLD_HOLD | 10/32 | 2024-08-05T08:00:00Z | +128.9% / +195.4% | 19/32 | 2024-07-21T20:00:00Z | +65.7% / +195.4% (n_eff 32) |
| NEW_s42 | 0/32 | none | +428.8% / +428.8% | 0/32 | None | +425.0% / +428.8% (n_eff 32) |
| NEW_s2027 | 0/32 | none | +366.1% / +366.1% | 0/32 | None | +367.7% / +366.1% (n_eff 32) |
