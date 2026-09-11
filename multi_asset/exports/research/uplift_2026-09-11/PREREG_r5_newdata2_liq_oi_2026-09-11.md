> **创建:** 2026-09-11 | **Session:** b9646a9e (round-5 NEW DATA 2) | **状态:** FROZEN before any alpha number | **作废条件:** 口径换面板文件 / GATE P 不过 / 数据来源改变

# PREREG — NEW DATA 2: liquidations and open-interest dynamics

## 0. Caliber (pinned by the round-5 brief, restated for the record)
- Panel `/workspace/data/wide_panel_4h_v2ext.npz` (ts 10039, symbols 829), meta
  `/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz` (E_ts 10182),
  king `SLOW_v3_on_v4axis.npy`, preds `f10_A0_s{42,2027}.npy`.
- Device `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 b88e35a46b93d712… (verified this session).
- ENV WHITELIST, asserted and recorded in every artifact:
  `CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 UMASK_NPZ=<UPIT_CRYPTO>
   COSTB_JSON=<see below> SLOW_NPY=<SLOW_v3_on_v4axis> LEGS PHI FSEED FPRED FTRIM FEMAT_NPZ OUT_TAG
   OMP_NUM_THREADS OPENBLAS_NUM_THREADS MKL_NUM_THREADS`
  GATE P runs at `COSTB_JSON=health_check/calib/costb_fee_steady.json` (that is what the ARCHIVED A0 was
  built with — bitwise parity is against that file). All ARM readings are at the FITTED cost
  `r3k/costb_PWR_G230k.json` (sha 295b4e7b462373e4, K=0.17).
- Readings: FULLCYCLE post-warm drops the first 900 device anchors (E-0911-A), n=9018, SE(Sharpe)=0.4928.
  Statistic g = net_ex/gross_total, paired, UTC-day block bootstrap 2000, rng default_rng([20260905,k]).
- RANK via scipy.stats.rankdata. No `_ext` cache, no expm1 on the pod 5m lineage, no clipped compounding.

## 1. Data provenance — declared BEFORE building anything
**Liquidations: NOT ACQUIRABLE for history.** Verified this session:
`data.binance.vision` has NO `liquidationSnapshot` prefix under either `futures/um/daily/` or
`futures/um/monthly/` (the complete prefix lists are aggTrades, bookDepth, bookTicker,
indexPriceKlines, klines, markPriceKlines, metrics, premiumIndexKlines, trades / and monthly
aggTrades, bookTicker, fundingRate, indexPriceKlines, klines, markPriceKlines, premiumIndexKlines,
trades). The REST historical endpoint `fapi/v1/allForceOrders` returns **404 (removed)**;
`fapi/v1/forceOrders` returns **401 = signed, and is the caller's OWN orders, not the market**, and
credentials are forbidden here anyway. The `!forceOrder@arr` websocket is real-time only and carries
no history. Therefore **the brief's item 1 "liquidation notional by side / liquidation count /
liq-notional-to-OI ratio" cannot be built on the v4 axis from any permitted source.** I will say so
plainly rather than substitute a proxy and call it liquidation data.
**Open interest: ACQUIRABLE, full span.** `futures/um/daily/metrics/<SYM>/<SYM>-metrics-<date>.zip`,
5-minute rows, columns `create_time, symbol, sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, count_long_short_ratio,
sum_taker_long_short_vol_ratio`. Verified present from at least 2021-06 through 2026-09.
**Liquidation PROXY** (labelled as a proxy everywhere, never as liquidation data): a forced
deleveraging event is the only observable footprint left — open interest FALLING while price moves
AGAINST the side that was crowded. That is constructible from OI + returns and is exactly what a
cascade leaves behind in the data that does survive.

### Causal availability at anchor time
Every column for anchor `t` uses only 5m metric rows with `create_time <= t - 300s` (a 5-minute
embargo, the same lag convention the closed track-2 build used). A `t - 0s` variant is built ONLY as
a leakage diagnostic: if the zero-lag variant is materially stronger, that is a timing-sensitivity
flag against the feature, not a licence to use it.

## 2. The partial prior, opened and read
`memory/ma_v3_track2_oi_positioning_closed.md` (closed 2026-07-13). What it actually tested:
a 140-coin **v3-lineage** panel, 7 channels (oi_level_norm, d_oi_1h, d_oi_24h, doi_x_ret,
top_ls_ratio_z, top_vs_global_divergence, taker_ratio_ema), at the **1h horizon on the YR4 residual**,
judged by **xsec rank-IC dIC gates** (Ridge dIC +0.0007 fold-sign-inconsistent; LightGBM dIC −0.0004)
**against the retired 32-channel Engine-A factor book**.
What that closes: OI/positioning as *incremental linear or GBDT channels at 1h/YR4 over Engine A*.
Its own "how to apply" line names the untested usages and keeps the data asset for them.
What it does NOT close, and why this round is adjacent rather than a re-run:
 (a) the **4h** horizon on the **v4 829-name** lineage;
 (b) the **book layer** — the project has five receipted cases of "ranking ≠ net"; a dIC gate is the
     score layer and cannot decide a net-of-cost book contribution either way;
 (c) the **incumbent** — the comparison book is now A0 (funding momentum + king + V2MAIN), not Engine A;
 (d) the **event construction** — `doi_x_ret` is a smooth product; a cascade proxy is a *rectified,
     one-sided* event feature (OI drop AND adverse move), which no track-2 channel expressed.
**Honest counterweight:** (a)–(c) are the weakest kind of reopening argument (same data, new frame) and
the project has burned four rounds on exactly that pattern. (d) is the only genuinely new construction.
I will report the state channels and the event channel separately so the prior's scope stays legible,
and I will not claim the prior was wrong if the state channels fail again — that would be its
confirmation, not its refutation.

## 3. MECHANISM AND DIRECTION — PREDICTED BEFORE MEASURING
A forced liquidation is a price-insensitive market order fired by the exchange's risk engine. Two
opposite effects, separated by timescale:
 (i) **while the cascade runs (seconds–minutes):** continuation. Each forced sale pushes price further
     against the crowded side and trips the next maintenance-margin band.
 (ii) **after it exhausts (hours):** reversion. The flow carried no information, so the liquidity
     providers who absorbed it are paid back as price recovers.
**Prediction, declared now:** at the 4h anchor the cascade is over before the book can act — the
anchor samples the *post-exhaustion* state. So the broad population effect I predict is **REVERSION**:
names that just deleveraged hard against themselves (OI down, price down) should **outperform** over
the next 4h, and the score is signed so that positive = "was force-sold, expect bounce".
**The project's surviving counter-clue, read and reconciled:**
`memory/parabolic_onset_continuation_lead_2026_09_06.md` found **continuation** (−64 bps to the next
anchor) — but only inside a narrow post-hoc stratum (long extreme-funding names with a 3-day gain
≥ +20% that then fall ≤ −8% intra-anchor; 28% of onsets, ≈0.5 events/anchor). That same receipt
records the **unconditional** intra-anchor continuation as a **rebound of +18 bps to the next anchor**.
So the two predictions are not in conflict: **population = reversion, continuation lives in a narrow
conditioned tail.** That is precisely my prediction, and it makes the conditional arm (G below) a
directional test rather than a fishing expedition: if the conditional arm reads continuation while the
broad arm reads reversion, the mechanism story survives; if the broad arm reads continuation, my
mechanism is wrong and I say so.

## 4. ARMS and K — declared before any number
Each arm is one score matrix injected as `FEMAT_NPZ` (replaces the fund-leg score), evaluated
(a) STANDALONE `LEGS=001 PHI=0` and (b) IN-BOOK as a rank blend into A0's fund slot at a=0.25
(`0.75*rank(fund) + 0.25*rank(score)`, the `inbook.py` construction, arm IB_AM25's shape).
STATE channels (what track-2 tested, rebuilt on the v4 4h axis — expected to fail, run for scope):
 A. `DOI4`  = Δlog OI over 4h
 B. `DOI24` = Δlog OI over 24h
 C. `OIV`   = log(OI notional / 24h quote volume)   [crowding state]
 D. `DOIxR` = ΔlogOI_4h × ret_4h                     [track-2's doi_x_ret, on the new axis]
EVENT channels (new construction, the actual hypothesis):
 E. `LIQP4`  = −sign(ret_4h) · max(0, −ΔlogOI_4h)     [rectified cascade proxy, 4h]
 F. `LIQP24` = −sign(ret_24h) · max(0, −ΔlogOI_24h)   [same, 24h]
 G. `LIQPC`  = E restricted to the parabolic-onset stratum (3-day gain ≥ +20% ∧ ret_4h ≤ −8%),
               zero elsewhere                          [the memory-linked conditional]
**K = 7.** Bonferroni α = 0.05/7 = 0.00714 two-sided ⇒ a corrected claim needs the **99.29%** interval
to exclude zero. I will report CI95 (comparable to rounds 3–4) AND state the Bonferroni requirement.
Seats: dynamic is primary, fixed (`W3FIX=0.21,0,0.79`) is the robustness read; seats are not extra K.
Seeds 42 and 2027 are a stability read, not extra K.

## 5. BAR (frozen)
**ADMIT** requires ALL of: standalone full-cycle post-warm Sharpe ≥ 1.5; |rho| to A0 ≤ 0.25;
carry fraction of net < 50%; beats ALL SIX turnover-matched nulls (SHIFT101/503/1009, RELAB1/2/3) on
both pnl_ex and g; top-20 share ≤ the live fund-leg control (11.09%) × 3 AND ex-top-20 Sharpe > 0;
per-year net sign positive in ≥ 4 of 5 years; in-book Δg CI95 lower bound > 0 (and > 0 at the
Bonferroni interval for a corrected claim).
**NEAR_MISS** = standalone bar met but in-book CI95 contains zero. **REJECTED** otherwise.

## 6. GATE ORDER (frozen, run in this order, numbers not looked at out of order)
P → provenance/causality assertions → forward-vs-backward rank-IC k=−3..+3 → standalone book
(Sharpe, per-year, rho) → carry fraction → turnover-matched nulls → tail concentration →
in-book Δg → horizon profile (is it a 4h object or a 1h object?).

## 7. The horizon problem, priced honestly in advance
Round 2 receipted the 1h clock at a break-even of 0.820 bps against a 1.80 bps maker fee — the cadence
axis is CLOSED. So if a liquidation-proxy signal only lives at 1h, the correct output is **"real but
not usable by this book"**, priced at that break-even, NOT a cadence proposal. I will measure the IC
at the 1h and 4h horizons on the same score and report the decay, and I will not convert a 1h finding
into a 4h claim by any weighting, smoothing or holding trick.

---
## AMENDMENT 1 — written BEFORE any alpha number, after GATE P and before the feature build
**(a) One arm added, K raised 7 -> 8.** The mechanism in §3 is a *cascade*, and a cascade that blows
out and refills inside one 4h anchor is INVISIBLE to an endpoint difference of open interest. The
archive gives 5-minute OI, so the mechanically correct event feature is the deepest intra-window OI
drawdown, not the endpoint change. Adding it:
 H. `LIQDD` = −sign(ret_4h) · max(0, −min_s log(OI_s / OI_first)) over the 5m rows in
    (t − 4h, t − 300s]. Positive = "open interest collapsed intra-window while price fell" = the
    strongest available footprint of forced selling.
**K = 8.** Bonferroni α = 0.05/8 = 0.00625 two-sided ⇒ a corrected claim needs the **99.375%**
interval to exclude zero. This amendment makes the correction STRICTER, not looser, and is made with
zero alpha numbers in hand (only GATE P, which is a parity check).
**(b) ΔlogOI is computed on `sum_open_interest` (position units), never on
`sum_open_interest_value`** — the notional moves with price, so Δlog(notional) would be part return
by construction and would manufacture a spurious return interaction. Recorded here so the choice
cannot be re-made after seeing numbers.
**(c) FULLCYCLE window, reconciled to the brief's n=9018.** GATE P shows the archived A0 has 10039
anchors; 10039 − 900 = 9139, which is 121 more than the brief's 9018. 121 anchors is exactly
2026-08-10 20Z → 2026-08-31 00Z. So FULLCYCLE = device anchors [900:] **AND** ts ≤ 2026-08-10 20Z.
I assert n == 9018 in code rather than trusting the arithmetic.

## AMENDMENT 2 — data-hygiene guards, declared BEFORE any alpha number
Open interest is reported in POSITION UNITS, so a contract-multiplier change, a ticker migration
(the 1000X family) or a relisting produces a step in `sum_open_interest` that is an accounting
artifact, not a market event — and a rectified feature like `max(0, −ΔlogOI)` would read the artifact
as the largest liquidation in the sample. Two guards, both fixed now, neither tuned on any result:
 - **G1:** a cell with |Δlog OI over 4h| > log(3) is set to NaN. A 3× change in open interest inside
   one 4-hour bar is an accounting event, not a cascade.
 - **G2:** a cell whose open-interest NOTIONAL at the anchor is < $50,000 is set to NaN. Below that,
   log(OI) is dominated by rounding in the reported units.
Both guards are applied identically to every arm including the state channels, so they cannot favour
the event family. The count of cells removed by each is reported in the coverage receipt.
Note the rank transform already limits the damage a surviving artifact can do (the device ranks, then
caps each name at 2.5/nsel of gross), and the tail-concentration ruler is in the battery precisely to
catch what the guards miss.
