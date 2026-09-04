# Carry composition: why the live combo book paid +1.21 bps/anchor per gross more funding than the replay's "live-form" book (28 anchors, 2026-08-26 04Z → 08-30 20Z)

> **创建:** 2026-09-05 | **Session:** b9646a9e (teammate carry_composition; read-only on ~/wide_shadow, ~/dl_quant_live, pod /workspace/{data,port_w10,shadow_bundle_v3}) | **状态:** 完成, 供 REVIEW_caliber_final §7 #25 / §9 G1 收口 | **作废条件:** target_live/target_combo/weights 文件或 pod probe_artifacts 被重写 ⇒ 复跑; 若执行器 per_name_stop 审计(notify_audit.jsonl)在 08-21→09-02 出现 ONGUSDT 事件 ⇒ §4.4 止损归因重估
> Units everywhere: bps per anchor per unit gross, device caliber `smr` (demean the non-zero set, rescale to the original gross), sign + = book pays. Rates = pod panel `f_fund_now × 4/f_fund_iv` (bitwise equal to the producer ledger, gap_1). Labels: VERIFIED = printed by a script quoted in §7; INFERRED = arithmetic on verified numbers or a bound; UNRESOLVED = not established here.

## 0. Bottom line (plain language)

1. **The +1.21 gap reproduces exactly** (+1.212 ± 0.167 se, n = 28, gap_1 definition; +1.207 ± 0.165 demeaned-vs-demeaned). VERIFIED.
2. **It is a form mismatch inside the window, not a structural excess of the deployed form.** The replay arm `pod_live_w3fix_callog_s42` carries two things the live book did **not** have on 08-26 → 08-30:
   - **FTRIM** (zero z for shorts with rn8 ≤ −10 bp/8h): replay had it; the live combo got it on **09-02 12Z** (first `ftrim` record in `target_combo`). A fresh replay of the same arm with `FTRIM=off` (V1) pays **+0.734 ± 0.061** more at the 28 anchors. VERIFIED.
   - **The replay's in-book stop layer** (`d30_n2_c42`) had **stopped ONGUSDT on 08-21 04Z** (7-day cooldown to ≈ 08-28), while the live *executed* book held the ONG short throughout (executor position readback −0.007 → −0.0096 of realized gross; the executor's own per-name stop clause, enabled, never triggered on ONG: 0 of its 40 audited events 08-20 → 09-04; the separate `~/wide_shadow/stop_overlay.py` is a zero-intervention logger whose FIRE on 08-26 20Z changed nothing). ONG's funding ran −40 to −797 bps/4h. Replay no-stop vs stop at the 28 anchors: **+0.444 ± 0.159**. VERIFIED. Excluding ONG alone, live − V1 falls from +0.473 ± 0.150 to **+0.076 ± 0.035**. VERIFIED.
   - Replay with **neither** FTRIM nor stop (V1, arm S0) pays **2.200** vs live **2.228**: the live pre-FTRIM book paid exactly what the replay predicts for that form. VERIFIED.
3. **Universe is the only structural residual and it points the other way for the replay**: restricting the replay book to the frozen 450 names raises its carry (+0.190 ± 0.020 on V1, +0.134 ± 0.015 on the deployed arm): the 829/400 replay holds 14.3 % of gross in ≈ 79 names outside the 450 and its eligible set is 360 vs the live's 280 (only 281 of the 450 pass the 2.5e5 liquidity gate; producer's own gate equals the meta's, Spearman 1.0000), so the live cap is 2.5/280 = 0.0090 vs 2.5/360 = 0.0070. On the same names, ex-ONG, the live pays **−0.094 ± 0.027 less** than the no-FTRIM replay. VERIFIED.
4. **Not drivers** (each measured): net exposure/demeaning +0.005; member set +0.011; king-form → combo −0.014; fund EMA input (producer ledger EMA vs panel `f_fund_ema_v1`: Spearman 1.0000, max |diff| 4.6e-4); fund rank base 829 vs M1 vs 400 (≤ 0.10 on single-anchor targets, LP share moves ≤ 0.02); seats (0.01–0.05); F10 model (live kc chain 2.203 vs fc chain 2.159). VERIFIED.
5. **Historical persistence**: FTRIM's carry saving in the replay is 0.23/0.21/0.12/0.61/1.22 per gross in 2022/23/24/25/26 (0.42 bps/NAV 2024→26) and it nets **+0.043/NAV** (0.414 → 0.457); the stop layer saves 0.03/0.17/0.19 (2024/25/26). The live post-FTRIM level (09-03 12Z → 09-04 16Z ≈ 0.9–1.4 per gross) sits inside the deployed form's 2026 p10–p90 (0.52–1.90). The live pre-FTRIM 2.23 sits at the **median** of the no-FTRIM form's 2026 distribution (p50 2.20). VERIFIED.
6. **Bound asked for (INFERRED, not applicable to the deployed form)**: scaling the deployed arm's carry by the measured ratio 2.18 would give 2024→26 net_ex −0.26 (CAL=log) / +0.76 (CAL=simple); by year −1.04/−0.52/+1.30. The meaningful counterfactual "run the 08-26 live target-book form (no FTRIM, no in-book stop) over history" is the replay's own V1-S0 arm: **+0.375/NAV 2024→26 (Sharpe 0.76)** vs deployed +0.457 (1.02). **The +0.457 headline is not flipped by this gap.**

