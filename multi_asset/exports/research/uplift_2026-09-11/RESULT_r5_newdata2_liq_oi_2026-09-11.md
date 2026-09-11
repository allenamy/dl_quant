> **创建:** 2026-09-11 | **Session:** b9646a9e (round-5 NEW DATA 2) | **状态:** CLOSED — 8 declared arms, ZERO admissions | **作废条件:** 面板文件更换 / 判官装置更换 / Binance 恢复发布历史强平数据

# RESULT — NEW DATA 2: liquidations and open-interest dynamics

Prereg: `PREREG_r5_newdata2_liq_oi_2026-09-11.md` (frozen, plus two amendments both written before any
alpha number: K 7→8 and the two data-hygiene guards). **K = 8, Bonferroni α = 0.00625.**
Everything below is EXPLORATORY in the contract sense: `ELIGIBILITY_CONTRACT.json` has an EMPTY
`approved_source_sha256` for `BUNDLE_export`, so no arm in this study can be a candidate.

## 0. GATES THAT RAN BEFORE ANY NUMBER
- **GATE P: PASS, bitwise, 8/8 arrays** (`d30_n2_c42_rec` and `d30_n2_c42_W`, seats dyn/fix × seeds
  42/2027), maxabs 0.0 against the archived `w10_ablation_series_V4_A0_*`.
  Device `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712…` (asserted in-code).
  Receipt `/workspace/uplift_2026-09-11/r5_oi/receipts/GATE_P.json`.
- **FULLCYCLE window VERIFIED, not assumed.** The archived A0 has 10039 anchors; 10039−900 = 9139,
  which is 121 more than the brief's 9018. Dropping 900 **and** capping at 2026-08-10 20Z gives
  n = 9018 and `A0_PWR230k_s42` then reads **Sharpe 1.4150** — the brief's number to 4 dp. Asserted in
  `judge.py`, so a wrong window fails loudly rather than quietly shifting every arm.
- **Injection path proven neutral.** `IB_PARITY` (fund slot = rank of the live fund score, i.e. a
  monotone no-op) is **bitwise identical** to `A0_PWR230k_s42` (`np.array_equal` True, maxabs 0.0).
  So any in-book difference below is the candidate, not the plumbing.
- **Env whitelist asserted per run** (a run using a variable outside it raises): `LEGS CAL WRULE LOOK
  MEMBERS_TOPN FTRIM PHI UMASK_SCOPE UMASK_NPZ SLOW_NPY FSEED FPRED COSTB_JSON OUT_TAG W3FIX
  FEMAT_NPZ OMP_NUM_THREADS OPENBLAS_NUM_THREADS MKL_NUM_THREADS`. Every value is written into each
  arm's `config_json`. (E-0826-D.)

## 1. DATA PROVENANCE — and the part that does not exist
**Historical liquidation data is NOT OBTAINABLE from Binance public sources. Verified, not assumed:**
- `data.binance.vision` has **no `liquidationSnapshot` prefix**. The complete listing is
  daily {aggTrades, bookDepth, bookTicker, indexPriceKlines, klines, markPriceKlines, metrics,
  premiumIndexKlines, trades} and monthly {aggTrades, bookTicker, fundingRate, indexPriceKlines,
  klines, markPriceKlines, premiumIndexKlines, trades}.
- `fapi/v1/allForceOrders` (the old public market-wide history endpoint) returns **404 — removed**.
- `fapi/v1/forceOrders` returns **401**: it is signed AND returns only the caller's own orders. Not
  the market, and credentials are forbidden here regardless.
- `!forceOrder@arr` is a real-time websocket with no history.
So the brief's item 1 — liquidation notional by side, liquidation count, liq-to-OI ratio — **cannot be
built on the v4 axis.** I did not substitute a proxy and call it liquidation data.

