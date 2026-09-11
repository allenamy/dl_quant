> **创建:** 2026-09-11 | **Session:** round-5 NEW DATA 3 (universe / listings) | **状态:** 预注册, 冻结于看任何臂数字之前 | **作废条件:** v4 口径链作废或在役书换装

# PREREG — NEW DATA 3: the names the book cannot see

## 0. Caliber (pinned, copied from the round-5 brief)
Device `/workspace/uplift_2026-09-11/w10_sleeve.py` sha256 `b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650`, UNMODIFIED.
GATE P re-run by me in `/workspace/uplift_2026-09-11/r5nd/` → `GATE_P_r5nd.json` PASS, all four cells bitwise on
`d30_n2_c42_rec` (10039x23) and `_W` (10039x829).

**ENV WHITELIST (asserted; every var my runs set, E-0826-D):**
`LEGS=101, CAL=log, WRULE=msharpe, LOOK=900, MEMBERS_TOPN=829, FTRIM=zero, PHI=0.45, UMASK_SCOPE=m1,
UMASK_NPZ=<arm mask>, SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy, FSEED in {42,2027},
FPRED=f10_A0_s{FSEED}.npy, COSTB_JSON=/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json,
W3FIX=0.21,0,0.79 (fix seat only), FEMAT_NPZ=<sleeve matrix> (sleeve arms only), OUT_TAG=<tag>,
OMP_NUM_THREADS=3, OPENBLAS_NUM_THREADS=3, MKL_NUM_THREADS=3.`
Nothing else is set. `FTRIM_TH` left at its default `-0.0010`; all of LTRIM_TH/CDAMP/SLEEVE/RNSM/FTPOS/
SEATNET/SEATF10/KTAIL/KMOD*/FUNDSCALE/TRADE_TOPN/REF_SKIP unset (device self-reports them into config_json).

**Statistic.** g = net_ex / gross_total (bps per anchor per unit gross), paired per anchor on common support,
UTC-day block bootstrap B=2000, rng `numpy.default_rng([20260905,k])`. Sharpe = mean/sd*sqrt(2190).
E-0911-A: the first 900 device rows are dropped from every reading. Span FULL_pw =
2022-01-01T00:00 .. 2026-08-10T20:00 (the round-4 full-cycle span). Four cells: seat {dyn,fix} x seed {42,2027}.

## 1. Declared K (fixed before any arm was run)
**K = 8** confirmatory book-change tests. Bonferroni alpha = 0.05/8 = 0.00625 → admission requires the paired
two-sided **CI99.375** on dg = g(arm) - g(A0) to exclude 0 in the arm's favour in **all four cells**, plus the
standard battery. CI95 is also reported for comparability with rounds 1-4 but is NOT the admission bar.

| # | arm | change to the book |
|---|---|---|
| H1 | `U_WIDE529` | membership breadth 449 -> 529 (venue-size), same monthly PIT ranking |
| H2 | `U_WIDE600` | membership breadth 449 -> 600 |
| H3 | `U_QTR` | refresh cadence monthly -> quarterly (hold the Jan/Apr/Jul/Oct selection) |
| H4 | `U_FROZEN_PIT` | refresh cadence monthly -> frozen at the first month of each 12-month block |
| H5 | `SL_AGE25` | in-book sleeve: fund score -> 0.75*ZF + 0.25*Z(-age) (young-listing tilt) |
| H6 | `SL_AGE50` | same at 0.50/0.50 |
| H7 | `U_NOYOUNG` | drop names younger than 90 days from the member set |
| H8 | `U_DROPTAIL` | drop the bottom 50 member names by trailing-30d quote volume each month (449 -> 399) |

Everything else in this study (the staleness curve, the listing-age return/funding profile, the forced-exit and
min-notional tails, the venue enumeration) is **descriptive measurement, not an admission test**, and is excluded
from K. Any arm not in this table that I run is exploratory and is labelled as such; it cannot be admitted in
this round.

