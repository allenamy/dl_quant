# REPORT — Axis B: seat-rule variants R1..R5 vs the production msharpe-900 seat (R0), strict-causal L-dyn replay, both calibers, both F10 seeds, K1 rolling king (primary) and K0 pinned king (secondary)

> **创建:** 2026-09-04 23:2xZ – 2026-09-05 00:3xZ UTC | **Session:** b9646a9e, teammate `seat-rule-axis` | **状态:** complete; decisions under the frozen criteria of PREREG §2 incl. AMENDMENT 1 | **作废条件:** PREREG §0 — device default path not bitwise-equivalent to the pod port baseline (checked: PASS, §1.3), or any arm added/removed after numbers (none: 6 rules × 2 kings × 2 calibers × 2 seeds = 48 artifacts, all present, one CMD/END pair each); also voided by a change of the king sources (pinned sha256 `158cd4ac…`, rollm `999f7d4d…`) or of the caliber metas (`wide_fea_v2ext_meta.npz`; `meta_newprod.npz` `831857dd…`).
> Prereg: `docs/PREREG_retrain_cadence_and_seat_rule_2026-09-05.md` sha256 `afeb1dd9991d10643bde9f8c37d9dbae9fb0a321db344a545edfc2c58659909a` (commit `39319c0` = AMENDMENT 1, R4 mask-first, written before any R4 number existed). Labels: **VERIFIED** = printed by a script and quoted with its command; **INFERRED** = derived from verified facts with the reasoning stated; **UNRESOLVED** = not established here. **[单仪器 pod]** — every number comes from the pod port device only; jpline was down for the whole run.
> READ-ONLY on `/workspace/data`, `/workspace/shadow_bundle_v3`, `/workspace/port_w10`, `/workspace/review_scratch/{refute_*,combo_recheck,rolling_king}`. Writes only under `/workspace/review_scratch/cadence_seats/axisB/` (pod) and `…/scratchpad/review_caliber/cadence_seats/axisB/` (Mac). No GPU.

## 0. Answer and decisions

**Question:** does any of the five pre-registered seat rules beat the production msharpe seat (window 900) at the book level, with the seat inputs strictly causal (rows only before anchor t), under both return calibers and both F10 seeds?

**Answer: no rule clears the frozen gate. All five are UNDECIDED under K1 rollm (primary) and again under K0 pinned (secondary): no rule has CI95 lower > 0 in all four caliber × seed cells of the primary window 2025→26, and no rule has CI95 upper < 0 in any cell of that window.** Paired Δ = R_k − R0 in net_ex bps/anchor per unit NAV (arm d30_n2_c42, n = 3642 anchors 2025→26, UTC-day-block bootstrap 2000×), K1 rollm, cells log/s42 · log/s2027 · prod/s42 · prod/s2027 (VERIFIED, `judge.log`):

| rule | Δ 2025→26 [CI95] per cell | Δturnover 2025→26 | mean king seat 2025→26 (R0 0.557 log / 0.567 prod) | verdict |
|---|---|---|---|---|
| R1 msharpe LOOK 300 | −0.018 [−0.316,+0.284] · −0.027 [−0.305,+0.264] · +0.019 [−0.273,+0.315] · +0.001 [−0.295,+0.324] | −8 to −9% | 0.461 / 0.467 | UNDECIDED |
| R2 net-turnover msharpe 900 (κ 3.52) | +0.134 [−0.099,+0.369] · +0.111 [−0.120,+0.342] · +0.149 [−0.116,+0.416] · +0.126 [−0.122,+0.393] | −31 to −34% | 0.343 / 0.329 | UNDECIDED |
| R3 shrink 0.5 to [0.5,0,0.5] | −0.120 [−0.274,+0.046] · −0.132 [−0.291,+0.029] · −0.087 [−0.247,+0.071] · −0.106 [−0.256,+0.052] | +4 to +5.5% | 0.529 / 0.534 | UNDECIDED (negative in 8/8 cells incl. K0; see §3) |
| R4 mean-variance 2-leg (AMENDMENT 1) | +0.047 [−0.007,+0.101] · +0.013 [−0.042,+0.065] · +0.021 [−0.029,+0.069] · +0.009 [−0.047,+0.068] | −3 to −5% | 0.531 / 0.549 | UNDECIDED (≈ R0) |
| R5 σ_fund-tercile regime msharpe | +0.101 [−0.051,+0.261] · +0.101 [−0.056,+0.265] · +0.128 [−0.036,+0.312] · +0.143 [−0.024,+0.318] | −0.2 to −1.8% | 0.553 / 0.563 | UNDECIDED |

K0 pinned (secondary, not for selection) gives the same picture: R1 +0.05 to +0.09 (CIs ±0.3), R2 +0.157 to +0.187 (P 0.89–0.93), R3 −0.094 to −0.145 (P 0.04–0.14), R4 −0.033 to +0.047, R5 +0.091 to +0.139 (P 0.87–0.95); all UNDECIDED.

**Recommendation (INFERRED from the tables; not a criterion): keep R0.** The only two rules with a consistent positive sign across all eight king × caliber × seed cells are R2 (P(Δ>0) 0.81–0.93) and R5 (0.87–0.95), and each has a reason not to be trusted beyond "not refuted": R2 is in effect a fixed tilt toward the fund leg (its deduction removes 74% of the king leg raw return, §3.2) whose whole gain sits in the high-σ_fund tercile with low/mid ≤ 0; R5 draws about half of its 2025→26 gain from 256 anchors (7% of the window) where it jumps to ≈100% king on a window that is on average 2161 anchors old (§3.5) — single-episode memory, not regime conditioning. R3 is the closest to a rejection (2024→26 CI95 upper < 0 in 5 of 8 cells, mid-σ tercile CI95 upper < 0 in 8/8) and R4 is numerically R0. The frozen test has a resolution of roughly ±0.15–0.3 bps/anchor on 2025→26; effects of the observed size (≈0.1 bps/anchor, which the scripted chain in §3.0 puts at ≈2.2 %/yr per unit NAV at the replay gross and ≈7 %/yr of NAV at the live 2× — economically material, statistically unresolved) are below it, so UNDECIDED is the expected verdict for any rule whose true effect is that small; a first hand-written version of this sentence said 0.2 %/yr and was corrected by the script (E-0904-G discipline).

## 1. Device (what was run)

### 1.1 `w10_universe_seats.py` = `rolling_king/w10_universe_recheck.py` + seat-rule branches
- Base: `/workspace/review_scratch/rolling_king/w10_universe_recheck.py` sha256 `5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9` (= port `/workspace/port_w10/w10_universe.py` `64c70a44…` + REF_SKIP guard, per the rolling_king REPORT §1.2). My device `w10_universe_seats.py` sha256 `944fa277c074059e7629b9cc2bddc911117b899ab7576212b4e480b7c5c7cfc1` (pod and Mac identical; the device writes its own sha into every artifact `config_json["AXISB"]["device_sha256"]`, and the judge asserts it is the same across all 48 artifacts).
- Full diff (`device.diff` sha256 `6f31b80930b342ca8ab54c01bb7893dda616978066beb23a585d00f95fb34959`, 154 lines) is quoted in §7. What it changes and what it does not:
  - **Unchanged**: every line of the `msharpe`, `eq`, `iv` and `W3FIX` seat paths, the warm-up (`p < LOOK → [1/3,1/3,1/3]`), the LOOK-window slice `sl = slice(p−LOOK, p)` (rows strictly before anchor t), the leg-return values of `legs()`, the book chain, the stop layer, the P&L / cost / carry accounting and the outputs. The new rules are reached only for the new `WRULE` values through `if WRULE in AXISB_RULES: return axisb_w3(LRa, p, sl, r)` placed after the `iv` branch.
  - **Added in `legs()`**: per leg (king / rev24 / fund) and anchor, `turn_j,t = Σ_names |z_j,t/g_j,t − z_j,t−1/g_j,t−1|` over the full 829-name vector (non-members = 0; `g ≤ 1e-9` ⇒ empty book), where `z/g` is exactly the unit-gross rank book used for that leg return in the same loop iteration (the leg return `_lr` is computed first and is untouched). Stored as `LRa["turn_<leg>"]`, saved as `axisb_turn` in every artifact.
  - **Added after `legs()`**: the σ_fund series over the legs() anchor sequence (R5 state) — per anchor `std(ddof=0)` over **META members** with finite `f_fund_now` of `f_fund_now·8/ivf·1e4` (bps/8h; `ivf = f_fund_iv` if finite and > 0 else 8; NaN if < 50 finite), trailing 30-anchor mean (≥ 15 valid). This is the rolling_king `judge.py` definition; the META members are captured before the `MEMBERS_TOPN=829` rebuild, so the definition does not depend on the arm universe. Receipt: on the 10,024 common finite anchors the device series equals the judge series to the bit (`max|diff| 0.000e+00, n(diff>1e-9) 0`, VERIFIED `judge.log`).
  - **Seat rules** (`axisb_w3`), all evaluated on the same window slice `sl` as msharpe, all returning the 3-vector (king, rev24, fund) that the existing code consumes unchanged:

| rule | env | implementation |
|---|---|---|
| R0 | `WRULE=msharpe LOOK=900` | untouched production path |
| R1 | `WRULE=msharpe LOOK=300` | untouched production path, shorter window (no code change) |
| R2 | `WRULE=msharpe_net LOOK=900` | `r_net = r − 3.52·turn` per leg over the window, then the byte-identical msharpe algebra (`shp = max(mean/std, 0)` → normalise → LEGS mask → renormalise) on `r_net` |
| R3 | `WRULE=shrink LOOK=900` | `w = 0.5·prior + 0.5·msharpe900(r)`, `prior = LEGS mask / Σmask` = [0.5, 0, 0.5] |
| R4 | `WRULE=meanvar LOOK=900` | AMENDMENT 1 (mask first): legs restricted to the LEGS-allowed ones (king, fund); `μ` = window mean, `Σ` = `np.cov` (ddof = 1) over the window, `ridge = 1e-3·trace(Σ)/2`, `w = clip(solve(Σ + ridge·I, μ), 0)`, all-zero ⇒ equal weight, normalised, placed back into the 3-vector (rev24 = 0). The literal 3-leg-then-mask ordering exists behind `MV_MASK_ORDER=after` and was **not run** |
| R5 | `WRULE=regime LOOK=900` | at anchor t (position p): cut points = 33.33 / 66.67 percentiles of the σ_fund series over positions `< p` (expanding, causal); tercile of every past anchor and of t by those cuts; seat = msharpe algebra over the most recent 900 positions `< p` in the tercile of t; fewer than 300 such positions (or < 300 finite history) ⇒ plain msharpe over the LOOK window. Per-anchor tercile and fallback flags are saved (`axisb_regime_tercile`, `axisb_regime_fallback`) |

  - Parameters are single asserted values: `KAPPA_TURN == 3.52`, `SHRINK_LAMBDA = 0.5`, `MV_RIDGE = 1e-3`, `REGIME_LOOK = 900`, `REGIME_MIN = 300`; `WRULE` and `MV_MASK_ORDER` are whitelist-asserted. All are self-reported in `config_json["AXISB"]` together with the σ_fund and turnover definitions, and the judge asserts every one of them on every artifact.

### 1.2 Layout, inputs, arms
- `axisB/dev/` and `axisB/dev_alt/` reproduce rolling_king layouts symlink for symlink; every resolved target was compared with rolling_king and is identical (`setup_dev.log`: 10/10 `SAME`). `dev/` meta → `/workspace/data/wide_fea_v2ext_meta.npz` (raw Σ-simple y4, caliber **log**); `dev_alt/` meta → `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz` (sha256 `831857dd6a2035235647158d26d0155d17c7e77d85fa248b2ae9a617658ddf13`, y4 = Π(1+r5)−1 over [E+1, E+48], caliber **prod**); E_ts / members / qvk of the two metas verified identical (printed `E_ts equal True`, `members equal True 10176`, `qvk equal True`).
- King sources: K1 = `/workspace/review_scratch/rolling_king/slow_pred_rollm.npy` (sha256 `999f7d4d8fa4de8e9eb46305d31af8a06b14419b07389f269a8d2fbad138be4a`; monthly refit, 60-anchor embargo, all 32 causal asserts True per the rolling_king REPORT §2.0); K0 = `/workspace/shadow_bundle_v3/slow_pred_pinned.npy` (sha256 `158cd4ac8f8f30f7f41a5a6cba0bd19a450ce756727e4aeae3d4e4b0b67d0054`; year folds). Both are NaN before 2024-01, so the king leg return is 0 and its rank book is empty (turnover 0) in 2022–23; the 2024 dynamic seat still carries that warm-up, which is why 2025→26 is the primary window (PREREG §0.4).
- Arms (L-dyn form; common env `LEGS=101 CAL=log MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero`, PHI default 0.45, F10 = `f10_V2MAIN_s{FSEED}.npy`, no W3FIX): 6 rules × {rollm, pinned} × {log, prod} × {42, 2027} = 48 runs (`run_axisB.sh <rule> <king> <cal> <seed>`; every command appended verbatim to `logs/commands.txt`, §6). Four were launched first as equivalence / smoke runs (R0 pinned log 42; R2, R4, R5 rollm log 42), the remaining 44 by a single flock-guarded queue (`run_all.sh`, 6 in parallel, 23:46:15Z–00:02:28Z). R0 was **re-run with this device** in all 8 (king, cal, seed) cells instead of reusing the rolling_king Ldyn artifacts, and each is checked bitwise against the corresponding rolling_king artifact (§1.3) — "reuse only if bitwise identical" holds by construction.
- Launch note: a guard `pgrep -f run_all.sh` matched the ssh shell own command line (pgrep pattern trap) and reported "already running" once; nothing had been launched, the queue was then started once under `flock -n logs/run_all.lock`, and the device process count was verified with a non-self-matching pattern (`ps -eo args | grep -c "[w]10_universe_seats.py"` → 0 before, 6 after). `logs/commands.txt` holds exactly 48 `CMD[...]` lines with 0 duplicate tags and 48 `END[...] rc=0` lines (VERIFIED).

### 1.3 Receipts (device equivalence, VERIFIED `logs/check_equiv.log`, `logs/judge.log`)
- **Required receipt**: `WRULE=msharpe LOOK=900`, pinned king, L-dyn s42, caliber log (`dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz`) vs `/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_live_callog_s42.npz`: `d30_n2_c42_rec array_equal True`, `S0_rec True`, `d30_n2_c42_W True`, `S0_W True`, `config_json equal (minus AXISB/REF_SKIP) True` — **PASS**. Same for s2027 vs `pod_live_callog_s2027` — PASS.
- **All 8 R0 cells** vs rolling_king `Ldyn_{king}_{cal}_{seed}` (pinned / rollm × log / prod × s42 / s2027): all four arrays `array_equal True`, config equal minus AXISB/REF_SKIP — **8/8 PASS**, `ALL_EQUIV True n 10`.
- Judge assertions: 48 artifacts loaded; one device sha256 across all (`944fa277…`); identical anchor set n = 10,038 (first 2022-01-31 00:00, last 2026-08-30 20:00) for every artifact; per-artifact config asserts (LEGS 101, CAL log, PHI 0.45, FSEED, SLOW_NPY, M829 / T400 / FTRIM zero / no W3FIX, rule-specific WRULE and LOOK, AXISB parameters incl. `mv_mask_order == first`).
- σ_fund receipt: device series (legs sequence, R5 state) vs the judge series (rec sequence): 10,024 common finite anchors, `max|diff| 0.000e+00`, `n(diff>1e-9) 0`.

