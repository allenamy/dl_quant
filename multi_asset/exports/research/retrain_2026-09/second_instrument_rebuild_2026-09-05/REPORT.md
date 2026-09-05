# REPORT — second instrument rebuilt from source on pod2 (PREREG_second_instrument_rebuild_2026-09-05, sha 32182341cb589c58)

> **创建:** 2026-09-05 03:4xZ | **Session:** b9646a9e (teammate: jpline rebuild) | **状态:** COMPLETE (chain CHAIN_DONE 03:27:44Z; all gates evaluated; G5 diagnostic only) | **作废条件:** any gate rule changed after seeing numbers; any number below without a script receipt; re-run of the chain with different inputs
> Pod root `/workspace/review_scratch/jpline_rebuild/` (logs/commands.txt = every command verbatim with rc; results/*.json = every number). Mac mirror `…/scratchpad/review_caliber/jpline_rebuild/` (pod_results/, pod_logs/). Tags: **VERIFIED** = printed by a script whose command is in logs/commands.txt; **INFERRED** = derived from verified facts, derivation stated; **UNRESOLVED** = not settled by this run.

## 0. Answer in one paragraph

The 08-21 instrument is reproduced from git-tracked source on pod2 (VERIFIED). The re-pulled 5-minute data build a panel that is bitwise identical to the 08-21 panel for every kline-derived array on every anchor from 2020-01-31 to 2026-08-11; the only kline differences are the last four August days, where the 08-21 zip tree had no daily files for 348 symbols. With the funding coverage of the 08-21 pod (450 live symbols) and the real 08-21 king, the 08-21 book device reproduces the 08-21 net series to within 1e-6 bps per anchor in 2023, 2024 and 2025 (2024 fully bitwise). The frozen gates G1, G2(a)(b)(c) and G3(b2) therefore FAIL as written, but every failing cell is classified: (i) funding coverage (pod2's funding tree has all 829 symbols, the 08-21 pod's had the 450 live names); (ii) the August-2026 tail; (iii) the w10 replay device is not the 08-21 device even at CAL=log (its DEMEAN-FIX and forced-exit rules change the book by −0.14 and −0.40 bps/anchor in 2025 and 2026 with identical inputs); (iv) LightGBM refits are not bitwise reproducible across machines (fold ICs within ±0.002, book −0.19/−0.27 bps/anchor in 2025/2026); (v) float16 quantisation of 5-minute returns (9 of 1,090 sampled cells exceed 2e-5, all within the float16 bound). No log/simple confusion exists anywhere on the return path (G3(a) and (b1) PASS bitwise). The leakage battery passes (i), (ii), (iv), (v), (vi); the shuffle-future null (iii) fails on 3 of 15 seed×fold runs with nulls ≤ +0.010 against 2·SE ≈ 0.005 (true IC ≈ 0.06), so under the frozen rule the rebuilt king was NOT admitted to G5 and G5 ran with the pinned king only. The one hist-vs-pinned pairing available (F1, log caliber) gives Δ(hist − pinned) 2024→26 = +0.012 bps/anchor [−0.130, +0.151]: the 2020-vs-2022 king training start (E-0905-A) is not a material driver of the 2024–26 numbers. The pod-vs-08-21 gap of −0.26 / −0.35 bps/anchor per gross in 2024 / 2025 decomposes into funding coverage, device form and LightGBM refit variance (§5).

## 1. Gate table (rules frozen in the prereg §2; verdicts printed by scripts, see results/*.json)

| gate | frozen rule | verdict | evidence (VERIFIED unless noted) |
|---|---|---|---|
| G0 input identity | v1 panel sha f14bc33d78b24929; repo reference (9941,2); each ported script sha == git HEAD | **PASS** | sha256 of /workspace/data/wide_panel_4h_v1.npz = f14bc33d78b2492994e793b494c2ff330958351abf5e6acbb1fe0364f032bc4a (G1.json inputs); nets_histv2_d30_pergross_ts_0821.npy shape (9941,2) sha 0f548011…; src/SHA256SUMS_src verified on pod (21 files, git HEAD cac4be6b); every patched script prints SELF_SHA256 + PATCH_SHA256 (stage logs) |
| G1 panel bitwise | every array: NaN positions + finite values bitwise vs v1 | **FAIL** (0/21 arrays) | kline arrays: 0 unequal, 0 NaN-mismatch for 2020–2025; all differences in 2026 ≥ 08-12 (§3). Funding arrays: 0 unequal values in f_fund_now/f_fund_ema; 1,155,487 NaN-mismatch cells = symbols absent from the 08-21 funding tree; 138/324/316 unequal cells (iv/ema_v1/ema_v2) all in 2026 |
| G1b cache 2022+ vs _ext | informational | — | 486,145 common ts; **0 unequal finite cells in all 7 channels**; NaN-only-in-ext cells from 2026-08-12 00:05 (plus the 2022-01-01 left edge) |
| G2(a) nets bitwise | stage-6 nets vs real 08-21 nets (pod copies are 144-byte stubs; ref = Mac backup of the 08-21 pod) | **FAIL** | identical 12,279-anchor grid; d30 corr 0.9275, max|Δ| 99 bps, mean Δ −0.237 bps/anchor; DIAG-A reproduces 08-21 (§5) |
| G2(b) per-gross series | ts set identical AND max|Δ| ≤ 1e-6 bps | **FAIL** | step-8 series has 12,279 anchors from 2021-01-06 (the 9,941-row reference is its 2022-01-31 08:00 truncation, ref ⊂ step8); on the 9,941 common anchors max|Δ| 117 bps, corr 0.906 |
| G2(c) device parity | log ≤ 1e-6 PASS and simple FAIL | **FAIL** | maxabs_diff_vs_pod_backup: CAL=log S0 45.0 / d30 56.2 bps; CAL=simple 273.5 / 261.2 bps |
| G3(a) static census | 0 log/expm1 hits on a return quantity in the 4 scripts | **PASS** | 0 return-path hits; volume-only hits pod_stop_arms_v3.py:59, pod_panel_ext.py:26 |
| G3(b1) Y4 == Σ ret5 | full grid bitwise incl. NaN positions | **PASS** | 3,734,643 finite cells, 0 unequal, 0 NaN-mismatch; independent float64 window sum on 300 anchors 0/75,173 unequal |
| G3(b2) y4s vs raw closes | ≥1000 anchors (≥300 in 2020-21), max|Δ| ≤ 2e-5 | **FAIL** | 1,090 cells (346 in 2020-21): max|Δ| 8.36e-5, p99 1.94e-5, median 2.9e-6; 9 cells > 2e-5, all within 1.5× the float16 quantisation bound; max |Δ|/bound 0.44 |
| G4 leakage battery | (i)…(vi) all pass ⇒ king enters G5 | **FAIL** (hist king not admitted) | (i) PASS 5/5 (ii) PASS (iii) FAIL 3/15 (iv) PASS (v) PASS (vi) PASS (§7) |
| G5 two-instrument separation | diagnostic tables only | done (pinned-only per G4; F1/log hist pairing from the G2 run) | §8 |
| G6 report | this document | done | pod + Mac, sha256 in the final message |

## 2. Lineage receipts

**Data (VERIFIED).** 829 symbols (repo panel_symbols_wide.txt, sha de74019e…) × (79 monthly 2020-01..2026-07 + 16 daily 2026-08-01..16) = 78,755 requests to data.binance.vision; result 33,296 zip files (7,847,016,563 bytes) + 45,459 `.404` sentinels = 78,755; 0 non-404 errors; zip integrity test (testzip on every file) 0 bad. Manifest: logs/klines5m_SHA256SUMS.txt (sha 1cf680ab…, 33,296 lines), logs/klines5m_404.txt (sha 4ef3553a…). Funding zips were not re-pulled (pod tree, 829 dirs, 19,609 zips, all with the interval column).
Timeline: paced downloader (4.00 req/s shared bucket, 8 threads, anchor-window pause logic) 01:13:02–02:02Z (11,724 requests); at 02:01:57Z another agent switched the stage to an unlimited variant citing a user ruling; I stopped it at 02:10:49Z not having received the ruling, restored the paced stage (02:12:55–02:21:25Z), it was switched again at 02:21:29Z; I then verified the ruling in the repo — **STATE.md §4 commit 6b38cbb (user, 2026-09-05 01:49Z): bulk pulls from the static CDN on pod2 are exempt from the ≤4 req/s + anchor-window rule (exchange API limits unchanged)** — and left the fast variant running (36–39 req/s, finished 02:42:00Z, never inside an anchor window). The fast variant (patched/dl_klines_fast.py) is my paced script plus env switches only (diff in logs/patches/dl_klines_fast.diff); file semantics identical. All three download logs are kept.

**Environment (VERIFIED).** pod2 `/workspace/venv/bin/python`: numpy 2.4.6, pandas 3.0.5, lightgbm 4.7.0, scipy 1.17.1; 64 cores; container cgroup memory.max = 60,999,999,488 bytes (host 259 GB).

**Artefacts (VERIFIED, sha256 first 16).** cache dlnative_5m_wide829_f16_hist.npz (696673, 829, 7) 5d5fd0f2f7622465; panel wide_panel_4h_hist_v2_rebuilt.npz 14,329 anchors 9f3e4ae14ef9ff1e; features wide_fea_hist_rebuilt.npy (12985, 829, 82) 3568c673b274959b; meta 509d8b5453239391; king slow_pred_hist_oos_rebuilt.npy 1090418fa793f87c; nets_histv2_-30_2_42.npy c1eaca5318a911a5, nets_histv2_0_0_0.npy b56d7c61917423ed; targets dlw_targets.npz ba10902ef312bb9c; prod-caliber meta 60af00925262f3db; pinned king re-indexed f48b57f9aff20dce; G5 series files listed in logs/10_G5_arms.log.

**Scripts.** 21 verbatim git-tracked files in src/ (SHA256SUMS_src verified on the pod). Five pipeline scripts patched in paths only (§10), plus two deviations forced by the environment: (P1b) the verbatim cache builder's temp name `OUT + '.tmp'` is suffixed `.npz` by numpy so its own `os.replace` fails (observed: 2,290,946,807-byte `*.npz.tmp.npz` written, then FileNotFoundError) — temp name changed to end in `.npz`; (P2-mem) the verbatim feature builder keeps all seven channels' float64 cumulative sums resident (~78 GB at 696,673 rows) and was OOM-killed at the 61 GB container limit — cumulative sums computed channel by channel in the same order; **parity receipt: on the dry-test inputs the P2-mem builder reproduced the verbatim builder's outputs byte for byte (features sha f88b07205bf19870…, meta sha 4b1b6047107d2557…; logs/fea_mem_parity.log)**. Dry-test chain (stages 03–11 on 2022-start substitutes) also reproduced the pod's existing v2ext panel (sha 5e67c0559daa904d) and v2ext meta (4b1b6047…) bitwise through the patched scripts.

## 3. G1 classification (results/G1.json)

Anchor axis and symbol axis identical to v1 (14,329 × 829). Per array (unequal = both finite and different; NaN-mismatch = finite on one side only):

| array | 2020–2025 | 2026 unequal | 2026 NaN-mismatch | symbols | class |
|---|---|---|---|---|---|
| elig (bool) | 0 | 2,274 differing cells (all 2026) | — | — | August tail (window coverage) |
| Y4 / Y24 | 0 / 0 | 0 / 0 | 4,608 / 6,348 (NaN only in v1) | 348 | August tail: no daily zips after 2026-08-11/12 in the 08-21 tree; rebuilt cells equal raw zips (hand check, 3 cells) |
| f_rev_4h/24h/3d, f_mom_7d/30d, f_volq_ratio, f_range/cpos/tbf/asz_24h | 0 | 2,694 each | 0 | 222 | same root cause (windows crossing 08-12) |
| f_mom_7d_x24 | 0 | 1,362 | 0 | 222 | same |
| f_vol_7d | 0 | 2,726 | 0 | 226 | same |
| f_amihud_24h | 0 | 1,314 | 1,380 | 222 | same (heavy-tailed column; built-in corr check 0.0555 driven by these cells) |
| f_fund_now, f_fund_ema | 0 unequal | 0 | 1,155,487 NaN-mismatch (NaN only in v1) over all years (2020 19,136 … 2026 202,688) | 385 | funding coverage: the 08-21 pod's funding tree = the 450 live symbols (exactly `live_pins.symbols_live`); pod2's has 829; the 450 common symbols are bitwise identical in every year |
| f_fund_iv / f_fund_ema_v1 / f_fund_ema_v2 | 0 unequal | 138 / 324 / 316 | 1,155,487 | 390 | + August-2026 interval column (2026-08 monthly zip vs the 08-21 API tail) |

INFERRED cause of the tail: the 08-21 tree was assembled by pod_dl_klines.py (daily 08-01..11), pod_dl_wide.py (new symbols, daily 08-01..12) and a later tail pull for the live names; the CDN now serves daily files through 08-16 for all traded symbols. Nothing in 2020–2025 differs: the CDN history is unrevised and the code path is deterministic across machines (VERIFIED by the zero counts and by G1b).

## 4. King rebuild (results/compare_king.json, results/G4a.json)

Training rows per fold: 2022 291,314 / 2023 596,082 / 2024 1,006,440 / 2025 1,607,846 / 2026 2,457,657 — the 2026-fold count equals the 08-21 receipt (RETRAIN_HIST.json train_rows 2,457,657) exactly; the rebuilt meta equals the 08-21 meta (E_ts, names, members) except 18 August-tail anchors. Fold IC rebuilt vs 08-21: 2022 0.0625 / 0.0603; 2023 0.0550 / 0.0557; 2024 0.0605 / 0.0621; 2025 0.0637 / 0.0617; 2026 0.0582 / 0.0580. Prediction finite masks identical 2022–2025; Pearson(rebuilt, 08-21) per year 0.85 / 0.86 / 0.86 / 0.81 / 0.87; bitwise share 0. In-script refit reproduces the stage-5 file exactly (G4b (v): refit == file True) ⇒ LightGBM is deterministic on this machine; the difference to 08-21 is the machine/thread count (INFERRED), not the data.

## 5. G2: reproduction of the 08-21 book and decomposition of the gap (results/G2a.json, diag_g2a.json, G2bc.json)

d30_n2_c42 arm, column `net` in bps per anchor at the device's own gross (0.56–0.90), yearly means on the identical 12,279-anchor grid (2021-01-06 16:00 → 2026-08-15 00:00):

| year | 08-21 real nets | DIAG-A: 450-symbol funding + real 08-21 king | DIAG-B: 829-symbol funding + real 08-21 king | stage-6 rebuilt (829 funding + rebuilt king) | step-8 F1_hist_log (w10 device form) |
|---|---|---|---|---|---|
| 2021 | −1.777 | −1.777 (bitwise 91%, max 7e-3) | −1.876 | −1.876 | −1.874 |
| 2022 | +0.856 | +0.858 (max 0.9 bps) | +0.791 | +0.790 | +0.792 |
| 2023 | +0.429 | +0.429 (max 6e-7) | +0.111 | +0.078 | +0.062 |
| 2024 | +0.404 | +0.404 (100% bitwise) | +0.197 | +0.180 | +0.161 |
| 2025 | +1.206 | +1.206 (max 5e-7) | +1.135 | +0.947 | +0.812 |
| 2026 (to 08-15) | +2.971 | +2.931 (tail) | +2.702 | +2.432 | +2.036 |

Reading (VERIFIED numbers, INFERRED attribution by construction of the columns): pipeline + data reproduce 08-21 exactly (column 2; the 2022 residual of ≤0.9 bps comes from 3,648 funding cells missing inside the 450 symbols in 2022, the 2026 residual is the August tail); funding coverage 450→829 lowers the book (column 3 − column 2: 2023 −0.318, 2024 −0.207, 2025 −0.071, 2026 −0.229); the LightGBM refit lowers it further (column 4 − column 3: 2023 −0.033, 2024 −0.017, 2025 −0.188, 2026 −0.270); the w10 device form lowers it again (column 5 − column 4, = ATTR(1): 2023 −0.017, 2024 −0.019, 2025 −0.136, 2026 −0.396). Stage-6 summary: rebuilt d30 net_all 0.296 / net_2024on 1.005 / Sharpe 2.36 / maxDD 4,375 / fires 4,357 vs 08-21 0.533 / 1.316 / 3.06 / 4,138 / 4,151.
Per-gross view (the E-0905-A unit, d30, net/gross_total): 08-21 2024 +0.585, 2025 +1.471, 2026 +2.317; step-8 with the rebuilt hist king +0.355 / +1.205 / +2.279; step-8 with the pinned king +0.325 / +1.123 / +2.321 (this last row reproduces the earlier pod numbers +0.327 / +1.129 / +2.351 of pod_armA_vs_0821.out). Implied 08-21 gross 0.794 vs step-8 0.737.
G2(c): the device's parity gate against the stage-6 nets fails under CAL=log (45/56 bps) — the recheck device is a different book form from pod_stop_arms_v3 (L205 demean inside `sel` only; L219-220 forced exit of non-`sel` names) — and CAL=simple adds a further ~200 bps of max deviation (274/261). The E-0904-F ledger sentence "pod 原始回放同法" is true only in that the 08-21 device has no expm1; it is false as a statement that the pod replay device equals the 08-21 device.

## 6. G3 caliber identity (results/G3.json)

(a) No log/expm1/log1p on any return quantity in pod_stop_arms_v3.py, pod_slow_hist_folds.py, pod_fea_wide_hist.py, pod_panel_ext.py (volume-channel hits only). (b1) Panel Y4 equals the float64 cumulative sum of float32 5-minute returns over rows [E, E+47], cast to float32, on all 3,734,643 finite cells, with identical NaN placement (<46 finite bars). (b2) dlw y4s = Π(1+r5)−1 over [E+1, E+48] vs raw close ratio c(N+4h)/c(N)−1 on 1,090 (anchor, member) cells with all 48 bars present: median 2.9e-6, p99 1.94e-5, max 8.36e-5; the 9 cells above the frozen 2e-5 are extreme moves (worst THETAUSDT 2023-08-17 20:00, 4h return −7.91%) and every cell is within 0.44× the first-order float16 quantisation bound (1+|y|)·Σ|r_i|·2^-11 of the cache path ⇒ definition identical; the bound of 2e-5 was set without the float16 term. (b3) Σ-simple[E,E+47] − Π(1+r)−1[E+1,E+48] at the cell level, bps: 2020 +0.58, 2021 +1.66, 2022 +0.46, 2023 +0.30, 2024 +0.27, 2025 +0.76, 2026 +0.22 (mean |·| 22–46 bps). Book-level effect: §8 (log vs prod calibers).

## 7. G4 leakage battery detail (results/G4a.json, G4b.json)

- (i) every fold: max(train E_ts) + 4h == first test anchor (gap 0 s), train ∩ test = ∅ — PASS 5/5.
- (ii) pre-2022 predictions all NaN; finite mask == members ∧ finite(y4) for 10,128/10,128 anchors; no values on unused anchors — PASS.
- (iii) shuffle-future null, labels permuted within each training year, refit with the production parameters (400 trees), OOS per-anchor Spearman mean; SE = std(per-anchor true IC)/√n: seed 0: 2022 −0.0013, 2023 +0.0022, 2024 −0.0002, 2025 −0.0027, 2026 +0.0047 (all PASS); seed 1: 2022 **+0.0081** (2·SE 0.0061, FAIL), 2023 −0.0031, 2024 +0.0014, 2025 −0.0026, 2026 +0.0022; seed 2: 2022 **+0.0070** (FAIL), 2023 −0.0023, 2024 +0.0022, 2025 −0.0034, 2026 **+0.0098** (2·SE 0.0052, FAIL). True ICs +0.055…+0.064. Information (not the gate): seed-mean null per fold 2022 +0.0046, 2023 −0.0011, 2024 +0.0011, 2025 −0.0029, 2026 +0.0055 vs 2·SE_anchor 0.0061/0.0059/0.0054/0.0053/0.0052 and 2·SE_dayblock 0.0064/0.0061/0.0054/0.0050/0.0059 (4 of 5 folds pass the seed-mean convention; 2026 is marginal). Verdict per frozen rule: **FAIL** ⇒ hist king not admitted.
- (iv) offset spectrum corr(pred_E, y4_{E+k}) k=−6..6: −0.055, −0.056, −0.059, −0.063, −0.071, −0.119, **+0.060**, +0.047, +0.040, +0.037, +0.036, +0.035, +0.031 — peak at k=0, max|k=1..3| 0.047 < 0.060 — PASS.
- (v) embargo invariance (60 anchors): 2024 IC 0.06051 → 0.05938 (Δ −0.0011), 2025 0.06371 → 0.06417 (Δ +0.0005) — PASS; the no-embargo refit reproduces the stage-5 file exactly.
- (vi) three features × 100 anchors recomputed over cache rows [E−w, E−1] are bitwise equal to the stored cells; the shifted window [E−w+1, E] differs in 94/86/20 of 100 ⇒ the last row used is E−1 — PASS.

## 8. G5 tables (results/judge_rebuild.json, results/REPORT_tables.md)

Units: `net_ex` and `net` are bps per anchor at the device's own gross (0.61–0.79, printed per row); `pg` = net / gross_total = bps per anchor per unit gross (the 08-21 comparison unit); ×2190/100 = %/gross/year; the live book runs gross 2.0×NAV. Windows: calendar years 2022–2026 (2026 to 08-15), 2024→26, 2025→26, 2022→26; S = Sharpe (√2190), DD = maxDD (bps), WM = worst calendar month (bps). Kings: pinned = in-service booster (2022–2025 training, re-indexed onto the hist grid, 10,086 rows bitwise equal to the source), hist = rebuilt 2020-start OOS king (only the F1/log pairing exists, from the G2 run, because G4 (iii) excluded it from G5). Calibers: log = raw Σ-simple y4 with CAL=log (no transform); prod = meta y4 replaced by Π(1+r5)−1 over [E+1,E+48] (parity 1.0 on 3,700,640 cells), CAL=log.

Cross-checks against known figures (VERIFIED here, INFERRED equality): F2 pinned/log 2024 = −0.642 S −1.68 DD 1,815 equals the caliber-review figure for the fixed-seat book (2024 −0.64, S −1.68, maxDD 1,815 bps); F2 pinned/log 2024→26 DD 2,614 equals its 2,613.7; F1 pinned/log per-gross 2024/2025/2026 = +0.325/+1.123/+2.321 vs pod_armA_vs_0821.out +0.327/+1.129/+2.351.

Paired Δ(hist − pinned), F1, log caliber, 12,279 anchors, day-block bootstrap: `net_ex` 2024 +0.045 [−0.197, +0.282], 2025 +0.018 [−0.187, +0.228], 2026 −0.051 [−0.297, +0.183], **2024→26 +0.012 [−0.130, +0.151] P(Δ>0)=0.55**, 2025→26 −0.008 [−0.165, +0.150]; 2022 +1.202 [+0.498, +1.896] and 2023 +0.450 [−0.185, +1.063] are "king present vs absent" (the pinned king has no 2022–23 predictions), not a training-start effect. ΔSharpe(2024→26) +0.03, Δturnover −0.7%. σ_fund terciles (cuts 5.33 / 13.77 bps per 8h): Δ low +0.018 [−0.225, +0.271], mid +0.111 [−0.108, +0.339], high −0.093 [−0.311, +0.122].

Caliber effect at the book level (pinned king, `net_ex`, 2024→26): F1 +0.717 (log) → +0.612 (prod), F2 s42 +0.527 → +0.474, F2 s2027 +0.540 → +0.491, F3 s42 +0.766 → +0.756, F3 s2027 +0.817 → +0.807 ⇒ the Σ-simple label overstates the book by 1–15% depending on form (7–10% for the in-service F2). CAL=simple (pseudo-convexity on Σ-simple, from the G2 negative control, F1 hist d30 `net`): 2023 −0.327 vs +0.062, 2024 +0.346 vs +0.161, 2026 +3.304 vs +2.036.

Full level tables (all forms, both calibers, three columns) follow verbatim from results/REPORT_tables.md:


### Levels — column `net_ex` — caliber log [raw Σ-simple y4 over [E,E+47] (rebuilt meta), CAL=log = no transform] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -0.393 S-1.10 DD883 WM-492 | -0.417 S-1.47 DD998 WM-296 | +0.067 S+0.20 DD1293 WM-318 | +0.594 S+1.26 DD601 WM-514 | +1.966 S+3.74 DD406 WM-60 | +0.717 S+1.62 DD1293 WM-514 | +1.119 S+2.27 DD692 WM-514 | +0.231 S+0.59 DD2813 WM-514 | 0.7782 | 0.5283 | 0.03164 |
| F1 | s42 | hist | 12279 | +0.809 S+1.92 DD744 WM-170 | +0.033 S+0.10 DD830 WM-414 | +0.112 S+0.32 DD1339 WM-270 | +0.612 S+1.33 DD561 WM-444 | +1.915 S+3.61 DD406 WM-41 | +0.729 S+1.65 DD1339 WM-444 | +1.111 S+2.28 DD606 WM-444 | +0.596 S+1.43 DD1844 WM-444 | 0.7767 | 0.5507 | 0.03141 |
| F2 | s42 | pinned | 12291 | -0.247 S-0.67 DD1093 WM-468 | -0.381 S-1.20 DD1239 WM-508 | -0.642 S-1.68 DD1815 WM-717 | +0.284 S+0.67 DD902 WM-634 | +2.809 S+4.98 DD458 WM106 | +0.527 S+1.18 DD2614 WM-717 | +1.250 S+2.59 DD902 WM-634 | +0.163 S+0.40 DD3790 WM-717 | 0.7914 | 0.21 | 0.01425 |
| F2 | s2027 | pinned | 12291 | -0.247 S-0.67 DD1093 WM-468 | -0.373 S-1.18 DD1202 WM-519 | -0.629 S-1.65 DD1788 WM-702 | +0.298 S+0.71 DD912 WM-635 | +2.823 S+4.98 DD462 WM114 | +0.540 S+1.21 DD2595 WM-702 | +1.264 S+2.62 DD912 WM-635 | +0.172 S+0.42 DD3752 WM-702 | 0.7904 | 0.21 | 0.01422 |
| F3 | s42 | pinned | 12291 | -0.247 S-0.67 DD1093 WM-468 | -0.373 S-1.21 DD1143 WM-497 | +0.149 S+0.53 DD795 WM-363 | +0.359 S+1.15 DD418 WM-294 | +2.423 S+4.65 DD452 WM71 | +0.766 S+2.11 DD795 WM-363 | +1.149 S+2.83 DD522 WM-294 | +0.300 S+0.85 DD2035 WM-497 | 0.6174 | 0.5875 | 0.03354 |
| F3 | s2027 | pinned | 12291 | -0.247 S-0.67 DD1093 WM-468 | -0.338 S-1.10 DD1098 WM-450 | +0.217 S+0.78 DD740 WM-365 | +0.438 S+1.36 DD430 WM-318 | +2.402 S+4.61 DD460 WM88 | +0.817 S+2.23 DD740 WM-365 | +1.189 S+2.90 DD576 WM-318 | +0.337 S+0.95 DD1886 WM-468 | 0.6246 | 0.5875 | 0.03279 |

### Levels — column `net_ex` — caliber prod [Π(1+r5)-1 over [E+1,E+48] (meta_hist_newprod swap), CAL=log] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -0.500 S-1.38 DD1109 WM-485 | -0.384 S-1.30 DD1038 WM-353 | -0.053 S-0.15 DD1640 WM-422 | +0.571 S+1.21 DD582 WM-507 | +1.757 S+3.44 DD377 WM-34 | +0.612 S+1.39 DD1640 WM-507 | +1.025 S+2.10 DD796 WM-507 | +0.156 S+0.39 DD3312 WM-507 | 0.77 | 0.5466 | 0.03406 |
| F2 | s42 | pinned | 12291 | -0.230 S-0.63 DD1109 WM-479 | -0.404 S-1.27 DD1274 WM-520 | -0.709 S-1.85 DD1913 WM-757 | +0.254 S+0.59 DD849 WM-575 | +2.743 S+4.89 DD352 WM110 | +0.474 S+1.05 DD2657 WM-757 | +1.206 S+2.48 DD849 WM-575 | +0.132 S+0.32 DD3892 WM-757 | 0.7889 | 0.21 | 0.01427 |
| F2 | s2027 | pinned | 12291 | -0.230 S-0.63 DD1109 WM-479 | -0.386 S-1.21 DD1220 WM-529 | -0.694 S-1.82 DD1882 WM-740 | +0.280 S+0.65 DD850 WM-561 | +2.750 S+4.88 DD357 WM124 | +0.491 S+1.09 DD2625 WM-740 | +1.225 S+2.51 DD850 WM-561 | +0.145 S+0.36 DD3819 WM-740 | 0.788 | 0.21 | 0.01425 |
| F3 | s42 | pinned | 12291 | -0.230 S-0.63 DD1109 WM-479 | -0.412 S-1.33 DD1180 WM-545 | +0.116 S+0.43 DD967 WM-375 | +0.339 S+1.06 DD413 WM-275 | +2.464 S+4.79 DD345 WM80 | +0.756 S+2.10 DD967 WM-375 | +1.152 S+2.84 DD546 WM-275 | +0.290 S+0.83 DD2241 WM-545 | 0.6061 | 0.6129 | 0.035 |
| F3 | s2027 | pinned | 12291 | -0.230 S-0.63 DD1109 WM-479 | -0.407 S-1.32 DD1172 WM-534 | +0.197 S+0.73 DD896 WM-364 | +0.399 S+1.22 DD446 WM-312 | +2.452 S+4.77 DD364 WM93 | +0.807 S+2.22 DD896 WM-364 | +1.184 S+2.89 DD586 WM-312 | +0.320 S+0.91 DD2142 WM-534 | 0.6138 | 0.6129 | 0.03427 |

### Levels — column `net` — caliber log [raw Σ-simple y4 over [E,E+47] (rebuilt meta), CAL=log = no transform] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -0.465 S-1.26 DD1025 WM-589 | -0.352 S-1.16 DD1097 WM-301 | +0.131 S+0.37 DD1087 WM-337 | +0.802 S+1.84 DD547 WM-451 | +2.037 S+3.90 DD416 WM-63 | +0.837 S+1.95 DD1087 WM-451 | +1.275 S+2.71 DD706 WM-451 | +0.298 S+0.76 DD2655 WM-589 | 0.7782 | 0.5283 | 0.03164 |
| F1 | s42 | hist | 12279 | +0.792 S+1.99 DD539 WM-175 | +0.062 S+0.19 DD742 WM-383 | +0.161 S+0.45 DD1101 WM-255 | +0.812 S+1.92 DD510 WM-432 | +2.036 S+3.79 DD419 WM-36 | +0.852 S+1.98 DD1101 WM-432 | +1.280 S+2.73 DD606 WM-432 | +0.668 S+1.65 DD1578 WM-432 | 0.7767 | 0.5507 | 0.03141 |
| F2 | s42 | pinned | 12291 | -0.116 S-0.20 DD1333 WM-472 | -0.319 S-0.95 DD1007 WM-491 | -0.594 S-1.26 DD1843 WM-535 | +0.355 S+0.67 DD600 WM-542 | +2.860 S+4.59 DD464 WM71 | +0.584 S+1.10 DD2334 WM-542 | +1.313 S+2.32 DD600 WM-542 | +0.237 S+0.47 DD3053 WM-542 | 0.7914 | 0.21 | 0.01425 |
| F2 | s2027 | pinned | 12291 | -0.116 S-0.20 DD1333 WM-472 | -0.307 S-0.91 DD954 WM-514 | -0.602 S-1.28 DD1866 WM-538 | +0.363 S+0.69 DD610 WM-549 | +2.869 S+4.58 DD468 WM76 | +0.586 S+1.10 DD2368 WM-549 | +1.321 S+2.33 DD610 WM-549 | +0.241 S+0.48 DD3052 WM-549 | 0.7904 | 0.21 | 0.01422 |
| F3 | s42 | pinned | 12291 | -0.116 S-0.20 DD1333 WM-472 | -0.367 S-1.09 DD838 WM-590 | +0.132 S+0.42 DD832 WM-444 | +0.440 S+1.11 DD380 WM-270 | +2.482 S+4.33 DD458 WM38 | +0.805 S+1.91 DD832 WM-444 | +1.221 S+2.58 DD520 WM-270 | +0.352 S+0.80 DD1821 WM-590 | 0.6174 | 0.5875 | 0.03354 |
| F3 | s2027 | pinned | 12291 | -0.116 S-0.20 DD1333 WM-472 | -0.315 S-0.94 DD758 WM-536 | +0.180 S+0.57 DD820 WM-446 | +0.503 S+1.24 DD395 WM-245 | +2.450 S+4.30 DD466 WM54 | +0.839 S+1.99 DD820 WM-446 | +1.248 S+2.62 DD571 WM-245 | +0.383 S+0.87 DD1648 WM-536 | 0.6246 | 0.5875 | 0.03279 |

### Levels — column `net` — caliber prod [Π(1+r5)-1 over [E+1,E+48] (meta_hist_newprod swap), CAL=log] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -0.500 S-1.31 DD1105 WM-577 | -0.330 S-1.05 DD1119 WM-352 | +0.023 S+0.07 DD1399 WM-371 | +0.715 S+1.63 DD593 WM-472 | +1.802 S+3.56 DD385 WM-48 | +0.707 S+1.66 DD1399 WM-472 | +1.131 S+2.43 DD815 WM-472 | +0.222 S+0.56 DD2977 WM-577 | 0.77 | 0.5466 | 0.03406 |
| F2 | s42 | pinned | 12291 | -0.033 S-0.06 DD1295 WM-473 | -0.352 S-1.04 DD1042 WM-517 | -0.685 S-1.42 DD1962 WM-603 | +0.381 S+0.70 DD616 WM-495 | +2.813 S+4.49 DD364 WM78 | +0.548 S+1.01 DD2408 WM-603 | +1.312 S+2.28 DD616 WM-495 | +0.228 S+0.45 DD3230 WM-603 | 0.7889 | 0.21 | 0.01427 |
| F2 | s2027 | pinned | 12291 | -0.033 S-0.06 DD1295 WM-473 | -0.329 S-0.98 DD975 WM-543 | -0.694 S-1.45 DD1999 WM-594 | +0.408 S+0.75 DD555 WM-482 | +2.817 S+4.48 DD369 WM87 | +0.556 S+1.02 DD2430 WM-594 | +1.330 S+2.30 DD555 WM-482 | +0.237 S+0.47 DD3187 WM-594 | 0.788 | 0.21 | 0.01425 |
| F3 | s42 | pinned | 12291 | -0.033 S-0.06 DD1295 WM-473 | -0.398 S-1.18 DD895 WM-636 | +0.098 S+0.32 DD948 WM-460 | +0.436 S+1.10 DD366 WM-255 | +2.547 S+4.50 DD356 WM51 | +0.805 S+1.94 DD948 WM-460 | +1.244 S+2.65 DD518 WM-255 | +0.364 S+0.83 DD2018 WM-636 | 0.6061 | 0.6129 | 0.035 |
| F3 | s2027 | pinned | 12291 | -0.033 S-0.06 DD1295 WM-473 | -0.386 S-1.14 DD869 WM-625 | +0.151 S+0.49 DD918 WM-453 | +0.482 S+1.18 DD391 WM-255 | +2.521 S+4.47 DD376 WM63 | +0.837 S+2.00 DD918 WM-453 | +1.262 S+2.66 DD548 WM-255 | +0.384 S+0.88 DD1932 WM-625 | 0.6138 | 0.6129 | 0.03427 |

### Levels — column `pg` — caliber log [raw Σ-simple y4 over [E,E+47] (rebuilt meta), CAL=log = no transform] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -0.744 S-1.05 DD1787 WM-879 | -0.556 S-1.18 DD1634 WM-496 | +0.325 S+0.66 DD1369 WM-372 | +1.123 S+1.93 DD793 WM-691 | +2.321 S+3.96 DD446 WM-79 | +1.101 S+2.00 DD1369 WM-691 | +1.581 S+2.71 DD793 WM-691 | +0.343 S+0.60 DD3976 WM-879 | 0.7782 | 0.5283 | 0.03164 |
| F1 | s42 | hist | 12279 | +1.115 S+1.78 DD877 WM-264 | +0.054 S+0.11 DD1110 WM-571 | +0.355 S+0.72 DD1346 WM-305 | +1.205 S+2.11 DD771 WM-643 | +2.279 S+3.83 DD469 WM-46 | +1.134 S+2.07 DD1346 WM-643 | +1.616 S+2.78 DD771 WM-643 | +0.896 S+1.62 DD2121 WM-643 | 0.7767 | 0.5507 | 0.03141 |
| F2 | s42 | pinned | 12291 | -0.240 S-0.30 DD1615 WM-515 | -0.377 S-0.98 DD1194 WM-523 | -0.767 S-1.30 DD2334 WM-648 | +0.515 S+0.71 DD759 WM-667 | +3.719 S+4.57 DD607 WM95 | +0.782 S+1.12 DD2945 WM-667 | +1.741 S+2.29 DD759 WM-667 | +0.310 S+0.46 DD4249 WM-667 | 0.7914 | 0.21 | 0.01425 |
| F2 | s2027 | pinned | 12291 | -0.240 S-0.30 DD1615 WM-515 | -0.365 S-0.94 DD1133 WM-552 | -0.774 S-1.32 DD2357 WM-658 | +0.527 S+0.72 DD764 WM-679 | +3.701 S+4.56 DD609 WM102 | +0.779 S+1.11 DD2986 WM-679 | +1.741 S+2.29 DD764 WM-679 | +0.311 S+0.46 DD4255 WM-679 | 0.7904 | 0.21 | 0.01422 |
| F3 | s42 | pinned | 12291 | -0.240 S-0.30 DD1615 WM-515 | -0.440 S-1.10 DD1028 WM-638 | +0.566 S+1.14 DD1160 WM-549 | +0.849 S+1.30 DD897 WM-783 | +3.169 S+4.33 DD578 WM52 | +1.289 S+2.08 DD1160 WM-783 | +1.737 S+2.54 DD897 WM-783 | +0.584 S+0.93 DD2776 WM-783 | 0.6174 | 0.5875 | 0.03354 |
| F3 | s2027 | pinned | 12291 | -0.240 S-0.30 DD1615 WM-515 | -0.377 S-0.95 DD944 WM-572 | +0.613 S+1.24 DD1126 WM-549 | +0.945 S+1.44 DD781 WM-645 | +3.116 S+4.31 DD584 WM72 | +1.331 S+2.15 DD1126 WM-645 | +1.776 S+2.60 DD781 WM-645 | +0.622 S+0.99 DD2544 WM-645 | 0.6246 | 0.5875 | 0.03279 |

### Levels — column `pg` — caliber prod [Π(1+r5)-1 over [E+1,E+48] (meta_hist_newprod swap), CAL=log] — arm d30_n2_c42

| arm | seed | king | n | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | gross 24→26 | w_king 24→26 | turn 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | pinned | 12279 | -1.001 S-1.49 DD2218 WM-856 | -0.479 S-1.03 DD1499 WM-514 | +0.210 S+0.42 DD1752 WM-432 | +1.044 S+1.79 DD822 WM-691 | +2.072 S+3.60 DD426 WM-65 | +0.968 S+1.75 DD1752 WM-691 | +1.437 S+2.48 DD866 WM-691 | +0.229 S+0.41 DD4710 WM-856 | 0.77 | 0.5466 | 0.03406 |
| F2 | s42 | pinned | 12291 | -0.121 S-0.15 DD1599 WM-517 | -0.415 S-1.07 DD1235 WM-554 | -0.881 S-1.45 DD2500 WM-708 | +0.551 S+0.74 DD807 WM-608 | +3.681 S+4.46 DD481 WM104 | +0.743 S+1.03 DD3054 WM-708 | +1.748 S+2.25 DD807 WM-608 | +0.305 S+0.45 DD4464 WM-708 | 0.7889 | 0.21 | 0.01427 |
| F2 | s2027 | pinned | 12291 | -0.121 S-0.15 DD1599 WM-517 | -0.390 S-1.01 DD1156 WM-585 | -0.887 S-1.47 DD2532 WM-706 | +0.589 S+0.78 DD731 WM-596 | +3.658 S+4.44 DD485 WM115 | +0.750 S+1.04 DD3073 WM-706 | +1.763 S+2.26 DD738 WM-596 | +0.315 S+0.46 DD4409 WM-706 | 0.788 | 0.21 | 0.01425 |
| F3 | s42 | pinned | 12291 | -0.121 S-0.15 DD1599 WM-517 | -0.474 S-1.19 DD1094 WM-679 | +0.583 S+1.18 DD1311 WM-541 | +0.910 S+1.38 DD899 WM-748 | +3.282 S+4.51 DD450 WM68 | +1.345 S+2.17 DD1311 WM-748 | +1.817 S+2.65 DD899 WM-748 | +0.634 S+1.01 DD3007 WM-748 | 0.6061 | 0.6129 | 0.035 |
| F3 | s2027 | pinned | 12291 | -0.121 S-0.15 DD1599 WM-517 | -0.457 S-1.15 DD1048 WM-666 | +0.644 S+1.31 DD1257 WM-530 | +0.971 S+1.47 DD798 WM-617 | +3.234 S+4.49 DD475 WM83 | +1.381 S+2.23 DD1257 WM-617 | +1.837 S+2.68 DD798 WM-617 | +0.658 S+1.05 DD2866 WM-666 | 0.6138 | 0.6129 | 0.03427 |

### Δ(hist − pinned) — column `net_ex` — caliber log — paired by anchor, UTC-day block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)

| arm | seed | n common | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | ΔSharpe 24→26 | Δturn% 24→26 | maxDD pinned/hist 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | 12279 | +1.202 [+0.498,+1.896] 1.000 | +0.450 [-0.185,+1.063] 0.912 | +0.045 [-0.197,+0.282] 0.651 | +0.018 [-0.187,+0.228] 0.538 | -0.051 [-0.297,+0.183] 0.324 | +0.012 [-0.130,+0.151] 0.550 | -0.008 [-0.165,+0.150] 0.447 | +0.364 [+0.153,+0.576] 0.999 | +0.03 | -0.7% | 1293/1339 |

### Δ(hist − pinned) — column `net_ex` — caliber prod — paired by anchor, UTC-day block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)

| arm | seed | n common | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | ΔSharpe 24→26 | Δturn% 24→26 | maxDD pinned/hist 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Δ(hist − pinned) — column `pg` — caliber log — paired by anchor, UTC-day block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)

| arm | seed | n common | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | ΔSharpe 24→26 | Δturn% 24→26 | maxDD pinned/hist 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | s42 | 12279 | +1.859 [+0.680,+3.052] 0.999 | +0.610 [-0.321,+1.560] 0.899 | +0.031 [-0.335,+0.422] 0.567 | +0.083 [-0.211,+0.369] 0.712 | -0.042 [-0.319,+0.232] 0.387 | +0.033 [-0.160,+0.238] 0.637 | +0.035 [-0.182,+0.251] 0.610 | +0.553 [+0.199,+0.901] 0.998 | +0.07 | -0.7% | 1369/1346 |

### Δ(hist − pinned) — column `pg` — caliber prod — paired by anchor, UTC-day block bootstrap NB=2000 seed=20260905; cells: Δ [CI95] P(Δ>0)

| arm | seed | n common | 2022 | 2023 | 2024 | 2025 | 2026 | 2024->26 | 2025->26 | 2022->26 | ΔSharpe 24→26 | Δturn% 24→26 | maxDD pinned/hist 24→26 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### σ_fund terciles (2024→26) — column `net_ex` — caliber log: per tercile pinned mean → hist mean, Δ [CI95] P(Δ>0)

| arm | seed | tercile | n | σ_fund mean (bps/8h) | pinned | hist | Δ [CI95] P |
|---|---|---|---|---|---|---|---|
| F1 | s42 | low | 1915 | 3.202 | -0.025 | -0.007 | +0.018 [-0.225,+0.271] 0.56 |
| F1 | s42 | mid | 1914 | 9.458 | +1.476 | +1.587 | +0.111 [-0.108,+0.339] 0.84 |
| F1 | s42 | high | 1914 | 21.201 | +0.700 | +0.607 | -0.093 [-0.311,+0.122] 0.21 |
| F2 | s42 | low | 1915 | 3.202 | -0.817 | — | — |
| F2 | s42 | mid | 1914 | 9.458 | +0.332 | — | — |
| F2 | s42 | high | 1914 | 21.201 | +2.065 | — | — |
| F2 | s2027 | low | 1915 | 3.202 | -0.813 | — | — |
| F2 | s2027 | mid | 1914 | 9.458 | +0.360 | — | — |
| F2 | s2027 | high | 1914 | 21.201 | +2.074 | — | — |
| F3 | s42 | low | 1915 | 3.202 | +0.068 | — | — |
| F3 | s42 | mid | 1914 | 9.458 | +0.980 | — | — |
| F3 | s42 | high | 1914 | 21.201 | +1.252 | — | — |
| F3 | s2027 | low | 1915 | 3.202 | +0.122 | — | — |
| F3 | s2027 | mid | 1914 | 9.458 | +1.036 | — | — |
| F3 | s2027 | high | 1914 | 21.201 | +1.295 | — | — |

### σ_fund terciles (2024→26) — column `net_ex` — caliber prod: per tercile pinned mean → hist mean, Δ [CI95] P(Δ>0)

| arm | seed | tercile | n | σ_fund mean (bps/8h) | pinned | hist | Δ [CI95] P |
|---|---|---|---|---|---|---|---|
| F1 | s42 | low | 1915 | 3.202 | -0.210 | — | — |
| F1 | s42 | mid | 1914 | 9.458 | +1.477 | — | — |
| F1 | s42 | high | 1914 | 21.201 | +0.571 | — | — |
| F2 | s42 | low | 1915 | 3.202 | -0.874 | — | — |
| F2 | s42 | mid | 1914 | 9.458 | +0.260 | — | — |
| F2 | s42 | high | 1914 | 21.201 | +2.036 | — | — |
| F2 | s2027 | low | 1915 | 3.202 | -0.866 | — | — |
| F2 | s2027 | mid | 1914 | 9.458 | +0.294 | — | — |
| F2 | s2027 | high | 1914 | 21.201 | +2.045 | — | — |
| F3 | s42 | low | 1915 | 3.202 | +0.009 | — | — |
| F3 | s42 | mid | 1914 | 9.458 | +0.957 | — | — |
| F3 | s42 | high | 1914 | 21.201 | +1.302 | — | — |
| F3 | s2027 | low | 1915 | 3.202 | +0.078 | — | — |
| F3 | s2027 | mid | 1914 | 9.458 | +1.006 | — | — |
| F3 | s2027 | high | 1914 | 21.201 | +1.337 | — | — |

### σ_fund terciles (2024→26) — column `pg` — caliber log: per tercile pinned mean → hist mean, Δ [CI95] P(Δ>0)

| arm | seed | tercile | n | σ_fund mean (bps/8h) | pinned | hist | Δ [CI95] P |
|---|---|---|---|---|---|---|---|
| F1 | s42 | low | 1915 | 3.202 | +0.339 | +0.408 | +0.069 [-0.302,+0.439] 0.64 |
| F1 | s42 | mid | 1914 | 9.458 | +1.966 | +2.134 | +0.169 [-0.192,+0.506] 0.83 |
| F1 | s42 | high | 1914 | 21.201 | +0.998 | +0.860 | -0.138 [-0.421,+0.154] 0.18 |
| F2 | s42 | low | 1915 | 3.202 | -0.834 | — | — |
| F2 | s42 | mid | 1914 | 9.458 | +0.793 | — | — |
| F2 | s42 | high | 1914 | 21.201 | +2.386 | — | — |
| F2 | s2027 | low | 1915 | 3.202 | -0.850 | — | — |
| F2 | s2027 | mid | 1914 | 9.458 | +0.803 | — | — |
| F2 | s2027 | high | 1914 | 21.201 | +2.386 | — | — |
| F3 | s42 | low | 1915 | 3.202 | +0.555 | — | — |
| F3 | s42 | mid | 1914 | 9.458 | +1.714 | — | — |
| F3 | s42 | high | 1914 | 21.201 | +1.598 | — | — |
| F3 | s2027 | low | 1915 | 3.202 | +0.611 | — | — |
| F3 | s2027 | mid | 1914 | 9.458 | +1.673 | — | — |
| F3 | s2027 | high | 1914 | 21.201 | +1.710 | — | — |

### σ_fund terciles (2024→26) — column `pg` — caliber prod: per tercile pinned mean → hist mean, Δ [CI95] P(Δ>0)

| arm | seed | tercile | n | σ_fund mean (bps/8h) | pinned | hist | Δ [CI95] P |
|---|---|---|---|---|---|---|---|
| F1 | s42 | low | 1915 | 3.202 | +0.122 | — | — |
| F1 | s42 | mid | 1914 | 9.458 | +1.978 | — | — |
| F1 | s42 | high | 1914 | 21.201 | +0.805 | — | — |
| F2 | s42 | low | 1915 | 3.202 | -0.906 | — | — |
| F2 | s42 | mid | 1914 | 9.458 | +0.724 | — | — |
| F2 | s42 | high | 1914 | 21.201 | +2.412 | — | — |
| F2 | s2027 | low | 1915 | 3.202 | -0.920 | — | — |
| F2 | s2027 | mid | 1914 | 9.458 | +0.760 | — | — |
| F2 | s2027 | high | 1914 | 21.201 | +2.410 | — | — |
| F3 | s42 | low | 1915 | 3.202 | +0.529 | — | — |
| F3 | s42 | mid | 1914 | 9.458 | +1.777 | — | — |
| F3 | s42 | high | 1914 | 21.201 | +1.730 | — | — |
| F3 | s2027 | low | 1915 | 3.202 | +0.590 | — | — |
| F3 | s2027 | mid | 1914 | 9.458 | +1.709 | — | — |
| F3 | s2027 | high | 1914 | 21.201 | +1.843 | — | — |

## 9. Deviations from the prereg and incidents (all logged in logs/commands.txt and logs/chain.log)

1. Download rate: paced 4 req/s with anchor pauses as instructed until 02:02Z; two switches to the unlimited variant by another agent citing the user ruling; verified in STATE.md §4 commit 6b38cbb and accepted from 02:30Z. The files written by the fast variant are valid (same code path, 0 errors, 0 bad zips).
2. P1b temp-name patch of pod_build_wide_ext.py (path only; the verbatim script cannot complete on numpy ≥1.x, INFERRED that the 08-21 run renamed the file by hand).
3. P2-mem restructuring of pod_fea_wide_hist.py under the 61 GB container limit; byte-identical outputs on the dry inputs (receipt above).
4. Reference for G2(a): the pod copies of nets_histv2_* are 144-byte stubs; the real 08-21 files came from the Mac scratchpad of session 6737834a (pod_backup, Aug 21 11:34; sha 77375782… and 9a165939…), together with the 08-21 king (83f57477…) and meta (0ca2e235…). The repo's 9,941-row per-gross reference is bitwise the same file as that scratchpad's nets_histv2_-30_2_42_pergross.npy (sha 0f548011…) = the d30 nets truncated at 2022-01-31 08:00.
5. DIAG-A/DIAG-B (masked-funding panel and the real 08-21 king through the stage-6 device) are diagnostics for classifying G2(a); they are not gates and not G5 arms; the chain's G5 used the unmasked rebuilt panel as prescribed.
6. G3(b2) sampling: one random member per sampled anchor with all 48 bars present (missing bars are zero-return by the target definition); 10 anchors skipped; the float16 bound is reported as information.
7. G4 (iii) SE definition fixed before the run as anchor-level std/√n (dlw_judge convention); seed-mean and day-block variants reported as information only.
8. The pinned king had to be re-indexed from the v2ext anchor grid onto the hist grid (adapter, rows bitwise equal to the source) because the device asserts the canonical king shape.
9. The 08-21 chain ran on the old pod (transcript 2026-08-21T02:01:44Z), not on jpline; the panel-producing script already had today's sha (db7f0474) at commit 236a702 (01:05Z that day).

## 10. Patches and file hashes (every diff in logs/patches/, sha256 first 16)

| file | sha256 (16) | bytes |
|---|---|---|
| 08_setup_dev.diff | 6e1f4f1d2b312940 | 4306 |
| 10_G5_arms.diff | 9d72b87c994a7037 | 4954 |
| dl_klines_fast.diff | c24a1975e6606c88 | 1614 |
| dl_klines_paced.diff | 5c7d46b53ea58a3b | 10328 |
| judge_rebuild.diff | 5a0ccaec85d3aa47 | 27930 |
| pod_build_wide_ext.py.diff | adeed9f959aa8c42 | 2588 |
| pod_fea_wide_hist.py.diff | 3ac2fd9873c2ae8f | 3185 |
| pod_panel_ext.py.diff | 7b9f6fa765fc15a1 | 1278 |
| pod_slow_hist_folds.py.diff | 9b55534c536312a7 | 2001 |
| pod_stop_arms_v3.py.diff | 03e8c3f08ee09998 | 2296 |
| data/dlnative_5m_wide829_f16_hist.npz | 5d5fd0f2f7622465 | 2290946807 |
| data/wide_panel_4h_hist_v2_rebuilt.npz | 9f3e4ae14ef9ff1e | 259081104 |
| data/wide_fea_hist_rebuilt.npy | 3568c673b274959b | 1765388788 |
| data/wide_fea_hist_meta_rebuilt.npz | 509d8b5453239391 | 27831856 |
| data/slow_pred_hist_oos_rebuilt.npy | 1090418fa793f87c | 43058388 |
| data/nets_histv2_-30_2_42.npy | c1eaca5318a911a5 | 196592 |
| data/nets_histv2_0_0_0.npy | b56d7c61917423ed | 196592 |
| data/dlw_hist/data/dlw_targets.npz | ba10902ef312bb9c | 240180930 |
| data/meta_hist_newprod.npz | 60af00925262f3db | 110685571 |
| data/slow_pred_pinned_on_hist.npy | f48b57f9aff20dce | 43058388 |
| logs/klines5m_SHA256SUMS.txt | 1cf680ab883e0602 | 3625156 |
| logs/klines5m_404.txt | 4ef3553af5d2d6f3 | 2093168 |

Path-only hunks: pod_build_wide_ext.py (lock, symbols file, zip tree, temp name), pod_panel_ext.py (zload import path), pod_fea_wide_hist.py (zload path + P2-mem), pod_slow_hist_folds.py (two output paths), pod_stop_arms_v3.py (two output paths); w10_universe_recheck.py and pod_dlw_targets_ext.py ran verbatim (env paths); judge_rebuild.py is an adaptation of rolling_king judge.py (layout, arms, windows, columns; diff 27,930 bytes); dl_klines_paced.py merges the two repo downloaders (diff vs pod_hist_dl.py 10,328 bytes); dl_klines_fast.diff is the other agent's variant.

## 11. What this run does not show / open items

- UNRESOLVED: the rebuilt king's admission — the frozen (iii) rule fails on 3 of 15 runs; the nulls are ten times smaller than the true IC and symmetric around zero, which is the signature of chance feature pick-up by a noise fit rather than of leakage, but only a re-ruling can admit the king. Consequently the F2/F3 hist-king arms were not run; the hist-vs-pinned separation rests on F1/log alone.
- UNRESOLVED: whether the 08-21 tree's August tail was produced by a pull not in git (INFERRED from the coverage pattern).
- The August-2026 interval column and the 375-symbol funding coverage are data-source choices, not code; a "08-21-faithful" instrument needs the 450-symbol funding mask (DIAG-A shows this reproduces 08-21), while the prereg's "rebuilt panel" instrument has the wider coverage and a lower book.
- LightGBM refit variance across machines is as large as the other effects (2025 −0.19, 2026 −0.27 bps/anchor at the book level with identical training data); any cross-instrument comparison of king-dependent books must pin the booster file, not the training recipe.

## Appendix A — every command, verbatim (logs/commands.txt)

```
CMD[launch] 2026-09-05T01:13:02Z: cd /workspace/review_scratch/jpline_rebuild && nohup bash run_chain.sh > logs/chain_nohup.out 2>&1 &
CMD[01_download] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T01:13:02Z: env DL_RATE=4.0 DL_THREADS=8 /workspace/venv/bin/python patched/dl_klines_paced.py
CMD[manual-switch] 2026-09-05T02:01:57Z: kill -TERM 65205 65214 65217   # user ruling 解除限速; paced chain stopped; stage 01 now runs patched/dl_klines_fast.py (DL_RATE=1000000 DL_THREADS=24 DL_PAUSE=0)
CMD[manual-switch] 2026-09-05T02:02:01Z: nohup bash run_chain.sh >> logs/chain_nohup.out 2>&1 &  (pid 69041)
CMD[01_download] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:02:01Z: env DL_RATE=1000000 DL_THREADS=24 DL_PAUSE=0 /workspace/venv/bin/python patched/dl_klines_fast.py
RC[01_download] rc=143 2026-09-05T02:10:49Z
CMD[relaunch-paced] 2026-09-05T02:12:54Z: restored stages/01_download.sh (paced, sha f458dbc52bf6dc3e); nohup bash run_chain.sh >> logs/chain_nohup.out 2>&1 &   # after killing the unauthorised fast chain at 02:10:49Z
CMD[01_download] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:12:55Z: env DL_RATE=4.0 DL_THREADS=8 /workspace/venv/bin/python patched/dl_klines_paced.py
CMD[manual-switch-2] 2026-09-05T02:21:25Z: kill -TERM 69952 69963 69968   # second manual switch to fast variant per user ruling 解除限速 (STATE §4 6b38cbb); agent had reverted at 02:10Z without having received the ruling
CMD[manual-switch-2] 2026-09-05T02:21:29Z: nohup bash run_chain.sh >> logs/chain_nohup.out 2>&1 &  (pid 71684)
CMD[01_download] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:21:29Z: env DL_RATE=1000000 DL_THREADS=24 DL_PAUSE=0 /workspace/venv/bin/python patched/dl_klines_fast.py
NOTE[agent] 2026-09-05T02:28:26Z: ruling verified in repo STATE.md §4 commit 6b38cbb (user, 01:49Z) — fast variant authorised; no further reverts by this agent
RC[01_download] rc=0 2026-09-05T02:42:00Z
CMD[01b_manifest] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:42:09Z: bash -c find klines5m -name '*.zip' | sort | xargs -P 16 -n 200 sha256sum > logs/klines5m_SHA256SUMS.txt
RC[01b_manifest] rc=0 2026-09-05T02:42:24Z
CMD[01b_manifest] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:42:24Z: bash -c find klines5m -name '*.404' | sort > logs/klines5m_404.txt
RC[01b_manifest] rc=0 2026-09-05T02:42:25Z
CMD[01b_manifest] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:42:26Z: /workspace/venv/bin/python -
RC[01b_manifest] rc=0 2026-09-05T02:43:04Z
CMD[01b_manifest] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:43:04Z: bash -c sha256sum logs/klines5m_SHA256SUMS.txt logs/klines5m_404.txt logs/klines5m_badzips.txt
RC[01b_manifest] rc=0 2026-09-05T02:43:04Z
CMD[02_cache] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:43:04Z: env EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz /workspace/venv/bin/python patched/pod_build_wide_ext.py
RC[02_cache] rc=1 2026-09-05T02:46:04Z
NOTE[agent] 2026-09-05T02:47:36Z: stage 02 crashed at verbatim L48 (np.savez_compressed appended .npz to the .tmp name; 2,290,946,807-byte *.npz.tmp.npz written 02:46:03Z); applied path-only patch P1b (temp name ends with .npz), removed the stale temp file, resuming chain at 02
CMD[02_cache] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:47:36Z: env EXT_START=2020-01-01 EXT_END=2026-08-16 EXT_OUT=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz /workspace/venv/bin/python patched/pod_build_wide_ext.py
RC[02_cache] rc=0 2026-09-05T02:50:51Z
CMD[02_cache] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:50:51Z: sha256sum data/dlnative_5m_wide829_f16_hist.npz
RC[02_cache] rc=0 2026-09-05T02:50:58Z
CMD[03_panel] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:51:01Z: env CACHE_IN=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz PANEL_OUT=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz /workspace/venv/bin/python patched/pod_panel_ext.py
RC[03_panel] rc=3 2026-09-05T02:57:11Z
CMD[03_panel] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:57:11Z: sha256sum data/wide_panel_4h_hist_v2_rebuilt.npz
RC[03_panel] rc=0 2026-09-05T02:57:12Z
CMD[03g_G1] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:57:12Z: /workspace/venv/bin/python gates/gate_G1.py
RC[03g_G1] rc=0 2026-09-05T02:59:34Z
CMD[04_fea] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T02:59:34Z: env CACHE_IN=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz FEA_OUT=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_rebuilt.npy META_OUT=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz /workspace/venv/bin/python patched/pod_fea_wide_hist.py
RC[04_fea] rc=137 2026-09-05T03:03:10Z
CMD[04_fea_memparity] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:06:05Z: env CACHE_IN=/workspace/data/dlnative_5m_wide829_f16_ext.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/drytest/data/wide_panel_4h_hist_v2_rebuilt.npz FEA_OUT=/workspace/review_scratch/jpline_rebuild/drytest/data/fea_memtest.npy META_OUT=/workspace/review_scratch/jpline_rebuild/drytest/data/meta_memtest.npz /workspace/venv/bin/python patched/pod_fea_wide_hist.py
NOTE[agent] 2026-09-05T03:09:31Z: P2-mem parity = byte-identical files (sha256 equal for FEA and meta); the auxiliary np.array_equal check failed only on the string names array (isnan). Resuming chain at 04_fea.
CMD[04_fea] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:09:31Z: env CACHE_IN=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz FEA_OUT=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_rebuilt.npy META_OUT=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz /workspace/venv/bin/python patched/pod_fea_wide_hist.py
RC[04_fea] rc=0 2026-09-05T03:13:24Z
CMD[04_fea] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:13:24Z: sha256sum data/wide_fea_hist_rebuilt.npy data/wide_fea_hist_meta_rebuilt.npz
RC[04_fea] rc=0 2026-09-05T03:13:29Z
CMD[04_fea] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:13:29Z: /workspace/venv/bin/python gates/compare_meta.py
RC[04_fea] rc=0 2026-09-05T03:13:31Z
CMD[05_king] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:13:40Z: env FEA_IN=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_rebuilt.npy META_IN=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz /workspace/venv/bin/python patched/pod_slow_hist_folds.py
RC[05_king] rc=0 2026-09-05T03:14:32Z
CMD[05_king] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:14:32Z: sha256sum data/slow_pred_hist_oos_rebuilt.npy data/slow_hist_folds_rebuilt.json
RC[05_king] rc=0 2026-09-05T03:14:32Z
CMD[05_king] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:14:32Z: /workspace/venv/bin/python gates/compare_king.py
RC[05_king] rc=0 2026-09-05T03:14:40Z
CMD[05g_G4a] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:14:40Z: /workspace/venv/bin/python gates/gate_G4a.py
RC[05g_G4a] rc=0 2026-09-05T03:15:40Z
CMD[06_stop_arms] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:15:40Z: env TAG=histv2 META_IN=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz KING_IN=/workspace/review_scratch/jpline_rebuild/data/slow_pred_hist_oos_rebuilt.npy /workspace/venv/bin/python patched/pod_stop_arms_v3.py
RC[06_stop_arms] rc=0 2026-09-05T03:16:18Z
CMD[06_stop_arms] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:16:18Z: sha256sum data/nets_histv2_0_0_0.npy data/nets_histv2_-30_2_42.npy data/nets_histv2_-25_2_42.npy data/nets_histv2_-25_1_42.npy data/stop_arms_pod_v3_histv2.json
RC[06_stop_arms] rc=0 2026-09-05T03:16:18Z
CMD[06g_G2a] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:16:18Z: /workspace/venv/bin/python gates/gate_G2a.py
RC[06g_G2a] rc=0 2026-09-05T03:16:19Z
CMD[06g_G2a] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:16:19Z: /workspace/venv/bin/python gates/diag_g2a.py
CMD[06g_diag] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:16:49Z: env TAG=diagA META_IN=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt_fund450_DIAG.npz KING_IN=/workspace/review_scratch/jpline_rebuild/data/king0821_on_rebuilt_meta_DIAG.npy /workspace/venv/bin/python /workspace/review_scratch/jpline_rebuild/patched/pod_stop_arms_v3.py
RC[06g_diag] diagA rc=0
CMD[06g_diag] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:17:27Z: env TAG=diagB META_IN=/workspace/review_scratch/jpline_rebuild/data/wide_fea_hist_meta_rebuilt.npz PANEL_IN=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz KING_IN=/workspace/review_scratch/jpline_rebuild/data/king0821_on_rebuilt_meta_DIAG.npy /workspace/venv/bin/python /workspace/review_scratch/jpline_rebuild/patched/pod_stop_arms_v3.py
RC[06g_diag] diagB rc=0
RC[06g_G2a] rc=0 2026-09-05T03:18:04Z
CMD[07_targets] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:18:04Z: env DLWT_CACHE=/workspace/review_scratch/jpline_rebuild/data/dlnative_5m_wide829_f16_hist.npz DLWT_PANEL=/workspace/review_scratch/jpline_rebuild/data/wide_panel_4h_hist_v2_rebuilt.npz DLWT_OUT=/workspace/review_scratch/jpline_rebuild/data/dlw_hist /workspace/venv/bin/python src/pod_dlw_targets_ext.py
RC[07_targets] rc=0 2026-09-05T03:19:22Z
CMD[07_targets] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:19:22Z: sha256sum data/dlw_hist/data/dlw_targets.npz data/dlw_hist/results/dlw_targets_report.json
RC[07_targets] rc=0 2026-09-05T03:19:22Z
CMD[07g_G3] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:19:22Z: /workspace/venv/bin/python gates/gate_G3.py
RC[07g_G3] rc=0 2026-09-05T03:21:25Z
CMD[08_setup_dev] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:21:25Z: /workspace/venv/bin/python gates/make_pinned_on_hist.py
RC[08_setup_dev] rc=0 2026-09-05T03:21:27Z
CMD[08_setup_dev] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:21:27Z: /workspace/venv/bin/python gates/build_alt_meta_hist.py
RC[08_setup_dev] rc=0 2026-09-05T03:22:51Z
CMD[08_arms_g2] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:22:52Z: env LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_hist_oos_rebuilt.npy LEGS=111 PHI=0 FSEED=42 CAL=log OUT_TAG=F1_hist_log /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[08_arms_g2] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:22:52Z: env LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_hist_oos_rebuilt.npy LEGS=111 PHI=0 FSEED=42 CAL=simple OUT_TAG=F1_hist_simple /workspace/venv/bin/python ../w10_universe_recheck.py
RC[08_arms_g2] F1_hist_log 0 2026-09-05T03:23:19Z
RC[08_arms_g2] F1_hist_simple 0 2026-09-05T03:23:19Z
CMD[08g_G2bc] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:23:19Z: /workspace/venv/bin/python gates/gate_G2bc.py
RC[08g_G2bc] rc=0 2026-09-05T03:23:20Z
CMD[09_G4b] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:23:20Z: /workspace/venv/bin/python gates/gate_G4b.py
RC[09_G4b] rc=0 2026-09-05T03:26:23Z
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=111 PHI=0 FSEED=42 OUT_TAG=F1_pinned_log /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=F2_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=F3_pinned_log_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=F2_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=F3_pinned_log_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev_alt) 2026-09-05T03:26:23Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=111 PHI=0 FSEED=42 OUT_TAG=F1_pinned_prod /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev_alt) 2026-09-05T03:26:50Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=F2_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev_alt) 2026-09-05T03:26:50Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=F3_pinned_prod_s42 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev_alt) 2026-09-05T03:27:01Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero W3FIX=0.21,0,0.79 OUT_TAG=F2_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
CMD[10_G5_arms] (cwd=/workspace/review_scratch/jpline_rebuild/dev_alt) 2026-09-05T03:27:01Z: env LOOK=900 WRULE=msharpe CAL=log SLOW_NPY=/workspace/review_scratch/jpline_rebuild/data/slow_pred_pinned_on_hist.npy LEGS=101 PHI=0.45 FSEED=2027 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=F3_pinned_prod_s2027 /workspace/venv/bin/python ../w10_universe_recheck.py
G5_ARMS_DONE 2026-09-05T03:27:39Z
CMD[11_judge] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:27:40Z: /workspace/venv/bin/python gates/judge_rebuild.py
RC[11_judge] rc=0 2026-09-05T03:27:44Z
CMD[11_judge] (cwd=/workspace/review_scratch/jpline_rebuild) 2026-09-05T03:27:44Z: sha256sum results/judge_rebuild.json results/REPORT_tables.md
RC[11_judge] rc=0 2026-09-05T03:27:44Z
```

## Appendix B — pod-side chain log (logs/chain.log)

```
CHAIN_START 2026-09-05T01:13:02Z pid 65205
START 01_download 2026-09-05T01:13:02Z
MANUAL_SWITCH 2026-09-05T02:01:57Z paced->fast (user ruling 2026-09-05 解除限速); killed 65205 65214 65217; relaunch run_chain.sh
CHAIN_START 2026-09-05T02:02:01Z pid 69041
START 01_download 2026-09-05T02:02:01Z
CHAIN_START 2026-09-05T02:12:55Z pid 69952
START 01_download 2026-09-05T02:12:55Z
MANUAL_SWITCH_2 2026-09-05T02:21:25Z paced->fast again (user ruling 2026-09-05 解除限速, STATE §4); killed 69952 69963 69968; relaunch run_chain.sh; DO NOT REVERT
CHAIN_START 2026-09-05T02:21:29Z pid 71684
START 01_download 2026-09-05T02:21:29Z
END 01_download rc=0 2026-09-05T02:42:09Z
START 01b_manifest 2026-09-05T02:42:09Z
END 01b_manifest rc=0 2026-09-05T02:43:04Z
START 02_cache 2026-09-05T02:43:04Z
END 02_cache rc=3 2026-09-05T02:46:04Z
CHAIN_HALT at 02_cache
CHAIN_START 2026-09-05T02:47:36Z pid 74501
skip 01_download (done)
skip 01b_manifest (done)
START 02_cache 2026-09-05T02:47:36Z
END 02_cache rc=0 2026-09-05T02:50:58Z
START 03_panel 2026-09-05T02:50:58Z
END 03_panel rc=0 2026-09-05T02:57:12Z
START 03g_G1 2026-09-05T02:57:12Z
END 03g_G1 rc=0 2026-09-05T02:59:34Z
START 04_fea 2026-09-05T02:59:34Z
END 04_fea rc=3 2026-09-05T03:03:10Z
CHAIN_HALT at 04_fea
CHAIN_START 2026-09-05T03:09:31Z pid 76009
skip 01_download (done)
skip 01b_manifest (done)
skip 02_cache (done)
skip 03_panel (done)
skip 03g_G1 (done)
START 04_fea 2026-09-05T03:09:31Z
END 04_fea rc=0 2026-09-05T03:13:31Z
START 05_king 2026-09-05T03:13:31Z
END 05_king rc=0 2026-09-05T03:14:40Z
START 05g_G4a 2026-09-05T03:14:40Z
END 05g_G4a rc=0 2026-09-05T03:15:40Z
START 06_stop_arms 2026-09-05T03:15:40Z
END 06_stop_arms rc=0 2026-09-05T03:16:18Z
START 06g_G2a 2026-09-05T03:16:18Z
END 06g_G2a rc=0 2026-09-05T03:18:04Z
START 07_targets 2026-09-05T03:18:04Z
END 07_targets rc=0 2026-09-05T03:19:22Z
START 07g_G3 2026-09-05T03:19:22Z
END 07g_G3 rc=0 2026-09-05T03:21:25Z
START 08_setup_dev 2026-09-05T03:21:25Z
END 08_setup_dev rc=0 2026-09-05T03:22:52Z
START 08_arms_g2 2026-09-05T03:22:52Z
END 08_arms_g2 rc=0 2026-09-05T03:23:19Z
START 08g_G2bc 2026-09-05T03:23:19Z
END 08g_G2bc rc=0 2026-09-05T03:23:20Z
START 09_G4b 2026-09-05T03:23:20Z
END 09_G4b rc=0 2026-09-05T03:26:23Z
START 10_G5_arms 2026-09-05T03:26:23Z
END 10_G5_arms rc=0 2026-09-05T03:27:40Z
START 11_judge 2026-09-05T03:27:40Z
END 11_judge rc=0 2026-09-05T03:27:44Z
CHAIN_DONE 2026-09-05T03:27:44Z
```
