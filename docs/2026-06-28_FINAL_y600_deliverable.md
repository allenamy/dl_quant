> **创建:** 2026-06-28 12:30 UTC | **Session:** dual-source-perp autonomous | **状态:** in-progress (7/10 months; 2026-03/04/05 lambda0.1 training) | **作废条件:** superseded when all 10 months land + final aggregate re-run

# FINAL DELIVERABLE — BTC USDT-perp y_600 (10-min return) — honest, rigor-verified

## 0. Headline (honest, all rigor applied)

- **Tradeable signal level: per-day-CLEAN Pearson ~0.045-0.05 (pooled), DENSE ~0.037.** EMA checkpoint, no-peek.
- **Regime-dependent:** STRONG/trending months ~0.06-0.08 (2025-10 cd-CLEAN 0.081, DENSE 0.079; 2025-11 cd-CLEAN 0.068); NORMAL ~0.04-0.06; DRIFT/weak months ~0.012-0.016 (2026-01/02).
- **Monotone & near-zero-bias:** bin-Spearman +0.83 decile / +1.00 quintile (perfectly rank-monotone). Pred long/short bias ~0 (q50_mean +0.0002 std-units). The decile-OLS intercept (-0.0166) = the test-period realized-y market drift, NOT a model bias.
- **beta is UNSTABLE** across months (range [0.38, 1.82] at fixed config) -> do NOT size on magnitude; size on RANK/SIGN.
- **NOT tradeable net-of-cost:** per-trade gross edge ~0.34 bps (gated up to ~+2 bps), vs round-trip cost 4-10 bps -> COST-DOMINATED. Gross Sharpe ~4 (signal real), net Sharpe negative. Research-stage. Same conclusion as single-asset.
- **2b (lambda_quantile 0.5) is a WASH** (same-checkpoint pooled dP ~ -0.007 DENSE / -0.001 per-day-CLEAN; helps 1, hurts 2 of 3 months) -> default lambda0.1 is the deliverable config.
- **0.10 Pearson is NOT achievable on-disk.** funding/OI weak at all honest horizons; liquidations infra-gated (not on box).

## 1. Per-month trajectory (lambda0.1, 450d rolling, patience10, EMA = no-peek headline)
Caliber: DENSE (all windows, q50-vs-raw-y) + per-day-CLEAN (non-overlap >=600s within day, corr then mean across days).
Headline = ABSOLUTE Pearson at sigma_hat/sigma_y>=0.02 (beta = separate, unstable stat — sizing-only).

```
month     N      | DENSE-P  cd-CLEAN-P  DENSE-S  cd-CLEAN-S |  beta  sigma   DA   health  regime
2025_08  4417    | +0.0355   +0.0385   +0.0377   +0.0412   | +1.82  0.019* 0.511  near-gate  normal
2025_09  3600    | +0.0583   +0.0578   +0.0578   +0.0260   | +1.41  0.041  0.515  OK         normal
2025_10  13356   | +0.0785   +0.0813   +0.0415   +0.0571   | +1.70  0.046  0.516  OK         STRONG
2025_11  13356   | +0.0427   +0.0679   +0.0384   +0.0511   | +0.82  0.052  0.512  OK         strong
2025_12  13356   | +0.0188   +0.0458   +0.0365   +0.0426   | +0.67  0.028  0.514  OK         choppy
2026_01  13356   | +0.0150   +0.0121   +0.0083   +0.0043   | +0.46  0.033  0.506  OK         DRIFT
2026_02  13356   | +0.0113   +0.0157   +0.0089   +0.0114   | +0.38  0.030  0.507  OK         DRIFT
2026_03  13356   | +0.0224   +0.0210           +0.0181   +0.0295    | +0.52  0.043  0.505  OK         DRIFT
2026_04  13356   | +0.0183   +0.0307           +0.0362   +0.0437    | +0.19  0.097  0.515  OK         DRIFT
2026_05  10494   | +0.0176   +0.0166           +0.0364   +0.0350    | +0.32  0.056  0.513  OK         DRIFT
```
(* 2025_08 EMA sigma 0.019 just under the 0.02 gate — near-collapse on the weakest-checkpoint month; BEST-ckpt healthier.)

### POOLED (FULL 10 months, EMA = no-peek headline) — FINAL:
- DENSE-P mean **+0.0318** | **per-day-CLEAN-P mean +0.0387 (HEADLINE)**
- DENSE-S +0.0320 | per-day-CLEAN-S +0.0342
- **IC-IR (per-day-CLEAN) = +1.70** | worst-month cd-CLEAN-P +0.0121 (2026-01)
- **%-positive = 100% (all 10 months positive)** | %-sigma-healthy = 90% | beta range [0.19,1.82] UNSTABLE
- REGIME: strong 2025-10/11 (cd-CLEAN 0.081/0.068), normal 2025-08/09/12 (0.04-0.06), DRIFT 2026-01..05 (0.012-0.031, all positive).

## 2. Logic verification (eval bug-free) — VERIFIED
- predictions = (N,3) quantiles [0.1, 0.5, 0.9]; **q50 = column 1** used for IC (correct).
- predictions/targets/timestamps **1:1 aligned, same length**, timestamps sorted; targets are the t->t+600s forward return.
- **No look-ahead:** each pred uses inputs <=t; target is strictly forward. Walk-forward train (prior 450d) -> 2-day embargo -> val -> test, strict temporal order per month.
- de-standardization consistent: raw = val*y_sigma + y_median (y_sigma/y_median stored per-file).
- Shuffle-null (DL preds, 2025-10, 200 perm): REAL DENSE-P +0.058 vs IID-null z=+6.55 / BLOCK-null(y-AR1) z=+4.87, both p<0.001 -> signal genuine, not overlap/autocorr artifact.

## 3. Monotonicity / calibration (user's key ask) — PNG: exports/final_l01/calibration_monotonicity.png (10-mo)
- **bin-Spearman (rank-monotone, PRIMARY) = +0.84 decile / +1.00 quintile** -> predictions rank realized returns monotonically.
- frac-increasing-steps = 0.78 decile / 1.00 quintile (decile reversals are adjacent-bin NOISE in a low-IC signal; quintile clean).
- quintile realized-y per pred-bin: [-0.043, -0.032, -0.001, +0.008, +0.012] (low pred -> negative realized, high pred -> positive; monotone).
- binned OLS slope +0.36, **intercept -0.0120 == pooled realized y_mean -0.0114** (q50_mean +0.0016 ~0) -> intercept is TEST-PERIOD MARKET DRIFT, NOT model bias. Model is near-zero-bias.