### 1.4 Judge (`judge_axisB.py`, frozen; adapted from rolling_king `judge.py`)
- Arm `d30_n2_c42`, column `net_ex` (bps/anchor per unit NAV, executor caliber); anchors paired by ts. Windows: 2024 | 2025 | 2026≤08-10 (ts ≤ 2026-08-10 20:00Z, last finite F10 row) | 2026→08-30 | 2024→26 | **2025→26 (PRIMARY)**; ≤cut variants printed. Bootstrap: UTC-calendar-day blocks, 2000 resamples, seed 20260905, CI95 = 2.5 / 97.5 pct of resampled means, P = P(mean > 0). Sharpe = mean/std(ddof=1)·√2190; maxDD = max(cummax(cumsum) − cumsum) in bps; Δturnover% = (turn_k / turn_R0 − 1)·100 over 2025→26 (decision) and 2024→26 (printed).
- Seat trajectory definitions (frozen before any number, mine — the prereg names the quantities but not the formulas): yearly mean `w3_king`; **switches** = anchors where sign(w_king − 0.5) differs from the previous anchor; **jumps** = anchors with |Δw_king| ≥ 0.05; **seat_turn** = mean |Δw_king| per anchor. Note R3 has exactly the switch count of R0 by construction (w = 0.25 + 0.5·w0 keeps the sign of w − 0.5).
- σ_fund-tercile Δ: the rolling_king `judge.py` definition (descriptive terciles over the 2024→26 anchors: cuts 5.45 / 13.67 bps/8h, n 1946 per tercile). This partition differs from the causal expanding one used inside R5 (§3.5).
- Decision (PREREG §2): per rule, ADMIT-candidate iff for both calibers and both seeds CI95 lower > 0 on 2025→26 and Δturnover ≤ +15%; REJECT iff any caliber (either seed) CI95 upper < 0 on 2025→26; else UNDECIDED. Primary = K1 rollm; K0 pinned printed as SECONDARY. 2026≤08-10 is the auxiliary window (printed next to each decision cell).

## 2. Results (all numbers printed by `judge_axisB.py`; VERIFIED; tables rendered by the judge into `REPORT_tables.md`)

### Levels — arm d30_n2_c42, net_ex (bps/anchor per unit NAV); cell = mean S=Sharpe DD=maxDD(bps); gross / w_king / w_fund / turnover over 2025->26

#### caliber **log** = raw Σ-simple y4 (meta), CAL=log = no transform

| rule | king | seed | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | gross | w_king | w_fund | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | rollm | s42 | +0.094 S+0.33 DD925 | +0.344 S+1.11 DD472 | +2.603 S+4.88 DD479 | +2.104 S+3.91 DD801 | +0.688 S+1.85 DD925 | +1.046 S+2.51 DD801 | 0.630 | 0.557 | 0.443 | 0.03121 |
| R1 | rollm | s42 | +0.052 S+0.19 DD937 | +0.438 S+1.41 DD515 | +2.409 S+4.62 DD455 | +1.919 S+3.64 DD803 | +0.661 S+1.81 DD937 | +1.028 S+2.50 DD803 | 0.626 | 0.461 | 0.539 | 0.02866 |
| R2 | rollm | s42 | +0.147 S+0.51 DD614 | +0.505 S+1.44 DD665 | +2.753 S+4.99 DD445 | +2.196 S+3.96 DD835 | +0.791 S+2.01 DD835 | +1.179 S+2.65 DD835 | 0.650 | 0.343 | 0.657 | 0.02139 |
| R3 | rollm | s42 | -0.036 S-0.13 DD777 | +0.218 S+0.72 DD503 | +2.427 S+4.78 DD454 | +1.992 S+3.88 DD710 | +0.564 S+1.58 DD777 | +0.925 S+2.31 DD710 | 0.660 | 0.529 | 0.471 | 0.03279 |
| R4 | rollm | s42 | +0.125 S+0.46 DD862 | +0.348 S+1.10 DD478 | +2.726 S+5.02 DD479 | +2.215 S+4.05 DD789 | +0.728 S+1.95 DD862 | +1.092 S+2.58 DD789 | 0.642 | 0.531 | 0.469 | 0.02990 |
| R5 | rollm | s42 | +0.144 S+0.54 DD484 | +0.496 S+1.52 DD468 | +2.575 S+5.11 DD472 | +2.127 S+4.20 DD703 | +0.769 S+2.13 DD703 | +1.146 S+2.81 DD703 | 0.626 | 0.553 | 0.447 | 0.03089 |
| R0 | rollm | s2027 | +0.166 S+0.59 DD860 | +0.424 S+1.34 DD500 | +2.594 S+4.86 DD474 | +2.102 S+3.90 DD794 | +0.744 S+2.00 DD860 | +1.093 S+2.60 DD794 | 0.642 | 0.557 | 0.443 | 0.03013 |
| R1 | rollm | s2027 | +0.136 S+0.50 DD855 | +0.495 S+1.58 DD560 | +2.412 S+4.62 DD457 | +1.927 S+3.65 DD794 | +0.716 S+1.95 DD855 | +1.066 S+2.58 DD794 | 0.634 | 0.461 | 0.539 | 0.02781 |
| R2 | rollm | s2027 | +0.187 S+0.64 DD621 | +0.558 S+1.56 DD561 | +2.733 S+4.95 DD444 | +2.178 S+3.93 DD833 | +0.821 S+2.08 DD833 | +1.204 S+2.70 DD833 | 0.657 | 0.343 | 0.657 | 0.02074 |
| R3 | rollm | s2027 | +0.056 S+0.21 DD729 | +0.294 S+0.95 DD521 | +2.394 S+4.70 DD458 | +1.968 S+3.82 DD707 | +0.621 S+1.73 DD729 | +0.961 S+2.38 DD707 | 0.670 | 0.529 | 0.471 | 0.03179 |
| R4 | rollm | s2027 | +0.200 S+0.75 DD797 | +0.407 S+1.26 DD507 | +2.665 S+4.89 DD477 | +2.160 S+3.94 DD785 | +0.765 S+2.04 DD797 | +1.106 S+2.58 DD785 | 0.653 | 0.531 | 0.469 | 0.02876 |
| R5 | rollm | s2027 | +0.233 S+0.88 DD463 | +0.550 S+1.66 DD490 | +2.612 S+5.17 DD472 | +2.166 S+4.26 DD695 | +0.833 S+2.29 DD695 | +1.194 S+2.90 DD695 | 0.636 | 0.553 | 0.447 | 0.03007 |
| R0 | pinned | s42 | +0.149 S+0.53 DD795 | +0.359 S+1.15 DD418 | +2.512 S+4.83 DD452 | +2.013 S+3.84 DD771 | +0.691 S+1.88 DD795 | +1.018 S+2.48 DD771 | 0.630 | 0.549 | 0.451 | 0.03086 |
| R1 | pinned | s42 | +0.028 S+0.10 DD995 | +0.522 S+1.70 DD459 | +2.396 S+4.63 DD442 | +1.939 S+3.74 DD706 | +0.689 S+1.92 DD995 | +1.087 S+2.69 DD706 | 0.624 | 0.468 | 0.532 | 0.02906 |
| R2 | pinned | s42 | +0.152 S+0.52 DD654 | +0.485 S+1.41 DD645 | +2.753 S+5.05 DD436 | +2.236 S+4.08 DD784 | +0.796 S+2.04 DD784 | +1.184 S+2.71 DD784 | 0.641 | 0.321 | 0.679 | 0.02089 |
| R3 | pinned | s42 | -0.048 S-0.17 DD815 | +0.230 S+0.74 DD471 | +2.285 S+4.66 DD430 | +1.859 S+3.76 DD666 | +0.531 S+1.50 DD815 | +0.879 S+2.23 DD666 | 0.662 | 0.524 | 0.476 | 0.03271 |
| R4 | pinned | s42 | +0.089 S+0.34 DD814 | +0.350 S+1.10 DD436 | +2.629 S+4.96 DD460 | +2.130 S+3.99 DD757 | +0.694 S+1.89 DD814 | +1.059 S+2.54 DD757 | 0.646 | 0.531 | 0.469 | 0.03000 |
| R5 | pinned | s42 | +0.028 S+0.11 DD802 | +0.480 S+1.48 DD408 | +2.457 S+5.02 DD447 | +2.059 S+4.18 DD625 | +0.703 S+1.98 DD802 | +1.109 S+2.78 DD625 | 0.620 | 0.554 | 0.446 | 0.03120 |
| R0 | pinned | s2027 | +0.217 S+0.78 DD740 | +0.438 S+1.36 DD430 | +2.486 S+4.78 DD460 | +1.994 S+3.80 DD757 | +0.742 S+2.00 DD757 | +1.058 S+2.55 DD757 | 0.642 | 0.549 | 0.451 | 0.03002 |
| R1 | pinned | s2027 | +0.104 S+0.40 DD927 | +0.611 S+1.96 DD440 | +2.398 S+4.63 DD444 | +1.944 S+3.74 DD695 | +0.752 S+2.09 DD927 | +1.143 S+2.80 DD695 | 0.633 | 0.468 | 0.532 | 0.02834 |
| R2 | pinned | s2027 | +0.183 S+0.62 DD666 | +0.586 S+1.67 DD551 | +2.757 S+5.04 DD437 | +2.239 S+4.08 DD777 | +0.846 S+2.16 DD777 | +1.245 S+2.82 DD777 | 0.649 | 0.321 | 0.679 | 0.02035 |
| R3 | pinned | s2027 | +0.004 S+0.01 DD798 | +0.291 S+0.92 DD497 | +2.266 S+4.61 DD447 | +1.851 S+3.73 DD652 | +0.571 S+1.60 DD798 | +0.913 S+2.30 DD652 | 0.672 | 0.524 | 0.476 | 0.03190 |
| R4 | pinned | s2027 | +0.160 S+0.61 DD770 | +0.430 S+1.32 DD485 | +2.617 S+4.92 DD465 | +2.123 S+3.97 DD743 | +0.750 S+2.02 DD770 | +1.105 S+2.62 DD743 | 0.658 | 0.531 | 0.469 | 0.02908 |
| R5 | pinned | s2027 | +0.094 S+0.36 DD782 | +0.541 S+1.64 DD476 | +2.477 S+5.05 DD467 | +2.083 S+4.22 DD616 | +0.756 S+2.12 DD782 | +1.156 S+2.86 DD616 | 0.631 | 0.554 | 0.446 | 0.03057 |

#### caliber **prod** = compounded Π(1+r5)-1 over [E+1,E+48] (meta_newprod swap), CAL=log

| rule | king | seed | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | gross | w_king | w_fund | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | rollm | s42 | +0.116 S+0.42 DD906 | +0.344 S+1.11 DD462 | +2.603 S+4.93 DD358 | +2.117 S+3.98 DD777 | +0.699 S+1.90 DD906 | +1.051 S+2.54 DD777 | 0.624 | 0.567 | 0.433 | 0.03181 |
| R1 | rollm | s42 | +0.081 S+0.29 DD942 | +0.458 S+1.45 DD484 | +2.488 S+4.77 DD348 | +1.994 S+3.79 DD781 | +0.698 S+1.91 DD942 | +1.070 S+2.59 DD781 | 0.621 | 0.467 | 0.533 | 0.02886 |
| R2 | rollm | s42 | +0.106 S+0.37 DD789 | +0.520 S+1.44 DD583 | +2.739 S+5.00 DD326 | +2.225 S+4.05 DD780 | +0.789 S+2.00 DD789 | +1.200 S+2.69 DD780 | 0.645 | 0.329 | 0.671 | 0.02105 |
| R3 | rollm | s42 | -0.031 S-0.12 DD786 | +0.223 S+0.73 DD464 | +2.516 S+4.97 DD348 | +2.081 S+4.08 DD699 | +0.590 S+1.66 DD786 | +0.964 S+2.40 DD699 | 0.655 | 0.534 | 0.466 | 0.03315 |
| R4 | rollm | s42 | +0.155 S+0.59 DD817 | +0.350 S+1.09 DD469 | +2.655 S+4.96 DD364 | +2.162 S+4.02 DD776 | +0.727 S+1.97 DD817 | +1.073 S+2.55 DD776 | 0.634 | 0.549 | 0.451 | 0.03097 |
| R5 | rollm | s42 | +0.206 S+0.76 DD447 | +0.498 S+1.48 DD485 | +2.633 S+5.30 DD358 | +2.207 S+4.42 DD666 | +0.813 S+2.24 DD666 | +1.179 S+2.88 DD666 | 0.622 | 0.563 | 0.437 | 0.03123 |
| R0 | rollm | s2027 | +0.214 S+0.79 DD806 | +0.404 S+1.27 DD484 | +2.641 S+4.99 DD359 | +2.155 S+4.04 DD773 | +0.768 S+2.08 DD806 | +1.102 S+2.64 DD773 | 0.636 | 0.567 | 0.433 | 0.03072 |
| R1 | rollm | s2027 | +0.185 S+0.68 DD871 | +0.538 S+1.68 DD547 | +2.445 S+4.67 DD346 | +1.956 S+3.71 DD780 | +0.758 S+2.06 DD871 | +1.103 S+2.65 DD780 | 0.629 | 0.467 | 0.533 | 0.02790 |
| R2 | rollm | s2027 | +0.190 S+0.66 DD728 | +0.574 S+1.57 DD505 | +2.728 S+4.96 DD327 | +2.215 S+4.03 DD779 | +0.838 S+2.11 DD779 | +1.228 S+2.74 DD779 | 0.652 | 0.329 | 0.671 | 0.02041 |
| R3 | rollm | s2027 | +0.093 S+0.36 DD708 | +0.309 S+0.99 DD512 | +2.439 S+4.84 DD358 | +2.034 S+4.00 DD670 | +0.657 S+1.85 DD708 | +0.997 S+2.48 DD670 | 0.665 | 0.534 | 0.466 | 0.03215 |
| R4 | rollm | s2027 | +0.257 S+0.98 DD753 | +0.415 S+1.27 DD489 | +2.651 S+4.96 DD374 | +2.162 S+4.02 DD769 | +0.790 S+2.13 DD769 | +1.112 S+2.62 DD769 | 0.645 | 0.549 | 0.451 | 0.02984 |
| R5 | rollm | s2027 | +0.277 S+1.04 DD422 | +0.563 S+1.65 DD491 | +2.699 S+5.42 DD354 | +2.274 S+4.54 DD657 | +0.881 S+2.42 DD657 | +1.245 S+3.02 DD657 | 0.632 | 0.563 | 0.437 | 0.03040 |
| R0 | pinned | s42 | +0.116 S+0.43 DD967 | +0.339 S+1.06 DD413 | +2.543 S+4.95 DD345 | +2.068 S+4.00 DD737 | +0.685 S+1.88 DD967 | +1.028 S+2.51 DD737 | 0.624 | 0.563 | 0.437 | 0.03157 |
| R1 | pinned | s42 | +0.064 S+0.24 DD1008 | +0.524 S+1.68 DD457 | +2.349 S+4.56 DD352 | +1.903 S+3.69 DD668 | +0.694 S+1.93 DD1008 | +1.074 S+2.64 DD668 | 0.615 | 0.474 | 0.525 | 0.02925 |
| R2 | pinned | s42 | +0.115 S+0.39 DD773 | +0.515 S+1.46 DD594 | +2.700 S+4.95 DD336 | +2.197 S+4.02 DD756 | +0.783 S+2.00 DD773 | +1.185 S+2.69 DD756 | 0.636 | 0.315 | 0.685 | 0.02085 |
| R3 | pinned | s42 | -0.025 S-0.09 DD828 | +0.243 S+0.77 DD420 | +2.387 S+4.89 DD328 | +1.942 S+3.96 DD688 | +0.565 S+1.60 DD828 | +0.920 S+2.33 DD688 | 0.655 | 0.531 | 0.469 | 0.03323 |
| R4 | pinned | s42 | +0.112 S+0.45 DD849 | +0.314 S+0.98 DD408 | +2.510 S+4.82 DD356 | +2.025 S+3.86 DD747 | +0.663 S+1.84 DD849 | +0.996 S+2.40 DD747 | 0.636 | 0.551 | 0.449 | 0.03125 |
| R5 | pinned | s42 | +0.078 S+0.29 DD779 | +0.480 S+1.44 DD425 | +2.503 S+5.20 DD345 | +2.120 S+4.39 DD601 | +0.737 S+2.07 DD779 | +1.134 S+2.83 DD601 | 0.617 | 0.568 | 0.432 | 0.03171 |
| R0 | pinned | s2027 | +0.197 S+0.73 DD896 | +0.399 S+1.22 DD446 | +2.524 S+4.92 DD364 | +2.058 S+3.98 DD730 | +0.736 S+2.00 DD896 | +1.060 S+2.56 DD730 | 0.636 | 0.563 | 0.437 | 0.03078 |
| R1 | pinned | s2027 | +0.165 S+0.63 DD916 | +0.588 S+1.85 DD478 | +2.356 S+4.56 DD351 | +1.909 S+3.69 DD672 | +0.757 S+2.10 DD916 | +1.115 S+2.72 DD672 | 0.624 | 0.474 | 0.525 | 0.02853 |
| R2 | pinned | s2027 | +0.183 S+0.62 DD727 | +0.575 S+1.61 DD522 | +2.688 S+4.93 DD334 | +2.187 S+4.00 DD751 | +0.829 S+2.10 DD751 | +1.218 S+2.75 DD751 | 0.643 | 0.315 | 0.685 | 0.02033 |
| R3 | pinned | s2027 | +0.062 S+0.23 DD772 | +0.311 S+0.97 DD452 | +2.379 S+4.88 DD352 | +1.954 S+3.98 DD655 | +0.626 S+1.77 DD772 | +0.966 S+2.43 DD655 | 0.665 | 0.531 | 0.469 | 0.03243 |
| R4 | pinned | s2027 | +0.184 S+0.74 DD817 | +0.389 S+1.19 DD446 | +2.560 S+4.90 DD344 | +2.076 S+3.95 DD728 | +0.731 S+2.01 DD817 | +1.061 S+2.54 DD728 | 0.648 | 0.551 | 0.449 | 0.03033 |
| R5 | pinned | s2027 | +0.159 S+0.60 DD712 | +0.565 S+1.66 DD449 | +2.532 S+5.24 DD362 | +2.156 S+4.45 DD577 | +0.808 S+2.25 DD712 | +1.199 S+2.96 DD601 | 0.628 | 0.568 | 0.432 | 0.03109 |

