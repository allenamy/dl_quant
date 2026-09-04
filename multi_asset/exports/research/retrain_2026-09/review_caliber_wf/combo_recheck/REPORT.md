# combo_recheck — 2026-08-26 combo selection re-tested under the correct return caliber

> **创建:** 2026-09-04 15:3xZ | **Session:** review_caliber teammate (combo_recheck) | **状态:** 完成, 16 臂全 OK, 装置等价逐位 PASS | **作废条件:** jpline 恢复后用原 pod_backup 面板复跑; 或 W3FIX 固定实盘席位臂入档后以其为准
> READ-ONLY on all inputs. Outputs only under `/workspace/review_scratch/combo_recheck/` (pod) and the Mac scratch dir. No GPU. jpline not used.
> Labels: **VERIFIED** = command + printed output or file:line quote in this report. **INFERRED** = derived from verified facts with stated reasoning. **UNRESOLVED** = not established here.

## 0. One-paragraph answer

The 08-26 verdict "combo (LEGS=101 ∧ PHI=0.45) is the strongest of the four forms" **survives in direction under both correct calibers** (raw Σ-simple y4 = CAL=log, and the compounded holding-window target = exchange accounting): on 2024→26 and 2025→26 pooled net_ex and Sharpe, arm D is the best of A/B/C/D for both F10 seeds. **The significance claimed on 08-26 does not survive at seed 42**: D−A 2024→26 is +0.108 [−0.101,+0.312] under CAL=log and +0.203 [−0.022,+0.439] under the compounded target (CI95 includes 0; P(Δ>0) 0.84 / 0.96); only seed 2027 under the compounded target excludes 0 (+0.256 [+0.029,+0.477]). **The attribution reverses**: under CAL=simple the gain was carried by V2MAIN (C−A +0.120, P 0.96; B−A +0.027). Under the correct calibers V2MAIN alone is ≈0 (C−A +0.005 log / +0.079 compounded, P 0.50 / 0.79) and the only pairwise delta whose CI95 excludes 0 is "drop rev24 given V2MAIN" (D−C: +0.103 [+0.006,+0.201] log; +0.124 [+0.016,+0.238] compounded, both seeds). **The 08-26 yearly claim "candidate ≥ in-role in every year" reverses for 2025** (D−A 2025: −0.137 log / −0.079 compounded vs +0.152 under CAL=simple). All numbers are at device (msharpe) seats, which the caliber itself moves from king 0.31 (simple) to king 0.52–0.54 (log/compounded); see §6.

## 1. What the 08-26 documents claimed (belief-level records, with line receipts)

**Device declared for the decision** — `~/wide_shadow/fea171/combo_stage.py` line 3 (VERIFIED, quoted):
`判据装置 = w10 LEGS=101 CAL=simple PHI=0.45(docs/PREREG_leg_ablation_2026-08-26.md §T5)。`

**CANDIDATE_wide_v2main_norev24_2026-08-26.md** (VERIFIED quotes):
- L56: `| 口径: 收益 | 全部 CAL=simple(交易所简单收益); 装置加白名单断言, \`CAL=exec\` 直接报错(E-0826-C 焊死) | 加固装置 9f15dea0 |`
- §2 main table (2023+ 7933 anchors, CAL=simple, jpline device), L20–24:

| form (doc row) | net/anchor bps | Sharpe | Δnet vs in-role [CI95] | maxDD | turnover | doc line |
|---|---|---|---|---|---|---|
| 在役三腿 (= arm A) | 1.307 | 2.18 | — | −1604 | 0.0312 | L20 |
| 只混 V2MAIN, 4 runs (= arm C) | 1.42–1.53 | 2.39–2.60 | +0.115~+0.224 (3/4 ★) | −1230~−1482 | 0.033 | L21 |
| 候选 s42 (= arm D) | 1.681 | 2.89 | +0.374 [+0.15,+0.60] ★ | −1333 | 0.0288 | L22 |
| 候选 s2027 (= arm D) | 1.736 | 2.99 | +0.429 [+0.20,+0.66] ★ | −1125 | 0.0279 | L23 |
| 候选 s3037 (= arm D) | 1.595 | 2.72 | +0.289 [+0.07,+0.52] ★ | −1466 | 0.0292 | L24 |

- L26: `**逐年 [净/锚, 夏普]**(候选三种子逐年全部 ≥ 在役; 在役 2023 为负, 候选转正)`; L30–33 yearly [net, Sharpe]: 在役 2024 [+0.55,+1.15] 2025 [+1.27,+1.89] 2026 [+5.12,+7.06]; 候选 s42 2024 [+0.62,+1.33] 2025 [+1.49,+2.36] 2026 [+6.06,+7.87]; s2027 2024 [+0.69,+1.49] 2025 [+1.59,+2.50] 2026 [+6.07,+7.88].
- L14: live composition at 2026-08-26 00:00Z: `掩码后 [king 0.232, fund 0.768] ⇒ 最终构成 ≈ **77% fund + 13% king + 10% V2MAIN**`.

