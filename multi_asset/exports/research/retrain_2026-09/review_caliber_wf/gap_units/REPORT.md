# REPORT — gap_units: units chain, cost model, and which column/arm each quoted number came from

> **创建:** 2026-09-04 | **Session:** b9646a9e (teammate `gap_units`, read-only on pod2) | **状态:** 完成, 全部数字由 `units_table.py` 打印 | **作废条件:** `/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_*_s42.npz` 或 `refute_C6_{1,2}` alt npz 重生成; `w10_universe.py` sha 变化

**Device receipts.** `units_table.py` self sha256[:16] `16ef03fa642b3218`; `w10_universe.py` sha256[:16] `64c70a44ee88b795`; meta `/workspace/data/wide_fea_v2ext_meta.npz` sha256[:16] `4b1b6047107d2557` (= realpath of `/workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz`). Full sha256: `units_table.py` `16ef03fa642b321899cb58ecd4b83dfe087b6fa461e7848df56fb4480e355f70`, `units_table.out` `cba2b2509da6edf30a2b24847b4ee6bc7d084e1491874732269278dc5d7b7569` (identical on pod and Mac).

**Command (verbatim):**
```
cd /workspace/review_scratch/gap_units && /workspace/venv/bin/python units_table.py > units_table.out 2>&1
```
Files: pod `/workspace/review_scratch/gap_units/{units_table.py,units_table.out,REPORT.md,cfg_dump.py,cfg_dump.out}`; Mac `.../scratchpad/review_caliber/gap_units/` (same names). Line numbers `Lnnn` below refer to `w10_universe.py`; `out:nnn` refer to `units_table.out`.

## 1. Definitions (VERIFIED — lines printed from the device file, out:7-83)