### Deltas — Δ = R_k − R0 (net_ex, bps/anchor), paired anchors; UTC-day-block bootstrap 2000×, seed 20260905; cell = Δ [CI95] P(Δ>0); **2025->26 = PRIMARY**

#### caliber **log**

| rule | king | seed | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | ΔSharpe 25on/24on | Δturn% 25on/24on | Δ mean w_king 25on | maxDD R0/Rk 25on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | rollm | s42 | -0.042 [-0.188,+0.098] 0.282 | +0.094 [-0.352,+0.557] 0.673 | -0.193 [-0.479,+0.053] 0.069 | -0.185 [-0.440,+0.065] 0.067 | -0.027 [-0.220,+0.168] 0.392 | **-0.018 [-0.316,+0.284] 0.440** | -0.01/-0.04 | -8.2%/-4.9% | -0.096 | 801/803 |
| R2 | rollm | s42 | +0.053 [-0.317,+0.439] 0.597 | +0.161 [-0.169,+0.508] 0.831 | +0.150 [-0.150,+0.459] 0.841 | +0.092 [-0.200,+0.386] 0.735 | +0.103 [-0.105,+0.311] 0.832 | **+0.134 [-0.099,+0.369] 0.861** | +0.14/+0.16 | -31.5%/-30.4% | -0.215 | 801/835 |
| R3 | rollm | s42 | -0.130 [-0.335,+0.059] 0.085 | -0.126 [-0.357,+0.103] 0.148 | -0.176 [-0.357,-0.000] 0.025 | -0.112 [-0.279,+0.061] 0.103 | -0.124 [-0.249,-0.003] 0.022 | **-0.120 [-0.274,+0.046] 0.078** | -0.21/-0.27 | +5.1%/+2.1% | -0.029 | 801/710 |
| R4 | rollm | s42 | +0.031 [-0.092,+0.157] 0.710 | +0.004 [-0.060,+0.064] 0.526 | +0.123 [+0.015,+0.240] 0.988 | +0.111 [+0.011,+0.218] 0.983 | +0.041 [-0.018,+0.101] 0.915 | **+0.047 [-0.007,+0.101] 0.952** | +0.06/+0.10 | -4.2%/-0.4% | -0.026 | 801/789 |
| R5 | rollm | s42 | +0.050 [-0.264,+0.384] 0.617 | +0.152 [+0.006,+0.300] 0.981 | -0.028 [-0.378,+0.347] 0.414 | +0.024 [-0.289,+0.372] 0.566 | +0.082 [-0.072,+0.243] 0.848 | **+0.101 [-0.051,+0.261] 0.897** | +0.30/+0.27 | -1.0%/-0.7% | -0.004 | 801/703 |
| R1 | rollm | s2027 | -0.030 [-0.194,+0.129] 0.341 | +0.071 [-0.403,+0.530] 0.613 | -0.182 [-0.445,+0.063] 0.085 | -0.175 [-0.411,+0.059] 0.063 | -0.028 [-0.210,+0.161] 0.373 | **-0.027 [-0.305,+0.264] 0.424** | -0.02/-0.04 | -7.7%/-4.6% | -0.096 | 794/794 |
| R2 | rollm | s2027 | +0.021 [-0.390,+0.395] 0.517 | +0.134 [-0.236,+0.502] 0.755 | +0.139 [-0.155,+0.415] 0.825 | +0.076 [-0.193,+0.353] 0.708 | +0.077 [-0.133,+0.288] 0.770 | **+0.111 [-0.120,+0.342] 0.806** | +0.09/+0.08 | -31.2%/-30.1% | -0.215 | 794/833 |
| R3 | rollm | s2027 | -0.110 [-0.323,+0.095] 0.148 | -0.130 [-0.350,+0.103] 0.145 | -0.200 [-0.381,-0.026] 0.015 | -0.134 [-0.313,+0.035] 0.061 | -0.123 [-0.249,-0.005] 0.022 | **-0.132 [-0.291,+0.029] 0.057** | -0.22/-0.26 | +5.5%/+2.4% | -0.029 | 794/707 |
| R4 | rollm | s2027 | +0.035 [-0.084,+0.163] 0.694 | -0.017 [-0.083,+0.051] 0.310 | +0.071 [-0.025,+0.167] 0.932 | +0.058 [-0.029,+0.151] 0.901 | +0.021 [-0.035,+0.078] 0.770 | **+0.013 [-0.042,+0.065] 0.670** | -0.02/+0.04 | -4.5%/-0.5% | -0.026 | 794/785 |
| R5 | rollm | s2027 | +0.067 [-0.233,+0.396] 0.668 | +0.126 [-0.016,+0.274] 0.955 | +0.018 [-0.345,+0.412] 0.530 | +0.064 [-0.279,+0.428] 0.627 | +0.088 [-0.067,+0.249] 0.864 | **+0.101 [-0.056,+0.265] 0.890** | +0.30/+0.29 | -0.2%/-0.2% | -0.004 | 794/695 |
| R1 | pinned | s42 | -0.121 [-0.309,+0.056] 0.086 | +0.163 [-0.293,+0.626] 0.748 | -0.116 [-0.460,+0.236] 0.283 | -0.074 [-0.389,+0.221] 0.316 | -0.003 [-0.201,+0.207] 0.510 | **+0.068 [-0.233,+0.379] 0.663** | +0.21/+0.04 | -5.8%/+0.8% | -0.081 | 771/706 |
| R2 | pinned | s42 | +0.004 [-0.339,+0.323] 0.510 | +0.126 [-0.220,+0.475] 0.773 | +0.241 [-0.067,+0.540] 0.943 | +0.223 [-0.043,+0.517] 0.944 | +0.104 [-0.094,+0.289] 0.844 | **+0.165 [-0.065,+0.404] 0.923** | +0.23/+0.16 | -32.3%/-29.7% | -0.227 | 771/784 |
| R3 | pinned | s42 | -0.197 [-0.401,+0.001] 0.025 | -0.129 [-0.358,+0.101] 0.142 | -0.226 [-0.407,-0.051] 0.008 | -0.154 [-0.329,+0.022] 0.049 | -0.161 [-0.285,-0.037] 0.005 | **-0.139 [-0.287,+0.018] 0.045** | -0.25/-0.39 | +6.0%/+4.9% | -0.024 | 771/666 |
| R4 | pinned | s42 | -0.060 [-0.188,+0.055] 0.165 | -0.009 [-0.082,+0.065] 0.394 | +0.117 [-0.001,+0.244] 0.974 | +0.116 [+0.005,+0.228] 0.981 | +0.003 [-0.055,+0.066] 0.555 | **+0.041 [-0.020,+0.105] 0.902** | +0.06/+0.01 | -2.8%/+2.0% | -0.017 | 771/757 |
| R5 | pinned | s42 | -0.121 [-0.376,+0.112] 0.155 | +0.121 [+0.010,+0.246] 0.983 | -0.055 [-0.424,+0.331] 0.382 | +0.046 [-0.303,+0.421] 0.609 | +0.011 [-0.127,+0.150] 0.569 | **+0.091 [-0.066,+0.256] 0.872** | +0.30/+0.09 | +1.1%/+3.5% | +0.005 | 771/625 |
| R1 | pinned | s2027 | -0.113 [-0.299,+0.070] 0.112 | +0.174 [-0.302,+0.634] 0.753 | -0.087 [-0.426,+0.226] 0.280 | -0.050 [-0.357,+0.234] 0.351 | +0.010 [-0.195,+0.216] 0.540 | **+0.085 [-0.231,+0.400] 0.686** | +0.25/+0.08 | -5.6%/+1.0% | -0.081 | 757/695 |
| R2 | pinned | s2027 | -0.034 [-0.355,+0.328] 0.431 | +0.149 [-0.200,+0.534] 0.804 | +0.271 [-0.029,+0.576] 0.962 | +0.246 [-0.026,+0.527] 0.962 | +0.104 [-0.082,+0.301] 0.843 | **+0.187 [-0.058,+0.422] 0.934** | +0.27/+0.15 | -32.2%/-29.4% | -0.227 | 757/777 |
| R3 | pinned | s2027 | -0.213 [-0.427,-0.009] 0.019 | -0.147 [-0.374,+0.087] 0.104 | -0.219 [-0.396,-0.045] 0.007 | -0.143 [-0.316,+0.016] 0.036 | -0.171 [-0.292,-0.046] 0.003 | **-0.145 [-0.305,+0.013] 0.037** | -0.25/-0.40 | +6.3%/+5.2% | -0.024 | 757/652 |
| R4 | pinned | s2027 | -0.057 [-0.179,+0.069] 0.186 | -0.008 [-0.080,+0.068] 0.420 | +0.131 [+0.012,+0.247] 0.986 | +0.130 [+0.027,+0.243] 0.992 | +0.008 [-0.054,+0.069] 0.593 | **+0.047 [-0.014,+0.112] 0.941** | +0.07/+0.02 | -3.1%/+1.9% | -0.017 | 757/743 |
| R5 | pinned | s2027 | -0.123 [-0.377,+0.128] 0.171 | +0.104 [-0.020,+0.232] 0.949 | -0.008 [-0.402,+0.416] 0.487 | +0.089 [-0.298,+0.485] 0.662 | +0.015 [-0.129,+0.146] 0.578 | **+0.098 [-0.071,+0.272] 0.873** | +0.31/+0.11 | +1.9%/+4.1% | +0.005 | 757/616 |

#### caliber **prod**

| rule | king | seed | 2024 | 2025 | 2026<=08-10 | 2026->08-30 | 2024->26 | 2025->26 | ΔSharpe 25on/24on | Δturn% 25on/24on | Δ mean w_king 25on | maxDD R0/Rk 25on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | rollm | s42 | -0.036 [-0.189,+0.116] 0.331 | +0.113 [-0.371,+0.584] 0.678 | -0.115 [-0.389,+0.140] 0.194 | -0.123 [-0.363,+0.112] 0.159 | -0.002 [-0.194,+0.199] 0.490 | **+0.019 [-0.273,+0.315] 0.552** | +0.05/+0.00 | -9.3%/-6.2% | -0.100 | 777/781 |
| R2 | rollm | s42 | -0.010 [-0.412,+0.373] 0.486 | +0.176 [-0.197,+0.578] 0.817 | +0.135 [-0.195,+0.455] 0.793 | +0.108 [-0.200,+0.419] 0.743 | +0.089 [-0.127,+0.315] 0.795 | **+0.149 [-0.116,+0.416] 0.869** | +0.15/+0.10 | -33.8%/-31.4% | -0.239 | 777/780 |
| R3 | rollm | s42 | -0.147 [-0.347,+0.052] 0.077 | -0.121 [-0.350,+0.098] 0.153 | -0.087 [-0.257,+0.076] 0.154 | -0.036 [-0.202,+0.140] 0.355 | -0.110 [-0.234,+0.008] 0.032 | **-0.087 [-0.247,+0.071] 0.139** | -0.14/-0.24 | +4.2%/+1.1% | -0.034 | 777/699 |
| R4 | rollm | s42 | +0.039 [-0.080,+0.157] 0.751 | +0.006 [-0.057,+0.075] 0.554 | +0.052 [-0.024,+0.131] 0.898 | +0.045 [-0.034,+0.118] 0.869 | +0.028 [-0.025,+0.082] 0.849 | **+0.021 [-0.029,+0.069] 0.813** | +0.01/+0.07 | -2.6%/-0.1% | -0.019 | 777/776 |
| R5 | rollm | s42 | +0.089 [-0.237,+0.398] 0.722 | +0.153 [-0.011,+0.317] 0.965 | +0.029 [-0.318,+0.411] 0.568 | +0.090 [-0.256,+0.446] 0.675 | +0.114 [-0.051,+0.272] 0.911 | **+0.128 [-0.036,+0.312] 0.939** | +0.34/+0.34 | -1.8%/-2.4% | -0.005 | 777/666 |
| R1 | rollm | s2027 | -0.029 [-0.189,+0.137] 0.366 | +0.134 [-0.333,+0.609] 0.700 | -0.195 [-0.497,+0.096] 0.089 | -0.199 [-0.460,+0.054] 0.062 | -0.010 [-0.211,+0.197] 0.457 | **+0.001 [-0.295,+0.324] 0.525** | +0.01/-0.02 | -9.2%/-6.2% | -0.100 | 773/780 |
| R2 | rollm | s2027 | -0.025 [-0.452,+0.379] 0.449 | +0.170 [-0.212,+0.540] 0.800 | +0.087 [-0.261,+0.426] 0.707 | +0.061 [-0.258,+0.397] 0.654 | +0.069 [-0.149,+0.283] 0.710 | **+0.126 [-0.122,+0.393] 0.838** | +0.10/+0.03 | -33.5%/-31.2% | -0.239 | 773/779 |
| R3 | rollm | s2027 | -0.121 [-0.320,+0.076] 0.112 | -0.096 [-0.337,+0.136] 0.204 | -0.201 [-0.368,-0.034] 0.009 | -0.121 [-0.290,+0.044] 0.070 | -0.112 [-0.237,+0.008] 0.036 | **-0.106 [-0.256,+0.052] 0.099** | -0.16/-0.23 | +4.6%/+1.4% | -0.034 | 773/670 |
| R4 | rollm | s2027 | +0.043 [-0.082,+0.168] 0.745 | +0.011 [-0.054,+0.082] 0.606 | +0.011 [-0.093,+0.113] 0.556 | +0.007 [-0.093,+0.102] 0.559 | +0.022 [-0.032,+0.081] 0.769 | **+0.009 [-0.047,+0.068] 0.618** | -0.02/+0.05 | -2.9%/-0.2% | -0.019 | 773/769 |
| R5 | rollm | s2027 | +0.063 [-0.262,+0.400] 0.641 | +0.159 [-0.006,+0.318] 0.969 | +0.059 [-0.319,+0.480] 0.620 | +0.120 [-0.257,+0.466] 0.742 | +0.113 [-0.050,+0.283] 0.916 | **+0.143 [-0.024,+0.318] 0.951** | +0.38/+0.34 | -1.1%/-1.9% | -0.005 | 773/657 |
| R1 | pinned | s42 | -0.051 [-0.221,+0.114] 0.258 | +0.185 [-0.314,+0.679] 0.780 | -0.194 [-0.545,+0.165] 0.151 | -0.165 [-0.503,+0.163] 0.172 | +0.009 [-0.216,+0.240] 0.546 | **+0.045 [-0.275,+0.371] 0.604** | +0.14/+0.05 | -7.4%/-2.3% | -0.088 | 737/668 |
| R2 | pinned | s42 | -0.001 [-0.356,+0.331] 0.518 | +0.176 [-0.195,+0.534] 0.829 | +0.157 [-0.210,+0.513] 0.787 | +0.129 [-0.212,+0.445] 0.773 | +0.098 [-0.113,+0.317] 0.822 | **+0.157 [-0.091,+0.421] 0.898** | +0.18/+0.12 | -34.0%/-31.6% | -0.247 | 737/756 |
| R3 | pinned | s42 | -0.141 [-0.348,+0.062] 0.092 | -0.096 [-0.336,+0.136] 0.198 | -0.155 [-0.298,-0.018] 0.013 | -0.126 [-0.272,+0.016] 0.043 | -0.120 [-0.244,-0.003] 0.024 | **-0.108 [-0.265,+0.049] 0.080** | -0.18/-0.28 | +5.2%/+3.5% | -0.031 | 737/688 |
| R4 | pinned | s42 | -0.004 [-0.129,+0.120] 0.449 | -0.026 [-0.100,+0.045] 0.238 | -0.033 [-0.191,+0.112] 0.345 | -0.043 [-0.194,+0.093] 0.306 | -0.022 [-0.087,+0.041] 0.240 | **-0.033 [-0.105,+0.037] 0.183** | -0.10/-0.05 | -1.0%/+3.0% | -0.011 | 737/747 |
| R5 | pinned | s42 | -0.037 [-0.308,+0.221] 0.370 | +0.141 [+0.017,+0.275] 0.990 | -0.040 [-0.415,+0.363] 0.427 | +0.052 [-0.317,+0.438] 0.611 | +0.052 [-0.088,+0.193] 0.763 | **+0.106 [-0.061,+0.278] 0.890** | +0.33/+0.19 | +0.4%/+0.5% | +0.005 | 737/601 |
| R1 | pinned | s2027 | -0.033 [-0.199,+0.134] 0.362 | +0.190 [-0.319,+0.708] 0.762 | -0.168 [-0.558,+0.206] 0.179 | -0.149 [-0.513,+0.178] 0.199 | +0.022 [-0.203,+0.258] 0.574 | **+0.055 [-0.278,+0.379] 0.627** | +0.16/+0.10 | -7.3%/-2.2% | -0.088 | 730/672 |
| R2 | pinned | s2027 | -0.014 [-0.368,+0.343] 0.462 | +0.176 [-0.176,+0.546] 0.827 | +0.164 [-0.201,+0.516] 0.808 | +0.129 [-0.208,+0.464] 0.771 | +0.093 [-0.114,+0.303] 0.812 | **+0.158 [-0.082,+0.426] 0.890** | +0.19/+0.10 | -34.0%/-31.4% | -0.247 | 730/751 |
| R3 | pinned | s2027 | -0.136 [-0.342,+0.069] 0.096 | -0.088 [-0.321,+0.155] 0.239 | -0.145 [-0.298,+0.003] 0.029 | -0.104 [-0.264,+0.047] 0.090 | -0.110 [-0.238,+0.012] 0.034 | **-0.094 [-0.244,+0.068] 0.136** | -0.13/-0.23 | +5.4%/+3.7% | -0.031 | 730/655 |
| R4 | pinned | s2027 | -0.013 [-0.146,+0.116] 0.402 | -0.010 [-0.079,+0.060] 0.401 | +0.036 [-0.140,+0.199] 0.675 | +0.018 [-0.154,+0.169] 0.611 | -0.004 [-0.075,+0.065] 0.456 | **+0.001 [-0.079,+0.073] 0.521** | -0.02/+0.00 | -1.4%/+2.8% | -0.011 | 730/728 |
| R5 | pinned | s2027 | -0.038 [-0.320,+0.225] 0.392 | +0.167 [+0.038,+0.307] 0.993 | +0.007 [-0.388,+0.430] 0.536 | +0.098 [-0.280,+0.512] 0.705 | +0.073 [-0.082,+0.221] 0.821 | **+0.139 [-0.034,+0.317] 0.948** | +0.40/+0.25 | +1.0%/+1.0% | +0.005 | 730/601 |