## 2. Gates every candidate must clear (fixed before looking)
1. **Mask parity gate (G0).** My re-derived MONTHLY mask must reproduce the pinned `umask_UPIT_CRYPTO.npz`
   cell-for-cell. If it does not, the pinned mask stays the A0 control and my re-derived MONTHLY mask is
   reported as a separate control so that the cache difference cannot be mistaken for a cadence effect.
2. **Turnover-matched nulls.** SHIFT101 / SHIFT503 / SHIFT1009 / RELAB1-3 built verbatim per
   `r3_attack_b9646/null.py` (sha 91d4c91cb92a6440), applied to the candidate's NEW input only. Both pnl_ex
   (gross) and g (net) reported. The defective per-anchor permutation placebo is NOT used.
3. **Tail-concentration ruler** `r3_gates/rs_conc.py` (sha 3fd2f76496a593ba): top-20 share and ex-top-20 Sharpe.
   Live fund-leg control = 11.09% / +6.71. RESID_SHARPE died at 130-189% / -2.40.
4. **Forward vs backward rank-IC at k = -3..+3**, reported as a spectrum, not a single ratio.
5. **Carry fraction of net**, and correlation of the arm's per-anchor g to A0's.
6. **Capacity**: for any new-listing claim, the min-notional floor and the achievable per-name notional at
   USD 230k and at USD 1M gross must be stated, or the claim is not admissible.

## 3. Pre-declared predictions (so a restatement cannot be mistaken for p-hacking)
- The v3-lineage receipt (`docs/AUDIT_live_vs_replay_2026-09-04.md` row 2) says the frozen universe costs -8%
  (monthly) / -43% (quarterly) Sharpe on 2023+. If the v4 redo reproduces a cadence cost of that order, H3/H4
  are *costs*, not admissions, and the deliverable is a refresh proposal, not a sleeve.
- `young_listings_carry_fund_alpha` predicts young names carry fund alpha. If true, H5/H6 should show positive
  dg; if the effect is a pure liquidity/Amihud restatement it will be collinear with the round-4 Amihud sleeve
  (rho to be reported) and is then NOT new information.
- Prior over all eight: low. Four rounds and ~300 candidates have admitted nothing.

## 4. AMENDMENT 1 (2026-09-11, written after opening the `young_listings_carry_fund_alpha` receipt and
## BEFORE any arm number was read; the universe arms H1-H4/H7/H8 were already launched, the sleeve arms were not)
The receipt does NOT say young names are a long. It says the **fund leg's IC is 3-4x higher on names listed
< 90 days** (2026: +0.086 young vs +0.024 old) and that deep-negative funding is 3x more common there. That is
an **interaction**, not a tilt. H5/H6 as declared (a direct young tilt of the fund score) test the wrong
functional form, but they stay in the family — a declared test is not dropped because it became inconvenient.
Two arms in the form the receipt actually supports are ADDED:

| # | arm | change to the book |
|---|---|---|
| H9  | `SL_AGEMOD50` | fund score -> ZF*(1 + 0.5*AY), AY = 2*rank(-age) in [-1,+1]; the device re-ranks, so young names are pushed further into BOTH tails = more weight where the signal is strong |
| H10 | `SL_AGEMOD100` | same at a = 1.0 |

**K is raised from 8 to 10.** Bonferroni alpha = 0.05/10 = 0.005 -> admission requires the paired two-sided
**CI99.5** on dg to exclude 0 in the arm's favour in all four cells. This amendment is a restatement of the
family before the fact, not a re-selection after it (`prereg_restatement_vs_phacking`).

**Age caliber, declared:** age = (anchor - first finite log_qv bar in the pinned 5m cache) / 86400. Names whose
first bar is within the first 3 cache bars are assigned the cache start 2022-01-01, so the entire pre-2022
cohort is TIED at the old end and the signal cannot order within it. This is the same listing rule
`build_umask.py` uses for its >= 30-day eligibility test, so the age axis and the membership axis agree.