## 1. Inputs and alignment (VERIFIED)

| Item | Source | Fact |
|---|---|---|
| Overlap anchors | replay `d30_n2_c42_rec` ts ∩ panel ∩ `state/target_live/*.json` | 28: 08-26 04Z → 08-30 20Z, 08-29 20Z missing (no live anchor). Sub-periods: 22 clean combo anchors (04Z 08-26 → 16Z 08-29), 1 king-form anchor (08-30 00Z, `producer=shadow_loop_v3`, combo did not run), 5 fc-reset anchors (08-30 04Z–20Z, `fc_state_source=warmstart`, fc gross 0.17 → 0.40) |
| Live book at those anchors | `target_live/{N}.json` = `combo_raw = 0.55·sm_kc + 0.45·sm_fc` (combo_stage.py L351, not demeaned); `target_combo/{N}.json` = `exec_reshape(combo_raw)` | asserted: `target_live == 0.55·state_H_kc + 0.45·state_H_fc` (max 1e-7), `target_combo == dm(target_live)` (1e-6), `target_live_king == weights/{N}.npz` (1e-6) |
| Live form at those anchors | `shadow_loop_v3.py.pre_m1_20260904_backup` L441; `shadow_log.jsonl` signal rows; `target_combo` | pre-M1 (fund rank inside the 400 members; `base_n` first appears 09-04 04Z), king booster `29ffaf58` (v3 `8d79186b` from 09-01 08Z), **no FTRIM** (`ftrim` record first at 09-02 12Z), seats w3m king 0.21–0.24 |
| Replay arm | `probe_artifacts/w10_ablation_series_pod_live_w3fix_callog_s42.npz` config_json | W3FIX 0.21/0/0.79, MEMBERS_TOPN 829, TRADE_TOPN 400, **FTRIM zero**, CAL log, LEGS 101, PHI 0.45, king = `shadow_bundle_v3/slow_pred_pinned.npy` (v3), stop arm d30_n2_c42 |
| Replay F10 leg in the window | `replay_inputs_overlap.json` | `f10_V2MAIN_s42` OOS preds are **NaN at all 28 anchors** (finite = 0) ⇒ replay fc chain = 0.79·xz(fund) there (kc and fc FTRIM sets identical). Caveat, not a carry driver |
| Rates | `panel_fund_tail.npz` (v2ext) vs `pod_backup/wide_panel_4h_hist_v2.npz` (replay input) | `f_fund_now`, `f_fund_ema_v1` max diff 0.00e+00 on the 28 anchors; mask mismatches 0 |
| Fund EMA input | producer ledger_tail re-integrated (rn = rate·8/iv, HL 3 d) vs panel `f_fund_ema_v1` | 08-26 04Z: 522 names, Spearman 1.0000, members 400 Spearman 1.0000, max |diff| 4.56e-4; 08-31 00Z: 1.49e-4 |

## 2. Step 1 — reproduce the gap (VERIFIED, `decompose_mac.out`)

| Comparison (live − replay, per gross) | mean | sd | se | n |
|---|---|---|---|---|
| gap_1 definition: live `target_live` raw − replay W3FIX demeaned | **+1.212** | 0.884 | 0.167 | 28 |
| demeaned − demeaned | +1.207 | 0.874 | 0.165 | 28 |
| raw − raw | +1.198 | 0.848 | 0.160 | 28 |
| live dm − replay dynamic-seat dm (`pod_live_callog_s42`) | +1.193 | 0.853 | 0.161 | 28 |
| live dm − replay canon W3FIX dm (`pod_canon_w3fix_callog_s42`, no FTRIM, meta members) | +0.674 | 0.831 | 0.157 | 28 |

Sub-periods (live dm / replay dm / gap): clean 22 anchors 2.092 / 0.991 / **+1.101**; king-form anchor 3.458 / 1.391 / +2.067; fc-reset 5 anchors 2.580 / 1.081 / +1.499. The gap is not an artefact of the odd anchors.

## 3. Step 2 — additive decomposition (VERIFIED, `decompose_mac.out`, `structural_tests.out`)

Composition columns: LP = gross share long & rate > 0, SN = short & rate < 0 (both pay), LN / SP receive; pay_* = bps paid by that quadrant per gross; recv = received by LN + SP.