### Seat trajectories — w3_king by year (mean), switches = sign(w_king−0.5) flips, jumps = |Δw_king|≥0.05, seat_turn = mean |Δw_king| per anchor; identical across calibers only if the seat inputs are (they are not: leg returns differ by caliber), so both calibers are listed

| rule | king | seed | cal | 2022 | 2023 | 2024 | 2025 | 2026 | 2025->26 mean | min/max w_king | switches 24on / 25on | jumps 24on / 25on | seat_turn 24on / 25on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 | rollm | s42 | log | 0.225 | 0.066 | 0.713 | 0.692 | 0.354 | 0.557 | 0.192/1.000 | 101 / 23 | 139 / 2 | 0.01037 / 0.00418 |
| R0 | rollm | s42 | prod | 0.222 | 0.050 | 0.735 | 0.705 | 0.360 | 0.567 | 0.198/1.000 | 109 / 29 | 155 / 8 | 0.01046 / 0.00457 |
| R0 | rollm | s2027 | log | 0.225 | 0.066 | 0.713 | 0.692 | 0.354 | 0.557 | 0.192/1.000 | 101 / 23 | 139 / 2 | 0.01037 / 0.00418 |
| R0 | rollm | s2027 | prod | 0.222 | 0.050 | 0.735 | 0.705 | 0.360 | 0.567 | 0.198/1.000 | 109 / 29 | 155 / 8 | 0.01046 / 0.00457 |
| R0 | pinned | s42 | log | 0.225 | 0.066 | 0.639 | 0.673 | 0.361 | 0.549 | 0.190/1.000 | 67 / 17 | 162 / 3 | 0.00878 / 0.00444 |
| R0 | pinned | s42 | prod | 0.222 | 0.050 | 0.682 | 0.687 | 0.375 | 0.563 | 0.207/1.000 | 85 / 27 | 184 / 9 | 0.00941 / 0.00477 |
| R0 | pinned | s2027 | log | 0.225 | 0.066 | 0.639 | 0.673 | 0.361 | 0.549 | 0.190/1.000 | 67 / 17 | 162 / 3 | 0.00878 / 0.00444 |
| R0 | pinned | s2027 | prod | 0.222 | 0.050 | 0.682 | 0.687 | 0.375 | 0.563 | 0.207/1.000 | 85 / 27 | 184 / 9 | 0.00941 / 0.00477 |
| R1 | rollm | s42 | log | 0.198 | 0.141 | 0.715 | 0.550 | 0.326 | 0.461 | 0.000/1.000 | 169 / 79 | 322 / 82 | 0.01746 / 0.01217 |
| R1 | rollm | s42 | prod | 0.187 | 0.138 | 0.721 | 0.564 | 0.322 | 0.467 | 0.000/1.000 | 158 / 65 | 358 / 88 | 0.01913 / 0.01252 |
| R1 | rollm | s2027 | log | 0.198 | 0.141 | 0.715 | 0.550 | 0.326 | 0.461 | 0.000/1.000 | 169 / 79 | 322 / 82 | 0.01746 / 0.01217 |
| R1 | rollm | s2027 | prod | 0.187 | 0.138 | 0.721 | 0.564 | 0.322 | 0.467 | 0.000/1.000 | 158 / 65 | 358 / 88 | 0.01913 / 0.01252 |
| R1 | pinned | s42 | log | 0.198 | 0.141 | 0.693 | 0.548 | 0.347 | 0.468 | 0.000/1.000 | 114 / 46 | 360 / 119 | 0.01763 / 0.01259 |
| R1 | pinned | s42 | prod | 0.187 | 0.138 | 0.698 | 0.557 | 0.350 | 0.474 | 0.000/1.000 | 140 / 53 | 361 / 118 | 0.01917 / 0.01343 |
| R1 | pinned | s2027 | log | 0.198 | 0.141 | 0.693 | 0.548 | 0.347 | 0.468 | 0.000/1.000 | 114 / 46 | 360 / 119 | 0.01763 / 0.01259 |
| R1 | pinned | s2027 | prod | 0.187 | 0.138 | 0.698 | 0.557 | 0.350 | 0.474 | 0.000/1.000 | 140 / 53 | 361 / 118 | 0.01917 / 0.01343 |
| R2 | rollm | s42 | log | 0.244 | 0.105 | 0.393 | 0.455 | 0.173 | 0.343 | 0.000/1.000 | 71 / 11 | 175 / 62 | 0.01114 / 0.00819 |
| R2 | rollm | s42 | prod | 0.233 | 0.087 | 0.410 | 0.443 | 0.156 | 0.329 | 0.000/1.000 | 76 / 20 | 194 / 68 | 0.01174 / 0.00939 |
| R2 | rollm | s2027 | log | 0.244 | 0.105 | 0.393 | 0.455 | 0.173 | 0.343 | 0.000/1.000 | 71 / 11 | 175 / 62 | 0.01114 / 0.00819 |
| R2 | rollm | s2027 | prod | 0.233 | 0.087 | 0.410 | 0.443 | 0.156 | 0.329 | 0.000/1.000 | 76 / 20 | 194 / 68 | 0.01174 / 0.00939 |
| R2 | pinned | s42 | log | 0.244 | 0.105 | 0.346 | 0.416 | 0.178 | 0.321 | 0.000/1.000 | 56 / 14 | 152 / 74 | 0.00968 / 0.00806 |
| R2 | pinned | s42 | prod | 0.233 | 0.087 | 0.369 | 0.410 | 0.173 | 0.315 | 0.000/1.000 | 54 / 26 | 146 / 71 | 0.00888 / 0.00824 |
| R2 | pinned | s2027 | log | 0.244 | 0.105 | 0.346 | 0.416 | 0.178 | 0.321 | 0.000/1.000 | 56 / 14 | 152 / 74 | 0.00968 / 0.00806 |
| R2 | pinned | s2027 | prod | 0.233 | 0.087 | 0.369 | 0.410 | 0.173 | 0.315 | 0.000/1.000 | 54 / 26 | 146 / 71 | 0.00888 / 0.00824 |
| R3 | rollm | s42 | log | 0.325 | 0.283 | 0.607 | 0.596 | 0.427 | 0.529 | 0.346/0.750 | 101 / 23 | 73 / 0 | 0.00518 / 0.00209 |
| R3 | rollm | s42 | prod | 0.324 | 0.275 | 0.617 | 0.603 | 0.430 | 0.534 | 0.349/0.750 | 109 / 29 | 67 / 0 | 0.00523 / 0.00228 |
| R3 | rollm | s2027 | log | 0.325 | 0.283 | 0.607 | 0.596 | 0.427 | 0.529 | 0.346/0.750 | 101 / 23 | 73 / 0 | 0.00518 / 0.00209 |
| R3 | rollm | s2027 | prod | 0.324 | 0.275 | 0.617 | 0.603 | 0.430 | 0.534 | 0.349/0.750 | 109 / 29 | 67 / 0 | 0.00523 / 0.00228 |
| R3 | pinned | s42 | log | 0.325 | 0.283 | 0.570 | 0.586 | 0.431 | 0.524 | 0.345/0.750 | 67 / 17 | 50 / 0 | 0.00439 / 0.00222 |
| R3 | pinned | s42 | prod | 0.324 | 0.275 | 0.591 | 0.594 | 0.437 | 0.531 | 0.354/0.750 | 85 / 27 | 61 / 0 | 0.00470 / 0.00238 |
| R3 | pinned | s2027 | log | 0.325 | 0.283 | 0.570 | 0.586 | 0.431 | 0.524 | 0.345/0.750 | 67 / 17 | 50 / 0 | 0.00439 / 0.00222 |
| R3 | pinned | s2027 | prod | 0.324 | 0.275 | 0.591 | 0.594 | 0.437 | 0.531 | 0.354/0.750 | 85 / 27 | 61 / 0 | 0.00470 / 0.00238 |
| R4 | rollm | s42 | log | 0.225 | 0.066 | 0.756 | 0.674 | 0.316 | 0.531 | 0.124/1.000 | 75 / 11 | 99 / 6 | 0.00884 / 0.00407 |
| R4 | rollm | s42 | prod | 0.222 | 0.050 | 0.769 | 0.694 | 0.330 | 0.549 | 0.114/1.000 | 63 / 13 | 112 / 15 | 0.00876 / 0.00441 |
| R4 | rollm | s2027 | log | 0.225 | 0.066 | 0.756 | 0.674 | 0.316 | 0.531 | 0.124/1.000 | 75 / 11 | 99 / 6 | 0.00884 / 0.00407 |
| R4 | rollm | s2027 | prod | 0.222 | 0.050 | 0.769 | 0.694 | 0.330 | 0.549 | 0.114/1.000 | 63 / 13 | 112 / 15 | 0.00876 / 0.00441 |
| R4 | pinned | s42 | log | 0.225 | 0.066 | 0.679 | 0.662 | 0.334 | 0.531 | 0.216/1.000 | 67 / 15 | 148 / 6 | 0.00875 / 0.00391 |
| R4 | pinned | s42 | prod | 0.222 | 0.050 | 0.720 | 0.683 | 0.353 | 0.551 | 0.226/1.000 | 89 / 11 | 166 / 13 | 0.00994 / 0.00421 |
| R4 | pinned | s2027 | log | 0.225 | 0.066 | 0.679 | 0.662 | 0.334 | 0.531 | 0.216/1.000 | 67 / 15 | 148 / 6 | 0.00875 / 0.00391 |
| R4 | pinned | s2027 | prod | 0.222 | 0.050 | 0.720 | 0.683 | 0.353 | 0.551 | 0.226/1.000 | 89 / 11 | 166 / 13 | 0.00994 / 0.00421 |
| R5 | rollm | s42 | log | 0.342 | 0.076 | 0.624 | 0.646 | 0.413 | 0.553 | 0.196/1.000 | 159 / 27 | 252 / 22 | 0.01670 / 0.00706 |
| R5 | rollm | s42 | prod | 0.326 | 0.093 | 0.639 | 0.660 | 0.415 | 0.563 | 0.189/1.000 | 147 / 29 | 206 / 20 | 0.01506 / 0.00701 |
| R5 | rollm | s2027 | log | 0.342 | 0.076 | 0.624 | 0.646 | 0.413 | 0.553 | 0.196/1.000 | 159 / 27 | 252 / 22 | 0.01670 / 0.00706 |
| R5 | rollm | s2027 | prod | 0.326 | 0.093 | 0.639 | 0.660 | 0.415 | 0.563 | 0.189/1.000 | 147 / 29 | 206 / 20 | 0.01506 / 0.00701 |
| R5 | pinned | s42 | log | 0.342 | 0.076 | 0.581 | 0.640 | 0.425 | 0.554 | 0.146/1.000 | 148 / 37 | 206 / 22 | 0.01486 / 0.00708 |
| R5 | pinned | s42 | prod | 0.326 | 0.093 | 0.597 | 0.656 | 0.436 | 0.568 | 0.160/1.000 | 146 / 41 | 197 / 21 | 0.01394 / 0.00699 |
| R5 | pinned | s2027 | log | 0.342 | 0.076 | 0.581 | 0.640 | 0.425 | 0.554 | 0.146/1.000 | 148 / 37 | 206 / 22 | 0.01486 / 0.00708 |
| R5 | pinned | s2027 | prod | 0.326 | 0.093 | 0.597 | 0.656 | 0.436 | 0.568 | 0.160/1.000 | 146 / 41 | 197 / 21 | 0.01394 / 0.00699 |