**Open interest IS obtainable, full span, and was pulled.**
`futures/um/daily/metrics/<SYM>/<SYM>-metrics-<date>.zip`, 5-minute rows.
- **526,784 files, 824 symbols, 150,883,030 five-minute rows, 3,486 genuinely-absent symbol-days,
  0 transport errors.** 404 (day absent) and transport error were counted separately throughout and
  the pull fails unless errors are zero — the `ma_v3_track2` download landmine.
- Coverage on the v4 panel: **99.75% of eligible (anchor, name) cells**, and flat by year —
  2022 99.57 / 2023 99.91 / 2024 99.73 / 2025 99.79 / 2026 99.71%. 5 of 829 symbols have no data and
  none of those 5 is ever eligible.
- Guards (declared in Amendment 2, before numbers) removed **197** cells for |Δlog OI over 4h| > log 3
  and **333** cells for OI notional < $50k.
- **Causality:** every column at anchor t uses only 5m rows with `create_time ≤ t − 300s`. The zero-lag
  variant `LIQDD_LAG0` was built as a leakage diagnostic and reads forward IC **0.01814 vs 0.01841** —
  essentially identical, so the embargo costs nothing and there is no timing-sensitivity flag.

### Two defects in MY OWN fetcher, found and repaired (recorded, not hidden)
1. **Column desync.** Older metrics files write a literal `""` for the two top-trader ratio columns.
   `float('""')` raises and `if p[4]` is True for `'""'`, so my empty-guard never fired; because the
   parse appended to five parallel lists one at a time, `t/oi/oiv` ran ahead of `ttlsr/tkvr` from that
   row on. **3,049 of 17,502 month-parts affected.** `t/oi/oiv` stayed mutually aligned (the failure is
   always at field 4), so the open-interest data itself was never scrambled — only the two
   *exploratory* ratio columns.
2. **Lossy repair.** My first repair made the row atomic, which is the right shape, but still let
   `float('""')` kill the whole row — so it would have dropped open interest for exactly the
   old-format days it was meant to fix. It rewrote 193 parts before I stopped it.
Final repair re-fetched all 3,070 affected parts with a parser where a ratio field that is `''`, `'""'`
or unparseable becomes NaN and **never** drops a row; only a bad time/OI/OI-notional drops one.
The merge then **hard-asserts** that all five columns are equal length in every part: 0 failures.

## 2. THE PARTIAL PRIOR, OPENED
`memory/ma_v3_track2_oi_positioning_closed.md` (closed 2026-07-13) tested a **140-coin v3-lineage**
panel, 7 OI/positioning channels, at the **1h horizon on the YR4 residual**, by **xsec rank-IC dIC
gates** (Ridge dIC +0.0007 fold-sign-inconsistent; LightGBM dIC −0.0004) **against the retired
32-channel Engine-A book**. It closes OI/positioning as incremental channels in that frame, and its own
"how to apply" line names other horizons and usages as untested and keeps the data asset for them.
What is genuinely new here: the 4h horizon on the v4 829-name lineage; the **book layer** rather than a
dIC gate; the current incumbent A0; and a **rectified event** construction that no track-2 channel
expressed. **The result below CONFIRMS the prior rather than overturning it** — `DOIxR`, the direct
rebuild of track-2's `doi_x_ret`, has forward IC −0.00957 and standalone Sharpe −1.45.

## 3. MECHANISM: WHAT I PREDICTED, AND WHAT HAPPENED
**Predicted before measuring (prereg §3):** REVERSION at the 4h horizon for the broad population,
because the cascade is over before the anchor samples it; CONTINUATION only inside the narrow
parabolic stratum of `parabolic_onset_continuation_lead_2026_09_06` (whose own receipt records the
*unconditional* intra-anchor continuation as a **rebound**, +18 bps — so the two are consistent).

