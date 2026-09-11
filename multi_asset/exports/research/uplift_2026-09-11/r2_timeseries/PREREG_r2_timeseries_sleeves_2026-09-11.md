> **创建:** 2026-09-11 | **Session:** b9646a9e (round-2 time-series sleeve hunter) | **状态:** 预注册(判据冻结先于任何候选数字; GATE P 已逐位通过) | **作废条件:** 判据在看到任何 arm 的 g 序列后被改; 触碰实盘

# PREREG · Round-2 TIME-SERIES sleeve family

## 0. GATE P (VERIFIED, before any measurement)
Device `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`,
all six knobs off, cwd `/workspace/uplift_2026-09-11/r2_ts/dev` (own symlink tree, nothing written outside
`/workspace/uplift_2026-09-11/`). Reproduces the archived `w10_ablation_series_V4_A0_{dyn,fix}_s{42,2027}.npz`
`d30_n2_c42_rec` AND `d30_n2_c42_W` **BITWISE (np.array_equal True, 4/4 arms, shapes (10039,23) and (10039,829))**.

## 1. Why a time-series family
A0 demeans every anchor's cross-section (`w[sel] -= w[sel].mean()`). **Everything in the cross-sectional MEAN is
discarded by construction.** A sleeve that bets on the aggregate is therefore structurally a different bet, not a
re-weighting. That is the structural argument; it is not evidence, and correlation to A0 is measured, not assumed.

## 2. Sleeve book construction (frozen)
Same panel / meta / universe / cost model as A0 (v4 pin). At anchor i:
- eligible set `sel` built by the device's own rule: members[i] (MEMBERS_TOPN=829) ∩ UMASK m1 (umask_UPIT_CRYPTO)
  ∩ finite y4 ∩ qv4h ≥ 2.5e5; anchors with |sel| < 80 skipped (identical to the device).
- position `s_i ∈ [-1,+1]` from the sleeve signal, CAUSAL: every window ENDS ON the panel row of anchor E
  (row j = pw_row[E_ts[i]]), i.e. it uses bar [E-4h, E] and earlier, never [E, E+4h].
- target weights `tgt = s_i / |sel|` on sel, 0 elsewhere (equal weight, L1 = |s_i|).
- SAME execution chain as the deployed book: `sm = H + 0.1*(tgt - H)`, band `|trade| < 2.5e-4 ⇒ no trade`,
  forced exit of non-sel names. gross_i = Σ|sm|.
- Accounting, CAL=log (pin: the pod 5m lineage y4 IS the accounting quantity, no expm1):
  `pnl_i = Σ sm·y4 ·1e4`, `carry_i = Σ sm·f_fund_now·(4/iv) ·1e4`, `cost_i = Σ |Δsm|·tier_rate` with
  COSTB_JSON=calib/costb_fee_steady.json tiers, `net_i = pnl_i − carry_i − cost_i`. Identity asserted per anchor.