### R2 — per-leg rank-book turnover (unit gross per anchor) and deduction κ·turn (bps/anchor), yearly mean over the legs() sequence

| king | cal | leg | 2022 | 2023 | 2024 | 2025 | 2026 | all | deduction 2024 / 2025 / 2026 (bps) | leg r mean 2025->26 → net |
|---|---|---|---|---|---|---|---|---|---|---|
| rollm | log | king | 0.0000 | 0.0000 | 0.5709 | 0.5541 | 0.5484 | 0.3251 | 2.010 / 1.950 / 1.930 | +2.620 → +0.678 |
| rollm | log | rev24 | 0.5745 | 0.5992 | 0.5939 | 0.5817 | 0.5385 | 0.5805 | 2.091 / 2.048 / 1.895 | +0.859 → -1.128 |
| rollm | log | fund | 0.0380 | 0.0383 | 0.0445 | 0.0344 | 0.0296 | 0.0375 | 0.157 / 0.121 / 0.104 | +3.082 → +2.968 |
| rollm | prod | king | 0.0000 | 0.0000 | 0.5709 | 0.5541 | 0.5484 | 0.3251 | 2.010 / 1.950 / 1.930 | +2.447 → +0.504 |
| rollm | prod | rev24 | 0.5745 | 0.5992 | 0.5939 | 0.5817 | 0.5385 | 0.5805 | 2.091 / 2.048 / 1.895 | +0.892 → -1.094 |
| rollm | prod | fund | 0.0380 | 0.0383 | 0.0445 | 0.0344 | 0.0296 | 0.0375 | 0.157 / 0.121 / 0.104 | +2.906 → +2.792 |
| pinned | log | king | 0.0000 | 0.0000 | 0.6308 | 0.5650 | 0.5480 | 0.3405 | 2.220 / 1.989 / 1.929 | +2.654 → +0.689 |
| pinned | log | rev24 | 0.5745 | 0.5992 | 0.5939 | 0.5817 | 0.5385 | 0.5805 | 2.091 / 2.048 / 1.895 | +0.859 → -1.128 |
| pinned | log | fund | 0.0380 | 0.0383 | 0.0445 | 0.0344 | 0.0296 | 0.0375 | 0.157 / 0.121 / 0.104 | +3.082 → +2.968 |
| pinned | prod | king | 0.0000 | 0.0000 | 0.6308 | 0.5650 | 0.5480 | 0.3405 | 2.220 / 1.989 / 1.929 | +2.536 → +0.571 |
| pinned | prod | rev24 | 0.5745 | 0.5992 | 0.5939 | 0.5817 | 0.5385 | 0.5805 | 2.091 / 2.048 / 1.895 | +0.892 → -1.094 |
| pinned | prod | fund | 0.0380 | 0.0383 | 0.0445 | 0.0344 | 0.0296 | 0.0375 | 0.157 / 0.121 / 0.104 | +2.906 → +2.792 |

### R5 — fallback (plain msharpe900) share by year over evaluated anchors, and causal-tercile membership counts 2024+

| king | cal | seed | 2022 | 2023 | 2024 | 2025 | 2026 | all | tercile counts 2024+ (low/mid/high) |
|---|---|---|---|---|---|---|---|---|---|
| rollm | log | s42 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| rollm | log | s2027 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| rollm | prod | s42 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| rollm | prod | s2027 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| pinned | log | s42 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| pinned | log | s2027 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| pinned | prod | s42 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |
| pinned | prod | s2027 | 0.013 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | [553, 1242, 4043] |

### σ_fund-tercile Δ (2024->26 anchors; cuts 5.45/13.67 bps/8h; n per tercile [1946, 1946, 1946]); cell = Δ [CI95] P (R0 mean → rule mean)

| rule | king | seed | cal | low | mid | high |
|---|---|---|---|---|---|---|
| R1 | rollm | s42 | log | -0.018 [-0.184,+0.140] P0.40 (+0.059→+0.041) | -0.064 [-0.374,+0.275] P0.34 (+0.840→+0.776) | +0.001 [-0.425,+0.427] P0.49 (+1.164→+1.165) |
| R2 | rollm | s42 | log | -0.038 [-0.464,+0.390] P0.45 (+0.059→+0.021) | -0.055 [-0.372,+0.264] P0.36 (+0.840→+0.786) | +0.403 [+0.065,+0.739] P0.99 (+1.164→+1.567) |
| R3 | rollm | s42 | log | -0.141 [-0.354,+0.066] P0.10 (+0.059→-0.083) | -0.258 [-0.489,-0.018] P0.02 (+0.840→+0.582) | +0.028 [-0.179,+0.219] P0.61 (+1.164→+1.192) |
| R4 | rollm | s42 | log | +0.049 [-0.081,+0.183] P0.77 (+0.059→+0.108) | -0.010 [-0.091,+0.065] P0.38 (+0.840→+0.830) | +0.083 [-0.001,+0.173] P0.97 (+1.164→+1.246) |
| R5 | rollm | s42 | log | +0.197 [-0.113,+0.529] P0.88 (+0.059→+0.256) | -0.035 [-0.347,+0.290] P0.42 (+0.840→+0.806) | +0.083 [-0.027,+0.197] P0.92 (+1.164→+1.247) |
| R1 | rollm | s2027 | log | -0.012 [-0.202,+0.169] P0.45 (+0.115→+0.103) | -0.059 [-0.383,+0.293] P0.36 (+0.895→+0.836) | -0.013 [-0.438,+0.427] P0.48 (+1.222→+1.209) |
| R2 | rollm | s2027 | log | -0.061 [-0.497,+0.340] P0.39 (+0.115→+0.055) | -0.111 [-0.423,+0.212] P0.26 (+0.895→+0.784) | +0.403 [+0.078,+0.718] P0.99 (+1.222→+1.625) |
| R3 | rollm | s2027 | log | -0.130 [-0.347,+0.080] P0.13 (+0.115→-0.015) | -0.235 [-0.466,-0.000] P0.03 (+0.895→+0.660) | -0.005 [-0.205,+0.188] P0.47 (+1.222→+1.218) |
| R4 | rollm | s2027 | log | +0.052 [-0.086,+0.181] P0.77 (+0.115→+0.167) | -0.036 [-0.118,+0.042] P0.20 (+0.895→+0.859) | +0.048 [-0.029,+0.131] P0.88 (+1.222→+1.270) |
| R5 | rollm | s2027 | log | +0.214 [-0.113,+0.582] P0.89 (+0.115→+0.330) | -0.046 [-0.369,+0.276] P0.39 (+0.895→+0.849) | +0.097 [-0.011,+0.212] P0.96 (+1.222→+1.319) |
| R1 | pinned | s42 | log | -0.107 [-0.303,+0.087] P0.15 (+0.084→-0.024) | +0.015 [-0.291,+0.351] P0.55 (+0.765→+0.781) | +0.083 [-0.385,+0.589] P0.66 (+1.225→+1.308) |
| R2 | pinned | s42 | log | -0.096 [-0.446,+0.267] P0.29 (+0.084→-0.013) | +0.015 [-0.284,+0.323] P0.55 (+0.765→+0.780) | +0.394 [+0.068,+0.726] P0.99 (+1.225→+1.619) |
| R3 | pinned | s42 | log | -0.238 [-0.463,-0.025] P0.02 (+0.084→-0.155) | -0.243 [-0.479,-0.001] P0.03 (+0.765→+0.522) | -0.000 [-0.191,+0.194] P0.50 (+1.225→+1.225) |
| R4 | pinned | s42 | log | -0.106 [-0.233,+0.018] P0.04 (+0.084→-0.022) | +0.030 [-0.048,+0.101] P0.78 (+0.765→+0.795) | +0.085 [-0.017,+0.192] P0.95 (+1.225→+1.310) |
| R5 | pinned | s42 | log | -0.009 [-0.257,+0.242] P0.48 (+0.084→+0.075) | -0.036 [-0.365,+0.281] P0.42 (+0.765→+0.730) | +0.078 [-0.026,+0.190] P0.92 (+1.225→+1.304) |
| R1 | pinned | s2027 | log | -0.103 [-0.318,+0.094] P0.15 (+0.136→+0.033) | +0.032 [-0.290,+0.374] P0.57 (+0.821→+0.853) | +0.102 [-0.346,+0.599] P0.68 (+1.268→+1.370) |
| R2 | pinned | s2027 | log | -0.115 [-0.458,+0.230] P0.27 (+0.136→+0.021) | -0.001 [-0.303,+0.314] P0.51 (+0.821→+0.820) | +0.428 [+0.090,+0.795] P0.99 (+1.268→+1.696) |
| R3 | pinned | s2027 | log | -0.257 [-0.481,-0.042] P0.01 (+0.136→-0.121) | -0.257 [-0.482,-0.022] P0.02 (+0.821→+0.564) | +0.002 [-0.196,+0.197] P0.50 (+1.268→+1.270) |
| R4 | pinned | s2027 | log | -0.098 [-0.241,+0.047] P0.10 (+0.136→+0.039) | +0.028 [-0.045,+0.103] P0.78 (+0.821→+0.849) | +0.094 [-0.007,+0.193] P0.97 (+1.268→+1.362) |
| R5 | pinned | s2027 | log | -0.016 [-0.266,+0.247] P0.47 (+0.136→+0.120) | -0.010 [-0.311,+0.306] P0.47 (+0.821→+0.811) | +0.070 [-0.046,+0.193] P0.90 (+1.268→+1.339) |
| R1 | rollm | s42 | prod | -0.027 [-0.201,+0.150] P0.38 (+0.068→+0.040) | -0.052 [-0.381,+0.266] P0.37 (+0.825→+0.772) | +0.075 [-0.364,+0.516] P0.62 (+1.206→+1.282) |
| R2 | rollm | s42 | prod | -0.103 [-0.552,+0.327] P0.33 (+0.068→-0.035) | -0.101 [-0.435,+0.229] P0.26 (+0.825→+0.724) | +0.471 [+0.114,+0.843] P0.99 (+1.206→+1.677) |
| R3 | rollm | s42 | prod | -0.162 [-0.376,+0.033] P0.06 (+0.068→-0.094) | -0.244 [-0.482,-0.004] P0.03 (+0.825→+0.581) | +0.077 [-0.117,+0.267] P0.79 (+1.206→+1.283) |
| R4 | rollm | s42 | prod | +0.052 [-0.076,+0.173] P0.79 (+0.068→+0.120) | -0.009 [-0.088,+0.070] P0.44 (+0.825→+0.816) | +0.041 [-0.026,+0.113] P0.88 (+1.206→+1.247) |
| R5 | rollm | s42 | prod | +0.254 [-0.060,+0.588] P0.94 (+0.068→+0.322) | +0.015 [-0.309,+0.344] P0.54 (+0.825→+0.839) | +0.072 [-0.046,+0.196] P0.88 (+1.206→+1.278) |
| R1 | rollm | s2027 | prod | -0.036 [-0.222,+0.148] P0.34 (+0.149→+0.114) | -0.027 [-0.342,+0.316] P0.44 (+0.896→+0.869) | +0.031 [-0.382,+0.475] P0.56 (+1.260→+1.291) |
| R2 | rollm | s2027 | prod | -0.121 [-0.548,+0.316] P0.30 (+0.149→+0.028) | -0.128 [-0.451,+0.207] P0.21 (+0.896→+0.768) | +0.457 [+0.087,+0.843] P0.99 (+1.260→+1.717) |
| R3 | rollm | s2027 | prod | -0.140 [-0.355,+0.061] P0.09 (+0.149→+0.009) | -0.229 [-0.465,+0.023] P0.03 (+0.896→+0.666) | +0.035 [-0.157,+0.228] P0.62 (+1.260→+1.294) |
| R4 | rollm | s2027 | prod | +0.052 [-0.079,+0.184] P0.78 (+0.149→+0.201) | -0.028 [-0.109,+0.047] P0.24 (+0.896→+0.868) | +0.042 [-0.042,+0.129] P0.84 (+1.260→+1.302) |
| R5 | rollm | s2027 | prod | +0.220 [-0.106,+0.561] P0.90 (+0.149→+0.369) | +0.011 [-0.304,+0.343] P0.54 (+0.896→+0.907) | +0.107 [-0.014,+0.238] P0.95 (+1.260→+1.367) |
| R1 | pinned | s42 | prod | -0.048 [-0.237,+0.126] P0.30 (+0.017→-0.031) | +0.036 [-0.281,+0.372] P0.58 (+0.765→+0.801) | +0.039 [-0.456,+0.562] P0.56 (+1.273→+1.312) |
| R2 | pinned | s42 | prod | -0.096 [-0.475,+0.285] P0.29 (+0.017→-0.078) | -0.034 [-0.344,+0.289] P0.39 (+0.765→+0.730) | +0.423 [+0.048,+0.779] P0.98 (+1.273→+1.696) |
| R3 | pinned | s42 | prod | -0.162 [-0.371,+0.049] P0.07 (+0.017→-0.145) | -0.247 [-0.487,-0.001] P0.02 (+0.765→+0.517) | +0.049 [-0.138,+0.229] P0.68 (+1.273→+1.322) |
| R4 | pinned | s42 | prod | -0.042 [-0.170,+0.089] P0.26 (+0.017→-0.024) | -0.010 [-0.085,+0.068] P0.39 (+0.765→+0.755) | -0.014 [-0.144,+0.100] P0.42 (+1.273→+1.259) |
| R5 | pinned | s42 | prod | +0.107 [-0.160,+0.393] P0.79 (+0.017→+0.124) | +0.007 [-0.305,+0.317] P0.50 (+0.765→+0.771) | +0.042 [-0.070,+0.158] P0.76 (+1.273→+1.315) |
| R1 | pinned | s2027 | prod | -0.032 [-0.218,+0.142] P0.35 (+0.083→+0.051) | +0.039 [-0.302,+0.381] P0.58 (+0.818→+0.857) | +0.058 [-0.489,+0.559] P0.60 (+1.306→+1.364) |
| R2 | pinned | s2027 | prod | -0.104 [-0.484,+0.284] P0.29 (+0.083→-0.021) | -0.076 [-0.376,+0.227] P0.31 (+0.818→+0.742) | +0.460 [+0.076,+0.834] P0.99 (+1.306→+1.765) |
| R3 | pinned | s2027 | prod | -0.165 [-0.392,+0.039] P0.06 (+0.083→-0.083) | -0.232 [-0.483,-0.013] P0.02 (+0.818→+0.586) | +0.068 [-0.111,+0.260] P0.77 (+1.306→+1.374) |
| R4 | pinned | s2027 | prod | -0.055 [-0.196,+0.081] P0.23 (+0.083→+0.028) | +0.010 [-0.069,+0.087] P0.59 (+0.818→+0.828) | +0.032 [-0.104,+0.160] P0.71 (+1.306→+1.338) |
| R5 | pinned | s2027 | prod | +0.109 [-0.168,+0.387] P0.78 (+0.083→+0.192) | +0.042 [-0.291,+0.340] P0.58 (+0.818→+0.860) | +0.066 [-0.061,+0.199] P0.84 (+1.306→+1.372) |

### Decisions (PREREG §2 frozen; PRIMARY = K1 rollm, window 2025->26; ADMIT iff both calibers × both seeds CI95 lower > 0 and Δturn ≤ +15%; REJECT iff any CI95 upper < 0; else UNDECIDED)