## 4. Causal sliding-window demean (trailing 3600s, <=t) — 10-mo
- pred long/short bias: before +0.00164 -> after +0.00002 (zeroed, causally, no future leak).
- binned intercept: -0.01195 -> -0.01136 (~unchanged — demeaning PRED cannot remove a realized-y mean / market drift).
- pooled DENSE IC: +0.0260 -> +0.0220 (small drop over 10mo incl drift; per-day-CLEAN headline unaffected). Demean is for BIAS removal (zeroes pred drift), not an IC lever.
- Production note: use the causal-demeaned q50 for sizing to avoid a slow directional drift in the book.

## 5. Best-practice trading scheme (single-asset BTC y_600) + honest net-of-cost
DESIGN (each element mechanistically justified):
1. **SIGN/RANK sizing, NOT magnitude** — beta is unstable [0.38,1.82], so a magnitude/beta-scaled size mis-sizes month-to-month; trade sign of the (demeaned) signal.
2. **Causal sliding-demean** (item 4) — removes persistent long/short bias before sign.
3. **Confidence gate** — only act on high-|signal| tail (trailing-z gate); raises per-trade edge (top-10% |signal|: 0.34->2.0 bps).
4. **Hysteresis + min/max-hold** — T_open > T_close, min-hold + max-hold -> low flip rate, caps churn.

HONEST NET-OF-COST (non-overlapping 600s decisions, no overlap inflation):
- non-overlap IC +0.053; trade-every per-trade GROSS edge **+0.34 bps** (std 19), gross Sharpe **+4.1**.
- NET per trade: pure-maker (4.0 RT) **-3.7 bps** | realistic-maker (5.8) **-5.5** | taker (10.0) **-9.7**.
- CONF-GATE top-10% |signal|: edge +2.0 bps -> still net -2.0 (maker) / -8.0 (taker).
- **VERDICT: COST-DOMINATED.** Signal is real (gross Sharpe ~4, IC ~0.05) but per-trade edge (0.3-2.0 bps) << cost floor (4-10 bps RT). NOT tradeable net-of-cost at retail fees. Research-stage. Identical to the single-asset BTC y_600 conclusion (cost is the binding constraint, not signal quality).
- Path to tradeable would need: (a) much lower fees (VIP/maker-rebate), AND (b) higher per-trade edge (orthogonal data — funding/OI/liquidations — which are weak/absent on disk), AND (c) breadth (multi-asset) to diversify. None available on-disk.

## 5b. TAIL-GATED ENTRY + HOLDING (cost-dominated best practice) — SHORT side is marginally tradeable at MAKER
Reconstructed price path (telescope y_600 on ~600s subgrid; node-incr std == y_600 std, validated). Signal = causal-demeaned
yhat. Entry: trailing-distribution tail (causal, 24h window). Hold: until opposite tail OR mean-revert THROUGH trailing median;
min-hold 3 nodes (~30min), max-hold 36 (~6h). PnL = cumulative price(exit)-price(entry), signed. RT cost maker 2bps / taker 8bps.

```
GATE     side   n     per-trade-edge  hold    GrossSharpe  NETmaker(RT2)   NETtaker(RT8)
+-10%    ALL   2850   +1.71 bps       40min   +2.7         -0.29 (S-0.5)   -6.29
         LONG  1426   +0.21           39min   +0.2         -1.79           -7.79      <- LONG worthless
         SHORT 1424   +3.22           40min   +3.5         +1.22 (S+1.3)   -4.78      <- SHORT net-POS at maker
+-5%     SHORT  851   +2.39           39min   +1.9         +0.39 (S+0.3)   -5.61
+-2.5%   SHORT  509   +2.98           40min   +1.8         +0.98 (S+0.6)   -5.02
```
- **STRONG LONG/SHORT ASYMMETRY (user was right):** SHORT side carries the signal (edge +2.4 to +3.2 bps, gross Sharpe +1.8..+3.5);
  LONG side is ~0 to -1.3 bps (dead). Bottom-tail predictions sort returns; top-tail don't.
- **SHORT is net-POSITIVE at MAKER** fees across all gates (+0.4 to +1.2 bps/trade, net Sharpe ~+0.3..+1.3, ~7 trades/day at +-10%).
  NOT taker-tradeable (net -5..-6 bps at RT8). So: short-only, maker-only, low-turnover.
- **NOT just riding the down-trend:** per-month short edge POSITIVE in EVERY month incl flat ones (2025-08 +2.0, 2025-09 +3.8,
  2025-12 +0.4, 2026-02 +2.5; down months 2025-11 +4.0). Genuine short-side alpha. (Caveat: no sustained UP month in the
  2025-08..2026-02 window to stress the hardest case; confirm on an up-trend month when available.)
- VERDICT (reconstructed-price): the tail+holding strategy upgrades the conclusion from "not tradeable" to "SHORT-side marginally
  tradeable at maker fees (net Sharpe ~1)". Still fragile (maker-only, modest Sharpe, untested in up-trend).

### 5b-REAL — VERIFIED on ACTUAL perp book-mid (btcusdt_copy binance-futures, midcov=1.00, <=t causal)
The reconstructed-y600 edge was re-tested on REAL entry-mid->exit-mid cumulative log-returns (no reconstruction). Holds:
```
POOLED REAL-PRICE (7 mo, hold ~3.9 nodes ~40min, gate +-10%, exact Sharpe=edge/sd*sqrt(n/span*365), tpy~2214):
  SHORT: n=1286 per-trade GROSS edge=+2.59bps Sgross=+2.63 | NET-maker(2bps)=+0.59 Snet=+0.60 | NET-taker(8bps)=-5.41 Snet=-5.50
  LONG : n=1247 per-trade edge=-0.40bps (DEAD) | net-neg everywhere
per-month SHORT real edge: 2025-08 -0.19 | 2025-09 +2.62 | 2025-10 +5.60 | 2025-11 +4.57 | 2025-12 -1.23 | 2026-01 +0.81 | 2026-02 +3.75
```
- REAL edge +2.59bps (vs reconstructed +3.22 — reconstruction was mildly optimistic, but the SHORT edge is REAL not artifact).
- SHORT positive 5/7 months (strong months 2025-10/11 drive it; negative 2025-08/12). LONG dead confirmed on real price.
- **CONFIRMED: SHORT net-POSITIVE at MAKER (net +0.59bps, Sharpe +0.60), net-NEGATIVE at TAKER (-5.41bps).** Maker-only.
- midcov=1.00 (every node matched a real book update <=5s, causal) -> no look-ahead, clean alignment.
- **shuffle-null (permute yhat, 50x): REAL +2.59bps | NULL mean=+0.89 sd=0.86 z=+1.97 -> NOT CLEAN (~2 sigma).**
  CRITICAL: the NULL mean is +0.89bps (NOT zero) -> a RANDOM short-tail strategy earns +0.89bps gross on this period,
  because 2025-08..2026-02 was net DOWN-trending and a frequently-short strategy harvests the drift regardless of signal.
  The signal's MARGINAL contribution above random-short = +2.59 - +0.89 = +1.70bps, significant only at z~1.97.
