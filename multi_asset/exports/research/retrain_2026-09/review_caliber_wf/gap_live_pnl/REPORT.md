# Live-book P&L: reconciliation of three instruments (2026-08-26 04Z → 2026-09-04 08Z)

> **创建:** 2026-09-04 16:06Z | **Session:** review_caliber/gap_live_pnl (teammate, read-only on `~/wide_shadow` and `~/dl_quant_live`) | **状态:** reconciled; two items UNRESOLVED (§9) | **作废条件:** any instrument re-run on a different log state, or the executor changes its pricing moment / readback timing.
> Device: `canon_reconcile.py` sha256 `03ab65399c0084061076a2c85f1eb80575bd6f8bd78f4309d4909e9e46fb4525`; input `rolling.npz` sha256 `4a30b7bb03d49a645a35a9d27d39f27ef8c89ac67c4e8539193bfc4e3c30c942` (identical to the sha I2 recorded); outputs `canon_report.json` `535d9ca4…`, `canon_run.log` `0871ffeb…`. Run: `python3 canon_reconcile.py > canon_run.log` at 2026-09-04T16:05:54Z. Structural dump: `dump_logs.py` → `dump_logs.out`. All under `scratchpad/review_caliber/gap_live_pnl/`.

## 0. Bottom line

**The three instruments do not disagree on any common anchor except one.** Paper Π, paper Σ, funding and the twin are bit-identical between I1 and I2 on 49 of the 50 anchors they share (max |Δ| = 0.0000 bps; §5). The headline gaps come from three things only: (a) different anchor sets (I1 starts at the first combo anchor 08-26 04Z and includes the halted 08-26 16Z anchor; I2 starts one anchor earlier at the pre-combo 08-26 00Z and, because it ran 80 minutes later, also closes 09-04 08Z); (b) one anchor, 08-26 12Z, where the book was flattened 26 minutes into the window and the two scripts read different position snapshots (I1 +0.00, I2 −68.32 bps); (c) a different shift grid for the "venue-aligned" paper series (I1 25 min, I2 20 min). I3 is the same twin in notional form plus the same funding: its sleeve total equals my notional-twin + funding to ≤0.01 USDT on all 12 anchors it covers, but its β leg uses an unshifted BTC window that does not match its own sleeve window.

**Reconciled numbers to carry forward** (canonical set = 50 clean 4h windows, 08-26 04Z … 09-04 08Z, exclusions in §3; bps of realized gross per anchor; VERIFIED):

| measure | n | mean | sd | s.e. | sum |
|---|---|---|---|---|---|
| paper Π (N, N+4h], target weights | 50 | **+2.88** | 33.8 | 4.8 | +144.0 |
| paper Σ (N, N+4h] | 50 | +1.57 | 34.7 | 4.9 | +78.4 |
| paper Π shifted 25 min (venue-aligned) | 49 | **+0.80** | 30.0 | 4.3 | +39.4 |
| paper Σ shifted 25 min | 49 | +0.37 | 30.6 | 4.4 | +18.0 |
| twin = positions × Δmid | 50 | **+1.58** | 32.2 | 4.6 | +79.0 |
| funding (settlement in (N, N+4h]) | 50 | **−1.95** | 0.65 | 0.09 | −97.3 |
| twin + funding | 50 | **−0.37** | 32.1 | 4.5 | −18.4 |
| corr(paper Π, twin) / corr(paper Π s25, twin) | | 0.761 / 0.822 | | | |

Without the 09-03 deposit day (drop the six windows ending in the 09-03 nav-day, N = 09-02 20Z … 09-03 16Z; n = 44): paper Π +4.85, paper Π s25 +2.17, twin +0.82, funding −2.01, **twin+funding −1.19** (sd 33.5, s.e. 5.05). Before the deposit (N < 09-02 20Z; n = 40): twin +2.59, funding −2.09, twin+funding +0.49 (s.e. 5.45). None of the twin+funding means is distinguishable from zero at n ≈ 50.

Daily check (§7): twin+funding reproduces the executor's own equity delta net of transfers on every full day once two timing terms are added (the twin prices positions at N+24 min, `daily_nav` at N+42 min, and fills execute in between). Over the eight full days 08-27 … 09-03 the executor's equity moved +382.4 USDT, twin+funding says +415.9, and the residual after the timing bridge, the fill-vs-mid term, BNB commissions and one known funding gap is −48 USDT (≈ −6 USDT/day on a 41k gross book). 09-03 (deposit day, six windows) closes to +7 USDT and must not be dropped. 08-26 (flatten day) and 09-04 (partial day; cache does not yet cover the last bridge) do not close and are flagged.

## 1. Instruments (files, hashes, what each printed)

| | I1 | I2 | I3 |
|---|---|---|---|
| script | `multi_asset/exports/research/retrain_2026-09/live_paper_vs_real.py` sha256 `934d63b2…` | `scratchpad/review_caliber/gt/mac_live_reconcile.py` sha256 `64da26cd…` (= its self-reported `self_sha256`) | `~/regime_dash/beta_alpha_attrib.py` sha256 `89138612…` + `~/regime_dash/regime_dash.py` sha256 `4349a5c5…` (sleeve source) |
| output | `live_paper_vs_real_20260904.out` (run 12:29Z; 51 anchors 08-26 04Z → 09-04 04Z) | `gt/live_reconcile_report.json`, `gt/mac_run.log` (run 13:49Z; 52 anchors 08-26 00Z → 09-04 08Z) | `~/regime_dash/beta_alpha.jsonl` (77 rows; sleeve populated from 09-02 04Z; 12 anchors with sleeve) |
| headline | paper Π +2.93, Σ +1.90, shift25 +0.57, twin +1.72, funding −1.92, twin+funding −0.20 | paper Π +1.957, Σ +0.818, shift20 +0.669, twin +0.029, funding −1.909, twin+funding −1.880 | sleeve total (USDT) = price + carry per anchor; β P&L; α = sleeve − β P&L |

A verbatim re-run of I1 from the scratch dir at 15:56Z (`I1_rerun_live_paper_vs_real.py` → `I1_rerun.out`) now shows 52 anchors (09-04 08Z became closable at the 12Z anchor) with twin +1.55 / twin+funding −0.36; the original 51-anchor rows are preserved in `…/6737834a…/scratchpad/live_paper_vs_real_rows.npy` (mtime 20:29 local) and were used for the per-anchor comparison in §5.

## 2. Definitional differences, side by side (VERIFIED from source)