| Book (28 anchors) | carry | se | net | LP | SN | pay_LP | pay_SN | recv | gross | names |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) replay W3FIX raw | +1.036 | 0.060 | −0.084 | 0.433 | 0.142 | +0.558 | +0.648 | −0.170 | 0.761 | 335 |
| (a) replay W3FIX dm (= device `carry_ex`) | **+1.021** | 0.054 | 0 | 0.472 | 0.134 | +0.595 | +0.585 | −0.158 | 0.761 | 335 |
| (a′) replay dynamic seats dm | +1.035 | 0.058 | 0 | 0.471 | 0.135 | +0.583 | +0.611 | | 0.747 | 341 |
| (a″) replay canon W3FIX dm (no FTRIM, meta members, no T400) | +1.554 | 0.095 | 0 | 0.419 | 0.146 | +0.534 | +1.171 | | 0.917 | 368 |
| (b) replay W3FIX restricted to live 450, dm | +1.156 | 0.066 | 0 | 0.494 | 0.147 | +0.623 | +0.694 | | 0.652 | 262 |
| (c) replay W3FIX restricted to live members (400), dm | +1.166 | 0.067 | 0 | 0.494 | 0.146 | +0.625 | +0.705 | | 0.648 | 261 |
| (d) live `target_live_king` (king form, producer) dm | +2.197 | 0.218 | 0 | 0.494 | 0.177 | +0.571 | +1.778 | | 0.843 | 279 |
| (d1) live kc chain alone (`state_H_kc`) dm | +2.203 | 0.220 | 0 | 0.494 | 0.175 | +0.582 | +1.774 | | 0.833 | 279 |
| (d2) live fc chain alone (`state_H_fc`) dm | +2.159 | 0.217 | 0 | 0.494 | 0.174 | +0.598 | +1.714 | | 0.757 | 271 |
| (e) live `target_live` raw (what the executor reads) | +2.233 | 0.217 | −0.038 | 0.476 | 0.179 | +0.575 | +1.817 | −0.159 | 0.797 | 279 |
| (e) live `target_combo` = dm(target_live) | **+2.228** | 0.216 | 0 | 0.494 | 0.174 | +0.594 | +1.788 | −0.153 | 0.797 | 279 |

Increments (dm caliber): (a)→(b) restrict to 450 **+0.134 ± 0.015**; (b)→(c) restrict to members +0.011 ± 0.001; (c)→(d) replay-on-live-names → producer king-form book **+1.048 ± 0.154** (n 27); (d)→(e) king-form → combo −0.014 ± 0.008; dm → raw +0.005 ± 0.003. The whole gap sits in **pay_SN** (short positions in negative-funding names): 1.788 vs 0.585, while pay_LP is identical (0.594 vs 0.595) and the LP share is identical (0.494 vs 0.494 after restriction).

Other facts: replay gross outside the 450: mean 0.143 (max 0.178); live gross outside its members 0.000; names in both books 261 (replay 335, live 279), sign agreement 0.944, correlation of dm weights 0.873; members' mean 4h rate −0.131 bps with 89.9 % of names positive.

Top-20 |w × rate| contributors, live dm (bps/anchor per gross; replay value in brackets; all 20 present in both books): ONG 0.604 [0.109], COTI 0.144 [0.040], TUT 0.140 [0.037], BICO 0.124 [0.047], HOME 0.115 [0.033], ONT 0.111 [0.037], ACE 0.108 [0.018], SKR 0.066 [0.019], SAND 0.045 [0.018], ESPORTS 0.042 [0.050], BTR 0.038 [0.030], EDEN 0.036 [0.019], SIREN 0.035 [0.039], STORJ 0.034 [0.012], BMT 0.031 [0.013], MOVE 0.027 [0.017], 4 0.027 [0.028], CLO 0.024 [0.007], STAR 0.022 [0.025], GAS 0.022 [0.013]. The live top-20 is 70.8 % of its |w·r| (45.7 % of the replay's). The first eight are all shorts in names with rn8 ≤ −10 bp/8h, i.e. FTRIM's targets; the replay's top-20 contains one name outside the 450 (BTWUSDT, long, +2.9 bps/4h).

## 4. Step 3 — structural tests

### 4.1 Test (i): fund rank base (VERIFIED, `structural_tests.out` §B)

Single-anchor targets (device chain lines 185–209 without EMA), z = 0.21·xz(pinned king) + 0.79·xz(fund | base), per gross:

| Fund rank base | FTRIM | sel | carry | pay_SN | LP | SN | band-short gross | band pay |
|---|---|---|---|---|---|---|---|---|
| 829 panel (replay) | off | replay (360) | +2.097 | +1.675 | 0.475 | 0.170 | 0.060 | +1.526 |
| M1 `base_syms` (aux, 528 today) | off | replay | +2.141 | +1.749 | 0.456 | 0.185 | 0.062 | +1.593 |
| 400 live members (producer at these anchors) | off | replay | +2.198 | +1.815 | 0.464 | 0.188 | 0.066 | +1.664 |
| 829 / M1 / 400 | off | live members (280) | +2.683 / +2.371 / +2.415 | | 0.497 | 0.213 / 0.190 / 0.195 | 0.081 / 0.069 / 0.071 | |
| 829 / M1 / 400 | zero | replay | +0.455 / +0.380 / +0.428 | +0.164 / +0.171 / +0.161 | 0.470 / 0.456 / 0.468 | | 0.000 | 0.000 |

Reading: the rank base moves the target's carry by ≤ 0.10 and the long-positive share by ≤ 0.02; FTRIM moves it by −1.6 to −1.8 on the target (−0.73 on the EMA'd book, see 4.3); the **eligible-set size** (280 vs 360, i.e. the frozen 450 vs top-400-of-829) moves it by +0.2 to +0.6 through the cap 2.5/n_sel. In the replay family (dynamic seats) the M1 base effect on the EMA'd book is +0.22 (`pod_t400` 1.644 → `pod_m1t400` 1.862) and T400 +0.04 — i.e. the M1 base (live since 09-04) makes the book pay slightly **more**, not less.