| rule | king | role | verdict | log/s42 Δ [CI] Δturn% | log/s2027 | prod/s42 | prod/s2027 |
|---|---|---|---|---|---|---|---|
| R1 | rollm | PRIMARY (frozen criteria) | **UNDECIDED** | -0.018 [-0.316,+0.284] -8.2% | -0.027 [-0.305,+0.264] -7.7% | +0.019 [-0.273,+0.315] -9.3% | +0.001 [-0.295,+0.324] -9.2% |
| R2 | rollm | PRIMARY (frozen criteria) | **UNDECIDED** | +0.134 [-0.099,+0.369] -31.5% | +0.111 [-0.120,+0.342] -31.2% | +0.149 [-0.116,+0.416] -33.8% | +0.126 [-0.122,+0.393] -33.5% |
| R3 | rollm | PRIMARY (frozen criteria) | **UNDECIDED** | -0.120 [-0.274,+0.046] +5.1% | -0.132 [-0.291,+0.029] +5.5% | -0.087 [-0.247,+0.071] +4.2% | -0.106 [-0.256,+0.052] +4.6% |
| R4 | rollm | PRIMARY (frozen criteria) | **UNDECIDED** | +0.047 [-0.007,+0.101] -4.2% | +0.013 [-0.042,+0.065] -4.5% | +0.021 [-0.029,+0.069] -2.6% | +0.009 [-0.047,+0.068] -2.9% |
| R5 | rollm | PRIMARY (frozen criteria) | **UNDECIDED** | +0.101 [-0.051,+0.261] -1.0% | +0.101 [-0.056,+0.265] -0.2% | +0.128 [-0.036,+0.312] -1.8% | +0.143 [-0.024,+0.318] -1.1% |
| R1 | pinned | SECONDARY (K0 pinned; not for selection) | **UNDECIDED** | +0.068 [-0.233,+0.379] -5.8% | +0.085 [-0.231,+0.400] -5.6% | +0.045 [-0.275,+0.371] -7.4% | +0.055 [-0.278,+0.379] -7.3% |
| R2 | pinned | SECONDARY (K0 pinned; not for selection) | **UNDECIDED** | +0.165 [-0.065,+0.404] -32.3% | +0.187 [-0.058,+0.422] -32.2% | +0.157 [-0.091,+0.421] -34.0% | +0.158 [-0.082,+0.426] -34.0% |
| R3 | pinned | SECONDARY (K0 pinned; not for selection) | **UNDECIDED** | -0.139 [-0.287,+0.018] +6.0% | -0.145 [-0.305,+0.013] +6.3% | -0.108 [-0.265,+0.049] +5.2% | -0.094 [-0.244,+0.068] +5.4% |
| R4 | pinned | SECONDARY (K0 pinned; not for selection) | **UNDECIDED** | +0.041 [-0.020,+0.105] -2.8% | +0.047 [-0.014,+0.112] -3.1% | -0.033 [-0.105,+0.037] -1.0% | +0.001 [-0.079,+0.073] -1.4% |
| R5 | pinned | SECONDARY (K0 pinned; not for selection) | **UNDECIDED** | +0.091 [-0.066,+0.256] +1.1% | +0.098 [-0.071,+0.272] +1.9% | +0.106 [-0.061,+0.278] +0.4% | +0.139 [-0.034,+0.317] +1.0% |

## 3. Reading (INFERRED from §2 unless marked VERIFIED)

### 3.0 Units chain (printed by script, §5 command)
```
Δ +0.05 bps/anchor per unit NAV  ×2190 anchors/yr = +109.5 bps/yr = +1.095 %/yr per unit NAV at replay gross ≈0.63×NAV; scaled to live gross 2.0×NAV (×3.17) ≈ +3.48 %/yr of NAV
Δ +0.10 bps/anchor per unit NAV  ×2190 anchors/yr = +219.0 bps/yr = +2.190 %/yr per unit NAV at replay gross ≈0.63×NAV; scaled to live gross 2.0×NAV (×3.17) ≈ +6.95 %/yr of NAV
Δ +0.15 bps/anchor per unit NAV  ×2190 anchors/yr = +328.5 bps/yr = +3.285 %/yr per unit NAV at replay gross ≈0.63×NAV; scaled to live gross 2.0×NAV (×3.17) ≈ +10.43 %/yr of NAV
```
(net_ex is per unit NAV of the replay book whose 2025→26 mean gross is 0.62–0.67; the CI half-widths on 2025→26 are ±0.15 to ±0.3 bps/anchor for R1/R2/R3/R5 and ±0.05 for R4.)

### 3.1 R1 (LOOK 300) — nothing, and a noisier seat
Δ ≈ 0 in every cell (K1: −0.03 to +0.02; K0: +0.05 to +0.09; CIs ±0.3). The shorter window makes the seat jump: 2025→26 switches 79 vs 23 (K1 log), jumps 82 vs 2, seat_turn 0.0122 vs 0.0042; the king seat is 0.10 lower on average and touches 0 and 1. The auxiliary 2026≤08-10 window is negative in all K1 cells (−0.12 to −0.20, CI upper +0.05 to +0.14). Book turnover −8 to −9%.

### 3.2 R2 (net-of-turnover msharpe) — a fund tilt in disguise; gain confined to the high-σ_fund tercile
- Mechanism (VERIFIED, `judge.log` R2 table): the king rank book churns 0.55–0.63 of its gross per anchor (re-ranked every anchor, no EMA), rev24 0.54–0.60, fund 0.03–0.045. With κ = 3.52 the deduction is 1.93–2.22 bps/anchor for king and 0.10–0.16 for fund, so on 2025→26 the king leg raw mean goes +2.62 → +0.68 (K1 log; K0 +2.65 → +0.69) while fund goes +3.08 → +2.97: the rule removes 74% of the king leg return and 4% of the fund leg return. The msharpe seat therefore drops the king from 0.557 to 0.343 (K1 log; K0 0.549 → 0.321) and book turnover falls 31–34%.
- Book level: positive in all 8 cells (K1 +0.11 to +0.15, K0 +0.16 to +0.19; P 0.81–0.93), never CI > 0 on 2025→26. σ_fund terciles (descriptive, 2024→26): high +0.39 to +0.47 with CI95 lower > 0 in **8/8** cells; low −0.04 to −0.12 and mid −0.05 to −0.13 (CIs include 0). ΔSharpe 2025→26 +0.09 to +0.27; maxDD 2025→26 slightly worse in 6/8 cells (e.g. 801 → 835 bps K1 log s42).
- Reading: what R2 buys is "less king, more fund", which pays when the fund leg is strong (high σ_fund) and costs otherwise — the same regime dependence as the fund leg itself. Caveat on the pre-registered κ: 3.52 bps is the book-level cost line (turnover after EMA 0.1 + band, ≈0.031 gross/anchor in these arms), but the device applies it to the leg rank-book turnover, a proxy ≈ 18× larger; the arm is exactly as pre-registered, and its interpretation is "a heavy fixed penalty on the leg that re-ranks fastest", not a cost-accurate seat.

### 3.3 R3 (shrink 0.5 to equal weight) — negative in 8/8 cells; the closest to a rejection
K1 2025→26 −0.09 to −0.13 (P 0.06–0.14), K0 −0.09 to −0.15 (P 0.04–0.14); 2024→26 CI95 upper < 0 in 5 of 8 cells (log: all four; prod: pinned s42); the auxiliary 2026≤08-10 window CI95 upper < 0 in 6 of 8 cells; σ_fund mid tercile −0.23 to −0.26 with CI95 upper < 0 in **8/8** cells. Mechanism: the shrink halves the responsiveness of the seat (seat_turn 0.0021 vs 0.0042, jumps 0 vs 2) and floors the king seat at ≥ 0.35 when msharpe wants less (min 0.346 vs 0.192 over 2025→26; 2026 mean 0.427 vs 0.354), while raising book turnover 4–6%. Under the frozen rule it is UNDECIDED only because the primary-window CI upper bounds are +0.03 to +0.07; on every other reading it hurts.

### 3.4 R4 (2-leg mean-variance) — numerically R0
With two weakly correlated legs the ridge-regularised Σ⁻¹μ is close to μ/σ², so the seat differs from R0 by −0.02 on average (2025→26 min/max 0.12–1.00 vs 0.19–1.00). Δ: K1 +0.01 to +0.05 (log s42 P 0.95, the others 0.62–0.81), K0 −0.03 to +0.05; turnover −3 to −5% (K1). The only CI > 0 cells are in the auxiliary 2026≤08-10 window (K1 log s42 +0.123 [+0.015, +0.240]; K0 log s2027 +0.131 [+0.012, +0.247]) and the prod caliber does not confirm them. Nothing to gain and nothing to lose.

### 3.5 R5 (σ_fund-tercile regime) — the best-looking numbers, produced by a 256-anchor episode
- Numbers: positive in 8/8 cells (K1 +0.10 to +0.14, P 0.89–0.95; K0 +0.09 to +0.14, P 0.87–0.95); ΔSharpe 2025→26 +0.30 to +0.40 (K1: 2.51/2.60/2.54/2.64 → 2.81/2.90/2.88/3.02); maxDD 2025→26 lower by 100–130 bps in all 8 cells; turnover −2% to +2%; the 2025 calendar window has CI95 lower > 0 in 3 of 8 cells (K0 log s42 +0.121 [+0.010, +0.246], K0 prod s42 +0.141 [+0.017, +0.275], K0 prod s2027 +0.167 [+0.038, +0.307]) and 2026≤08-10 is ≈ 0 everywhere (−0.06 to +0.06, CIs ±0.4).
- How the rule actually behaves (VERIFIED, `logs/r5_window_diag.log`, script `r5_window_diag.py`): under the causal expanding cuts, the 2022–23 history (mean σ_fund ≈ 3–5 bps/8h) dominates the quantiles, so of the 5838 anchors since 2024, 4043 are classified "high", 1242 "mid", 553 "low"; the fallback fired on 0.15% of evaluated anchors (2022 only). In **2025→26 there is no low-tercile anchor at all**: 3386 anchors are "high" (window mean age 585 anchors, 1.2% before 2024; R5 king seat 0.520 vs R0 0.563; Δ +0.05) and **256 are "mid"** (window mean age 2161 anchors = the mid-σ anchors of 2024, 0% before 2024; R5 king seat **0.995** vs R0 0.49; Δ **+0.73** bps/anchor). Those 256 anchors (7% of the window) contribute 187 of the 357 bps of total 2025→26 Δ (K1 log s42); the same split holds for prod and for K0 (mid n = 256, w_king 0.994–0.998, Δ +0.74 / +0.92). In 2024 the high-tercile anchors (657, window 63% pre-2024 where the king leg is empty) show Δ −0.34 (K1 log) / −0.29 (prod) / −0.37 (K0).
- Reading: the gain is "when σ_fund dips to the 2024-like band, remember that in 2024 fund was negative and king was not, and go all-in king". It worked once (2025→26 mid anchors) and it is one episode with n = 256; the rule also makes the seat jump (switches 27 vs 23, jumps 22 vs 2, seat_turn 0.0071 vs 0.0042 on 2025→26; 159 switches vs 101 over 2024→26). Not a candidate on this evidence; if the regime idea is pursued, the tercile definition must not be an expanding quantile over a history in which the king leg did not exist.

### 3.6 Cross-checks
- K0 pinned reproduces the K1 ranking of rules (R2 > R5 > R4 ≈ R1 > R3 by point estimate), so nothing above depends on the rolling king.
- The two calibers agree in sign for every rule and cell.
- PREREG §3 cross-check (K_best × R_best): not run — there is no ADMIT candidate on this axis.

## 4. What was not verified / open risks (executor view)
- **Single instrument** (pod port device, [单仪器 pod]); jpline was down, so no second implementation of the book chain saw these arms. The device default path is bitwise the port, but the new seat branches have no independent re-implementation (they are 60 lines of numpy; the diff is in §7 for review).
- **Resolution**: the frozen gate cannot resolve effects of the size observed (≈ 0.1 bps/anchor) on 3642 anchors; UNDECIDED here means "not measurable", not "zero". A rule with a true +0.1 would need roughly 4× the anchors to clear CI95 > 0 at these variances.
- **R2 κ semantics**: κ = 3.52 was priced at book-level turnover but applied to leg rank-book turnover (pre-registered as such); the arm answers "does a heavy penalty on the fast leg help", not "does cost-accurate seating help".
- **R5 tercile partition** inside the rule (causal expanding) and in the σ_fund Δ table (descriptive 2024→26) are different partitions; both are stated, neither was tuned.
- **R4 after-mask ordering** was never run (AMENDMENT 1); the reported R4 is the 2-leg solve only.
- **Seat "switch" formula** is mine (frozen before numbers); the prereg names the quantity but not the formula.
- The 2024 window for dynamic seats still carries the king-empty 2022–23 warm-up in every rule; 2024 numbers are auxiliary only (PREREG §0.4).
- No arm was added, removed, re-parameterised or re-run after any number was seen; the four smoke runs are the real arms (identical env to the queued ones).

## 5. Verbatim commands (non-arm)
```
# layout (pod), receipts in setup_dev.log
ssh pod2 'ROOT=/workspace/review_scratch/cadence_seats/axisB; for v in dev dev_alt; do d=$ROOT/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs; ... ln -sfn (see setup_dev.log for the resolved targets) ...; done'
# device diff (Mac)
diff -u w10_universe_recheck.py w10_universe_seats.py > device.diff
# equivalence / smoke runs (pod, 23:35:37Z), then the queue and the chained judge
for a in "R0 pinned log 42" "R2 rollm log 42" "R4 rollm log 42" "R5 rollm log 42"; do nohup bash run_axisB.sh $a > logs/launch_$(echo $a | tr " " _).out 2>&1 & done
nohup flock -n logs/run_all.lock bash run_all.sh > logs/run_all.out 2>&1 &
nohup bash chain_judge.sh > logs/chain_judge.out 2>&1 &      # = until RUN_ALL_DONE; python check_equiv.py > logs/check_equiv.log; python judge_axisB.py > logs/judge.log
/workspace/venv/bin/python check_equiv.py      # ALL_EQUIV True n 10
/workspace/venv/bin/python judge_axisB.py      # judge.json + REPORT_tables.md
/workspace/venv/bin/python r5_window_diag.py   # logs/r5_window_diag.log
# units chain (Mac): python3 - <<PY ... d*2190 ... PY  (output quoted in §3.0)
```