| item | I1 `live_paper_vs_real.py` | I2 `mac_live_reconcile.py` | I3 `beta_alpha_attrib.py` (+ `regime_dash.py`) | canonical (this report) |
|---|---|---|---|---|
| anchor universe | iterates `anchors.jsonl` rows (L36 `for A in sorted(anch)`), keeps A ≥ 08-26 04Z (L37 "combo 起"), needs `target_live/A.json`, an A+4h row and Σ\|w\| > 0. **Includes 08-26 16Z** (halted, gross 0: paper computed, twin/funding NaN). At its 12:29Z run the last closable anchor was 09-04 04Z → **51** | same but from 08-26 00Z (L57) and **skips realized_gross < 1000** (L61, drops 08-26 16Z); ran after the 12Z anchor → closes 09-04 08Z → **52** | every 4h grid point in the cache with a target file (L45); sleeve only where `regime_dash.jsonl` has the A+4h row (labels from 09-02 08Z) → 12 anchors | 08-26 04Z … 09-04 08Z; anchor row at both ends, realized_gross ≥ 1000, no intra-window flatten → **50** (§3) |
| first combo anchor | 04Z (correct: `external_book.producer` flips from `shadow_loop_v3` to `combo_stage_v1` at 08-26 04Z; dump_logs) | 00Z (one pre-combo anchor included) | n/a | 04Z |
| paper window | rows ts in (A, A+4h] via `cd[i0+1 : i1+1]` (L9); NaN if < 40 of 48 bars (L10) | rows ts in (N, N+4h] via `row_of[N+300] … row_of[N+14400]` (L24); NaN if < 46 of 48 (L29) | n/a | (N, N+4h]; NaN if > 2 bars missing. Identical result: max Δ vs I1 and I2 = 0.0000 bps |
| paper calibers | Π = `expm1(Σ log1p r)`, Σ = `Σ r`, and `expm1(Σ r)` ("装置法") | Π, Σ, Σ log1p ("paper_log") | – | Π and Σ |
| paper "venue-aligned" shift | **5 bars = 25 min** (L43 `rets(A,5)`) | **4 bars = 20 min** (L74; comment says "closest 5m grid to N+24m") | – | **25 min**. Receipt: actual `anchor_ts` − nominal = 1382 s up to 08-27 04Z and 1442 s from 08-27 08Z (60/60 anchors); median first fill = actual anchor + 2.1 s = nominal + 1443.8 s; notional-weighted median fill = nominal + 1501 s (`dump_logs.out` "ACROSS ANCHORS"). 24.0 min is closer to 25 than to 20; the BTC check (§6) confirms the 25-min window tracks the venue mid ratio |
| weights | `target_live` `weights` / Σ\|w\| (L43); `gross_norm` unused | same | β uses `weights` / Σ\|w\|; **sleeve uses venue notionals** | `weights` / Σ\|w\| (Σ\|w\| equals `gross_norm` to 1e-4 on every file; dump_logs) |
| twin: positions | `position_readback` keyed by **nominal** anchor (L27 `anchor_ts//14400*14400`), last row per symbol wins → on 08-26 12Z the 12:49:28Z `ladder_flatten@post_flatten` read (334 names, all qty 0) **overwrites** the 12:23Z post-anchor read | keyed by **actual** `anchor_ts` float (L47), i.e. only that anchor's `fapi/v3/account@post_anchor` rows | `regime_dash.py` L106 keys by `round(anchor_ts/14400)` = nominal (same exposure; not hit in its 09-02+ range); uses `venue_position_notional` | keyed by actual `anchor_ts`, `source == fapi/v3/account@post_anchor` only; qty × Δmid (primary) and notional × ratio (I3 form) both computed |
| twin: mids | `mid_at_anchor_vector` of rows A and A+4h (bookTicker mid at the pricing moment ≈ N+24 min) | same | same (`regime_dash.py` L55–66 `mids()`) | same |
| twin: formula | Σ q·(m1 − m0) over names with m0 > 0 in both vectors (L51–52) | same, skipping q = 0 | Σ notional·(m1/m0 − 1) (L121); notional = qty × mark at the ~N+41 min read | qty form = I1/I2; notional form = I3 |
| twin: denominator | `realized_gross` of row A, else Σ\|q·m0\|, else NaN (L54) | `realized_gross` of row N | USDT, no denominator (β P&L uses `realized_gross` as `gross_usdt`, L21) | `realized_gross` of row N |
| sign | q signed (short < 0); P&L positive when we gain | same | same; `funding_paid` is our signed cash flow | same |
| funding window | settlement in (A, A+4h] via `(ts−1)//14400` (L33) | `N < settlement ≤ N+4h` (L93) | `ceil(st/14400)*14400` (`regime_dash.py` L111): settlements in (A−4h, A] labelled A = the "prev interval" of anchor A = (N, N+4h] for anchor N | (N, N+4h] |
| names missing mid / cache | paper: masked names dropped, Σ\|w\| **not** rescaled; twin: counted in `nmiss` (mean 2.5 of 265 names) | same (`paper_cov` 1.000, `twin_cov` 0.9996) | sleeve skips names lacking either mid | same as I2 |
| daily mapping | anchor A → day of (A+4h+3min); compares Σ(twin+funding) with the last `daily_nav` row's `equity_delta_since_prev` − `external_flow_usdt` (L72–78). 08-26 prints NaN (16Z twin NaN) and is silently lost; 09-04 used the 08:43Z row | windows whose end pricing ∈ (nav_ts(D−1), nav_ts(D)]; `days_with_6_windows` counts 4h windows only (L136–149) → 5 days, but 08-30 and 09-02 are fully covered by 8h windows I2 does not build | none | §7: I2's span rule + 8h windows where the middle anchor is missing + timing bridge + fill term |

## 3. Canonical anchor set (VERIFIED against the logs; receipts in `dump_logs.out`)

Nominal slots 08-26 04Z … 09-04 08Z = 56. Excluded 6 → **50 canonical**:

| slot | why excluded | receipt | I1 | I2 |
|---|---|---|---|---|
| 08-26 12Z | book flattened intra-window at 12:49:28Z (`position_readback` source `ladder_flatten@post_flatten`, 334 names, all qty 0); positions held 12:23Z → 12:49Z only, so a 4h twin is fiction (I2 −68.32 bps) and I1's +0.00 is an accident of dict overwrite | `dump_logs.out` readback table; `docs/ERROR_LEDGER_2026-08-20.md` L233 (gross_mult 1.5→2.0 first anchor, 157 venue rejects, §4-5e flatten, "平仓成本 ≈$20-30") | in (twin 0.00) | in (twin −68.32) |
| 08-26 16Z | `opening_halted=True`, `realized_gross=0.0`, readback 267 rows all qty 0 | `dump_logs.out` anchors table | in (paper +16.73, twin NaN) | out |
| 08-29 16Z | next anchor 08-29 20Z has no `anchors.jsonl` row → no 4h end mid. Positions held to 08-30 00:24Z; an **8h window** is computed and used in §7 (twin +44.62 bps/8h, funding −5.13) | `pilot_journal/journal_2026-08.md` L5–6 (E-0829-B: 18:06Z restart killed the guardians; "20:00Z 锚 fail-open 不交易, 权益无损") | out | out |
| 08-29 20Z | no `target_live/1788033600.json`, no anchor row, no fills; readback at 20:29:03Z shows the 16Z book unchanged (256 names, gross 42191); `daily_nav` row at 20:29Z with `target_gross 0.0` | same E-0829-B; target_live listing in `dump_logs.out` | out | out |
| 09-01 20Z | next anchor 09-02 00Z missing → 8h window to 09-02 04:24Z used in §7 (twin +64.04 bps/8h) | E-0902-A (`ERROR_LEDGER` L267–271): venue cut max leverage on 182 names overnight, `arm()` refused at 00:00Z, zero trades, book kept the 20Z positions | out | out |
| 09-02 00Z | target file exists but no anchor row / readback / fills / nav row | E-0902-A | out | out |

Also computed, outside the canonical range: 08-25 20Z and 08-26 00Z (producer `shadow_loop_v3`, pre-combo; needed only so the 08-26 nav-day has all six windows).

## 4. Summary by set (bps per anchor; `canon_run.log` "SUMMARY BY SET")

| set | n | paper Π | paper Σ | paper Π s25 | paper Π s20 | twin | funding | twin+funding (sd, s.e.) |
|---|---|---|---|---|---|---|---|---|
| canonical | 50 | +2.880 | +1.568 | +0.803 (49) | +1.548 (49) | +1.579 | −1.947 | **−0.368** (32.1, 4.54) |
| canonical ex 09-03 nav-day | 44 | +4.847 | +2.799 | +2.170 (43) | +3.431 (43) | +0.823 | −2.014 | **−1.191** (33.5, 5.05) |
| canonical, N < 09-02 20Z | 40 | +7.443 | +5.250 | +3.812 | +5.108 | +2.587 | −2.093 | **+0.494** (34.5, 5.45) |
| canonical + flatten anchor 12Z | 51 | +1.977 | +0.851 | +0.068 (50) | +0.526 (50) | +0.209 | −1.909 | −1.700 |
| I1's set, recomputed here | 51 | +2.932 | +1.898 | +0.568 | +1.157 | +0.358 (50) | −1.921 (50) | −1.563 (50) |
| I2's set, recomputed here | 52 | +1.957 | +0.818 | +0.199 (51) | +0.669 (51) | +0.029 | −1.909 | −1.880 |

I2's set reproduces I2's published numbers exactly (paper Π +1.957, Σ +0.818, s20 +0.669, twin +0.029, funding −1.909, twin+funding −1.880). I1's set reproduces I1's paper Π (+2.93), Σ (+1.90) and s25 (+0.57) exactly; its twin differs (+0.36 here vs +1.72 published) **only** because of the 08-26 12Z overwrite (§5).

## 5. Numerical decomposition of the I1-vs-I2 gaps (VERIFIED; `canon_report.json["decomposition"]`)

Per-anchor comparison of I1's saved rows (51) against I2's JSON rows (52): 50 common anchors; on them max |Δ paper Π| = 0.0000, max |Δ paper Σ| = 0.0000, max |Δ funding| = 0.0000, max |Δ twin| = 68.32 (08-26 12Z only; the other 49 anchors Δ = 0.0000).

**Twin: I1 +1.72 (n=50, Σ +86.21) → I2 +0.029 (n=52, Σ +1.49).** Σ bridge: +86.21 − 68.32 (08-26 12Z: I1 reads the post-flatten zero positions, I2 the pre-flatten positions) − 9.14 (I2 adds pre-combo 08-26 00Z) − 7.25 (I2 adds 09-04 08Z, closable only after 12:24Z) = +1.49 ✓. In means: −1.37 bps from the flatten anchor, −0.33 from the anchor-set change. Zero from mid-vector choice, denominator or sign convention: those are identical.

**Paper Π: I1 +2.93 (n=51, Σ +149.5) → I2 +1.957 (n=52, Σ +101.8).** Σ bridge: +149.5 − 16.73 (drop halted 08-26 16Z, priced by I1 on a book that did not exist) + 0.96 (add 08-26 00Z) − 31.95 (add 09-04 08Z) = +101.8 ✓. Entirely anchor set.

**Funding: I1 −1.92 → I2 −1.909.** Σ −96.05 − 1.92 (00Z) − 1.30 (09-04 08Z) = −99.27 ✓ (both count 08-26 12Z as 0.00: no settlements were recorded 13–20Z while flat).

**Twin+funding: I1 −0.20 → I2 −1.88.** Σ −9.85 − 68.32 − 11.06 − 8.55 = −97.78 ✓.

**Shifted paper: I1 +0.57 (25 min) vs I2 +0.669 (20 min).** Not the same series: on the 50 common anchors the 25-min mean is +0.07 and the 20-min mean +0.53, mean |per-anchor difference| = 6.96 bps. The rest of I1's +0.57 is 08-26 16Z (+25.59 on a non-existent book); I2's +0.669 excludes 09-04 08Z (cache ends 12:00Z, shifted window incomplete).

## 6. Which conventions match the executor's own accounting

The executor values the book as `equity = totalWalletBalance + totalUnrealizedProfit` at the post-anchor read (`daily_nav.nav_source`, `nav_ts` ≈ N+42 min, one row per anchor), realises P&L at fill price, and books funding as the venue's `FUNDING_FEE` income at settlement (`realised_by_type`). Against that:

- **Twin = post-anchor `position_readback` qty × (mid at end pricing moment − mid at start pricing moment) / `realized_gross`** is the right instrument and is what I1, I2 and (in notional form) I3 compute; I2's implementation (actual-`anchor_ts` keys, post-anchor source only, flat-book skip) is the one to keep. **VERIFIED**: `funding.jsonl` summed from 00:00Z inclusive equals the venue's `FUNDING_FEE` since 00:00Z to the cent on 9 of 10 days (08-28 −40.39 vs −40.39; 09-03 −47.24 vs −47.24); the one miss is 09-02 (−37.08 vs −46.83): settlement hours 01–04Z are absent from `funding.jsonl` after the E-0902-A refused anchor.
- The twin is priced at N+24 min but the executor's snapshot is at ~N+42 min, and fills happen in between. Both timing terms are measurable (§7) and net to ≈0 across days; they are why single-day residuals of ±200 USDT appear on the 166k book (09-03 −219.8, 09-04 +197.7) without any P&L leak.
- **Shifted paper must use the 25-min grid.** BTC 4h return from the cache on (N+25m, N+4h+25m] vs the venue mid ratio (N+24:02 → N+4h+24:02) agree to a few bps on every anchor (09-03 12Z +3.533% vs +3.535%; 08-28 12Z −3.086% vs −2.854%), whereas the unshifted (N, N+4h] differs by up to 1.6 pp (08-28 12Z −1.576%; 08-28 16Z −0.974% vs +0.236%). I2's 20-min comment is arithmetically wrong (24 min is closer to 25).
- **I3's sleeve** = notional-twin + funding, **VERIFIED identical** to my notional form on all 12 anchors (|Δ| ≤ 0.01 USDT; 09-04 00Z −630.13 vs −630.15). The qty form differs from the notional form by up to 36.7 USDT on the 09-03 16Z scale-up anchor (−76.97 vs −40.30) because notional = qty × mark at N+41 min, not qty × mid at N+24 min; the qty form is the cleaner "fixed position between two pricing moments". **I3's β P&L is mis-specified**: `btc_ret_4h` is the unshifted cache window (L11) while the sleeve it is subtracted from is priced N+24m → N+4h+24m; 09-03 12Z uses BTC +4.373% (β P&L −297.76) where the sleeve's own window saw +3.535% (≈ −240); 09-02 08Z −0.848% vs −0.396%; 09-03 20Z −0.602% vs −0.126%; 09-04 00Z −0.520% vs −0.185%. Its α column inherits the error. Its `gross_nav()` (L21) also takes `realized_gross` from any row with A ≤ ts < A+4h, which on a flatten anchor would be the pre-flatten gross.

## 7. Daily cross-check against `daily_nav` (all 10 days; USDT; `canon_run.log` "DAILY vs daily_nav")