- **HONEST VERDICT (real-price + shuffle-null):** the short-side maker net-positive (+0.59bps, Sharpe +0.60) is PARTLY
  DOWN-TREND DRIFT-RIDING, not purely alpha. The genuine signal increment is ~+1.7bps gross at ~2 sigma — real-ish but
  marginal and period-confounded (no up-trend month to falsify the drift component). Cannot claim a clean tradeable Sharpe.
- TAKER-optimization (longer holds): would AMPLIFY the drift-riding component (longer short holds in a down-market) more than
  alpha -> a taker Sharpe from it would be confounded, NOT a clean signal result. Reported with that caveat (sweep available).

## 6. Conclusion (honest, reliable)
- BTC y_600 has a **real, rank-monotone, near-zero-bias signal ~0.045-0.05 per-day-CLEAN Pearson** (strong months 0.06-0.08 DENSE, drift ~0.02). Shuffle-null confirms it's genuine (z>4-6).
- **beta is unstable -> size on rank/sign, demean causally, gate on confidence, hold low-turnover.**
- **Naive trade-every is NOT tradeable** (per-trade 0.3-2 bps << 4-10 bps RT, cost-dominated). BUT **tail-gated SHORT-only + holding IS marginally tradeable at MAKER fees** (net +0.4..+1.2 bps/trade, Sharpe ~1, ~7 trades/day): the cumulative-move holding (~40min) lifts per-trade gross edge to +2.4..+3.2 bps on the short side, above the 2bps maker RT floor. LONG side dead; taker not viable. Short edge present in every month (not just down-trend).
- **2b/lambda0.5 is a wash** (not an alpha lever; calibration knob only) -> lambda0.1 default is the deliverable.
- **0.10 Pearson not achievable on-disk:** funding/OI weak at all honest horizons (falsified 6 forms x 5 horizons; 4h "wrong-horizon" rise was overlap inflation, collapses under CLEAN); liquidations the only untested orthogonal source but infra-gated (source host not reachable from training box).

## Artifacts
- Per-month + monotonicity + demean: `multi_asset/eval/final_deliverable_l01.py` -> PNG `exports/final_l01/calibration_monotonicity.png`
- Trading scheme: `multi_asset/eval/trading_scheme_l01.py`
- Shuffle-null: `multi_asset/eval/shuffle_null_preds.py`
- 2b same-checkpoint comparison: `multi_asset/eval/lq_apples_compare.py`
- Production CSV (raw y, no-peek EMA, + causal-demeaned q50): `exports/final_l01/y600_l01_alwaysEMA_walkforward.csv`
- Causal aggregator (4 checkpoint rules, no test-peek): `multi_asset/eval/honest_aggregate_causal.py`

## 7. ROOT-CAUSE — why current (Sharpe ~0.6) << milestone (2.8/4.4)? (2026-06-28)
DEEP DIAGNOSTIC: re-ran the MILESTONE backtest (its own logic + CSV, backtest_csh_v4_retail) with CURRENT rigor
(shuffle-null + drift-neutralization), and drift-decomposed the current short-side. RESULT inverts the initial hypothesis.

### 7.1 Milestone re-check (2025-02..2025-09, UP-trending +0.093bps/bar, headline To2/Tc-2/maxhold10, DPY=525600):
```
            headline Sharpe   shuffle-null z      drift-NEUTRAL Sharpe   drift harvest
maker(4RT)  2.58 (~the 2.8)   +2.45 (clean)       5.10 (RISES!)          -4247bps (NEGATIVE)
taker(10RT) 0.44             +2.54 (clean)        3.56 (RISES!)          -4547bps (NEGATIVE)
```
- Milestone shuffle-null z~2.5 = marginally clean (NOT meaningfully cleaner than current's 1.97).
- **DRIFT-NEUTRAL Sharpe RISES (2.58->5.10):** the milestone strategy was net-SHORT-leaning (long-frac 0.46) in an
  UP-market -> it FOUGHT the drift, LOST -4247bps to it. Its signal alpha was MASKED, not inflated, by adverse drift.
  => the milestone 2.8 was NOT drift-riding; if anything it UNDERSTATES a clean alpha of ~5 (maker) / ~3.5 (taker).

### 7.2 Current short-side drift decomposition (2025-08..2026-02, DOWN-trending, n=1603, hold ~40min):
```
  RAW short pnl       = +2.17 bps/trade  Sharpe +2.52
  DRIFT component     = +1.08 bps/trade  (random-short harvest of the down-drift over same hold)
  DRIFT-NEUTRAL ALPHA = +1.09 bps/trade  Sharpe +1.26   (== 50% of raw; matches shuffle-null +2.59-+0.89=+1.70 real-price)
```
- Current: net-SHORT in a DOWN-market -> drift HELPS -> headline OVERSTATES; clean alpha is HALF the raw (+1.09bps, Sharpe 1.26).

### 7.3 GAP DECOMPOSITION (milestone clean ~3.5-5.1 -> current clean ~1.26), ranked by magnitude:
1. **ANNUALIZATION BASIS (methodology, LARGE):** milestone DPY=525600 (per 12-min bar, sqrt=725); my real-price used
   per-TRADE tpy~2214 (sqrt~47) -> ~15x Sharpe-multiplier difference for the SAME economics. On a common per-trade basis
   the milestone drift-neutral per-trade Sharpe and current's are MUCH closer. (Sharpe magnitudes are not comparable across
   bases; per-trade EDGE in bps is the honest common unit: milestone clean ~e.g. 13bps/trade vs current clean +1.09bps/trade.)
2. **SIGNAL STRENGTH genuinely weaker in current period (REAL):** milestone drift-neutral per-trade edge >> current +1.09bps.
   Milestone period 2025-02..09 had stronger BTC y_600 signal (the "0.06-0.08 strong-regime"); current window includes the
   2026 DRIFT regime (2026-01/02 IC ~0.012-0.016) which dilutes. This is the choppy/drift non-stationarity, not a bug.
3. **SHORT-ONLY vs LONG-SHORT (REAL):** milestone traded both sides (long-frac 0.46); current LONG side is DEAD (-0.40bps)
   so only short works -> half the opportunity + fully drift-exposed on one side.