## 6. Verbatim arm commands (`logs/commands.txt`, 48 CMD + 48 END lines)
```
CMD[R2_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:35:37Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe_net LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:35:37Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R5_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:35:37Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=regime LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R4_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:35:37Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=meanvar LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_pinned_log_s42] rc=0 2026-09-04T23:38:13Z
END[R2_rollm_log_s42] rc=0 2026-09-04T23:38:17Z
END[R4_rollm_log_s42] rc=0 2026-09-04T23:38:20Z
END[R5_rollm_log_s42] rc=0 2026-09-04T23:38:34Z
QUEUE 44 arms 2026-09-04T23:46:15Z
CMD[R0_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R0_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:46:15Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_rollm_log_s2027] rc=0 2026-09-04T23:48:52Z
CMD[R0_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:48:53Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R0_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_pinned_log_s2027] rc=0 2026-09-04T23:48:53Z
CMD[R1_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:48:53Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=300 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_rollm_prod_s2027] rc=0 2026-09-04T23:48:56Z
CMD[R1_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:48:56Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=300 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_rollm_prod_s42] rc=0 2026-09-04T23:48:57Z
END[R0_rollm_log_s42] rc=0 2026-09-04T23:48:57Z
CMD[R1_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:48:57Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=300 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R1_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:48:57Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe LOOK=300 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_pinned_prod_s42] rc=0 2026-09-04T23:48:58Z
CMD[R1_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:48:58Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=300 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_rollm_prod_s42] rc=0 2026-09-04T23:51:31Z
END[R1_rollm_log_s2027] rc=0 2026-09-04T23:51:31Z
CMD[R1_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:51:31Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=300 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_rollm_prod_s2027] rc=0 2026-09-04T23:51:31Z
CMD[R1_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:51:31Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=300 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R1_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:51:31Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=300 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R1_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_rollm_log_s42] rc=0 2026-09-04T23:51:32Z
CMD[R2_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:51:32Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe_net LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_pinned_log_s42] rc=0 2026-09-04T23:51:32Z
CMD[R2_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:51:32Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe_net LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R0_pinned_prod_s2027] rc=0 2026-09-04T23:51:33Z
CMD[R2_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:51:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=msharpe_net LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R2_rollm_log_s2027] rc=0 2026-09-04T23:53:25Z
CMD[R2_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe_net LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_pinned_prod_s42] rc=0 2026-09-04T23:53:25Z
CMD[R2_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe_net LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_pinned_prod_s2027] rc=0 2026-09-04T23:53:25Z
CMD[R2_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe_net LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R1_pinned_log_s2027] rc=0 2026-09-04T23:53:25Z
CMD[R2_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe_net LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R2_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R2_rollm_prod_s2027] rc=0 2026-09-04T23:53:25Z
CMD[R3_rollm_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=shrink LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_rollm_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R2_rollm_prod_s42] rc=0 2026-09-04T23:53:25Z
CMD[R3_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:25Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=shrink LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R2_pinned_log_s42] rc=0 2026-09-04T23:53:59Z
CMD[R3_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=shrink LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R2_pinned_prod_s42] rc=0 2026-09-04T23:53:59Z
END[R2_pinned_prod_s2027] rc=0 2026-09-04T23:53:59Z
CMD[R3_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=shrink LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R3_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=shrink LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_rollm_log_s2027] rc=0 2026-09-04T23:53:59Z
END[R2_pinned_log_s2027] rc=0 2026-09-04T23:53:59Z
CMD[R3_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=shrink LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
CMD[R3_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=shrink LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_rollm_log_s42] rc=0 2026-09-04T23:53:59Z
CMD[R3_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:53:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=shrink LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R3_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_rollm_prod_s42] rc=0 2026-09-04T23:54:32Z
CMD[R4_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:54:32Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=meanvar LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_rollm_prod_s2027] rc=0 2026-09-04T23:54:33Z
CMD[R4_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:54:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=meanvar LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_pinned_prod_s42] rc=0 2026-09-04T23:54:33Z
CMD[R4_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:54:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=meanvar LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_pinned_log_s42] rc=0 2026-09-04T23:54:33Z
CMD[R4_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:54:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=meanvar LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_pinned_prod_s2027] rc=0 2026-09-04T23:54:33Z
CMD[R4_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:54:33Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=meanvar LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R3_pinned_log_s2027] rc=0 2026-09-04T23:54:34Z
CMD[R4_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:54:34Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=meanvar LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_rollm_log_s2027] rc=0 2026-09-04T23:56:52Z
CMD[R4_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:56:52Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=meanvar LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R4_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_rollm_prod_s42] rc=0 2026-09-04T23:56:53Z
CMD[R5_rollm_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:56:53Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=regime LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_rollm_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_pinned_log_s2027] rc=0 2026-09-04T23:56:56Z
CMD[R5_rollm_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:56:56Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=regime LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_rollm_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_rollm_prod_s2027] rc=0 2026-09-04T23:56:56Z
CMD[R5_rollm_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:56:56Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/review_scratch/rolling_king/slow_pred_rollm.npy WRULE=regime LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_rollm_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_pinned_prod_s42] rc=0 2026-09-04T23:56:56Z
CMD[R5_pinned_log_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:56:56Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=regime LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_pinned_log_s42] rc=0 2026-09-04T23:56:59Z
CMD[R5_pinned_log_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev) 2026-09-04T23:56:59Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=regime LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R4_pinned_prod_s2027] rc=0 2026-09-04T23:59:37Z
CMD[R5_pinned_prod_s42] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:59:37Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=regime LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_seats.py
END[R5_pinned_log_s42] rc=0 2026-09-04T23:59:44Z
CMD[R5_pinned_prod_s2027] (cwd=/workspace/review_scratch/cadence_seats/axisB/dev_alt) 2026-09-04T23:59:45Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=regime LOOK=900 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=R5_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_seats.py
END[R5_pinned_log_s2027] rc=0 2026-09-04T23:59:45Z
END[R5_rollm_prod_s42] rc=0 2026-09-04T23:59:46Z
END[R5_rollm_log_s2027] rc=0 2026-09-04T23:59:47Z
END[R5_rollm_prod_s2027] rc=0 2026-09-04T23:59:48Z
END[R5_pinned_prod_s42] rc=0 2026-09-05T00:02:16Z
END[R5_pinned_prod_s2027] rc=0 2026-09-05T00:02:18Z
RUN_ALL_DONE 2026-09-05T00:02:18Z
```

## 7. Device diff (`w10_universe_recheck.py` → `w10_universe_seats.py`; `device.diff`)
```diff
--- w10_universe_recheck.py	2026-09-05 07:29:17
+++ w10_universe_seats.py	2026-09-05 07:33:31
@@ -13,7 +13,14 @@
 """
 import json, time, sys, os
 LOOK = int(os.environ.get("LOOK", "900"))          # 腿权重回看窗(锚)
-WRULE = os.environ.get("WRULE", "msharpe")            # msharpe | eq | iv
+WRULE = os.environ.get("WRULE", "msharpe")            # msharpe | eq | iv | axisB seat rules (PREREG_retrain_cadence_and_seat_rule_2026-09-05 §2): msharpe_net(R2) | shrink(R3) | meanvar(R4) | regime(R5)
+assert WRULE in ("msharpe", "eq", "iv", "msharpe_net", "shrink", "meanvar", "regime"), f"WRULE 白名单外: {WRULE}"
+# ── axisB seat-rule parameters: pre-registered single values (asserted), self-reported in _CFG["AXISB"]; msharpe/eq/iv code paths are untouched
+KAPPA_TURN = float(os.environ.get("KAPPA_TURN", "3.52")); assert KAPPA_TURN == 3.52, f"KAPPA_TURN 白名单外: {KAPPA_TURN}"   # R2: bps per unit turnover (换手成本复审线 3.52)
+SHRINK_LAMBDA = 0.5      # R3: w = λ·prior + (1−λ)·msharpe(LOOK); prior = equal weight over LEGS-allowed legs
+MV_RIDGE = 1e-3          # R4: ridge = MV_RIDGE · trace(Σ)/n_legs (= mean diagonal variance)
+MV_MASK_ORDER = os.environ.get("MV_MASK_ORDER", "first"); assert MV_MASK_ORDER in ("first", "after"), MV_MASK_ORDER   # R4: first = solve over LEGS-allowed legs only (default); after = 3-leg solve then LEGS mask
+REGIME_LOOK = 900; REGIME_MIN = 300   # R5: msharpe over the most recent 900 anchors in the same causal σ_fund tercile as t; <300 such anchors ⇒ plain msharpe(LOOK)
 CAL = os.environ.get("CAL", "simple")                 # simple = 交易所记账(y -> expm1)
 assert CAL in ("simple", "log"), (
     f"CAL 必须是 simple|log(收到 {CAL!r})。simple=交易所简单收益(expm1), log=对数收益(仅诊断用)。"
@@ -43,10 +50,19 @@
 REF_SKIP = int(os.environ.get("REF_SKIP", "0")); assert REF_SKIP in (0, 1)   # combo_recheck 2026-09-04: 1 = skip pod_backup reference parity (port stubs are 144-byte placeholders); self-reported in _CFG
 _CFG = {"REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10, "KMOD_L": KMOD_L, "KMOD_AGREE": KMOD_AGREE, "SEATF10": SEATF10, "KTAIL": KTAIL, "KMOD": KMOD, "SEATNET": SEATNET, "FUNDSCALE": FUNDSCALE, "FEMAT_NPZ": FEMAT_NPZ, "SLOW_NPY": os.environ.get("SLOW_NPY"), "W3FIX": W3FIX, "MEMBERS_TOPN": MEMBERS_TOPN, "TRADE_TOPN": TRADE_TOPN, "FTRIM": FTRIM, "UMASK_NPZ": os.environ.get("UMASK_NPZ"), "LOOK": LOOK, "WRULE": WRULE, "CAL": CAL, "LEGS": LEGS, "PHI": PHI, "FSEED": FSEED,
         "FPRED": os.environ.get("FPRED", "(default f10_V2MAIN_s{FSEED})")}
+import hashlib as _hl
+_CFG["AXISB"] = {"device": "w10_universe_seats.py = w10_universe_recheck.py + axisB seat-rule branches (R2..R5 in w3_at via axisb_w3) + per-leg unit-gross rank-book turnover recorded in legs()",
+                 "device_sha256": _hl.sha256(open(__file__, "rb").read()).hexdigest(),
+                 "rule": WRULE, "look": LOOK, "kappa_turn_bps": KAPPA_TURN, "shrink_lambda": SHRINK_LAMBDA, "mv_ridge_frac": MV_RIDGE, "mv_mask_order": MV_MASK_ORDER,
+                 "regime_look": REGIME_LOOK, "regime_min": REGIME_MIN,
+                 "regime_sigma_def": "per anchor: std (ddof=0) over META members with finite f_fund_now of f_fund_now*8/ivf *1e4 (bps/8h; ivf = f_fund_iv if finite&>0 else 8), NaN if <50 finite; trailing 30-anchor mean (>=15 valid) over the legs() anchor sequence; tercile cuts = expanding 33.33/66.67 percentiles over anchors strictly before t (causal)",
+                 "turn_def": "turn_j,t = sum over all 829 names of |z_j,t/g_j,t - z_j,t-1/g_j,t-1| (non-members = 0; g<=1e-9 ⇒ empty book); z/g = the leg's unit-gross rank book exactly as used for the leg return in legs()",
+                 "warmup": "p<LOOK -> [1/3,1/3,1/3] for every rule (inherited from the msharpe path, unchanged)"}
 print("CONFIG " + json.dumps(_CFG), flush=True)   # E-0826-C/D: 装置必须自报全部生效配置
 t0 = time.time()
 MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
 E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]
+MEMBERS_META = MT["members"]   # axisB R5: σ_fund is defined over the META members (judge.py definition), independent of MEMBERS_TOPN
 if MEMBERS_TOPN > 0:   # 扩展臂: 逐锚按当锚 qvk 排名取前 N(era-synchronous: 只用当锚已知的报价额), 与 meta 排序口径同源
     _mem2 = np.empty(len(E_ts), dtype=object)
     for _i in range(len(E_ts)):
@@ -120,6 +136,7 @@
     return t
 def legs(SLOW):
     LR = {l: [] for l in ("king", "rev24", "fund", "f10")}; idx = []
+    TURN = {l: [] for l in ("king", "rev24", "fund")}; _prevb = {l: np.zeros(NW) for l in TURN}   # axisB R2: per-leg unit-gross rank-book turnover
     for i in range(nA):
         j = pw_row.get(int(E_ts[i]))
         if j is None: continue
@@ -139,8 +156,57 @@
             if SEATNET and g > 1e-9:   # X1: 减去该腿单位 gross 书的 4h carry(多头付正费率), bps
                 _lr -= float((z / g * np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / _IVf[j, m])).sum() * 1e4)
             LR[leg].append(_lr)
+            if leg in TURN:   # axisB: turnover of this leg's own unit-gross rank book t-1 -> t (full 829-vector, non-members = 0; g<=1e-9 ⇒ empty book); _lr above is untouched
+                _zb = np.zeros(NW)
+                if g > 1e-9: _zb[m] = z / g
+                TURN[leg].append(float(np.abs(_zb - _prevb[leg]).sum())); _prevb[leg] = _zb
         idx.append(i)
-    return {k: np.array(v) for k, v in LR.items()}, {int(i): p for p, i in enumerate(idx)}
+    _out = {k: np.array(v) for k, v in LR.items()}
+    for l in TURN: _out["turn_" + l] = np.array(TURN[l])
+    return _out, {int(i): p for p, i in enumerate(idx)}
+# ── axisB seat rules (R2..R5). The msharpe/eq/iv paths inside w3_at are byte-for-byte the original; these helpers are only reached for the new WRULE values.
+AXISB_RULES = ("msharpe_net", "shrink", "meanvar", "regime")
+_LEGMSK = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
+def _msharpe_w(r):   # exact copy of the production msharpe algebra in w3_at (shp -> normalise -> LEGS mask -> renormalise)
+    shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
+    w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
+    if LEGS != "111":
+        msk = np.array([1.0 if c == "1" else 0.0 for c in LEGS])
+        w_ = w_ * msk
+        w_ = w_ / w_.sum() if w_.sum() > 1e-12 else msk / max(msk.sum(), 1.0)
+    return w_
+SIG_RAW = SIG_ROLL = REG_TER = REG_FB = None   # filled after legs(): σ_fund series over the legs() sequence; R5 tercile / fallback flags per position (-1 = not evaluated)
+def axisb_w3(LRa, p, sl, r):
+    if WRULE == "msharpe_net":      # R2: r_j,t − κ·turn_j,t (bps) in place of r_j,t, then the production msharpe algebra over the same LOOK window
+        rn = r - KAPPA_TURN * np.stack([LRa["turn_king"][sl], LRa["turn_rev24"][sl], LRa["turn_fund"][sl]])
+        return _msharpe_w(rn)
+    if WRULE == "shrink":           # R3: λ·prior + (1−λ)·msharpe(LOOK); prior = equal weight over LEGS-allowed legs (LEGS=101 -> [0.5,0,0.5])
+        prior = _LEGMSK / max(_LEGMSK.sum(), 1.0)
+        return SHRINK_LAMBDA * prior + (1.0 - SHRINK_LAMBDA) * _msharpe_w(r)
+    if WRULE == "meanvar":          # R4: w ∝ clip((Σ + ridge·I)^-1 μ, 0); Σ (np.cov, ddof=1), μ over the LOOK window; ridge = MV_RIDGE·trace(Σ)/n; all-zero ⇒ equal weight
+        if MV_MASK_ORDER == "first":
+            ia = np.where(_LEGMSK > 0)[0]; rs = r[ia]
+        else:
+            ia = np.arange(3); rs = r
+        mu = rs.mean(1); S = np.atleast_2d(np.cov(rs)); ridge = MV_RIDGE * np.trace(S) / len(ia)
+        w = np.clip(np.linalg.solve(S + ridge * np.eye(len(ia)), mu), 0.0, None)
+        if w.sum() <= 1e-12: w = np.ones(len(ia))
+        w = w / w.sum(); out = np.zeros(3); out[ia] = w
+        if MV_MASK_ORDER == "after":
+            out = out * _LEGMSK; out = out / out.sum() if out.sum() > 1e-12 else _LEGMSK / max(_LEGMSK.sum(), 1.0)
+        return out
+    if WRULE == "regime":           # R5: msharpe over the most recent REGIME_LOOK anchors (strictly before t) whose causal σ_fund tercile equals t's; <REGIME_MIN ⇒ plain msharpe(LOOK)
+        hist = SIG_ROLL[:p]; fin = np.isfinite(hist); cur = SIG_ROLL[p]; REG_FB[p] = 1; REG_TER[p] = -1
+        if fin.sum() >= REGIME_MIN and np.isfinite(cur):
+            q1, q2 = np.percentile(hist[fin], [100.0 / 3, 200.0 / 3])     # expanding causal cut points (anchors < t only)
+            th = np.where(hist <= q1, 0, np.where(hist <= q2, 1, 2)); th[~fin] = -1
+            tc = 0 if cur <= q1 else (1 if cur <= q2 else 2); REG_TER[p] = tc
+            same = np.where(th == tc)[0]
+            if len(same) >= REGIME_MIN:
+                sel = same[-REGIME_LOOK:]; REG_FB[p] = 0
+                return _msharpe_w(np.stack([LRa["king"][sel], LRa["rev24"][sel], LRa["fund"][sel]]))
+        return _msharpe_w(r)
+    raise AssertionError(WRULE)
 W3FC = None
 def run(SLOW, LRa, pos, depth, need, cool, look=900):
     def w3_at(i):
@@ -165,6 +231,8 @@
         if WRULE == "iv":
             iv = 1.0 / (r.std(1) + 1e-9)
             return iv / iv.sum()
+        if WRULE in AXISB_RULES:   # axisB R2..R5 (same warm-up and same LOOK-window slice `sl` as msharpe; only the seat algebra differs)
+            return axisb_w3(LRa, p, sl, r)
         shp = np.maximum(r.mean(1) / (r.std(1) + 1e-9), 0.0)
         w_ = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
         if LEGS != "111":
@@ -317,6 +385,26 @@
         if i % 2000 == 0: print("run depth", depth, i, "/", nA, round(time.time() - t0, 1), "s", flush=True)
     return np.array(rec), np.stack(WS)
 LRa, pos = legs(SLOW); print("legs done", round(time.time() - t0, 1), "s", flush=True)
+# ── axisB: σ_fund series over the legs() anchor sequence (R5 state; judge.py definition over META members) + per-leg turnover diagnostics (R2)
+_idxL = np.array(sorted(pos, key=pos.get)); _yrsL = yrs[_idxL]; _YL = sorted(set(_yrsL.tolist()))
+def _sigma_fund_series(idxs):
+    raw = []
+    for i in idxs:
+        j = pw_row[int(E_ts[i])]; m = MEMBERS_META[i]; f = FN[j, m]; iv = IV[j, m]; ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0); ok = np.isfinite(f)
+        raw.append(float(np.std(f[ok] * 8.0 / ivf[ok]) * 1e4) if ok.sum() >= 50 else np.nan)
+    raw = np.array(raw); roll = np.full(len(raw), np.nan)
+    for p in range(len(raw)):
+        w = raw[max(0, p - 29):p + 1]; v = w[np.isfinite(w)]
+        if len(v) >= 15: roll[p] = v.mean()
+    return raw, roll
+SIG_RAW, SIG_ROLL = _sigma_fund_series(_idxL); REG_TER = np.full(len(_idxL), -1, np.int8); REG_FB = np.full(len(_idxL), -1, np.int8)
+print(f"AXISB sigma_fund: n {len(SIG_RAW)} finite raw {int(np.isfinite(SIG_RAW).sum())} roll {int(np.isfinite(SIG_ROLL).sum())} mean roll {np.nanmean(SIG_ROLL):.3f} bps/8h", flush=True)
+for _l in ("king", "rev24", "fund"):
+    _t = LRa["turn_" + _l]
+    print(f"AXISB turn_{_l} yearly mean (unit gross/anchor): " + " ".join(f"{int(y)}={_t[_yrsL == y].mean():.4f}" for y in _YL) + f" | all={_t.mean():.4f}", flush=True)
+    if WRULE == "msharpe_net":
+        print(f"AXISB R2 deduction κ·turn_{_l} (bps/anchor) yearly mean: " + " ".join(f"{int(y)}={KAPPA_TURN * _t[_yrsL == y].mean():.4f}" for y in _YL)
+              + f" | all={KAPPA_TURN * _t.mean():.4f}; leg r mean {LRa[_l].mean():+.4f} -> net {(LRa[_l] - KAPPA_TURN * _t).mean():+.4f}", flush=True)
 ARMS = [("S0", None, 0, 0, "nets_histv2_0_0_0.npy"), ("d30_n2_c42", -0.30, 2, 42, "nets_histv2_-30_2_42.npy")]
 COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
 out = {}; save = {}
@@ -357,6 +445,12 @@
     print("RECEIPT_EX", nm, json.dumps(outx), flush=True)
     save[f"{nm}_rec"] = R
     save[f"{nm}_W"] = WS
+if WRULE == "regime":   # axisB R5: fallback frequency by year over evaluated anchors (p >= LOOK); tercile counts of evaluated anchors
+    _ev = REG_FB >= 0
+    print("AXISB R5 fallback share by year (evaluated anchors): " + " ".join(f"{int(y)}={REG_FB[_ev & (_yrsL == y)].mean():.3f}(n{int((_ev & (_yrsL == y)).sum())})" for y in _YL if (_ev & (_yrsL == y)).any())
+          + f" | all={REG_FB[_ev].mean():.3f}; tercile counts 2024+: {[int(((REG_TER == t) & (_yrsL >= 2024)).sum()) for t in range(3)]}", flush=True)
+save["axisb_legs_ts"] = E_ts[_idxL]; save["axisb_legs_r"] = np.stack([LRa["king"], LRa["rev24"], LRa["fund"]]); save["axisb_turn"] = np.stack([LRa["turn_king"], LRa["turn_rev24"], LRa["turn_fund"]])
+save["axisb_sigma_raw"] = SIG_RAW; save["axisb_sigma_roll"] = SIG_ROLL; save["axisb_regime_tercile"] = REG_TER; save["axisb_regime_fallback"] = REG_FB
 _OT = os.environ.get("OUT_TAG", "")   # 并行道输出隔离(PREREG_universe_dyn): 未设时文件名与旧装置同
 _OT = f"_{_OT}" if _OT else ""
 json.dump(out, open(f"{PD}/w10_ablation_summary{_OT}.json", "w"), indent=1, ensure_ascii=False)
```