## 3. Statistic (copied verbatim from judge_v4 where applicable)
- A0 reference series `g_A0,i = rec[i,18]/rec[i,5]` = net_ex/gross_total, bps per anchor per unit gross.
- Sleeve level `standalone_bps_per_anchor_per_gross = mean(net_i)/mean(gross_i)` (DEPLOYED-gross convention,
  directly comparable to A0's +0.663).
- Sleeve `standalone_sharpe = mean(net_i)/std(net_i,ddof=1)·sqrt(2190)` on the ALLOCATED-budget series (budget = 1
  unit of gross; Sharpe is scale-invariant so this is the number that enters SR_total = sqrt(Σ SR_i²)).
- Windows, every arm on the SAME span: FULL CYCLE 2022-01-31 → 2026-08-31 (n = 10039 panel rows, the device's own
  span); FROZEN 2025-03-01 → 2026-08-10 20Z; 2024-on; OUT-OF-FIT STRESS 2026-08-11 → 2026-08-31 (n = 121).
- Bootstrap: UTC-day block, 2000 resamples, `numpy.default_rng([20260905, k])`, per-contrast substream k.
- SE(annualised Sharpe) = sqrt(2190/N) = 0.47 full cycle, 0.83 frozen.
- `carry_fraction_of_net := (−carry_i mean)/(net_i mean)` = fraction of net that is carry RECEIVED.
  (A0's is −1.08: A0 PAYS carry, its alpha is price. > +0.40 ⇒ the sleeve belongs to the closed carry axis.)

## 4. K DECLARED BEFORE LOOKING: **K = 25 arms in 7 families**
- F1 TSMOM aggregate trend, lookback L ∈ {6, 12, 30, 42, 90, 180} anchors — **6 arms**
- F2 AGG-FUND level (XS median 8h-equiv funding at E), z-window ∈ {90, 180, 360} — **3 arms**
- F3 AGG-FUND surprise / term structure (XS median of rate_now − rate_ema), z-window ∈ {90, 180, 360} — **3 arms**
- F4 XS DISPERSION timing, z-window ∈ {90, 180, 360} — **3 arms**; plus 1 arm dispersion→A0 gross scaling — **1 arm**
- F5 VOL TERM STRUCTURE, (short, long) ∈ {(6,42), (12,90), (30,180)} — **3 arms**
- F6 PARABOLIC-ONSET CONTINUATION (project clue), θ ∈ {5, 8, 12}% — **3 arms**
- F7 BREADTH (fraction of names with positive trailing return), z-window ∈ {90, 180, 360} — **3 arms**
Bonferroni over K=25: two-sided per-arm α = 0.002, z = 3.09. Placebos and the in-book blend of a SURVIVOR are
confirmatory, not selection, and are not counted in K.

## 5. Admission rule (frozen)
**ADMITTED** requires ALL of:
 (a) standalone FULL-CYCLE Sharpe ≥ 1.50;
 (b) |corr(g_sleeve, g_A0)| ≤ 0.25 on the FULL CYCLE;
 (c) carry_fraction_of_net ≤ +0.40;
 (d) BOTH placebos fail: per-anchor permuted feature and the operator applied to a permuted signal, each with
     |level| ≤ 0.3 × the real arm AND CI95 containing zero;
 (e) ≥ 4 of 5 calendar years (2022..2026) positive in level;
 (f) forward rank-IC at k=0 exceeds |backward IC| at k=−1 (a k=−1 reading that dwarfs k=0 = no forward power);
 (g) monotone dose response in the signal→position gain;
 (h) in-book blend delta vs A0 with CI95 excluding zero at the BONF25 level.
**NEAR_MISS** = (a) in [1.20, 1.50) or (b) in (0.25, 0.35] with everything else passing. Otherwise **REJECTED**.
A family with zero admissions is a reported result, not a failure to report.

## 6. AMENDMENT 1 (written BEFORE any candidate arm was run; no g-series had been computed)
Reading the device closed a structural fact I had not priced: the executor caliber re-demeans the non-zero set
(`smr[nz] -= smr[nz].mean()`, device L~330, blueprint `dl_quant_live/signal/legs.py:124`). **A purely directional
sleeve is annihilated by that operator** (sm = +c on every sel name ⇒ smr ≡ 0). Consequences, frozen now:
1. Sleeve arms are accounted in the **FILE caliber** (`net = pnl − carry − cost` on `sm`, no re-demean); A0's
   reference `g` stays the judge's `net_ex/gross_total`. Both are stated wherever quoted.
2. Any directional sleeve that survives carries a **deployment blocker**, reported as a hole, not hidden.
3. Added family **F8 BETA-ROTATION** — the dollar-neutral, executor-legal expression of the same time-series bet:
   long the low-beta half / short the high-beta half of `sel` (beta = trailing 180-anchor regression of the name's
   y4 on the equal-weight market return, ending on row j), signed by the timing signal. Applied to ONE a-priori
   lookback per timing family — F1 L=42, F2 z180, F3 z180, F5 (12,90), F7 z180 — **5 arms**, no selection.
**K revised to 30.** Bonferroni two-sided α = 0.05/30 = 0.001667 ⇒ z = 3.14.
4. In-book blend for a directional sleeve is computed on the COMBINED weight matrix
   `W = (1−w)·W_A0 + w·W_sleeve` with the full accounting re-run on `W` (turnover netting handled correctly),
   compared against A0's own file-caliber net on `W_A0`. Paired per anchor, same bootstrap.

## 7. AMENDMENT 2 (still before any candidate arm; span pin + sign rule)
- **FULL CYCLE pinned to 2022-01-01 → 2026-08-10 20Z, n = 9918**, because that is the span on which A0's headline
  reproduces: VERIFIED from `w10_ablation_series_V4_A0_dyn_s42.npz`, `g = rec[:,18]/rec[:,5]`, mean **+0.6627**,
  annualised Sharpe **1.316** (brief: +0.663 / 1.32). On 2022-01-31 → 2026-08-31 (n=10039) the same A0 arm is
  +0.6152 / 1.213 — reported wherever used, never mixed.
- **Sign is not a free parameter.** F1 fixed +1 (trend-following prior), F2 and F3 fixed −1 (crowding prior);
  F4, F5, F7 have no directional prior and use a CAUSAL walk-forward sign: `sgn_i = sign(corr(z_t, mret_t))` over
  the trailing 720 anchors t < i. This prevents a hidden ×2 sign-mining multiplicity.
- **Common burn-in**: every arm holds position 0 for the first 900 anchors (matches the book's LOOK=900), so every
  variant is evaluated on the SAME span with the SAME warm-up. Primary statistics INCLUDE those zero anchors.

## 8. AMENDMENT 3 (before any F6 number; execution chain for the event family)
F6 (parabolic-onset continuation) is a ONE-ANCHOR event response: the mechanism (PREREG_crash_continuation_parabolic
_stratum_2026-09-06 §1) is a move over the 4h that FOLLOWS the onset. The deployed EMA(0.1) chain puts only 10% of
the target into the book on the first anchor, so it cannot express a one-anchor bet. F6 therefore runs with
**no EMA and no band — the target is taken in full and the full round-trip cost is charged** at the same COST_B
tiers. That makes F6 the most cost-exposed arm in the family, which is the honest direction for this deviation.
F6 construction, frozen: at anchor E, trigger = (3-day gain over the 864 5m bars ending at E ≥ +20%, ≥ 80% finite)
AND (the running cumulative 5m return WITHIN the previous anchor interval [E−4h, E] reached ≤ −θ). Position
= SHORT, weight −1/10 per triggered name (nominal basket 10), gross capped at 1. 5m source = the pinned
`dlnative_5m_wide829_f16_holefix2.npz`. θ ∈ {5, 8, 12}%.

## 9. AMENDMENT 4 — K EXTENSION, declared AFTER the first 30 arms were read (flagged as such)
The brief named "funding term structure (1h vs 4h vs 8h names)" and my K=30 covered funding term structure only as
rate-minus-EMA (F3), not as the VENUE's funding-INTERVAL structure. Leaving a named direction unmeasured is worse
than measuring it with an honest multiplicity penalty, so I add family **F9** and raise **K to 34**
(Bonferroni two-sided α = 0.05/34 = 0.00147, z = 3.18). These four arms were specified before they were run but
after the first 30 were read; they are EXPLORATORY and cannot be admitted on this round's evidence alone.
- F9a/b/c: `IVFRAC` = fraction of `sel` names with a finite funding quote whose `f_fund_iv ≤ 2` (the venue has moved
  them to 1h/2h funding = venue-declared funding extremity), z-window ∈ {90, 180, 360}, causal walk-forward sign,
  directional market expression — **3 arms**.
- F9d: the DOLLAR-NEUTRAL, executor-legal cross-sectional expression — long the `f_fund_iv == 8` names, short the
  `f_fund_iv == 4` names, equal weight within each side, L1 = 1, no timing — **1 arm**.