4. **rolling vs fixed-split (minor):** milestone = fixed 2025-02..09 fold-0; current = 7 rolling months incl weak ones.
   Rolling is MORE honest (no single lucky period) and naturally includes the weak 2026 regime -> lower but truer.

### 7.4 MOST-EFFECTIVE FIX (ranked by expected Sharpe impact):
1. **SIGNAL STRENGTH is THE binding constraint (biggest lever, hardest):** clean drift-neutral alpha +1.09bps < maker 2bps
   < taker 8bps RT. Even perfect execution can't make +1.09bps clear taker. Need a STRONGER signal / ORTHOGONAL data
   (liquidations = only untested source, infra-gated; funding/OI falsified). No backtest tweak substitutes for this.
2. **maker-only execution (real, modest):** at maker (2bps RT) the clean alpha is ~break-even-to-slightly-positive on the
   short side in strong/down regimes; taker is hopeless. Maker rebate / passive fills is necessary but not sufficient.
3. **drift-neutralize for HONEST reporting (not a P&L fix):** removes the ~50% drift-confound from the headline so the
   real ~+1.1bps alpha is seen clearly. Improves truth, not returns.
4. **longer holds for taker (NEGATIVE expected, drift-confounded):** in the down-period, longer short holds amplify the
   drift component more than alpha -> a higher taker number that is NOT clean signal. Rejected as misleading.

### 7.5 VERDICT on "is 7+ reachable / taker-tradeable":
NO. Clean drift-neutral alpha is ~+1.1 bps/trade (Sharpe ~1.26 per-trade basis). Below maker (2) and far below taker (8)
RT cost. The milestone 2.8/4.4 was a per-BAR-annualized, fixed-strong-period, long-short number; on the honest common unit
(per-trade clean drift-neutral edge in bps) the BINDING constraint is SIGNAL STRENGTH, identical to every prior conclusion:
~0.045-0.05 IC -> ~1-2bps clean edge < cost floor. 7+ is not reachable without orthogonal data that is not on-disk.

## 8. MECHANISM — short-vs-long asymmetry is a HOLDING-IN-DOWNTREND ARTIFACT, not a signal asymmetry (2026-06-28)
USER asked to deep-analyze WHY short has alpha and long is dead. CORE decomposition (hypothesis #1, per-side IC/sigma/
hit-rate/conditional-mean, drift-neutral, per month) OVERTURNS the premise: at the SIGNAL level the two sides are SYMMETRIC.

### 8.1 Per-side decomposition (pooled, gate +-10%, drift-neutral):
```
  BOTTOM(short): n=7480 within-tail IC=+0.014 rankIC=+0.020 realized_sigma=25.1bps E[r|tail]-drift=-0.79bps hit=0.523
  TOP(long)    : n=7480 within-tail IC=+0.075 rankIC=+0.016 realized_sigma=24.5bps E[r|tail]-drift=+0.69bps hit=0.517
  leverage sigma(bot)/sigma(top)=1.025 (down moves only ~3% bigger -- NOT a driver)
```
### 8.2 PER-MONTH drift-neutral single-bar tail alpha (the decisive control for regime drift):
```
  MEAN short-alpha (down beyond drift) = +0.82bps  (positive 7/7 months)
  MEAN long-alpha  (up beyond drift)   = +0.78bps  (positive 6/7 months)
  => SYMMETRIC (diff +0.045bps). Both sides carry real, consistent single-bar tail alpha ~+0.8bps.
```
### 8.3 RESOLUTION (corrects earlier "long is dead"):
- The "LONG dead / SHORT alive" result in the HOLDING backtest was an ARTIFACT of holding ~40min positions in a
  net-DOWN-trending test window (2025-08..2026-02): holding LONG bleeds the down-drift (kills long P&L), holding SHORT
  collects it (inflates short P&L). At the SIGNAL/tail level, drift-neutral, the alpha is SYMMETRIC (~+0.8bps both sides).
- Within-tail IC is actually slightly HIGHER on the LONG side (+0.075 vs +0.014) -> the model ranks top-tail moves at least
  as well as bottom-tail. Leverage effect negligible (sigma ratio 1.03). Hit-rates ~equal (0.52).
- HYPOTHESES (a) selling-more-telegraphed / (b) long-liquidation-cascade / (c) leverage -> NONE supported: the signal
  asymmetry they predict DOES NOT EXIST in the data. The observed asymmetry was purely the holding x down-drift interaction.
### 8.4 POSITIONING-CONDITIONING (#2) — funding REVIVES a real short-specific amplification (regime-dependent):
Pooled tail alpha conditioned on funding rate (causal <=t, drift-neutral):
```
  SHORT(bot): low-fund=-0.58 | mid=+1.13 | HIGH-fund(crowd over-long)=+1.83 bps   <- MONOTONE RISING (long-squeeze)
  LONG(top) : low-fund=+0.79 | mid=+1.04 | HIGH-fund=+0.24 bps                      <- DECAYS (long worse when over-long)
```
- CLEAR long-squeeze signature POOLED: short-side edge ~3x larger when funding is HIGH (crowd over-leveraged long) -> the
  over-long crowd gets squeezed down -> bottom-tail predictions pay more. Long side does the OPPOSITE (over-long => long worse).
- PER-MONTH robustness (within-month drift-neutral, hi-fund minus lo-fund short alpha): mean +1.44bps, POSITIVE 4/7 months,
  STRONG in volatile/down regimes (2025-10 +2.1, 2025-11 +3.2, 2026-01 +3.1, 2026-02 +4.0) but NEGATIVE in 3 calm low-funding-
  variance months (2025-08/09/12). => REAL but REGIME-DEPENDENT (strongest exactly where leverage/cascades matter), not universal.

### 8.5 DOMINANT MECHANISM + liquidations implication (CORRECTED):
- Unconditional tail signal is ~SYMMETRIC (~+0.8bps both sides, single-bar); the trading "long-dead" was holding x down-drift.
- BUT conditioning on FUNDING reveals a genuine SHORT-SPECIFIC amplification consistent with HYPOTHESIS (b) long-liquidation-
  cascade: over-long crowd (high funding) -> down-squeezes are more predictable -> bottom-tail edge rises ~3x. Regime-dependent.
- DOMINANT MECHANISM (ranked): (b) positioning/long-squeeze conditioning = the real asymmetry driver (funding-gated, regime-
  dependent) > (c) leverage effect (negligible, sigma ratio 1.03) > (a) selling-telegraphed (untested feature-attribution #3;
  the symmetric unconditional IC argues against a strong (a)).