- **Units.** Every `*_rec` column except `ts/gross_*/nsel/nmember/fires/w3_*/turnover/netlong` is **bps per anchor per unit NAV**, where the book's weights sum to `gross_total` (0.53-0.88 of NAV in the tables below, L309 `gt = np.abs(sm).sum()`). "Per gross" = divide by `gross_total`. Annualised %/gross = ×2190/100. "2× gross" = ×2 (the task's convention; the live book runs 1.5×NAV per CLAUDE.md, so the live-leverage figure is 1.5× the per-gross number, not 2×).
- **`net`** (file caliber, col 1) = `pnl_raw − car − cbps` on the blended book `sm` (L264, L310): `pnl_raw = Σ_m sm[m]·yv ×1e4` (L281), `car = Σ_m sm[m]·fnow·(4/ivv) ×1e4` (L280, funding paid by longs), `cbps` = COST_B on `|trade[m]|`, `trade = sm − HB` (L265, L274-275).
- **`net_ex`** (executor caliber, col 18) = `pnl_r − car_r − cbps_r` (L312) on `smr` = `sm` with its non-zero set re-demeaned and L1-rescaled to the original gross (L266-272, the executor's `reshape_after_withhold` semantics), trades `trr = smr − HR` (L273). `pnl_ex`/`carry_ex`/`cost_ex` = cols 19/20/21 (L304-307). Identity `net_ex = pnl_ex − carry_ex − cost_ex` holds row-wise with max residual 0.000e+00 in all 22 arm blocks (out: every `-- ARM` line).
- **`gross_total`** = `Σ|sm|` over all 829 names; `gross_member` over current members; `gross_sel` over tradable set (L309).
- **Caliber switch** L17-20: `CAL=simple` applies `np.expm1` to `y4` (L277-278, also in the seat-return path L135-136); `CAL=log` applies no transform. The meta `y4` is bitwise `Σ r5[E..E+47]` of 5-minute simple returns (refuters' receipt `refute_C6_2/bitwise_y4.out` `old_sum exact_eq=1.000000`; my `y4-INPUT CHECK` reproduces every run's `pnl` column from the saved `W` and the run's own y4 file at max|Δ| 0.0000 bps). So `CAL=log` = **Σ-simple**, `CAL=simple` = **expm1 applied to a Σ-simple target** (a convexity add-on, not the exchange caliber).
- **Stop-layer arms** L319: `("S0", None, 0, 0)` = depth None → no stop; `("d30_n2_c42", -0.30, 2, 42)` = a name is suspended (`tgt[bl]=0`, L211-213) when its average-cost depth ≤ −30% for 2 consecutive anchors, cool-off 42 anchors (L300-303).
- **COST_B** L116 `[(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]` = `(maker_bps, taker_bps, maker_fraction)` per liquidity tier; `tier_of` L117-119: tier 0 if `qv4h ≥ 5e6`, tier 1 if `≥ 1e6`, else tier 2, with `qv4h = expm1(clip(qvk,0,30))*48` (L198). Cost per anchor = `Σ_tier Σ_names |trade| × (fr·mk + (1−fr)·tk)` (L275, L307), one-way, bps per NAV. Blended rates printed by the script (out:86-89):
      tier 0: maker -0.25 bps × 0.85 + taker 5.00 bps × 0.15 = blended 0.5375 bps per unit |trade| (one-way, per NAV)
      tier 1: maker +0.50 bps × 0.75 + taker 6.00 bps × 0.25 = blended 1.8750 bps per unit |trade| (one-way, per NAV)
      tier 2: maker +2.00 bps × 0.55 + taker 8.00 bps × 0.45 = blended 4.7000 bps per unit |trade| (one-way, per NAV)
      cost per anchor = Σ_tier Σ_names |trade_name| × blended_rate_tier  (bps per NAV); trade = one-way change in weight (sm - previous)

**Device mislabel (INFERRED from L349 text):** `w10_ablation_summary_*.json["turnover_ex_mean"]` is `np.abs(R[:,21]).mean()` = **cost_ex**, not turnover. `turnover` (col 17) is `Σ|sm − HB|` on the blended path, not the reshaped path; the `cost_ex/turnover` ratio below is indicative only.

## 2. What each npz is (VERIFIED from `config_json` + y4-input recompute)

| form | caliber | file | config_json | y4 input check |
|---|---|---|---|---|
| fixed-seat live | Σ-simple (CAL=log) | `port_w10/.../pod_live_w3fix_callog_s42.npz` sha `5faf9106ed84dc8f` | CAL=log W3FIX=0.21,0,0.79 M829 T400 FTRIM=zero LEGS=101 PHI=0.45 | meta y4, T=id: max|Δ| 0.0000 bps |
| fixed-seat live | expm1 (CAL=simple) | `pod_live_w3fix_calsimple_s42.npz` sha `53bdbcfbbc9b5f21` | CAL=simple, same flags | meta y4, T=expm1: 0.0000 |
| fixed-seat live | Π same window | `refute_C6_1/dev/.../alt_true_old_w3fix.npz` sha `6f0376d6432ef89c` | CAL=log, same flags | `refute_C6_1/alt/meta_true_old.npz`: 0.0000 |
| fixed-seat live | Π exchange window | `refute_C6_2/altrun/newprod/.../alt_newprod_w3fix.npz` sha `aa5771a803a880ba` | CAL=log, same flags | `refute_C6_2/altrun/meta_newprod.npz`: 0.0000 |
| dynamic-seat live | Σ-simple | `pod_live_callog_s42.npz` sha `dd85ded80c7af058` | CAL=log W3FIX=None M829 T400 FTRIM=zero | 0.0000 |
| dynamic-seat live | expm1 | `pod_live_calsimple_s42.npz` sha `e0917815955a5f3b` | CAL=simple, same | 0.0000 |
| dynamic-seat live | Π same window | `alt_true_old_dyn.npz` sha `a47f14ee5793e5d2` | CAL=log, same | 0.0000 |
| dynamic-seat live | Π exchange window | `alt_newprod_dyn.npz` sha `b95c1553ee0bce10` | CAL=log, same | 0.0000 |
| canon | Σ-simple | `pod_canon_callog_s42.npz` sha `e80c957d949e3247` | CAL=log W3FIX=None M0 T0 FTRIM=off | meta members: 0.0000 |
| canon | expm1 | `pod_canon_calsimple_s42.npz` sha `5d601e1adeb195ab` | CAL=simple, same | 0.0000 |
| canon | compounded | **NOT AVAILABLE** (out:91) | — | — |
| extra: canon fixed-seat | Σ-simple | `pod_canon_w3fix_callog_s42.npz` sha `8f8194586f289520` | CAL=log W3FIX=0.21,0,0.79 M0 T0 FTRIM=off | 0.0000 |

- "Π same window" = `expm1(Σ log1p(r5[E..E+47]))` (refute_C6_1 `build_alt_meta.py`, `true_old`); "Π exchange window" = same on `[E+1..E+48]` = hold `(E, E+4h]` (refute_C6_2 `build_alt_meta.py`, `newprod`, PARITY vs `dlw_targets.npz["y4s"]` exact_eq 1.000000 in the refuters' `build_alt_meta.out`). That the alt meta files really are Π(1+r) is **INFERRED** from the refuters' build scripts/receipts; that each alt run consumed its stated meta file is **VERIFIED** by my recompute. Cross-checks (out:602-620): C6_1 `alt_sum_old` == PORT callog bitwise (both arms, both forms); C6_2 `alt_base` == PORT bitwise; C6_1 `true_new` vs C6_2 `newprod` (independent builds of the same target) differ by max 6.6e-08 bps in `net_ex`; C6_1 `rerun_prodnew` == C6_2 `newprod` bitwise.

## 3. Cost model, numerically — fixed-seat live form, `cost_ex` per year (VERIFIED, out:548-573)

```
  [Σ-simple] S0:
    2022: cost_ex 0.0268 bps/anchor (= 0.59%/yr NAV; cost(file) 0.0252; turnover 0.01629; cost_ex/turnover 1.645 bps per unit)
    2023: cost_ex 0.0367 bps/anchor (= 0.80%/yr NAV; cost(file) 0.0351; turnover 0.01722; cost_ex/turnover 2.131 bps per unit)
    2024: cost_ex 0.0325 bps/anchor (= 0.71%/yr NAV; cost(file) 0.0303; turnover 0.01392; cost_ex/turnover 2.334 bps per unit)
    2025: cost_ex 0.0407 bps/anchor (= 0.89%/yr NAV; cost(file) 0.0357; turnover 0.01235; cost_ex/turnover 3.297 bps per unit)
    2026: cost_ex 0.0680 bps/anchor (= 1.49%/yr NAV; cost(file) 0.0600; turnover 0.01701; cost_ex/turnover 3.997 bps per unit)
  [Σ-simple] d30_n2_c42:
    2022: cost_ex 0.0273 bps/anchor (= 0.60%/yr NAV; cost(file) 0.0255; turnover 0.01645; cost_ex/turnover 1.661 bps per unit)
    2023: cost_ex 0.0370 bps/anchor (= 0.81%/yr NAV; cost(file) 0.0352; turnover 0.01731; cost_ex/turnover 2.136 bps per unit)
    2024: cost_ex 0.0337 bps/anchor (= 0.74%/yr NAV; cost(file) 0.0309; turnover 0.01428; cost_ex/turnover 2.358 bps per unit)
    2025: cost_ex 0.0422 bps/anchor (= 0.92%/yr NAV; cost(file) 0.0366; turnover 0.01261; cost_ex/turnover 3.345 bps per unit)
    2026: cost_ex 0.0691 bps/anchor (= 1.51%/yr NAV; cost(file) 0.0605; turnover 0.01707; cost_ex/turnover 4.046 bps per unit)
  [expm1] S0:
    2022: cost_ex 0.0268 bps/anchor (= 0.59%/yr NAV; cost(file) 0.0252; turnover 0.01629; cost_ex/turnover 1.645 bps per unit)
    2023: cost_ex 0.0367 bps/anchor (= 0.80%/yr NAV; cost(file) 0.0351; turnover 0.01722; cost_ex/turnover 2.131 bps per unit)
    2024: cost_ex 0.0325 bps/anchor (= 0.71%/yr NAV; cost(file) 0.0303; turnover 0.01392; cost_ex/turnover 2.334 bps per unit)
    2025: cost_ex 0.0407 bps/anchor (= 0.89%/yr NAV; cost(file) 0.0357; turnover 0.01235; cost_ex/turnover 3.297 bps per unit)
    2026: cost_ex 0.0680 bps/anchor (= 1.49%/yr NAV; cost(file) 0.0600; turnover 0.01701; cost_ex/turnover 3.997 bps per unit)
  [expm1] d30_n2_c42:
    2022: cost_ex 0.0272 bps/anchor (= 0.60%/yr NAV; cost(file) 0.0255; turnover 0.01642; cost_ex/turnover 1.658 bps per unit)
    2023: cost_ex 0.0371 bps/anchor (= 0.81%/yr NAV; cost(file) 0.0353; turnover 0.01732; cost_ex/turnover 2.141 bps per unit)
    2024: cost_ex 0.0336 bps/anchor (= 0.74%/yr NAV; cost(file) 0.0309; turnover 0.01430; cost_ex/turnover 2.354 bps per unit)
    2025: cost_ex 0.0419 bps/anchor (= 0.92%/yr NAV; cost(file) 0.0364; turnover 0.01251; cost_ex/turnover 3.350 bps per unit)
    2026: cost_ex 0.0687 bps/anchor (= 1.50%/yr NAV; cost(file) 0.0603; turnover 0.01698; cost_ex/turnover 4.046 bps per unit)
```

Reading: `cost_ex` for the fixed-seat live d30 arm is 0.0337 / 0.0422 / 0.0691 bps per anchor per NAV in 2024 / 2025 / 2026, i.e. 0.74% / 0.92% / 1.51% of NAV per year. Implied all-in cost per unit one-way turnover rises from 2.358 to 4.046 bps (indicative; paths differ), approaching the tier-2 blended rate 4.7000 bps as the tradable set spreads into thinner names. Cost is not what separates the calibers: `cost_ex` is identical across calibers for S0 (out:625), and for d30 differs only in the fourth decimal (2024 0.0337 vs 0.0336; 2025 0.0422 vs 0.0419; 2026 0.0691 vs 0.0687).

## 4. Headline tables (VERIFIED; d30 arm out:404-473, S0 arm out:476-545)

Columns: `net_ex` bps/anchor per NAV; `A` = mean(net_ex)/mean(gross_total) bps/anchor per gross; `A %/yr gross` = A×2190/100; Sharpe = mean/std(ddof=1)×√2190 on net_ex; DD = max drawdown of cumsum(net_ex) in bps NAV, zero baseline (matches the refuters' no-baseline convention for every row checked: 1814.9 vs 1814.9, out:121); worst month = min over UTC calendar months of Σ net_ex; `cost_ex` bps/anchor. 2026 rows: `2026<=08-10` = 1332 anchors = 7.3 months; `2026->08-30` = 1452 anchors = 8.0 months (the extra 120 anchors are the post-08-10 tail). Full-width tables with recipe B, 2× gross, DD in gross bps with peak→trough dates, `net` (file caliber), w3 seats, turnover, pnl_ex/carry_ex are in `units_table.out` per FORM block (out:94-402).

### 4a. Arm d30_n2_c42 (stop layer; the deployed arm)

| form | caliber | period | n | net_ex | A per-gross | A %/yr gross | Sharpe | DD NAV bps | worst month | cost_ex |
|---|---|---|---|---|---|---|---|---|---|---|
| fixed-seat live | Σ-simple | 2024 | 2196 | -0.6421 | -0.7585 | -16.61% | -1.682 | 1814.9 | 2024-11 -717.0 | 0.0337 |
| fixed-seat live | Σ-simple | 2025 | 2190 | +0.2844 | +0.3790 | +8.30% | +0.673 | 901.8 | 2025-01 -634.5 | 0.0422 |
| fixed-seat live | Σ-simple | 2026<=08-10 | 1332 | +2.9107 | +3.7893 | +82.99% | +5.164 | 458.1 | 2026-02 +171.2 | 0.0679 |
| fixed-seat live | Σ-simple | 2026->08-30 | 1452 | +2.3780 | +3.0986 | +67.86% | +4.209 | 774.0 | 2026-08 -252.4 | 0.0691 |
| fixed-seat live | Σ-simple | 2024->26 | 5838 | +0.4566 | +0.5774 | +12.65% | +1.017 | 2613.7 | 2024-11 -717.0 | 0.0457 |
| fixed-seat live | Σ-simple | 2025->26 | 3642 | +1.1191 | +1.4780 | +32.37% | +2.308 | 901.8 | 2025-01 -634.5 | 0.0529 |
| fixed-seat live | expm1 | 2024 | 2196 | -0.3582 | -0.4236 | -9.28% | -0.921 | 1513.6 | 2024-11 -576.1 | 0.0336 |
| fixed-seat live | expm1 | 2025 | 2190 | +1.4060 | +1.8660 | +40.87% | +3.079 | 717.5 | 2025-01 -463.5 | 0.0419 |
| fixed-seat live | expm1 | 2026<=08-10 | 1332 | +4.9478 | +6.4204 | +140.61% | +8.555 | 263.9 | 2026-08 +324.3 | 0.0677 |
| fixed-seat live | expm1 | 2026->08-30 | 1452 | +4.3441 | +5.6332 | +123.37% | +7.490 | 694.3 | 2026-08 +41.5 | 0.0687 |
| fixed-seat live | expm1 | 2024->26 | 5838 | +1.4731 | +1.8588 | +40.71% | +3.139 | 2126.0 | 2024-11 -576.1 | 0.0455 |
| fixed-seat live | expm1 | 2025->26 | 3642 | +2.5774 | +3.3890 | +74.22% | +5.051 | 717.5 | 2025-01 -463.5 | 0.0526 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024 | 2196 | -0.7337 | -0.8687 | -19.02% | -1.920 | 1972.5 | 2024-11 -752.6 | 0.0337 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025 | 2190 | +0.2068 | +0.2761 | +6.05% | +0.477 | 822.4 | 2025-01 -559.4 | 0.0423 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026<=08-10 | 1332 | +2.8478 | +3.7300 | +81.69% | +5.072 | 357.0 | 2026-08 +175.6 | 0.0684 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026->08-30 | 1452 | +2.3233 | +3.0428 | +66.64% | +4.128 | 765.0 | 2026-08 -244.2 | 0.0694 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024->26 | 5838 | +0.3795 | +0.4812 | +10.54% | +0.838 | 2691.5 | 2024-11 -752.6 | 0.0458 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025->26 | 3642 | +1.0506 | +1.3919 | +30.48% | +2.145 | 822.4 | 2025-01 -559.4 | 0.0531 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024 | 2196 | -0.7089 | -0.8395 | -18.39% | -1.855 | 1912.7 | 2024-11 -756.8 | 0.0337 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025 | 2190 | +0.2538 | +0.3387 | +7.42% | +0.586 | 849.3 | 2025-01 -574.9 | 0.0423 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026<=08-10 | 1332 | +2.8329 | +3.7141 | +81.34% | +5.046 | 351.9 | 2026-08 +161.5 | 0.0684 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026->08-30 | 1452 | +2.3236 | +3.0458 | +66.70% | +4.132 | 753.5 | 2026-08 -238.0 | 0.0694 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024->26 | 5838 | +0.4065 | +0.5155 | +11.29% | +0.899 | 2657.3 | 2024-11 -756.8 | 0.0458 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025->26 | 3642 | +1.0790 | +1.4298 | +31.31% | +2.207 | 849.3 | 2025-01 -574.9 | 0.0531 |
| dynamic-seat live | Σ-simple | 2024 | 2196 | +0.1489 | +0.2473 | +5.42% | +0.533 | 794.9 | 2024-04 -363.1 | 0.0825 |
| dynamic-seat live | Σ-simple | 2025 | 2190 | +0.3590 | +0.6756 | +14.79% | +1.146 | 417.6 | 2025-12 -294.5 | 0.1037 |
| dynamic-seat live | Σ-simple | 2026<=08-10 | 1332 | +2.5118 | +3.2180 | +70.47% | +4.832 | 452.1 | 2026-02 +103.6 | 0.0902 |
| dynamic-seat live | Σ-simple | 2026->08-30 | 1452 | +2.0132 | +2.5838 | +56.58% | +3.842 | 770.6 | 2026-08 -293.5 | 0.0899 |
| dynamic-seat live | Σ-simple | 2024->26 | 5838 | +0.6914 | +1.1159 | +24.44% | +1.884 | 794.9 | 2024-04 -363.1 | 0.0923 |
| dynamic-seat live | Σ-simple | 2025->26 | 3642 | +1.0185 | +1.6161 | +35.39% | +2.479 | 770.6 | 2025-12 -294.5 | 0.0982 |
| dynamic-seat live | expm1 | 2024 | 2196 | +0.2195 | +0.3450 | +7.56% | +0.749 | 585.5 | 2024-07 -343.2 | 0.0646 |
| dynamic-seat live | expm1 | 2025 | 2190 | +1.2226 | +2.2253 | +48.73% | +3.374 | 646.8 | 2025-04 -369.9 | 0.0779 |
| dynamic-seat live | expm1 | 2026<=08-10 | 1332 | +4.8227 | +7.0235 | +153.82% | +8.697 | 252.5 | 2026-08 +342.7 | 0.0559 |
| dynamic-seat live | expm1 | 2026->08-30 | 1452 | +4.2467 | +6.1647 | +135.01% | +7.633 | 688.9 | 2026-08 +85.1 | 0.0571 |
| dynamic-seat live | expm1 | 2024->26 | 5838 | +1.5975 | +2.5900 | +56.72% | +3.998 | 688.9 | 2025-04 -369.9 | 0.0677 |
| dynamic-seat live | expm1 | 2025->26 | 3642 | +2.4283 | +4.0136 | +87.90% | +5.386 | 688.9 | 2025-04 -369.9 | 0.0696 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024 | 2196 | +0.0790 | +0.1373 | +3.01% | +0.289 | 998.7 | 2024-04 -345.8 | 0.0875 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025 | 2190 | +0.2856 | +0.5495 | +12.03% | +0.897 | 408.2 | 2025-12 -265.2 | 0.1066 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026<=08-10 | 1332 | +2.4750 | +3.2017 | +70.12% | +4.812 | 355.3 | 2026-02 +49.1 | 0.0931 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026->08-30 | 1452 | +1.9838 | +2.5671 | +56.22% | +3.824 | 750.4 | 2026-08 -274.6 | 0.0926 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024->26 | 5838 | +0.6302 | +1.0444 | +22.87% | +1.727 | 998.7 | 2024-04 -345.8 | 0.0959 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025->26 | 3642 | +0.9626 | +1.5512 | +33.97% | +2.345 | 750.4 | 2026-08 -274.6 | 0.1010 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024 | 2196 | +0.1155 | +0.1979 | +4.33% | +0.426 | 966.6 | 2024-04 -374.9 | 0.0869 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025 | 2190 | +0.3391 | +0.6468 | +14.16% | +1.062 | 413.3 | 2025-12 -275.2 | 0.1057 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026<=08-10 | 1332 | +2.5427 | +3.2865 | +71.97% | +4.953 | 345.0 | 2026-02 +107.3 | 0.0927 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026->08-30 | 1452 | +2.0682 | +2.6745 | +58.57% | +3.999 | 737.3 | 2026-08 -260.8 | 0.0922 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024->26 | 5838 | +0.6850 | +1.1258 | +24.65% | +1.881 | 966.6 | 2024-04 -374.9 | 0.0953 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025->26 | 3642 | +1.0284 | +1.6494 | +36.12% | +2.507 | 737.3 | 2025-12 -275.2 | 0.1003 |
| canon | Σ-simple | 2024 | 2196 | +0.2549 | +0.4103 | +8.99% | +0.860 | 719.4 | 2024-04 -380.3 | 0.0807 |
| canon | Σ-simple | 2025 | 2190 | +0.4363 | +0.7360 | +16.12% | +1.247 | 502.9 | 2025-12 -367.1 | 0.0944 |
| canon | Σ-simple | 2026<=08-10 | 1332 | +2.3734 | +2.7602 | +60.45% | +4.614 | 394.8 | 2026-02 +34.4 | 0.0751 |
| canon | Σ-simple | 2026->08-30 | 1452 | +1.8929 | +2.1890 | +47.94% | +3.638 | 726.6 | 2026-08 -279.9 | 0.0746 |
| canon | Σ-simple | 2024->26 | 5838 | +0.7304 | +1.0883 | +23.83% | +1.908 | 726.6 | 2024-04 -380.3 | 0.0843 |
| canon | Σ-simple | 2025->26 | 3642 | +1.0170 | +1.4504 | +31.76% | +2.386 | 726.6 | 2025-12 -367.1 | 0.0865 |
| canon | expm1 | 2024 | 2196 | +0.3217 | +0.4966 | +10.88% | +1.061 | 694.4 | 2024-07 -372.4 | 0.0621 |
| canon | expm1 | 2025 | 2190 | +0.8433 | +1.3914 | +30.47% | +2.413 | 670.5 | 2025-04 -403.6 | 0.0668 |
| canon | expm1 | 2026<=08-10 | 1332 | +3.6291 | +4.9399 | +108.18% | +7.144 | 258.1 | 2026-01 +161.2 | 0.0431 |
| canon | expm1 | 2026->08-30 | 1452 | +3.1319 | +4.2331 | +92.71% | +6.105 | 681.6 | 2026-08 +9.6 | 0.0438 |
| canon | expm1 | 2024->26 | 5838 | +1.2163 | +1.8568 | +40.66% | +3.179 | 694.4 | 2025-04 -403.6 | 0.0593 |
| canon | expm1 | 2025->26 | 3642 | +1.7557 | +2.6626 | +58.31% | +4.152 | 681.6 | 2025-04 -403.6 | 0.0576 |
| EXTRA canon fixed-seat | Σ-simple | 2024 | 2196 | -0.5741 | -0.6630 | -14.52% | -1.430 | 1834.6 | 2024-12 -635.0 | 0.0317 |
| EXTRA canon fixed-seat | Σ-simple | 2025 | 2190 | +0.2177 | +0.2626 | +5.75% | +0.505 | 1040.1 | 2025-01 -616.0 | 0.0302 |
| EXTRA canon fixed-seat | Σ-simple | 2026<=08-10 | 1332 | +2.6491 | +3.1304 | +68.56% | +4.928 | 393.6 | 2026-02 +74.8 | 0.0534 |
| EXTRA canon fixed-seat | Σ-simple | 2026->08-30 | 1452 | +2.1584 | +2.5364 | +55.55% | +3.983 | 708.8 | 2026-08 -244.8 | 0.0541 |
| EXTRA canon fixed-seat | Σ-simple | 2024->26 | 5838 | +0.4025 | +0.4745 | +10.39% | +0.891 | 2742.5 | 2024-12 -635.0 | 0.0367 |
| EXTRA canon fixed-seat | Σ-simple | 2025->26 | 3642 | +0.9914 | +1.1834 | +25.92% | +2.071 | 1040.1 | 2025-01 -616.0 | 0.0397 |

### 4b. Arm S0 (no stop layer)

| form | caliber | period | n | net_ex | A per-gross | A %/yr gross | Sharpe | DD NAV bps | worst month | cost_ex |
|---|---|---|---|---|---|---|---|---|---|---|
| fixed-seat live | Σ-simple | 2024 | 2196 | -0.6741 | -0.7640 | -16.73% | -1.604 | 1949.8 | 2024-11 -737.6 | 0.0325 |
| fixed-seat live | Σ-simple | 2025 | 2190 | +0.1542 | +0.1937 | +4.24% | +0.315 | 1192.4 | 2025-01 -826.2 | 0.0407 |
| fixed-seat live | Σ-simple | 2026<=08-10 | 1332 | +2.9627 | +3.6756 | +80.50% | +5.034 | 497.9 | 2026-01 +147.2 | 0.0671 |
| fixed-seat live | Σ-simple | 2026->08-30 | 1452 | +2.4408 | +3.0247 | +66.24% | +4.106 | 778.9 | 2026-08 -224.3 | 0.0680 |
| fixed-seat live | Σ-simple | 2024->26 | 5838 | +0.4114 | +0.4949 | +10.84% | +0.831 | 3012.2 | 2025-01 -826.2 | 0.0444 |
| fixed-seat live | Σ-simple | 2025->26 | 3642 | +1.0658 | +1.3317 | +29.16% | +1.995 | 1192.4 | 2025-01 -826.2 | 0.0516 |
| fixed-seat live | expm1 | 2024 | 2196 | -0.3977 | -0.4508 | -9.87% | -0.934 | 1714.2 | 2024-11 -659.4 | 0.0325 |
| fixed-seat live | expm1 | 2025 | 2190 | +1.3147 | +1.6516 | +36.17% | +2.559 | 895.3 | 2025-01 -593.4 | 0.0407 |
| fixed-seat live | expm1 | 2026<=08-10 | 1332 | +4.8064 | +5.9630 | +130.59% | +7.986 | 307.3 | 2026-01 +249.4 | 0.0671 |
| fixed-seat live | expm1 | 2026->08-30 | 1452 | +4.2592 | +5.2780 | +115.59% | +7.027 | 707.2 | 2026-08 +125.1 | 0.0680 |
| fixed-seat live | expm1 | 2024->26 | 5838 | +1.4029 | +1.6878 | +36.96% | +2.751 | 2478.1 | 2024-11 -659.4 | 0.0444 |
| fixed-seat live | expm1 | 2025->26 | 3642 | +2.4886 | +3.1093 | +68.09% | +4.499 | 895.3 | 2025-01 -593.4 | 0.0516 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024 | 2196 | -0.7513 | -0.8516 | -18.65% | -1.776 | 2095.3 | 2024-11 -779.1 | 0.0325 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025 | 2190 | +0.0860 | +0.1080 | +2.36% | +0.171 | 1133.1 | 2025-01 -774.1 | 0.0407 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026<=08-10 | 1332 | +2.8861 | +3.5806 | +78.42% | +4.868 | 399.0 | 2026-01 +93.9 | 0.0671 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026->08-30 | 1452 | +2.3508 | +2.9131 | +63.80% | +3.928 | 789.9 | 2026-08 -251.5 | 0.0680 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024->26 | 5838 | +0.3343 | +0.4022 | +8.81% | +0.666 | 3099.6 | 2024-11 -779.1 | 0.0444 |
| fixed-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025->26 | 3642 | +0.9889 | +1.2355 | +27.06% | +1.819 | 1133.1 | 2025-01 -774.1 | 0.0516 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024 | 2196 | -0.7500 | -0.8501 | -18.62% | -1.782 | 2079.3 | 2024-11 -784.8 | 0.0325 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025 | 2190 | +0.1175 | +0.1476 | +3.23% | +0.233 | 1132.9 | 2025-01 -777.5 | 0.0407 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026<=08-10 | 1332 | +2.8810 | +3.5743 | +78.28% | +4.869 | 401.7 | 2026-01 +102.6 | 0.0671 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026->08-30 | 1452 | +2.3662 | +2.9322 | +64.22% | +3.969 | 773.6 | 2026-08 -235.6 | 0.0680 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024->26 | 5838 | +0.3505 | +0.4216 | +9.23% | +0.700 | 3081.7 | 2024-11 -784.8 | 0.0444 |
| fixed-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025->26 | 3642 | +1.0140 | +1.2669 | +27.75% | +1.868 | 1132.9 | 2025-01 -777.5 | 0.0516 |
| dynamic-seat live | Σ-simple | 2024 | 2196 | +0.1488 | +0.2404 | +5.26% | +0.498 | 895.6 | 2024-04 -360.5 | 0.0826 |
| dynamic-seat live | Σ-simple | 2025 | 2190 | +0.4099 | +0.7490 | +16.40% | +1.199 | 565.7 | 2025-12 -337.2 | 0.1041 |
| dynamic-seat live | Σ-simple | 2026<=08-10 | 1332 | +2.6002 | +3.2025 | +70.13% | +4.762 | 490.4 | 2026-02 +109.6 | 0.0901 |
| dynamic-seat live | Σ-simple | 2026->08-30 | 1452 | +2.1082 | +2.5953 | +56.84% | +3.799 | 766.3 | 2026-08 -257.8 | 0.0896 |
| dynamic-seat live | Σ-simple | 2024->26 | 5838 | +0.7341 | +1.1467 | +25.11% | +1.869 | 895.6 | 2024-04 -360.5 | 0.0924 |
| dynamic-seat live | Σ-simple | 2025->26 | 3642 | +1.0870 | +1.6648 | +36.46% | +2.472 | 766.3 | 2025-12 -337.2 | 0.0983 |
| dynamic-seat live | expm1 | 2024 | 2196 | +0.2950 | +0.4478 | +9.81% | +0.944 | 556.7 | 2024-07 -383.3 | 0.0644 |
| dynamic-seat live | expm1 | 2025 | 2190 | +1.2163 | +2.1429 | +46.93% | +3.151 | 703.0 | 2025-04 -340.8 | 0.0782 |
| dynamic-seat live | expm1 | 2026<=08-10 | 1332 | +4.6469 | +6.4513 | +141.28% | +8.115 | 296.7 | 2026-01 +267.8 | 0.0553 |
| dynamic-seat live | expm1 | 2026->08-30 | 1452 | +4.0984 | +5.6698 | +124.17% | +7.101 | 720.2 | 2026-08 +138.6 | 0.0563 |
| dynamic-seat live | expm1 | 2024->26 | 5838 | +1.5866 | +2.4772 | +54.25% | +3.777 | 720.2 | 2024-07 -383.3 | 0.0676 |
| dynamic-seat live | expm1 | 2025->26 | 3642 | +2.3654 | +3.7575 | +82.29% | +5.006 | 720.2 | 2025-04 -340.8 | 0.0695 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024 | 2196 | +0.0829 | +0.1405 | +3.08% | +0.284 | 1080.8 | 2024-04 -334.8 | 0.0879 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025 | 2190 | +0.3306 | +0.6170 | +13.51% | +0.950 | 622.5 | 2025-12 -345.4 | 0.1071 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026<=08-10 | 1332 | +2.4796 | +3.0736 | +67.31% | +4.563 | 394.8 | 2026-01 +79.7 | 0.0932 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2026->08-30 | 1452 | +1.9775 | +2.4489 | +53.63% | +3.581 | 773.6 | 2026-08 -294.9 | 0.0925 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2024->26 | 5838 | +0.6470 | +1.0371 | +22.71% | +1.651 | 1080.8 | 2025-12 -345.4 | 0.0963 |
| dynamic-seat live | compounded same window Π(1+r5[E..E+47])−1 | 2025->26 | 3642 | +0.9872 | +1.5326 | +33.56% | +2.238 | 861.1 | 2025-12 -345.4 | 0.1013 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024 | 2196 | +0.1213 | +0.2024 | +4.43% | +0.420 | 1056.7 | 2024-04 -352.2 | 0.0872 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025 | 2190 | +0.3972 | +0.7337 | +16.07% | +1.129 | 606.5 | 2025-12 -350.6 | 0.1062 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026<=08-10 | 1332 | +2.5078 | +3.1050 | +68.00% | +4.619 | 397.9 | 2026-01 +92.3 | 0.0927 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2026->08-30 | 1452 | +2.0210 | +2.4999 | +54.75% | +3.670 | 757.7 | 2026-08 -277.8 | 0.0921 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2024->26 | 5838 | +0.6973 | +1.1076 | +24.26% | +1.780 | 1056.7 | 2024-04 -352.2 | 0.0955 |
| dynamic-seat live | compounded exchange window Π(1+r5[E+1..E+48])−1 | 2025->26 | 3642 | +1.0446 | +1.6125 | +35.31% | +2.362 | 844.6 | 2025-12 -350.6 | 0.1006 |
| canon | Σ-simple | 2024 | 2196 | +0.1782 | +0.2793 | +6.12% | +0.562 | 885.9 | 2024-04 -376.1 | 0.0808 |
| canon | Σ-simple | 2025 | 2190 | +0.4685 | +0.7665 | +16.79% | +1.242 | 526.2 | 2025-12 -306.3 | 0.0947 |
| canon | Σ-simple | 2026<=08-10 | 1332 | +2.5398 | +2.8197 | +61.75% | +4.495 | 402.3 | 2026-01 +40.9 | 0.0745 |
| canon | Σ-simple | 2026->08-30 | 1452 | +2.0028 | +2.2082 | +48.36% | +3.485 | 806.4 | 2026-08 -384.3 | 0.0739 |
| canon | Σ-simple | 2024->26 | 5838 | +0.7409 | +1.0662 | +23.35% | +1.778 | 885.9 | 2026-08 -384.3 | 0.0843 |
| canon | Σ-simple | 2025->26 | 3642 | +1.0802 | +1.4815 | +32.45% | +2.316 | 806.4 | 2026-08 -384.3 | 0.0864 |
| canon | expm1 | 2024 | 2196 | +0.3223 | +0.4793 | +10.50% | +0.975 | 708.9 | 2024-07 -435.4 | 0.0620 |
| canon | expm1 | 2025 | 2190 | +0.7759 | +1.2295 | +26.93% | +2.087 | 728.2 | 2025-04 -399.3 | 0.0669 |
| canon | expm1 | 2026<=08-10 | 1332 | +3.4411 | +4.3831 | +95.99% | +6.313 | 346.7 | 2026-01 +47.0 | 0.0420 |
| canon | expm1 | 2026->08-30 | 1452 | +2.9485 | +3.7315 | +81.72% | +5.343 | 730.0 | 2026-08 +16.2 | 0.0425 |
| canon | expm1 | 2024->26 | 5838 | +1.1457 | +1.6695 | +36.56% | +2.786 | 730.0 | 2024-07 -435.4 | 0.0590 |
| canon | expm1 | 2025->26 | 3642 | +1.6421 | +2.3644 | +51.78% | +3.627 | 730.0 | 2025-04 -399.3 | 0.0572 |
| EXTRA canon fixed-seat | Σ-simple | 2024 | 2196 | -0.6007 | -0.6647 | -14.56% | -1.357 | 1881.4 | 2024-12 -710.0 | 0.0303 |
| EXTRA canon fixed-seat | Σ-simple | 2025 | 2190 | +0.1022 | +0.1163 | +2.55% | +0.203 | 1217.9 | 2025-01 -789.5 | 0.0285 |
| EXTRA canon fixed-seat | Σ-simple | 2026<=08-10 | 1332 | +2.8654 | +3.1959 | +69.99% | +4.897 | 396.1 | 2026-01 +62.7 | 0.0521 |
| EXTRA canon fixed-seat | Σ-simple | 2026->08-30 | 1452 | +2.3110 | +2.5607 | +56.08% | +3.894 | 799.6 | 2026-08 -315.7 | 0.0526 |
| EXTRA canon fixed-seat | Σ-simple | 2024->26 | 5838 | +0.3872 | +0.4330 | +9.48% | +0.763 | 2942.0 | 2025-01 -789.5 | 0.0352 |
| EXTRA canon fixed-seat | Σ-simple | 2025->26 | 3642 | +0.9828 | +1.1062 | +24.23% | +1.813 | 1217.9 | 2025-01 -789.5 | 0.0381 |

## 5. Caliber-only effect on an identical book (VERIFIED, out:623-645)

For the fixed-seat live form, arm S0, the book path cannot depend on y4 values (no stop layer, fixed seats). The script asserts `S0_W` is bitwise equal across the four calibers (`array_equal=True`, `max|ΔW|=0`, and the turnover / gross_total / cost_ex / carry_ex columns are equal), so these deltas are pure accounting:

```
  [expm1] S0_W array_equal vs Σ-simple: True  max|ΔW|=0.000e+00; turnover col equal: True; gross_total col equal: True; cost_ex col equal: True; carry_ex col equal: True
      2024         n=2196 Δnet_ex(this − Σ-simple) mean +0.2763 bps/anchor NAV (= Δpnl_ex mean +0.2763); per-gross A +0.3132 => +6.86%/yr gross; Sharpe -0.934 vs -1.604
      2025         n=2190 Δnet_ex(this − Σ-simple) mean +1.1605 bps/anchor NAV (= Δpnl_ex mean +1.1605); per-gross A +1.4579 => +31.93%/yr gross; Sharpe +2.559 vs +0.315
      2026<=08-10  n=1332 Δnet_ex(this − Σ-simple) mean +1.8437 bps/anchor NAV (= Δpnl_ex mean +1.8437); per-gross A +2.2874 => +50.09%/yr gross; Sharpe +7.986 vs +5.034
      2026->08-30  n=1452 Δnet_ex(this − Σ-simple) mean +1.8184 bps/anchor NAV (= Δpnl_ex mean +1.8184); per-gross A +2.2533 => +49.35%/yr gross; Sharpe +7.027 vs +4.106
      2024->26     n=5838 Δnet_ex(this − Σ-simple) mean +0.9915 bps/anchor NAV (= Δpnl_ex mean +0.9915); per-gross A +1.1929 => +26.12%/yr gross; Sharpe +2.751 vs +0.831
      2025->26     n=3642 Δnet_ex(this − Σ-simple) mean +1.4228 bps/anchor NAV (= Δpnl_ex mean +1.4228); per-gross A +1.7776 => +38.93%/yr gross; Sharpe +4.499 vs +1.995
  [compounded same window Π(1+r5[E..E+47])−1] S0_W array_equal vs Σ-simple: True  max|ΔW|=0.000e+00; turnover col equal: True; gross_total col equal: True; cost_ex col equal: True; carry_ex col equal: True
      2024         n=2196 Δnet_ex(this − Σ-simple) mean -0.0773 bps/anchor NAV (= Δpnl_ex mean -0.0773); per-gross A -0.0876 => -1.92%/yr gross; Sharpe -1.776 vs -1.604
      2025         n=2190 Δnet_ex(this − Σ-simple) mean -0.0682 bps/anchor NAV (= Δpnl_ex mean -0.0682); per-gross A -0.0857 => -1.88%/yr gross; Sharpe +0.171 vs +0.315
      2026<=08-10  n=1332 Δnet_ex(this − Σ-simple) mean -0.0766 bps/anchor NAV (= Δpnl_ex mean -0.0766); per-gross A -0.0950 => -2.08%/yr gross; Sharpe +4.868 vs +5.034
      2026->08-30  n=1452 Δnet_ex(this − Σ-simple) mean -0.0901 bps/anchor NAV (= Δpnl_ex mean -0.0901); per-gross A -0.1116 => -2.44%/yr gross; Sharpe +3.928 vs +4.106
      2024->26     n=5838 Δnet_ex(this − Σ-simple) mean -0.0771 bps/anchor NAV (= Δpnl_ex mean -0.0771); per-gross A -0.0927 => -2.03%/yr gross; Sharpe +0.666 vs +0.831
      2025->26     n=3642 Δnet_ex(this − Σ-simple) mean -0.0769 bps/anchor NAV (= Δpnl_ex mean -0.0769); per-gross A -0.0961 => -2.11%/yr gross; Sharpe +1.819 vs +1.995
  [compounded exchange window Π(1+r5[E+1..E+48])−1] S0_W array_equal vs Σ-simple: True  max|ΔW|=0.000e+00; turnover col equal: True; gross_total col equal: True; cost_ex col equal: True; carry_ex col equal: True
      2024         n=2196 Δnet_ex(this − Σ-simple) mean -0.0760 bps/anchor NAV (= Δpnl_ex mean -0.0760); per-gross A -0.0861 => -1.89%/yr gross; Sharpe -1.782 vs -1.604
      2025         n=2190 Δnet_ex(this − Σ-simple) mean -0.0367 bps/anchor NAV (= Δpnl_ex mean -0.0367); per-gross A -0.0461 => -1.01%/yr gross; Sharpe +0.233 vs +0.315
      2026<=08-10  n=1332 Δnet_ex(this − Σ-simple) mean -0.0817 bps/anchor NAV (= Δpnl_ex mean -0.0817); per-gross A -0.1013 => -2.22%/yr gross; Sharpe +4.869 vs +5.034
      2026->08-30  n=1452 Δnet_ex(this − Σ-simple) mean -0.0746 bps/anchor NAV (= Δpnl_ex mean -0.0746); per-gross A -0.0925 => -2.02%/yr gross; Sharpe +3.969 vs +4.106
      2024->26     n=5838 Δnet_ex(this − Σ-simple) mean -0.0609 bps/anchor NAV (= Δpnl_ex mean -0.0609); per-gross A -0.0733 => -1.60%/yr gross; Sharpe +0.700 vs +0.831
      2025->26     n=3642 Δnet_ex(this − Σ-simple) mean -0.0518 bps/anchor NAV (= Δpnl_ex mean -0.0518); per-gross A -0.0647 => -1.42%/yr gross; Sharpe +1.868 vs +1.995
```

Reading: on the same trades, **expm1-on-Σ-simple adds +0.9915 bps/anchor (2024→26), +1.1605 in 2025 and +1.8437 in 2026≤08-10**, i.e. +26.12% to +50.09% per year of gross, and lifts the 2024→26 Sharpe from +0.831 to +2.751. That is the E-0904-F artefact at book level. A true compounded target (either window) moves the same book by **−0.0367 to −0.0901 bps/anchor** (−1.01% to −2.44% per year of gross): Σ-simple slightly overstates a Π(1+r) hold, in the opposite direction and an order of magnitude smaller than the expm1 artefact. Panel-level receipt: `mean(expm1(y4) − y4) = +3.4552 bps` per name-cell vs `mean(y4) = +0.1140 bps` (out:620).

## 6. Previously quoted numbers — column and arm (VERIFIED, out:576-599)

```
Recomputed from the npz rec arrays over 2024->26 (all anchors with year>=2024), mean and mean/std(ddof=1)*sqrt(2190):
  canon              S0          | 'net' (file caliber) col: CAL=simple +1.1108 S 2.594  vs CAL=log +0.7821 S 1.926  | 'net_ex' col: CAL=simple +1.1457 S 2.786  vs CAL=log +0.7409 S 1.778
  canon              d30_n2_c42  | 'net' (file caliber) col: CAL=simple +1.1402 S 2.699  vs CAL=log +0.7546 S 1.929  | 'net_ex' col: CAL=simple +1.2163 S 3.179  vs CAL=log +0.7304 S 1.908
  dynamic-seat live  S0          | 'net' (file caliber) col: CAL=simple +1.4936 S 3.225  vs CAL=log +0.7865 S 1.845  | 'net_ex' col: CAL=simple +1.5866 S 3.777  vs CAL=log +0.7341 S 1.869
  dynamic-seat live  d30_n2_c42  | 'net' (file caliber) col: CAL=simple +1.4541 S 3.134  vs CAL=log +0.7158 S 1.690  | 'net_ex' col: CAL=simple +1.5975 S 3.998  vs CAL=log +0.6914 S 1.884
  fixed-seat live    S0          | 'net' (file caliber) col: CAL=simple +1.3256 S 2.487  vs CAL=log +0.5279 S 1.017  | 'net_ex' col: CAL=simple +1.4029 S 2.751  vs CAL=log +0.4114 S 0.831
  fixed-seat live    d30_n2_c42  | 'net' (file caliber) col: CAL=simple +1.2976 S 2.403  vs CAL=log +0.4969 S 0.930  | 'net_ex' col: CAL=simple +1.4731 S 3.139  vs CAL=log +0.4566 S 1.017
Summary-JSON fields (device L336: net_2024on/sharpe_2024on are computed on column 1 = 'net'; L345-347: net_ex_2024on/sharpe_ex_2024on on column 18 = 'net_ex'):
  pod_canon_calsimple_s42        S0          net_2024on=1.1108 sharpe_2024on=2.594 | net_ex_2024on=1.1457 sharpe_ex_2024on=2.786
  pod_canon_calsimple_s42        d30_n2_c42  net_2024on=1.1402 sharpe_2024on=2.699 | net_ex_2024on=1.2163 sharpe_ex_2024on=3.179
  pod_canon_callog_s42           S0          net_2024on=0.7821 sharpe_2024on=1.926 | net_ex_2024on=0.7409 sharpe_ex_2024on=1.778
  pod_canon_callog_s42           d30_n2_c42  net_2024on=0.7546 sharpe_2024on=1.929 | net_ex_2024on=0.7304 sharpe_ex_2024on=1.908
  pod_live_calsimple_s42         S0          net_2024on=1.4936 sharpe_2024on=3.225 | net_ex_2024on=1.5866 sharpe_ex_2024on=3.777
  pod_live_calsimple_s42         d30_n2_c42  net_2024on=1.4541 sharpe_2024on=3.134 | net_ex_2024on=1.5975 sharpe_ex_2024on=3.998
  pod_live_callog_s42            S0          net_2024on=0.7865 sharpe_2024on=1.845 | net_ex_2024on=0.7341 sharpe_ex_2024on=1.869
  pod_live_callog_s42            d30_n2_c42  net_2024on=0.7158 sharpe_2024on=1.690 | net_ex_2024on=0.6914 sharpe_ex_2024on=1.884
  pod_live_w3fix_calsimple_s42   S0          net_2024on=1.3256 sharpe_2024on=2.487 | net_ex_2024on=1.4029 sharpe_ex_2024on=2.751
  pod_live_w3fix_calsimple_s42   d30_n2_c42  net_2024on=1.2976 sharpe_2024on=2.403 | net_ex_2024on=1.4731 sharpe_ex_2024on=3.139
  pod_live_w3fix_callog_s42      S0          net_2024on=0.5279 sharpe_2024on=1.017 | net_ex_2024on=0.4114 sharpe_ex_2024on=0.831
  pod_live_w3fix_callog_s42      d30_n2_c42  net_2024on=0.4969 sharpe_2024on=0.930 | net_ex_2024on=0.4566 sharpe_ex_2024on=1.017
  canon: quoted pair matches S0 'net' (CAL=simple 1.1108/2.594 vs CAL=log 0.7821/1.926). Same comparison on d30 'net_ex': 1.2163/3.179 vs 0.7304/1.908. Δ(S0 net − d30 net_ex): CAL=simple -0.1055 bps (S -0.585); CAL=log +0.0517 bps (S +0.018)
  live dyn: quoted pair matches S0 'net' (CAL=simple 1.4936/3.225 vs CAL=log 0.7865/1.845). Same comparison on d30 'net_ex': 1.5975/3.998 vs 0.6914/1.884. Δ(S0 net − d30 net_ex): CAL=simple -0.1039 bps (S -0.773); CAL=log +0.0951 bps (S -0.039)
```

Attribution: **"canon net_2024on 1.11 vs 0.78 (Sharpe 2.59 vs 1.93); live 1.49 vs 0.79 (3.23 vs 1.85)" are the `S0` arm, `net` (file-caliber, blended-book) column, `2024->26` window, CAL=simple vs CAL=log**, read from `w10_ablation_summary_*.json["S0"]["net_2024on"/"sharpe_2024on"]` (device L335-336 computes those on column 1 = `net`). They are not the deployed arm and not the executor caliber. The same comparison on the deployed arm and executor column (`d30_n2_c42`, `net_ex`) is canon 1.2163/3.179 vs 0.7304/1.908 and live-dyn 1.5975/3.998 vs 0.6914/1.884. The exact S0-net minus d30-net_ex gaps are printed: canon −0.1055 bps (CAL=simple) / +0.0517 (CAL=log); live-dyn −0.1039 / +0.0951.

## 7. Caveats

- All numbers are replay (`w10_universe.py` port on pod2), Σ-simple / expm1 / Π targets on the same 5-minute cache; not fills. Execution-time decay and real fills are outside this script.
- "2× gross" follows the task's convention; the in-service book is 1.5×NAV gross.
- Canon × compounded target does not exist as an artefact; producing it would be a new run (not done: read-only task).
- The two independently built Π-exchange-window runs (C6_1 `true_new`, C6_2 `newprod`) differ at 1e-8 bps (float ordering), so either may be cited; this report uses C6_2 `newprod` and C6_1 `true_old`.