**PREREG_leg_ablation_2026-08-26.md** (VERIFIED quotes):
- §R1 L29 baseline: `每锚净 **1.3067 bps** / 夏普 **2.18** / 换手 **0.0312**`; L36 drop-rev24 (= arm B): `| 去 rev24 | 1.4320 | **+0.1253** | [−0.051,+0.310] | **2.41** | +0.22 | [−0.07,+0.54] | **0.0270** | +0.190 | −0.022 | −0.004 | +0.469 |` (yearly 2023/24/25/26).
- §T3 L259–260, same prediction file `f10_V2MAIN_s42.npy`, φ=0.45, only the caliber switched:
  - `| **simple(正确, 交易所记账)** | **+0.187 [+0.047,+0.337] ★** | +0.239 | +0.051 | +0.106 | **+0.453** |`
  - `| exec→落进对数分支(我的污染) | −0.030 [−0.323,+0.276] | +0.907 | +0.348 | −0.098 | **−2.044** |`
  - L262: `**"2026 全是 −1.9"是对数口径的签名, 不是任何模型的属性。** 昨晚全部 CAL=exec 臂(v2par 书/k78 书/combo/cur 曲线/s3037 书/legs100 重跑)以此作废。`
- §T5 clean table (all CAL=simple), L275–276, L282–284: 混V2MAIN φ.45 s42 +0.187 [+0.047,+0.337] (2023 +0.239 / 2024 +0.051 / 2025 +0.106 / 2026 +0.453); s2027 +0.224 [+0.073,+0.375]; **去rev24 ∧ 混V2MAIN s42 +0.375 [+0.152,+0.603]** (2023 +0.498 / 2024 +0.064 / 2025 +0.214 / 2026 +0.937); s2027 +0.429 [+0.203,+0.661]; s3037 +0.289 [+0.068,+0.515].
- L288: `**修正一个昨判**: "两个好改动不可叠加"反转 —— 干净口径下 **组合优于单项且三种子全显著** ... E-0826 前的"组合判负"是 CAL=exec 伪影。`

**ERROR_LEDGER_2026-08-20.md E-0826-C** (VERIFIED, L213–218): `CAL` accepted any string, non-"simple" fell into the log branch; the 13 contaminated arms include `combo ×2`; L215: `"当前装置全剂量为负、2026 全是 −1.9"整族结论是口径伪影(同一预测文件双口径对照: simple +0.187/2026+0.45, log −0.030/2026−2.04)`; fix = `assert CAL in ("simple","log")` + CONFIG print + config_json in npz.

**The CAL=exec combo-arm numbers themselves are not tabulated in any of the three documents** (UNRESOLVED as belief record): only the single-mix arm's exec-branch row (§T3 L260) is given. What the docs record about the exec combo arms is the qualitative statement at PREREG L288 / E-0826-C L214 that they were discarded as "口径伪影".

**INFERRED, important for reconciliation:** PREREG §T1 F2 states the exec arms were compared against the *simple* baseline (`s3037 书层跑在 CAL=exec(=对数收益) 上, 与 simple 基线相减`). A log-caliber arm minus a simple-caliber baseline subtracts the expm1 convexity term, which in this port is +1.2 to +1.3 bps/anchor in 2026 (§3: A 2026all simple 2.812 vs log 1.499; D 3.132 vs 1.893). So the "2026 ≈ −2" signature was a **mixed-caliber subtraction**, not a property of the log caliber. The 08-26 reading ("log is the artifact, simple is correct") had the direction backwards: the same-caliber log comparisons below show the mix arm at ≈0 and the combo positive.

## 2. Device-equivalence receipt and the REF_SKIP diff

**Port vs research copy** (VERIFIED): `diff multi_asset/exports/research/retrain_2026-09/w10_universe.py <port>` differs only at L26 (`B`/`PD` path constants) and L93 (`_R2`), as stated in the brief. sha256 research `43578158…`, port `64c70a44…`.

**My copy** `/workspace/review_scratch/combo_recheck/w10_universe_recheck.py` (sha256 `5424aceb34b4595b8b9be0d720e90a60e1944fd9bb915fad4c934bc4cf59e9f9`) = port copy + this diff (VERIFIED, `diff /workspace/port_w10/w10_universe.py w10_universe_recheck.py`):

```
43c43,44
< _CFG = {"KMOD_F10": KMOD_F10, ...
---
> REF_SKIP = int(os.environ.get("REF_SKIP", "0")); assert REF_SKIP in (0, 1)   # combo_recheck 2026-09-04: 1 = skip pod_backup reference parity (port stubs are 144-byte placeholders); self-reported in _CFG
> _CFG = {"REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10, ...
325c326,328
<     if WRULE == "msharpe" and LOOK == 900 and LEGS == "111":
---
>     if REF_SKIP:   # combo_recheck: reference parity skipped on request (REF_SKIP=1)
>         print(f"NOTE {nm}: REF_SKIP=1, reference parity vs pod_backup skipped", flush=True); ref = None
>     elif WRULE == "msharpe" and LOOK == 900 and LEGS == "111":
```

The guard only affects the parity block (device L325–334); no computation path changes. Stub check (VERIFIED): `nets_histv2_0_0_0.npy` loads as shape (1, 2), so with LEGS=101 the device already takes the `NOTE ... 仅比较共同年份` branch and sets `ref=None`; with LEGS=111 the assertion at L327 would fail, hence REF_SKIP=1 on the four LEGS=111 arms only.