Span for day D = (nav_ts of the last row of D−1, nav_ts of the last row of D]; equity Δ net = nav − prev nav − `external_flow_usdt`. Windows = anchor windows whose end pricing moment falls in the span (8h windows where the middle anchor is missing). Bridge(N) = post-anchor positions of anchor N × cache return from the 5m close at N+25 to N+45 min (the move between the twin's pricing moment and the NAV snapshot); IS = Σ over that anchor's fills of sgn·(mid_N − fill_px)·qty (> 0 when fills beat the anchor mid; includes intra-rebalance drift); commission from `fills.jsonl` `commission` (BNB, 10194/10194 fills) × BNB mid at that anchor. Closing residual = residual − (bridge end − bridge start) − IS + commission.

| day | equity Δ net | ext flow | n win | twin | funding (span) | twin+funding | residual | IS | bridge end / start | residual − Δbridge − IS | commission | closing residual | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 08-26 | +70.8 | 0 | 6 | −6.0 | −15.6 | −21.6 | +92.4 | +7.4 | −33.9 / +14.8 | +133.7 | 5.4 | ≈ −43 (see note) | **flatten day, does not close**: the 12Z window twin (−201.8) is invalid; replacing it by the executor's own 12:45Z→16:38Z equity change (−19.7; funding 0) gives twin+funding +160.5, residual −89.7, ≈ −43 after bridge/IS/commission. Two pre-combo windows, one halted window. UNRESOLVED |
| 08-27 | −64.2 | +5449.6 | 6 | −70.1 | −35.2 | −105.3 | +41.1 | +5.6 | −7.1 / −33.9 | +8.7 | 6.3 | +15.0 | closes |
| 08-28 | +169.1 | 0 | 6 | +207.5 | −41.7 | +165.8 | +3.3 | +4.1 | +7.5 / −7.1 | −15.4 | 1.5 | −13.9 | closes |
| 08-29 | +411.2 | 0 | 5 | +392.4 | −44.9 | +347.5 | +63.7 | +2.9 | n/a / +7.5 | +68.3 | 2.4 | +70.7 | 16:24Z→20:29Z segment uncovered (no 20Z mid); see merged row |
| 08-30 | −171.8 | 0 | 6 (one 8h) | −56.0 | −69.2 | −125.2 | −46.7 | +6.4 | +32.8 / n/a | −85.9 | 3.6 | −82.3 | start bridge undefined (08-29 20Z has no mid); see merged row |
| 08-29+30 merged | +239.4 | 0 | 11 | | | +222.4 | +17.0 | +9.3 | +32.8 / +7.5 | −17.6 | 6.0 | −11.6 | closes |
| 08-31 | −267.0 | 0 | 6 | −186.9 | −54.3 | −241.2 | −25.7 | +1.1 | −19.9 / +32.8 | +25.9 | 2.6 | +28.5 | closes |
| 09-01 | −336.9 | 0 | 6 | −304.8 | −57.9 | −362.6 | +25.7 | +2.2 | +40.1 / −19.9 | −36.4 | 1.9 | −34.5 | closes |
| 09-02 | +778.1 | 0 | 5 (one 8h) | +691.7 | −38.5 | +653.2 | +124.9 | +70.3 | +146.0 / +40.1 | −51.3 | 2.8 | −48.5 (−38.7 after the +9.75 `funding.jsonl` gap) | closes; IS +66.2 and the end bridge are dominated by AKEUSDT (+14% between the 20:24Z mid and the 20:40Z taker fills) |
| 09-03 | −136.1 | +62997.8 | 6 | +131.2 | −47.6 | +83.6 | −219.8 | −44.6 | −3.1 / +146.0 | −26.1 | 33.4 | +7.3 | **closes; deposit day must be kept** (scale-up to 163k gross at 16:24Z: 898 fills, 126.7k notional, taker IS −54.0, commission 33.4) |
| 09-04 (partial, to 12:43Z) | −994.0 | 0 | 4 | −1110.9 | −80.8 | −1191.8 | +197.7 | +4.8 | n/a / −3.1 | +189.8 | 4.4 | UNRESOLVED | end bridge needs cache bars 12:30–12:45Z (cache ends 12:00Z); ≈ +190 is a 0.12% move on a 161k book. Re-run after the 16Z anchor |

Totals 08-27 … 09-03 (eight full days): equity +382.4; twin+funding +415.9; raw residual −33.5; after bridge and IS −112.2; after commissions (54.5) −57.7; after the 09-02 funding gap −48.0. Sources not modelled: mark-vs-mid at the two snapshots, float16 cache rounding, the uncovered 08-29 16:24Z→20:29Z segment. IS over all combo anchors: maker fills +119.2 USDT on 249k notional (+4.8 bps), taker top-ups −64.4 on 46k (−14.0 bps).

Funding cross-check per day (`funding.jsonl` from 00:00Z inclusive vs venue `FUNDING_FEE` since 00:00Z at the day's last row): 08-26 −15.39/−15.39, 08-27 −35.05/−35.05, 08-28 −40.39/−40.39, 08-29 −43.53/−43.53, 08-30 −65.37/−65.37, 08-31 −53.06/−53.06, 09-01 −56.36/−56.36, 09-02 **−37.08/−46.83**, 09-03 −47.24/−47.24, 09-04 −79.15/−79.15. (With an exclusive 00:00Z boundary the two differ by 12–19% every day: a boundary artefact, not under-recording.)

The claim "only four clean days, 09-03 dropped" is wrong on both counts: 09-03 has six 4h windows and closes to +7 USDT; 08-30 and 09-02 are fully covered once the 8h windows are built; the merged 08-29+30 block closes to −12 USDT. The only day that genuinely does not reconcile by twin is 08-26 (flatten), and 09-04 is simply not finished.

## 8. I3 rows (USDT; `canon_run.log` "I3 (beta_alpha)")

| anchor | I3 sleeve | canon notional-twin + funding | canon qty-twin + funding | I3 β P&L | I3 BTC 4h (unshifted cache) | venue BTC ratio (N+24m→N+4h+24m) |
|---|---|---|---|---|---|---|
| 09-02 04Z | −4.83 | −4.83 | −5.61 | +7.55 | −0.115% | −0.127% |
| 09-02 08Z | +25.81 | +25.82 | +27.31 | +57.67 | −0.848% | −0.396% |
| 09-02 12Z | +250.99 | +251.00 | +251.41 | −40.69 | +0.601% | +0.665% |
| 09-02 16Z | +147.24 | +147.25 | +129.45 | −4.48 | +0.067% | −0.115% |
| 09-02 20Z | +164.36 | +164.35 | +165.91 | +0.11 | −0.002% | −0.421% |
| 09-03 00Z | −56.34 | −56.34 | −58.76 | −31.05 | +0.473% | +0.686% |
| 09-03 04Z | −36.68 | −36.67 | −36.31 | +3.21 | −0.049% | +0.285% |
| 09-03 08Z | +16.51 | +16.50 | +15.33 | −24.01 | +0.364% | +0.206% |
| 09-03 12Z | +76.77 | +76.77 | +74.43 | −297.76 | +4.373% | +3.535% |
| 09-03 16Z | −40.30 | −40.30 | −76.97 | −126.52 | +0.500% | +0.789% |
| 09-03 20Z | −153.04 | −153.04 | −148.08 | +153.28 | −0.602% | −0.126% |
| 09-04 00Z | −630.13 | −630.15 | −636.73 | +126.27 | −0.520% | −0.185% |

## 9. Labels

- **VERIFIED**: every definitional row in §2 (read from source, line numbers given); anchor-set membership and the six exclusions (logs + ledger/journal receipts); bit-identity of paper/funding/twin on 49 common anchors; the Σ bridges in §5 (close to 0.01 bps); I2's published numbers reproduced exactly; I1's paper numbers reproduced exactly; the 08-26 12Z overwrite mechanism (readback table shows the 12:49:28Z `ladder_flatten@post_flatten` rows in the same nominal slot); anchor timing (1382/1442 s) and fill timing (median first fill +2.1 s after the actual anchor); `funding.jsonl` = venue `FUNDING_FEE` on 9/10 days; I3 sleeve = notional-twin + funding on 12/12 anchors; BTC cache-vs-venue alignment at 25 min; `rolling.npz` channel 0 = `close/prev_close − 1` per 5m kline with row ts = bar close (`shadow_loop_v3.py` L285, L292), stored float16 and clipped to ±0.30 (L150).
- **INFERRED**: that the remaining −48 USDT over eight days is mark-vs-mid and cache rounding (not measured); that the 09-04 residual (+190) is the missing end bridge; that AKEUSDT's +14% between mid and fill on 09-02 20Z is a genuine price move rather than a stale mid (not checked against klines).
- **UNRESOLVED**: the 08-26 closing residual (≈ −43 USDT after every adjustment; the flatten's own fills are not in `fills.jsonl`, only bracketed by two nav rows); 09-04 until the cache extends past 12:45Z; the cause of the 09-02 `funding.jsonl` gap (hours 01–04Z absent; consistent with a per-anchor funding puller and the refused 00Z anchor, but the puller code was not read).

## 10. What to carry into the review document

Use §0/§4 and cite this device. State the anchor set explicitly ("50 clean 4h windows, 08-26 04Z → 09-04 08Z, excluding 08-26 12Z/16Z, 08-29 16Z/20Z, 09-01 20Z, 09-02 00Z"). Quote twin+funding as −0.37 ± 4.5 bps/anchor (n=50), −1.19 ± 5.1 without the 09-03 nav-day, +0.49 ± 5.5 before the deposit. For paper, put the 25-min-shifted Π (+0.80) next to the twin (+1.58), not the unshifted Π (+2.88), whenever the sentence is about what the executor could capture. Do not quote I1's twin +1.72 (flatten overwrite) or I2's shift20 +0.669 (wrong grid); I2's twin +0.029 is arithmetically right for its set but includes a pre-combo anchor and the flatten fiction. For I3, use its sleeve column only; do not use its β P&L or α until `btc_ret_4h` is computed on the shifted window.

## Appendix A. Canonical per-slot table (verbatim from `canon_run.log`)

Columns: N | canon | I1 I2 membership | window h | realized_gross | paper Π, paper Σ | s25 Π, s25 Σ | s20 Π | twin | funding | twin+funding | IS USDT | reasons. bps of realized_gross.

```
=== PER-SLOT TABLE (bps of realized_gross; paper on target_live weights) ===
N | canon | I1 I2 | wh | rg | paper_comp paper_sum | s25_comp s25_sum | s20_comp | twin | fund | twin+fund | IS$ | reasons
08-25 20Z | - | .. | 4 |   21975 |  +27.44  +27.57 |  +32.96  +33.12 |  +34.08 |  +28.81 |   -1.89 |  +26.92 |    +0.6 | pre-combo anchor (producer=shadow_loop_v3)
08-26 00Z | - | .2 | 4 |   21999 |   +0.96   -0.90 |   +6.76   +3.44 |   +7.78 |   -9.14 |   -1.92 |  -11.06 |    -1.7 | pre-combo anchor (producer=shadow_loop_v3)
08-26 04Z | Y | 12 | 4 |   22065 |  +47.53  +29.14 |  +38.87  +23.02 |  +36.15 |  +26.55 |   -2.00 |  +24.55 |    +0.7 | 
08-26 08Z | Y | 12 | 4 |   22098 |  +33.62  +31.51 |  +23.73  +24.53 |  +29.86 |  +42.54 |   -1.27 |  +41.27 |    +0.2 | 
08-26 12Z | - | 12 | 4 |   29536 |  -43.17  -34.98 |  -35.96  -29.52 |  -49.53 |  -68.32 |   +0.00 |  -68.32 |    -0.2 | book flattened intra-window (ladder_flatten@post_flatten @ 08-26 12:49Z; E-0826 §4-5e)
08-26 16Z | - | 1. | 4 |       0 |  +16.73  +20.19 |  +25.59  +29.08 |  +32.68 |    nan |    nan |    nan |    +0.0 | flat book at anchor (opening_halted=True, realized_gross=0)
08-26 20Z | Y | 12 | 4 |   15665 |  -50.14  -48.77 |  -47.72  -45.91 |  -45.80 |  -90.99 |   -2.79 |  -93.78 |    +8.3 | 
08-27 00Z | Y | 12 | 4 |   22338 | +100.44 +108.45 |  +80.19  +87.26 |  +81.34 |  +89.60 |   -3.89 |  +85.71 |    -0.8 | 
08-27 04Z | Y | 12 | 4 |   26054 |  +44.52  +43.78 |  +34.07  +31.18 |  +36.60 |  +13.71 |   -2.38 |  +11.33 |    +0.7 | 
08-27 08Z | Y | 12 | 4 |   29410 |  -64.51  -73.21 |  -56.60  -65.24 |  -65.40 |  -37.89 |   -1.28 |  -39.17 |    +1.5 | 
08-27 12Z | Y | 12 | 4 |   40264 |  -13.20  -12.20 |  -15.94  -15.59 |   -7.44 |  -31.59 |   -1.50 |  -33.09 |    +4.0 | 
08-27 16Z | Y | 12 | 4 |   41284 |  +20.18  +21.59 |  +21.04  +22.29 |  +20.22 |  +18.21 |   -1.48 |  +16.73 |    +1.2 | 
08-27 20Z | Y | 12 | 4 |   40828 |   -5.09   -4.58 |   -2.19   -1.75 |   -5.72 |   -8.93 |   -2.17 |  -11.10 |    -0.9 | 
08-28 00Z | Y | 12 | 4 |   41103 |  +16.68  +17.99 |  +27.65  +28.55 |  +22.37 |  +25.03 |   -1.70 |  +23.33 |    -0.0 | 
08-28 04Z | Y | 12 | 4 |   40904 |  +22.36  +22.22 |  +17.70  +17.46 |  +14.42 |  +11.56 |   -1.50 |  +10.06 |    +0.4 | 
08-28 08Z | Y | 12 | 4 |   40999 |  -20.36  -20.22 |  -11.13  -12.05 |   -6.04 |   -4.91 |   -1.44 |   -6.35 |    +0.7 | 
08-28 12Z | Y | 12 | 4 |   41321 |  +35.77  +36.10 |  +36.83  +38.19 |  +32.23 |  +14.02 |   -2.04 |  +11.98 |    +0.7 | 
08-28 16Z | Y | 12 | 4 |   41282 |  +24.55  +22.76 |  +13.59  +11.88 |  +23.09 |  +13.56 |   -1.32 |  +12.25 |    +1.6 | 
08-28 20Z | Y | 12 | 4 |   41298 |  -12.98  -13.86 |  -12.47  -12.50 |  -18.09 |  -15.05 |   -1.73 |  -16.78 |    +0.7 | 
08-29 00Z | Y | 12 | 4 |   41450 |  +38.74  +37.92 |  +38.73  +37.73 |  +46.65 |  +39.86 |   -1.88 |  +37.98 |    +0.5 | 
08-29 04Z | Y | 12 | 4 |   41512 |   +0.70   +0.38 |   +8.33   +8.07 |   +9.31 |   +4.27 |   -1.21 |   +3.06 |    -2.1 | 
08-29 08Z | Y | 12 | 4 |   41616 |  +67.50  +64.27 |  +58.38  +53.26 |  +43.13 |  +65.37 |   -2.20 |  +63.17 |    +1.0 | 
08-29 12Z | Y | 12 | 4 |   42013 |  -11.16   -9.80 |  -26.24  -22.44 |  -12.44 |   -0.10 |   -1.89 |   -1.99 |    +2.0 | 
08-29 16Z | - | .. | 8 |   42181 |   -7.84   -6.85 |  +16.01  +15.05 |  +12.32 |  +44.62 |   -5.13 |  +39.49 |    +1.4 | next anchor row missing -> no 4h end mid; 8h extended window used
08-29 20Z | - | .. | 4 |       0 |    nan    nan |    nan    nan |    nan |    nan |    nan |    nan |    +nan | no target_live file (producer down: E-0829-B restart); no anchors.jsonl row (executor did not trade this slot)
08-30 00Z | Y | 12 | 4 |   42146 |  -15.94  -16.20 |  -13.83  -13.62 |  -20.43 |  -11.40 |   -2.51 |  -13.91 |    +1.1 | 
08-30 04Z | Y | 12 | 4 |   42033 |  +21.77  +21.68 |   +9.91  +10.69 |  +19.29 |  +13.08 |   -2.64 |  +10.44 |    +1.2 | 
08-30 08Z | Y | 12 | 4 |   42505 |   -9.08   -8.47 |   -7.29   -7.53 |   -2.22 |   +3.28 |   -2.53 |   +0.74 |    +1.1 | 
08-30 12Z | Y | 12 | 4 |   42491 |   -3.50   -4.18 |  -15.51  -14.53 |  -19.61 |  -13.73 |   -2.72 |  -16.45 |    +1.4 | 
08-30 16Z | Y | 12 | 4 |   42147 |  -49.84  -50.51 |  -42.97  -43.93 |  -39.66 |  -49.05 |   -2.70 |  -51.75 |    +1.9 | 
08-30 20Z | Y | 12 | 4 |   41395 |   +3.05   +3.47 |  +12.68  +11.56 |  +10.77 |   -1.32 |   -2.64 |   -3.96 |    -0.3 | 
08-31 00Z | Y | 12 | 4 |   41408 |  +17.44  +16.73 |  +17.38  +19.64 |  +14.25 |  +42.16 |   -3.22 |  +38.94 |    +0.5 | 
08-31 04Z | Y | 12 | 4 |   41524 |  -33.84  -42.36 |  -16.14  -24.43 |  -23.03 |  -36.58 |   -2.74 |  -39.32 |    +0.6 | 
08-31 08Z | Y | 12 | 4 |   41509 |   +1.88   +4.47 |  -26.81  -25.27 |  -23.76 |   +5.84 |   -1.44 |   +4.40 |    +0.6 | 
08-31 12Z | Y | 12 | 4 |   41019 |   -4.72   -6.02 |   -8.29   -8.05 |   -3.32 |  -30.91 |   -1.77 |  -32.68 |    -0.2 | 
08-31 16Z | Y | 12 | 4 |   41166 |  -24.28  -25.10 |  -16.99  -17.23 |  -18.96 |  -24.68 |   -1.32 |  -26.00 |    -1.0 | 
08-31 20Z | Y | 12 | 4 |   40975 |  -12.53  -12.35 |  +11.89  +11.16 |   -6.38 |  -13.65 |   -1.96 |  -15.62 |    +0.6 | 
09-01 00Z | Y | 12 | 4 |   40753 |  +25.32   +7.37 |  -11.22  -15.89 |  +18.40 |  -41.08 |   -2.11 |  -43.19 |    -1.3 | 
09-01 04Z | Y | 12 | 4 |   40414 |   +9.95   +8.79 |  -11.77  -10.63 |  -13.54 |   -2.71 |   -2.59 |   -5.29 |    +0.2 | 
09-01 08Z | Y | 12 | 4 |   40200 |  -71.50  -97.82 |  -66.14  -72.08 |  -60.10 |  -36.21 |   -2.75 |  -38.96 |    +0.9 | 
09-01 12Z | Y | 12 | 4 |   39934 |  +58.47  +59.44 |  +51.38  +53.22 |  +44.51 |  +36.05 |   -3.07 |  +32.98 |    +1.0 | 
09-01 16Z | Y | 12 | 4 |   40212 |   -0.36   +1.13 |   +1.88   +2.73 |   +3.12 |  -17.12 |   -1.86 |  -18.98 |    +0.8 | 
09-01 20Z | - | .. | 8 |   40417 |  +39.44  +39.78 |  +16.13  +16.74 |  +21.56 |  +64.04 |   -2.01 |  +62.02 |    +0.5 | next anchor row missing -> no 4h end mid; 8h extended window used
09-02 00Z | - | .. | 4 |       0 |  -26.04  -26.39 |  +35.07  +37.71 |  +18.75 |    nan |    nan |    nan |    +nan | no anchors.jsonl row (executor did not trade this slot)
09-02 04Z | Y | 12 | 4 |   40801 |  +13.75  +13.79 |  -34.66  -38.64 |  -24.72 |   +0.59 |   -1.96 |   -1.38 |    +1.8 | 
09-02 08Z | Y | 12 | 4 |   40555 |  +12.88  +16.01 |  +17.23  +20.66 |  +17.34 |   +9.01 |   -2.28 |   +6.73 |    -0.3 | 
09-02 12Z | Y | 12 | 4 |   40520 |  +14.85  +14.53 |  +44.04  +42.52 |  +34.53 |  +63.93 |   -1.88 |  +62.05 |    +1.0 | 
09-02 16Z | Y | 12 | 4 |   40693 |  +68.78  +52.13 |  +30.90  +23.92 |  +63.42 |  +33.16 |   -1.35 |  +31.81 |    +1.2 | 
09-02 20Z | Y | 12 | 4 |   41282 |  -31.96  -18.96 |   -2.75   +9.21 |  -19.73 |  +42.20 |   -2.01 |  +40.19 |   +66.6 | 
09-03 00Z | Y | 12 | 4 |   41502 |  -20.27  -17.14 |  -24.49  -24.27 |  -20.60 |  -12.53 |   -1.63 |  -14.16 |    +6.9 | 
09-03 04Z | Y | 12 | 4 |   41674 |   +6.35  +10.25 |  -10.52   -6.66 |  -15.65 |   -6.76 |   -1.95 |   -8.71 |    +0.9 | 
09-03 08Z | Y | 12 | 4 |   41639 |   +6.81  +10.55 |   +3.18   +6.54 |  +14.00 |   +4.71 |   -1.03 |   +3.68 |    -1.3 | 
09-03 12Z | Y | 12 | 4 |   42029 |   -7.30   -8.42 |   -3.25   -5.86 |  -12.18 |  +18.90 |   -1.19 |  +17.71 |    -1.6 | 
09-03 16Z | Y | 12 | 4 |  163439 |  -22.91  -21.04 |  -16.13  -13.61 |  -17.50 |   -3.78 |   -0.92 |   -4.71 |   -54.0 | 
09-03 20Z | Y | 12 | 4 |  166138 |  -20.51  -24.89 |  -36.87  -41.08 |  -36.25 |   -7.41 |   -1.51 |   -8.91 |    +4.5 | 
09-04 00Z | Y | 12 | 4 |  165589 |  -15.20  -14.91 |  -16.10  -14.91 |   -8.75 |  -37.41 |   -1.05 |  -38.45 |    +2.2 | 
09-04 04Z | Y | 12 | 4 |  164402 |  -16.79  -13.85 |   -6.21   -3.55 |  -11.81 |  -15.20 |   -1.05 |  -16.25 |    +1.6 | 
09-04 08Z | Y | .2 | 4 |  163524 |  -31.95  -33.18 |    nan    nan |    nan |   -7.25 |   -1.30 |   -8.55 |    +1.0 | 

```

## Appendix B. Daily table (verbatim from `canon_run.log`)

```
=== DAILY vs daily_nav (USDT) ===
day | span | nav_prev->nav | ext | eqΔnet | nwin | twin$ | fund$(span) | twin+fund | resid | IS$ | bridge_end(anchor) | bridge_start(anchor) | resid−bridgeΔ−IS | paper$ | paper_s25$ | fund.jsonl since00Z (excl/incl 00Z) vs venue FUNDING_FEE | notes
20260826 | (08-25 20:46Z, 08-26 20:45Z] | 15057->15127 | 0 |    +70.8 | 6 |     -6.0 |   -15.6 |    -21.6 |   +92.4 |   +7.4 |   -33.9(08-26 20Z) |   +14.8(08-25 20Z) |  +133.7 |   +114.1 |   +119.3 | -11.45/-15.39 vs -15.39 | ['08-25 20Z', '08-26 00Z', '08-26 04Z', '08-26 08Z', '08-26 12Z', '08-26 16Z'] ['08-25 20Z:pre-combo anchor (producer=shadow_loop_v3)', '08-26 00Z:pre-combo anchor (producer=shadow_loop_v3)', '08-26 12Z:book flattened intra-window (ladder_flatten@post_flatten @ 08-26 12:49Z; E-0826 §4-5e)', '08-26 16Z:flat book at anchor (opening_halted=True, realized_gross=0)']
20260827 | (08-26 20:45Z, 08-27 20:41Z] | 15127->20513 | 5450 |    -64.2 | 6 |    -70.1 |   -35.2 |   -105.3 |   +41.1 |   +5.6 |    -7.1(08-27 20Z) |   -33.9(08-26 20Z) |    +8.7 |   +102.3 |    +49.3 | -30.81/-35.05 vs -35.05 | ['08-26 20Z', '08-27 00Z', '08-27 04Z', '08-27 08Z', '08-27 12Z', '08-27 16Z'] []
20260828 | (08-27 20:41Z, 08-28 20:41Z] | 20513->20682 | 0 |   +169.1 | 6 |   +207.5 |   -41.7 |   +165.8 |    +3.3 |   +4.1 |    +7.5(08-28 20Z) |    -7.1(08-27 20Z) |   -15.4 |   +304.9 |   +339.7 | -32.87/-40.39 vs -40.39 | ['08-27 20Z', '08-28 00Z', '08-28 04Z', '08-28 08Z', '08-28 12Z', '08-28 16Z'] []
20260829 | (08-28 20:41Z, 08-29 20:29Z] | 20682->21093 | 0 |   +411.2 | 5 |   +392.4 |   -44.9 |   +347.5 |   +63.7 |   +2.9 | nan(08-29 20Z) |    +7.5(08-28 20Z) |   +68.3 |   +344.0 |   +276.3 | -37.76/-43.53 vs -43.53 | ['08-28 20Z', '08-29 00Z', '08-29 04Z', '08-29 08Z', '08-29 12Z'] []
20260830 | (08-29 20:29Z, 08-30 20:42Z] | 21093->20921 | 0 |   -171.8 | 6 |    -56.0 |   -69.2 |   -125.2 |   -46.7 |   +6.4 |   +32.8(08-30 20Z) | nan(08-29 20Z) |   -85.9 |   -272.3 |   -227.1 | -55.40/-65.37 vs -65.37 | ['08-29 16Z(8h)', '08-30 00Z', '08-30 04Z', '08-30 08Z', '08-30 12Z', '08-30 16Z'] ['08-29 16Z:next anchor row missing -> no 4h end mid; 8h extended window used']
20260831 | (08-30 20:42Z, 08-31 20:41Z] | 20921->20654 | 0 |   -267.0 | 6 |   -186.9 |   -54.3 |   -241.2 |   -25.7 |   +1.1 |   -19.9(08-31 20Z) |   +32.8(08-30 20Z) |   +25.9 |   -167.2 |   -157.8 | -43.35/-53.06 vs -53.06 | ['08-30 20Z', '08-31 00Z', '08-31 04Z', '08-31 08Z', '08-31 12Z', '08-31 16Z'] []
20260901 | (08-31 20:41Z, 09-01 20:41Z] | 20654->20317 | 0 |   -336.9 | 6 |   -304.8 |   -57.9 |   -362.6 |   +25.7 |   +2.2 |   +40.1(09-01 20Z) |   -19.9(08-31 20Z) |   -36.4 |    +36.7 |    -97.7 | -49.83/-56.36 vs -56.36 | ['08-31 20Z', '09-01 00Z', '09-01 04Z', '09-01 08Z', '09-01 12Z', '09-01 16Z'] []
20260902 | (09-01 20:41Z, 09-02 20:41Z] | 20317->21096 | 0 |   +778.1 | 5 |   +691.7 |   -38.5 |   +653.2 |  +124.9 |  +70.3 |  +146.0(09-02 20Z) |   +40.1(09-01 20Z) |   -51.3 |   +607.8 |   +297.8 | -30.36/-37.08 vs -46.83 | ['09-01 20Z(8h)', '09-02 04Z', '09-02 08Z', '09-02 12Z', '09-02 16Z'] ['09-01 20Z:next anchor row missing -> no 4h end mid; 8h extended window used']
20260903 | (09-02 20:41Z, 09-03 20:43Z] | 21096->83957 | 62998 |   -136.1 | 6 |   +131.2 |   -47.6 |    +83.6 |  -219.8 |  -44.6 |    -3.1(09-03 20Z) |  +146.0(09-02 20Z) |   -26.1 |   -566.3 |   -420.8 | -39.31/-47.24 vs -47.24 | ['09-02 20Z', '09-03 00Z', '09-03 04Z', '09-03 08Z', '09-03 12Z', '09-03 16Z'] []
20260904 | (09-03 20:43Z, 09-04 12:43Z] | 83957->82963 | 0 |   -994.0 | 4 |  -1110.9 |   -80.8 |  -1191.8 |  +197.7 |   +4.8 | nan(09-04 12Z) |    -3.1(09-03 20Z) |  +189.8 |  -1390.9 |   -981.1 | -55.78/-79.15 vs -79.15 | PARTIAL ['09-03 20Z', '09-04 00Z', '09-04 04Z', '09-04 08Z'] []
```

## Appendix C. Commands (verbatim)

```
cd /Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/gap_live_pnl
python3 dump_logs.py > dump_logs.out           # structural dump of anchors/readback/nav/fills/funding/target_live/regime_dash/beta_alpha
python3 I1_rerun_live_paper_vs_real.py > I1_rerun.out   # verbatim copy of I1, run from scratch (writes its npy here, not in the research repo)
python3 canon_reconcile.py > canon_run.log     # canonical device; writes canon_report.json
shasum -a 256 canon_reconcile.py canon_report.json canon_run.log /Users/haosiyu/wide_shadow/state/rolling.npz
```