### 4.2 Test (ii): FTRIM name sets (VERIFIED, `structural_tests.out` §C, `ftrim_live_cf.out`)

- At the 28 anchors: panel band names (rn8 ≤ −10 bp/8h) 11.3/anchor; replay trimmed (kc) 11.1 (fc identical because F10 is NaN); live shorts in band ("would have been trimmed") 9.6; intersection 9.6; live-only 0.0; replay-only 1.4 (names outside the live members/sel). Jaccard 0.885. Same rule, same rates, same names — the only difference is that the live did not apply it yet.
- Post-09-02 (14 anchors with a `ftrim` record): combo trims 11.3 kc / 11.3 fc per anchor; the live target still holds 8.1 shorts in band names per anchor, **all** inside the combo's trimmed set (no live-only names) — these are EMA residuals frozen by the 2.5e-4 band, exactly as in the replay (deployed arm: band shorts 2.2 % of gross paying +0.460 of its +1.021, i.e. 45 % of the deployed form's carry in this window comes from band-frozen FTRIM residuals). All combo-trimmed names satisfy rn8 ≤ −10 bp under the ledger (0 WARN).
- Live-side counterfactual (zero the live book's band shorts, renormalise): 2.228 → **0.580** (removes +1.648 ± 0.215; upper bound since it zeroes positions, not targets); band shorts in live: 9.6 names, 6.3 % of gross, paying +1.651 vs replay 9.5 names, 2.2 %, +0.460.
- Live trajectory (ledger rates): pre-FTRIM 42 anchors 08-26 00Z → 09-02 00Z carry 2.563, pay_SN 2.132, band gross 0.068; post-FTRIM 16 anchors 09-02 04Z → 09-04 16Z carry 1.530, pay_SN 1.087, band gross 0.035, decaying (ONG weight −0.0061 → −0.0006; 09-03 12Z → 09-04 16Z carry 0.97/0.94/0.92/1.35/0.99/0.91/1.17/1.15).

### 4.3 Replay-side confirmation: same arm with FTRIM off (V1) (VERIFIED, `replay_family_V1.out`, `structural_tests.out` §A)

Fresh run in pod scratch, byte-identical device (`sha256 64c70a44…` = `/workspace/port_w10/w10_universe.py`), `OUT_TAG=cc_live_w3fix_noftrim_callog_s42`, command in §7.

| Book (28 anchors, dm) | carry | pay_SN | band-short gross | band pay | names |
|---|---|---|---|---|---|
| canon W3FIX, no FTRIM (`pod_canon_w3fix`) | +1.554 | +1.171 | 0.048 | +1.052 | 368 |
| M1+T400 dynamic, no FTRIM (`pod_m1t400`) | +1.862 | +1.434 | 0.061 | +1.282 | 330 |
| **V1** = W3FIX 829/400 no FTRIM, stop arm | **+1.755** | +1.318 | 0.055 | +1.169 | 326 |
| V1 restricted to live 450 | +1.946 | +1.485 | 0.062 | +1.331 | 260 |
| V1 restricted to live members | +1.958 | +1.498 | 0.063 | +1.343 | 259 |
| **live** `target_live` dm | **+2.228** | +1.788 | 0.063 | +1.651 | 279 |
| deployed arm (FTRIM zero, stop) | +1.021 | +0.585 | 0.022 | +0.460 | 335 |

Ladder: V1 → V1|450 **+0.190 ± 0.020**; → |members +0.013 ± 0.001; → live **+0.270 ± 0.144**; live − V1 total +0.473 ± 0.150; **V1 − deployed (FTRIM effect in the replay) +0.734 ± 0.061**; live − deployed +1.207 ± 0.165.

Per-name mean weight per gross (dm) of the deep-negative names, live / V1 / m1t400 / canon / deployed: ONG (−84 bps/4h mean) −0.0074 / −0.0032 / −0.0035 / −0.0032 / −0.0012; COTI −0.0082 / −0.0085 / −0.0091 / −0.0071 / −0.0024; TUT −0.0028 / −0.0012 / −0.0014 / −0.0026 / −0.0005; BICO −0.0069 / −0.0079 / −0.0081 / −0.0064 / −0.0028; HOME −0.0074 / −0.0090 / −0.0093 / −0.0072 / −0.0022; ONT −0.0073 / −0.0032 / −0.0034 / −0.0024 / −0.0024; ACE −0.0070 / −0.0044 / −0.0078 / −0.0053 / −0.0012; SKR −0.0020 / −0.0016 / −0.0017 / −0.0015 / −0.0006. Without FTRIM the replay shorts COTI/BICO/HOME **harder** than the live; the live's excess is ONG (and ONT/ACE).

### 4.4 The residual is one name and the replay's stop layer (VERIFIED, `residual_checks.out`, `stop_arm.out`, pod ONG check, executor stop audit)

- live − V1: **+0.473 ± 0.150 with ONG, +0.076 ± 0.035 without**; live − V1|members: +0.270 ± 0.144 with, **−0.094 ± 0.027 without**; live − deployed ex-ONG +0.725 ± 0.066.
- ONG facts: fund rank z −0.497/−0.499 (bottom of both bases), pinned king z −0.47 (also short), qvk rank 22–44, passes the replay sel at every anchor; rate4h +0.1 (08-26 04Z) → −150 (16Z) → −200 → **−797 (08-27 00Z)** → −131 → −45 … −72 (08-30 00Z) → −33. Live target weight per gross −0.0069 → −0.0094 (history: −0.0044 on 08-22, −0.0060 on 08-25). Replay stop arm: −0.0016 flat to 08-27 20Z, then rebuilding to −0.0061 by 08-30 20Z; replay **no-stop arm S0: −0.0072 throughout** (= live). S0 ≠ d30 for ONG from **08-21 04Z** (S0 −0.00605 vs d30 −0.0032) for 59 consecutive anchors: the d30_n2_c42 layer stopped ONG on 08-21 04Z (book-path cost-average depth −0.30 × 2 anchors, cooldown 42 anchors = 7 days).
- Stop effect on carry (d30 − S0): V1 at the 28 anchors **−0.444 ± 0.159**; deployed arm −0.116 ± 0.043. **V1-S0 (no FTRIM, no stop) = 2.200 vs live 2.228.**
- Live stop status in the window (read after the lead's query; all VERIFIED from the named files):
  - The executor's per-name stop clause is **enabled**: `~/dl_quant_live/config/book.json` `per_name_stop` = {enabled true, depth_pct −0.25, consecutive_anchors 2, cooloff_days 7, min_notional_usdt 20, active_profile "wide"}; `live/per_name_stop.py` (docstring + L77–142): profile wide = d30_n2_c42 (depth −0.30 × 2 consecutive end-of-anchor readbacks × 7-day cooldown), **depth = venue `unrealizedProfit / |notional|` of the current position** from `broker.account_snapshot`; action = name goes untradable, target 0, flatten_only (maker exit); applied in `scheduler/anchor_loop.py` L2100–2116 under `LIVE_MODE=LIVE`, per-anchor result logged to `state/anchor_runs.log` phase_C (157 lines) and every trigger/exit/cooldown event to `state/notify_audit.jsonl`.
  - `state/notify_audit.jsonl` holds **40 per_name_stop events 08-20 12:16Z → 09-04 16:44Z** (BOME, ENA, TAC, MAGMA ×2, VELVET, US, SKYAI, PROM, SKR, ZORA, BTR, CYS, TRIA, RIVER, EGLD, ARB, USELESS); **none names ONGUSDT**. `state/live/per_name_stop.json` (09-05 00:44Z): stopped {CYS, MAGMA, RIVER, TRIA}, cooldown {ARB, BTR, EGLD, SKR, USELESS, ZORA}, counters {FLOCK 1}; no ONG. `anchor_runs.log` phase_C per_name_stop dicts: no ONG in stopped/counters. ⇒ the executor's stop never acted on ONG.
  - The separate `~/wide_shadow/stop_overlay.py` (docstring: "零干预证据采集器 … 换装日这层可直接升格为真止损") FIREd counterfactually on ONG at 08-26 20Z with depth −46 % on its own book-path cost-average accounting (`stop_overlay.log`: `FIRE 1787774400 [('ONGUSDT', -0.461, 0.0)]`); it never touches the book. The executor's clause measures depth on the venue's unrealized PnL of the current position, which is a different quantity (INFERRED reason for the non-trigger; the venue depth series for ONG was not recomputed — `position_readback.jsonl` rows carry no unrealized field).
  - Executor readback (`~/dl_quant_live/state/live/pilot_log/2026MMDD/position_readback.jsonl`, symbol ONGUSDT, fields `venue_position_qty` / `venue_position_notional` USD): 08-26 00Z −1,680 / −164; 04Z −1,581 / −161; 08Z −1,499 / −155; 12Z −2,332 / −222 (a second 12Z row and the 16Z, 20Z rows read 0 — the 08-26 leverage-change rebuild window); 08-27 00Z −851 / −154; 04Z −1,651 / −190; 08Z −1,840 / −220; 12Z–20Z −2,494 → −2,324 / −293 → −291; 08-28 00Z–20Z −2,420 → −2,692 / −292 → −299; 08-29 00Z–20Z −2,528 → −2,729 / −303 → −332; 08-30 00Z–20Z −3,297 → −3,441 / −404 → −376; 08-31 00Z–20Z −3,647 → −4,032 / −378 → −365; 09-01 00Z–20Z −4,248 → −2,997 / −380 → −342; 09-02 04Z/08Z −3,427 / −346, −3,551 / −357; then the FTRIM decay 09-02 12Z −3,122 / −311, 16Z −2,719 / −269, 20Z −2,360 / −233. Share of realized gross: −0.0065 (08-25 00Z) → −0.0073 (08-26 04Z) → −0.0071 (08-28) → −0.0096 (08-30 00Z) → −0.0093 (09-01 00Z) → −0.0077 (09-02 12Z) → −0.0008 (09-04 12Z). So the executed book held the full ONG short at target size through the −797 bps/4h print.

### 4.5 Universe / eligible-set mechanism (VERIFIED, `residual_checks.out` §2)

From meta `qvk` at the 28 anchors: names of the frozen 450 passing qv4h ≥ 2.5e5: 281.2 (= live sel 280.2, `signal` rows); top-400-of-829 passing (= replay nsel): 360.1, of which 318.5 are in the 450 and **78.9 are outside the 450** (young listings); producer's own cache `qvm` vs meta `qvk`: Spearman 1.0000, median difference 0.000, gate counts identical (280.2 / 280.2). Consequence: live cap 2.5/280 = 0.00899 vs replay 2.5/360 = 0.00698 (+29 %), and the replay holds 14 % of gross in names the live cannot trade. This is the "frozen universe aging" of `docs/RESULT_universe_dyn_2026-09-04.md`, seen from the carry side; it persists until the universe is refreshed (Phase B).

## 5. Step 4 — historical persistence (VERIFIED, `replay_family_existing.out`, `replay_family_V1.out`, `stop_arm.out`)

Per-gross carry (dm) by year, replay live-form arms (W3FIX 0.21/0/0.79, 829/400, CAL=log, s42):

| Year | n | deployed (FTRIM zero, stop) | p10 / p50 / p90 | roll-28 max | V1 (FTRIM off, stop) | V1 p10 / p50 / p90 | V1-S0 (FTRIM off, no stop) | FTRIM effect | stop effect (V1) |
|---|---|---|---|---|---|---|---|---|---|
| 2022 | 2010 | 0.509 | 0.17 / 0.45 / 0.82 | 2.35 | 0.741 | 0.24 / 0.56 / 1.19 | 0.748 | −0.23 | −0.007 |
| 2023 | 2190 | 0.327 | 0.09 / 0.29 / 0.63 | 0.87 | 0.532 | 0.15 / 0.40 / 1.10 | 0.644 | −0.21 | −0.112 |
| 2024 | 2196 | 0.407 | 0.14 / 0.32 / 0.83 | 1.35 | 0.527 | 0.19 / 0.43 / 1.00 | 0.553 | −0.12 | −0.026 |
| 2025 | 2190 | 0.911 | 0.33 / 0.83 / 1.63 | 2.16 | 1.525 | 0.55 / 1.32 / 2.76 | 1.693 | −0.61 | −0.168 |
| 2026 | 1452 | 1.191 | 0.52 / 1.17 / 1.90 | 2.08 | 2.407 | 1.20 / 2.20 / 3.78 | 2.598 | −1.22 | −0.192 |
| 28-anchor window | 28 | 1.021 | | | 1.755 | | 2.200 | −0.734 | −0.444 |
| live window | 28 | **2.228** | | | | | | | |

Placement: the live 2.228 is above the deployed form's 2026 p90 (1.90) and above its largest rolling-28 mean of 2026 (2.08) — **outside** the deployed form's own range — but at the **median** of the no-FTRIM form (2.20) and below the median of the no-FTRIM/no-stop form (2026 mean 2.60). The live post-FTRIM readings (0.9–1.4 from 09-03 12Z) are inside the deployed form's 2026 p10–p90. Band-short gross in the deployed form: 0.7 % / 2.8 % / 2.9 % of gross in 2024/25/26 paying 0.11 / 0.53 / 0.62 — FTRIM's frozen residuals are a persistent ≈ 45–50 % of its remaining carry in 2025–26.

Per-NAV headline arithmetic (replay `net_ex`, CAL=log):

| Arm (2024 → 26) | net_ex/NAV | Sharpe_ex | carry_ex/NAV | 2024 / 2025 / 2026 net_ex |
|---|---|---|---|---|
| deployed (FTRIM zero, stop d30) | **+0.4566** | 1.02 | +0.6101 | −0.642 / +0.284 / +2.378 |
| deployed, no stop (S0) | +0.4114 | 0.83 | +0.6859 | −0.674 / +0.154 / +2.441 |
| V1 (FTRIM off, stop d30) | +0.4139 | 0.95 | +1.0304 | −0.669 / +0.223 / +2.340 |
| **V1-S0 (FTRIM off, no in-book stop) ≈ the target-book form live 08-26 → 09-02** (the executor's separate stop clause acted on other names in the window, never on ONG) | **+0.3751** | 0.76 | +1.1929 | −0.681 / +0.079 / +2.419 |
| INFERRED bound: deployed with carry × 2.18 (live/replay ratio) | −0.264 | | | −1.044 / −0.517 / +1.296 |
| INFERRED bound: deployed with carry × 1.72 (V1/deployed ratio) | +0.018 | | | −0.887 / −0.203 / +1.720 |
| same two bounds on `pod_live_w3fix_calsimple_s42` (+1.4731 headline) | +0.755 / +1.036 | | | |

The scaled bounds assume the live book pays 2.18× the deployed form's carry at every anchor of history; §4 shows the ratio is FTRIM (absent in live until 09-02) + the stop-layer treatment of one name + universe, so the bound describes a book that no longer exists. FTRIM's net effect in this arm is +0.043/NAV (0.414 → 0.457), consistent in sign with the 09-02 deployment receipt (whose Δ +0.21–0.23 was measured under a different caliber/seat set-up; not re-adjudicated here).

## 6. Statement of cause, and what remains open

**Likely causes (in order of size at the 28 anchors, all VERIFIED):**
1. FTRIM present in the replay, absent in the live combo until 09-02 12Z: +0.73 (replay-internal) to +1.65 (live-side upper bound) — the whole of pay_SN's excess in names with rn8 ≤ −10 bp/8h (ONG, COTI, TUT, BICO, HOME, ONT, ACE, SKR).
2. The replay's in-book stop layer had ONGUSDT stopped from 08-21 04Z; the executed live book held it through the −797 bps/4h funding print (the executor's own stop clause never triggered on ONG): +0.44 on the no-FTRIM replay, and the entire residual after FTRIM (ex-ONG residual +0.08 ± 0.04, on same names −0.09 ± 0.03).
3. Frozen 450 universe: eligible set 280 vs 360, cap +29 %, 14 % of replay gross untradeable for live: +0.13 to +0.19 per gross, structural until the universe is refreshed; historically the only part of the gap that persists, and it is offset on the same names.

**Structural vs specific:** the +1.21 is specific to the window's form mismatch. The deployed form (with FTRIM) has never paid 2.2 per gross for 28 anchors in the replay's history (2026 rolling-28 max 2.08); the target-book form that was live (no FTRIM, no in-book stop) pays 2.6 per gross in 2026 on average, so the live book's 2.23 was normal for what it was. The fixed-seat headline +0.457 stands on this axis; the honest counterfactual for a book without FTRIM is +0.375.

**UNRESOLVED / caveats:**
- U1. Executor side closed: the executor's per-name stop (enabled, wide profile) never triggered on ONGUSDT (`notify_audit.jsonl` 40 events, none ONG; `per_name_stop.json` and `anchor_runs.log` phase_C: no ONG). Still open is *why* its venue-unrealized depth on the current position stayed above −30 % for two consecutive readbacks while the overlay's and the replay's book-path cost-average depth crossed −46 % / −30 %: the two accountings differ by construction (current-position venue PnL vs path cost average; ONG's qty grew as its price fell, so the venue position was largely in profit), and the venue depth series for ONG was not recomputed here (readback rows carry no unrealized field). ONG was held at target size, so it does not explain §7 #26 (realized −0.31 vs target).
- U2. Replay F10 preds are NaN at all 28 anchors (and the `f10_V2MAIN_s42` file is 28 % finite overall), so any replay-vs-live comparison in this window compares a fund-only fc chain with the live F10 chain; carry-neutral here (kc 2.203 vs fc 2.159 in live) but relevant for pnl comparisons on the same window.
- U3. Device caveat: for MEMBERS_TOPN=0 arms the stored `carry_ex`/`pnl_ex` count only current members while `W` keeps stale positions outside the member set (max |carry_ex − dm·gross| 0.4–0.7 vs 1e-7 for 829 arms); the canon-arm numbers in §3/§5 use my all-names recomputation.
- U4. FTRIM leaves band-frozen residual shorts (≤ 2.5e-3 per name) that pay ≈ 45 % of the deployed form's remaining carry in this window and 2.8–2.9 % of gross in 2025–26; a force-exit of band names would be a book-behaviour change (pre-registration + user ruling), not proposed here.
- U5. Post-FTRIM live convergence is 16 anchors only (09-02 04Z → 09-04 16Z); the level comparison with the replay's 2026 distribution is by placement, not by same-anchor pairing (replay ends 08-30 20Z).
- U6. The M1 base went live 09-04; the replay says it raises carry by ≈ +0.22 per gross at these anchors (dynamic-seat family). Not yet visible in live data (3 anchors).
- U7. The executor's stop clause acted on other names during the window (SKR 08-30 16Z, MAGMA 08-31 04Z, ZORA 08-31 08Z, BTR 08-31 12Z, CYS 09-01 08Z, TRIA 09-01 12Z, RIVER 09-02 08Z; `notify_audit.jsonl`), so the *executed* live book differs from `target_live` on those names; their carry contribution was not isolated here (they are not among the top-20 |w·r| names except SKR, 0.066).

## 7. Commands and receipts (all read-only on production paths; outputs in `<SCRATCH>/review_caliber/carry_composition/` and pod `/workspace/review_scratch/carry_composition/`)

`SCRATCH = /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad`

```
# Mac — step 1 + 2 (reproduction, ladder, composition, top-20)
cd $SCRATCH/review_caliber/carry_composition && python3 decompose_mac.py | tee decompose_mac.out        # -> decompose_mac_rows.json
# Mac — live-side FTRIM counterfactual, live time series to 09-04 16Z, EMA input check
python3 ftrim_live_cf.py | tee ftrim_live_cf.out                                                          # -> ftrim_live_cf.json
# pod — fresh replay of the live-form arm with FTRIM off (V1); device byte-identical (sha256 64c70a44ee88…)
ssh pod2 'D=/workspace/review_scratch/carry_composition/dev; mkdir -p $D/probe_artifacts $D/logs; cd $D; ln -sfn /workspace/port_w10/pod_backup_2026-08-21 pod_backup_2026-08-21; ln -sfn /workspace/port_w10/f8_2026-08-22 f8_2026-08-22; ln -sfn /workspace/port_w10/dlw_2026-08-22 dlw_2026-08-22; cp /workspace/port_w10/w10_universe.py w10_universe.py; export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4; env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy CAL=log FSEED=42 W3FIX=0.21,0,0.79 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=off OUT_TAG=cc_live_w3fix_noftrim_callog_s42 /workspace/venv/bin/python w10_universe.py > logs/cc_live_w3fix_noftrim_callog_s42.log 2>&1'
#   log: RECEIPT d30_n2_c42 net_ex_2024on 0.4139 sharpe_ex 0.946 carry_ex_mean 0.8257 ... DONE 27.2 s
# pod — replay family carry table (28 anchors + by year), panel equality check
ssh pod2 'cd /workspace/review_scratch/carry_composition && P=/workspace/port_w10/probe_artifacts && /workspace/venv/bin/python replay_family_pod.py --panelcheck $P/w10_ablation_series_pod_live_w3fix_callog_s42.npz $P/w10_ablation_series_pod_live_w3fix_calsimple_s42.npz $P/w10_ablation_series_pod_live_callog_s42.npz $P/w10_ablation_series_pod_canon_w3fix_callog_s42.npz $P/w10_ablation_series_pod_canon_callog_s42.npz $P/w10_ablation_series_pod_t400_callog_s42.npz $P/w10_ablation_series_pod_m1t400_callog_s42.npz $P/w10_ablation_series_pod_ftrim_callog_s42.npz $P/w10_ablation_series_pod_live_callog_s2027.npz | tee replay_family_existing.out'
ssh pod2 'cd /workspace/review_scratch/carry_composition && /workspace/venv/bin/python replay_family_pod.py dev/probe_artifacts/w10_ablation_series_cc_live_w3fix_noftrim_callog_s42.npz | tee replay_family_V1.out'
# pod — dump 28-anchor W rows of 4 arms and the replay inputs (pinned king, F10, qvk, y4 mask, meta members); scp to Mac
#   (inline python in the session; outputs W_overlap_4arms.json, replay_inputs_overlap.json)
# Mac — structural tests: V1 vs live ladder, rank-base test, FTRIM name sets, scaled bound
python3 structural_tests.py | tee structural_tests.out                                                    # -> structural_tests.json
# Mac — residual checks: ONG exclusion, eligible-set mechanism (rolling.npz qvm vs meta qvk), ONG diagnostics
python3 residual_checks.py | tee residual_checks.out
# pod — stop layer (d30) vs no stop (S0): overlap, by year, S0 net_ex bound
ssh pod2 'cd /workspace/review_scratch/carry_composition && /workspace/venv/bin/python stop_arm_pod.py | tee stop_arm.out'   # -> stop_arm.json
# pod — ONG in S0 vs d30 per arm (inline python; printed: V1 S0 overlap carry 2.200, ONG S0≠d30 from 08-21 04Z, 59 anchors)
# Mac — live stop overlay (inline): stop_overlay.py docstring, stop_overlay.log FIRE line
# Mac — executor stop audit (inline, read-only, after the lead's query): config/book.json per_name_stop; live/per_name_stop.py L1-150;
#   scheduler/anchor_loop.py L2095-2116; state/live/per_name_stop.json; state/notify_audit.jsonl (40 per_name_stop events, 0 ONG);
#   state/anchor_runs.log phase_C per_name_stop dicts (157 lines, 0 ONG); pilot_log/2026MMDD/position_readback.jsonl ONGUSDT rows 08-26 00Z -> 09-02 20Z
```

Receipt files (Mac scratch): `decompose_mac.py/.out/_rows.json`, `ftrim_live_cf.py/.out/.json`, `replay_family_pod.py`, `replay_family_existing.out`, `replay_family_V1.out`, `replay_family_existing.json` (merged), `w10_ablation_summary_cc_live_w3fix_noftrim_callog_s42.json`, `cc_live_w3fix_noftrim_callog_s42.log`, `W_overlap_4arms.json`, `replay_inputs_overlap.json`, `structural_tests.py/.out/.json`, `residual_checks.py/.out`, `stop_arm_pod.py`, `stop_arm.out/.json`, `SHA256SUMS` (23 files). Pod scratch: the pod-side scripts/outputs plus `dev/probe_artifacts/w10_ablation_series_cc_live_w3fix_noftrim_callog_s42.npz`, `dev/logs/commands.txt`, `SHA256SUMS` (13 files). No production file was modified.