## 8. SHA256SUMS (pod, `/workspace/review_scratch/cadence_seats/axisB/`)
```
944fa277c074059e7629b9cc2bddc911117b899ab7576212b4e480b7c5c7cfc1  w10_universe_seats.py
6f31b80930b342ca8ab54c01bb7893dda616978066beb23a585d00f95fb34959  device.diff
fc4f8305e895ad3c4f547febeb701b6ed9e5a007ee70eaa1d9d3fb01f7fe66ed  run_axisB.sh
7b976b0f6249f098363eca277fb8695f19deb87c553ee06f4e7578ccc0dcf974  run_all.sh
f9323402258ab012d6ef0d7b4ab4b741a34a0c4ed4ff800471b0104d41209ec8  chain_judge.sh
cb0e59d9a0dab6082d5e136add0f385cf0ce0aab794c62e2a2f586bc5cdf1a03  check_equiv.py
650839553ca82a40cb05ad627502af6caf305c2404e97065348403b5f77d9605  judge_axisB.py
22f64356cf65cf9c56d984c681aedb1789f1eecd2d0430591fa34c9d8454a345  r5_window_diag.py
f4e1f7e663ba954b97928f4073bd918665399e00918fde031900fb692b3af31f  judge.json
bee7a7f13e28e5718605f315cb983a790bd23c4ae1192dfd20497fa86ea9d9d1  REPORT_tables.md
79a032187cb69d77073159f717410b413db7de92fd15c944619f51af7c56a0c7  head.txt
02acac5bc2a786a78df2735f11b010c8d41223269adde0d0a0f13ea7470b29f0  tail.txt
e5dc7e3637923636edd7722e2c6490b92fdc824b74814699cfa7278493dbcf5f  logs/commands.txt
e12ceaac553b686e12d991cba7d3ef1199fab5148003a9fe72cceeb978405541  logs/judge.log
6cad8806c27338fbc84dcf3bd38db434ef1744936fb8e5ee4dc9b8ad75073dbd  logs/check_equiv.log
0d1d409426c6bb17005f63aae2e7e7ee78d18621a7b813fd9f425279b4d2e3a2  logs/r5_window_diag.log
e459a73778f9dc2556a1f8a4bfc1c304a364313b20ce2c1362ee73ab965023f7  logs/run_all.out
0104b123f85aab879a0e82d8abef102ab1d24ddbd7916a7f01b686ad724ccb59  logs/chain_judge.out
e7e450d745262461068dd31f66f2733b769871f3cfbad87cb03b66dbbdcc31e1  dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s2027.npz
b20ec4fba5695d5189cb8ac23b81cef098c7250750376ace72a859bdc3759124  dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz
2c36f84518605f9cd5f8d0c8c4da0da9ba52392ead2006eac09ab463c79b5696  dev/probe_artifacts/w10_ablation_series_R0_rollm_log_s2027.npz
61c299c57b01759773dd5f2e3f03e1f2231c9957544d4c62ca3073c7818ed32f  dev/probe_artifacts/w10_ablation_series_R0_rollm_log_s42.npz
2d054cde82c9787c77cab4131e99df2adc0aaa01830386f2db11e79e256d326d  dev/probe_artifacts/w10_ablation_series_R1_pinned_log_s2027.npz
f30fb6277b8d0febec6c478e1484224b725b5d74243f5d2c77635b8f4b12538f  dev/probe_artifacts/w10_ablation_series_R1_pinned_log_s42.npz
a21bae0a47f148e0625627c9bf7024b0f2ff761b11a0f83c795bcefa89122606  dev/probe_artifacts/w10_ablation_series_R1_rollm_log_s2027.npz
4e841af1809950e2561504576816d6dbd37c2a5627687c6741b9c18da6d568a4  dev/probe_artifacts/w10_ablation_series_R1_rollm_log_s42.npz
f11e963f9e55e5edeeff3fee150be5aa5afa775b2d6e9c7a012f756923d2fb39  dev/probe_artifacts/w10_ablation_series_R2_pinned_log_s2027.npz
b3234b140861b833d0665c7a8cc1c70112af035d51565c17994214923fb7dc8e  dev/probe_artifacts/w10_ablation_series_R2_pinned_log_s42.npz
2cd164857552a9a3eab1b8b37979a12a24b79b63beb5d257fdad06c1e164118e  dev/probe_artifacts/w10_ablation_series_R2_rollm_log_s2027.npz
874f3bc40fb0b3d300a0152f99489ebb31563c5419d9a4bc253db5e05dc7d293  dev/probe_artifacts/w10_ablation_series_R2_rollm_log_s42.npz
1cf01b1ee4f54845a39d445efabc599353c6acea24ce6d9463257a23f04292d1  dev/probe_artifacts/w10_ablation_series_R3_pinned_log_s2027.npz
dc8970ad14dfe3e1316d00e4c58bd42418071044c8ab414a3a717950db554cdc  dev/probe_artifacts/w10_ablation_series_R3_pinned_log_s42.npz
ba95fea3a85576a7054485eb76ee8bd866bc047a598eb51e9d1ec9fda1ba40fd  dev/probe_artifacts/w10_ablation_series_R3_rollm_log_s2027.npz
464667ec5a7414235aecc98d1bdd5207fb4cfa46e4e0e1835c8be36d1bafda62  dev/probe_artifacts/w10_ablation_series_R3_rollm_log_s42.npz
5edaac96a961a861d27e11beef5fc752ea86d0bb97e581e75cf516ac89a609ca  dev/probe_artifacts/w10_ablation_series_R4_pinned_log_s2027.npz
172ef07cf5792d4c70099a7372089b470f52106b3e32b8d8fa5645395b4a4962  dev/probe_artifacts/w10_ablation_series_R4_pinned_log_s42.npz
e78ef35ed0cfa6e3f9ba8366dc7592541cb3a99f8f729df6610d65d919094a03  dev/probe_artifacts/w10_ablation_series_R4_rollm_log_s2027.npz
f7f851d9ce2e825d88e23ca5fc8e12a751568c98a1f5c06de5cdaaecbc31f9e4  dev/probe_artifacts/w10_ablation_series_R4_rollm_log_s42.npz
9aa23e4c9440a15cc73f168da5991a8539778b2af50d7032e68a900a6e79ead1  dev/probe_artifacts/w10_ablation_series_R5_pinned_log_s2027.npz
34c58ef8f028986bbc51b082a523a072825f2b53ab5dd651182e8a0dcd932c85  dev/probe_artifacts/w10_ablation_series_R5_pinned_log_s42.npz
037f2dec915c1ac835bdc42b0451dd1cf4ba7e5aea71e0c43ea9e4286df3db03  dev/probe_artifacts/w10_ablation_series_R5_rollm_log_s2027.npz
2241ae688109001d26444184619770775e7acb18964cda14513b99351d66100f  dev/probe_artifacts/w10_ablation_series_R5_rollm_log_s42.npz
5fa5a27fde197751ee36a9325d506bcfd333c055ef0bc81d7ef1f4d1c8133f4e  dev_alt/probe_artifacts/w10_ablation_series_R0_pinned_prod_s2027.npz
634e5efef470913613de6cbf433ed2e06c8e26766f7ffdd75158f8e77366cdfb  dev_alt/probe_artifacts/w10_ablation_series_R0_pinned_prod_s42.npz
6a7ac289f57539d31013dfa9044c9b504271b40bd3ed28891895080ab2d77c0c  dev_alt/probe_artifacts/w10_ablation_series_R0_rollm_prod_s2027.npz
f8afa4c75eb3e50f2f8fb4fff9bb702c3b1260c5a19ff39bf4c5e6510519a12e  dev_alt/probe_artifacts/w10_ablation_series_R0_rollm_prod_s42.npz
bafee1b0d36b18e04e32889cc7f75b6fa87b3050502e6f272c7c9c262ef25fe1  dev_alt/probe_artifacts/w10_ablation_series_R1_pinned_prod_s2027.npz
4c5215072574143a10c646913e23bc1ff3d848dbcb071355acf5c964f750203e  dev_alt/probe_artifacts/w10_ablation_series_R1_pinned_prod_s42.npz
01a5e375282dd930ec943a752d340e8aa5020f9642d7822b3d9ab59c6538ff54  dev_alt/probe_artifacts/w10_ablation_series_R1_rollm_prod_s2027.npz
86cb1ed6339bd6eefd8d51bceec52565c9591cb292fe2185b218eb03fd96e748  dev_alt/probe_artifacts/w10_ablation_series_R1_rollm_prod_s42.npz
2b61cb9e38eb25ef84e306b7e486a5f901c211dad22768a9ad534edd758bc820  dev_alt/probe_artifacts/w10_ablation_series_R2_pinned_prod_s2027.npz
21707122193870f7714ceb82877392ccf51b620edfd970765905ab60732b2984  dev_alt/probe_artifacts/w10_ablation_series_R2_pinned_prod_s42.npz
78d68b6653be3ecf429448966fabaa8950c69ad8b0d9752ac0caead172709514  dev_alt/probe_artifacts/w10_ablation_series_R2_rollm_prod_s2027.npz
79736c4f43aa97c612204ca45d341d3de66efcf3371c393748652d510316a606  dev_alt/probe_artifacts/w10_ablation_series_R2_rollm_prod_s42.npz
fd52f3dc439b44e1f71b408c8433223a1e3b75de62a3a0fb921988b036180bc9  dev_alt/probe_artifacts/w10_ablation_series_R3_pinned_prod_s2027.npz
326431b9539d8e605dd9d381fadbdbc0ffef7cb5e6e75431388d3816d4a57a91  dev_alt/probe_artifacts/w10_ablation_series_R3_pinned_prod_s42.npz
fdb31ffed750f5db7eadd6701fc12351ec98973f43feb88409758c8ad2b3f26d  dev_alt/probe_artifacts/w10_ablation_series_R3_rollm_prod_s2027.npz
c32a9c2e794f1648ea9c23837817dd84e477040221ec7ee6351bd3f8aec347c4  dev_alt/probe_artifacts/w10_ablation_series_R3_rollm_prod_s42.npz
8a5f4a809393bbd209b65a6dd6b473e5be8cab24c6958c5653f23b23ed2deace  dev_alt/probe_artifacts/w10_ablation_series_R4_pinned_prod_s2027.npz
e954d46b3b8af240c4e3e48699845ff28d8eec1ee1dfeb13647ddca0d74d89da  dev_alt/probe_artifacts/w10_ablation_series_R4_pinned_prod_s42.npz
197c26d6964a35662415ddf2bcc4426b0807406bc3e650be8d003eb6b8f615b0  dev_alt/probe_artifacts/w10_ablation_series_R4_rollm_prod_s2027.npz
62f1f4f20fc8020c8535439c69fb219a1c88097be7303f5d749a305874368da4  dev_alt/probe_artifacts/w10_ablation_series_R4_rollm_prod_s42.npz
19904578fac7745174ed390927969ffe1d3207ae3821e48f294e6c4077f46b68  dev_alt/probe_artifacts/w10_ablation_series_R5_pinned_prod_s2027.npz
677c966506456a9376d315096fd2bf2c9ba083cafd96cb02206c35c63414a979  dev_alt/probe_artifacts/w10_ablation_series_R5_pinned_prod_s42.npz
7386687ccaf6e04cff57cc3e2fbf05daf82b82e27ee29d3e2e50a747b7bca0fe  dev_alt/probe_artifacts/w10_ablation_series_R5_rollm_prod_s2027.npz
67e4c78c3d92777178ea81fed0ba85dd8411ea2cb73e362b59ed7179d95746e8  dev_alt/probe_artifacts/w10_ablation_series_R5_rollm_prod_s42.npz
```