**Event study, cross-sectionally demeaned forward 4h return, FULLCYCLE n=9018 anchors, 2,368,130 base
cells, UTC-day block bootstrap:** **every one of the 16 threshold cells has a CI95 containing zero**,
and the point-estimate sign flips with the threshold (REVERSION at OI-drop ≥1%, CONTINUATION at ≥3–5%).
The highest-power cell, OI-drop ≥1% with a down move, n = 494,629, reads **+0.46 bps [−0.17, +1.12]**.
So the 4h post-cascade drift is **bounded above by roughly 1.1 bps** — against a book cost of
~2.95 bps per unit turnover. The short-squeeze mirror (OI drop with price up) is +0.26 [−5.50, +6.43]
and +2.68 [−5.42, +11.10] — also zero.
**Parabolic stratum reconciliation:** n = 2,308, **−4.29 bps [−45.95, +36.80]** — the sign agrees with
the memory's continuation finding but the interval is so wide it settles nothing. Conditioning further
on actual deleveraging (OI drop ≥2%) gives −8.04 [−51.07, +36.16]; without it, +8.61 [−84.82, +104.98].
**Honest verdict on my own prediction: UNRESOLVED, not confirmed.** The gross book point estimates are
in the reversion direction, but no event-study cell excludes zero, so I am not entitled to claim the
direction was right.