**Equivalence run** (VERIFIED; cwd `/workspace/review_scratch/combo_recheck/dev`, inputs = per-file symlinks to `/workspace/port_w10/pod_backup_2026-08-21/*`, `f8_2026-08-22`, `dlw_2026-08-22`; verbatim command from `dev/logs/commands.txt`):

```
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log OUT_TAG=equiv_canon_callog_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
```
Printed: `CONFIG {"REF_SKIP": 0, ... "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`; `RECEIPT_EX d30_n2_c42 {"net_ex_all": 0.329, "net_ex_2024on": 0.7304, "sharpe_ex_2024on": 1.908, ...}`; `DONE 24.5 s`.
Compared to `/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_canon_callog_s42.npz`:
```
d30_n2_c42_rec array_equal: True shapes (10038, 23) (10038, 23)
S0_rec array_equal: True shapes (10038, 23) (10038, 23)
d30_n2_c42_W array_equal: True shapes (10038, 829) (10038, 829)
S0_W array_equal: True shapes (10038, 829) (10038, 829)
config_json equal (minus REF_SKIP): True
```
**PASS.** Arm D (s42) under CAL=log and CAL=simple is therefore taken from the port artifacts as instructed (sha256 `e80c957d…` / `5d601e1a…`), not rerun.

**Compounded-target swap mechanism (refuters' `refute_C6_*`)** — read and reused (VERIFIED):
- `refute_C6_1/run_alt.sh` builds a dev dir, symlinks the panel/king/F10/dlw inputs, and repoints `pod_backup_2026-08-21/wide_fea_hist_meta.npz` at a rebuilt meta whose only changed key is `y4`; runs the device with `CAL=log` (no transform). Its own runs were on the *live* form (MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero), so not reused as numbers.
- `refute_C6_2/build_alt_meta.py` + `altrun/build_alt_meta.out`: `PARITY oldsum(rebuilt) vs meta y4: cells 3446599 exact_eq 1.000000 max|Δ| 0.00e+00 nan-mismatch 0`; `PARITY newprod vs dlw y4s: common anchors 10056 cells 3374240 exact_eq 1.000000 max|Δ| 0.00e+00 nan-mismatch 0`. `meta_newprod.npz` = `Π(1+r5)−1` over rows [E+1,E+48], NaN if <46 finite bars. `final_stats.out`: `BITWISE my-base vs port: ... rec equal: True` (their base dir reproduces the port).
- My own check on `meta_newprod.npz` (sha256 `831857dd…`) vs `/workspace/data/wide_fea_v2ext_meta.npz`: `E_ts equal True members equal True qvk equal True`; `finite-mask mismatch cells 1` (alt finite where meta NaN, 1 cell of 8.44M, in 2025); mean(alt−meta) per year 2024 −0.274 / 2025 −0.756 / 2026 −0.215 bps per name-cell. **Mechanism judged sound**: identical anchor/member/liquidity inputs, only the realised-return key replaced; selection mask `ok = isfinite(y4)` differs at 1 cell.
- Used as `/workspace/review_scratch/combo_recheck/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz -> .../refute_C6_2/altrun/meta_newprod.npz`, everything else identical to `dev/`.

Note (VERIFIED from device source, L130–137 and L276–278): `y4` feeds both the P&L (`yv`) and the msharpe seat leg-returns (`legs()`), and the stop-layer price path `Pi` (L315). So a caliber change moves the seats too (see §3 columns w_king/w_fund).

## 3. Per-arm results (arm `d30_n2_c42` = deployed stop layer; net_ex = bps/anchor per unit NAV, executor caliber)

Common facts (VERIFIED, `analyze.py` output): all 18 artifacts share the identical anchor set n=10038, first 2022-01-31 00:00Z, last 2026-08-30 20:00Z. F10 predictions (both seeds) finite rows 7908, first 2023-01-01, **last 2026-08-10 20:00Z** → cut = ts ≤ 2026-08-10 20:00Z. Window sizes: 2024 n=2196, 2025 n=2190, 2026≤cut n=1332, 2026all n=1452, 2024on n=5838, 2025on n=3642. Sharpe = mean/std(ddof=1)·√2190; maxDD = max(cummax(cumsum)−cumsum) in bps; gross/w3/turnover are 2024on means.

Arms: **A** LEGS=111 PHI=0 (pre-combo three legs) · **B** LEGS=101 PHI=0 (drop rev24) · **C** LEGS=111 PHI=0.45 (add V2MAIN) · **D** LEGS=101 PHI=0.45 (combo = deployed). All canon form: LOOK=900 WRULE=msharpe SLOW_NPY=slow_pred_pinned.npy, MEMBERS_TOPN=0 TRADE_TOPN=0 FTRIM=off W3FIX unset (config_json asserted per artifact by `analyze.py`).

### 3a. CAL=log — raw Σ-simple y4, no transform (close to exchange accounting)

| arm | seed | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king / w_rev24 / w_fund | turn |
|---|---|---|---|---|---|---|---|---|---|---|
| A | – | +0.093 S0.26 DD1334 | +0.573 S1.25 DD561 | +2.058 S4.01 DD403 | +1.499 S2.87 DD840 | **+0.623 S1.41 DD1334** | +0.942 S1.94 DD840 | 0.778 | 0.524 / 0.098 / 0.378 | 0.0315 |
| B | – | +0.158 S0.46 DD1206 | +0.551 S1.23 DD566 | +2.163 S4.01 DD394 | +1.653 S3.04 DD756 | **+0.677 S1.54 DD1206** | +0.990 S2.03 DD756 | 0.778 | 0.588 / 0 / 0.412 | 0.0281 |
| C | 42 | +0.161 S0.52 DD916 | +0.444 S1.24 DD485 | +2.160 S4.45 DD392 | +1.609 S3.23 DD862 | **+0.627 S1.65 DD916** | +0.909 S2.17 DD862 | 0.672 | 0.524 / 0.098 / 0.378 | 0.0342 |
| C | 2027 | +0.233 S0.75 DD921 | +0.521 S1.39 DD515 | +2.129 S4.36 DD403 | +1.584 S3.16 DD862 | +0.677 S1.74 DD921 | +0.944 S2.20 DD862 | 0.682 | same | 0.0333 |
| D | 42 | +0.255 S0.86 DD719 | +0.436 S1.25 DD503 | +2.373 S4.61 DD395 | +1.893 S3.64 DD727 | **+0.730 S1.91 DD727** | +1.017 S2.39 DD727 | 0.671 | 0.588 / 0 / 0.412 | 0.0308 |
| D | 2027 | +0.308 S1.04 DD765 | +0.523 S1.43 DD536 | +2.345 S4.53 DD401 | +1.884 S3.59 DD705 | +0.780 S2.00 DD765 | +1.065 S2.44 DD705 | 0.681 | same | 0.0301 |

### 3b. CAL=simple — expm1(Σ-simple y4) (the 08-26 caliber; spurious convexity)

| arm | seed | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king / w_rev24 / w_fund | turn |
|---|---|---|---|---|---|---|---|---|---|---|
| A | – | +0.302 S0.85 DD792 | +0.692 S1.60 DD1156 | +3.307 S6.32 DD294 | +2.812 S5.33 DD712 | **+1.072 S2.48 DD1156** | +1.537 S3.25 DD1156 | 0.740 | 0.312 / 0.052 / 0.636 | 0.0213 |
| B | – | +0.325 S0.94 DD747 | +0.706 S1.65 DD1173 | +3.362 S6.55 DD278 | +2.864 S5.52 DD706 | **+1.099 S2.58 DD1173** | +1.566 S3.35 DD1173 | 0.732 | 0.344 / 0 / 0.656 | 0.0199 |
| C | 42 | +0.308 S0.99 DD757 | +0.818 S2.32 DD685 | +3.586 S6.96 DD262 | +3.094 S5.95 DD682 | **+1.192 S3.07 DD757** | +1.725 S4.03 DD685 | 0.663 | 0.312 / 0.052 / 0.636 | 0.0229 |
| C | 2027 | +0.368 S1.17 DD768 | +0.860 S2.40 DD631 | +3.540 S6.86 DD289 | +3.051 S5.86 DD683 | +1.220 S3.12 DD768 | +1.734 S4.02 DD683 | 0.668 | same | 0.0223 |
| D | 42 | +0.322 S1.06 DD694 | +0.843 S2.41 DD670 | +3.629 S7.14 DD258 | +3.132 S6.11 DD682 | **+1.216 S3.18 DD694** | +1.756 S4.15 DD682 | 0.655 | 0.344 / 0 / 0.656 | 0.0214 |
| D | 2027 | +0.389 S1.27 DD699 | +0.878 S2.47 DD618 | +3.620 S7.11 DD261 | +3.123 S6.07 DD683 | +1.252 S3.25 DD699 | +1.773 S4.16 DD683 | 0.660 | same | 0.0208 |

### 3c. Compounded holding-window target — y4 := Π(1+r5)−1 over [E+1,E+48], CAL=log (exchange caliber)

| arm | seed | 2024 | 2025 | 2026≤08-10 | 2026→08-30 | 2024→26 | 2025→26 | gross | w_king / w_rev24 / w_fund | turn |
|---|---|---|---|---|---|---|---|---|---|---|
| A | – | **−0.038 S−0.10 DD1674** | +0.550 S1.18 DD573 | +1.823 S3.63 DD380 | +1.305 S2.56 DD787 | **+0.517 S1.17 DD1674** | +0.851 S1.76 DD792 | 0.769 | 0.542 / 0.115 / 0.343 | 0.0340 |
| B | – | +0.087 S0.25 DD1426 | +0.531 S1.17 DD612 | +2.052 S3.85 DD367 | +1.549 S2.88 DD754 | **+0.617 S1.40 DD1426** | +0.937 S1.91 DD830 | 0.772 | 0.617 / 0 / 0.383 | 0.0297 |
| C | 42 | +0.095 S0.32 DD1088 | +0.481 S1.31 DD491 | +1.998 S4.18 DD329 | +1.526 S3.12 DD782 | **+0.596 S1.57 DD1088** | +0.897 S2.14 DD782 | 0.657 | 0.542 / 0.115 / 0.343 | 0.0367 |
| C | 2027 | +0.184 S0.62 DD1040 | +0.532 S1.41 DD522 | +2.021 S4.21 DD337 | +1.545 S3.16 DD783 | +0.653 S1.71 DD1040 | +0.936 S2.20 DD783 | 0.667 | same | 0.0358 |
| D | 42 | +0.232 S0.82 DD797 | +0.471 S1.31 DD512 | +2.271 S4.43 DD336 | +1.833 S3.54 DD704 | **+0.720 S1.89 DD797** | +1.014 S2.36 DD704 | 0.658 | 0.617 / 0 / 0.383 | 0.0324 |
| D | 2027 | +0.309 S1.10 DD765 | +0.536 S1.45 DD551 | +2.268 S4.40 DD344 | +1.833 S3.52 DD694 | +0.773 S2.01 DD765 | +1.053 S2.41 DD694 | 0.667 | same | 0.0317 |

**Caveats on the rows (VERIFIED facts, INFERRED consequence):** `slow_pred_pinned.npy` finite fraction by year = 2022 0.000 / 2023 0.000 / 2024 0.330 / 2025 0.468 / 2026 0.483. With NaN king predictions the king leg return is identically 0 in 2022–23, so the msharpe window entering 2024 contains up to 900 anchors of zero king return and the king seat ramps in during 2024 — the 2024 rows and the 2024→26 pooled rows carry this device artifact; **2025→26 is the cleaner pooled window.** Also, after 2026-08-10 20:00Z the F10 predictions are NaN, so in C and D the F10 sub-book degenerates to its remaining legs (fund-only for D) for the last 120 anchors; the "≤08-10" cut isolates this.

**Caliber effect on the same book (INFERRED from the tables):** convexity term A(simple)−A(log) 2024→26 = +0.449, 2026all = +1.313 bps/anchor; D: +0.486 / +1.239. Compounded vs raw Σ-simple: A −0.106 (2024→26), D −0.010 — the exchange caliber penalises the pre-combo book more than the combo. And the caliber moves the seats: king seat 0.31 (simple) → 0.52 (log) → 0.54 (compounded) for A; fund seat 0.64 → 0.38 → 0.34. The book that was judged on 08-26 (fund-heavy, turnover 0.021) is not the book the correct caliber produces from the same rule (king-heavy, turnover 0.031–0.034).

## 4. Pairwise deltas (paired by anchor, identical anchor sets; day-block bootstrap, block = UTC calendar day, 2000 resamples, seed 20260904; CI95 = 2.5/97.5 pct)

Δ net_ex bps/anchor; "P" = P(Δ>0) across resamples. Per-year Δ = point estimates. ΔSharpe = Sharpe(x) − Sharpe(y).

### 4a. CAL=log (raw Σ-simple)

| pair | seed | 2024→26 Δ [CI95] P | 2025→26 Δ [CI95] P | 2024→26≤cut | 2025→26≤cut | Δ 2024 / 2025 / 2026≤cut / 2026all | ΔSharpe 24on/25on | Δturn |
|---|---|---|---|---|---|---|---|---|
| **D−A** combo vs pre-combo | 42 | +0.108 [−0.101,+0.312] 0.84 | +0.075 [−0.227,+0.375] 0.68 | +0.083 [−0.129,+0.293] | +0.034 [−0.284,+0.327] | +0.162 / **−0.137** / +0.315 / +0.394 | +0.50 / +0.44 | −0.0007 |
| **D−A** | 2027 | +0.158 [−0.052,+0.367] 0.92 | +0.123 [−0.189,+0.413] 0.79 | +0.130 [−0.080,+0.342] | +0.077 [−0.216,+0.362] | +0.215 / **−0.050** / +0.286 / +0.385 | +0.59 / +0.50 | −0.0014 |
| B−A drop rev24 | – | +0.054 [−0.041,+0.157] 0.87 | +0.048 [−0.099,+0.192] 0.73 | +0.041 [−0.057,+0.134] | +0.025 [−0.121,+0.161] | +0.065 / −0.022 / +0.104 / +0.154 | +0.13 / +0.08 | −0.0034 |
| C−A add V2MAIN | 42 | **+0.005 [−0.177,+0.200] 0.50** | −0.034 [−0.286,+0.232] 0.41 | +0.000 [−0.188,+0.177] | −0.042 [−0.294,+0.227] | +0.068 / −0.129 / +0.102 / +0.111 | +0.23 / +0.22 | +0.0027 |
| C−A | 2027 | +0.054 [−0.122,+0.224] 0.72 | +0.002 [−0.245,+0.241] 0.51 | +0.050 [−0.131,+0.231] | −0.006 [−0.263,+0.246] | +0.140 / −0.052 / +0.071 / +0.085 | +0.33 / +0.26 | +0.0018 |
| D−B V2MAIN given no rev24 | 42 | +0.053 [−0.133,+0.225] 0.70 | +0.027 [−0.212,+0.283] 0.58 | +0.043 [−0.138,+0.226] | +0.009 [−0.252,+0.269] | +0.097 / −0.114 / +0.211 / +0.240 | +0.37 / +0.36 | +0.0027 |
| D−B | 2027 | +0.103 [−0.069,+0.284] 0.86 | +0.075 [−0.157,+0.336] 0.75 | +0.089 [−0.079,+0.267] | +0.052 [−0.198,+0.293] | +0.150 / −0.028 / +0.182 / +0.231 | +0.47 / +0.42 | +0.0020 |
| D−C drop rev24 given V2MAIN | 42 | **+0.103 [+0.006,+0.201] 0.98** | +0.108 [−0.035,+0.256] 0.93 | +0.083 [−0.014,+0.181] | +0.076 [−0.069,+0.215] | +0.094 / −0.008 / +0.213 / +0.283 | +0.26 / +0.22 | −0.0034 |
| D−C | 2027 | **+0.104 [+0.004,+0.213] 0.98** | +0.121 [−0.019,+0.273] 0.95 | +0.080 [−0.014,+0.182] | +0.083 [−0.062,+0.223] | +0.076 / +0.002 / +0.216 / +0.300 | +0.26 / +0.24 | −0.0032 |

### 4b. CAL=simple (the 08-26 caliber)

| pair | seed | 2024→26 Δ [CI95] P | 2025→26 Δ [CI95] P | 2024→26≤cut | 2025→26≤cut | Δ 2024 / 2025 / 2026≤cut / 2026all | ΔSharpe 24on/25on | Δturn |
|---|---|---|---|---|---|---|---|---|
| **D−A** | 42 | +0.144 [−0.009,+0.305] 0.97 | +0.219 [−0.004,+0.426] 0.97 | +0.141 [−0.031,+0.307] | +0.216 [−0.009,+0.435] | +0.020 / **+0.152** / +0.322 / +0.320 | +0.70 / +0.91 | +0.0001 |
| **D−A** | 2027 | **+0.180 [+0.023,+0.338] 0.99** | **+0.236 [+0.034,+0.446] 0.99** | +0.178 [+0.025,+0.335] | +0.234 [+0.022,+0.444] | +0.088 / +0.186 / +0.313 / +0.312 | +0.77 / +0.91 | −0.0004 |
| B−A | – | +0.027 [−0.026,+0.084] 0.83 | +0.029 [−0.044,+0.102] 0.79 | +0.027 [−0.028,+0.086] | +0.030 [−0.045,+0.107] | +0.024 / +0.014 / +0.056 / +0.052 | +0.11 / +0.10 | −0.0014 |
| C−A | 42 | **+0.120 [−0.018,+0.271] 0.96** | +0.189 [−0.008,+0.391] 0.97 | +0.116 [−0.033,+0.269] | +0.184 [−0.027,+0.396] | +0.007 / +0.127 / +0.279 / +0.282 | +0.59 / +0.79 | +0.0016 |
| C−A | 2027 | +0.148 [+0.006,+0.295] 0.98 | +0.197 [−0.002,+0.386] 0.97 | +0.144 [−0.006,+0.287] | +0.193 [−0.009,+0.403] | +0.067 / +0.169 / +0.233 / +0.240 | +0.64 / +0.78 | +0.0010 |
| D−B | 42 | +0.117 [−0.027,+0.259] 0.94 | +0.190 [−0.010,+0.388] 0.96 | +0.113 [−0.032,+0.259] | +0.186 [−0.019,+0.392] | −0.004 / +0.138 / +0.267 / +0.268 | +0.60 / +0.80 | +0.0015 |
| D−B | 2027 | +0.153 [+0.015,+0.291] 0.99 | +0.207 [+0.007,+0.405] 0.98 | +0.150 [−0.001,+0.294] | +0.204 [+0.004,+0.402] | +0.064 / +0.172 / +0.257 / +0.259 | +0.67 / +0.81 | +0.0009 |
| D−C | 42 | +0.024 [−0.034,+0.081] 0.78 | +0.030 [−0.038,+0.098] 0.78 | +0.025 [−0.037,+0.085] | +0.032 [−0.039,+0.109] | +0.013 / +0.025 / +0.043 / +0.038 | +0.11 / +0.12 | −0.0015 |
| D−C | 2027 | +0.032 [−0.025,+0.091] 0.86 | +0.039 [−0.032,+0.115] 0.85 | +0.033 [−0.028,+0.094] | +0.041 [−0.032,+0.115] | +0.021 / +0.018 / +0.080 / +0.072 | +0.13 / +0.14 | −0.0014 |

### 4c. Compounded holding-window target (exchange caliber)

| pair | seed | 2024→26 Δ [CI95] P | 2025→26 Δ [CI95] P | 2024→26≤cut | 2025→26≤cut | Δ 2024 / 2025 / 2026≤cut / 2026all | ΔSharpe 24on/25on | Δturn |
|---|---|---|---|---|---|---|---|---|
| **D−A** | 42 | +0.203 [−0.022,+0.439] 0.96 | +0.163 [−0.139,+0.474] 0.85 | +0.178 [−0.049,+0.416] | +0.120 [−0.192,+0.448] | +0.270 / **−0.079** / +0.448 / +0.528 | +0.72 / +0.60 | −0.0015 |
| **D−A** | 2027 | **+0.256 [+0.029,+0.477] 0.99** | +0.202 [−0.110,+0.506] 0.90 | **+0.231 [+0.011,+0.465]** | +0.159 [−0.153,+0.469] | +0.346 / **−0.014** / +0.444 / +0.528 | +0.84 / +0.65 | −0.0022 |
| B−A | – | +0.101 [−0.017,+0.211] 0.95 | +0.086 [−0.074,+0.252] 0.86 | +0.094 [−0.023,+0.210] | +0.075 [−0.088,+0.236] | +0.124 / −0.019 / +0.228 / +0.245 | +0.23 / +0.15 | −0.0043 |
| C−A | 42 | +0.079 [−0.114,+0.263] 0.79 | +0.047 [−0.207,+0.312] 0.64 | +0.066 [−0.132,+0.257] | +0.023 [−0.253,+0.301] | +0.133 / −0.069 / +0.175 / +0.221 | +0.40 / +0.38 | +0.0028 |
| C−A | 2027 | +0.137 [−0.035,+0.305] 0.94 | +0.085 [−0.161,+0.333] 0.77 | +0.125 [−0.051,+0.309] | +0.064 [−0.196,+0.324] | +0.222 / −0.018 / +0.197 / +0.241 | +0.53 / +0.43 | +0.0019 |
| D−B | 42 | +0.102 [−0.086,+0.297] 0.84 | +0.077 [−0.194,+0.341] 0.72 | +0.084 [−0.115,+0.279] | +0.045 [−0.230,+0.323] | +0.145 / −0.060 / +0.220 / +0.284 | +0.49 / +0.45 | +0.0028 |
| D−B | 2027 | +0.156 [−0.030,+0.353] 0.96 | +0.116 [−0.139,+0.373] 0.81 | +0.137 [−0.066,+0.327] | +0.085 [−0.165,+0.359] | +0.222 / +0.005 / +0.216 / +0.283 | +0.61 / +0.50 | +0.0021 |
| D−C | 42 | **+0.124 [+0.016,+0.238] 0.99** | +0.116 [−0.028,+0.262] 0.94 | **+0.112 [+0.005,+0.225]** | +0.097 [−0.059,+0.256] | +0.137 / −0.010 / +0.273 / +0.307 | +0.32 / +0.22 | −0.0043 |
| D−C | 2027 | **+0.119 [+0.013,+0.230] 0.99** | +0.117 [−0.027,+0.280] 0.94 | +0.107 [−0.003,+0.217] | +0.096 [−0.062,+0.252] | +0.124 / +0.004 / +0.247 / +0.287 | +0.30 / +0.22 | −0.0041 |

Appendix (S0 arm = no stop layer, same runs; full tables in `analyze_S0.out`): same ordering and same pattern. D−A 2024→26: log +0.162 [−0.045,+0.361] / simple +0.138 [−0.015,+0.297] / compounded +0.230 [−0.004,+0.466] (s42); B−A is CI-excluding-0 under log (+0.115 [+0.021,+0.220]) and compounded (+0.144 [+0.028,+0.259]); C−A never excludes 0 under log/compounded (+0.048 / +0.098, P 0.71 / 0.85); D−C excludes 0 under all three calibers.

## 5. Does the 08-26 verdict survive? (strictly from the numbers)

1. **Ranking survives.** Under CAL=log and under the compounded (exchange) target, D is the highest of A/B/C/D on 2024→26 mean, 2025→26 mean, and Sharpe, for both seeds (tables 3a/3c). Under the compounded target A is negative in 2024 (−0.038) while D is +0.232/+0.309.
2. **"Strongest form, significant" does not survive at the available precision.** D−A CI95 includes 0 under CAL=log for both seeds and both pooled windows (s42 P(Δ>0) 0.84/0.68), and under the compounded target for s42 (0.96/0.85); it excludes 0 only for s2027 on 2024→26 under the compounded target (+0.256 [+0.029,+0.477]) and under CAL=simple. The 08-26 magnitude (+0.375/+0.429 on 2023+, CANDIDATE L22–23) is not reproduced in this port under any caliber; note the panel and window differ (§6), so magnitude comparability to the 08-26 tables is limited — the within-port caliber contrast is the valid comparison.
3. **The attribution reverses.** Under CAL=simple the combo gain is mostly V2MAIN (C−A +0.120, P 0.96; D−B +0.117; B−A only +0.027). Under CAL=log the V2MAIN main effect is zero (C−A +0.005 [−0.177,+0.200], P 0.50; s2027 +0.054, P 0.72); under the compounded target +0.079 (P 0.79) / +0.137 (P 0.94). The drop-rev24 effect grows under the correct calibers (B−A +0.054 log / +0.101 compounded vs +0.027 simple), and **D−C (dropping rev24 in the presence of V2MAIN) is the only pairwise delta with CI95 > 0 under both correct calibers and both seeds** (log +0.103/+0.104; compounded +0.124/+0.119). So what the correct caliber supports is "drop rev24"; "add V2MAIN" is undecidable-to-null on net_ex (it still raises Sharpe: ΔSharpe C−A +0.23~+0.53, via lower gross and lower drawdown, 3a/3c).
4. **The 08-26 yearly claim reverses for 2025.** "候选逐年全部 ≥ 在役" (CANDIDATE L26): under CAL=log D−A 2025 = −0.137 (s42) / −0.050 (s2027); compounded −0.079 / −0.014; under CAL=simple it was +0.152 / +0.186. 2024 and 2026 stay positive under all calibers.
5. **The 08-26 reconciliation's characterisation of the exec-branch arms was wrong in direction, but the arms it discarded were not clean either.** The "2026 ≈ −2" signature (PREREG L260/262) is consistent with subtracting a CAL=simple baseline from a CAL=log arm (convexity term ≈ +1.2~1.3 bps/anchor in 2026 in this port); same-caliber log comparisons give C−A 2026 = +0.10 and D−A 2026 = +0.32~+0.39. So neither "combo does not compose" (the exec-era reading) nor "combo +0.37 significant, V2MAIN-driven" (the 08-26 reading) is what the correct caliber shows; it shows a positive but not-significant combo edge driven by rev24 removal.
6. **Verdict statement:** "combo is the strongest of the four forms" — **survives as a point-estimate ranking under the correct caliber; the significance and the mechanism claimed on 08-26 do not survive; the every-year dominance claim reverses in 2025.** Undecidable at the available precision as a significant improvement over the pre-combo form (seed 42), marginally decidable for seed 2027 under the exchange caliber only.

## 6. UNRESOLVED / caveats

- **Seats are device seats, not live seats.** The msharpe seats under the correct calibers are king ≈0.52–0.62 / fund ≈0.34–0.41 (3a/3c), vs king 0.31 / fund 0.64 under CAL=simple, vs the live fixed seat 0.21 king (STATE.md L1 banner, 09-04). A W3FIX=0.21,0,0.79 replay would test the V2MAIN effect at live seats, but the whitelisted W3FIX value has rev24=0, so it cannot test A vs B (rev24 present vs absent). Not run (out of the requested arm set).
- **Panel/window differ from the 08-26 device**: this port uses `/workspace/data/wide_fea_v2ext_meta.npz` (10176 anchors, 2022-01-31→2026-08-30; 10038 replayed) and `slow_pred_pinned.npy`; the 08-26 numbers were on jpline `pod_backup_2026-08-21` meta (2023+, 7933 anchors). Absolute levels are not comparable across the two; only the caliber contrast within this port is.
- **Pinned king file OOS status**: `slow_pred_pinned.npy` sha256 `158cd4ac…` matches `shadow_bundle_v3/MANIFEST.json` per the port REPORT (L32); whether its 2024–26 values are walk-forward OOS (as the device header requires) was not verified by me. The king seat ramp-in artifact (NaN 2022–23) is VERIFIED.
- **Seed s3037** is not wired in the port (`f8_2026-08-22/preds` holds only `f10_V2MAIN_s42.npy` and `_s2027.npy`); the 08-26 three-seed claim is re-tested with two seeds.
- **The CAL=exec combo-arm numbers of 08-25/26** are not tabulated in the docs; the reconciliation in §5.5 rests on the single-mix arm row (PREREG L259–260) and the F2 statement (§T1) that exec arms were differenced against a simple baseline (INFERRED for the s42 row).
- **Multiple comparisons**: 5 pairs × 3 calibers × 2 seeds × 4 windows of CI95, no adjustment; the "CI excludes 0" flags in §4 are per-comparison.
- Alt-target finite mask differs from the meta mask at 1 cell (2025); negligible but not zero.
- The stop-layer price path `Pi` (device L315) uses the same `yv`, so under CAL=log it compounds Σ-simple and under the compounded target it compounds the true 4h return; both are internally consistent, neither was separately validated.

## 7. Receipts index

- Pod dir: `/workspace/review_scratch/combo_recheck/` — `w10_universe_recheck.py` (5424aceb…), `patch_refskip.py`, `analyze.py` (0d2d9fd8…), `analyze_d30.out`, `analyze_S0.out`, `stats_d30_n2_c42_rec.json`, `stats_S0_rec.json`, `dev/logs/commands.txt` + `dev_alt/logs/commands.txt` (verbatim commands), `dev/logs/*.log`, `dev_alt/logs/*.log` (CONFIG + RECEIPT lines), `dev/probe_artifacts/*.npz`, `dev_alt/probe_artifacts/*.npz`.
- Artifact sha256: A_callog 13e1f0fa… · A_calsimple aad84c56… · B_callog 777865f8… · B_calsimple 74c80e8b… · C_callog_s42 a1cd1279… · C_callog_s2027 35cb8627… · C_calsimple_s42 b6edd1f2… · C_calsimple_s2027 bd7c6eec… · D_callog_s2027 38309efa… · D_calsimple_s2027 6f76d07b… · equiv_canon_callog_s42 e25b96b4… · A_prod fdc948ed… · B_prod 3f1d330e… · C_prod_s42 7b58e43a… · C_prod_s2027 023c6e58… · D_prod_s42 5deff241… · D_prod_s2027 880bc1b9… · port D callog e80c957d… · port D calsimple 5d601e1a… · meta_newprod 831857dd… · f10_V2MAIN_s42 baf747ce… · f10_V2MAIN_s2027 c742ffaa… · slow_pred_pinned 158cd4ac….
- Mac copy: `/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/combo_recheck/` (REPORT.md, analyze outputs, stats json, scripts, port device copy).