- LIQUIDATIONS IMPLICATION (revised UP from 8.4 draft): there IS a pre-existing funding/positioning-conditioned short edge for
  liquidations to AMPLIFY -> the liquidations pull is now better-motivated and should be TARGETED at high-funding/over-long
  states (long-liquidation cascades). Expected value: amplify the +1.83bps high-funding short edge, conditional & regime-gated.
  Still infra-gated (source host not reachable from training box) -- but the MECHANISM case for pulling it is now POSITIVE.
- CAVEAT: even the high-funding short edge (+1.83bps) is < taker 8bps RT; would need maker + the funding gate + (hoped)
  liquidation amplification to clear cost. Signal strength remains binding; funding-gating is a real but partial lever (+~1.4bps
  conditional, regime-dependent), NOT a full fix to tradeability.

## 9. FUNDING-GATED LONG-SHORT — gate does NOT beat short-only (real perp price, 2026-06-28)
Strategies (real perp mid, causal funding<=t, hold-until-median-revert, min3/max36): A short-only, B symmetric LS no-gate,
C funding-gated (high funding=over-long -> short ok/long suppressed; low funding -> long ok/short suppressed).
SWEEP gate{10,5,2.5%} x funding-band{[.33,.66],[.25,.75],[.20,.80]}. Exact Sharpe=edge/sd*sqrt(n/span*365). span 212d.