## 4. FORWARD vs BACKWARD RANK-IC (k = −3..+3), FULLCYCLE n=9018
| score | fwd IC k=0 | t | bwd k=−1 | \|bwd/fwd\| |
|---|---|---|---|---|
| LIQDD (intra-anchor OI drawdown, signed) | **+0.01841** | **19.33** | −0.47189 | 25.6 |
| LIQDD_LAG0 (leak diagnostic) | +0.01814 | 19.08 | −0.46841 | 25.8 |
| LIQP4 | +0.01013 | 11.70 | −0.35826 | 35.4 |
| LIQP24 | +0.00870 | 9.73 | −0.09859 | 11.3 |
| OIV (OI notional / 24h volume) | **+0.02335** | 15.34 | +0.05155 | 2.2 |
| DOI4 | −0.00778 | −9.29 | +0.09795 | 12.6 |
| DOI24 | −0.00775 | −8.67 | +0.03379 | 4.4 |
| DOIxR (track-2's doi_x_ret) | −0.00957 | −11.18 | −0.00864 | 0.9 |
| LIQPC (parabolic-conditioned) | −0.00292 | −1.20 | −0.11032 | 37.8 (n=1259) |
| *exploratory* TTLSR (top-trader L/S) | +0.02313 | 16.75 | −0.04610 | 2.0 |
| *exploratory* TKVR | −0.00712 | −9.22 | +0.03226 | 4.5 |
| **CONTROL: the live fund leg** | **+0.00732** | 6.92 | +0.00527 | 0.7 |
The large backward IC on the LIQ* family is **not** a stale-echo defect — those features contain
`sign(ret_4h)` by construction, and `ret_4h` *is* the k=−1 return. Reported because the brief asks for
the profile, flagged so it is not read as the event/settlement-window failure signature.
**Three OI-derived channels have a forward rank-IC 2.5–3.2× the deployed fund leg's, all t > 15.**

## 5. THE HORIZON QUESTION (brief item 4) — priced honestly
| score | fwd 30m | fwd 1h | fwd 4h |
|---|---|---|---|
| LIQDD | 0.02315 | 0.02152 | 0.01897 |
| LIQP4 | 0.01561 | 0.01394 | 0.01124 |
| OIV | 0.01337 | 0.01575 | 0.02078 |
**The signal is NOT a 1h-only object.** LIQDD's IC at 30 minutes is only 22% above its 4h value — a
flat profile, not a decaying one. So the horizon mismatch is *not* the binding constraint here and
there is nothing to recover by going faster; the binding constraint is magnitude (§6–7). No cadence
proposal is made — that axis is closed at a 0.820 bps break-even against a 1.80 bps maker fee.
*Caveat:* this table's returns are rebuilt from the 5m lineage and correlate 0.962 with the meta `y4`,
so it is a shape reading, not a primary number; the §4 table uses the meta `y4` directly.

## 6. STANDALONE BOOKS — bar was Sharpe ≥ 1.5 at |rho| ≤ 0.25
FULLCYCLE post-warm n = 9018, SE(Sharpe) = 0.4928, fitted cost `costb_PWR_G230k.json` (K=0.17).
| arm | Sharpe | rho A0 | pnl_ex | carry | cost | **net g** | turnover | yrs+ |
|---|---|---|---|---|---|---|---|---|
| A0 (deployed) | **1.4150** | 1.00 | 1.3266 | 0.4694 | 0.1682 | **0.6890** | 0.03037 | 4/5 |
| SA_OIV | 0.4698 | 0.293 | +0.5051 | +0.1776 | 0.0523 | +0.2753 | 0.01254 | 3/5 |
| SA_LIQPC | 0.4464 | 0.099 | +1.3061 | −1.8072 | 2.0396 | +1.0737 | 0.06331 | 2/5 |
| SA_LIQP24 | −0.9142 | −0.069 | +0.3626 | +0.0194 | 0.7511 | −0.4079 | 0.07912 | 1/5 |
| SA_DOIxR | −1.4455 | 0.010 | +0.0568 | −0.1832 | 1.0422 | −0.8022 | 0.08836 | 1/5 |
| SA_DOI24 | −1.7623 | 0.059 | −0.4773 | −0.1815 | 0.5333 | −0.8292 | 0.07476 | 1/5 |
| SA_LIQP4 | −2.0234 | −0.038 | +0.4033 | +0.0192 | 1.2425 | −0.8584 | 0.08827 | 0/5 |
| SA_LIQDD | −2.1511 | −0.067 | **+0.4462** | +0.1724 | **1.3039** | −1.0301 | **0.09021** | 0/5 |
| SA_DOI4 | −2.5534 | 0.061 | −0.2637 | −0.0920 | 1.1601 | −1.3318 | 0.08892 | 1/5 |
**Nothing reaches 1.5.** Read the decomposition, not the Sharpe: the *rectified event* features
(LIQDD, LIQP4, LIQP24) have **positive gross** pnl, while the *state* features (DOI4, DOI24) have
**negative gross** — the mechanism discriminates exactly where it predicted it would. But LIQDD
turns over **0.0902 vs A0's 0.0304 (2.97×)** and pays 1.3039 bps of cost against 0.4462 bps of gross
alpha. It captures about **one third** of what it would need to pay for itself.
`SA_LIQPC` is a carry trade wearing an event's clothes: its net is +1.07 bps of which **168% is
funding carry** (carry −1.8072) — it fails the carry gate outright.

## 7. TURNOVER-MATCHED NULLS — the result that actually decides it
Nulls built with `r3_attack_b9646/null.py` (sha 91d4c91cb92a6440) semantics: RELAB = one fixed symbol
permutation at every anchor; SHIFT = the score matrix advanced k anchors. Both preserve the per-anchor
rank distribution and the lag-1 persistence, hence the turnover — **measured ratios 0.97–1.22×**, versus
the 2.6–7.7× of the defective per-anchor placebo. Both `pnl_ex` (gross) and `g` (net) reported.

**LIQDD**: arm gross **+0.4462, CI95 [−0.0475, +0.9396]** — *its own interval contains zero*.
Against its 6 nulls it wins on gross in only **2 of 6** (RELAB1 +0.798 [+0.066,+1.531]; SHIFT101
+0.697 [+0.113,+1.277]); the other four contain zero, and RELAB2 alone earns +0.2250 gross — half the
arm. Null mean +0.0201, null SD 0.2511 ⇒ the arm sits **1.7 null-SDs** above the null mean.
**BEATS ALL NULLS: NO**, on gross and on net.

**OIV** (the arm that came closest): arm gross +0.5051 [−0.0612, +1.0823], net g +0.2753
[−0.2699, +0.8453] — both contain zero. And the kill is unambiguous: **SHIFT101 earns +0.5244 gross,
MORE than the arm itself** (d −0.0189, P>0 = 0.464), and +0.4221 net against the arm's +0.2753.
A 101-anchor (17-day) time shift of the OI-to-volume score earns what the real score earns, which is
the definition of a **static cross-sectional characteristic, not time-varying information**.
**BEATS ALL NULLS: NO** (1 of 6 on gross).

**LIQP4**: arm gross +0.4033 [−0.0313, +0.8297]; beats 1 of 6; 1.95 null-SDs. **NO.**

## 8. TAIL CONCENTRATION — the one gate the event family passes cleanly
`r3_gates/rs_conc.py` (sha 3fd2f76496a593ba), FULLCYCLE post-warm.
| leg | leg ret bps | top-20 share | ex-top-20 bps | ex-top-20 Sharpe |
|---|---|---|---|---|
| LIQDD | 0.6597 | **−0.848** | +1.2193 | **+5.353** |
| LIQP4 | 0.6395 | −0.263 | +0.8078 | +2.947 |
| OIV | 0.2437 | −5.628 | +1.6151 | +5.670 |
| LIQPC | −3.9228 | +0.519 | −1.8878 | −1.245 |
| CONTROL live fund | 1.1059 | +0.079 | +1.0190 | +3.580 |
**Instrument validation:** the brief quotes the live fund-leg control as **11.09% / +6.71**. My
independent rebuild reads that control on the 2025-on subwindow as **top-20 share 0.1109 and ex-top-20
Sharpe 6.709** — an exact reproduction of both figures, which pins down both the ruler and the window
the brief's control was measured on.

LIQDD's gross leg return is **broad-based, not tail-driven** — a *negative* top-20 share means the
twenty largest contributors lose money and the rest of the book earns more than the total, the exact
opposite of RESID_SHARPE's 130–189% / −2.40 death. This gate would have passed. It is the book's
cost, not its concentration, that kills it. (The share ratios for OIV and for the 2025-on subwindows
are unstable because their denominators are near zero — do not read those magnitudes.)

## 9. IN-BOOK (fund slot = 0.75·rank(live fund) + 0.25·rank(candidate)), dg vs A0, CI95
| arm | Sharpe | dg bps | dg CI95 | dg CI Bonferroni K=8 | dSharpe CI95 |
|---|---|---|---|---|---|
| IB_OIV | 1.4947 | +0.0620 | [−0.11249, +0.23566] | [−0.18882, +0.30659] | +0.0797 [−0.270, +0.425] |
| IB_LIQP24 | 1.4183 | −0.0200 | [−0.10750, +0.06324] | [−0.14069, +0.10760] | +0.0032 [−0.168, +0.179] |
| IB_LIQPC | 1.4128 | −0.0007 | [−0.02306, +0.01992] | [−0.03142, +0.02811] | — |
| IB_LIQP4 | 1.4038 | −0.0313 | [−0.12981, +0.06539] | [−0.16963, +0.10209] | — |
| IB_LIQDD | 1.3905 | −0.0389 | [−0.13343, +0.05514] | [−0.16904, +0.08901] | — |
| IB_DOI4 | 1.3857 | −0.0257 | [−0.13581, +0.08553] | [−0.17186, +0.13559] | — |
| IB_DOI24 | 1.3487 | −0.0379 | [−0.16236, +0.08868] | [−0.20198, +0.13246] | — |
| IB_DOIxR | 1.3233 | −0.0626 | [−0.18784, +0.06007] | [−0.21412, +0.12041] | — |
| IB_PARITY | 1.4150 | 0.0 | [0.0, 0.0] | — | bitwise == A0 |
**All eight contain zero at CI95, before any Bonferroni correction.** Seven of eight point estimates
are negative. Compare the standard this must beat: the round-4 Amihud sleeve at a=0.20 had four CI95
lower bounds of +0.0336/+0.0319/+0.0315/+0.0305, all above zero.

## 10. VERDICT
**ZERO ADMISSIONS from 8 declared arms.** Nothing reaches Sharpe 1.5, nothing clears |rho| ≤ 0.25 with
a positive book, nothing beats its turnover-matched nulls, and every in-book delta contains zero.

**What was actually learned, which is not nothing:**
1. **The liquidation half of the brief is not answerable with the data that exists.** Binance withdrew
   market-wide forced-order history from both the archive and the REST API. Any future liquidation work
   needs either a paid third-party aggregator or a forward-only capture of `!forceOrder@arr` starting
   now. **A zero-touch forward capture is the only cheap option and it costs nothing to start.**
2. **The closed track-2 axis is confirmed, on a new lineage, at a new horizon, at the book layer.**
   `doi_x_ret` rebuilt on the v4 4h axis reads forward IC −0.0096 and standalone Sharpe −1.45.
3. **The sixth case of "ranking ≠ net", and the sharpest one yet.** LIQDD's forward rank-IC is
   **+0.01841 at t = 19.33 — 2.5× the deployed fund leg's +0.00732** — and its leg return is
   broad-based (ex-top-20 Sharpe +5.35). It still produces a book that is 1.7 null-SDs from a
   turnover-matched null and −2.15 Sharpe net. A t = 19 score layer bought nothing at the book layer.
4. **The mechanism of that gap is a shape mismatch, and it is measurable.** LIQDD's IC collapses from
   +0.0184 at k=0 to +0.0064 at k=+1 and +0.0020 at k=+2 — a one-anchor event. The book advances
   positions by `H + 0.1·(tgt − H)` with a 2.5e-4 trade band, i.e. a position half-life of roughly
   seven anchors. A one-bar signal pays the full round trip and collects a fraction of the intended
   exposure. This is an INFERRED mechanism, consistent with the measured 2.97× turnover and the
   1.3039 bps cost, but I did not build a no-EMA counterfactual to prove it.
5. **The honest ceiling on the mechanism itself**: the post-cascade 4h cross-sectional drift is bounded
   at roughly **1.1 bps** (the tightest event cell, n = 494,629, +0.46 [−0.17, +1.12]) against a
   ~2.95 bps per-unit-turnover cost. Even a perfect one-name-per-anchor expression of it does not pay.

**What I would NOT do next:** re-transform these columns. That is the pattern four rounds have already
falsified, and the null result here is not a near miss that a better transform rescues — the arm is
inside its own null band on gross.

## 11. ARTIFACTS
- pod2 `/workspace/uplift_2026-09-11/r5_oi/` — `receipts/{GATE_P,coverage,ic_probe,event_study,judge,concentration,nulls}.json`,
  `sig/oi_feats.npz` (11 columns × 10039 × 829), `raw/*.npz` (824 symbols of 5m OI), `out/*.npz` (31 arm books),
  `manifest_fetch.json`, and the scripts `fetch2.py repair.py merge3.py build_feats.py arms.py nulls.py
  nulljudge.py conc.py event.py ic_probe.py judge.py gateP_r5.py`.
- local (branch `research/book-uplift-2026-09-11`, NOT committed)
  `multi_asset/exports/research/uplift_2026-09-11/{PREREG,RESULT}_r5_newdata2_liq_oi_2026-09-11.md`.
- Nothing was written to `~/dl_quant_live` or `~/wide_shadow`; no signed endpoint; no order; no process
  touched. All venue traffic was the public bulk archive, none inside an anchor window
  (archive pulls ran 13:52–14:38Z and 14:50–14:58Z by log mtime; anchor windows are HH:00–HH:57 of
  00/04/08/12/16/20Z, so no request fell inside one).