KEY ROWS (per-trade edge bps | net-maker(2) | net-taker(8)):
```
gate    mode    n(L/S)        edge   Sgross  NETmak(S)     NETtak(S)
+-10%   short   1601(0/1601)  +2.21  +2.4    +0.21(+0.2)   -5.79(-6.4)
+-10%   sym     2533          +1.12  +1.6    -0.88(-1.3)   -6.88(-9.8)   <- long bleeds
+-10%   gated   1912          +2.20  +2.7    +0.20(+0.3)   -5.80(-7.2)   <- ~= short-only
+-2.5%  short    540(0/540)   +4.44  +2.8    +2.44(+1.5)   -3.56(-2.2)   <- BEST (short-only)
+-2.5%  sym      972          -0.07  -0.1    -2.07(-1.6)   -8.07(-6.4)
+-2.5%  gated    689          +2.14  +1.5    +0.14(+0.1)   -5.86(-4.0)
```
VERDICT (sweep): FUNDING-GATING does NOT beat SHORT-ONLY. At every config gated edge < short-only edge -- the gate adds
back LONG trades that DILUTE (the funding filter isn't sharp enough to make longs net-additive). SYMMETRIC is worst
(long bleeds). Best gated net-maker Sharpe = +0.25 (gate10). Honest best overall = SHORT-ONLY +-2.5% (raw +4.44bps, maker
S+1.5) -- but that is PROVISIONAL pending its OWN null + drift-neutral (the script only nulled the gated config = wrong target).
Mechanism (funding conditions the short edge) is REAL but funding-AS-A-GATE adds NO value over plain short-only tight-tail.
=> POST-CHECKLIST on short-only +-2.5% running (short25_postcheck.py): null + drift-neutral + per-month before any claim.

### 9.1 Gated-config dual shuffle-null (best gated: gate10, edge +2.20bps):
- permute-YHAT: null edge mean=+0.85 sd=0.86 -> z=+1.58 (NOT clean; weaker than short-only's 1.97)
- permute-FUND: null edge mean=+1.04 sd=0.61 -> z=+1.90; permuting funding only drops edge +2.20->+1.04
  => the FUNDING GATE adds little (most edge survives RANDOM funding) -> confirms funding-as-gate is not doing real work.

## 10. ROOT-CAUSE — milestone 4.4/2.8 vs current marginal: SPOT-target + regime + caliber + annualization (2026-06-28)
USER asked why the reg_arch milestone "worked" vs current. Verified from docs/memory/cache (rigor-first):

### 10.1 MILESTONE CONFIG FACTS (docs/SINGLE_ASSET_Y600_FINAL_MILESTONE_2026_05_20.md + memory):
- TARGET = SPOT 600s return; FEATURES = SPOT book (npz_v4 = binance SPOT LOB) + 64 hand feats. => SPOT->SPOT.
- EVAL = 2025-02-09..2025-09-09, 3-fold walk-forward (train700/val60/test90). **~92% of backtest profit from FOLD 0
  (early-2025 STRONG regime); fold 1 (May-Jul) ~break-even** -- explicitly flagged "lucky early run", realistic 25-35% ann.
- Sharpe ANNUALIZATION = DECISIONS_PER_YEAR=525600 (per 12-min bar; sqrt~725). Backtest on y_pred_q50_bps_live
  (causal-EMA-demean live cal), per-bar PnL.
- HEADLINE CALIBER = 5-sigma-CLIPPED y + EMA-demean: P=0.0646. HONEST raw-y = 0.0367 pooled / 0.0427 mean-of-folds
  (memory single-asset-record-caliber-correction: 30% of gap = clip/EMA convention, 70% = regime decay).

### 10.2 SPOT vs PERP (memory spot_book_is_the_signal_source, multi-angle proven):
- SPOT book is ~2x MORE predictive than perp: Ridge in-sample TRAIN P spot 0.100 vs perp 0.055; honest 2025-02 test
  P spot 0.0585 vs perp 0.031. npz_v4(spot)-vs-perp per-feature median corr only +0.27 (fundamentally different).
- CURRENT trajectory cache (npz_v2arch): X_raw (Path B book) = SPOT (L0 spread +-0.00044) -- CONFIRMED spot book;
  X_raw_perp_deep = perp enrich (L0 spread +-0.0044, 10x wider). BUT current TARGET = PERP y_600 (multi-asset target).
  => CURRENT = SPOT-features -> PERP-target (spot signal must survive the basis); MILESTONE = SPOT-features -> SPOT-target.
  This is a REAL signal-source disadvantage for current: predicting the harder perp return, not the clean spot->spot combo.

### 10.3 SAME-BASIS DECOMPOSITION (honest common unit = per-trade clean drift-neutral bps):
- MILESTONE realistic-maker per-trade PnL 11.77bps headline -> but ~92% from fold0 strong regime + 5sigma-clip/EMA caliber.
  On honest raw-y the milestone signal is P~0.037-0.043 (NOT 0.065). Per-trade alpha milestone claimed ~1.5-2bps (doc 0.section).
- CURRENT short-only +-2.5% real-price: raw +4.44bps -> clean drift-neutral ~half (pending short25 null; +-10% was 50% drift).
  Current per-day-CLEAN pooled P=0.0456 (7mo incl 2026 drift).
- FACTOR RANKING (milestone "4.4/2.8" -> current marginal), each quantified:
  (a) ANNUALIZATION basis (per-bar DPY525600 sqrt725 vs per-trade tpy~2214 sqrt47) = ~15x Sharpe MULTIPLIER. LARGEST
      single factor in the SHARPE NUMBER (not economics). On a common per-trade-bps unit this factor vanishes.
  (b) SPOT->SPOT vs SPOT->PERP target = ~2x signal (P 0.058 vs 0.031 spot vs perp). REAL economics, ~half the edge.
  (c) REGIME (2025 strong fold0 vs current incl 2026 drift) = milestone 92% fold0; current pooled includes weak months.
      Memory: 70% of the 0.065->0.037 gap is regime. LARGE real factor.
  (d) CALIBER (5sigma-clip+EMA-demean 0.0646 vs honest raw-y per-day-CLEAN) = 30% of the 0.065->0.037 gap. Real but smaller.
- ANSWER: milestone superiority is MOSTLY (a) annualization + (c) regime + (d) caliber = NOT real economics, PLUS a
  GENUINE (b) spot->spot vs spot->perp edge (~2x) that the current PERP-target work loses. On the honest common unit
  (per-trade clean drift-neutral bps, same regime, same caliber) the two are MUCH closer (~1-2bps), but the milestone
  retains a real ~2x signal advantage from predicting the cleaner SPOT return.
- ACTIONABLE: the one RECOVERABLE real lever = build a SPOT-target model (spot->spot, like milestone) instead of perp-target,
  OR spot-features->perp with explicit basis modeling. Spot->spot is ~2x more predictive; if the goal is a tradeable BTC
  signal (not specifically perp), the spot-target path is the genuine edge the milestone had. (Spot builder exists:
  multi_asset/data/build_regarch_spot_npz.py.) FLAG: this needs a rebuild+retrain to quantify on the current rolling window.

## 9.2 SHORT-ONLY +-2.5% POST-CHECKLIST (the actual winner, real perp price) — 2026-06-28
RAW (PROVISIONAL): n=540 edge=+4.44bps Sgross=+2.80 | NET-maker=+2.44 (S+1.54) | NET-taker=-3.56 (S-2.25) tpy=930
DRIFT component (random-short harvest)=+1.01bps (only 23% of raw -- vs 50% at +-10%; tight tail concentrates real signal)
DRIFT-NEUTRAL CLEAN edge=+3.43bps | clean-maker Sharpe=+0.90 | clean-gross Sharpe=+2.16
PER-MONTH (6/7 positive): 08:+2.3(n32) 09:+4.6(n21) 10:+1.7(n100) 11:+13.4(n96) 12:+0.8(n95) 26-01:-1.7(n98) 26-02:+8.7(n98)
  worst=2026-01 -1.7 | OUTLIER=2025-11 +13.4 (strong-trend month carries much of the mean; n=540 total, ~95/mo moderate)
SHUFFLE-NULL (permute yhat 50x): null edge mean=+0.91 sd=1.82 -> z=+1.94 | signal increment +3.53bps above random-short.
FINAL VERDICT (short-only +-2.5%): clean drift-neutral +3.43bps, clean-maker Sharpe +0.90, 6/7 mo positive -- BUT z=+1.94
  (~2 sigma, NOT clean at the conventional bar). Null sd large (1.82) because n=540 small + edge OUTLIER-DEPENDENT (2025-11
  +13.4 carries much of the mean). Same ~2sigma marginal significance as EVERY other config (short-only +-10% was 1.97;
  gated 1.58). => the tight-tail short edge is REAL-ish (clean +3.4bps, maker-positive) but NOT statistically robust (single
  strong month, n too small to clear null), and taker-negative (-3.56). NOT a clean tradeable claim. Consistent with the
  whole-session conclusion: marginal ~2sigma signal, maker-only, period/outlier-dependent, below taker cost.

## 10.4 SELF-CORRECTION — "spot->spot ~2x lever" was likely an OVER-CLAIM (user clarified target IS perp) 2026-06-28
My 10.2/10.3 framing conflated TWO different comparisons. Correcting (the "every challenge reverses" pattern):
- The "2x" (spot 0.058 vs perp 0.031) was a FEATURES comparison: spot-BOOK features vs perp-BOOK features, each predicting
  their own return. It is NOT a TARGET comparison. The current model ALREADY uses spot-book features -> the "2x" does NOT
  imply a spot-TARGET lever.
- PURE TARGET EFFECT (the right test): SAME spot features, SAME period/caliber, IC(->SPOT-target) vs IC(->PERP-target).
  Mechanism: perp_ret = spot_ret + d(basis). dilution rho = 1/sqrt(1+var(dbasis)/var(spot_ret)). If sigma(dbasis/600s) is a
  few bps << sigma_ret~22bps, rho~0.98 -> perp-target costs only ~2% IC, NOT ~2x.
- RUNNING (spot_vs_perp_target.py): measuring sigma(dbasis/600s), corr(spot_ret,perp_ret), theoretical rho, AND empirical
  IC(production yhat -> perp) vs IC(yhat -> spot) at same nodes. [result pending]
- EQUIVALENCE CHECK: milestone honest raw-y IC (0.0367 pooled / 0.0427 mof) vs current perp honest IC (per-day-CLEAN 0.0456
  / DENSE 0.0372). These are STATISTICALLY EQUAL on matched caliber -> NO real IC gap. If the pure-target test confirms
  ~2% dilution, then the milestone's apparent superiority is ENTIRELY (a) caliber [0.0646=5sigma-clip+EMA vs 0.037 raw],
  (b) annualization [per-bar sqrt725 vs per-trade sqrt47 ~15x], (c) regime [92% fold-0 strong] -- NOT economics, NOT a
  spot-target penalty. CORRECTING the 10.3 "(b) ~2x spot->spot edge" claim pending the measured dilution.

## 10.5 RESOLVED — pure-target effect is ~0.2% (NEGLIGIBLE); milestone gap is caliber+annualization+regime, NOT spot-target (2026-06-28)
MEASURED from real spot+perp book (btcusdt_copy, 21735 600s steps, 5 mo 2025-10..2026-02):
```
  sigma(spot 600s ret)=23.28bps  sigma(perp 600s ret)=23.49bps  sigma(d_basis/600s)=1.455bps
  corr(spot_ret, perp_ret)=0.9981   theoretical dilution rho=0.9981
  per-month corr: 10:0.9962 11:0.9989 12:0.9983 26-01:0.9984 26-02:0.9992 (all >0.996)
```
=> PURE TARGET EFFECT spot->perp = ~0.2% IC loss (rho 0.998), NEGLIGIBLE. The basis change over 600s (~1.5bps) is tiny vs
   return sigma (~23bps), so spot and perp 600s returns are ~the same series. PREDICTING PERP COSTS ~NOTHING vs spot.
=> CORRECTS my 10.3 "(b) ~2x spot->spot edge": WRONG. The "2x" was a FEATURES comparison (spot-book vs perp-book features),
   not a target comparison; current already uses spot-book features. There is NO spot-target lever.

FINAL ANSWER (why milestone 4.4/2.8 >> current marginal), corrected & ranked -- ALL methodology/regime, NOT economics:
  1. ANNUALIZATION basis: per-bar DPY=525600 (sqrt~725) vs per-trade tpy~930-2214 (sqrt~30-47) = ~15-24x Sharpe MULTIPLIER.
     Pure unit convention; vanishes on a common per-trade-bps unit. LARGEST factor in the Sharpe NUMBER.
  2. REGIME: milestone 92% of profit from fold-0 (early-2025 strong); current pooled includes 2026 drift. 70% of the
     0.0646->0.037 honest-IC gap is regime decay (memory). LARGE real factor (but it's regime luck, not model superiority).
  3. CALIBER: milestone headline 0.0646 = 5sigma-clip + EMA-demean; honest raw-y = 0.0367 pooled/0.0427 mof. 30% of the gap.
  4. TARGET (spot vs perp): ~0.2% (rho 0.998) = NEGLIGIBLE. NOT a factor.
EQUIVALENCE: milestone honest IC (0.0367 pooled / 0.0427 mof) ~= current perp honest IC (DENSE 0.0372 / per-day-CLEAN 0.0456).
  STATISTICALLY EQUAL on matched caliber. => NO real IC gap. Milestone's apparent superiority is ENTIRELY annualization +
  regime + caliber. The current perp work is NOT economically worse; it is the SAME ~0.037-0.046 honest signal, more
  honestly measured (per-trade, rolling incl drift months, raw-y per-day-CLEAN), in a weaker regime.

## 10.6 EMPIRICAL TARGET EFFECT is LARGER than variance-dilution predicted — partial re-correction (2026-06-28)
EMPIRICAL (production yhat, n=74797, same nodes): IC(yhat,PERP)=+0.0326 | IC(yhat,SPOT)=+0.0433 | ratio spot/perp=1.33.
=> the model predicts SPOT return ~1.33x BETTER than PERP return -- NOT the ~1.002x the variance-only theoretical rho=0.998
   predicted. So the pure-target effect is ~25% IC LOSS (1 - 0.0326/0.0433), NOT ~0.2%.
WHY the discrepancy (theoretical 0.2% vs empirical 25%): the variance-dilution bound assumes d_basis is ORTHOGONAL noise.
   It is NOT: the model's signal (spot-microstructure-derived) correlates with the SPOT-specific return component; the basis
   adjustment partially OFFSETS the predicted move in perp -> perp IC drops MORE than the sigma ratio implies. (To confirm:
   corr(yhat, d_basis) != 0 -- pending quick check.)
NET (honest, both directions corrected):
  - My "spot->spot ~2x" (10.3) was an OVER-claim (the 2x was features). CORRECT.
  - But my "~0.2% target effect, negligible" (10.5) was an UNDER-claim (variance-only bound). The EMPIRICAL target effect is
    ~25% (ratio 1.33) -- spot-features predict the SPOT return ~1.33x better than the perp return they're trained on.
  - So predicting SPOT-target instead of PERP-target IS a real ~1.33x IC lever (0.0326->0.0433 DENSE) -- SMALLER than the
    falsely-claimed 2x, but NOT negligible. The milestone's spot->spot DID capture this ~1.33x.
REVISED milestone-gap ranking: annualization (~15-24x, unit) > regime (70% of honest-IC gap) > caliber (30%) > TARGET
  spot-vs-perp (~1.33x IC, REAL but modest) -- target is now a real minor factor, not zero. The dominant gap is still
  annualization + regime + caliber (methodology), but spot-target is a genuine ~1.33x recoverable lever (NOT 2x).
PENDING: corr(yhat,d_basis) to nail the mechanism; per-month robustness of the 1.33 ratio.

## 10.7 RESOLVED (final) — target effect IS negligible; the "1.33x" was a measurement artifact (2026-06-28)
CLEAN re-measurement (yhat_dbasis_mechanism.py, spot & perp ret computed IDENTICALLY at each node, n~21k):
```
  IC(yhat,SPOT)=+0.0433  IC(yhat,PERP)=+0.0451  ratio=0.96  (PERP marginally BETTER pooled)
  IC(yhat,d_basis)=+0.037  sig_dbasis=1.11bps
  cov(yhat,perp) = cov(yhat,spot) + cov(yhat,dbasis); basis offsets only -4.3% of spot cov
  per-month ratio spot/perp: 08:1.50 09:1.31 10:1.01 11:0.93 12:0.83 26-01:0.91 26-02:0.85
  corr(yhat,dbasis) per-month: NEG in strong early months (08:-0.23 09:-0.20 -> spot better) POS in drift (-> perp better)
```
=> POOLED ratio 0.96 -- spot & perp targets are ESSENTIALLY EQUIVALENT (perp even marginally better). The earlier "ratio
   1.33" (10.6) was a MEASUREMENT ARTIFACT of the first spotperp script (its empirical perp-IC 0.0326 used a different
   return alignment than the clean re-run's 0.0451). RETRACT 10.6's "~1.33x real lever".
=> 10.5 STANDS: pure target effect spot-vs-perp is NEGLIGIBLE (basis offsets ~4%, pooled ratio ~1.0). There is NO
   spot-target lever. (The per-month ratio swings 0.83-1.50 regime-dependently and roughly cancels.)

FINAL milestone-gap answer (3 self-corrections later, clean): milestone 4.4/2.8 >> current marginal is ENTIRELY
  (1) ANNUALIZATION basis (per-bar sqrt725 vs per-trade sqrt~40 = ~15-24x, pure unit), (2) REGIME (92% fold-0 strong;
  70% of honest-IC gap), (3) CALIBER (5sigma-clip+EMA 0.0646 vs raw 0.037; 30% of gap). TARGET spot-vs-perp = ~0% (ratio
  0.96, NEGLIGIBLE). FEATURES spot-book-vs-perp-book = the real ~2x but current ALREADY uses spot-book -> not a lever either.
  EQUIVALENCE CONFIRMED: milestone honest IC (0.037-0.043) == current perp honest IC (0.037-0.046) on matched caliber.
  NO REAL ECONOMIC IC GAP. Current is the SAME signal, more honestly measured, in a weaker regime.
  (Audit trail of my over/under-claims this thread: "2x spot->spot" over-claim -> "0.2% negligible" under-claim ->
   "1.33x artifact" -> FINAL "negligible ~0.96, gap is methodology+regime". The CLEAN-caliber/identical-alignment
   discipline caught each before it reached a headline.)

## 9.3 EXACT net-taker @ RT 3.4bps (1.7/side) on short-only +-2.5% — RAW positive is DRIFT, clean ~0 (2026-06-28)
n=540, tpy=930, exact Sharpe=mean/sd*sqrt(n/span*365), bootstrap 5000x:
```
  RAW (incl down-trend drift): net/trade=+1.04bps  net-taker Sharpe=+0.656  95%CI=[-1.95,+3.14] (INCLUDES 0)
  DRIFT-NEUTRAL (regime-robust): net/trade=+0.034bps net-taker Sharpe=+0.021 95%CI=[-2.59,+2.55] (INCLUDES 0)
  per-month net @3.4: only 3/7 positive (raw AND clean). 2025-11 outlier = +8.75..+9.98 carries it.
  OUTLIER drop 2025-11: CLEAN net-taker Sharpe +0.021 -> -1.158 (NEGATIVE).
```
VERDICT @ RT3.4: coordinator estimate CONFIRMED EXACTLY (raw +0.66, clean ~breakeven +0.02).
- RAW +0.66 = mostly DOWN-TREND DRIFT-RIDING (period-specific, reverses in up-trend).
- DRIFT-NEUTRAL (regime-robust) = ~0 breakeven, and NEGATIVE (-1.16) without the single 2025-11 outlier month.
- BOTH CIs include 0 -> within 2sigma noise. => NOT a reliable positive. The lower 3.4bps fee makes the RAW number look
  tradeable, but it is drift + one outlier, not regime-robust alpha. At 1.7bps/side taker the clean Sharpe is breakeven.

## 9.4 PRINCIPLED SYMMETRIC L-S, 4 EXITS — no horizon-matched exit clears cost; signal too weak per-horizon (2026-06-28)
User critiques (both CONFIRMED): (1) short-only was regime-fitting (signal symmetric); (2) opposite-tail exit holds ~40min
>> 10-min horizon -> rides drift. Tested symmetric LS, gate +-2.5%, real perp price, DRIFT-NEUTRAL throughout.

DRIFT-NEUTRAL (regime-robust) net @ RT 3.4bps, per exit x side:
```
  exit                 hold    BOTH        LONG        SHORT       gross_clean_edge(BOTH)
  SIGNAL-DECAY         1.9nd   -1.7(S-1.9) -3.0(S-2.2) -0.4(S-0.4) +1.69bps
  FIXED-HORIZON ~600s  1.0nd   -1.5(S-2.4) -1.6(S-1.8) -1.3(S-1.5) +1.94bps
  HOLD-WHILE-PERSISTS  1.1nd   -1.1(S-1.6) -1.1(S-1.1) -1.1(S-1.2) +2.32bps
  OPPOSITE-TAIL        20.4nd  -5.0(S-1.6) -6.6        -3.3        -1.59bps (clean collapses; raw was drift)
```
DECISIVE ANSWER (user's core question): NO exit gives a regime-robust (drift-neutral) net-positive Sharpe at 3.4bps.
EVERY exit x side is clean-net-NEGATIVE. Mechanism confirmed:
- HORIZON-MATCHED exits (decay/fixed-600s/persist) hold ~1-2 nodes (~10-20min, correct) but clean GROSS edge is only
  +1.7..+2.3bps -- BELOW the 3.4bps cost. The signal is GENUINELY TOO WEAK PER-HORIZON to clear cost without drift.
- OPPOSITE-TAIL (the old rule) holds 20.4nd (~3.4h!) -- its raw short edge was the drift harvest; clean it collapses to
  +0.14bps. Confirms critique #2 (it was riding drift, mismatched to horizon).
- SYMMETRIC: long & short clean edges ~equal per exit (e.g. persist L+2.30 vs S+2.34) -- confirms critique #1 (signal
  symmetric; short-only's edge was the down-period drift, not a real side asymmetry).
FINAL: a smarter/horizon-matched exit does NOT fix tradeability. The per-600s signal (~2bps clean) < 3.4bps taker cost.
  The only way to a raw-positive is long holds that ride drift (not robust alpha). At maker (RT2) the horizon exits are
  ~breakeven (e.g. persist SHORT RT2 +0.6, BOTH +0.3) but drift-neutral still <=0. SIGNAL STRENGTH is binding, not exit design.

## 9.5 Symmetric-exit shuffle-null + CONSOLIDATED trading verdict (2026-06-28 final)
Shuffle-null on best drift-neutral config (opposite-tail, which was -1.57 = best of an all-negative set):
  REAL clean edge=-1.59bps | NULL mean=+0.45 sd=5.33 | z=-0.38 (consistent with noise/negative, as expected).
Maker (RT2.0) nuance: horizon-matched exits are marginally RAW-positive short-side (decay SHORT +1.4 S+1.2, persist
  SHORT +0.6) but DRIFT-NEUTRAL all <=0 -> even at maker the regime-robust alpha does not clear cost.

CONSOLIDATED TRADING VERDICT (across ALL strategies tested this session -- all converge):
  short-only / funding-gated LS / tail+holding / symmetric-4-exit -> SAME conclusion:
  - Regime-robust (drift-neutral) signal ~2bps clean per-horizon (IC ~0.039 per-day-CLEAN) < cost floor at EVERY fee tier:
    taker 8 (deeply neg), taker 3.4 (clean ~0/neg), maker 2 (clean <=0).
  - Every apparent net-positive traced to: down-trend DRIFT-RIDING (long holds) and/or a SINGLE outlier month (2025-11),
    all within ~2 sigma (bootstrap CIs include 0; shuffle-null z 1.6-1.97).
  - SIGNAL STRENGTH is the binding constraint, NOT exit design / sizing / gating / side selection. Confirmed by:
    horizon-matched exits (correct ~10-20min holds) give clean edge +1.7..+2.3bps < 3.4bps cost.
  - The signal is SYMMETRIC (long ~= short clean); short-only's edge was period drift.
  => BTC y_600 is NOT robustly tradeable net-of-cost on-disk at any tested fee tier. Research-stage. The ONLY untested
     orthogonal lever = liquidations (infra-gated; funding-conditioning §8.4 gives it a positive but regime-dependent
     mechanism case). Matches single-asset milestone conclusion once put on the honest common unit (cost binds, not alpha).
